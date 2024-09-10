"""
Filename: calculate_mix_thread.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
Description: Contains the threaded functionality function for calculating the heat generation mix.
"""

import numpy as np
import traceback

from PyQt5.QtCore import QThread, pyqtSignal

from net_simulation_pandapipes.pp_net_time_series_simulation import import_results_csv
from heat_generators.heat_generation_mix import Berechnung_Erzeugermix, optimize_mix

class CalculateMixThread(QThread):
    """
    Thread for calculating the heat generation mix.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (Exception): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, filename, load_scale_factor, TRY_data, COP_data, gas_price, electricity_price, wood_price, BEW, tech_objects, optimize, interest_on_capital, price_increase_rate, period, wage, weights):
        """
        Initializes the CalculateMixThread.

        Args:
            filename (str): Filename for the CSV containing the initial data.
            load_scale_factor (float): Scaling factor for the load.
            TRY_data: Test Reference Year data.
            COP_data: Coefficient of Performance data.
            gas_price (float): Gas price.
            electricity_price (float): Electricity price.
            wood_price (float): Wood price.
            BEW (str): Subsidy eligibility.
            tech_objects (list): List of technology objects.
            optimize (bool): Whether to optimize the mix.
            interest_on_capital (float): Interest rate on capital.
            price_increase_rate (float): Price increase rate.
            period (int): Analysis period.
            wage (float): Wage rate.
            weights (dict): Weights for optimization criteria.
        """
        super().__init__()
        self.filename = filename
        self.load_scale_factor = load_scale_factor
        self.TRY_data = TRY_data
        self.COP_data = COP_data
        self.gas_price = gas_price
        self.electricity_price = electricity_price
        self.wood_price = wood_price
        self.BEW = BEW
        self.tech_objects = tech_objects
        self.optimize = optimize
        self.interest_on_capital = interest_on_capital
        self.price_increase_rate = price_increase_rate
        self.period = period
        self.wage = wage
        self.weights = weights

    def run(self):
        """
        Runs the heat generation mix calculation.
        """
        try:
            time_steps, waerme_ges_kW, strom_wp_kW, pump_results = import_results_csv(self.filename)
            ### hier erstmal Vereinfachung, Temperaturen, Drücke der Hauptzenztrale, Leistungen addieren
            
            qext_values = []  # Diese Liste wird alle qext_kW Arrays speichern
            for pump_type, pumps in pump_results.items():
                for idx, pump_data in pumps.items():
                    if 'qext_kW' in pump_data:
                        qext_values.append(pump_data['qext_kW'])  # Nehmen wir an, dass dies numpy Arrays sind
                    else:
                        print(f"Keine qext_kW Daten für {pump_type} Pumpe {idx}")

                    if pump_type == "Heizentrale Haupteinspeisung":
                        flow_temp_circ_pump = pump_data['flow_temp']
                        return_temp_circ_pump = pump_data['return_temp']

            # Überprüfen, ob die Liste nicht leer ist
            if qext_values:
                # Summieren aller Arrays in der Liste zu einem Summenarray
                qext_kW = np.sum(np.array(qext_values), axis=0)
            else:
                qext_kW = np.array([])  # oder eine andere Form der Initialisierung, die in Ihrem Kontext sinnvoll ist
            
            calc1, calc2 = 0, len(time_steps)
            qext_kW *= self.load_scale_factor
            initial_data = time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump

            if self.optimize:
                self.tech_objects = optimize_mix(self.tech_objects, initial_data, calc1, calc2, self.TRY_data, self.COP_data, self.gas_price, self.electricity_price, self.wood_price, self.BEW, \
                                            kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate, betrachtungszeitraum=self.period, stundensatz=self.wage, weights=self.weights)

            result = Berechnung_Erzeugermix(self.tech_objects, initial_data, calc1, calc2, self.TRY_data, self.COP_data, self.gas_price, self.electricity_price, self.wood_price, self.BEW, \
                                            kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate, betrachtungszeitraum=self.period, stundensatz=self.wage)
            result["waerme_ges_kW"] = waerme_ges_kW
            result["strom_wp_kW"] = strom_wp_kW
            
            self.calculation_done.emit(result)
        except Exception as e:
            tb = traceback.format_exc()  # Returns the full traceback as a string
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))
