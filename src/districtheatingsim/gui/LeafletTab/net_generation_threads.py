"""
Filename: net_generation_thread.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
Description: Contains the threaded functionality function for generating the network.
"""

import geopandas as gpd
import traceback

from PyQt5.QtCore import QThread, pyqtSignal

from districtheatingsim.net_generation.import_and_create_layers import generate_and_export_layers
from districtheatingsim.geocoding.geocoding import process_data

class NetGenerationThread(QThread):
    """
    Thread for generating the network.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (str): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, inputs, base_path):
        """
        Initializes the NetGenerationThread.

        Args:
            inputs (dict): Input parameters for generating the network.
            base_path (str): Base path for file operations.
        """
        super().__init__()
        self.inputs = inputs
        self.base_path = base_path

    def run(self):
        """
        Runs the network generation.
        """
        try:
            print(self.inputs["coordinates"])
            generate_and_export_layers(self.inputs["streetLayer"], self.inputs["dataCsv"], self.inputs["coordinates"], self.base_path, algorithm=self.inputs["generation_mode"])

            self.calculation_done.emit(())
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        """
        Stops the thread.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate

class FileImportThread(QThread):
    """
    Thread for importing files.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (str): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, m, filenames, color):
        """
        Initializes the FileImportThread.

        Args:
            m: Map object for visualizing the imported files.
            filenames (list): List of filenames to import.
            color (str): Color for visualizing the imported files.
        """
        super().__init__()
        self.m = m
        self.filenames = filenames
        self.color = color

    def run(self):
        """
        Runs the file import.
        """
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
        """
        Stops the thread.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate

class GeocodingThread(QThread):
    """
    Thread for geocoding.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (Exception): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, inputfilename):
        """
        Initializes the GeocodingThread.

        Args:
            inputfilename (str): Filename for the input data to be geocoded.
        """
        super().__init__()
        self.inputfilename = inputfilename

    def run(self):
        """
        Runs the geocoding process.
        """
        try:
            process_data(self.inputfilename)
            self.calculation_done.emit((self.inputfilename))
        except Exception as e:
            tb = traceback.format_exc()  # Returns the full traceback as a string
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))

    def stop(self):
        """
        Stops the thread.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate