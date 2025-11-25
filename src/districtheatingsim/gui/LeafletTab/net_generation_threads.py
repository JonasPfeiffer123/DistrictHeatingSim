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