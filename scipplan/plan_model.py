from .config import Config
from .variables import Variable, VarType
from .parse_model import ParseModel as PM, EvalParams
from .helpers import list_accessible_files

import math
import os
import re

from pyscipopt.scip import Model
from pkg_resources import parse_version
from importlib.metadata import version
from sympy import Eq, Function, Derivative as dd, Symbol, parse_expr
from sympy.solvers.ode.systems import dsolve_system


if parse_version(version("pyscipopt")) >= parse_version("4.3.0"):
    from pyscipopt import quicksum, exp, log, sqrt, sin, cos
    allow_trig_funcs = True
else:
    from pyscipopt import quicksum, exp, log, sqrt 
    allow_trig_funcs = False

class PlanModel:
    def __init__(self, config: Config) -> None:
        self.config: Config = config
        self.var_names: set[str] = set()
        
        self.model = Model(f"{config.domain}_{config.instance}_{config.horizon}")
        
        # Translation -> line_num -> horizon -> aux
        self.aux_vars: dict[str, list[list[list]]] = {}
        
        self.file_translations = self.read_translations()

        self.constants = self.encode_constants()
        self.variables = self.encode_pvariables()
        self.translations = self.encode_constraints()
        
        self.rewards = self.encode_reward()
        
        # Encode bounds on Dt
        for h in range(self.config.horizon):
            dt_var = self.variables[(self.config.dt_var, h)].model_var
            self.model.addCons(dt_var >= 0.0, f"dt_{h}_lower_bound")
            self.model.addCons(dt_var <= self.config.bigM, f"dt_{h}_upper_bound")   
    
    def read_translations(self) -> dict[str, list[str]]:
        with open(self.get_file_path("solutions" if self.config.provide_sols else "odes")) as f:
            translations = {}
            new_sec = True
            for line in f:
                line = line.strip()
                if line == "":
                    pass
                elif line == "---":
                    new_sec = True
                elif new_sec is True:
                    translation = line.removesuffix(":")
                    translations[translation] = []
                    new_sec = False
                else:
                    translations[translation].append(line)
        
        return translations



    def encode_constants(self) -> dict[str, float]:
        constants = {}
        translation = "constants"
        config_vals = {
            # Since horizon can be incremented without this value being updated, it will be removed for the time being
            # "config_horizon": self.config.horizon,
            "config_epsilon": self.config.epsilon,
            "config_gap": self.config.gap,
            "config_bigM": self.config.bigM
        }
    
            
        for line in self.file_translations[translation]:

            var, val = line.split("=")
            var, val = var.strip(), val.strip()
            
            val = val if val not in config_vals else config_vals[val]
            
            try:
                val = float(val)
            except ValueError:
                raise ValueError("Constants can only be floats, please reconfigure: ")
            
            constants[var] = val
            self.var_names.add(var)
                
        constants["bigM"] = self.config.bigM
        self.var_names.add("bigM")
        return constants
                
        
    def encode_pvariables(self) -> dict[tuple[str, int], Variable]:
        variables: dict[tuple[str, int], Variable] = {}
        for t in range(self.config.horizon):
            for constant, val in self.constants.items():
                variables[(constant, t)] = Variable.create_var(self.model, constant, "constant", t, self.constants)
                var_type = variables[(constant, t)].var_type
                
        translation = "pvariables"
        for line in self.file_translations[translation]:
            
            var = line.rstrip("\n").strip()
            if var == "":
                continue
            vtype, name = var.split(": ")
            vtype, name = vtype.strip(), name.strip()
            
            self.var_names.add(name)
            
            if vtype.startswith("global"):
                var = Variable.create_var(self.model, name, vtype, "global", self.constants)
                for t in range(self.config.horizon + 1):
                    variables[(name, t)] = var
            else:
                for t in range(self.config.horizon):
                    variables[(name, t)] = Variable.create_var(self.model, name, vtype, t, self.constants)
                    var_type = variables[(name, t)].var_type
                if var_type is VarType.STATE:
                    variables[(name, self.config.horizon)] = Variable.create_var(self.model, name, vtype, self.config.horizon, self.constants)

        return variables
                
         
         
    def encode_constraints(self) -> dict[str, list[str]]:
        translation_names = [
            "initials",
            "instantaneous_constraints",
            "temporal_constraints",
            "goals",
            "odes" if self.config.provide_sols is False else "transitions"
        ]
        translations: dict[str, list[str]] = {}
        for translation in translation_names:
            translations[translation] = []
            
            for line in self.file_translations[translation]:
                expr = line.rstrip("\n").strip()
                # If line is empty don't append
                if expr == "":
                    continue
                
                translations[translation].append(expr)

        if self.config.provide_sols is False: 
            self.ode_functions = self.solve_odes(translations["odes"])

            translations["transitions"] = []
            for func_name, func in self.ode_functions.items():
                translations["transitions"].append((func_name + "_dash" + " == " + func))
            
            del translations["odes"]
            

        # Encode constraints into model
        for cons_idx, (translation, constraints) in enumerate(translations.items()):
            for idx, constraint in enumerate(constraints):
                if (self.config.provide_sols is False) and (translation == "temporal_constraints"):
                    pattern = r"|".join(f"({func_name})" for func_name, func in self.ode_functions.items())
                    constraint = re.sub(pattern, lambda x: self.ode_functions[x.group(0)], constraint)
                    constraints[idx] = constraint
                    
                if translation == "initials":
                    exprs = PM(self.get_parser_params(horizon=0, add_aux_vars=True)).evaluate(constraint, horizon=0, expr_name=f"{translation}_{idx}_0")
                    
                    if self.aux_vars.get(translation) is None: self.aux_vars[translation] = [None] * len(constraints)
                    if self.aux_vars[translation][idx] is None: self.aux_vars[translation][idx] = [None] * self.config.horizon
                    self.aux_vars[translation][idx][0] = exprs.aux_vars

                    for eqtn_idx, eqtn in enumerate(exprs):
                        self.model.addCons(eqtn, f"{translation}_{idx}_{eqtn_idx}")
                        
                elif translation == "goals":
                    # horizon - 1 is because the final action time is horizon - 1
                    exprs = PM(self.get_parser_params(horizon=self.config.horizon - 1, is_goal=True, add_aux_vars=True)).evaluate(constraint, horizon=self.config.horizon - 1, expr_name=f"{translation}_{idx}_{self.config.horizon - 1}")
                    
                    if self.aux_vars.get(translation) is None: self.aux_vars[translation] = [None] * len(constraints)
                    if self.aux_vars[translation][idx] is None: self.aux_vars[translation][idx] = [None] * self.config.horizon
                    self.aux_vars[translation][idx][self.config.horizon - 1] = exprs.aux_vars
                    
                    for eqtn_idx, eqtn in enumerate(exprs):
                        self.model.addCons(eqtn, f"{translation}_{idx}_{eqtn_idx}")
                else:
                    for t in range(self.config.horizon):
                        exprs = PM(self.get_parser_params(horizon=t, add_aux_vars=True)).evaluate(constraint, horizon=t, expr_name=f"{translation}_{idx}_{t}")
                        
                        if self.aux_vars.get(translation) is None: self.aux_vars[translation] = [None] * len(constraints)
                        if self.aux_vars[translation][idx] is None: self.aux_vars[translation][idx] = [None] * self.config.horizon
                        self.aux_vars[translation][idx][t] = exprs.aux_vars
                        
                        for eqtn_idx, eqtn in enumerate(exprs):
                            self.model.addCons(eqtn, f"{translation}_{idx}_{eqtn_idx}")
                    
        return translations
    
    def encode_reward(self):
        objectives = [None] * self.config.horizon
        translation = "reward"
        reward = self.file_translations[translation][0]
        for t in range(self.config.horizon):
            objectives[t] = self.model.addVar(f"Obj_{t}", vtype="C", lb=None, ub=None)
            # For the sake of similarity the reward is similar to constraint parsing, however, only one reward function is allowed
            exprs = PM(self.get_parser_params(t)).evaluate(reward)
            for expr_idx, expr in enumerate(exprs):
                self.model.addCons(objectives[t] == expr, f"Obj_{t}_{expr_idx}")
            
        self.model.setObjective(quicksum(objectives), "maximize")
            
        return objectives
            
            

    def get_parser_params(self, horizon: int, is_goal: bool = False, add_aux_vars: bool = False) -> EvalParams:
        functions = {
            "exp": exp, 
            "log": log, 
            "sqrt": sqrt, 
        }
        if allow_trig_funcs:
            functions["sin"] = sin 
            functions["cos"] = cos 
            
        variables = {}
        operators = {}
        if is_goal:
            for name in self.var_names:
                var = self.variables[(name, horizon)]
                if var.var_type is VarType.STATE:
                    var = self.variables[(name, horizon + 1)]
                variables[var.name] = var.model_var
        else:
            for name in self.var_names:
                var = self.variables[(name, horizon)]
                variables[var.name] = var.model_var
                if var.var_type is VarType.STATE:
                    var = self.variables[(name, horizon + 1)]
                    variables[f"{var.name}_dash"] = var.model_var
            
        return EvalParams.as_parser(variables, functions, operators, self.model, add_aux_vars)
    

    def get_calc_params(self, horizon, dt) -> EvalParams:
        functions = {
            "exp": math.exp, 
            "log": math.log, 
            "sqrt": math.sqrt, 
        }
        if allow_trig_funcs:
            functions["sin"] = math.sin 
            functions["cos"] = math.cos
        
        variables = {}
        operators = {}
        for name in self.var_names:
            var = self.variables[(name, horizon)]
            if var.var_type is VarType.CONSTANT:
                variables[var.name] = var.model_var
            else:
                variables[var.name] = self.model.getVal(var.model_var)
                
                if var.var_type is VarType.STATE:
                    var = self.variables[(name, horizon + 1)]
                    variables[f"{var.name}_dash"] = self.model.getVal(var.model_var)
        
        variables[self.config.dt_var] = dt
        
        
        return EvalParams.as_calculator(variables, functions, operators, self.model)
    
    
    def get_file_path(self, translation: str) -> str:
        path = f"{translation}_{self.config.domain}_{self.config.instance}.txt"
        
        usr_files_path = os.path.join("./", "translation")
        usr_files = list_accessible_files(usr_files_path)
        
        pkg_files_path = os.path.join(os.path.dirname(__file__), "translation")
        pkg_files = list_accessible_files(pkg_files_path)
        
        
        if path in usr_files:
            return os.path.join(usr_files_path, path)
        elif path in pkg_files:
            return os.path.join(pkg_files_path, path)
        else:
            raise Exception("Unkown file name, please enter a configuration for a valid domain instance in translation: ")
        

    def solve_odes(self, ode_system: list[str]) -> dict[str, str]:
        dt_var = self.config.dt_var

        dt = Symbol(dt_var)
        # Used to represent constant variables
        temp_var = Symbol("ODES_TEMP_VAR")

        variables = {}
        states = []

        for var_name in self.var_names:
            var = self.variables[(var_name, 0)]
            if var.var_type is VarType.STATE:
                states.append(var.name)
                variables[var.name] = Function(var.name)(dt)
            elif var.var_type is VarType.CONSTANT:
                variables[var.name] = self.constants[var.name]
            else: # the variable is an action or aux variable which is encoded as a function of some unused variable as workaround to not being able to use symbols for constants
                variables[var.name] = Function(var.name)(temp_var)
        
        variables[dt_var] = dt
        
        system = []
        for eqtn in ode_system:
            lhs, rhs = eqtn.split("==")
            lhs = parse_expr(lhs.strip(), local_dict=variables | {"dd": dd})
            rhs = parse_expr(rhs.strip(), local_dict=variables | {"dd": dd})
            system.append(Eq(lhs, rhs))
        results = dsolve_system(system, ics={variables[state].subs(dt, 0): state for state in states})



        functions: dict[str, str] = {}
        for eqtn in results[0]:
            new_eqtn = eqtn.doit()
            func_name = new_eqtn.lhs.name.replace(f"({temp_var.name})", "").replace(f"({self.config.dt_var})", "_dash")
            functions[func_name] = str(new_eqtn.rhs).replace(f"({temp_var.name})", "").replace(f"({self.config.dt_var})", "_dash")
        
        
        return functions


