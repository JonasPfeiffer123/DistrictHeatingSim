"""
Filename: building_thread.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the threaded functionality function for calculating the heat generation mix.
"""

import numpy as np
import traceback
from PyQt5.QtCore import QThread, pyqtSignal
from districtheatingsim.heat_generators.heat_generation_mix import EnergySystem, EnergySystemOptimizer

class CalculateBuildingMixThread(QThread):
    """
    Thread for calculating the heat generation mix for individual buildings.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (Exception): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, building_id, building_data, tech_objects, TRY_data, COP_data, gas_price, electricity_price, wood_price, BEW, capital_interest_rate, inflation_rate, time_period, hourly_rate, optimize=False, weights=None):
        """
        Initializes the CalculateBuildingMixThread.

        Args:
            building_id (str): The ID of the building.
            building_data (dict): Dictionary containing the building's load profile and temperature data.
            tech_objects (list): List of technology objects.
            TRY_data: Test Reference Year data.
            COP_data: Coefficient of Performance data.
            gas_price (float): Gas price.
            electricity_price (float): Electricity price.
            wood_price (float): Wood price.
            BEW (str): Subsidy eligibility.
            capital_interest_rate (float): Interest rate on capital.
            price_increase_rateinflation_rate (float): Price increase rate.
            time_period (int): Analysis period.
            hourly_rate (float): Wage rate.
            optimize (bool, optional): Whether to optimize the mix. Defaults to False.
            weights (dict, optional): Weights for optimization criteria. Defaults to None.
        """
        super().__init__()
        self.building_id = building_id
        self.building_data = building_data
        self.tech_objects = tech_objects
        self.TRY_data = TRY_data
        self.COP_data = COP_data
        self.gas_price = gas_price
        self.electricity_price = electricity_price
        self.wood_price = wood_price
        self.BEW = BEW
        self.capital_interest_rate = capital_interest_rate
        self.inflation_rate = inflation_rate
        self.time_period = time_period
        self.hourly_rate = hourly_rate
        self.optimize = optimize
        self.weights = weights

    def run(self):
        """
        Runs the calculation for the heat generation mix for the building.
        """
        try:
            # Extract time_steps and other data directly from building_data
            time_steps = np.array(self.building_data['zeitschritte']).astype("datetime64")
            last_profile = np.array(self.building_data['wärme'])
            flow_temp = np.array(self.building_data['vorlauftemperatur'])
            return_temp = np.array(self.building_data['rücklauftemperatur'])

            self.economic_parameters = {
                "gas_price": self.gas_price,
                "electricity_price": self.electricity_price,
                "wood_price": self.wood_price,
                "capital_interest_rate": 1 + self.capital_interest_rate / 100,
                "inflation_rate": 1 + self.inflation_rate / 100,
                "time_period": self.time_period,
                "hourly_rate": self.hourly_rate,
                "subsidy_eligibility": self.BEW
            }

            energy_system = EnergySystem(
                time_steps=time_steps,
                load_profile=last_profile,
                VLT_L=flow_temp,
                RLT_L=return_temp,
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

            result["building_id"] = self.building_id  # Include the building ID in the result
            self.calculation_done.emit(result)

        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Error calculating for building {self.building_id}: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))
