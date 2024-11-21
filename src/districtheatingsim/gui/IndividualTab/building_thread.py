"""
Filename: building_thread.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
Description: Contains the threaded functionality function for calculating the heat generation mix.
"""

import numpy as np
import traceback
from PyQt5.QtCore import QThread, pyqtSignal
from districtheatingsim.heat_generators.heat_generation_mix import Berechnung_Erzeugermix, optimize_mix

class CalculateBuildingMixThread(QThread):
    """
    Thread for calculating the heat generation mix for individual buildings.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (Exception): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, building_id, building_data, tech_objects, TRY_data, COP_data, gas_price, electricity_price, wood_price, BEW, interest_on_capital, price_increase_rate, period, wage, optimize=False, weights=None):
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
            interest_on_capital (float): Interest rate on capital.
            price_increase_rate (float): Price increase rate.
            period (int): Analysis period.
            wage (float): Wage rate.
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
        self.interest_on_capital = interest_on_capital
        self.price_increase_rate = price_increase_rate
        self.period = period
        self.wage = wage
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

            initial_data = time_steps, last_profile, flow_temp, return_temp
            calc1, calc2 = 0, len(time_steps)

            if self.optimize:
                self.tech_objects = optimize_mix(
                    self.tech_objects, initial_data, calc1, calc2, self.TRY_data, self.COP_data,
                    self.gas_price, self.electricity_price, self.wood_price, self.BEW,
                    kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate,
                    betrachtungszeitraum=self.period, stundensatz=self.wage, weights=self.weights
                )

            result = Berechnung_Erzeugermix(
                self.tech_objects, initial_data, calc1, calc2, self.TRY_data, self.COP_data,
                self.gas_price, self.electricity_price, self.wood_price, self.BEW,
                kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate,
                betrachtungszeitraum=self.period, stundensatz=self.wage
            )

            result["building_id"] = self.building_id  # Include the building ID in the result
            self.calculation_done.emit(result)

        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Error calculating for building {self.building_id}: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))
