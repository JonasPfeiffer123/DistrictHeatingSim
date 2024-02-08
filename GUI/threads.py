import geopandas as gpd
import os
import numpy as np

from PyQt5.QtCore import QThread, pyqtSignal
import traceback

from main import import_TRY

from net_generation.import_and_create_layers import generate_and_export_layers
from net_simulation_pandapipes.net_simulation_calculation import *
from net_simulation_pandapipes.net_simulation import generate_profiles_from_geojson, thermohydraulic_time_series_net, import_results_csv, init_timeseries_opt
from net_simulation_pandapipes.stanet_import_pandapipes import create_net_from_stanet_csv

from heat_generators.heat_generator_classes import Berechnung_Erzeugermix, optimize_mix

from geocoding.geocodingETRS89 import process_data

class NetInitializationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, *args, diameter_mm=107.1, pipetype="KMR 100/250-2v", k=0.0470, alpha=0.61, pipe_creation_mode="type", **kwargs):
        super().__init__()
        self.args = args
        self.diameter_mm = diameter_mm
        self.pipetype = pipetype
        self.k = k
        self.alpha = alpha
        self.pipe_creation_mode = pipe_creation_mode
        self.kwargs = kwargs

    def run(self):
        try:
            if self.kwargs.get("import_type") == "GeoJSON":
                net, yearly_time_steps, qext_w, max_waerme_ges_W = self.initialize_geojson()
            elif self.kwargs.get("import_type") == "Stanet":
                net, yearly_time_steps, qext_w, max_waerme_ges_W = self.initialize_stanet()
            else:
                raise ValueError("Unbekannter Importtyp")

            # Gemeinsame Schritte für beide Importtypen
            net = self.common_net_initialization(net, max_waerme_ges_W)
            self.calculation_done.emit((net, yearly_time_steps, qext_w))

        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def initialize_geojson(self):
        self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, self.calc_method, self.building_type, self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump = self.args
        self.vorlauf = gpd.read_file(self.vorlauf, driver='GeoJSON')
        self.ruecklauf = gpd.read_file(self.ruecklauf, driver='GeoJSON')
        self.hast = gpd.read_file(self.hast, driver='GeoJSON')
        self.erzeugeranlagen = gpd.read_file(self.erzeugeranlagen, driver='GeoJSON')
        yearly_time_steps, waerme_ges_W, max_waerme_ges_W = generate_profiles_from_geojson(self.hast, self.building_type, self.calc_method)
        net = create_network(self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, max_waerme_ges_W, self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump)
        return net, yearly_time_steps, waerme_ges_W, max_waerme_ges_W

    def initialize_stanet(self):
        self.stanet_csv, self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump = self.args
        net, yearly_time_steps, waerme_ges_W, max_waerme_ges_W = create_net_from_stanet_csv(self.stanet_csv, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump)
        return net, yearly_time_steps, waerme_ges_W, max_waerme_ges_W

    def common_net_initialization(self, net, max_waerme_ges_W):
        # Gemeinsame Schritte nach der Netzinitialisierung
        net = create_controllers(net, max_waerme_ges_W, self.return_temperature)
        net = correct_flow_directions(net)
        net = init_timeseries_opt(net, max_waerme_ges_W, target_temperature=self.return_temperature)

        if self.kwargs.get("import_type") == "GeoJSON":
            if self.pipe_creation_mode == "diameter":
                net = optimize_diameter_parameters(net)

            if self.pipe_creation_mode == "type":
                net = optimize_diameter_types(net, v_max=1.0)

        net = optimize_diameter_parameters(net, element="heat_exchanger", v_max_he=2.2, v_min_he=1.8)
        net = optimize_diameter_parameters(net, element="flow_control", v_max_he=2.2, v_min_he=1.8)
        
        return net
    
    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()

class NetCalculationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, net, yearly_time_steps, waerme_ges_W, calc1, calc2, supply_temperature, return_temperature):
        
        super().__init__()
        self.net = net
        self.yearly_time_steps = yearly_time_steps
        self.waerme_ges_W = waerme_ges_W
        self.calc1 = calc1
        self.calc2 = calc2
        self.supply_temperature = supply_temperature
        self.return_temperature = return_temperature

    def run(self):
        try:
            self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net(self.net, self.yearly_time_steps, self.waerme_ges_W, self.calc1, self.calc2, self.supply_temperature, self.return_temperature)

            self.calculation_done.emit((self.time_steps, self.net, self.net_results, self.waerme_ges_W))
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Warten auf das sichere Beenden des Threads

class NetGenerationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
            generate_and_export_layers(self.inputs["streetLayer"], self.inputs["dataCsv"], float(self.inputs["xCoord"]), float(self.inputs["yCoord"]))

            self.calculation_done.emit(())
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Warten auf das sichere Beenden des Threads

class FileImportThread(QThread):
    calculation_done = pyqtSignal(object)  # Dies könnte ein Dictionary oder eine Liste von Ergebnissen sein
    calculation_error = pyqtSignal(str)

    def __init__(self, m, filenames, color):
        super().__init__()
        self.m = m
        self.filenames = filenames  # Eine Liste von Dateinamen
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
            self.wait()  # Warten auf das sichere Beenden des Threads

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
            self.calculation_done.emit(())    # Ergebnis zurückgeben
        except Exception as e:
            self.calculation_error.emit(str(e))  # Fehler zurückgeben

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Warten auf das sichere Beenden des Threads

class CalculateMixThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, filename, load_scale_factor, try_filename, cop_filename, gaspreis, strompreis, holzpreis, BEW, tech_objects, optimize, kapitalzins, preissteigerungsrate, betrachtungszeitraum):
        super().__init__()
        self.filename = filename
        self.load_scale_factor = load_scale_factor
        self.try_filename = try_filename
        self.cop_filename = cop_filename
        self.gaspreis = gaspreis
        self.strompreis = strompreis
        self.holzpreis = holzpreis
        self.BEW = BEW
        self.tech_objects = tech_objects
        self.optimize = optimize
        self.kapitalzins = kapitalzins
        self.preissteigerungsrate = preissteigerungsrate
        self.betrachtungszeitraum = betrachtungszeitraum

    def run(self):
        try:
            # Hier beginnt die Berechnung
            time_steps, Last_L, flow_temp_circ_pump, return_temp_circ_pump = import_results_csv(self.filename)
            calc1, calc2 = 0, len(time_steps)

            Last_L *= self.load_scale_factor

            initial_data = time_steps, Last_L, flow_temp_circ_pump, return_temp_circ_pump

            TRY = import_TRY(self.try_filename)
            COP_data = np.genfromtxt(self.cop_filename, delimiter=';')

            if self.optimize:
                self.tech_objects = optimize_mix(self.tech_objects, initial_data, calc1, calc2, TRY, COP_data, self.gaspreis, self.strompreis, self.holzpreis, self.BEW, \
                                            kapitalzins=self.kapitalzins, preissteigerungsrate=self.preissteigerungsrate, betrachtungszeitraum=self.betrachtungszeitraum)

            result = Berechnung_Erzeugermix(self.tech_objects, initial_data, calc1, calc2, TRY, COP_data, self.gaspreis, self.strompreis, self.holzpreis, self.BEW, \
                                            kapitalzins=self.kapitalzins, preissteigerungsrate=self.preissteigerungsrate, betrachtungszeitraum=self.betrachtungszeitraum)

            self.calculation_done.emit(result)  # Ergebnis zurückgeben
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())  # Fehler zurückgeben