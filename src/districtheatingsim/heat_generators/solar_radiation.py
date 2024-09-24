"""
Filename: solar_radiation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-24
Description: Calculates the solar irradiation input based on Test Reference Year data.

Additional Information: Yield calculation program for solar thermal energy in heating networks (calculation basis: ScenoCalc District Heating 2.0) https://www.scfw.de/)
"""

# Import libraries
import numpy as np

# Constant for degree-to-radian conversion
DEG_TO_RAD = np.pi / 180

def calculate_solar_radiation(global_radiation, direct_radiation, day_of_year, time_steps, Longitude, STD_Longitude, Latitude, Albedo, East_West_collector_azimuth_angle, Collector_tilt_angle, IAM_W=None, IAM_N=None):    
    """
    Calculates solar radiation based on Test Reference Year data.

    Args:
        global_radiation (np.ndarray): Global radiation data.
        direct_radiation (np.ndarray): Direct radiation data.
        day_of_year (np.ndarray): Day of the year data.
        time_steps (np.ndarray): Array of time steps.
        Longitude (float): Longitude of the location.
        STD_Longitude (float): Standard longitude for the time zone.
        Latitude (float): Latitude of the location.
        Albedo (float): Albedo value.
        East_West_collector_azimuth_angle (float): East-West collector azimuth angle.
        Collector_tilt_angle (float): Collector tilt angle.
        IAM_W (dict): Incidence Angle Modifier for EW orientation.
        IAM_N (dict): Incidence Angle Modifier for NS orientation.

    Returns:
        tuple: Contains arrays for total radiation on the inclined surface, beam radiation, diffuse radiation, and modified beam radiation.
    """
    hour_L = (time_steps - time_steps.astype('datetime64[D]')).astype('timedelta64[m]').astype(float) / 60

    # Calculate the day of the year as an angle
    B = (day_of_year - 1) * 360 / 365  # °

    # Calculate the time correction based on the day angle
    E = 229.2 * (0.000075 + 0.001868 * np.cos(np.deg2rad(B)) - 0.032077 * np.sin(np.deg2rad(B)) -
                 0.014615 * np.cos(2 * np.deg2rad(B)) - 0.04089 * np.sin(2 * np.deg2rad(B)))

    # Calculate solar time considering the time correction and geographical longitude
    Solar_time = ((hour_L - 0.5) * 3600 + E * 60 + 4 * (STD_Longitude - Longitude) * 60) / 3600

    # Calculate solar declination
    Solar_declination = 23.45 * np.sin(np.deg2rad(360 * (284 + day_of_year) / 365))

    # Calculate the hour angle of the sun
    Hour_angle = -180 + Solar_time * 180 / 12

    # Calculate the solar zenith angle
    SZA = np.arccos(np.cos(np.deg2rad(Latitude)) * np.cos(np.deg2rad(Hour_angle)) *
                    np.cos(np.deg2rad(Solar_declination)) + np.sin(np.deg2rad(Latitude)) *
                    np.sin(np.deg2rad(Solar_declination))) / DEG_TO_RAD

    # Determine the azimuth angle of the sun
    EWs_az_angle = np.sign(Hour_angle) * np.arccos((np.cos(np.deg2rad(SZA)) * np.sin(np.deg2rad(Latitude)) -
                                                    np.sin(np.deg2rad(Solar_declination))) /
                                                   (np.sin(np.deg2rad(SZA)) * np.cos(np.deg2rad(Latitude)))) / \
                   DEG_TO_RAD

    # Calculate the incidence angle of solar radiation on the collector
    IaC = np.arccos(np.cos(np.deg2rad(SZA)) * np.cos(np.deg2rad(Collector_tilt_angle)) + np.sin(np.deg2rad(SZA)) *
                    np.sin(np.deg2rad(Collector_tilt_angle)) * np.cos(np.deg2rad(EWs_az_angle - East_West_collector_azimuth_angle))) / DEG_TO_RAD

    # Condition under which the collector receives solar radiation
    condition = (SZA < 90) & (IaC < 90)

    # Calculate the ratio of radiation intensity on the inclined collector to the horizontal surface
    function_Rb = np.cos(np.deg2rad(IaC)) / np.cos(np.deg2rad(SZA))
    Rb = np.where(condition, function_Rb, 0)

    # Calculate the beam radiation on the horizontal surface
    Gbhoris = direct_radiation * np.cos(np.deg2rad(SZA))

    # Calculate the diffuse radiation on a horizontal surface
    Gdhoris = global_radiation - Gbhoris

    # Calculate the atmospheric diffuse fraction Ai based on horizontal beam radiation Gbhoris and other parameters
    Ai = Gbhoris / (1367 * (1 + 0.033 * np.cos(np.deg2rad(360 * day_of_year / 365))) *
                    np.cos(np.deg2rad(SZA)))

    # Total radiation GT_H_Gk on the inclined surface, including direct, diffuse, and albedo-reflected contributions
    GT_H_Gk = (Gbhoris * Rb +  # Direct radiation adjusted by the angle
               Gdhoris * Ai * Rb +  # Diffuse radiation directly affected by the angle
               Gdhoris * (1 - Ai) * 0.5 * (1 + np.cos(np.deg2rad(
                Collector_tilt_angle))) +  # Diffuse radiation indirectly affected by the angle
               global_radiation * Albedo * 0.5 * (
                           1 - np.cos(np.deg2rad(Collector_tilt_angle))))  # Albedo-reflected radiation

    # Beam radiation on the inclined surface
    GbT = Gbhoris * Rb

    # Diffuse radiation on the inclined surface
    GdT_H_Dk = GT_H_Gk - GbT

    # only for solart thermal collectors
    # IAM_EW and IAM_NS are factors that describe the influence of the angle of incidence
    # on the radiation. K_beam is the product of these two factors.
    # Functions to calculate the incidence angles on the collector in EW and NS directions
    if IAM_W is not None and IAM_N is not None:
        f_EW = np.arctan(np.sin(SZA * DEG_TO_RAD) * np.sin((EWs_az_angle - East_West_collector_azimuth_angle) * DEG_TO_RAD) /
                        np.cos(IaC * DEG_TO_RAD)) / DEG_TO_RAD

        f_NS = -(180 / np.pi * np.arctan(np.tan(SZA * DEG_TO_RAD) * np.cos((EWs_az_angle - East_West_collector_azimuth_angle) * DEG_TO_RAD)) - Collector_tilt_angle)

        Incidence_angle_EW = np.where(condition, f_EW, 89.999)
        Incidence_angle_NS = np.where(condition, f_NS, 89.999)

        def IAM(Incidence_angle, iam_data):
            sverweis_1 = np.abs(Incidence_angle) - np.abs(Incidence_angle) % 10
            sverweis_2 = np.vectorize(iam_data.get)(sverweis_1)
            sverweis_3 = (np.abs(Incidence_angle) + 10) - (np.abs(Incidence_angle) + 10) % 10
            sverweis_4 = np.vectorize(iam_data.get)(sverweis_3)

            result = sverweis_2 + (np.abs(Incidence_angle) - sverweis_1) / (sverweis_3 - sverweis_1) * (sverweis_4 - sverweis_2)
            return result

        # For IAM_EW
        IAM_EW = IAM(Incidence_angle_EW, IAM_W)
        # For IAM_NS
        IAM_NS = IAM(Incidence_angle_NS, IAM_N)
        K_beam = IAM_EW * IAM_NS
    else:
        K_beam = None

    return GT_H_Gk, K_beam, GbT, GdT_H_Dk
