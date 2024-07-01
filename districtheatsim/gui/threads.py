import numpy as np
import geopandas as gpd
import traceback

from PyQt5.QtCore import QThread, pyqtSignal

from net_generation.import_and_create_layers import generate_and_export_layers

from net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
from net_simulation_pandapipes.pp_net_time_series_simulation import thermohydraulic_time_series_net, import_results_csv, time_series_preprocessing
from net_simulation_pandapipes.stanet_import_pandapipes import create_net_from_stanet_csv
from net_simulation_pandapipes.utilities import net_optimization

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

    def __init__(self, *args, mass_flow_secondary_producers=0.1, **kwargs):
        super().__init__()
        self.args = args
        self.mass_flow_secondary_producers = mass_flow_secondary_producers
        self.kwargs = kwargs

    def run(self):
        try:
            if self.kwargs.get("import_type") == "GeoJSON":
                self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, self.TRY_filename, self.COP_filename, self.calc_method, self.building_type, \
                self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump, \
                self.netconfiguration, self.pipetype, self.v_max_pipe, self.material_filter, self.insulation_filter, \
                self.base_path, self.dT_RL, self.v_max_heat_consumer, self.DiameterOpt_ckecked = self.args

                self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.return_temperature, \
                self.supply_temperature_buildings, self.return_temperature_buildings, self.supply_temperature_building_curve, \
                self.return_temperature_building_curve, strombedarf_hast_ges_W, max_el_leistung_hast_ges_W  = initialize_geojson(self.vorlauf, self.ruecklauf, self.hast, \
                                                                             self.erzeugeranlagen, self.TRY_filename, self.COP_filename, self.calc_method, self.building_type, \
                                                                             self.return_temperature, self.supply_temperature, \
                                                                             self.flow_pressure_pump, self.lift_pressure_pump, \
                                                                             self.netconfiguration, self.pipetype, self.dT_RL, \
                                                                             self.v_max_pipe, self.material_filter, self.insulation_filter, \
                                                                             self.v_max_heat_consumer, self.mass_flow_secondary_producers)
            
            elif self.kwargs.get("import_type") == "Stanet":
                self.stanet_csv, self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump = self.args
                self.initialize_stanet()
            else:
                raise ValueError("Unbekannter Importtyp")

            # Common steps for both import types
            if self.DiameterOpt_ckecked == True:
                self.net = net_optimization(self.net, self.v_max_pipe, self.v_max_heat_consumer, self.material_filter, self.insulation_filter)
            
            self.calculation_done.emit((self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.return_temperature, self.supply_temperature_buildings, \
                                        self.return_temperature_buildings, self.supply_temperature_building_curve, self.return_temperature_building_curve, \
                                        strombedarf_hast_ges_W, max_el_leistung_hast_ges_W))

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
                 return_temperature_buildings, supply_temperature_buildings_curve, return_temperature_buildings_curve, dT_RL=5, netconfiguration=None, building_temp_checked=False, TRY_filename=None, COP_filename=None):
        
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
        self.TRY_filename = TRY_filename
        self.COP_filename = COP_filename
    
    def run(self):
        try:
            self.waerme_hast_ges_W, self.strom_hast_ges_W, self.return_temperature  = time_series_preprocessing(self.supply_temperature, self.return_temperature, self.supply_temperature_buildings, \
                                                                                                                self.return_temperature_buildings, self.building_temp_checked, self.netconfiguration, \
                                                                                                                self.total_heat_W, self.return_temperature_buildings_curve, self.dT_RL, 
                                                                                                                self.supply_temperature_buildings_curve, self.COP_filename)

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
            generate_and_export_layers(self.inputs["streetLayer"], self.inputs["dataCsv"], self.inputs["coordinates"], self.base_path, algorithm=self.inputs["generation_mode"])

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

    def __init__(self, filename, load_scale_factor, TRY_data, COP_data, gas_price, electricity_price, wood_price, BEW, tech_objects, optimize, interest_on_capital, price_increase_rate, period, wage):
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

    def run(self):
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
                                            kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate, betrachtungszeitraum=self.period, stundensatz=self.wage)

            result = Berechnung_Erzeugermix(self.tech_objects, initial_data, calc1, calc2, self.TRY_data, self.COP_data, self.gas_price, self.electricity_price, self.wood_price, self.BEW, \
                                            kapitalzins=self.interest_on_capital, preissteigerungsrate=self.price_increase_rate, betrachtungszeitraum=self.period, stundensatz=self.wage)
            result["waerme_ges_kW"] = waerme_ges_kW
            result["strom_wp_kW"] = strom_wp_kW
            
            self.calculation_done.emit(result)
        except Exception as e:
            tb = traceback.format_exc()  # Gibt den kompletten Traceback als String zurück
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))
