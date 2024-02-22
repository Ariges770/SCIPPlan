import ast
import operator as op
from typing import Union

from .variables import Variable

from dataclasses import dataclass, field
from enum import Enum
from math import exp, log, sqrt, sin, cos, isclose

from pyscipopt.scip import Model, SumExpr

def switch_comparator(comparator):
    if isinstance(comparator, ast.Eq): return ast.NotEq()
    if isinstance(comparator, ast.NotEq): return ast.Eq()
    if isinstance(comparator, ast.Lt): return ast.Gt()
    if isinstance(comparator, ast.LtE): return ast.GtE()
    if isinstance(comparator, ast.Gt): return ast.Lt()
    if isinstance(comparator, ast.GtE): return ast.LtE()

@dataclass
class Expressions:
    expr_str: str
    horizon: int
    expressions: list
    aux_vars: list
    
    def add_expressions(self, *expressions):
        for expression in expressions:
            self.expressions.append(expression)
    def __len__(self) -> int:
        return len(self.expressions)
    def __iter__(self):
        for expr in self.expressions:
            yield expr


class ParserType(Enum):
    """ParserType
    "enum type CALCULATOR: Used to calculate using feastol
    "enum type PARSER: Used to parse an expression and create the correct minlp constraints
    """
    CALCULATOR = "calculator"
    PARSER = "parser"


@dataclass
class EvalParams:
    variables: dict = field(default_factory={})
    functions: dict = field(default_factory={})
    operators: dict = field(default_factory={})
    parser_type: ParserType = ParserType.PARSER
    rounds_vars: bool = False
    model: Union[Model, None] = None
    add_aux_vars: bool = False
    
    @classmethod
    def as_calculator(cls, variables: dict, functions: dict, operators: dict, model: Model, add_aux_vars: bool = False):
        return EvalParams(variables, functions, operators, ParserType.CALCULATOR, False, model, add_aux_vars)
    @classmethod
    def as_parser(cls, variables: dict, functions: dict, operators: dict, model: Model, add_aux_vars: bool = False):
        return EvalParams(variables, functions, operators, ParserType.PARSER, True, model, add_aux_vars)


class ParseModel:
    
    def __init__(self, eval_params: EvalParams):
        self.params = eval_params
        self.variables = eval_params.variables
        self.functions = eval_params.functions
        
        self.model_feastol = eval_params.model.feastol()
        self.variables["feastol"] = self.model_feastol
        
        # Calculate operators (use evaluate operators for non calculations)
        feastol = self.model_feastol if eval_params.parser_type is ParserType.CALCULATOR else 0
        self.operators = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Pow: op.pow,
            
            ast.UAdd: op.pos,
            ast.USub: op.neg,
            
            ast.Not: op.not_,
            ast.Eq: lambda x, y: op.eq(x, y) if self.params.parser_type is ParserType.PARSER else isclose(x, y, rel_tol=feastol),
            # ast.Eq: op.eq,
            ast.NotEq: lambda x, y: op.ne(x, y) if self.params.parser_type is ParserType.PARSER else not isclose(x, y, rel_tol=feastol),
            # ast.NotEq: op.ne,
            ast.Lt: lambda x, y: op.lt(x, y + feastol),
            ast.LtE: lambda x, y: op.le(x, y + feastol),
            ast.Gt: lambda x, y: op.gt(x + feastol, y),
            ast.GtE: lambda x, y: op.ge(x + feastol, y),
        } | eval_params.operators
        
        self.expressions = Expressions("", -1, [], [])
            
        
    def evaluate(self, eqtn, aux_vars: Union[list, None] = None, expr_name: Union[str, None] = None, horizon: int = -1):
        
        if isinstance(eqtn, str):
            # Reset self.expressions for every new equation evaluated
            self.expressions = Expressions(
                "" if expr_name is None else expr_name, 
                horizon,
                [], 
                [] if aux_vars is None else aux_vars
            )
            
            return self.evaluate(ast.parse(eqtn))
        
        if isinstance(eqtn, ast.Module):
            self.expressions.add_expressions(*(self.evaluate(expr) for expr in eqtn.body))
            return self.expressions
        
        if isinstance(eqtn, ast.Expr):
            return self.evaluate(eqtn.value)
  
        if isinstance(eqtn, ast.BoolOp):
            # And expressions are decomposed into their individual segments and evaluated separately
            if isinstance(eqtn.op, ast.And):
                # Evaluate and add all expressions except the first to the expressions object
                self.expressions.add_expressions(*(self.evaluate(expr) for expr in eqtn.values[1:]))
                # Evaluate and return the first expression 
                return self.evaluate(eqtn.values[0])
            
            if isinstance(eqtn.op, ast.Or):
                if self.params.parser_type is ParserType.CALCULATOR:
                    results = [self.evaluate(expr) for expr in eqtn.values]
                    return any(results)
                else:
                    aux_vars = self.expressions.aux_vars
                    if self.params.add_aux_vars is True and len(aux_vars) > 0:
                        raise Exception("aux_vars should be empty to add new aux vars")
                    
                    for idx, expr in enumerate(eqtn.values):
                        if isinstance(expr, ast.Compare):
                        
                            if self.params.add_aux_vars is True:
                                aux_var = Variable.create_var(
                                    model=self.params.model, 
                                    name=f"Aux_{idx}_{self.expressions.expr_str}",
                                    vtype="auxiliary_boolean",
                                    time=self.expressions.horizon,
                                    const_vals={}
                                )
                            else:
                                aux_var: Variable = self.expressions.aux_vars[idx]
                    
                            aux_vars.append(aux_var)
                            self.variables[aux_var.name] = aux_var.model_var
                            
                            expr.left = ast.BinOp(
                                left=expr.left, 
                                op=(ast.Add() if isinstance(expr.ops[0], (ast.Gt, ast.GtE)) else ast.Sub()), 
                                right=ast.parse(f"bigM * {aux_var.name}").body[0].value
                            )
                            self.expressions.add_expressions(self.evaluate(expr))
                            
                            expr.ops[0] = switch_comparator(expr.ops[0])
                            
                            expr.comparators[0] = ast.BinOp(
                                left=expr.comparators[0], 
                                op=(ast.Add() if isinstance(expr.ops[0], (ast.Gt, ast.GtE)) else ast.Sub()), 
                                right=ast.parse(f"feastol - bigM").body[0].value
                            )
                            
                            self.expressions.add_expressions(self.evaluate(expr))
                        else:
                            raise Exception("or expressions may only be made up of inequalities")
                    lhs = SumExpr()
                    for var in aux_vars:
                        lhs += var.model_var
                    return lhs <= len(aux_vars) - 1
                    
        if isinstance(eqtn, ast.IfExp):
            raise Exception("Can't use if else")
            
        if isinstance(eqtn, ast.Compare):
            if len(eqtn.comparators) != 1:
                raise Exception("Too many comparator operators, please don't use more than 1 per equation")
            
            left = self.evaluate(eqtn.left)
            right = self.evaluate(eqtn.comparators[0])
            comp_type = type(eqtn.ops[0])
            comparator = self.operators[comp_type]
            
            return comparator(left, right)
            
        if isinstance(eqtn, ast.Name):
            return self.variables[eqtn.id]
        
        if isinstance(eqtn, ast.BinOp):
            left = self.evaluate(eqtn.left)
            right = self.evaluate(eqtn.right)
            operator = type(eqtn.op)
            return self.operators[operator](left, right)
        
        if isinstance(eqtn, ast.Call):
            if not isinstance(eqtn.func, ast.Name):
                raise Exception("Attributes such as main.secondary() functions are not allowed")
            
            func_name = eqtn.func.id
            args = (self.evaluate(arg) for arg in eqtn.args)
            func = self.functions[func_name]
            return func(*args)
        
        if isinstance(eqtn, ast.Constant):
            return eqtn.value
        
        if isinstance(eqtn, ast.UnaryOp):
            op_type = type(eqtn.op)
            operator = self.operators[op_type]
            return operator(self.evaluate(eqtn.operand))
        
        raise Exception("Unknown ast type")



if __name__ == "__main__":
    # params = EvalParams.as_calculator(variables, functions, {})
    # calc = ParseModel(params).evaluate
    
    # print(calc(constraint))
    eqtns = """
1 + 2
1 + 5 < 5    
"""
    print((eqtns))
#     print(calc(
# """
# a >= b if a + b + c >= 5 else a - b - c == 10
# """))
#     print(calc(
# """
# a + b + c >= 5 or a - b - c == 10
# """))