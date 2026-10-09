"""
Analysis M4 – longitude sign convention of the solar thermal defaults
======================================================================

``calculate_solar_radiation`` uses ``4 * (STD_Longitude - Longitude)`` minutes, i.e. east is
negative. The class defaults are consistent (−14.42 / −15), the GUI dialog pre-fills
−14.42 / +15. Compares the annual tilted irradiance and the hour of the daily maximum.

Measured 2026-10-08: annual sum +0.2 %, daily maximum one hour earlier with the GUI defaults.

Run: ``python tests/e2e/analysis_solar_time.py``
"""

import numpy as np

from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation
from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.utilities.utilities import DEFAULT_TRY_RESOURCE, get_resource_path


def main():
    temperature, wind, direct, global_radiation = import_TRY(get_resource_path(DEFAULT_TRY_RESOURCE))[:4]
    time_steps = np.arange("2023-01-01T00", "2024-01-01T00", dtype="datetime64[h]")
    cases = [
        ("class defaults (-14.42 / -15)", -14.4222, -15),
        ("GUI defaults (-14.42 / +15)", -14.4222, 15),
        ("east-positive input (+14.42 / +15)", 14.4222, 15),
    ]
    for label, longitude, std_longitude in cases:
        tilted = np.asarray(
            calculate_solar_radiation(
                time_steps, global_radiation, direct, longitude, std_longitude, 51.1676, 0.2, 0, 36
            )[0]
        )
        day = tilted[4008:4032]
        print(
            f"{label:36s} annual {np.nansum(tilted) / 1000:7.1f} kWh/m2, "
            f"day 168: maximum at {int(np.nanargmax(day))}:00"
        )


if __name__ == "__main__":
    main()
