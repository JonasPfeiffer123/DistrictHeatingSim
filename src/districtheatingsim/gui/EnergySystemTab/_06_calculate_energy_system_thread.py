"""
Calculate Energy System Thread Module
======================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Thread for calculating heat generation mix in district heating simulation, running calculations in a separate thread.
"""

import traceback

from PyQt6.QtCore import QThread, pyqtSignal

class CalculateEnergySystemThread(QThread):
    """
    Thread for calculating heat generation mix.

    :signal calculation_done: Emitted when calculation is done.
    :signal calculation_error: Emitted when error occurs during calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

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
            # Calculate the energy mix
            self.energy_system.calculate_mix()

            # Perform optimization if needed
            if self.optimize:
                optimized_energy_system = self.energy_system.optimize_mix(self.weights)

                # Calculate the energy mix
                optimized_energy_system.calculate_mix()

                # Emit the calculation result
                self.calculation_done.emit(([self.energy_system, optimized_energy_system]))
            else:
                # Emit the calculation result
                self.calculation_done.emit([self.energy_system])

        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(Exception(error_message))
