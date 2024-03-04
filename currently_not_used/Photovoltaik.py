# Created by Jonas Pfeiffer
# Calculation of solar irradiation according to Scenocalc District Heating 2.0 and PV according to eupvgis

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def import_TRY(filename):
    # Import TRY
    # Define column widths
    col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]
    # Define column names
    col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]

    # Read the file
    data = pd.read_fwf(filename, widths=col_widths, names=col_names,
                       skiprows=34)

    # Store the columns as numpy arrays
    temperature = data['t'].values
    windspeed = data['WG'].values
    direct_radiation = data['B'].values
    diffuse_radiation = data['D'].values
    global_radiation = direct_radiation + diffuse_radiation

    return temperature, windspeed, direct_radiation, global_radiation

# Constant for degree-radian conversion
DEG_TO_RAD = np.pi / 180

def deg_to_rad(deg):
    return deg * DEG_TO_RAD

def Calculate_Solar_Radiation(Irradiance_hori_L, D_L, Day_of_Year_L, Longitude, STD_Longitude, Latitude, Albedo,
                              East_West_collector_azimuth_angle, Collector_tilt_angle):
    # Creating an array from 1 to 24 h for 365 days
    Hour_L = np.tile(np.arange(1, 25), 365)

    # Calculates the angle of the day in the annual cycle
    B = (Day_of_Year_L - 1) * 360 / 365  # °

    # Calculates the Equation of Time (E), considering differences between sundial and standard time
    E = 229.2 * (0.000075 + 0.001868 * np.cos(deg_to_rad(B)) - 0.032077 * np.sin(deg_to_rad(B)) -
                 0.014615 * np.cos(2 * deg_to_rad(B)) - 0.04089 * np.sin(2 * deg_to_rad(B)))

    # Determines the solar time
    Solar_time = ((Hour_L - 0.5) * 3600 + E * 60 + 4 * (STD_Longitude - Longitude) * 60) / 3600

    # Calculates the solar declination based on the day of the year
    Solar_declination = 23.45 * np.sin(deg_to_rad(360 * (284 + Day_of_Year_L) / 365))

    # Determines the hour angle of the sun
    Hour_angle = -180 + Solar_time * 180 / 12

    # Calculates the solar zenith angle
    Solar_Zenith_angle = np.arccos(np.cos(deg_to_rad(Latitude)) * np.cos(deg_to_rad(Hour_angle)) *
                                   np.cos(deg_to_rad(Solar_declination)) + np.sin(deg_to_rad(Latitude)) *
                                   np.sin(deg_to_rad(Solar_declination))) / DEG_TO_RAD

    # Determines the solar azimuth angle
    East_West_solar_azimuth_angle = np.sign(Hour_angle) * \
                                    np.arccos((np.cos(deg_to_rad(Solar_Zenith_angle)) * np.sin(deg_to_rad(Latitude)) -
                                               np.sin(deg_to_rad(Solar_declination))) /
                                              (np.sin(deg_to_rad(Solar_Zenith_angle)) * np.cos(deg_to_rad(Latitude)))) / \
                                    DEG_TO_RAD

    # Calculates the incidence angle of solar radiation on the collector
    Incidence_angle_onto_collector = np.arccos(
        np.cos(deg_to_rad(Solar_Zenith_angle)) * np.cos(deg_to_rad(Collector_tilt_angle)) +
        np.sin(deg_to_rad(Solar_Zenith_angle)) * np.sin(deg_to_rad(Collector_tilt_angle)) *
        np.cos(deg_to_rad(East_West_solar_azimuth_angle - East_West_collector_azimuth_angle))) / DEG_TO_RAD

    # Defines the condition under which the collector receives solar radiation
    condition = (Solar_Zenith_angle < 90) & (Incidence_angle_onto_collector < 90)

    # Determines the ratio of radiation intensity on the tilted collector to the horizontal surface
    function_Rb = np.cos(deg_to_rad(Incidence_angle_onto_collector)) / np.cos(deg_to_rad(Solar_Zenith_angle))
    Rb = np.where(condition, function_Rb, 0)

    # Determines the radiation portion that directly hits a horizontal surface from the sun
    Gbhoris = D_L * np.cos(deg_to_rad(Solar_Zenith_angle))

    # Determines the anisotropy index for diffuse radiation
    Ai = Gbhoris / (1367 * (1 + 0.033 * np.cos(deg_to_rad(360 * Day_of_Year_L / 365))) *
                    np.cos(deg_to_rad(Solar_Zenith_angle)))

    # Determines the diffuse radiation part on a horizontal surface
    Gdhoris = Irradiance_hori_L - Gbhoris

    # Combines all radiation components to determine the total radiation intensity on the collector
    GT_H_Gk = (Gbhoris * Rb + Gdhoris * Ai * Rb + Gdhoris * (1 - Ai) * 0.5 *
               (1 + np.cos(deg_to_rad(Collector_tilt_angle))) +
               Irradiance_hori_L * Albedo * 0.5 * (1 - np.cos(deg_to_rad(Collector_tilt_angle))))

    print("Total irradiation: " + str(round(np.sum(GT_H_Gk)/1000, 1)) + " kWh/m²")

    # Returns the total radiation intensity on the collector
    return GT_H_Gk

def Calculate_PV(TRY_data, Gross_area, Longitude, STD_Longitude, Latitude, Albedo,
                 East_West_collector_azimuth_angle, Collector_tilt_angle):
    # Import TRY
    Ta_L, W_L, D_L, G_L = import_TRY(TRY_data)

    # Define constants for the photovoltaic calculation.
    eff_nom = 0.199  # Nominal efficiency
    sys_loss = 0.14  # System losses
    U0 = 26.9  # Temperature-dependent power loss (W / (°C * m^2))
    U1 = 6.2  # Temperature-dependent power loss (W * s / (°C * m^3))

    # Constants for the efficiency calculation depending on temperature and irradiation.
    k1, k2, k3, k4, k5, k6 = -0.017237, -0.040465, -0.004702, 0.000149, 0.000170, 0.000005

    Day_of_Year_L = np.repeat(np.arange(1, 366), 24)
    # Calculate the solar irradiation for the given data.
    GT_L = Calculate_Solar_Radiation(G_L, D_L, Longitude, Day_of_Year_L, STD_Longitude, Latitude, Albedo,
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

    print("works")
    
    df['Annual Hours'] = Annual_hours
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
                print(f"PV yield {building}{suffix}: {yield} MWh")
                print(f"Maximum PV power {building}{suffix}: {max_power} kW")

                df[f'{building} {suffix} {area} m^2 [kW]'] = P_L

    # Save the DataFrame after completing the loop
    df.to_csv(output_filename, index=False, sep=';')

calculate_building("heating_network_generation/heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat", "building_data_pv.csv", 'pv_data_results.csv')