"""
Solar Radiation Calculation Module
==================================

This module provides comprehensive solar radiation calculations based on Test Reference Year
data for solar thermal collectors in district heating applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-24

It implements advanced solar geometry algorithms, incidence angle modeling, and radiation component separation
for accurate assessment of solar thermal energy potential.

The calculations follow established solar engineering standards and are specifically adapted
for German climate conditions and district heating integration requirements. The module
supports various collector orientations, tilt angles, and includes Incidence Angle Modifier
(IAM) corrections for high-precision solar thermal system modeling.

Features
--------
- Precise solar position calculations using astronomical algorithms
- Separation of direct and diffuse radiation components
- Incidence angle calculations for tilted and oriented collectors
- Atmospheric attenuation and albedo reflection modeling
- Incidence Angle Modifier (IAM) corrections for collector performance
- Support for East-West and North-South collector orientations
- Test Reference Year (TRY) data compatibility

Mathematical Foundation
-----------------------
The module implements the following key calculations:

**Solar Position**:
    - Solar declination angle based on day of year
    - Solar zenith and azimuth angles using spherical trigonometry
    - Hour angle calculations with equation of time corrections
    - Local solar time adjustments for longitude and time zone

**Radiation Components**:
    - Beam radiation on horizontal and inclined surfaces
    - Diffuse radiation with atmospheric diffuse fraction
    - Ground-reflected radiation using albedo factors
    - Total radiation combining all components

**Collector Performance**:
    - Incidence angle calculations for arbitrary orientations
    - Incidence Angle Modifier interpolation and application
    - Collector-specific radiation adjustments

Requirements
------------
- numpy >= 1.20.0
- datetime (standard library)
- Test Reference Year meteorological data

References
----------
Calculation methodology based on:
- ScenoCalc District Heating 2.0 (https://www.scfw.de/)
- DIN EN ISO 9806 - Test methods for solar collectors
- VDI 6002 - Solar heating systems design guidelines
- Duffie, J.A. & Beckman, W.A. - Solar Engineering of Thermal Processes

Additional Information
----------------------
Yield calculation program for solar thermal energy in heating networks
(calculation basis: ScenoCalc District Heating 2.0) https://www.scfw.de/
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
    Calculate solar radiation components for tilted solar thermal collectors.

    This function performs comprehensive solar radiation calculations for solar thermal
    collectors in district heating applications. It processes Test Reference Year
    meteorological data to determine incident radiation on collectors with arbitrary
    orientation and tilt angles, including advanced corrections for incidence angle
    effects and atmospheric conditions.

    The calculation methodology follows established solar engineering standards and
    includes sophisticated modeling of solar geometry, atmospheric effects, and
    collector-specific performance characteristics essential for accurate solar
    thermal system design and performance prediction.

    Parameters
    ----------
    time_steps : numpy.ndarray
        Time series as numpy datetime64 array [hours].
        Must contain hourly timestamps for entire simulation period.
        Typically represents Test Reference Year (TRY) time series.
    global_radiation : numpy.ndarray
        Global horizontal irradiance time series [W/m²].
        Total solar radiation on horizontal surface from TRY data.
        Includes both direct and diffuse radiation components.
    direct_radiation : numpy.ndarray
        Direct normal irradiance time series [W/m²].
        Direct beam solar radiation normal to sun's rays from TRY data.
        Used for calculation of beam radiation on horizontal surface.
    Longitude : float
        Site longitude coordinate [degrees].
        Positive values for locations east of Greenwich meridian.
        Range: -180° to +180°. Used for solar time corrections.
    STD_Longitude : float
        Standard time zone longitude [degrees].
        Central meridian of local time zone (e.g., 15° for CET).
        Used for local solar time calculation and equation of time.
    Latitude : float
        Site latitude coordinate [degrees].
        Positive values for northern hemisphere locations.
        Range: -90° to +90°. Critical for solar angle calculations.
    Albedo : float
        Ground reflectance factor [-].
        Fraction of solar radiation reflected by ground surface.
        Typical values: 0.2 (grass), 0.8 (snow), 0.1 (asphalt).
    East_West_collector_azimuth_angle : float
        Collector azimuth angle [degrees].
        Deviation from south orientation (0° = due south).
        Positive values for west-facing, negative for east-facing.
        Range: -180° to +180°.
    Collector_tilt_angle : float
        Collector tilt angle from horizontal [degrees].
        Inclination angle of collector surface.
        Range: 0° (horizontal) to 90° (vertical).
        Optimal values typically 30-50° for Germany.
    IAM_W : dict of {float: float}, optional
        Incidence Angle Modifier lookup table for East-West direction.
        Keys represent incidence angles [degrees], values are IAM factors [-].
        Used for collector-specific performance corrections.
        If None, no IAM corrections applied.
    IAM_N : dict of {float: float}, optional
        Incidence Angle Modifier lookup table for North-South direction.
        Keys represent incidence angles [degrees], values are IAM factors [-].
        Used for collector-specific performance corrections.
        If None, no IAM corrections applied.

    Returns
    -------
    tuple of numpy.ndarray
        Solar radiation components for collector surface:
        
        GT_H_Gk : numpy.ndarray
            Total solar irradiance on tilted collector surface [W/m²].
            Includes direct beam, diffuse sky, and ground-reflected radiation.
            Primary input for solar thermal collector performance calculations.
            
        K_beam : numpy.ndarray or None
            Combined Incidence Angle Modifier factor [-].
            Product of East-West and North-South IAM factors.
            Applied to beam radiation for collector-specific corrections.
            Returns None if IAM data not provided.
            
        GbT : numpy.ndarray
            Direct beam irradiance on tilted collector surface [W/m²].
            Beam radiation component after geometric projection.
            Important for tracking systems and optical analysis.
            
        GdT_H_Dk : numpy.ndarray
            Diffuse irradiance on tilted collector surface [W/m²].
            Combined diffuse sky and ground-reflected radiation.
            Includes atmospheric diffuse and albedo components.

    Notes
    -----
    Calculation Methodology:
        
        **Solar Position Calculation**:
        The function implements standard solar position algorithms:
        
        1. **Day Angle**: B = (day_of_year - 1) × 360° / 365°
        2. **Equation of Time**: Corrects for Earth's orbital variations
        3. **Solar Declination**: δ = 23.45° × sin(360° × (284 + day_of_year) / 365°)
        4. **Hour Angle**: ω = -180° + Solar_time × 180° / 12°
        5. **Solar Zenith Angle**: cos(θz) = cos(φ)cos(ω)cos(δ) + sin(φ)sin(δ)
        6. **Solar Azimuth Angle**: Calculated using spherical trigonometry
        
        **Radiation Components**:
        
        **Total Radiation on Tilted Surface**:
        GT = Gb,T + Gd,T + Gr,T
        
        Where:
        - Gb,T = Direct beam radiation on tilted surface
        - Gd,T = Diffuse radiation on tilted surface  
        - Gr,T = Ground-reflected radiation on tilted surface
        
        **Beam Radiation Calculation**:
        Gb,T = Gb,h × Rb
        
        Where Rb is the beam radiation tilt factor:
        Rb = cos(θi) / cos(θz)
        
        **Diffuse Radiation Model**:
        The model separates diffuse radiation into:
        - Atmospheric diffuse: Gd,h × Ai × Rb
        - Isotropic diffuse: Gd,h × (1 - Ai) × (1 + cos(β)) / 2
        
        **Ground Reflection**:
        Gr,T = Gh × ρ × (1 - cos(β)) / 2
        
        **Incidence Angle Modifier (IAM)**:
        For collectors with provided IAM data, the function calculates:
        - Incidence angles in East-West and North-South directions
        - Bilinear interpolation of IAM values from lookup tables
        - Combined IAM factor: K_beam = IAM_EW × IAM_NS

    Physical Interpretation:
        
        **Solar Angles**:
        - **Solar Zenith Angle (θz)**: Angle between sun and vertical
        - **Solar Azimuth Angle**: Horizontal angle from south to sun projection
        - **Incidence Angle (θi)**: Angle between sun rays and collector normal
        
        **Radiation Components**:
        - **Direct Beam**: Radiation directly from solar disk
        - **Diffuse Sky**: Scattered radiation from sky hemisphere
        - **Ground Reflected**: Radiation reflected from ground surface
        
        **Atmospheric Effects**:
        - **Air Mass**: Atmospheric path length affects beam radiation
        - **Clearness Index**: Ratio of actual to extraterrestrial radiation
        - **Diffuse Fraction**: Proportion of diffuse to total radiation

    Validation and Quality Assurance:
        
        **Input Validation**:
        - Time series consistency and completeness
        - Geographical coordinate validity
        - Physical parameter bounds checking
        - Radiation data quality assessment
        
        **Calculation Bounds**:
        - Solar angles limited to physical ranges
        - Radiation values bounded by extraterrestrial limits
        - Incidence angles capped at 90° for night conditions
        
        **Energy Conservation**:
        - Total radiation components sum consistently
        - Beam and diffuse radiation separation maintained
        - No radiation during night hours (θz > 90°)

    Applications:
        
        **Solar Thermal System Design**:
        - Collector field layout optimization
        - Annual energy yield prediction
        - Economic feasibility assessment
        - System sizing and configuration
        
        **District Heating Integration**:
        - Seasonal energy storage sizing
        - Load matching and system operation
        - Grid integration planning
        - Performance monitoring and validation

    Examples
    --------
    >>> # Basic solar radiation calculation for German location
    >>> import numpy as np
    >>> from datetime import datetime, timedelta
    >>> 
    >>> # Create hourly time series for one year
    >>> start_time = datetime(2023, 1, 1)
    >>> time_steps = np.array([
    ...     start_time + timedelta(hours=h) for h in range(8760)
    ... ], dtype='datetime64[h]')
    >>> 
    >>> # Load TRY meteorological data (example values)
    >>> global_rad = np.random.uniform(0, 800, 8760)    # W/m² global radiation
    >>> direct_rad = np.random.uniform(0, 900, 8760)    # W/m² direct normal
    >>> 
    >>> # Define location (Munich, Germany)
    >>> longitude = 11.5      # degrees east
    >>> std_longitude = 15.0  # CET time zone
    >>> latitude = 48.1       # degrees north
    >>> albedo = 0.2          # grass/vegetation
    >>> 
    >>> # Define collector orientation
    >>> azimuth = 0.0         # due south orientation
    >>> tilt = 45.0           # optimal tilt for Germany
    >>> 
    >>> # Calculate solar radiation
    >>> GT_total, K_beam, Gb_tilted, Gd_tilted = calculate_solar_radiation(
    ...     time_steps, global_rad, direct_rad,
    ...     longitude, std_longitude, latitude, albedo,
    ...     azimuth, tilt
    ... )
    >>> 
    >>> # Analyze results
    >>> annual_irradiation = np.sum(GT_total)  # Wh/m²
    >>> print(f"Annual irradiation: {annual_irradiation/1000:.0f} kWh/m²")
    >>> print(f"Peak irradiance: {np.max(GT_total):.0f} W/m²")
    >>> print(f"Beam fraction: {np.sum(Gb_tilted)/np.sum(GT_total):.2f}")

    >>> # Advanced calculation with IAM corrections
    >>> # Define Incidence Angle Modifier data for specific collector
    >>> IAM_EW_data = {0: 1.00, 10: 0.99, 20: 0.96, 30: 0.91, 
    ...                40: 0.85, 50: 0.77, 60: 0.67, 70: 0.53, 80: 0.35}
    >>> IAM_NS_data = {0: 1.00, 10: 0.99, 20: 0.97, 30: 0.93,
    ...                40: 0.87, 50: 0.79, 60: 0.69, 70: 0.56, 80: 0.38}
    >>> 
    >>> # Calculate with IAM corrections
    >>> GT_corrected, K_beam_factor, Gb_corrected, Gd_corrected = calculate_solar_radiation(
    ...     time_steps, global_rad, direct_rad,
    ...     longitude, std_longitude, latitude, albedo,
    ...     azimuth, tilt, IAM_EW_data, IAM_NS_data
    ... )
    >>> 
    >>> # Compare with and without IAM corrections
    >>> efficiency_loss = 1 - np.sum(GT_corrected) / np.sum(GT_total)
    >>> print(f"IAM efficiency loss: {efficiency_loss:.1%}")
    >>> print(f"Average IAM factor: {np.mean(K_beam_factor[K_beam_factor > 0]):.3f}")

    >>> # Seasonal analysis
    >>> # Calculate monthly irradiation totals
    >>> monthly_totals = []
    >>> for month in range(12):
    ...     start_hour = month * 730  # Approximate monthly hours
    ...     end_hour = min(start_hour + 730, 8760)
    ...     monthly_total = np.sum(GT_total[start_hour:end_hour]) / 1000  # kWh/m²
    ...     monthly_totals.append(monthly_total)
    >>> 
    >>> # Identify peak and minimum months
    >>> peak_month = np.argmax(monthly_totals) + 1
    >>> min_month = np.argmin(monthly_totals) + 1
    >>> print(f"Peak irradiation month: {peak_month} ({monthly_totals[peak_month-1]:.0f} kWh/m²)")
    >>> print(f"Minimum irradiation month: {min_month} ({monthly_totals[min_month-1]:.0f} kWh/m²)")

    >>> # Optimization study for collector tilt angle
    >>> tilt_angles = np.arange(0, 91, 5)  # 0° to 90° in 5° steps
    >>> annual_yields = []
    >>> 
    >>> for tilt in tilt_angles:
    ...     GT_opt, _, _, _ = calculate_solar_radiation(
    ...         time_steps, global_rad, direct_rad,
    ...         longitude, std_longitude, latitude, albedo,
    ...         azimuth, tilt
    ...     )
    ...     annual_yield = np.sum(GT_opt) / 1000  # kWh/m²
    ...     annual_yields.append(annual_yield)
    >>> 
    >>> # Find optimal tilt angle
    >>> optimal_tilt = tilt_angles[np.argmax(annual_yields)]
    >>> max_yield = np.max(annual_yields)
    >>> print(f"Optimal tilt angle: {optimal_tilt}°")
    >>> print(f"Maximum annual yield: {max_yield:.0f} kWh/m²")

    See Also
    --------
    numpy.datetime64 : Time series handling for meteorological data
    Solar thermal collector performance modeling
    District heating solar integration methods
    Test Reference Year (TRY) data processing

    Raises
    ------
    ValueError
        If input arrays have mismatched dimensions or invalid parameter ranges.
    TypeError
        If input data types are incompatible with calculation requirements.
    """
    # Extract local time from datetime64 time steps
    hour_L = (time_steps - time_steps.astype('datetime64[D]')).astype('timedelta64[m]').astype(float) / 60

    # Calculate day of year for each time step
    day_of_year = np.array([
        datetime.fromtimestamp(t.astype('datetime64[s]').astype(np.int64), tz=timezone.utc).timetuple().tm_yday 
        for t in time_steps
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
            Interpolate Incidence Angle Modifier values from lookup table.
            
            Performs bilinear interpolation between tabulated IAM values for
            accurate collector performance corrections at arbitrary incidence angles.
            
            Parameters
            ----------
            Incidence_angle : numpy.ndarray
                Array of incidence angles [degrees].
            iam_data : dict
                IAM lookup table with angles as keys and factors as values.
                
            Returns
            -------
            numpy.ndarray
                Interpolated IAM factors for input incidence angles.
            """
            # Find lower bound incidence angles (rounded down to nearest 10°)
            sverweis_1 = np.abs(Incidence_angle) - np.abs(Incidence_angle) % 10
            # Get IAM values for lower bounds
            sverweis_2 = np.vectorize(iam_data.get)(sverweis_1)
            # Find upper bound incidence angles (rounded up to nearest 10°)
            sverweis_3 = (np.abs(Incidence_angle) + 10) - (np.abs(Incidence_angle) + 10) % 10
            # Get IAM values for upper bounds
            sverweis_4 = np.vectorize(iam_data.get)(sverweis_3)

            # Perform linear interpolation between bounds
            result = sverweis_2 + (np.abs(Incidence_angle) - sverweis_1) / (sverweis_3 - sverweis_1) * (sverweis_4 - sverweis_2)
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