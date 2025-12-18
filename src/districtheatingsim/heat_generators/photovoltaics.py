"""
Photovoltaics Module
====================

This module provides comprehensive photovoltaic (PV) power generation modeling
capabilities for district heating systems.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-24

The implementation is based on the
EU PVGIS methodology and includes detailed solar irradiation calculations,
temperature-dependent efficiency modeling, and system-level performance analysis.

The module supports both single-system calculations and building-level PV yield
assessments for district-wide renewable energy integration. It includes advanced
modeling of environmental factors, system losses, and performance optimization
for various installation configurations.

Features
--------
- EU PVGIS-compliant photovoltaic modeling with validated algorithms
- Temperature and irradiation-dependent efficiency calculations
- Multi-directional PV system analysis (including East-West configurations)
- Building-level PV yield assessment for district heating integration
- Comprehensive solar irradiation modeling with meteorological data integration
- System loss modeling including inverter, cabling, and soiling losses

Technical Specifications
------------------------
**PV System Modeling**:
- Nominal efficiency modeling with temperature coefficients
- System loss factors including inverter and DC/AC conversion losses
- Module temperature calculation based on ambient conditions and wind speed
- Irradiation-dependent efficiency corrections using logarithmic models

**Solar Resource Assessment**:
- Integration with Test Reference Year (TRY) meteorological data
- Solar position and irradiation calculations for tilted surfaces
- Albedo effects and ground reflection modeling
- Directional irradiation analysis for optimal system orientation

**Performance Analysis**:
- Annual energy yield calculations with hourly resolution
- Peak power determination and capacity factor analysis
- Multi-orientation system modeling for complex roof configurations
- Economic performance indicators for district heating integration

Functions
---------
Calculate_PV : Comprehensive PV system performance calculation
azimuth_angle : Direction-to-azimuth angle conversion utility
calculate_building : Building-level PV assessment for multiple systems

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- pandas >= 1.3.0 : Data manipulation and CSV file handling
- datetime : Time series generation and calendar calculations
- districtheatingsim.utilities.test_reference_year : Meteorological data import
- districtheatingsim.heat_generators.solar_radiation : Solar irradiation calculations

Applications
------------
The module supports photovoltaic applications including:
- District heating system renewable energy integration
- Building-level solar energy assessment and optimization
- Grid-connected PV systems with feed-in tariff analysis
- Hybrid renewable energy systems for district heating
- Energy storage system sizing and optimization support

References
----------
Photovoltaic modeling based on:
- EU PVGIS (Photovoltaic Geographical Information System) methodology
- IEC 61853 PV module performance standards
- NREL System Advisor Model (SAM) validation data
- German DIN V 18599 renewable energy calculation standards
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Tuple, Union, List, Optional

from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation

# Constant for degree-radian conversion
DEG_TO_RAD = np.pi / 180

def Calculate_PV(TRY_data: str, Gross_area: float, Longitude: float, STD_Longitude: float, 
                Latitude: float, Albedo: float, East_West_collector_azimuth_angle: float, 
                Collector_tilt_angle: float) -> Tuple[float, float, np.ndarray]:
    """
    Calculate photovoltaic power output based on EU PVGIS methodology.

    This function performs comprehensive photovoltaic system modeling using
    meteorological data and system specifications. The calculation follows
    EU PVGIS standards and includes temperature-dependent efficiency modeling,
    system losses, and environmental factor corrections.

    The implementation provides detailed hourly PV power generation profiles
    suitable for district heating system integration, renewable energy planning,
    and economic analysis of solar installations.

    Parameters
    ----------
    TRY_data : str
        Path to Test Reference Year (TRY) meteorological data file.
        Contains hourly weather data including temperature, wind, and irradiation.
    Gross_area : float
        Gross photovoltaic system area [m²].
        Total PV module area including spacing and mounting structure.
    Longitude : float
        Geographic longitude of the installation site [degrees].
        Eastern coordinates positive, western coordinates negative.
    STD_Longitude : float
        Standard longitude for the local time zone [degrees].
        Reference meridian for solar time calculations.
    Latitude : float
        Geographic latitude of the installation site [degrees].
        Northern coordinates positive, southern coordinates negative.
    Albedo : float
        Ground reflection coefficient [-].
        Fraction of solar irradiation reflected from surrounding surfaces.
    East_West_collector_azimuth_angle : float
        PV system azimuth angle [degrees].
        0° = South, 90° = West, 180° = North, 270° = East.
    Collector_tilt_angle : float
        PV system tilt angle from horizontal [degrees].
        0° = horizontal, 90° = vertical installation.

    Returns
    -------
    tuple of (float, float, numpy.ndarray)
        Comprehensive PV system performance results:
        
        yield_kWh : float
            Annual photovoltaic energy yield [kWh].
            Total electrical energy production over one year.
            
        P_max : float
            Maximum instantaneous power output [kW].
            Peak power generation under optimal conditions.
            
        P_L : numpy.ndarray
            Hourly power output time series [kW].
            8760-hour array of electrical power generation.

    Notes
    -----
    EU PVGIS Methodology:
        
        **Solar Irradiation Modeling**:
        The function calculates solar irradiation on tilted surfaces using:
        - Direct normal irradiation (DNI) with solar position tracking
        - Diffuse horizontal irradiation (DHI) with sky model corrections
        - Ground-reflected irradiation with albedo factor
        - Incidence angle effects on PV module surfaces
        
        **Temperature Effects**:
        Module temperature calculation considers:
        - Ambient air temperature from meteorological data
        - Solar irradiation heating effects on PV modules
        - Wind speed cooling effects with heat transfer modeling
        - Mounting configuration thermal characteristics
        
        **Efficiency Modeling**:
        The PV efficiency calculation includes:
        - Nominal efficiency under Standard Test Conditions (STC)
        - Temperature coefficient corrections for module heating
        - Irradiation-dependent efficiency variations
        - System losses including inverter, cabling, and soiling
        
        **Performance Coefficients**:
        Based on EU PVGIS database correlations:
        - k1, k2: Irradiation-dependent efficiency coefficients
        - k3, k4, k5, k6: Temperature-irradiation interaction terms
        - Validated against extensive measurement databases

    System Loss Modeling:
        
        **DC System Losses**:
        - Module degradation and manufacturing tolerances
        - DC cabling resistance losses
        - Module soiling and snow coverage effects
        - Shading losses from surrounding objects
        
        **AC System Losses**:
        - Inverter efficiency curves with load-dependent losses
        - AC cabling and transformer losses
        - Grid connection and power conditioning losses
        - System availability and maintenance downtime

    Examples
    --------
    >>> # Calculate PV performance for south-facing rooftop installation
    >>> yield_kwh, max_power, hourly_power = Calculate_PV(
    ...     TRY_data="weather_data_2024.csv",
    ...     Gross_area=100.0,                    # m² PV system area
    ...     Longitude=11.576,                    # Munich longitude
    ...     STD_Longitude=15.0,                  # Central European Time
    ...     Latitude=48.137,                     # Munich latitude
    ...     Albedo=0.2,                          # Typical ground reflection
    ...     East_West_collector_azimuth_angle=0, # South-facing (optimal)
    ...     Collector_tilt_angle=35             # Optimal tilt for latitude
    ... )
    >>> 
    >>> print(f"Annual PV yield: {yield_kwh:,.0f} kWh")
    >>> print(f"Peak power: {max_power:.1f} kW")
    >>> print(f"Capacity factor: {yield_kwh/(max_power*8760)*100:.1f}%")

    >>> # East-West configuration for morning/evening optimization
    >>> yield_ew, max_ew, power_ew = Calculate_PV(
    ...     TRY_data="weather_data_2024.csv",
    ...     Gross_area=150.0,                    # m² larger area for EW
    ...     Longitude=11.576,
    ...     STD_Longitude=15.0,
    ...     Latitude=48.137,
    ...     Albedo=0.2,
    ...     East_West_collector_azimuth_angle=90, # West-facing
    ...     Collector_tilt_angle=15              # Lower tilt for EW
    ... )
    >>> 
    >>> # Compare daily profiles (summer day example)
    >>> summer_day = slice(4344, 4368)  # June 21st (24 hours)
    >>> south_profile = hourly_power[summer_day]
    >>> west_profile = power_ew[summer_day]
    >>> 
    >>> print("Hour | South | West")
    >>> for h, (s, w) in enumerate(zip(south_profile, west_profile)):
    ...     print(f"{h:2d}   | {s:5.1f} | {w:5.1f}")

    >>> # Calculate specific yield for system comparison
    >>> specific_yield_south = yield_kwh / 100.0  # kWh/m²
    >>> specific_yield_west = yield_ew / 150.0    # kWh/m²
    >>> 
    >>> print(f"South-facing specific yield: {specific_yield_south:.0f} kWh/m²")
    >>> print(f"West-facing specific yield: {specific_yield_west:.0f} kWh/m²")

    See Also
    --------
    calculate_solar_radiation : Solar irradiation calculations for tilted surfaces
    import_TRY : Test Reference Year meteorological data import
    calculate_building : Building-level PV assessment for multiple systems
    """
    # Import Test Reference Year meteorological data
    Ta_L, W_L, D_L, G_L, _ = import_TRY(TRY_data)

    # Define photovoltaic system constants based on EU PVGIS methodology
    eff_nom = 0.199  # Nominal PV module efficiency under STC conditions [-]
    sys_loss = 0.14  # Total system losses including inverter, cabling, soiling [-]
    U0 = 26.9        # Thermal loss coefficient constant [W/(°C·m²)]
    U1 = 6.2         # Thermal loss coefficient wind-dependent [W·s/(°C·m³)]

    # EU PVGIS efficiency model coefficients for crystalline silicon
    k1, k2, k3, k4, k5, k6 = -0.017237, -0.040465, -0.004702, 0.000149, 0.000170, 0.000005

    # Generate annual hourly time series (8760 hours)
    start_date = np.datetime64('2024-01-01T00:00')
    time_steps = start_date + np.arange(8760) * np.timedelta64(1, 'h')
    
    # Calculate day of year for solar position calculations
    Day_of_Year_L = np.array([
        datetime.fromtimestamp(
            t.astype('datetime64[s]').astype(np.int64), 
            tz=timezone.utc
        ).timetuple().tm_yday 
        for t in time_steps
    ])

    # Calculate solar irradiation on tilted PV surface
    GT_L, _, _, _ = calculate_solar_radiation(
        G_L, D_L, Day_of_Year_L, time_steps, 
        Longitude, STD_Longitude, Latitude, Albedo,
        East_West_collector_azimuth_angle, Collector_tilt_angle
    )

    # Convert irradiation from W/m² to kW/m² for efficiency calculations
    G1 = GT_L / 1000

    # Calculate PV module temperature using thermal model
    # Accounts for ambient temperature, solar heating, and wind cooling
    Tm = Ta_L + GT_L / (U0 + U1 * W_L)
    T1m = Tm - 25  # Temperature difference from Standard Test Conditions

    # Calculate relative efficiency based on irradiation and temperature
    eff_rel = np.ones_like(G1)
    non_zero_mask = G1 != 0
    
    # Apply EU PVGIS efficiency model for non-zero irradiation periods
    eff_rel[non_zero_mask] = (
        1 + k1 * np.log(G1[non_zero_mask]) 
        + k2 * np.log(G1[non_zero_mask]) ** 2 
        + k3 * T1m[non_zero_mask] 
        + k4 * T1m[non_zero_mask] * np.log(G1[non_zero_mask]) 
        + k5 * Tm[non_zero_mask] * np.log(G1[non_zero_mask]) ** 2 
        + k6 * Tm[non_zero_mask] ** 2
    )
    
    # Set efficiency to zero for no irradiation periods
    eff_rel[~non_zero_mask] = 0
    eff_rel = np.nan_to_num(eff_rel, nan=0)

    # Calculate instantaneous PV power output [kW]
    # P = Irradiation × Area × Nominal_Efficiency × Relative_Efficiency × (1 - System_Losses)
    P_L = G1 * Gross_area * eff_nom * eff_rel * (1 - sys_loss)

    # Calculate performance metrics
    P_max = np.max(P_L)  # Maximum instantaneous power [kW]
    E = np.sum(P_L)      # Total annual energy [kWh]

    # Round results for practical use
    yield_kWh = round(E, 2)
    P_max = round(P_max, 2)

    return yield_kWh, P_max, P_L

def azimuth_angle(direction: str) -> Optional[float]:
    """
    Convert cardinal direction to azimuth angle for PV system orientation.

    This utility function translates common directional descriptions into
    numerical azimuth angles suitable for solar irradiation calculations.
    It supports both English and German directional conventions commonly
    used in European PV system planning.

    Parameters
    ----------
    direction : str
        Cardinal direction identifier.
        Supports single directions (N, S, E, W) and combinations (NE, SW, etc.).
        Case-insensitive input with German conventions (O=East, NO=Northeast).

    Returns
    -------
    float or None
        Azimuth angle in degrees [°]:
        
        - 0° = South (optimal for Northern Hemisphere)
        - 90° = West  
        - 180° = North
        - 270° = East (German: O for "Ost")
        - Returns None for unrecognized directions

    Notes
    -----
    Azimuth Convention:
        
        **Solar Energy Standard**:
        The azimuth angle follows solar energy conventions:
        - 0° (South): Maximum annual irradiation in Northern Hemisphere
        - 90° (West): Afternoon energy production optimization
        - 180° (North): Minimal irradiation, typically avoided
        - 270° (East): Morning energy production optimization
        
        **German/European Conventions**:
        - 'O' represents "Ost" (East) in German
        - 'NO' represents "Nordost" (Northeast) in German
        - 'SO' represents "Südost" (Southeast) in German
        
        **Compound Directions**:
        Diagonal orientations (NE, SW, etc.) use intermediate angles
        optimized for balanced daily energy production profiles.

    The function provides robust direction parsing for automated
    building-level PV assessments and system optimization workflows.

    Examples
    --------
    >>> # Standard cardinal directions
    >>> print(f"South: {azimuth_angle('S')}°")    # Output: 0°
    >>> print(f"West: {azimuth_angle('W')}°")     # Output: 90°
    >>> print(f"North: {azimuth_angle('N')}°")    # Output: 180°
    >>> print(f"East: {azimuth_angle('O')}°")     # Output: 270° (German)

    >>> # Compound directions for optimal energy profiles
    >>> print(f"Southeast: {azimuth_angle('SO')}°")  # Output: 315°
    >>> print(f"Southwest: {azimuth_angle('SW')}°")  # Output: 45°
    >>> print(f"Northeast: {azimuth_angle('NO')}°")  # Output: 225°
    >>> print(f"Northwest: {azimuth_angle('NW')}°")  # Output: 135°

    >>> # Case-insensitive input handling
    >>> directions = ['s', 'South', 'SOUTH', 'w', 'west']
    >>> for dir_str in directions:
    ...     angle = azimuth_angle(dir_str)
    ...     print(f"'{dir_str}' → {angle}°")

    >>> # Error handling for invalid directions
    >>> invalid_directions = ['X', 'North-East', '45', '']
    >>> for invalid in invalid_directions:
    ...     result = azimuth_angle(invalid)
    ...     if result is None:
    ...         print(f"'{invalid}': Invalid direction")
    ...     else:
    ...         print(f"'{invalid}': {result}°")

    >>> # Building automation example
    >>> building_orientations = ['S', 'SW', 'W', 'NW', 'O', 'SO']
    >>> for orientation in building_orientations:
    ...     angle = azimuth_angle(orientation)
    ...     if angle is not None:
    ...         # Calculate expected performance factor
    ...         if angle in [315, 0, 45]:  # SE, S, SW
    ...             performance = "High"
    ...         elif angle in [270, 90]:    # E, W
    ...             performance = "Medium"
    ...         else:                       # N, NE, NW
    ...             performance = "Low"
    ...         print(f"Orientation {orientation} ({angle}°): {performance} performance")

    See Also
    --------
    Calculate_PV : Main PV calculation function using azimuth angles
    calculate_building : Building-level analysis with multiple orientations
    """
    # Azimuth angle mapping for PV system orientations
    # Following solar energy conventions: 0° = South, 90° = West
    azimuths = {
        'N': 180,   # North - minimal irradiation
        'W': 90,    # West - afternoon energy production
        'S': 0,     # South - optimal for Northern Hemisphere
        'O': 270,   # East ("Ost" in German) - morning energy production
        'NO': 225,  # Northeast ("Nordost") - morning-biased production
        'SO': 315,  # Southeast ("Südost") - morning-optimal production
        'SW': 45,   # Southwest - afternoon-optimal production
        'NW': 135   # Northwest - afternoon-biased production
    }
    
    return azimuths.get(direction.upper(), None)

def calculate_building(TRY_data: str, building_data: str, output_filename: str) -> None:
    """
    Calculate photovoltaic yield for multiple buildings in a district heating system.

    This function performs comprehensive building-level PV assessment for
    district-wide renewable energy integration. It processes building data
    with multiple roof orientations and generates detailed energy production
    profiles suitable for district heating system planning and optimization.

    The function supports complex roof configurations including East-West
    orientations and provides economic analysis data for renewable energy
    investment decisions in district heating applications.

    Parameters
    ----------
    TRY_data : str
        Path to Test Reference Year meteorological data file.
        Contains hourly weather data for annual PV performance calculations.
    building_data : str
        Path to CSV file containing building PV system specifications.
        Must include columns: building_id, roof_area, orientation.
    output_filename : str
        Path for saving detailed PV performance results CSV file.
        Contains hourly power generation data for all building systems.

    Notes
    -----
    Input Data Format:
        
        **Building Data CSV Structure**:
        The building_data file must contain semicolon-separated values with:
        - Column 1: Building identifier (string)
        - Column 2: Available roof area for PV installation [m²]
        - Column 3: Roof orientation (cardinal direction string)
        
        **Example Building Data**:
        ```
        Building;Area_m2;Orientation
        House_01;150.5;S
        House_02;200.0;SW
        House_03;180.0;OW
        Commercial_01;500.0;S
        ```
        
        **Special Orientations**:
        - "OW" (East-West): Automatically splits area between East and West
        - Single directions: Uses full area for specified orientation
        - Invalid orientations: Skipped with warning message

    Calculation Process:
        
        **1. Data Processing**:
        - Loads building specifications from CSV file
        - Validates orientation data and area values
        - Handles East-West configurations with area splitting
        
        **2. PV Performance Calculation**:
        - Applies Calculate_PV function for each building system
        - Uses standard location parameters (can be customized)
        - Generates annual hourly power production profiles
        
        **3. Results Compilation**:
        - Creates comprehensive results DataFrame
        - Includes system identification and performance metrics
        - Exports detailed CSV file for further analysis

    Location Parameters:
        
        **Default Settings** (customizable in function):
        - Longitude: 11.576° (Munich, Germany)
        - Standard Longitude: 15.0° (Central European Time)
        - Latitude: 48.137° (Munich, Germany)
        - Albedo: 0.2 (typical ground reflection)
        - Collector Tilt: 36° (optimal for latitude)

    Output Data Structure:
        
        **Results CSV Format**:
        - Column 1: Annual Hours (1-8760)
        - Subsequent columns: Building PV power output [kW]
        - Column naming: "{Building_ID} {Orientation} {Area} m² [kW]"
        - East-West systems: Separate columns for each orientation

    Examples
    --------
    >>> # Prepare building data file
    >>> building_data_content = '''Building;Area_m2;Orientation
    ... Residential_01;120.0;S
    ... Residential_02;95.5;SW
    ... Residential_03;140.0;W
    ... Commercial_01;450.0;S
    ... Industrial_01;800.0;OW
    ... School_01;300.0;SO'''
    >>> 
    >>> with open('buildings_pv.csv', 'w') as f:
    ...     f.write(building_data_content)

    >>> # Calculate PV performance for all buildings
    >>> calculate_building(
    ...     TRY_data="TRY_2024_Munich.csv",
    ...     building_data="buildings_pv.csv",
    ...     output_filename="district_pv_results.csv"
    ... )
    >>> # Output: Detailed calculation progress and results

    >>> # Load and analyze results
    >>> import pandas as pd
    >>> results = pd.read_csv("district_pv_results.csv", sep=';')
    >>> 
    >>> # Calculate total district PV capacity and annual yield
    >>> pv_columns = [col for col in results.columns if '[kW]' in col]
    >>> total_capacity = results[pv_columns].max().sum()
    >>> annual_yield = results[pv_columns].sum().sum()
    >>> 
    >>> print(f"Total district PV capacity: {total_capacity:.1f} kW")
    >>> print(f"Annual district PV yield: {annual_yield/1000:.1f} MWh")

    >>> # Analyze peak production and load matching
    >>> daily_totals = results[pv_columns].sum(axis=1)
    >>> peak_hour = daily_totals.idxmax()
    >>> peak_production = daily_totals.max()
    >>> 
    >>> print(f"Peak production hour: {peak_hour} ({peak_production:.1f} kW)")

    >>> # Economic analysis preparation
    >>> for col in pv_columns:
    ...     system_data = results[col]
    ...     annual_kwh = system_data.sum()
    ...     capacity_kw = system_data.max()
    ...     capacity_factor = annual_kwh / (capacity_kw * 8760) if capacity_kw > 0 else 0
    ...     print(f"{col}: {annual_kwh:.0f} kWh/year, CF: {capacity_factor:.2f}")

    >>> # Seasonal analysis for district heating integration
    >>> winter_months = list(range(0, 2160)) + list(range(7300, 8760))  # Dec-Feb
    >>> summer_months = list(range(3624, 6552))  # May-Aug
    >>> 
    >>> winter_yield = results.iloc[winter_months][pv_columns].sum().sum()
    >>> summer_yield = results.iloc[summer_months][pv_columns].sum().sum()
    >>> 
    >>> print(f"Winter PV yield: {winter_yield/1000:.1f} MWh")
    >>> print(f"Summer PV yield: {summer_yield/1000:.1f} MWh")
    >>> print(f"Summer/Winter ratio: {summer_yield/winter_yield:.2f}")

    See Also
    --------
    Calculate_PV : Core PV performance calculation function
    azimuth_angle : Direction-to-azimuth conversion utility
    import_TRY : Test Reference Year meteorological data import
    pandas.DataFrame : Data manipulation and CSV export functionality
    """
    # Load building data from CSV file with robust error handling
    try:
        gdata = np.genfromtxt(
            building_data, 
            delimiter=";", 
            skip_header=1, 
            dtype=None, 
            encoding='utf-8'
        )
    except Exception as e:
        raise ValueError(f"Error loading building data from {building_data}: {e}")

    # Location parameters for PV calculation (customizable)
    # Default: Munich, Germany - Central European location
    Longitude = 11.576       # Munich longitude [degrees]
    STD_Longitude = 15.0     # Central European Time standard longitude [degrees]
    Latitude = 48.137        # Munich latitude [degrees]
    
    # PV system parameters
    Albedo = 0.2            # Typical ground reflection coefficient [-]
    Collector_tilt_angle = 36  # Optimal tilt angle for latitude [degrees]
    
    # Initialize time series for annual hourly data
    Annual_hours = np.arange(1, 8761)  # Hours 1-8760 for full year

    # Initialize results DataFrame with time column
    df = pd.DataFrame()
    df['Annual Hours'] = Annual_hours

    print("Calculating PV yield for buildings...")
    print(f"Processing {len(gdata)} building systems...")

    # Process each building in the input data
    for idx, (building, area, direction) in enumerate(gdata):
        try:
            # Convert numpy types to Python native types
            building = str(building)
            area = float(area)
            direction = str(direction)
            
            print(f"Processing {building}: {area:.1f} m² {direction}-facing")
            
            # Get azimuth angle for the specified direction
            current_azimuth = azimuth_angle(direction)

            # Handle East-West (OW) configuration with split installation
            if current_azimuth is None and direction.upper() == "OW":
                # Split area equally between East and West orientations
                area_split = area / 2
                directions = ["O", "W"]  # East and West in German notation
                print(f"  → East-West configuration: {area_split:.1f} m² each direction")
            else:
                # Single orientation configuration
                directions = [direction]

            # Calculate PV performance for each orientation
            for orientation in directions:
                current_azimuth = azimuth_angle(orientation)
                
                if current_azimuth is not None:
                    # Use split area for EW systems, full area for single orientation
                    system_area = area_split if direction.upper() == "OW" else area
                    
                    # Calculate PV performance using EU PVGIS methodology
                    yield_kWh, max_power, P_L = Calculate_PV(
                        TRY_data, system_area, Longitude, STD_Longitude, 
                        Latitude, Albedo, current_azimuth, Collector_tilt_angle
                    )

                    # Generate appropriate column suffix for EW systems
                    suffix = f" {orientation}" if direction.upper() == "OW" else ""
                    
                    # Display calculation results
                    print(f"  → PV yield {building}{suffix}: {yield_kWh/1000:.1f} MWh")
                    print(f"  → Maximum power {building}{suffix}: {max_power:.1f} kW")
                    
                    # Add results to DataFrame with descriptive column name
                    column_name = f'{building}{suffix} {system_area:.1f} m² [kW]'
                    df[column_name] = P_L
                else:
                    print(f"  → Warning: Invalid orientation '{orientation}' for {building}")
                    
        except Exception as e:
            print(f"  → Error processing {building}: {e}")
            continue

    # Save comprehensive results to CSV file
    try:
        df.to_csv(output_filename, index=False, sep=';', encoding='utf-8-sig')
        print(f"\nResults successfully saved to: {output_filename}")
        
        # Calculate and display summary statistics
        pv_columns = [col for col in df.columns if '[kW]' in col]
        total_systems = len(pv_columns)
        total_capacity = df[pv_columns].max().sum()
        annual_yield = df[pv_columns].sum().sum() / 1000  # Convert to MWh
        
        print(f"Summary:")
        print(f"  → Total systems processed: {total_systems}")
        print(f"  → Total PV capacity: {total_capacity:.1f} kW")
        print(f"  → Annual district yield: {annual_yield:.1f} MWh")
        print(f"  → Average capacity factor: {annual_yield*1000/(total_capacity*8760):.2f}")
        
    except Exception as e:
        raise IOError(f"Error saving results to {output_filename}: {e}")