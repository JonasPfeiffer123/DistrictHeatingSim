"""
Filename: heat_generator_mix.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: 

"""

import numpy as np
import copy

from scipy.optimize import minimize
from pyomo.environ import ConcreteModel, Var, Objective, ConstraintList, SolverFactory, NonNegativeIntegers

class EnergySystem:
    def __init__(self, time_steps, load_profile, VLT_L, RLT_L, TRY_data, COP_data, economic_parameters):
        """
        Initialize the energy system with relevant data.

        Args:
            time_steps (np.ndarray): Time steps for the simulation.
            load_profile (np.ndarray): Heat demand profile.
            VLT_L (np.ndarray): Supply temperature profile.
            RLT_L (np.ndarray): Return temperature profile.
            TRY_data (object): Test Reference Year data.
            COP_data (object): Coefficient of Performance data.
            economic_parameters (dict): Economic parameters for the system.
        """
        self.time_steps = time_steps
        self.load_profile = load_profile
        self.VLT_L = VLT_L
        self.RLT_L = RLT_L
        self.TRY_data = TRY_data
        self.COP_data = COP_data
        self.economic_parameters = economic_parameters
        self.technologies = []  # List to store generator objects
        self.results = {}

    def add_technology(self, tech):
        """
        Add a technology to the energy system.

        Args:
            tech (object): Technology object to add.
        """
        self.technologies.append(tech)

    def calculate_mix(self, variables=[], variables_order=[]):
        """
        Calculate the energy generation mix for the given technologies.

        Args:
            variables (list): Variables for optimization.
            variables_order (list): Order of variables for optimization.

        Returns:
            dict: Results of the energy system simulation.
        """
        duration = np.diff(self.time_steps[:2]) / np.timedelta64(1, 'h')
        duration = duration[0]

        general_results = {
            'time_steps': self.time_steps,
            'Last_L': self.load_profile,
            'VLT_L': self.VLT_L,
            'RLT_L': self.RLT_L,
            'Jahreswärmebedarf': (np.sum(self.load_profile) / 1000) * duration,
            'WGK_Gesamt': 0,
            'Restwärmebedarf': (np.sum(self.load_profile) / 1000) * duration,
            'Restlast_L': self.load_profile.copy(),
            'Wärmeleistung_L': [],
            'colors': [],
            'Wärmemengen': [],
            'Anteile': [],
            'WGK': [],
            'Strombedarf': 0,
            'Strommenge': 0,
            'el_Leistungsbedarf_L': np.zeros_like(self.load_profile),
            'el_Leistung_L': np.zeros_like(self.load_profile),
            'el_Leistung_ges_L': np.zeros_like(self.load_profile),
            'specific_emissions_L': [],
            'primärenergie_L': [],
            'specific_emissions_Gesamt': 0,
            'primärenergiefaktor_Gesamt': 0,
            'techs': [],
            'tech_classes': []
        }

        for tech in self.technologies.copy():
            # Set variables for optimization
            if len(variables) > 0:
                idx = tech.name.split("_")[-1]
                tech.set_parameters(variables, variables_order, idx)

            # Perform technology-specific calculation
            tech_results = tech.calculate(economic_parameters=self.economic_parameters,
                                        duration=duration,
                                        general_results=general_results,
                                        VLT_L=self.VLT_L,
                                        RLT_L=self.RLT_L,
                                        TRY_data=self.TRY_data,
                                        COP_data=self.COP_data,
                                        time_steps=self.time_steps)

            # Check if heat is generated, 0 values and very small values are not allowed
            if tech_results['Wärmemenge'] > 1e-6:
                general_results['Wärmeleistung_L'].append(tech_results['Wärmeleistung_L'])
                general_results['Wärmemengen'].append(tech_results['Wärmemenge'])
                general_results['Anteile'].append(tech_results['Wärmemenge']/general_results['Jahreswärmebedarf'])
                general_results['WGK'].append(tech_results['WGK'])
                general_results['specific_emissions_L'].append(tech_results['spec_co2_total'])
                general_results['primärenergie_L'].append(tech_results['primärenergie'])
                general_results['colors'].append(tech_results['color'])
                general_results['Restlast_L'] -= tech_results['Wärmeleistung_L']
                general_results['Restwärmebedarf'] -= tech_results['Wärmemenge']
                general_results['WGK_Gesamt'] += (tech_results['Wärmemenge']*tech_results['WGK'])/general_results['Jahreswärmebedarf']
                general_results['specific_emissions_Gesamt'] += (tech_results['Wärmemenge']*tech_results['spec_co2_total'])/general_results['Jahreswärmebedarf']
                general_results['primärenergiefaktor_Gesamt'] += tech_results['primärenergie']/general_results['Jahreswärmebedarf']

                if tech.name.startswith("BHKW") or tech.name.startswith("Holzgas-BHKW"):
                    general_results['Strommenge'] += tech_results["Strommenge"]
                    general_results['el_Leistung_L'] += tech_results["el_Leistung_L"]
                    general_results['el_Leistung_ges_L'] += tech_results["el_Leistung_L"]

                if tech.name.startswith("Abwärme") or tech.name.startswith("Abwasserwärme") or tech.name.startswith("Flusswasser") or tech.name.startswith("Geothermie"):
                    general_results['Strombedarf'] += tech_results["Strombedarf"]
                    general_results['el_Leistungsbedarf_L'] += tech_results["el_Leistung_L"]
                    general_results['el_Leistung_ges_L'] -= tech_results['el_Leistung_L']

                if "Wärmeleistung_Speicher_L" in tech_results.keys():
                    general_results['Restlast_L'] -= tech_results['Wärmeleistung_Speicher_L']

            else:
                # Remove technology if no heat is generated
                self.technologies.remove(tech)
                print(f"{tech.name} wurde durch die Optimierung entfernt.")

                # Remove variables from mapping
                #variables_mapping = {var: tech.name for tech in self.technologies for var in tech.add_optimization_parameters(0)[1]}
                #variables_order = list(variables_mapping.keys())
                #print(f"Updated variables_order: {variables_order}")

        for tech in self.technologies:
            general_results['techs'].append(tech.name)
            general_results['tech_classes'].append(tech)

        self.results = general_results
        return general_results
    
    def copy(self):
        """
        Create a deep copy of the EnergySystem instance.

        Returns:
            EnergySystem: A new instance of EnergySystem with the same data.
        """
        copied_system = EnergySystem(
            time_steps=self.time_steps.copy(),
            load_profile=self.load_profile.copy(),
            VLT_L=self.VLT_L.copy(),
            RLT_L=self.RLT_L.copy(),
            TRY_data=self.TRY_data,
            COP_data=self.COP_data,
            economic_parameters=copy.deepcopy(self.economic_parameters)
        )
        # Deep-copy the technologies
        copied_system.technologies = [copy.deepcopy(tech) for tech in self.technologies]
        return copied_system

    def optimize_mix(self, weights):
        """
        Optimize the energy generation mix for minimal cost, emissions, and primary energy use.

        Args:
            weights (dict): Weights for optimization criteria.

        Returns:
            list: Optimized list of technology objects with updated parameters.
        """
        optimizer = EnergySystemOptimizer(self, weights)
        self.optimized_energy_system = optimizer.optimize()
        return self.optimized_energy_system

class EnergySystemOptimizer:
    def __init__(self, initial_energy_system, weights, num_restarts=5):
        """
        Initialize the optimizer for the energy system with support for multiple random restarts.

        Args:
            initial_energy_system (object): Initial energy system object.
            weights (dict): Weights for optimization criteria.
            num_restarts (int): Number of random restarts for optimization. Default is 5.
        """
        self.initial_energy_system = initial_energy_system
        self.weights = weights
        self.num_restarts = num_restarts

    def optimize(self):
        """
        Perform optimization of the energy system with multiple random restarts.

        Returns:
            object: Optimized energy system object.
        """
        best_solution = None
        best_objective_value = float('inf')

        for restart in range(self.num_restarts):
            print(f"Starting optimization run {restart + 1}/{self.num_restarts}")

            # Copy the energy system for this run
            self.energy_system_copy = self.initial_energy_system.copy()

            initial_values = []
            bounds = []
            variables_mapping = {}  # Mapping für Variablen

            for tech in self.energy_system_copy.technologies:
                # idx is index in the name of the technology
                idx = tech.name.split("_")[-1]
                tech_values, tech_variables, tech_bounds = tech.add_optimization_parameters(idx)
                
                # Skip technologies without optimization parameters
                if not tech_values and not tech_variables and not tech_bounds:
                    continue

                initial_values.extend(tech_values)
                bounds.extend(tech_bounds)

                # Map variables to technology name and parameter
                for var in tech_variables:
                    variables_mapping[var] = tech.name
            
            variables_order = list(variables_mapping.keys())
            print(f"Variables mapping: {variables_mapping}")
            print(f"Optimization variables: {variables_order}")

            if not initial_values:
                print("Keine Optimierungsparameter vorhanden. Optimierung wird übersprungen.")
                return self.energy_system_copy.technologies

            # Generate random initial values within the bounds
            random_initial_values = [
                np.random.uniform(low=bound[0], high=bound[1]) if bound[0] < bound[1] else bound[0]
                for bound in bounds
            ]

            def objective(variables):
                # Calculate the mix for the copied system
                self.energy_system_copy.calculate_mix(variables, variables_order)
                results = self.energy_system_copy.results
                
                # Calculate the weighted sum
                weighted_sum = (
                    self.weights['WGK_Gesamt'] * results['WGK_Gesamt'] +
                    self.weights['specific_emissions_Gesamt'] * results['specific_emissions_Gesamt'] +
                    self.weights['primärenergiefaktor_Gesamt'] * results['primärenergiefaktor_Gesamt']
                )
                return weighted_sum

            # Perform the optimization
            result = minimize(objective, random_initial_values, method='SLSQP', bounds=bounds)

            # Check if the current run has a better solution
            if result.success and result.fun < best_objective_value:
                best_objective_value = result.fun
                best_solution = result
                best_system_copy = self.energy_system_copy.copy()

        # If a valid solution was found, apply the best solution
        if best_solution:
            for tech in best_system_copy.technologies:
                idx = tech.name.split("_")[-1]
                tech.update_parameters(best_solution.x, variables_order, idx)
            print("Optimierung erfolgreich")
            return best_system_copy
        else:
            print("Keine gültige Lösung gefunden.")
            return self.initial_energy_system

"""
class EnergySystemOptimizer:
    def __init__(self, initial_energy_system, weights):
        
        Initialize the optimizer for the energy system using pyomo.

        Args:
            initial_energy_system (object): Initial energy system object.
            weights (dict): Weights for optimization criteria.
        
        self.initial_energy_system = initial_energy_system
        self.weights = weights

    def optimize(self):
        
        Perform optimization of the energy system with integer constraints using pyomo.

        Returns:
            object: Optimized energy system object.
        
        # Copy the energy system
        self.energy_system_copy = self.initial_energy_system.copy()

        # Initialize the pyomo model
        model = ConcreteModel()

        # Collect optimization parameters
        tech_indices = []
        tech_bounds = []
        tech_variables = []
        initial_values = []

        for idx, tech in enumerate(self.energy_system_copy.technologies):
            tech_values, tech_vars, tech_bnds = tech.add_optimization_parameters(idx)
            if not tech_values and not tech_vars and not tech_bnds:
                continue

            for var, bound in zip(tech_vars, tech_bnds):
                tech_indices.append(idx)
                tech_variables.append(var)
                tech_bounds.append(bound)
            initial_values.extend(tech_values)

        # Define pyomo variables (as integers)
        model.vars = Var(
            range(len(initial_values)), 
            domain=NonNegativeIntegers, 
            bounds=lambda model, i: tech_bounds[i]
        )

        # Define the objective function
        def objective_rule(model):
            # Extract variable values
            variables = [model.vars[i]() for i in range(len(initial_values))]
            # Call the calculate_mix function with numeric values
            self.energy_system_copy.calculate_mix(variables, tech_variables)
            results = self.energy_system_copy.results

            # Weighted sum
            weighted_sum = (
                self.weights['WGK_Gesamt'] * results['WGK_Gesamt'] +
                self.weights['specific_emissions_Gesamt'] * results['specific_emissions_Gesamt'] +
                self.weights['primärenergiefaktor_Gesamt'] * results['primärenergiefaktor_Gesamt']
            )
            return weighted_sum

        model.objective = Objective(rule=objective_rule, sense=minimize)

        # Define constraints (if necessary)
        model.constraints = ConstraintList()
        # Add your constraints here if you have any

        # Solve the model
        solver = SolverFactory('glpk')  # Or any solver supporting MILP
        result = solver.solve(model, tee=True)

        # Check if the solution is optimal
        if result.solver.termination_condition == "optimal":
            # Map optimized values back to the energy system
            optimized_values = [model.vars[i]() for i in range(len(initial_values))]
            for idx, tech in enumerate(self.energy_system_copy.technologies):
                tech.update_parameters(optimized_values, tech_variables, idx)
            print("Optimierung erfolgreich")
            return self.energy_system_copy
        else:
            print("Optimierung nicht erfolgreich:", result.solver.termination_condition)
            return self.initial_energy_system
"""