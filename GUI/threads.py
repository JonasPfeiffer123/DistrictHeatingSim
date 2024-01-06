import geopandas as gpd
import os
import numpy as np

from PyQt5.QtCore import QThread, pyqtSignal
import traceback

from main import import_TRY

from net_generation.import_and_create_layers import generate_and_export_layers

from net_simulation_pandapipes.net_simulation import initialize_net_geojson, generate_profiles_from_geojson, thermohydraulic_time_series_net_calculation, import_results_csv
from net_simulation_pandapipes.stanet_import_pandapipes import create_net_from_stanet_csv

from heat_generators.heat_generator_classes import Berechnung_Erzeugermix, optimize_mix

from geocoding.geocodingETRS89 import process_data

class NetInitializationGEOJSONThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type, calc_method):
        super().__init__()
        self.gdf_vl = gdf_vl
        self.gdf_rl = gdf_rl
        self.gdf_HAST = gdf_HAST
        self.gdf_WEA = gdf_WEA
        self.building_type = building_type
        self.calc_method = calc_method

    def run(self):
        try:
            # geojson
            self.yearly_time_steps, self.waerme_ges_W, self.max_waerme_ges_W = generate_profiles_from_geojson(self.gdf_HAST, self.building_type, self.calc_method)
            self.net = initialize_net_geojson(self.gdf_vl, self.gdf_rl, self.gdf_HAST, self.gdf_WEA, self.max_waerme_ges_W)
            
            self.calculation_done.emit((self.net, self.yearly_time_steps, self.waerme_ges_W))
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Warten auf das sichere Beenden des Threads

class NetInitializationSTANETThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def run(self):
        try:
            # STANET
            self.net, self.yearly_time_steps, self.waerme_ges_W = create_net_from_stanet_csv(self.filename)

            self.calculation_done.emit((self.net, self.yearly_time_steps, self.waerme_ges_W))
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Warten auf das sichere Beenden des Threads

class NetCalculationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, net, yearly_time_steps, waerme_ges_W, calc1, calc2):
        super().__init__()
        self.net = net
        self.yearly_time_steps = yearly_time_steps
        self.waerme_ges_W = waerme_ges_W
        self.calc1 = calc1
        self.calc2 = calc2

    def run(self):
        try:
            self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net_calculation(self.net, self.yearly_time_steps, self.waerme_ges_W, self.calc1, self.calc2)

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
                    'name': os.path.basename(filename),
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

    def __init__(self, filename, load_scale_factor, try_filename, cop_filename, gaspreis, strompreis, holzpreis, BEW, tech_objects, optimize):
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

    def run(self):
        try:
            # Hier beginnt die Berechnung
            time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump = import_results_csv(self.filename)
            calc1, calc2 = 0, len(time_steps)

            qext_kW *= self.load_scale_factor

            initial_data = time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump

            TRY = import_TRY(self.try_filename)
            COP_data = np.genfromtxt(self.cop_filename, delimiter=';')

            if self.optimize:
                self.tech_objects = optimize_mix(self.tech_objects, initial_data, calc1, calc2, TRY, COP_data, self.gaspreis, self.strompreis, self.holzpreis, self.BEW)

            WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, Wärmemengen, WGK, Anteile, specific_emissions = Berechnung_Erzeugermix(self.tech_objects, initial_data, calc1, calc2, TRY, COP_data, self.gaspreis, self.strompreis, self.holzpreis, self.BEW)

            result = WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, Wärmemengen, WGK, Anteile, specific_emissions, self.tech_objects, time_steps
            self.calculation_done.emit(result)  # Ergebnis zurückgeben
        except Exception as e:
            self.calculation_error.emit(str(e))  # Fehler zurückgeben