from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union

from pyscipopt.scip import Model, Variable as SCIPVariable

@dataclass
class Variable:
    name: str
    var_type: VarType
    val_type: ValType
    time: int
    model: Model
    model_var: Union[SCIPVariable | float]
    
    @classmethod
    def create_var(cls, model: Model, name: str, vtype: str, time: int, const_vals: dict[str, float]) -> Variable:
        
        if "action" in vtype:
            var_type = VarType.ACTION
        elif "state" in vtype:
            var_type = VarType.STATE
        elif "auxiliary" in vtype:
            var_type = VarType.AUX
        elif "constant" in vtype:
            var_type = VarType.CONSTANT
        else: # var type isn't recognised
            raise Exception("Unknown variable type: ")
        
        if "continuous" in vtype:
            val_type = ValType.CONTINUOUS
        elif "integer" in vtype:
            val_type = ValType.INTEGER
        elif "boolean" in vtype:
            val_type = ValType.BOOLEAN
        elif var_type is VarType.CONSTANT:
            # Special case for constants as the value type doesn't matter for the model as it is numeric
            val_type = None
        else: # val type isn't recognised
            raise Exception("Unkown value type: ")
        
        if var_type is VarType.CONSTANT:
            model_var = const_vals[name]
        else:
            model_var = model.addVar(name=f"{name}_{time}", vtype=val_type.value, lb=None, ub=None)
        
        var = Variable(
            name=name,
            var_type=var_type,
            val_type=val_type,
            time=time,
            model=model,
            model_var=model_var
        )
        
        return var
    
    def to_dict(self):
        if self.var_type is VarType.CONSTANT:
            var_val = self.model_var
            val_type = None
        else:
            val_type = self.val_type.name
            try:
                var_val = self.model.getVal(self.model_var)
            except Warning:
                var_val = None
        
             
        return {
            "name": self.name,
            "variable_type": self.var_type.name,
            "value_type": val_type,
            "horizon": self.time,
            "variable_value": var_val
        }



class VarType(Enum):
    ACTION = "action"
    STATE = "state"
    AUX = "auxiliary"
    CONSTANT = "constant"

class ValType(Enum):
    CONTINUOUS = "C"
    INTEGER = "I"
    BOOLEAN = "B"
