"""
Net Generation Threads Module
=============================

Threading classes for network generation, file import, and geocoding operations.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
"""

import geopandas as gpd
import traceback

from PyQt6.QtCore import QThread, pyqtSignal

from districtheatingsim.net_generation.osmnx_steiner_network import generate_and_export_osmnx_layers
from districtheatingsim.net_generation.import_and_create_layers import generate_and_export_layers
from districtheatingsim.geocoding.geocoding import process_data

class NetGenerationThread(QThread):
    """
    Thread for generating district heating networks.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, inputs, base_path):
        """
        Initialize network generation thread.

        Parameters
        ----------
        inputs : dict
            Input parameters for network generation.
        base_path : str
            Base path for file operations.
        """
        super().__init__()
        self.inputs = inputs
        self.base_path = base_path

    def run(self):
        """Run network generation process."""
        try:
            print("Starting network generation thread...")
            print(f"Generation mode: {self.inputs['generation_mode']}")
            print(f"Coordinates: {self.inputs['coordinates']}")
            
            if self.inputs["generation_mode"] == "OSMnx":
                # Use OSMnx-based network generation
                generate_and_export_osmnx_layers(
                    osm_street_layer_geojson_file_name=self.inputs.get("streetLayer", ""),
                    data_csv_file_name=self.inputs["dataCsv"],
                    coordinates=self.inputs["coordinates"],
                    base_path=self.base_path,
                    algorithm=self.inputs["generation_mode"],
                    custom_filter=self.inputs.get("custom_filter", None)
                )
            else:
                # Use traditional MST/Steiner algorithms
                generate_and_export_layers(
                    osm_street_layer_geojson_file_name=self.inputs["streetLayer"],
                    data_csv_file_name=self.inputs["dataCsv"],
                    coordinates=self.inputs["coordinates"],
                    base_path=self.base_path,
                    algorithm=self.inputs["generation_mode"]
                )

            self.calculation_done.emit(())
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ERROR in network generation: {error_msg}")
            self.calculation_error.emit(Exception(error_msg))

    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()


class OSMStreetDownloadThread(QThread):
    """
    Thread for downloading OSM street data.
    """
    download_done = pyqtSignal(str)  # Emits filepath when done
    download_error = pyqtSignal(str)
    
    def __init__(self, download_func, *args, **kwargs):
        """
        Initialize OSM street download thread.
        
        Parameters
        ----------
        download_func : callable
            The download function to execute.
        *args : tuple
            Positional arguments for download_func.
        **kwargs : dict
            Keyword arguments for download_func.
        """
        super().__init__()
        self.download_func = download_func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        """Run download process."""
        try:
            filepath = self.download_func(*self.args, **self.kwargs)
            self.download_done.emit(filepath)
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Fehler beim Download:\n{str(e)}\n\n{tb}"
            self.download_error.emit(error_message)


class OSMBuildingDownloadThread(QThread):
    """
    Thread for downloading OSM building data.
    """
    download_done = pyqtSignal(str, int)  # Emits filepath and building count when done
    download_error = pyqtSignal(str)
    
    def __init__(self, download_func, *args, **kwargs):
        """
        Initialize OSM building download thread.
        
        Parameters
        ----------
        download_func : callable
            The download function to execute.
        *args : tuple
            Positional arguments for download_func.
        **kwargs : dict
            Keyword arguments for download_func.
        """
        super().__init__()
        self.download_func = download_func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        """Run download process."""
        try:
            filepath, building_count = self.download_func(*self.args, **self.kwargs)
            self.download_done.emit(filepath, building_count)
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Fehler beim Download:\n{str(e)}\n\n{tb}"
            self.download_error.emit(error_message)

class FileImportThread(QThread):
    """
    Thread for importing geospatial files.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, m, filenames, color):
        """
        Initialize file import thread.

        Parameters
        ----------
        m : object
            Map object for visualization.
        filenames : list
            List of filenames to import.
        color : str
            Color for visualization styling.
        """
        super().__init__()
        self.m = m
        self.filenames = filenames
        self.color = color

    def run(self):
        """Run file import process."""
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
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()

class GeocodingThread(QThread):
    """
    Thread for geocoding address data.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, inputfilename):
        """
        Initialize geocoding thread.

        Parameters
        ----------
        inputfilename : str
            Input filename for geocoding data.
        """
        super().__init__()
        self.inputfilename = inputfilename

    def run(self):
        """Run geocoding process."""
        try:
            process_data(self.inputfilename)
            self.calculation_done.emit((self.inputfilename))
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))

    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()


class GeoJSONToCSVThread(QThread):
    """
    Thread for converting GeoJSON to CSV with reverse geocoding.
    """
    progress_update = pyqtSignal(int, int, str)  # current, total, message
    calculation_done = pyqtSignal(str)  # output_file_path
    calculation_error = pyqtSignal(str)
    
    def __init__(self, geojson_file_path, output_file_path, default_values, model):
        """
        Initialize GeoJSON to CSV conversion thread.
        
        Parameters
        ----------
        geojson_file_path : str
            Input GeoJSON file path.
        output_file_path : str
            Output CSV file path.
        default_values : dict
            Default values for building parameters.
        model : ProjectModel
            Model instance with calculate_centroid method.
        """
        super().__init__()
        self.geojson_file_path = geojson_file_path
        self.output_file_path = output_file_path
        self.default_values = default_values
        self.model = model
    
    def run(self):
        """Run GeoJSON to CSV conversion with reverse geocoding."""
        import json
        import csv
        from geopy.geocoders import Nominatim
        from pyproj import Transformer
        
        try:
            with open(self.geojson_file_path, 'r') as geojson_file:
                data = json.load(geojson_file)
            
            total_features = len(data['features'])
            self.progress_update.emit(0, total_features, "Starte Konvertierung...")
            
            # Initialize geocoder and transformer once
            geolocator = Nominatim(user_agent="DistrictHeatingSim")
            transformer = Transformer.from_crs("epsg:25833", "epsg:4326", always_xy=True)
            
            with open(self.output_file_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
                fieldnames = ["Land", "Bundesland", "Stadt", "Adresse", "Wärmebedarf", "Gebäudetyp", "Subtyp", "WW_Anteil", "Typ_Heizflächen", 
                              "VLT_max", "Steigung_Heizkurve", "RLT_max", "Normaußentemperatur", "UTM_X", "UTM_Y"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
                writer.writeheader()
                
                for i, feature in enumerate(data['features']):
                    if self.isInterruptionRequested():
                        self.calculation_error.emit("Konvertierung abgebrochen")
                        return
                    
                    centroid = self.model.calculate_centroid(feature['geometry']['coordinates'])
                    
                    # Reverse geocode each building individually
                    land = self.default_values.get("Land", "Deutschland")
                    bundesland = self.default_values.get("Bundesland", "")
                    stadt = self.default_values.get("Stadt", "")
                    adresse = self.default_values.get("Adresse", "")
                    
                    if centroid[0] is not None and centroid[1] is not None:
                        try:
                            # Transform UTM to WGS84
                            lon, lat = transformer.transform(centroid[0], centroid[1])
                            
                            # Reverse geocode with timeout
                            location = geolocator.reverse(f"{lat}, {lon}", language="de", timeout=10)
                            
                            if location and location.raw.get('address'):
                                address_data = location.raw['address']
                                
                                # Extract address components
                                land = address_data.get('country', land)
                                bundesland = address_data.get('state', bundesland)
                                stadt = address_data.get('city') or address_data.get('town') or address_data.get('village') or address_data.get('municipality') or stadt
                                
                                # Build street address
                                street_parts = []
                                if 'road' in address_data:
                                    street_parts.append(address_data['road'])
                                if 'house_number' in address_data:
                                    street_parts.append(address_data['house_number'])
                                
                                if street_parts:
                                    adresse = " ".join(street_parts)
                                
                                self.progress_update.emit(i + 1, total_features, f"Gebäude {i+1}/{total_features}: {adresse}, {stadt}")
                        except Exception as e:
                            self.progress_update.emit(i + 1, total_features, f"Gebäude {i+1}/{total_features}: Geocoding fehlgeschlagen")
                            print(f"Reverse Geocoding für Gebäude {i+1} fehlgeschlagen: {e}")
                    else:
                        self.progress_update.emit(i + 1, total_features, f"Gebäude {i+1}/{total_features}: Keine Koordinaten")
                    
                    writer.writerow({
                        "Land": land,
                        "Bundesland": bundesland,
                        "Stadt": stadt,
                        "Adresse": adresse,
                        "Wärmebedarf": self.default_values["Wärmebedarf"],
                        "Gebäudetyp": self.default_values["Gebäudetyp"],
                        "Subtyp": self.default_values["Subtyp"],
                        "WW_Anteil": self.default_values["WW_Anteil"],
                        "Typ_Heizflächen": self.default_values["Typ_Heizflächen"],
                        "VLT_max": self.default_values["VLT_max"],
                        "Steigung_Heizkurve": self.default_values["Steigung_Heizkurve"],
                        "RLT_max": self.default_values["RLT_max"],
                        "Normaußentemperatur": self.default_values["Normaußentemperatur"],
                        "UTM_X": centroid[0],
                        "UTM_Y": centroid[1]
                    })
            
            self.calculation_done.emit(self.output_file_path)
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Fehler beim Erstellen der CSV-Datei:\n{str(e)}\n\n{tb}"
            self.calculation_error.emit(error_message)
    
    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()