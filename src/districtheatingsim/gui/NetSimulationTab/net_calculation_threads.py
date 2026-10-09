"""Network Calculation Threads Module
===================================

Threaded network initialization and calculation functionality.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import copy
import threading
import traceback

from PyQt6.QtCore import QThread, pyqtSignal

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import (
    TimeSeriesCancelled,
    simplified_time_series_net,
    thermohydraulic_time_series_net,
    time_series_preprocessing,
)
from districtheatingsim.net_simulation_pandapipes.utilities import optimize_diameter_types, recalculate_net


def format_time_series_progress(done: int, total: int, elapsed_s: float) -> str:
    """
    Progress text of the detailed time series: time step and remaining time.

    :param done: Time steps done.
    :param total: Time steps of the run.
    :param elapsed_s: Seconds since the first time step started.
    """
    text = f"Zeitschritt {done} von {total}"
    if done < 3 or elapsed_s <= 0:
        return f"{text} – Restzeit wird ermittelt …"
    remaining_min = elapsed_s / done * (total - done) / 60.0
    if remaining_min < 1:
        return f"{text} – noch unter 1 min"
    if remaining_min < 90:
        return f"{text} – noch ca. {round(remaining_min)} min"
    hours, minutes = divmod(round(remaining_min), 60)
    return f"{text} – noch ca. {hours} h {minutes:02d} min"


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
            if self.NetworkGenerationData.diameter_optimization_pipe_checked:
                self.NetworkGenerationData.net = optimize_diameter_types(
                    self.NetworkGenerationData.net,
                    self.NetworkGenerationData.max_velocity_pipe,
                    self.NetworkGenerationData.material_filter_pipe,
                    self.NetworkGenerationData.k_mm_pipe,
                )

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

    Works on a copy of the network data: a cancelled or failed run leaves the caller's net as it
    was (no controllers or half a time series in it). The detailed run reports its progress and
    can be cancelled between two time steps (BACKLOG UT-H1).
    """

    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)
    #: ``(done, total)`` time steps of the detailed calculation
    progress = pyqtSignal(int, int)
    calculation_cancelled = pyqtSignal()

    def __init__(self, NetworkGenerationData, simplified=False, workers=1):
        """
        Initialize calculation thread.

        :param NetworkGenerationData: Network generation data object.
        :type NetworkGenerationData: object
        :param simplified: Use simplified fast calculation instead of detailed simulation.
        :type simplified: bool
        :param workers: Worker processes for the detailed time series (1 = sequential).
        :type workers: int
        """
        super().__init__()
        self.NetworkGenerationData = NetworkGenerationData
        self.simplified = simplified
        self.workers = workers
        self._cancel = threading.Event()

    def cancel(self):
        """Ask the calculation to stop before its next time step (thread-safe)."""
        self._cancel.set()

    def _report(self, done: int, total: int) -> None:
        """Progress hook of the time series: emit the progress, or stop if cancelled."""
        if self._cancel.is_set():
            raise TimeSeriesCancelled()
        self.progress.emit(done, total)

    def run(self):
        """
        Run time series calculation process.
        """
        try:
            data = time_series_preprocessing(copy.deepcopy(self.NetworkGenerationData))

            if self.simplified:
                # Use simplified fast calculation
                data = simplified_time_series_net(data)
            else:
                # Use detailed hydraulic simulation
                data = thermohydraulic_time_series_net(data, workers=self.workers, progress=self._report)
            if self._cancel.is_set():
                raise TimeSeriesCancelled()

            # Compute KPIs here (off the UI thread) so the info panel just renders them.
            data.calculate_results()
            self.NetworkGenerationData = data
            self.calculation_done.emit(data)
        except TimeSeriesCancelled:
            self.calculation_cancelled.emit()
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        """Cancel the calculation and wait (closing the app no longer waits for the whole run)."""
        if self.isRunning():
            self.cancel()
            self.requestInterruption()
            self.wait()
