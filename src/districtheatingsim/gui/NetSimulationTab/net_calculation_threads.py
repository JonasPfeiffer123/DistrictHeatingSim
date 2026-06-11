"""Network Calculation Threads Module
===================================

Threaded network initialization and calculation functionality.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import traceback

from PyQt6.QtCore import QThread, pyqtSignal

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import (
    simplified_time_series_net,
    thermohydraulic_time_series_net,
    time_series_preprocessing,
)
from districtheatingsim.net_simulation_pandapipes.utilities import optimize_diameter_types, recalculate_net


class NetInitializationThread(QThread):
    """
    Thread for network initialization tasks.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, NetworkGenerationData):
        """
        Initialize network initialization thread.

        :param NetworkGenerationData: Network generation data object.
        :type NetworkGenerationData: object
        """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData

    def run(self):
        """
        Run network initialization process.
        """
        try:
            self.NetworkGenerationData = initialize_geojson(self.NetworkGenerationData)      

            # Diameter optimization if enabled
            if self.NetworkGenerationData.diameter_optimization_pipe_checked == True:
                self.NetworkGenerationData.net = optimize_diameter_types(self.NetworkGenerationData.net, self.NetworkGenerationData.max_velocity_pipe, self.NetworkGenerationData.material_filter_pipe, self.NetworkGenerationData.k_mm_pipe)

            # Compute KPIs here (off the UI thread) so the info panel just renders them.
            self.NetworkGenerationData.calculate_results()
            self.calculation_done.emit(self.NetworkGenerationData)

        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())
    
    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()

class NetRecalculationThread(QThread):
    """
    Thread for steady-state network recalculation (pipeflow + controllers).

    Runs the recalculation off the UI thread so the GUI does not freeze while the
    solver runs (e.g. after the user edits pipe parameters).
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, NetworkGenerationData):
        """
        :param NetworkGenerationData: Network generation data object (recalculated in place).
        """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData

    def run(self):
        """Run the steady-state recalculation."""
        try:
            recalculate_net(self.NetworkGenerationData.net)
            self.NetworkGenerationData.calculate_results()
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

    def __init__(self, NetworkGenerationData, simplified=False):
        """
        Initialize calculation thread.

        :param NetworkGenerationData: Network generation data object.
        :type NetworkGenerationData: object
        :param simplified: Use simplified fast calculation instead of detailed simulation.
        :type simplified: bool
        """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData
        self.simplified = simplified
    
    def run(self):
        """
        Run time series calculation process.
        """
        try:
            self.NetworkGenerationData = time_series_preprocessing(self.NetworkGenerationData)
            
            if self.simplified:
                # Use simplified fast calculation
                self.NetworkGenerationData = simplified_time_series_net(self.NetworkGenerationData)
            else:
                # Use detailed hydraulic simulation
                self.NetworkGenerationData = thermohydraulic_time_series_net(self.NetworkGenerationData)

            # Compute KPIs here (off the UI thread) so the info panel just renders them.
            self.NetworkGenerationData.calculate_results()
            self.calculation_done.emit(self.NetworkGenerationData)
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        """Stop thread execution."""
        if self.isRunning():
            self.requestInterruption()
            self.wait()