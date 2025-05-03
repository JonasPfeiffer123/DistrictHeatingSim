"""
Filename: heat_generator_mix.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-25
Description: Class to calculate the heat generation mix for a district heating system.

"""

import logging
logging.basicConfig(level=logging.INFO)

import numpy as np
import matplotlib.pyplot as plt
import copy
import json
import pandas as pd

from scipy.optimize import minimize as scipy_minimize

from districtheatingsim.heat_generators import TECH_CLASS_REGISTRY

from districtheatingsim.heat_generators.STES import TemperatureStratifiedThermalStorage

from districtheatingsim.gui.EnergySystemTab._10_utilities import CustomJSONEncoder

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
        self.storage = None
        
        self.results = {}

        self.duration = (np.diff(self.time_steps[:2]) / np.timedelta64(1, 'h'))[0]

    def add_technology(self, tech):
        """
        Add a technology to the energy system.

        Args:
            tech (object): Technology object to add.
        """
        self.technologies.append(tech)

    def add_storage(self, storage):
        """
        Add a seasonal storage to the energy system.

        Args:
            storage (TemperatureStratifiedThermalStorage): Storage object.
        """
        self.storage = storage

    def initialize_results(self):
        """
        Initialize results for the energy system.
        """
        if not hasattr(self, 'results') or not isinstance(self.results, dict):
            self.results = {}

        self.results.update({
            'time_steps': self.time_steps,
            'Last_L': self.load_profile,
            'VLT_L': self.VLT_L,
            'RLT_L': self.RLT_L,
            'Jahreswärmebedarf': (np.sum(self.load_profile) / 1000) * self.duration,
            'Restlast_L': self.load_profile.copy(),
            'Restwärmebedarf': (np.sum(self.load_profile) / 1000) * self.duration,
            'WGK_Gesamt': 0,
            'Strombedarf': 0,
            'Strommenge': 0,
            'el_Leistungsbedarf_L': np.zeros_like(self.load_profile),
            'el_Leistung_L': np.zeros_like(self.load_profile),
            'el_Leistung_ges_L': np.zeros_like(self.load_profile),
            'specific_emissions_Gesamt': 0,
            'primärenergiefaktor_Gesamt': 0,
        })

        # Ensure lists are initialized or cleared
        for key in ['Wärmeleistung_L', 'colors', 'Wärmemengen', 'Anteile', 'WGK', 
                    'specific_emissions_L', 'primärenergie_L', 'techs']:
            if key not in self.results:
                self.results[key] = []
            else:
                self.results[key].clear()

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
        
        # Initialize optimization variables
        self.set_optimization_variables(variables, variables_order)
        
        for tech in self.technologies:
            if isinstance(tech, TemperatureStratifiedThermalStorage):
                self.storage = tech
                # remove the storage from the technologies list
                self.technologies.remove(tech)

            else:
                # Initialize each technology
                tech.init_operation(8760)

        if self.storage:
            self.storage_state = np.zeros(len(self.time_steps))

            # Ergebnisse für jeden Zeitschritt initialisieren
            time_steps = len(self.time_steps)

            for t in range(time_steps):
                Q_in_total = 0  # Summe der Wärmeeinspeisung

                T_Q_in_flow = self.VLT_L[t] # Vorlauftemperatur
                T_Q_out_return = self.RLT_L[t] # Rücklauftemperatur

                Q_out_total = self.load_profile[t] # Wärmebedarf
                remaining_load = Q_out_total

                # Speicherzustand und Temperaturen abrufen
                upper_storage_temperature, lower_storage_temperature = self.storage.current_storage_temperatures(t-1) if t > 0 else (0, 0)
                # Speicherzustand und verfügbare Energie abrufen
                current_storage_state, available_energy, max_energy = self.storage.current_storage_state(t-1, T_Q_out_return, T_Q_in_flow) if t > 0 else (0, 0, 0)
                # Speicherverluste berechnen
                Q_loss = self.storage.Q_loss[t - 1] if t > 0 else 0

                # Generatoren basierend auf Priorität steuern
                for i, tech in enumerate(self.technologies):
                    tech.active = tech.strategy.decide_operation(tech.active, upper_storage_temperature, lower_storage_temperature, remaining_load)

                    if tech.active:
                        # Erstelle ein kwargs-Dictionary mit technologie-spezifischen Daten
                        kwargs = {
                            "remaining_load": remaining_load,
                            "VLT_L": self.VLT_L[t],
                            "COP_data": self.COP_data,
                            "time_steps": self.time_steps,
                            "duration": self.duration,
                            "TRY_data": self.TRY_data,
                            "RLT_L": self.RLT_L[t],
                            "upper_storage_temperature": upper_storage_temperature,
                            "lower_storage_temperature": lower_storage_temperature,
                            "current_storage_state": current_storage_state,
                            "available_energy": available_energy,
                            "max_energy": max_energy,
                            "Q_loss": Q_loss,
                        }
                        Q_in, _ = tech.generate(t, **kwargs)
                        remaining_load -= Q_in
                        Q_in_total += Q_in

                        tech.calculated = True  # Markiere die Technologie als berechnet

                # Speicher aktualisieren
                self.storage.simulate_stratified_temperature_mass_flows(t, Q_in_total, Q_out_total, T_Q_in_flow, T_Q_out_return)

            # Speicherergebnisse berechnen
            self.storage.calculate_efficiency(self.load_profile)
            self.storage.calculate_operational_costs(0.10) # needs to be changed to a parameter
            self.results['storage_class'] = self.storage
        
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

        self.getInitialPlotData()

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
    
    def getInitialPlotData(self):
        """
        Returns the initial data for plotting.

        """

        # Daten extrahieren
        self.extracted_data = {}
        for tech_class in self.technologies:
            for var_name in dir(tech_class):
                var_value = getattr(tech_class, var_name)
                if isinstance(var_value, (list, np.ndarray)) and len(var_value) == len(self.time_steps):
                    unique_var_name = f"{tech_class.name}_{var_name}"
                    self.extracted_data[unique_var_name] = var_value

        # Speicherdaten hinzufügen
        if self.storage:
            Q_net_storage_flow = self.storage.Q_net_storage_flow
            print(f"Speicherergebnisse: {Q_net_storage_flow[8000]}")

            # Speicherbeladung (negative Werte) und Speicherentladung (positive Werte) trennen
            Q_net_positive = np.maximum(Q_net_storage_flow, 0)  # Speicherentladung
            Q_net_negative = np.minimum(Q_net_storage_flow, 0)  # Speicherbeladung

            # Speicherdaten zur extrahierten Datenstruktur hinzufügen
            self.extracted_data['Speicherbeladung_kW'] = Q_net_negative
            self.extracted_data['Speicherentladung_kW'] = Q_net_positive

        # Initiale Auswahl
        self.initial_vars = [var_name for var_name in self.extracted_data.keys() if "_Wärmeleistung" in var_name]
        self.initial_vars.append("Last_L")
        if self.storage:
            self.initial_vars.append("Speicherbeladung_kW")
            self.initial_vars.append("Speicherentladung_kW")

        return self.extracted_data, self.initial_vars
    
    def plot_stack_plot(self, figure=None, selected_vars=None, second_y_axis=False):
        """
        Plots the stack plot of the energy system.

        Args:
            figure (matplotlib.figure.Figure): The figure to plot on.
            selected_vars (list, optional): List of selected variables to plot. Defaults to None.
            second_y_axis (bool): Whether to use a second y-axis for some variables. Defaults to False.
        """
        if figure is None:
            figure = plt.figure()

        if selected_vars is None:
            selected_vars = self.initial_vars

        ax1 = figure.add_subplot(111)

        # Speicherbeladung und -entladung priorisieren
        stackplot_vars = []
        if "Speicherbeladung_kW" in selected_vars:
            stackplot_vars.append("Speicherbeladung_kW")
        if "Speicherentladung_kW" in selected_vars:
            stackplot_vars.append("Speicherentladung_kW")

        # Füge die restlichen Variablen hinzu
        stackplot_vars += [var for var in selected_vars if var not in stackplot_vars and "_Wärmeleistung" in var]

        # Speicherentladung ans Ende verschieben
        if "Speicherentladung_kW" in stackplot_vars:
            stackplot_vars.remove("Speicherentladung_kW")
            stackplot_vars.append("Speicherentladung_kW")

        # Linienvariablen (z. B. Lastprofil)
        line_vars = [var for var in selected_vars if var not in stackplot_vars and var != "Last_L"]

        # Stackplot-Daten vorbereiten
        stackplot_data = []
        for var in stackplot_vars:
            if var == "Speicherbeladung_kW" and var in self.extracted_data:
                # Speicherbeladung als negative Werte darstellen, aber nicht in den Stackplot integrieren
                ax1.fill_between(
                    self.results["time_steps"],
                    0,
                    self.extracted_data[var],
                    label=var,
                    step="mid",
                    color="gray",
                    alpha=1.0,
                )
            elif var in self.extracted_data:
                stackplot_data.append(self.extracted_data[var])

        # Zeichne den Stackplot für die restlichen Variablen
        if stackplot_data:
            ax1.stackplot(
                self.results["time_steps"],
                stackplot_data,
                labels=[var for var in stackplot_vars if var != "Speicherbeladung_kW"],
                step="mid"
            )

        # Linienplot
        ax2 = ax1.twinx() if second_y_axis else None
        for var_name in line_vars:
            if var_name in self.extracted_data:
                if ax2:
                    ax2.plot(self.results["time_steps"], self.extracted_data[var_name], label=var_name)
                else:
                    ax1.plot(self.results["time_steps"], self.extracted_data[var_name], label=var_name)

        # Lastprofil
        if "Last_L" in selected_vars:
            ax1.plot(self.results["time_steps"], self.results["Last_L"], color='blue', label='Last', linewidth=0.25)

        # Achsentitel und Legende
        ax1.set_title("Jahresganglinie")
        ax1.set_xlabel("Jahresstunden")
        ax1.set_ylabel("thermische Leistung in kW")
        ax1.grid()
        ax1.legend(loc='upper left' if ax2 else 'upper center')
        if ax2:
            ax2.legend(loc='upper right', ncol=2)

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
        # Create a new EnergySystem instance with copied basic attributes
        copied_system = EnergySystem(
            time_steps=self.time_steps.copy(),
            load_profile=self.load_profile.copy(),
            VLT_L=self.VLT_L.copy(),
            RLT_L=self.RLT_L.copy(),
            TRY_data=copy.deepcopy(self.TRY_data),
            COP_data=copy.deepcopy(self.COP_data),
            economic_parameters=copy.deepcopy(self.economic_parameters)
        )

        # Deep-copy the technologies
        copied_system.technologies = [copy.deepcopy(tech) for tech in self.technologies]

        # Deep-copy the storage, if it exists
        if self.storage:
            copied_system.storage = copy.deepcopy(self.storage)

        # Deep-copy the results dictionary
        copied_system.results = copy.deepcopy(self.results)

        # Copy any additional attributes that may have been added dynamically
        for attr_name, attr_value in self.__dict__.items():
            if attr_name not in copied_system.__dict__:
                copied_system.__dict__[attr_name] = copy.deepcopy(attr_value)

        return copied_system

    def to_dict(self):
        return {
            'time_steps': self.time_steps.astype(str).tolist(),  # Convert datetime64 to string
            'load_profile': self.load_profile.tolist(),
            'VLT_L': self.VLT_L.tolist(),
            'RLT_L': self.RLT_L.tolist(),
            'TRY_data': [data.tolist() for data in self.TRY_data],
            'COP_data': self.COP_data.tolist(), 
            'economic_parameters': self.economic_parameters,
            'technologies': [tech.to_dict() for tech in self.technologies],
            'storage': self.storage.to_dict() if self.storage else None,  # Serialize storage
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
        time_steps = np.array(data['time_steps'], dtype='datetime64')
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

        # Restore storage
        if data.get('storage'):
            obj.storage = TemperatureStratifiedThermalStorage.from_dict(data['storage'])


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
    
    def save_to_csv(self, file_path):
        """
        Saves the heat generation results to a CSV file.

        Args:
            file_path (str): The path to save the CSV file.
        """
        if not self.results:
            raise ValueError("No results available to save.")

        # Initialize the DataFrame with the timestamps
        df = pd.DataFrame({'time_steps': self.results['time_steps']})
        
        # Add the load data
        df['Last_L'] = self.results['Last_L']
        
        # Add the heat generation data for each technology
        for tech_results, techs in zip(self.results['Wärmeleistung_L'], self.results['techs']):
            df[techs] = tech_results
        
        # Add the electrical power data
        df['el_Leistungsbedarf_L'] = self.results['el_Leistungsbedarf_L']
        df['el_Leistung_L'] = self.results['el_Leistung_L']
        df['el_Leistung_ges_L'] = self.results['el_Leistung_ges_L']
        
        # Save the DataFrame as a CSV file
        df.to_csv(file_path, index=False, sep=";")

    def save_to_json(self, file_path):
        """
        Saves the EnergySystem object and its results to a JSON file.

        Args:
            file_path (str): The path to save the JSON file.
        """
        with open(file_path, 'w') as json_file:
            json.dump(self.to_dict(), json_file, indent=4, cls=CustomJSONEncoder)

    @classmethod
    def load_from_json(cls, file_path):
        """
        Loads the EnergySystem object and its results from a JSON file.

        Args:
            file_path (str): The path to the JSON file.

        Returns:
            EnergySystem: The loaded EnergySystem object.
        """
        try:
            with open(file_path, 'r') as json_file:
                data_loaded = json.load(json_file)
            return cls.from_dict(data_loaded)
        except Exception as e:
            raise ValueError(f"Fehler beim Laden der JSON-Datei: {e}")

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