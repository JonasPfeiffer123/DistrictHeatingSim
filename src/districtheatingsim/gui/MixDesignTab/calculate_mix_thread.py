"""
Filename: calculate_mix_thread.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the threaded functionality function for calculating the heat generation mix.
"""

import numpy as np
import traceback

from PyQt5.QtCore import QThread, pyqtSignal

from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import import_results_csv
from districtheatingsim.heat_generators.heat_generation_mix import EnergySystem

class CalculateMixThread(QThread):
    """
    Thread for calculating the heat generation mix.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (Exception): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, filename, load_scale_factor, TRY_data, COP_data, economic_parameters, tech_objects, optimize, weights):
        """
        Initializes the CalculateMixThread.

        Args:
            filename (str): Filename for the CSV containing the initial data.
            load_scale_factor (float): Scaling factor for the load.
            TRY_data: Test Reference Year data.
            COP_data: Coefficient of Performance data.
            economic_parameters (dict): Economic parameters.
            tech_objects (list): List of technology objects.
            optimize (bool): Whether to optimize the mix.
            weights (dict): Weights for optimization criteria.
        """
        super().__init__()
        self.filename = filename
        self.load_scale_factor = load_scale_factor
        self.TRY_data = TRY_data
        self.COP_data = COP_data
        self.economic_parameters = economic_parameters
        self.tech_objects = tech_objects
        self.optimize = optimize
        self.weights = weights

    def run(self):
        """
        Runs the heat generation mix calculation.
        """
        try:
            # Import data from the CSV file
            time_steps, waerme_ges_kW, strom_wp_kW, pump_results = import_results_csv(self.filename)

            # Collect qext_kW values from pump results
            qext_values = []
            for pump_type, pumps in pump_results.items():
                for idx, pump_data in pumps.items():
                    if 'qext_kW' in pump_data:
                        qext_values.append(pump_data['qext_kW'])
                    else:
                        print(f"Keine qext_kW Daten für {pump_type} Pumpe {idx}")

                    if pump_type == "Heizentrale Haupteinspeisung":
                        flow_temp_circ_pump = pump_data['flow_temp']
                        return_temp_circ_pump = pump_data['return_temp']

            if qext_values:
                qext_kW = np.sum(np.array(qext_values), axis=0)
            else:
                qext_kW = np.array([])

            qext_kW *= self.load_scale_factor

            # Create the energy system object
            energy_system = EnergySystem(
                time_steps=time_steps,
                load_profile=qext_kW,
                VLT_L=flow_temp_circ_pump,
                RLT_L=return_temp_circ_pump,
                TRY_data=self.TRY_data,
                COP_data=self.COP_data,
                economic_parameters=self.economic_parameters,
            )

            # Add technologies to the system
            for tech in self.tech_objects:
                energy_system.add_technology(tech)

            # Calculate the energy mix
            result = energy_system.calculate_mix()

            # Perform optimization if needed
            if self.optimize:
                print("Optimizing mix")
                optimized_energy_system = energy_system.optimize_mix(self.weights)
                print("Optimization done")

                # Calculate the energy mix
                result = optimized_energy_system.calculate_mix()

            ### To do: Return / save both energy_system and optimized_energy_system for further analysis ###

            # Add additional data to the result
            result["waerme_ges_kW"] = waerme_ges_kW
            result["strom_wp_kW"] = strom_wp_kW

            # Emit the calculation result
            self.calculation_done.emit(result)

        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))
