import geopandas as gpd
import os

from PyQt5.QtCore import QThread, pyqtSignal
import traceback

from main import initialize_net_profile_calculation, thermohydraulic_time_series_net_calculation
from net_generation.import_and_create_layers import generate_and_export_layers

class NetInitializationThread(QThread):
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
            self.net, self.yearly_time_steps, self.waerme_ges_W = initialize_net_profile_calculation(self.gdf_vl, self.gdf_rl, self.gdf_HAST, self.gdf_WEA, self.building_type, self.calc_method)
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

    def __init__(self, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type, calc_method, calc1, calc2):
        super().__init__()
        self.gdf_vl = gdf_vl
        self.gdf_rl = gdf_rl
        self.gdf_HAST = gdf_HAST
        self.gdf_WEA = gdf_WEA
        self.building_type = building_type
        self.calc_method = calc_method
        self.calc1 = calc1
        self.calc2 = calc2

    def run(self):
        try:
            self.net, self.yearly_time_steps, self.waerme_ges_W = initialize_net_profile_calculation(self.gdf_vl, self.gdf_rl, self.gdf_HAST, self.gdf_WEA, self.building_type, self.calc_method)

            self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net_calculation(self.net, self.yearly_time_steps, self.waerme_ges_W, self.calc1, self.calc2)

            self.calculation_done.emit((self.time_steps, self.net, self.net_results))
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
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, m, filename, color):
        super().__init__()
        self.m = m
        self.filename = filename
        self.color = color

    def run(self):
        try:
            gdf = gpd.read_file(self.filename)
            # Bereiten Sie die Daten vor, aber fügen Sie sie nicht hier zur GUI hinzu.
            geojson_data = {
                'gdf': gdf,
                'name': os.path.basename(self.filename),
                'style': {
                    'fillColor': self.color,
                    'color': self.color,
                    'weight': 1.5,
                    'fillOpacity': 0.5,
                }
            }

            self.calculation_done.emit((geojson_data))
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Warten auf das sichere Beenden des Threads