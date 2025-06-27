"""
Net Generation Threads Module
=============================

Threading classes for network generation, file import, and geocoding operations.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
"""

import geopandas as gpd
import traceback

from PyQt5.QtCore import QThread, pyqtSignal

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
            print(self.inputs["coordinates"])
            generate_and_export_layers(self.inputs["streetLayer"], self.inputs["dataCsv"], self.inputs["coordinates"], self.base_path, algorithm=self.inputs["generation_mode"])

            self.calculation_done.emit(())
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

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