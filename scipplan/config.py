from __future__ import annotations

from dataclasses import dataclass, field
from textwrap import dedent
import argparse

@dataclass
class Config:
    """
    The Config class provides an interface to set the configuration for SCIPPlan. 
    Config can be set by creating an instance of the class adding the variables desired. 
    Alternatively, the `get_config` class method will return a config instance using variables set by the programs args (e.g. -D 'domain').
    """
    domain: str
    instance: str
    horizon: int = field(default=None)
    epsilon: float = field(default=None)
    gap: float = field(default=None)
    provide_sols: bool = field(default=False)
    show_output: bool = False
    save_sols: bool = False
    bigM: float = 1000.0
    dt_var: str = "Dt"
    _defaults: dict[str, bool] = field(default_factory=dict, repr=False)
    
    def __post_init__(self) -> None:
        # Set all defaults to False and if the value is None then it will be updated to true
        self._defaults = {
            "domain": False,
            "instance": False,
            "horizon": False,
            "epsilon": False,
            "gap": False
        }
        if self.horizon is None:
            print("Horizon is not provided, and is set to 1. ")
            self.horizon = 1
            self._defaults["horizon"] = True
            
        if self.epsilon is None:
            print("Epsilon is not provided, and is set to 0.1. ")
            self.epsilon = 0.1
            self._defaults["epsilon"] = True
            
        if self.gap is None:
            print("Gap is not provided, and is set to 10.0%. ")
            self.gap = 0.1
            self._defaults["gap"] = True
            
    def __str__(self) -> str:
        text = f"""
        Configuration:
        
        Use System of ODE's: {not self.provide_sols}
        Display SCIP Output: {self.show_output}
        Save Solutions: {self.show_output}
        Dt Variable Name: {self.dt_var}
        
        Domain (str): {self.domain}
        Instance (str): {self.instance}
        Horizon (int): {self.horizon} {'(default)' if self._defaults['horizon'] is True else ''}
        Epsilon (float): {self.epsilon} {'(default)' if self._defaults['epsilon'] is True else ''}
        Gap (float): {self.gap * 100}% {'(default)' if self._defaults['gap'] is True else ''}
        BigM (float): {self.bigM}
        """
        return dedent(text)
    
    def increment_horizon(self, value: int = 1):
        # self._defaults["horizon"] = False
        self.horizon += value
        
    def get_defaults(self) -> dict[str, bool]:
        return self._defaults
    
    @classmethod
    def get_config(cls) -> Config:
        parser = argparse.ArgumentParser(
            prog="SCIPPlan"
        )
        parser.add_argument(
            "-D", 
            "--domain", 
            required=True,
            type=str,
            help="This variable is the name of the domain (e.g. pandemic or navigation)."
        )
        parser.add_argument(
            "-I", 
            "--instance", 
            required=True,
            type=str,
            help="This is the instance number of the domain (e.g. navigation has instances 1, 2 and 3)."
        )
        parser.add_argument(
            "-H", 
            "--horizon", 
            required=False,
            # default=1,
            type=int,
            help="The initial horizon. The solve method will initially begin with this horizon until it finds a feasible solution."
        )
        parser.add_argument(
            "-E", 
            "--epsilon", 
            required=False,
            # default=0.1,
            type=float,
            help="SCIPPlan iteratively checks solution for violations at each epsilon value."
        )
        parser.add_argument(
            "-G", 
            "--gap", 
            required=False,
            # default=0.1,
            type=float,
            help="SCIP will search for solution with an optimality gap by at least this value."
        )
        
        parser.add_argument(
            "--bigM", 
            required=False,
            default=1000.0,
            type=float,
            help="A large value which is used for some constraint encoding formulations, defaults to 1000.0 and can be changed as needed."
        )
        
        parser.add_argument(
            "--dt-var", 
            required=False,
            default="Dt",
            type=str,
            help="When writing the constraints, dt_var is the variable name for Dt, defaults to 'Dt' and can be changed based on users preference (e.g. 'dt')."
        )
        
        parser.add_argument(
            "--provide-sols", 
            action="store_true", 
            default=False, 
            help="This flag determines whether the user would like to provide a system of odes or solution equations, odes must be provided by default."
        )

        parser.add_argument(
            "--show-output", 
            action="store_true", 
            default=False, 
            help="Include this flag to show output from SCIP."
        )
        
        parser.add_argument(
            "--save-sols", 
            action="store_true", 
            default=False, 
            help="Include this flag to save the solutions from each of the scipplan iterations as well as constraints generated (note, only saves for horizon which has been solved)."
        )
        
        args = parser.parse_args()
        
        return Config(**vars(args))
    
    
if __name__ == "__main__":
    
    print(Config.get_config())