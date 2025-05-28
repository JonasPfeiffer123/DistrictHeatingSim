"""
Filename: net_calculation_threads.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-17
Description: Contains the threaded functionality functions for network initialization and calculation.
"""

import traceback
import numpy as np

from PyQt5.QtCore import QThread, pyqtSignal

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import thermohydraulic_time_series_net, time_series_preprocessing
from districtheatingsim.net_simulation_pandapipes.utilities import optimize_diameter_types

class NetInitializationThread(QThread):
    """
    Thread for initializing the network.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (str): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, NetworkGenerationData):
        """
        Initializes the NetInitializationThread.

        Args:
            NetworkGenerationData (object): Network generation data object containing all necessary parameters.
        """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData

    def run(self):
        """
        Runs the network initialization.
        """
        try:
            self.NetworkGenerationData = initialize_geojson(self.NetworkGenerationData)      

            # Common steps for both import types
            if self.NetworkGenerationData.diameter_optimization_pipe_checked == True:
                self.NetworkGenerationData.net = optimize_diameter_types(self.NetworkGenerationData.net, self.NetworkGenerationData.max_velocity_pipe, self.NetworkGenerationData.material_filter_pipe, self.NetworkGenerationData.k_mm_pipe)
            
            self.calculation_done.emit(self.NetworkGenerationData)

        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())
    
    def stop(self):
        """
        Stops the thread.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()

class NetCalculationThread(QThread):
    """
    Thread for network calculations.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (str): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, NetworkGenerationData):
        """
        Initializes the NetCalculationThread.

        Args:
            NetworkGenerationData (object): Network generation data object containing all necessary parameters.
            """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData
    
    def run(self):
        """
        Runs the network calculation.
        """
        try:
            self.NetworkGenerationData = time_series_preprocessing(self.NetworkGenerationData)
            
            self.NetworkGenerationData = thermohydraulic_time_series_net(self.NetworkGenerationData)

            self.calculation_done.emit(self.NetworkGenerationData)
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        """
        Stops the thread.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Wait for the thread to safely terminate
