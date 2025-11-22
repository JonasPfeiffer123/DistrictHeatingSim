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
                    offset_angle=self.inputs.get("offset_angle", 0),
                    offset_distance=self.inputs.get("offset_distance", 0.5),
                    buffer_meters=self.inputs.get("buffer_meters", 500.0),
                    network_type=self.inputs.get("network_type", "drive_service"),
                    custom_filter=self.inputs.get("custom_filter", None),
                    node_threshold=self.inputs.get("node_threshold", 0.1),
                    remove_dead_ends_flag=self.inputs.get("remove_dead_ends", True),
                    target_crs=self.inputs.get("target_crs", "EPSG:25833")
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
            self.calculation_error.emit(error_msg)

    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()

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