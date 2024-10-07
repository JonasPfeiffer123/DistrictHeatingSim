"""
Filename: photovoltaics.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-24
Description: Calculation of PV according to eupvgis.

"""

import numpy as np
import pandas as pd

from utilities.test_reference_year import import_TRY
from heat_generators.solar_radiation import calculate_solar_radiation

# Constant for degree-radian conversion
DEG_TO_RAD = np.pi / 180

def Calculate_PV(TRY_data, Gross_area, Longitude, STD_Longitude, Latitude, Albedo,
                 East_West_collector_azimuth_angle, Collector_tilt_angle):
    """
    Calculates the photovoltaic power output based on TRY data and system specifications.

    Args:
        TRY_data (str): Path to the TRY data file.
        Gross_area (float): Gross area of the photovoltaic system.
        Longitude (float): Longitude of the location.
        STD_Longitude (float): Standard longitude for the time zone.
        Latitude (float): Latitude of the location.
        Albedo (float): Albedo value.
        East_West_collector_azimuth_angle (float): East-West collector azimuth angle.
        Collector_tilt_angle (float): Collector tilt angle.

    Returns:
        tuple: Annual PV yield (kWh), maximum power (kW), and power output array (W).
    """
    # Import TRY
    Ta_L, W_L, D_L, G_L, _ = import_TRY(TRY_data)

    # Define constants for the photovoltaic calculation.
    eff_nom = 0.199  # Nominal efficiency
    sys_loss = 0.14  # System losses
    U0 = 26.9  # Temperature-dependent power loss (W / (°C * m^2))
    U1 = 6.2  # Temperature-dependent power loss (W * s / (°C * m^3))

    # Constants for the efficiency calculation depending on temperature and irradiation.
    k1, k2, k3, k4, k5, k6 = -0.017237, -0.040465, -0.004702, 0.000149, 0.000170, 0.000005

    Day_of_Year_L = np.repeat(np.arange(1, 366), 24)

    # Generate time steps (hourly intervals) for a specific date range
    start_date = np.datetime64('2024-01-01T00:00')
    end_date = np.datetime64('2024-01-02T00:00')  # Example of 1 day
    time_steps = np.arange(start_date, end_date, np.timedelta64(1, 'h'))

    # Calculate the solar irradiation for the given data.
    GT_L, _, _, _ = calculate_solar_radiation(G_L, D_L, Longitude, Day_of_Year_L, time_steps, STD_Longitude, Latitude, Albedo,
                                     East_West_collector_azimuth_angle, Collector_tilt_angle)

    # Calculate the average solar irradiation value (in kW/m^2).
    G1 = GT_L / 1000

    # Calculate the module temperature based on ambient temperature, irradiation, and wind speed.
    Tm = Ta_L + GT_L / (U0 + U1 * W_L)
    T1m = Tm - 25

    # Calculate the relative efficiency considering irradiation and temperature.
    eff_rel = np.ones_like(G1)
    non_zero_mask = G1 != 0
    eff_rel[non_zero_mask] = 1 + k1 * np.log(G1[non_zero_mask]) + k2 * np.log(G1[non_zero_mask]) ** 2 + k3 * T1m[
        non_zero_mask] + k4 * T1m[non_zero_mask] * np.log(G1[non_zero_mask]) + k5 * Tm[non_zero_mask] * np.log(
        G1[non_zero_mask]) ** 2 + k6 * Tm[non_zero_mask] ** 2
    eff_rel[~non_zero_mask] = 0
    eff_rel = np.nan_to_num(eff_rel, nan=0)

    # Calculate the photovoltaic power based on irradiation, area, nominal efficiency, and relative efficiency.
    P_L = G1 * Gross_area * eff_nom * eff_rel * (1 - sys_loss)

    # Determine the maximum power and total annual yield.
    P_max = np.max(P_L)
    E = np.sum(P_L)

    # Convert the total yield to kWh.
    yield_kWh = round(E / 1000, 2)
    P_max = round(P_max, 2)

    # Return the annual PV yield in kWh, maximum power, and the power list.
    return yield_kWh, P_max, P_L

def azimuth_angle(direction):
    """
    Converts direction to azimuth angle.

    Args:
        direction (str): Cardinal direction (e.g., 'N', 'W', 'S', 'E').

    Returns:
        float: Azimuth angle in degrees.
    """
    azimuths = {
        'N': 180,
        'W': 90,
        'S': 0,
        'O': 270,  # 'O' in German is 'E' (East) in English
        'NO': 225,  # 'NO' in German is 'NE' (Northeast) in English
        'SO': 315,  # 'SO' in German is 'SE' (Southeast) in English
        'SW': 45,
        'NW': 135
    }
    return azimuths.get(direction.upper(), None)

def calculate_building(TRY_data, building_data, output_filename):
    """
    Calculates the photovoltaic yield for buildings based on their specifications.

    Args:
        TRY_data (str): Path to the TRY data file.
        building_data (str): Path to the CSV file containing building data.
        output_filename (str): Path to save the output CSV file.
    """
    # Load data from CSV file
    gdata = np.genfromtxt(building_data, delimiter=";", skip_header=1, dtype=None, encoding='utf-8')

    # Definitions
    Longitude = -14.4222
    STD_Longitude = -15
    Latitude = 51.1676

    Albedo = 0.2
    Collector_tilt_angle = 36
    Annual_hours = np.arange(1, 8761)

    # Result file
    df = pd.DataFrame()
    df['Annual Hours'] = Annual_hours

    print("Calculating PV yield for buildings...")

    for idx, (building, area, direction) in enumerate(gdata):
        azimuth_angle = azimuth_angle(direction)

        # In case the direction is "EW" (East-West) // German "OW"
        if azimuth_angle is None and direction == "OW":
            area /= 2
            directions = ["O", "W"]
        else:
            directions = [direction]

        for hr in directions:
            azimuth_angle = azimuth_angle(hr)
            if azimuth_angle is not None:
                yield_kWh, max_power, P_L = Calculate_PV(TRY_data, area, Longitude, STD_Longitude, Latitude, Albedo,
                                                     azimuth_angle, Collector_tilt_angle)

                suffix = hr if direction == "OW" else ""
                print(f"PV yield {building}{suffix}: {yield_kWh} MWh")
                print(f"Maximum PV power {building}{suffix}: {max_power} kW")

                df[f'{building} {suffix} {area} m^2 [kW]'] = P_L

    # Save the DataFrame after completing the loop
    df.to_csv(output_filename, index=False, sep=';')