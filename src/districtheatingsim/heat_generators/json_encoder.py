"""
JSON encoder for energy-system serialization.
==============================================

GUI-free ``json.JSONEncoder`` that handles the non-standard types produced by the
domain core (numpy scalars/arrays, pandas DataFrames, heat-generator/storage
objects). Lives here — not in the ``gui`` package — so that
``energy_system.save_to_json`` does not drag PyQt6 into the GUI-free domain core
(BACKLOG B5). The GUI re-exports it from ``EnergySystemTab/_10_utilities.py``.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import json

import numpy as np
import pandas as pd

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy
from districtheatingsim.heat_generators.thermal_storage import ThermalStorageAdapter


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder for handling numpy arrays, pandas DataFrames, and custom objects.
    """

    def default(self, obj):
        try:
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, pd.DataFrame):
                # Use 'split' format for DataFrame serialization
                return obj.to_dict(orient="split")
            if isinstance(obj, (BaseHeatGenerator, BaseStrategy, ThermalStorageAdapter)):
                return obj.to_dict()
            return super().default(obj)
        except TypeError as e:
            raise e
