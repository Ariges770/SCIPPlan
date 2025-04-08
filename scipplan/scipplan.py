from __future__ import annotations

import time

from .config import Config
from .plan_model import PlanModel
from .variables import VarType
from .zero_crossing import ZeroCrossing
from .parse_model import ParseModel as PM
from .helpers import InfeasibilityError, iterate, write_to_csv

from importlib.metadata import version
from pyscipopt.scip import Model

class SCIPPlan:
    """
    SCIPPlan is a planner which optimises mixed integer non-linear programming problems over hybrid domains
    
    In order to use SCIPPlan you must pass in as input a Config object which contains the configuration of the problem.
    Then you may either use the optimize or solve methods.
    
    The optimize method attempts to optimise the problem for the provided horizon. 
    If there are no feasible solutions, then the optimize method will raise InfeasibilityError.
    
    The solve method attempts to solve the problem starting with the provided horizon.
    If there are no feasible solutions for the current horizon then the configs horizon will be incremented.
    After which the solve method will attempt to optimize the problem again.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.plan = PlanModel(self.config)
        self.scip_model = self.plan.model
        
        self.scip_model.setRealParam("limits/gap", self.config.gap)
        
        if config.show_output is False:
            self.scip_model.hideOutput()
        
        self.results_table = []
        self.new_constraints = []
        
        self.state_actions = []
               

    def optimize(self):
        iteration = 0
        
        const_gen_aux_vars = [[None] * self.config.horizon for _ in range(len(self.plan.translations["temporal_constraints"]))]

        while True:
            self.scip_model.optimize()
            
            if len(self.scip_model.getSols()) == 0:
                raise InfeasibilityError

            zero_cross = self.check_violated_constraints(iteration)
                
            self.save_values(iteration)
            
            if zero_cross.is_violated is False:
                return None
            
            self.new_constraints.append({
                "interval_start": zero_cross.start,
                "interval_end": zero_cross.end,
                "dt_interval": zero_cross.dt_interval,
                "zero_crossing_coefficient": zero_cross.coef,
                "new_dt_val": zero_cross.new_dt_val,
                "horizon": zero_cross.horizon,
                "iteration": zero_cross.iteration
            })
            
            if self.config.show_output is True:
                print("\n\n")
                print("New Constraints: \n")
                for new_constraint in self.new_constraints:
                    print(new_constraint, end="\n\n")
                print("\n\n")
            
            self.scip_model.freeTransform()
            
            for idx, constraint in enumerate(self.plan.translations["temporal_constraints"]):
                t = zero_cross.horizon
                # aux_vars = self.plan.aux_vars["temporal_constraints"][idx][t]
                aux_vars = const_gen_aux_vars[idx][t]
                # Only add aux vars if there are no aux vars added for the secific constraint
                params = self.plan.get_parser_params(horizon=t, add_aux_vars=aux_vars is None)
                params.variables[self.config.dt_var] *= zero_cross.coef
                exprs = PM(params).evaluate(constraint, aux_vars=aux_vars)
                if const_gen_aux_vars[idx][t] is None:
                    const_gen_aux_vars[idx][t] = exprs.aux_vars
                    
                for eqtn_idx, eqtn in enumerate(exprs):
                    self.plan.model.addCons(eqtn, f"{constraint}_{idx}_{eqtn_idx}")
            
            iteration += 1

    
    def check_violated_constraints(self, iteration: int) -> ZeroCrossing:
        is_violated = False
        cross_interval = [-1.0 * self.config.epsilon, -1.0 * self.config.epsilon]
        
        for h in range(self.config.horizon):
            dt = self.scip_model.getVal(self.plan.variables[(self.config.dt_var, h)].model_var)
            
            for constraint in self.plan.translations["temporal_constraints"]:
                is_violated = False
                
                for time in iterate(0, dt, self.config.epsilon):
                    pm = PM(self.plan.get_calc_params(horizon=h, dt=time))
                    exprs = pm.evaluate(constraint)
                    
                    for eqtn_idx, constraint_eval in enumerate(exprs):
                        if constraint_eval is False:
                            if not is_violated:
                                # Set interval start when first part of zero crossing is found
                                is_violated = True
                                cross_interval[0] = time
                            
                            # Keep updating end point until end of zero crossing or end of dt interval
                            cross_interval[1] = time
                        
                if is_violated and (constraint_eval is True or time + self.config.epsilon > dt):
                    return ZeroCrossing(
                        is_violated=True,
                        horizon=h,
                        iteration=iteration,
                        start=cross_interval[0],
                        end=cross_interval[1],
                        dt_interval=dt,
                    )
        
        return ZeroCrossing(is_violated=False)
        
    
     
    @classmethod
    def solve(cls, config: Config) -> tuple[SCIPPlan, float]:
        # Time total solve time including incrementing horizon
        start_time = time.time()
        while True:
            model = SCIPPlan(config)
            try:
                print(f"Encoding the problem over horizon h={config.horizon}.")
                print("Solving the problem.")
                model.optimize()
                                
                solve_time = (time.time() - start_time)
                # print(f"Total Time: {solve_time: .3f} seconds")
                print("Problem solved. \n")
                return model, solve_time 
                    
            
            except InfeasibilityError:    
                if config.get_defaults().get("horizon") is False:
                    print(f"Horizon of h={model.config.horizon} is infeasible.")

                    solve_time = (time.time() - start_time)
                    print(f"Total time: {solve_time:.3f}")

                    raise InfeasibilityError
                    
                
                # print("Problem is infeasible for the given horizon.")
                print(f"Horizon of h={model.config.horizon} is infeasible, incrementing to h={model.config.horizon + 1}.")
                config.increment_horizon()
                if config.show_output is True:
                    print(f"Horizon Time: {(time.time() - start_time): .3f} seconds.")
        

    def save_values(self, iteration: int):
        for (name, h), var in self.plan.variables.items():
            self.results_table.append(var.to_dict() | {"iteration": iteration})           
    

def main():    
    print(f"SCIP Version: {Model().version()}")
    print(f"PySCIPOpt Version: {version('pyscipopt')}\n")
    config = Config.get_config()
    print(config)
    
    try:
        plan, solve_time = SCIPPlan.solve(config)  
    except InfeasibilityError:
        return None
    
    if config.save_sols is True:
        write_to_csv("new_constraints", plan.new_constraints, config)
        write_to_csv("results", plan.results_table, config)
        print("Solutions saved: \n")
        
        
    print("Plan: ")
    
    # Get action variable names
    action_names = [
        var_name for var_name in plan.plan.var_names 
        if plan.plan.variables[(var_name, 0)].var_type is VarType.ACTION
        ]
    
    action_names = sorted(action_names)
    
    for step in range(plan.config.horizon):
        for action_name in action_names:
            if action_name == config.dt_var:
                continue
            print(f"{action_name} at step {step} by value {plan.scip_model.getVal(plan.plan.variables[(action_name, step)].model_var):.3f}.")
        
        print(f"Dt at step {step} by value {plan.scip_model.getVal(plan.plan.variables[('Dt', step)].model_var):.3f}. \n")
    
    print(f"Total reward: {(plan.scip_model.getObjVal()):.3f}")
    print(f"Total time: {solve_time:.3f}")

if __name__ == "__main__":
    main()