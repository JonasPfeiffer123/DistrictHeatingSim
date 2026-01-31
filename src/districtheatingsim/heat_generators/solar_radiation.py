"""
Solar Radiation Calculation Module
==================================

Solar radiation calculations for tilted collectors using Test Reference Year data.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

# Import libraries
import numpy as np
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Union

# Constant for degree-to-radian conversion
DEG_TO_RAD = np.pi / 180

def calculate_solar_radiation(
    time_steps: np.ndarray, 
    global_radiation: np.ndarray, 
    direct_radiation: np.ndarray, 
    Longitude: float, 
    STD_Longitude: float, 
    Latitude: float, 
    Albedo: float, 
    East_West_collector_azimuth_angle: float, 
    Collector_tilt_angle: float, 
    IAM_W: Optional[Dict[float, float]] = None, 
    IAM_N: Optional[Dict[float, float]] = None
) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray, np.ndarray]:
    """
    Calculate solar radiation components for tilted collectors using Test Reference Year data.

    :param time_steps: Time series as datetime64 array [hours]
    :type time_steps: numpy.ndarray
    :param global_radiation: Global horizontal irradiance [W/m²]
    :type global_radiation: numpy.ndarray
    :param direct_radiation: Direct normal irradiance [W/m²]
    :type direct_radiation: numpy.ndarray
    :param Longitude: Site longitude [degrees], range -180° to +180°
    :type Longitude: float
    :param STD_Longitude: Standard time zone longitude [degrees] (e.g., 15° for CET)
    :type STD_Longitude: float
    :param Latitude: Site latitude [degrees], range -90° to +90°
    :type Latitude: float
    :param Albedo: Ground reflectance factor [-], typical values 0.2 (grass), 0.8 (snow)
    :type Albedo: float
    :param East_West_collector_azimuth_angle: Collector azimuth [degrees], 0° = south
    :type East_West_collector_azimuth_angle: float
    :param Collector_tilt_angle: Collector tilt from horizontal [degrees], 0-90°
    :type Collector_tilt_angle: float
    :param IAM_W: Incidence Angle Modifier lookup table for East-West direction {angle: factor}
    :type IAM_W: Optional[Dict[float, float]]
    :param IAM_N: Incidence Angle Modifier lookup table for North-South direction {angle: factor}
    :type IAM_N: Optional[Dict[float, float]]
    :return: (GT_total[W/m²], K_beam[-], Gb_tilted[W/m²], Gd_tilted[W/m²])
    :rtype: Tuple[np.ndarray, Optional[np.ndarray], np.ndarray, np.ndarray]

    .. note::
       Implements comprehensive solar geometry, atmospheric effects, and collector-specific IAM corrections.
       Total radiation GT = beam + diffuse sky + ground-reflected components.
    """
    # Convert time_steps to datetime64 if needed and extract hour of day
    time_steps_dt = np.asarray(time_steps, dtype='datetime64[h]')
    time_of_day = (time_steps_dt - time_steps_dt.astype('datetime64[D]')).astype('timedelta64[h]').astype(float)
    hour_L = time_of_day
    
    # Calculate day of year for each time step
    day_of_year = np.array([
        datetime.fromtimestamp(t.astype('datetime64[s]').astype(np.int64), tz=timezone.utc).timetuple().tm_yday 
        for t in time_steps_dt
    ])

    # Calculate the day of the year as an angle for solar calculations
    B = (day_of_year - 1) * 360 / 365  # degrees

    # Calculate the equation of time correction based on the day angle
    # Accounts for Earth's orbital eccentricity and axial tilt variations
    E = 229.2 * (0.000075 + 0.001868 * np.cos(np.deg2rad(B)) - 0.032077 * np.sin(np.deg2rad(B)) -
                 0.014615 * np.cos(2 * np.deg2rad(B)) - 0.04089 * np.sin(2 * np.deg2rad(B)))

    # Calculate apparent solar time considering equation of time and longitude
    # Corrects local time to solar time using geographical and temporal factors
    Solar_time = ((hour_L - 0.5) * 3600 + E * 60 + 4 * (STD_Longitude - Longitude) * 60) / 3600

    # Calculate solar declination angle using standard approximation
    # Represents sun's angular position relative to Earth's equatorial plane
    Solar_declination = 23.45 * np.sin(np.deg2rad(360 * (284 + day_of_year) / 365))

    # Calculate the hour angle of the sun
    # Represents sun's east-west position relative to solar noon
    Hour_angle = -180 + Solar_time * 180 / 12

    # Calculate the solar zenith angle using spherical trigonometry
    # Angle between sun's position and vertical (zenith direction)
    SZA = np.arccos(np.cos(np.deg2rad(Latitude)) * np.cos(np.deg2rad(Hour_angle)) *
                    np.cos(np.deg2rad(Solar_declination)) + np.sin(np.deg2rad(Latitude)) *
                    np.sin(np.deg2rad(Solar_declination))) / DEG_TO_RAD

    # Determine the azimuth angle of the sun
    # Horizontal angle from south to sun's projection on horizontal plane
    EWs_az_angle = np.sign(Hour_angle) * np.arccos((np.cos(np.deg2rad(SZA)) * np.sin(np.deg2rad(Latitude)) -
                                                    np.sin(np.deg2rad(Solar_declination))) /
                                                   (np.sin(np.deg2rad(SZA)) * np.cos(np.deg2rad(Latitude)))) / \
                   DEG_TO_RAD

    # Calculate the incidence angle of solar radiation on the collector
    # Angle between incoming solar rays and collector surface normal
    IaC = np.arccos(np.cos(np.deg2rad(SZA)) * np.cos(np.deg2rad(Collector_tilt_angle)) + 
                    np.sin(np.deg2rad(SZA)) * np.sin(np.deg2rad(Collector_tilt_angle)) * 
                    np.cos(np.deg2rad(EWs_az_angle - East_West_collector_azimuth_angle))) / DEG_TO_RAD

    # Condition under which the collector receives solar radiation
    # Both sun and collector must be above horizon for radiation reception
    condition = (SZA < 90) & (IaC < 90)

    # Calculate the ratio of radiation intensity on the inclined collector to the horizontal surface
    # Geometric factor for beam radiation projection onto tilted surface
    function_Rb = np.cos(np.deg2rad(IaC)) / np.cos(np.deg2rad(SZA))
    Rb = np.where(condition, function_Rb, 0)

    # Calculate the beam radiation on the horizontal surface
    # Project direct normal irradiance onto horizontal plane
    Gbhoris = direct_radiation * np.cos(np.deg2rad(SZA))

    # Calculate the diffuse radiation on a horizontal surface
    # Difference between global and beam radiation components
    Gdhoris = global_radiation - Gbhoris

    # Calculate the atmospheric diffuse fraction Ai based on clearness conditions
    # Fraction of diffuse radiation that behaves like direct radiation
    extraterrestrial_normal = 1367 * (1 + 0.033 * np.cos(np.deg2rad(360 * day_of_year / 365)))
    Ai = Gbhoris / (extraterrestrial_normal * np.cos(np.deg2rad(SZA)))

    # Total radiation GT_H_Gk on the inclined surface
    # Combines direct beam, diffuse sky, and ground-reflected radiation components
    GT_H_Gk = (Gbhoris * Rb +  # Direct beam radiation projected to tilted surface
               Gdhoris * Ai * Rb +  # Atmospheric diffuse radiation (directional component)
               Gdhoris * (1 - Ai) * 0.5 * (1 + np.cos(np.deg2rad(
                Collector_tilt_angle))) +  # Isotropic diffuse radiation from sky hemisphere
               global_radiation * Albedo * 0.5 * (
                           1 - np.cos(np.deg2rad(Collector_tilt_angle))))  # Ground-reflected radiation

    # Beam radiation on the inclined surface
    # Direct component of solar radiation on collector surface
    GbT = Gbhoris * Rb

    # Diffuse radiation on the inclined surface
    # Combined diffuse sky and ground-reflected radiation components
    GdT_H_Dk = GT_H_Gk - GbT

    # Incidence Angle Modifier (IAM) calculations for solar thermal collectors
    # IAM_EW and IAM_NS are factors describing incidence angle influence on collector performance
    # K_beam is the combined product of East-West and North-South IAM factors
    if IAM_W is not None and IAM_N is not None:
        # Calculate incidence angles in East-West direction
        # Angle between solar ray projection and collector normal in EW plane
        f_EW = np.arctan(np.sin(SZA * DEG_TO_RAD) * 
                        np.sin((EWs_az_angle - East_West_collector_azimuth_angle) * DEG_TO_RAD) /
                        np.cos(IaC * DEG_TO_RAD)) / DEG_TO_RAD

        # Calculate incidence angles in North-South direction
        # Angle between solar ray projection and collector normal in NS plane
        f_NS = -(180 / np.pi * np.arctan(np.tan(SZA * DEG_TO_RAD) * 
                np.cos((EWs_az_angle - East_West_collector_azimuth_angle) * DEG_TO_RAD)) - Collector_tilt_angle)

        # Apply radiation condition limits to incidence angles
        # Set to near-90° for conditions with no solar radiation
        Incidence_angle_EW = np.where(condition, f_EW, 89.999)
        Incidence_angle_NS = np.where(condition, f_NS, 89.999)

        def IAM(Incidence_angle: np.ndarray, iam_data: Dict[float, float]) -> np.ndarray:
            """
            Interpolate Incidence Angle Modifier values from lookup table using bilinear interpolation.

            :param Incidence_angle: Incidence angles [degrees]
            :type Incidence_angle: numpy.ndarray
            :param iam_data: IAM lookup table {angle: factor}
            :type iam_data: Dict[float, float]
            :return: Interpolated IAM factors
            :rtype: numpy.ndarray
            """
            # Find lower bound incidence angles (rounded down to nearest 10°)
            sverweis_1 = np.abs(Incidence_angle) - np.abs(Incidence_angle) % 10
            # Get IAM values for lower bounds (default to 0.0 if key not found)
            sverweis_2 = np.vectorize(lambda x: iam_data.get(x, 0.0))(sverweis_1)
            # Find upper bound incidence angles (rounded up to nearest 10°)
            sverweis_3 = (np.abs(Incidence_angle) + 10) - (np.abs(Incidence_angle) + 10) % 10
            # Get IAM values for upper bounds (default to 0.0 if key not found)
            sverweis_4 = np.vectorize(lambda x: iam_data.get(x, 0.0))(sverweis_3)

            # Perform linear interpolation between bounds
            # Handle division by zero for same angle bounds
            denominator = sverweis_3 - sverweis_1
            numerator = sverweis_4 - sverweis_2
            result = np.where(denominator != 0, 
                            sverweis_2 + (np.abs(Incidence_angle) - sverweis_1) / denominator * numerator,
                            sverweis_2)
            return result

        # Calculate IAM factors for both directions
        IAM_EW = IAM(Incidence_angle_EW, IAM_W)  # East-West direction IAM
        IAM_NS = IAM(Incidence_angle_NS, IAM_N)  # North-South direction IAM
        
        # Combined IAM factor as product of directional components
        K_beam = IAM_EW * IAM_NS
    else:
        # No IAM corrections applied if data not provided
        K_beam = None

    return GT_H_Gk, K_beam, GbT, GdT_H_Dk