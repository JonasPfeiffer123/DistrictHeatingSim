"""
Calculate Energy System Thread Module
======================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Thread for calculating heat generation mix in district heating simulation, running calculations in a separate thread.
"""

import copy
import traceback

from PyQt6.QtCore import QThread, pyqtSignal


def run_energy_system_calculation(energy_system, optimize, weights):
    """
    Compute the heat-generation mix on a **deep copy** of ``energy_system``.

    The copy is what gets mutated and returned; the input object is left
    untouched so the UI thread can keep reading it until the result is swapped in
    on the main thread (via ``calculation_done``). This closes the read/write race
    on the shared ``energy_system`` (BACKLOG C1). GUI-free so it is unit-testable
    without a ``QThread`` / event loop.

    :param energy_system: The system to compute (not mutated).
    :param optimize: Whether to also run the SLSQP mix optimization.
    :param weights: Optimization criteria weights (used only when ``optimize``).
    :return: ``[system]`` or, when optimizing, ``[system, optimized_system]`` —
        both freshly computed copies, independent of the input.
    :rtype: list
    """
    system = copy.deepcopy(energy_system)
    system.calculate_mix()
    if optimize:
        optimized_system = system.optimize_mix(weights)
        optimized_system.calculate_mix()
        return [system, optimized_system]
    return [system]


class CalculateEnergySystemThread(QThread):
    """
    Thread for calculating heat generation mix.

    :signal calculation_done: Emitted when calculation is done.
    :signal calculation_error: Emitted when error occurs during calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, energy_system, optimize, weights):
        """
        Initialize the CalculateEnergySystemThread.

        :param energy_system: Energy system to calculate.
        :type energy_system: object
        :param optimize: Whether to optimize the mix.
        :type optimize: bool
        :param weights: Weights for optimization criteria.
        :type weights: dict
        """
        super().__init__()
        self.energy_system = energy_system
        self.optimize = optimize
        self.weights = weights

    def run(self):
        """
        Run heat generation mix calculation.
        """
        try:
            # Compute on a deep copy (the UI keeps its object until the main thread
            # swaps in this result), then emit it. See run_energy_system_calculation.
            result = run_energy_system_calculation(self.energy_system, self.optimize, self.weights)
            self.calculation_done.emit(result)

        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(error_message)

    def stop(self):
        """
        Request the thread to stop and block until it has finished.

        ``calculate_mix`` is not cooperatively interruptible, so this waits for the
        current run to complete (rather than killing it mid-computation) — enough to
        avoid emitting into a destroyed widget on close, consistent with the other
        worker threads.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()
