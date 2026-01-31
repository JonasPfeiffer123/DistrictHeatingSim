"""
Energy System Module
=====================

Multi-technology energy system modeling with optimization and visualization.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging
logging.basicConfig(level=logging.INFO)

import numpy as np
import matplotlib.pyplot as plt
import copy
import json
import pandas as pd

from typing import Dict, Tuple, List, Optional, Union

from scipy.optimize import minimize as scipy_minimize

from districtheatingsim.heat_generators import *
from districtheatingsim.gui.EnergySystemTab._10_utilities import CustomJSONEncoder
import itertools
from matplotlib import cm

class EnergySystem:
    """
    Multi-technology district heating system integration.

    :param time_steps: Simulation time steps
    :type time_steps: numpy.ndarray
    :param load_profile: Hourly thermal load [kW]
    :type load_profile: numpy.ndarray
    :param VLT_L: Supply temperature profile [°C]
    :type VLT_L: numpy.ndarray
    :param RLT_L: Return temperature profile [°C]
    :type RLT_L: numpy.ndarray
    :param TRY_data: Test Reference Year meteorological data
    :type TRY_data: object
    :param COP_data: Heat pump performance data
    :type COP_data: object
    :param economic_parameters: Economic parameters dict
    :type economic_parameters: dict

    .. note::
       Supports multi-technology dispatch, storage integration and optimization.
    """

    def __init__(self, time_steps: np.ndarray, load_profile: np.ndarray, VLT_L: np.ndarray, 
                 RLT_L: np.ndarray, TRY_data: object, COP_data: object, economic_parameters: dict):
        """
        Initialize energy system.

        :param time_steps: Time steps for simulation
        :type time_steps: numpy.ndarray
        :param load_profile: Hourly thermal load [kW]
        :type load_profile: numpy.ndarray
        :param VLT_L: Supply temperature [°C]
        :type VLT_L: numpy.ndarray
        :param RLT_L: Return temperature [°C]
        :type RLT_L: numpy.ndarray
        :param TRY_data: Test Reference Year data
        :type TRY_data: object
        :param COP_data: Heat pump performance data
        :type COP_data: object
        :param economic_parameters: Economic parameters
        :type economic_parameters: dict
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

    def add_technology(self, tech) -> None:
        """
        Add a heat generation technology to the energy system.

        :param tech: Technology object to add.
        :type tech: BaseHeatGenerator

        .. note:: Technologies operate based on priority and control strategies.
        """
        self.technologies.append(tech)

    def add_storage(self, storage) -> None:
        """
        Add a seasonal thermal energy storage system to the energy system.

        :param storage: Seasonal Thermal Energy Storage object.
        :type storage: STES

        .. note:: Enables temporal decoupling of generation and demand for improved efficiency.
        """
        self.storage = storage

    def initialize_results(self) -> None:
        """
        Initialize the results dictionary for energy system calculations.

        .. note:: Sets up structure for energy balance, economic, environmental, and performance results.
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

    def set_optimization_variables(self, variables: list, variables_order: list) -> None:
        """
        Set optimization variables for technologies.

        :param variables: Optimization variable values
        :type variables: list
        :param variables_order: Variable names
        :type variables_order: list
        """
        for tech in self.technologies:
            if len(variables) > 0:
                idx = tech.name.split("_")[-1]
                tech.set_parameters(variables, variables_order, idx)

    def aggregate_results(self, tech_results: dict) -> None:
        """
        Aggregate technology results into system-level metrics.

        :param tech_results: Technology results dictionary
        :type tech_results: dict
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
            self.results['colors'].append("gray")

    def calculate_mix(self, variables: list = [], variables_order: list = []) -> dict:
        """
        Calculate energy generation mix with technology dispatch and storage.

        :param variables: Optimization variables, defaults to []
        :type variables: list
        :param variables_order: Variable order, defaults to []
        :type variables_order: list
        :return: System results dictionary
        :rtype: dict
        """
        self.initialize_results()
        
        # Initialize optimization variables
        self.set_optimization_variables(variables, variables_order)
        
        for tech in self.technologies:
            if isinstance(tech, STES):
                self.storage = tech
                # remove the storage from the technologies list
                self.technologies.remove(tech)
            else:
                # Initialize each technology
                tech.init_operation(8760)

        if self.storage:
            self.storage_state = np.zeros(len(self.time_steps))

            # Initialize results for each time step
            time_steps = len(self.time_steps)

            for t in range(time_steps):
                Q_in_total = 0  # Total heat input

                T_Q_in_flow = self.VLT_L[t] # Supply temperature
                T_Q_out_return = self.RLT_L[t] # Return temperature

                Q_out_total = self.load_profile[t] # Heat demand
                remaining_load = Q_out_total

                # Get storage state and temperatures
                upper_storage_temperature, lower_storage_temperature = self.storage.current_storage_temperatures(t-1) if t > 0 else (0, 0)
                # Get storage state and available energy
                current_storage_state, available_energy, max_energy = self.storage.current_storage_state(t-1, T_Q_out_return, T_Q_in_flow) if t > 0 else (0, 0, 0)
                # Calculate storage losses
                Q_loss = self.storage.Q_loss[t - 1] if t > 0 else 0

                # Control generators based on priority
                for i, tech in enumerate(self.technologies):
                    tech.active = tech.strategy.decide_operation(tech.active, upper_storage_temperature, lower_storage_temperature, remaining_load)

                    if tech.active:
                        # Create kwargs dictionary with technology-specific data
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

                        tech.calculated = True  # Mark technology as calculated

                # Update storage
                self.storage.simulate_stratified_temperature_mass_flows(t, Q_in_total, Q_out_total, T_Q_in_flow, T_Q_out_return)

            # Calculate storage results
            self.storage.calculate_efficiency(self.load_profile)
            # self.storage.calculate_operational_costs(0.10) # TODO: needs to be implemented in STES class
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

        # Calculate unmet demand after processing all technologies
        if np.any(self.results['Restlast_L'] > 1e-6):
            unmet_demand = np.sum(self.results['Restlast_L']) / 1000 * self.duration
            self.results['Wärmeleistung_L'].append(self.results['Restlast_L'])
            self.results['Wärmemengen'].append(unmet_demand)
            self.results['techs'].append("Ungedeckter Bedarf")
            self.results['Anteile'].append(unmet_demand / self.results['Jahreswärmebedarf'])
            self.results['colors'].append("black")

        self.getInitialPlotData()

        return self.results

    def optimize_mix(self, weights: dict, num_restarts: int = 5):
        """
        Optimize energy mix for multi-objective performance.

        :param weights: Optimization weights (WGK_Gesamt, specific_emissions_Gesamt, primärenergiefaktor_Gesamt)
        :type weights: dict
        :param num_restarts: Number of random restarts, defaults to 5
        :type num_restarts: int
        :return: Optimized energy system
        :rtype: EnergySystem
        """
        optimizer = EnergySystemOptimizer(self, weights, num_restarts)
        self.optimized_energy_system = optimizer.optimize()
        
        return self.optimized_energy_system
    
    def getInitialPlotData(self) -> tuple:
        """
        Extract and prepare data for visualization.

        :return: (extracted_data, initial_vars)
        :rtype: tuple
        """
        # Extract data
        self.extracted_data = {}
        for tech_class in self.technologies:
            for var_name in dir(tech_class):
                var_value = getattr(tech_class, var_name)
                if isinstance(var_value, (list, np.ndarray)) and len(var_value) == len(self.time_steps):
                    unique_var_name = f"{tech_class.name}_{var_name}"
                    self.extracted_data[unique_var_name] = var_value

        # Add storage data
        if self.storage:
            Q_net_storage_flow = self.storage.Q_net_storage_flow

            # Separate storage charging (negative values) and discharging (positive values)
            Q_net_positive = np.maximum(Q_net_storage_flow, 0)  # Storage discharging
            Q_net_negative = np.minimum(Q_net_storage_flow, 0)  # Storage charging

            # Add storage data to extracted data structure
            self.extracted_data['Speicherbeladung_kW'] = Q_net_negative
            self.extracted_data['Speicherentladung_kW'] = Q_net_positive

        if "Ungedeckter Bedarf" in self.results['techs']:
            # Find index of "Ungedeckter Bedarf" in technology list
            if isinstance(self.results['techs'], list):
                unmet_demand_index = self.results['techs'].index("Ungedeckter Bedarf")
            elif isinstance(self.results['techs'], np.ndarray):
                unmet_demand_index = np.where(self.results['techs'] == "Ungedeckter Bedarf")[0][0]
            else:
                # Skip unmet demand if data type is unknown
                unmet_demand_index = None
            
            # Add unmet demand to extracted data structure if index was found
            if unmet_demand_index is not None:
                self.extracted_data['Ungedeckter_Bedarf_kW'] = self.results["Wärmeleistung_L"][unmet_demand_index]

        # Initial selection
        self.initial_vars = [var_name for var_name in self.extracted_data.keys() if "_Wärmeleistung" in var_name]
        self.initial_vars.append("Last_L")
        if self.storage:
            self.initial_vars.append("Speicherbeladung_kW")
            self.initial_vars.append("Speicherentladung_kW")

        return self.extracted_data, self.initial_vars
    
    def plot_stack_plot(self, figure=None, selected_vars=None, second_y_axis=False) -> None:
        """
        Create stack plot visualization of energy system operation.

        :param figure: Figure object, defaults to None
        :type figure: matplotlib.figure.Figure, optional
        :param selected_vars: Selected variables, defaults to None
        :type selected_vars: list, optional
        :param second_y_axis: Use second y-axis, defaults to False
        :type second_y_axis: bool, optional
        """
        if figure is None:
            figure = plt.figure()

        if selected_vars is None:
            selected_vars = self.initial_vars

        # X-Achse: Jahresstunden als int
        n_steps = len(self.time_steps)
        x = np.arange(n_steps)
        import matplotlib.gridspec as gridspec
        figure.clear()
        # Breitere Legenden-Spalten für lange Namen
        gs = gridspec.GridSpec(1, 3, width_ratios=[0.22, 0.56, 0.22], figure=figure)
        ax_legend_left = figure.add_subplot(gs[0, 0])
        ax_main = figure.add_subplot(gs[0, 1])
        ax_legend_right = figure.add_subplot(gs[0, 2])
        ax_legend_left.axis('off')
        ax_legend_right.axis('off')
        ax_main.set_prop_cycle(color=cm.tab10.colors)

        # Stackplot- und Linienplot-Logik auf ax_main
        stackplot_vars = []
        if "Speicherbeladung_kW" in selected_vars:
            stackplot_vars.append("Speicherbeladung_kW")
        if "Speicherentladung_kW" in selected_vars:
            stackplot_vars.append("Speicherentladung_kW")
        stackplot_vars += [var for var in selected_vars if var not in stackplot_vars and "_Wärmeleistung" in var]
        if "Ungedeckter_Bedarf_kW" in selected_vars:
            stackplot_vars.append("Ungedeckter_Bedarf_kW")
        if "Speicherentladung_kW" in stackplot_vars:
            stackplot_vars.remove("Speicherentladung_kW")
            stackplot_vars.append("Speicherentladung_kW")

        line_vars = [var for var in selected_vars if var not in stackplot_vars and var != "Last_L"]

        stackplot_data = []
        stackplot_labels = []
        for var in stackplot_vars:
            if var == "Speicherbeladung_kW" and var in self.extracted_data:
                ax_main.fill_between(
                    x,
                    0,
                    self.extracted_data[var],
                    label=var,
                    step="mid",
                    color="gray",
                    alpha=1.0,
                )
            elif var in self.extracted_data:
                stackplot_data.append(self.extracted_data[var])
                stackplot_labels.append(var)

        if stackplot_data:
            ax_main.stackplot(
                x,
                stackplot_data,
                labels=stackplot_labels,
                step="mid",
                edgecolor='none'
            )

        ax2 = ax_main.twinx() if second_y_axis else None
        lines_ax1 = []
        labels_ax1 = []
        lines_ax2 = []
        labels_ax2 = []
        import itertools
        color_cycle = itertools.cycle(cm.Dark2.colors)
        for var_name in line_vars:
            if var_name in self.extracted_data:
                if ax2:
                    line, = ax2.plot(
                        x,
                        self.extracted_data[var_name],
                        label=var_name,
                        color=next(color_cycle)
                    )
                    lines_ax2.append(line)
                    labels_ax2.append(var_name)
                else:
                    line, = ax_main.plot(x, self.extracted_data[var_name], label=var_name)
                    lines_ax1.append(line)
                    labels_ax1.append(var_name)

        if "Last_L" in selected_vars:
            line, = ax_main.plot(x, self.results["Last_L"], color='blue', label='Last', linewidth=0.25)
            lines_ax1.append(line)
            labels_ax1.append('Last')

        # Achsenbeschriftung und Grid
        ax_main.set_title("Jahresganglinie", fontsize=16)
        ax_main.set_xlabel("Jahresstunden", fontsize=14)
        ax_main.set_ylabel("Wärmeleistung [kW]", fontsize=14)
        ax_main.grid()
        if ax2:
            ax2.set_ylabel('Temperatur (°C)', fontsize=14)
            ax2.tick_params(axis='y', labelsize=14)

        step = 1000
        ax_main.set_xticks(np.arange(0, n_steps+step, step))
        ax_main.set_xticklabels([str(i) for i in np.arange(0, n_steps+step, step)])

        # Legenden in eigenen Achsen
        def get_ncol(n):
            return 1 if n <= 18 else 2

        if lines_ax1 or stackplot_labels:
            ncol_left = get_ncol(len(lines_ax1) + len(stackplot_labels))
            ax_legend_left.legend(
                ax_main.get_legend_handles_labels()[0],
                ax_main.get_legend_handles_labels()[1],
                loc='best',
                fontsize=12,
                frameon=False,
                ncol=ncol_left
            )
        if lines_ax2:
            ncol_right = get_ncol(len(lines_ax2))
            ax_legend_right.legend(lines_ax2, labels_ax2, loc='best', fontsize=12, frameon=False, ncol=ncol_right)

        # Weniger Rand, damit die Daten direkt an den Achsen anliegen
        figure.subplots_adjust(left=0.08, right=0.92, wspace=0.18)
        # X-Achse: min/max exakt an Daten
        ax_main.set_xlim(x[0], x[-1])
        # Y-Achse: min/max exakt an Daten
        y_data_ax1 = []
        for arr in stackplot_data:
            y_data_ax1.append(np.asarray(arr))
        for var_name in line_vars:
            if var_name in self.extracted_data:
                y_data_ax1.append(np.asarray(self.extracted_data[var_name]))
        if "Last_L" in selected_vars:
            y_data_ax1.append(np.asarray(self.results["Last_L"]))
        if y_data_ax1:
            y_min = min(arr.min() for arr in y_data_ax1)
            y_max = max(arr.max() for arr in y_data_ax1)
            ax_main.set_ylim(y_min, y_max)
        if ax2:
            y_data_ax2 = []
            for var_name in line_vars:
                if var_name in self.extracted_data:
                    y_data_ax2.append(np.asarray(self.extracted_data[var_name]))
            if y_data_ax2:
                y2_min = min(arr.min() for arr in y_data_ax2)
                y2_max = max(arr.max() for arr in y_data_ax2)
                ax2.set_ylim(y2_min, y2_max)

    def plot_pie_chart(self, figure=None) -> None:
        """
        Create pie chart visualization of technology contributions.

        :param figure: Figure object, defaults to None
        :type figure: matplotlib.figure.Figure, optional
        """
        if figure is None:
            figure = plt.figure()

        # clear the figure if it already exists
        if figure.axes:
            for ax in figure.axes:
                ax.clear()

        ax = figure.add_subplot(111)
        labels = self.results['techs']
        Anteile = self.results['Anteile']
        colors = self.results['colors']

        # Create the pie chart without percentage labels on the chart
        wedges, _ = ax.pie(
            Anteile,
            labels=None,
            colors=colors,
            startangle=90
        )
        ax.set_title("Anteile Wärmeerzeugung")
        ax.axis("equal")  # Ensure the pie chart is circular

        # Prepare legend labels with percentages
        percent_labels = [f"{label}: {100 * anteil:.1f}%" for label, anteil in zip(labels, Anteile)]
        ax.legend(wedges, percent_labels, loc="center left")
    
    def copy(self):
        """
        Create deep copy of EnergySystem instance.

        :return: Deep copy of energy system
        :rtype: EnergySystem
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

    def to_dict(self) -> dict:
        """
        Convert EnergySystem to dictionary for serialization and storage.

        Returns
        -------
        dict
            Dictionary representation of the complete energy system.
        """
        return {
            'time_steps': self.time_steps.astype(str).tolist(),  # Convert datetime64 to string
            'load_profile': self.load_profile.tolist(),
            'VLT_L': self.VLT_L.tolist(),
            'RLT_L': self.RLT_L.tolist(),
            'TRY_data': [data.tolist() for data in self.TRY_data],
            'COP_data': self.COP_data.tolist(),
            'economic_parameters': self.economic_parameters,
            'technologies': [tech.to_dict() for tech in self.technologies],
            'storage': self.storage.to_dict() if self.storage else None,
            'results': {
                key: (value.to_dict(orient='split') if isinstance(value, pd.DataFrame) else value)
                for key, value in self.results.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        Recreate EnergySystem instance from dictionary representation.

        Parameters
        ----------
        data : dict
            Dictionary representation of the EnergySystem.

        Returns
        -------
        EnergySystem
            Fully initialized EnergySystem object.
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
            obj.storage = STES.from_dict(data['storage'])

        # Restore results (if available)
        obj.results = {}
        if 'results' in data:
            for key, value in data['results'].items():
                if isinstance(value, dict) and 'columns' in value and 'data' in value:
                    obj.results[key] = pd.DataFrame(**value)
                elif isinstance(value, list):
                    if all(isinstance(v, list) for v in value):
                        obj.results[key] = [np.array(v) for v in value]
                    else:
                        obj.results[key] = np.array(value)
                else:
                    obj.results[key] = value

        return obj
    
    def save_to_csv(self, file_path: str) -> None:
        """
        Save energy system results to CSV file.

        :param file_path: Path for CSV output
        :type file_path: str
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
        df.to_csv(file_path, index=False, sep=";", encoding='utf-8-sig')

    def save_to_json(self, file_path: str) -> None:
        """
        Save complete EnergySystem object to JSON file for persistence.

        Parameters
        ----------
        file_path : str
            Path for JSON file output.
        """
        with open(file_path, 'w') as json_file:
            json.dump(self.to_dict(), json_file, indent=4, cls=CustomJSONEncoder)

    @classmethod
    def load_from_json(cls, file_path: str):
        """
        Load complete EnergySystem object from JSON file.

        Parameters
        ----------
        file_path : str
            Path to JSON file for loading.

        Returns
        -------
        EnergySystem
            Loaded EnergySystem object with complete configuration.
        """
        try:
            with open(file_path, 'r') as json_file:
                data_loaded = json.load(json_file)
            return cls.from_dict(data_loaded)
        except Exception as e:
            raise ValueError(f"Error loading JSON file: {e}")

class EnergySystemOptimizer:
    """
    Multi-objective optimizer for energy system configuration.

    :param initial_energy_system: Initial system configuration
    :type initial_energy_system: EnergySystem
    :param weights: Optimization weights dict with 'WGK_Gesamt', 'specific_emissions_Gesamt', 'primärenergiefaktor_Gesamt'
    :type weights: dict
    :param num_restarts: Number of random restart runs, defaults to 5
    :type num_restarts: int, optional

    .. note::
       Uses SLSQP with random restarts for multi-objective optimization.
    """

    def __init__(self, initial_energy_system: 'EnergySystem', weights: Dict[str, float], num_restarts: int = 5):
        """
        Initialize multi-objective optimizer.

        :param initial_energy_system: Initial system configuration
        :type initial_energy_system: EnergySystem
        :param weights: Optimization weights
        :type weights: dict
        :param num_restarts: Number of random restarts, defaults to 5
        :type num_restarts: int

        :raises ValueError: If required weights missing or negative
        """
        self.initial_energy_system = initial_energy_system
        self.weights = weights
        self.num_restarts = num_restarts
        
        # Validate optimization weights
        required_weights = ['WGK_Gesamt', 'specific_emissions_Gesamt', 'primärenergiefaktor_Gesamt']
        for weight_key in required_weights:
            if weight_key not in weights:
                raise ValueError(f"Required weight '{weight_key}' missing from weights dictionary")
            if weights[weight_key] < 0:
                raise ValueError(f"Weight '{weight_key}' must be non-negative")

    def optimize(self) -> 'EnergySystem':
        """
        Perform multi-objective optimization with random restarts.

        :return: Optimized energy system
        :rtype: EnergySystem

        :raises ValueError: If no optimization parameters available
        :raises RuntimeError: If optimization fails in all restarts
        """
        best_solution = None
        best_objective_value = float('inf')

        # Validate that technologies have optimization parameters
        has_optimization_params = False
        for tech in self.initial_energy_system.technologies:
            idx = tech.name.split("_")[-1] if "_" in tech.name else "0"
            tech_values, tech_variables, tech_bounds = tech.add_optimization_parameters(idx)
            if tech_values and tech_variables and tech_bounds:
                has_optimization_params = True
                break

        if not has_optimization_params:
            raise ValueError("No optimization parameters available. Energy system optimization requires "
                           "technologies with configurable parameters (e.g., capacity, storage volume).")

        for restart in range(self.num_restarts):
            print(f"Starting optimization run {restart + 1}/{self.num_restarts}")

            # Create fresh copy for this optimization run
            self.energy_system_copy = self.initial_energy_system.copy()

            # Extract optimization parameters from all technologies
            initial_values = []
            bounds = []
            variables_mapping = {}

            for tech in self.energy_system_copy.technologies:
                idx = tech.name.split("_")[-1] if "_" in tech.name else "0"
                tech_values, tech_variables, tech_bounds = tech.add_optimization_parameters(idx)
                
                # Skip technologies without optimization parameters
                if not tech_values or not tech_variables or not tech_bounds:
                    continue

                initial_values.extend(tech_values)
                bounds.extend(tech_bounds)

                # Map variables to technology for solution interpretation
                for var in tech_variables:
                    variables_mapping[var] = tech.name
            
            variables_order = list(variables_mapping.keys())

            if not initial_values:
                print("No optimization parameters found. Skipping optimization.")
                return self.initial_energy_system

            # Generate random initial values within parameter bounds
            random_initial_values = [
                np.random.uniform(low=bound[0], high=bound[1]) if bound[1] > bound[0] else bound[0]
                for bound in bounds
            ]

            print(f"Initial values for restart {restart + 1}: {random_initial_values}")

            def objective_function(variables):
                """
                Multi-objective function for energy system optimization.

                Parameters
                ----------
                variables : array_like
                    Technology parameter values for evaluation.

                Returns
                -------
                float
                    Weighted sum of optimization criteria.
                """
                try:
                    # Create fresh copy for objective evaluation
                    fresh_energy_system = self.energy_system_copy.copy()

                    # Calculate energy system performance with given parameters
                    results = fresh_energy_system.calculate_mix(variables, variables_order)

                    # Calculate weighted multi-objective value
                    weighted_sum = (
                        self.weights['WGK_Gesamt'] * results['WGK_Gesamt'] +
                        self.weights['specific_emissions_Gesamt'] * results['specific_emissions_Gesamt'] +
                        self.weights['primärenergiefaktor_Gesamt'] * results['primärenergiefaktor_Gesamt']
                    )
                    
                    return weighted_sum

                except Exception as e:
                    print(f"Error in objective function evaluation: {e}")
                    return float('inf')  # Return large value for infeasible solutions

            # Perform optimization with SLSQP algorithm
            try:
                result = scipy_minimize(
                    objective_function, 
                    random_initial_values, 
                    method='SLSQP', 
                    bounds=bounds,
                    options={'maxiter': 1000, 'ftol': 1e-6}
                )

                # Check if current solution is better than previous best
                if result.success and result.fun < best_objective_value:
                    best_objective_value = result.fun
                    best_solution = result
                    print(f"New best solution found in restart {restart + 1}: {result.fun:.4f}")

            except Exception as e:
                print(f"Optimization failed in restart {restart + 1}: {e}")
                continue

        # Apply best solution if found
        if best_solution is not None:
            print(f"Optimization completed successfully. Best objective value: {best_objective_value:.4f}")
            
            # Apply optimal parameters to energy system
            for tech in self.energy_system_copy.technologies:
                idx = tech.name.split("_")[-1] if "_" in tech.name else "0"
                tech.set_parameters(best_solution.x, variables_order, idx)

            # Store optimization results
            self.best_solution = best_solution
            self.best_objective_value = best_objective_value

            return self.energy_system_copy
        else:
            raise RuntimeError("Optimization failed to find valid solution in all restart attempts. "
                             "Consider adjusting parameter bounds, weights, or increasing restart attempts.")

    def get_optimization_summary(self) -> Dict[str, Union[float, int, bool]]:
        """
        Generate optimization summary report.

        :return: Summary dict with success, best_objective_value, num_restarts, etc.
        :rtype: dict
        """
        if hasattr(self, 'best_solution') and self.best_solution is not None:
            return {
                'success': True,
                'best_objective_value': self.best_objective_value,
                'num_restarts': self.num_restarts,
                'optimization_message': f"Optimization successful with {self.num_restarts} restarts",
                'solution_variables': self.best_solution.x.tolist(),
                'function_evaluations': getattr(self.best_solution, 'nfev', 0),
                'iterations': getattr(self.best_solution, 'nit', 0)
            }
        else:
            return {
                'success': False,
                'best_objective_value': float('inf'),
                'num_restarts': self.num_restarts,
                'optimization_message': "Optimization failed to find valid solution",
                'solution_variables': [],
                'function_evaluations': 0,
                'iterations': 0
            }