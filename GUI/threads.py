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

from scipy.interpolate import RegularGridInterpolator

class NetInitializationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, *args, pipe_creation_mode="type", **kwargs):
        super().__init__()
        self.args = args
        self.pipe_creation_mode = pipe_creation_mode
        self.kwargs = kwargs

    def run(self):
        try:
            if self.kwargs.get("import_type") == "GeoJSON":
                self.initialize_geojson()
            elif self.kwargs.get("import_type") == "Stanet":
                self.initialize_stanet()
            else:
                raise ValueError("Unbekannter Importtyp")

            # Gemeinsame Schritte für beide Importtypen
            self.net = self.common_net_initialization(self.net, self.max_waerme_hast_ges_W)
            self.calculation_done.emit((self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.return_temperature, self.supply_temperature_curve, self.return_temperature_curve))

        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def COP_WP(self, VLT_L, QT):
            # Interpolationsformel für den COP
            values = np.genfromtxt('C:/Users/username/heating_network_generation/heat_generators/Kennlinien WP.csv', delimiter=';')
            row_header = values[0, 1:]  # Vorlauftemperaturen
            col_header = values[1:, 0]  # Quelltemperaturen
            values = values[1:, 1:]
            f = RegularGridInterpolator((col_header, row_header), values, method='linear')

            # technische Grenze der Wärmepumpe ist Temperaturhub von 75 °C
            VLT_L = np.minimum(VLT_L, 75+QT)

            # Überprüfen, ob QT eine Zahl oder ein Array ist
            if np.isscalar(QT):
                # Wenn QT eine Zahl ist, erstellen wir ein Array mit dieser Zahl
                QT_array = np.full_like(VLT_L, QT)
            else:
                # Wenn QT bereits ein Array ist, prüfen wir, ob es die gleiche Länge wie VLT_L hat
                if len(QT) != len(VLT_L):
                    raise ValueError("QT muss entweder eine einzelne Zahl oder ein Array mit der gleichen Länge wie VLT_L sein.")
                QT_array = QT

            # Berechnung von COP_L
            COP_L = f(np.column_stack((QT_array, VLT_L)))

            return COP_L, VLT_L
    
    def initialize_geojson(self):
        self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, self.calc_method, self.building_type, self.return_temperature, self.supply_temperature, \
            self.flow_pressure_pump, self.lift_pressure_pump, self.netconfiguration, self.pipetype, self.v_max_pipe, self.material_filter, self.insulation_filter = self.args

        self.vorlauf = gpd.read_file(self.vorlauf, driver='GeoJSON')
        self.ruecklauf = gpd.read_file(self.ruecklauf, driver='GeoJSON')
        self.hast = gpd.read_file(self.hast, driver='GeoJSON')
        self.erzeugeranlagen = gpd.read_file(self.erzeugeranlagen, driver='GeoJSON')
        print(f"Vorlauftemperatur Netz: {self.supply_temperature} °C")

        self.supply_temperature_buildings = self.hast["VLT_max"].values.astype(float)
        print(f"Vorlauftemperatur Gebäude: {self.supply_temperature_buildings} °C")

        dT_RL = 5 # K
        self.return_temperature_buildings = self.hast["RLT_max"].values.astype(float) + dT_RL
        print(f"Rücklauftemperatur Gebäude: {self.return_temperature_buildings} °C")

        if self.return_temperature == None:
            self.return_temperature = self.return_temperature_buildings
            print(f"Rücklauftemperatur HAST: {self.return_temperature} °C")
        else:
            self.return_temperature = np.full_like(self.return_temperature_buildings, self.return_temperature)
            print(f"Rücklauftemperatur HAST: {self.return_temperature} °C")

        if np.any(self.return_temperature >= self.supply_temperature):
            raise ValueError("Rücklauftemperatur darf nicht höher als die Vorlauftemperatur sein. Bitte überprüfen sie die Eingaben.")

        self.yearly_time_steps, self.waerme_gebaeude_ges_W, self.max_waerme_gebaeude_ges_W, self.supply_temperature_curve, self.return_temperature_curve = generate_profiles_from_geojson(self.hast, self.building_type, self.calc_method, self.supply_temperature_buildings, self.return_temperature_buildings)

        self.waerme_hast_ges_W = []
        self.max_waerme_hast_ges_W = []
        if self.netconfiguration == "kaltes Netz":
            self.COP, _ = self.COP_WP(self.supply_temperature_buildings, self.return_temperature)
            print(f"COP dezentrale Wärmepumpen Gebäude: {self.COP}")

            for waerme_gebaeude, leistung_gebaeude, cop in zip(self.waerme_gebaeude_ges_W, self.max_waerme_gebaeude_ges_W, self.COP):
                self.strom_wp = waerme_gebaeude/cop
                self.waerme_hast = waerme_gebaeude - self.strom_wp
                self.waerme_hast_ges_W.append(self.waerme_hast)

                self.stromleistung_wp = leistung_gebaeude/cop
                self.waerme_leistung_hast = leistung_gebaeude - self.stromleistung_wp
                self.max_waerme_hast_ges_W.append(self.waerme_leistung_hast)

            self.waerme_hast_ges_W = np.array(self.waerme_hast_ges_W)
            self.max_waerme_hast_ges_W = np.array(self.max_waerme_hast_ges_W)

        else:
            self.waerme_hast_ges_W = self.waerme_gebaeude_ges_W
            self.max_waerme_hast_ges_W = self.max_waerme_gebaeude_ges_W

        self.net = create_network(self.vorlauf, self.ruecklauf, self.hast, self.erzeugeranlagen, self.max_waerme_hast_ges_W, self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump, self.pipetype)

    def initialize_stanet(self):
        self.stanet_csv, self.return_temperature, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump = self.args
        self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.max_waerme_hast_ges_W = create_net_from_stanet_csv(self.stanet_csv, self.supply_temperature, self.flow_pressure_pump, self.lift_pressure_pump)

    def common_net_initialization(self, net, max_waerme_ges_W):
        # Gemeinsame Schritte nach der Netzinitialisierung
        net = create_controllers(net, max_waerme_ges_W, self.return_temperature)
        net = correct_flow_directions(net)
        net = init_timeseries_opt(net, max_waerme_ges_W, return_temperature=self.return_temperature)

        if self.kwargs.get("import_type") == "GeoJSON":
            if self.pipe_creation_mode == "diameter":
                net = optimize_diameter_parameters(net, element="pipe", v_max=1)

            if self.pipe_creation_mode == "type":
                net = optimize_diameter_types(net, v_max=self.v_max_pipe, material_filter=self.material_filter, insulation_filter=self.insulation_filter)

        net = optimize_diameter_parameters(net, element="heat_exchanger", v_max=1.5)
        net = optimize_diameter_parameters(net, element="flow_control", v_max=1.5)
        
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
            self.calculation_error.emit(e)  # Fehler zurückgeben

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
            time_steps, qext_kW, waerme_ges_W, flow_temp_circ_pump, return_temp_circ_pump, mass_flow_circ_pump, deltap_circ_pump, return_pressure_circ_pump, flow_pressure_circ_pump = import_results_csv(self.filename)
            calc1, calc2 = 0, len(time_steps)

            print(time_steps)
            qext_kW *= self.load_scale_factor

            initial_data = time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump

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