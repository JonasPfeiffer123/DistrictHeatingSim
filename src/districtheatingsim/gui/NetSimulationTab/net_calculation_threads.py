"""
Filename: net_calculation_threads.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains the threaded functionality functions for network initialization and calculation.
"""

import traceback
import numpy as np

from PyQt5.QtCore import QThread, pyqtSignal

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import thermohydraulic_time_series_net, time_series_preprocessing
from districtheatingsim.net_simulation_pandapipes.utilities import optimize_diameter_types

class NetInitializationThread(QThread):
    """
    Thread for initializing the network.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (str): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        """
        Initializes the NetInitializationThread.

        Args:
            *args: Positional arguments.
            mass_flow_secondary_producers (float): Mass flow of secondary producers. Defaults to 0.1.
            **kwargs: Keyword arguments.
        """
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """
        Runs the network initialization.
        """
        try:
            if self.kwargs.get("import_type") == "GeoJSON":
                self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, self.json_path, self.COP_filename, self.supply_temperature_heat_consumer, \
                self.return_temperature_heat_consumer, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump, \
                self.netconfiguration, self.pipetype, self.v_max_pipe, self.material_filter, self.dT_RL, self.DiameterOpt_ckecked, self.k_mm, \
                self.main_producer_location_index, self.secondary_producers = self.args

                self.results = (initialize_geojson(self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, self.json_path, self.COP_filename, 
                                                   self.supply_temperature_heat_consumer, self.return_temperature_heat_consumer, self.supply_temperature, 
                                                   self.flow_pressure_pump, self.lift_pressure_pump, self.netconfiguration, self.pipetype, self.dT_RL, 
                                                   self.v_max_pipe, self.material_filter, self.k_mm, self.main_producer_location_index, self.secondary_producers))
                
                self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.return_temperature_heat_consumer, self.supply_temperature_buildings, \
                self.return_temperature_buildings, self.supply_temperature_building_curve, self.return_temperature_building_curve, min_supply_temperature_heat_consumer, \
                strombedarf_hast_ges_W, max_el_leistung_hast_ges_W = self.results 
            else:
                raise ValueError("Unbekannter Importtyp")

            # Common steps for both import types
            if self.DiameterOpt_ckecked == True:
                self.net = optimize_diameter_types(self.net, self.v_max_pipe, self.material_filter, self.k_mm)
            
            self.calculation_done.emit((self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.supply_temperature_heat_consumer, self.return_temperature_heat_consumer, \
                                        self.supply_temperature_buildings, self.return_temperature_buildings, self.supply_temperature_building_curve, self.return_temperature_building_curve, \
                                        min_supply_temperature_heat_consumer, strombedarf_hast_ges_W, max_el_leistung_hast_ges_W))

        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())
    
    def stop(self):
        """
        Stops the thread.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()

class NetCalculationThread(QThread):
    """
    Thread for network calculations.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (str): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, net, yearly_time_steps, total_heat_W, calc1, calc2, supply_temperature, supply_temperature_heat_consumer, return_temperature_heat_consumer, supply_temperature_buildings, \
                 return_temperature_buildings, supply_temperature_buildings_curve, return_temperature_buildings_curve, min_supply_temperature_heat_consumer, dT_RL=5, netconfiguration=None, building_temp_checked=False, \
                    TRY_filename=None, COP_filename=None, secondary_producers=None):
        """
        Initializes the NetCalculationThread.

        Args:
            net: Network object.
            yearly_time_steps (array): Yearly time steps.
            total_heat_W (float): Total heat in watts.
            calc1 (float): Calculation parameter 1.
            calc2 (float): Calculation parameter 2.
            supply_temperature (float): Supply temperature in degrees Celsius.
            supply_temperature_heat_consumer (float): Supply temperature for heat consumers.
            return_temperature_heat_consumer (float): Return temperature for heat consumers.
            supply_temperature_buildings (float): Supply temperature for buildings.
            return_temperature_buildings (float): Return temperature for buildings.
            supply_temperature_buildings_curve (float): Supply temperature curve for buildings.
            return_temperature_buildings_curve (float): Return temperature curve for buildings.
            dT_RL (float, optional): Temperature difference for return line. Defaults to 5.
            netconfiguration (optional): Network configuration. Defaults to None.
            building_temp_checked (bool, optional): Whether building temperature is checked. Defaults to False.
            TRY_filename (str, optional): TRY filename. Defaults to None.
            COP_filename (str, optional): COP filename. Defaults to None.
            secondary_producers (list, optional): List of secondary producers. Defaults to None. Needs to be implemented in following work flow.
        """
        super().__init__()
        self.net = net
        self.yearly_time_steps = yearly_time_steps
        self.total_heat_W = total_heat_W
        self.calc1 = calc1
        self.calc2 = calc2
        self.supply_temperature = supply_temperature
        self.supply_temperature_heat_consumer = supply_temperature_heat_consumer
        self.return_temperature_heat_consumer = return_temperature_heat_consumer
        self.supply_temperature_buildings = supply_temperature_buildings
        self.return_temperature_buildings = return_temperature_buildings
        self.supply_temperature_buildings_curve = supply_temperature_buildings_curve
        self.return_temperature_buildings_curve = return_temperature_buildings_curve
        self.min_supply_temperature_heat_consumer = min_supply_temperature_heat_consumer
        self.dT_RL = dT_RL
        self.netconfiguration = netconfiguration
        self.building_temp_checked = building_temp_checked
        self.TRY_filename = TRY_filename
        self.COP_filename = COP_filename
        self.secondary_producers = secondary_producers
    
    def run(self):
        """
        Runs the network calculation.
        """
        try:
            self.waerme_hast_ges_W, self.strom_hast_ges_W, self.supply_temperature_heat_consumer, self.return_temperature_heat_consumer  = time_series_preprocessing(self.supply_temperature, self.supply_temperature_heat_consumer, \
                                                                                                                              self.return_temperature_heat_consumer, self.supply_temperature_buildings, \
                                                                                                                                self.return_temperature_buildings, self.building_temp_checked, \
                                                                                                                                self.netconfiguration, self.total_heat_W, \
                                                                                                                                self.return_temperature_buildings_curve, self.dT_RL, \
                                                                                                                                self.supply_temperature_buildings_curve, self.COP_filename)
            self.return_temperature_heat_consumer = np.array([np.full(self.calc2 - self.calc1, temp) for temp in self.return_temperature_heat_consumer])
            self.min_supply_temperature_heat_consumer = np.array([np.full(self.calc2 - self.calc1, temp) for temp in self.min_supply_temperature_heat_consumer])
            
            self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net(self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.calc1, \
                                                                                          self.calc2, self.supply_temperature, self.min_supply_temperature_heat_consumer, \
                                                                                        self.return_temperature_heat_consumer, self.secondary_producers)

            self.calculation_done.emit((self.time_steps, self.net, self.net_results, self.waerme_hast_ges_W, self.strom_hast_ges_W))
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        """
        Stops the thread.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate
