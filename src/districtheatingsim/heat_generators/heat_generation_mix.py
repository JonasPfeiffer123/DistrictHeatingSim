"""
Filename: heat_generator_mix.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-13
Description: Class to calculate the heat generation mix for a district heating system.

"""

import logging
logging.basicConfig(level=logging.INFO)

import numpy as np
import matplotlib.pyplot as plt
import copy

from scipy.optimize import minimize as scipy_minimize
from pyomo.environ import ConcreteModel, Var, Objective, ConstraintList, SolverFactory, NonNegativeReals, Integers, Reals, minimize as pyomo_minimize

from districtheatingsim.heat_generators import TECH_CLASS_REGISTRY

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

        self.duration = (np.diff(self.time_steps[:2]) / np.timedelta64(1, 'h'))[0]

    def add_technology(self, tech):
        """
        Add a technology to the energy system.

        Args:
            tech (object): Technology object to add.
        """
        self.technologies.append(tech)

    def initialize_results(self):
        """
        Initialize results for the energy system.

        """
        
        self.results = {
            'time_steps': self.time_steps,
            'Last_L': self.load_profile,
            'VLT_L': self.VLT_L,
            'RLT_L': self.RLT_L,
            'Jahreswärmebedarf': (np.sum(self.load_profile) / 1000) * self.duration,
            'WGK_Gesamt': 0,
            'Restwärmebedarf': (np.sum(self.load_profile) / 1000) * self.duration,
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

    def set_optimization_variables(self, variables, variables_order):
        for tech in self.technologies:
            if len(variables) > 0:
                idx = tech.name.split("_")[-1]
                tech.set_parameters(variables, variables_order, idx)

    def aggregate_results(self, tech_results):
        """
        Aggregate results from a single technology into the overall system results.

        Args:
            tech_results (dict): Results from the individual technology.
        """
        self.results['techs'].append(tech_results.get('tech_name', 'unknown'))
        self.results['Wärmeleistung_L'].append(tech_results.get('Wärmeleistung_L', np.zeros_like(self.load_profile)))
        self.results['Wärmemengen'].append(tech_results.get('Wärmemenge', 0))
        self.results['Anteile'].append(tech_results.get('Wärmemenge', 0) / self.results['Jahreswärmebedarf'])
        self.results['WGK'].append(tech_results.get('WGK', 0))
        self.results['specific_emissions_L'].append(tech_results.get('spec_co2_total', 0))
        self.results['primärenergie_L'].append(tech_results.get('primärenergie', 0))
        self.results['colors'].append(tech_results.get('color', 'gray'))

        if tech_results.get('Wärmemenge', 0) > 1e-6:
            self.results['Restlast_L'] -= tech_results.get('Wärmeleistung_L', np.zeros_like(self.load_profile))
            self.results['Restwärmebedarf'] -= tech_results.get('Wärmemenge', 0)
            self.results['WGK_Gesamt'] += (tech_results['Wärmemenge'] * tech_results['WGK']) / self.results['Jahreswärmebedarf']
            self.results['specific_emissions_Gesamt'] += (tech_results['Wärmemenge'] * tech_results['spec_co2_total']) / self.results['Jahreswärmebedarf']
            self.results['primärenergiefaktor_Gesamt'] += tech_results['primärenergie'] / self.results['Jahreswärmebedarf']

        if tech_results.get("Strommenge"):
            self.results['Strommenge'] += tech_results["Strommenge"]
            self.results['el_Leistung_L'] += tech_results["el_Leistung_L"]
            self.results['el_Leistung_ges_L'] += tech_results["el_Leistung_L"]

        if tech_results.get("Strombedarf"):
            self.results['Strombedarf'] += tech_results["Strombedarf"]
            self.results['el_Leistungsbedarf_L'] += tech_results["el_Leistung_L"]
            self.results['el_Leistung_ges_L'] -= tech_results["el_Leistung_L"]

        if "Wärmeleistung_Speicher_L" in tech_results.keys():
            self.results['Restlast_L'] -= tech_results["Wärmeleistung_Speicher_L"]
            self.results['Wärmeleistung_L'].append(tech_results["Wärmeleistung_Speicher_L"])
            self.results['techs'].append(f"{tech_results['tech_name']}_Speicher")
            self.results['Anteile'].append(0)
            self.results['colors'].append("gray")  # Optional: Farbzuordnung für Speicherleistung, ggf. dynamisch anpassen

    def calculate_mix(self, variables=[], variables_order=[]):
        """
        Calculate the energy generation mix for the given technologies.

        Args:
            variables (list): Variables for optimization.
            variables_order (list): Order of variables for optimization.

        Returns:
            dict: Results of the energy system simulation.
        """
        
        self.initialize_results()

        self.set_optimization_variables(variables, variables_order)

        for tech in self.technologies:
            # Perform technology-specific calculation
            tech_results = tech.calculate(economic_parameters=self.economic_parameters,
                                        duration=self.duration,
                                        load_profile=self.results["Restlast_L"],
                                        VLT_L=self.VLT_L,
                                        RLT_L=self.RLT_L,
                                        TRY_data=self.TRY_data,
                                        COP_data=self.COP_data,
                                        time_steps=self.time_steps)
            
            if tech_results['Wärmemenge'] > 1e-6:
                self.aggregate_results(tech_results)
            else:
                # Add technology as inactive with zero contribution
                self.aggregate_results({'tech_name': tech.name})
        
        self.results['tech_classes'] = self.technologies

        return self.results

    def optimize_mix(self, weights, num_restarts=5):
        """
        Optimize the energy generation mix for minimal cost, emissions, and primary energy use.

        Args:
            weights (dict): Weights for optimization criteria.

        Returns:
            list: Optimized list of technology objects with updated parameters.
        """
        optimizer = EnergySystemOptimizer(self, weights, num_restarts)
        self.optimized_energy_system = optimizer.optimize()
        
        return self.optimized_energy_system
    
    def optimize_milp(self, weights, num_restarts=5):
        """
        Optimize the energy generation mix using a MILP solver.

        Args:
            weights (dict): Weights for optimization criteria.

        Returns:
            list: Optimized list of technology objects with updated parameters.
        """
        optimizer = EnergySystemMILPOptimizer(self, weights, num_restarts)
        self.optimized_energy_system = optimizer.optimize()
        return self.optimized_energy_system
    
    def plot_stack_plot(self, figure=None):
        """
        Plot a stack plot of the thermal power generated by each technology, including storage performance if applicable.

        Args:
            figure (matplotlib.figure.Figure, optional): Figure object for the plot. Defaults to None.
        """
        if figure is None:
            figure = plt.figure()

        data = self.results['Wärmeleistung_L']
        labels = self.results['techs']
        colors = self.results['colors']

        ax = figure.add_subplot(111)
        ax.stackplot(self.results['time_steps'], data, labels=labels, colors=colors)
        ax.plot(self.results['time_steps'], self.results["Last_L"], color="black", linewidth=0.5, label="Lastprofil")
        ax.set_title("Jahresdauerlinie")
        ax.set_xlabel("Jahresstunden")
        ax.set_ylabel("thermische Leistung in kW")
        ax.grid()
        ax.legend(loc="upper center", ncol=3)

    def plot_pie_chart(self, figure=None, include_unmet_demand=True):
        """
        Plot a pie chart showing the contribution of each technology.

        Args:
            figure (matplotlib.figure.Figure, optional): Figure object for the plot. Defaults to None.
            include_unmet_demand (bool): Whether to include unmet demand in the chart.
        """
        if figure is None:
            figure = plt.figure()

        ax = figure.add_subplot(111)
        labels = self.results['techs']
        Anteile = self.results['Anteile']
        colors = self.results['colors']

        # Check if unmet demand should be included
        summe = sum(Anteile)
        if include_unmet_demand and summe < 1:
            Anteile.append(1 - summe)
            labels.append("ungedeckter Bedarf")
            colors.append("black")

        ax.pie(
            Anteile,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            pctdistance=0.85
        )
        ax.set_title("Anteile Wärmeerzeugung")
        ax.axis("equal")  # Ensure the pie chart is circular
    
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

    def to_dict(self):
        return {
            'time_steps': self.time_steps.tolist(),
            'load_profile': self.load_profile.tolist(),
            'VLT_L': self.VLT_L.tolist(),
            'RLT_L': self.RLT_L.tolist(),
            'TRY_data': [data.tolist() for data in self.TRY_data],
            'COP_data': self.COP_data.tolist(), 
            'economic_parameters': self.economic_parameters,
            'technologies': [tech.to_dict() for tech in self.technologies],
            'results': self.results,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Recreate an EnergySystem instance from a dictionary.

        Args:
            data (dict): Dictionary representation of the EnergySystem.

        Returns:
            EnergySystem: A fully initialized EnergySystem object.
        """
        # Restore basic attributes
        time_steps = np.array(data['time_steps'], dtype='datetime64[ns]')
        load_profile = np.array(data['load_profile'])
        VLT_L = np.array(data['VLT_L'])
        RLT_L = np.array(data['RLT_L'])
        TRY_data = [np.array(item) for item in data['TRY_data']]
        COP_data = np.array(data['COP_data'])
        economic_parameters = data['economic_parameters']

        # Create the EnergySystem object
        obj = cls(
            time_steps=time_steps,
            load_profile=load_profile,
            VLT_L=VLT_L,
            RLT_L=RLT_L,
            TRY_data=TRY_data,
            COP_data=COP_data,
            economic_parameters=economic_parameters
        )

        # Restore technologies
        obj.technologies = []
        for tech_data in data.get('technologies', []):
            for prefix, tech_class in TECH_CLASS_REGISTRY.items():
                if tech_data['name'].startswith(prefix):
                    obj.technologies.append(tech_class.from_dict(tech_data))
                    break

        # Restore results (if available)
        obj.results = {}
        if 'results' in data:
            for key, value in data['results'].items():
                if isinstance(value, list):
                    # Handle arrays, list of lists, or objects
                    if all(isinstance(v, list) for v in value):
                        obj.results[key] = [np.array(v) for v in value]
                    else:
                        obj.results[key] = np.array(value)
                else:
                    obj.results[key] = value

        return obj

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

            if not initial_values:
                print("Keine Optimierungsparameter vorhanden. Optimierung wird übersprungen.")
                return self.energy_system_copy.technologies

            # Generate random initial values within the bounds
            random_initial_values = [
                np.random.uniform(low=bound[0], high=bound[1]) if bound[0] < bound[1] else bound[0]
                for bound in bounds
            ]

            print(f"Initial values: {random_initial_values}")

            def objective(variables):
                # Erstelle bei jedem Aufruf eine neue Kopie
                fresh_energy_system = self.energy_system_copy.copy()

                # Berechnung auf Basis der frischen Kopie
                fresh_energy_system.calculate_mix(variables, variables_order)
                results = fresh_energy_system.results

                #print(f"Variables: {variables}, Variables Order: {variables_order}, Results['WGK_Gesamt']: {results['WGK_Gesamt']}")

                # Calculate the weighted sum
                weighted_sum = (
                    self.weights['WGK_Gesamt'] * results['WGK_Gesamt'] +
                    self.weights['specific_emissions_Gesamt'] * results['specific_emissions_Gesamt'] +
                    self.weights['primärenergiefaktor_Gesamt'] * results['primärenergiefaktor_Gesamt']
                )
                return weighted_sum

            # Perform the optimization
            result = scipy_minimize(objective, random_initial_values, method='SLSQP', bounds=bounds)

            # Check if the current run has a better solution
            if result.success and result.fun < best_objective_value:
                best_objective_value = result.fun
                best_solution = result

        # If a valid solution was found, apply the best solution
        if best_solution:
            for tech in self.energy_system_copy.technologies:
                print(f"Best Solution: {best_solution.x}, Variables Order: {variables_order}")
                tech.update_parameters(best_solution.x, variables_order)

            print("Optimierung erfolgreich")
            return self.energy_system_copy
        else:
            print("Keine gültige Lösung gefunden.")
            return self.initial_energy_system

### MILP Optimizer: Doesn't work for the current energy system setup as it is not defined linerarly ###
### Therefore, the MILP optimizer is not used in the current implementation ###
### But shows how to implement a MILP optimizer could look like ###
class EnergySystemMILPOptimizer:
    def __init__(self, initial_energy_system, weights, num_restarts=5):
        """
        Initialize the MILP optimizer for the energy system with support for multiple random restarts.

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
        Perform MILP optimization of the energy system with multiple random restarts.

        Returns:
            object: Optimized energy system object.
        """
        best_solution = None
        best_objective_value = float('inf')

        for restart in range(self.num_restarts):
            print(f"Starting MILP optimization run {restart + 1}/{self.num_restarts}")

            # Copy the energy system for this run
            self.energy_system_copy = self.initial_energy_system.copy()

            initial_values = []
            bounds = []
            variables_mapping = {}  # Mapping for variables

            for tech in self.energy_system_copy.technologies:
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

            if not initial_values:
                print("Keine Optimierungsparameter vorhanden. Optimierung wird übersprungen.")
                return self.energy_system_copy.technologies
            
            # Teste die Zielfunktion mit unterschiedlichen Variablenwerten
            for test_value in range(bounds[0][0], bounds[0][1], 100):
                variables = [test_value]  # Beispiel: Nur eine Variable
                fresh_system = self.energy_system_copy.copy()
                fresh_system.calculate_mix(variables, variables_order)
                #print(f"Test variables: {variables}, Results['WGK_Gesamt']: {fresh_system.results['WGK_Gesamt']}")

            # Pyomo model setup
            model = ConcreteModel()

            # Generate random initial values within the bounds
            random_initial_values = [
                np.random.randint(low=bound[0], high=bound[1] + 1) if bound[0] < bound[1] else bound[0]
                for bound in bounds
            ]

            print(f"Initial values: {random_initial_values}")

            # Define Pyomo variables as integers (MILP constraint) with initialization
            model.vars = Var(
                range(len(variables_order)),
                domain=Integers,
                initialize=lambda model, i: random_initial_values[i],
                bounds=lambda model, i: bounds[i]
            )

            def objective_rule(model):
                variables = [model.vars[i].value for i in range(len(variables_order))]
                
                # Erstelle bei jedem Aufruf eine neue Kopie
                fresh_energy_system = self.energy_system_copy.copy()

                # Berechnung auf Basis der frischen Kopie
                fresh_energy_system.calculate_mix(variables, variables_order)
                results = fresh_energy_system.results

                print(f"Variables: {variables}, Variables Order: {variables_order}, Results['WGK_Gesamt']: {results['WGK_Gesamt']}")

                # Zielfunktion berechnen
                weighted_sum = (
                    self.weights['WGK_Gesamt'] * results['WGK_Gesamt'] +
                    self.weights['specific_emissions_Gesamt'] * results['specific_emissions_Gesamt'] +
                    self.weights['primärenergiefaktor_Gesamt'] * results['primärenergiefaktor_Gesamt']
                )
                return weighted_sum
            
            model.vars.pprint()

            # Add objective function
            model.objective = Objective(rule=objective_rule, sense=pyomo_minimize)

            # Add constraints (if any)
            model.constraints = ConstraintList()
            model.constraints.add(model.vars[0] >= 10)

            # Solve the MILP problem
            solver = SolverFactory('highs')
            result = solver.solve(model, tee=True)

            if restart == 0:
                best_objective_value = model.objective()
            # Check if the current run has a better solution
            if result.solver.termination_condition == 'optimal' and model.objective() <= best_objective_value:
                model.vars.pprint()
                print(f"Best objective value: {model.objective()}, Best solution: {[model.vars[i].value for i in range(len(variables_order))]}")
                best_objective_value = model.objective()
                best_solution = [model.vars[i].value for i in range(len(variables_order))]

        # If a valid solution was found, apply the best solution
        if best_solution:
            for tech in self.energy_system_copy.technologies:
                print(f"Best Solution: {best_solution}, Variables Order: {variables_order}")
                tech.update_parameters(best_solution, variables_order)

            print("MILP Optimierung erfolgreich")
            return self.energy_system_copy
        else:
            print("Keine gültige Lösung gefunden.")
            return self.initial_energy_system