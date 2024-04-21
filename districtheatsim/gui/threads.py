import numpy as np
import geopandas as gpd
import traceback

from PyQt5.QtCore import QThread, pyqtSignal

from utilities.test_reference_year import import_TRY

from net_generation.import_and_create_layers import generate_and_export_layers

from net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
from net_simulation_pandapipes.pp_net_time_series_simulation import thermohydraulic_time_series_net, import_results_csv
from net_simulation_pandapipes.stanet_import_pandapipes import create_net_from_stanet_csv
from net_simulation_pandapipes.utilities import net_optimization, COP_WP

from heat_generators.heat_generator_classes import Berechnung_Erzeugermix, optimize_mix

from geocoding.geocodingETRS89 import process_data

import os
import sys

def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

class NetInitializationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            if self.kwargs.get("import_type") == "GeoJSON":
                self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, self.calc_method, self.building_type, \
                self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump, \
                self.netconfiguration, self.pipetype, self.v_max_pipe, self.material_filter, self.insulation_filter, \
                self.base_path, self.dT_RL, self.v_max_heat_exchanger, self.DiameterOpt_ckecked = self.args

                self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.return_temperature, \
                self.supply_temperature_buildings, self.return_temperature_buildings, self.supply_temperature_building_curve, \
                self.return_temperature_building_curve  = initialize_geojson(self.vorlauf, self.ruecklauf, self.hast, \
                                                                             self.erzeugeranlagen, self.calc_method, self.building_type, \
                                                                             self.return_temperature, self.supply_temperature, \
                                                                             self.flow_pressure_pump, self.lift_pressure_pump, \
                                                                             self.netconfiguration, self.pipetype, self.dT_RL)
            
            elif self.kwargs.get("import_type") == "Stanet":
                self.stanet_csv, self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump = self.args
                self.initialize_stanet()
            else:
                raise ValueError("Unbekannter Importtyp")

            # Common steps for both import types
            if self.DiameterOpt_ckecked == True:
                self.net = net_optimization(self.net, self.v_max_pipe, self.v_max_heat_exchanger, self.material_filter, self.insulation_filter)
            
            self.calculation_done.emit((self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.return_temperature, self.supply_temperature_buildings, \
                                        self.return_temperature_buildings, self.supply_temperature_building_curve, self.return_temperature_building_curve))

        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def initialize_stanet(self):
        self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.max_waerme_hast_ges_W = create_net_from_stanet_csv(self.stanet_csv, self.supply_temperature, \
                                                                                                                          self.flow_pressure_pump, self.lift_pressure_pump)
    
    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()

class NetCalculationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, net, yearly_time_steps, total_heat_W, calc1, calc2, supply_temperature, return_temperature, supply_temperature_buildings, \
                 return_temperature_buildings, supply_temperature_buildings_curve, return_temperature_buildings_curve, dT_RL=5, netconfiguration=None, building_temp_checked=False):
        
        super().__init__()
        self.net = net
        self.yearly_time_steps = yearly_time_steps
        self.total_heat_W = total_heat_W
        self.calc1 = calc1
        self.calc2 = calc2
        self.supply_temperature = supply_temperature
        self.return_temperature = return_temperature
        self.supply_temperature_buildings = supply_temperature_buildings
        self.return_temperature_buildings = return_temperature_buildings
        self.supply_temperature_buildings_curve = supply_temperature_buildings_curve
        self.return_temperature_buildings_curve = return_temperature_buildings_curve
        self.dT_RL = dT_RL
        self.netconfiguration = netconfiguration
        self.building_temp_checked = building_temp_checked
    
    def run(self):
        try:
            print(f"Vorlauftemperatur Netz: {self.supply_temperature} °C")
            print(f"Rücklauftemperatur HAST: {self.return_temperature} °C")
            print(f"Vorlauftemperatur Gebäude: {self.supply_temperature_buildings} °C")
            print(f"Rücklauftemperatur Gebäude: {self.return_temperature_buildings} °C")

            self.waerme_hast_ges_W = []
            self.strom_hast_ges_W = []
            
            # Building temperatures are not time varying, so return_temperature from initialization is used, no COP calculation is done
            if self.building_temp_checked == False and self.netconfiguration != "kaltes Netz":
                self.waerme_hast_ges_W = self.total_heat_W
                self.strom_hast_ges_W = None

            # Building temperatures are not time-varying, so return_temperature from initialization is used, a COP calculation is made with non-time-varying building temperatures
            elif self.building_temp_checked == False and self.netconfiguration == "kaltes Netz":
                self.COP, _ = COP_WP(self.supply_temperature_buildings, self.return_temperature)
                print(f"COP dezentrale Wärmepumpen Gebäude: {self.COP}")

                for waerme_gebaeude, cop in zip(self.total_heat_W, self.COP):
                    self.strom_wp = waerme_gebaeude/cop
                    self.waerme_hast = waerme_gebaeude - self.strom_wp

                    self.waerme_hast_ges_W.append(self.waerme_hast)
                    self.strom_hast_ges_W.append(self.strom_wp)

                self.waerme_hast_ges_W = np.array(self.waerme_hast_ges_W)
                self.strom_hast_ges_W = np.array(self.strom_hast_ges_W)
            
            # Building temperatures are time-varying, so return_temperature is determined from the building temperatures, there is no COP calculation
            if self.building_temp_checked == True and self.netconfiguration != "kaltes Netz":
                self.return_temperature = self.return_temperature_buildings_curve + self.dT_RL
                self.waerme_hast_ges_W = self.total_heat_W
                self.strom_hast_ges_W = None

            # Building temperatures are time-varying, so return_temperature is determined from the building temperatures, a COP calculation is made with time-varying building temperatures
            elif self.building_temp_checked == True and self.netconfiguration == "kaltes Netz":
                for st, rt, waerme_gebaeude in zip(self.supply_temperature_buildings_curve, self.return_temperature, self.total_heat_W):
                    cop, _ = COP_WP(st, rt)

                    self.strom_wp = waerme_gebaeude/cop
                    self.waerme_hast = waerme_gebaeude - self.strom_wp

                    self.waerme_hast_ges_W.append(self.waerme_hast)
                    self.strom_hast_ges_W.append(self.strom_wp)

                self.waerme_hast_ges_W = np.array(self.waerme_hast_ges_W)
                self.strom_hast_ges_W = np.array(self.strom_hast_ges_W)

            print(f"Rücklauftemperatur HAST: {self.return_temperature} °C")


            self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net(self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.calc1, \
                                                                                          self.calc2, self.supply_temperature, self.return_temperature)

            self.calculation_done.emit((self.time_steps, self.net, self.net_results, self.waerme_hast_ges_W, self.strom_hast_ges_W))
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate

class NetGenerationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, inputs, base_path):
        super().__init__()
        self.inputs = inputs
        self.base_path = base_path

    def run(self):
        try:
            generate_and_export_layers(self.inputs["streetLayer"], self.inputs["dataCsv"], float(self.inputs["xCoord"]), float(self.inputs["yCoord"]), self.base_path)

            self.calculation_done.emit(())
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate

class FileImportThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, m, filenames, color):
        super().__init__()
        self.m = m
        self.filenames = filenames
        self.color = color

    def run(self):
        try:
            results = {}
            for filename in self.filenames:
                gdf = gpd.read_file(filename)
                results[filename] = {
                    'gdf': gdf,
                    'name': filename,
                    'style': {
                        'fillColor': self.color,
                        'color': self.color,
                        'weight': 1.5,
                        'fillOpacity': 0.5,
                    }
                }
            self.calculation_done.emit(results)
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate

class GeocodingThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, inputfilename, outputfilename):
        super().__init__()
        self.inputfilename = inputfilename
        self.outputfilename = outputfilename

    def run(self):
        try:
            process_data(self.inputfilename, self.outputfilename)
            self.calculation_done.emit(())
        except Exception as e:
            self.calculation_error.emit(e)

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate

class CalculateMixThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, filename, load_scale_factor, try_filename, cop_filename, gas_price, electricity_price, wood_price, BEW, tech_objects, optimize, interest_on_capital, price_increase_rate, period):
        super().__init__()
        self.filename = filename
        self.load_scale_factor = load_scale_factor
        self.try_filename = try_filename
        self.cop_filename = cop_filename
        self.gas_price = gas_price
        self.electricity_price = electricity_price
        self.wood_price = wood_price
        self.BEW = BEW
        self.tech_objects = tech_objects
        self.optimize = optimize
        self.interest_on_capital = interest_on_capital
        self.price_increase_rate = price_increase_rate
        self.period = period

    def run(self):
        try:
            time_steps, qext_kW, waerme_ges_W, flow_temp_circ_pump, return_temp_circ_pump, mass_flow_circ_pump, deltap_circ_pump, return_pressure_circ_pump, flow_pressure_circ_pump = import_results_csv(self.filename)
            calc1, calc2 = 0, len(time_steps)

            qext_kW *= self.load_scale_factor

            initial_data = time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump

            TRY = import_TRY(self.try_filename)
            COP_data = np.genfromtxt(self.cop_filename, delimiter=';')

            if self.optimize:
                self.tech_objects = optimize_mix(self.tech_objects, initial_data, calc1, calc2, TRY, COP_data, self.gas_price, self.electricity_price, self.wood_price, self.BEW, \
                                            kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate, betrachtungszeitraum=self.period )

            result = Berechnung_Erzeugermix(self.tech_objects, initial_data, calc1, calc2, TRY, COP_data, self.gas_price, self.electricity_price, self.wood_price, self.BEW, \
                                            kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate, betrachtungszeitraum=self.period )

            self.calculation_done.emit(result)
        except Exception as e:
            tb = traceback.format_exc()  # Gibt den kompletten Traceback als String zurück
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))
