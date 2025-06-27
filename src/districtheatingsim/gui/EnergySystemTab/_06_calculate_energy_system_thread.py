"""
Calculate Energy System Thread Module
=====================================

This module contains the CalculateEnergySystemThread class, which is responsible for calculating the heat generation mix in a district heating simulation application. It runs the calculation in a separate thread to avoid blocking the main GUI thread.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-03
"""

import traceback

from PyQt5.QtCore import QThread, pyqtSignal

class CalculateEnergySystemThread(QThread):
    """
    Thread for calculating the heat generation mix.

    Signals:
        calculation_done (object): Emitted when the calculation is done.
        calculation_error (Exception): Emitted when an error occurs during the calculation.
    """
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(Exception)

    def __init__(self, energy_system, optimize, weights):
        """
        Initializes the CalculateMixThread.

        Args:
            filename (str): Filename for the CSV containing the load data.
            load_scale_factor (float): Scaling factor for the load.
            TRY_data: Test Reference Year data.
            COP_data: Coefficient of Performance data.
            economic_parameters (dict): Economic parameters.
            tech_objects (list): List of technology objects.
            optimize (bool): Whether to optimize the mix.
            weights (dict): Weights for optimization criteria.
        """
        super().__init__()
        self.energy_system = energy_system
        self.optimize = optimize
        self.weights = weights

    def run(self):
        """
        Runs the heat generation mix calculation.
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
