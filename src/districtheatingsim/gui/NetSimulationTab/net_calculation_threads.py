"""
Network Calculation Threads Module
==================================

Threaded network initialization and calculation functionality.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-17
"""

import traceback
import numpy as np

from PyQt5.QtCore import QThread, pyqtSignal

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import thermohydraulic_time_series_net, time_series_preprocessing
from districtheatingsim.net_simulation_pandapipes.utilities import optimize_diameter_types

class NetInitializationThread(QThread):
    """
    Thread for network initialization tasks.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, NetworkGenerationData):
        """
        Initialize network initialization thread.

        Parameters
        ----------
        NetworkGenerationData : object
            Network generation data object.
        """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData

    def run(self):
        """Run network initialization process."""
        try:
            self.NetworkGenerationData = initialize_geojson(self.NetworkGenerationData)      

            # Diameter optimization if enabled
            if self.NetworkGenerationData.diameter_optimization_pipe_checked == True:
                self.NetworkGenerationData.net = optimize_diameter_types(self.NetworkGenerationData.net, self.NetworkGenerationData.max_velocity_pipe, self.NetworkGenerationData.material_filter_pipe, self.NetworkGenerationData.k_mm_pipe)
            
            self.calculation_done.emit(self.NetworkGenerationData)

        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())
    
    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()

class NetCalculationThread(QThread):
    """
    Thread for network time series calculations.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, NetworkGenerationData):
        """
        Initialize calculation thread.

        Parameters
        ----------
        NetworkGenerationData : object
            Network generation data object.
        """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData
    
    def run(self):
        """Run time series calculation process."""
        try:
            self.NetworkGenerationData = time_series_preprocessing(self.NetworkGenerationData)
            
            self.NetworkGenerationData = thermohydraulic_time_series_net(self.NetworkGenerationData)

            self.calculation_done.emit(self.NetworkGenerationData)
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()