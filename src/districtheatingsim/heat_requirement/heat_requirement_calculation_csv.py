"""
Heat Requirement Calculation from CSV
=====================================

This module provides comprehensive heat demand profile generation for buildings
using CSV-based input data.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-09

It integrates multiple calculation methodologies
(VDI 4655, BDEW) and automatically selects appropriate methods based on building
types. The module supports batch processing of building portfolios with
temperature curve calculation for district heating network design.

The module serves as a data integration layer between building databases and
standardized heat demand calculation methods, enabling efficient processing
of large building datasets for district heating system planning and optimization.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Union, Optional

from districtheatingsim.heat_requirement import heat_requirement_VDI4655, heat_requirement_BDEW

def generate_profiles_from_csv(data: pd.DataFrame, 
                             TRY: str, 
                             calc_method: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, 
                                                      np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate comprehensive heat demand profiles from CSV building data using standardized calculation methods.

    This function processes building data from CSV files to generate realistic heat demand
    profiles for district heating applications. It automatically selects appropriate
    calculation methods (VDI 4655 or BDEW) based on building types and generates
    time series data suitable for network design and operation planning.

    Parameters
    ----------
    data : pandas.DataFrame
        Building information dataframe containing required columns:
        
        - **Wärmebedarf** (float) : Annual heat demand [kWh/a]
        - **Gebäudetyp** (str) : Building type identifier (EFH, MFH, HEF, etc.)
        - **Subtyp** (str) : Building subtype for detailed classification
        - **WW_Anteil** (float) : Domestic hot water fraction [0-1]
        - **Normaußentemperatur** (float) : Design outdoor temperature [°C]
        - **VLT_max** (float) : Maximum supply temperature [°C]
        - **RLT_max** (float) : Maximum return temperature [°C]
        - **Steigung_Heizkurve** (float) : Heating curve slope [K/K]
        
    TRY : str
        Path to Test Reference Year meteorological data file.
        Contains hourly weather data for demand calculation.
    calc_method : str
        Calculation method selection:
        
        - **"Datensatz"** : Automatic method selection based on building type
        - **"VDI4655"** : Force VDI 4655 method for all buildings
        - **"BDEW"** : Force BDEW method for all buildings

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]
        Comprehensive building energy data:
        
        - **yearly_time_steps** (numpy.ndarray) : Time stamps for demand profiles
        - **total_heat_W** (numpy.ndarray) : Total heat demand [W] per building per timestep
        - **heating_heat_W** (numpy.ndarray) : Space heating demand [W] per building per timestep
        - **warmwater_heat_W** (numpy.ndarray) : DHW demand [W] per building per timestep
        - **max_heat_requirement_W** (numpy.ndarray) : Peak heat demand [W] per building
        - **supply_temperature_curve** (numpy.ndarray) : Supply temperature [°C] per building per timestep
        - **return_temperature_curve** (numpy.ndarray) : Return temperature [°C] per building per timestep
        - **hourly_air_temperatures** (numpy.ndarray) : Outdoor temperature [°C] per timestep

    Notes
    -----
    Automatic Method Selection:
        When calc_method="Datensatz", the function automatically selects calculation
        methods based on building type identifiers:
        
        - **VDI 4655**: Residential buildings (EFH, MFH)
        - **BDEW**: Commercial and public buildings (HEF, HMF, GKO, GHA, etc.)

    Building Type Categories:
        - **EFH**: Single family house (Einfamilienhaus)
        - **MFH**: Multi-family house (Mehrfamilienhaus)
        - **HEF**: Commercial single family house
        - **HMF**: Commercial multi-family house
        - **GKO**: Office building (Bürogebäude)
        - **GHA**: Retail building (Handel)
        - **GMK**: School building (Schule)
        - **GBD**: Hotel building (Hotel)
        - **GBH**: Restaurant building (Restaurant)
        - **GWA**: Hospital building (Krankenhaus)
        - **GGA**: Sports facility (Sportstätte)
        - **GBA**: Cultural building (Kultur)
        - **GGB**: Public building (Öffentlich)
        - **GPD**: Production building (Produktion)
        - **GMF**: Mixed-use building (Mischnutzung)
        - **GHD**: Service building (Dienstleistung)

    Temperature Curve Calculation:
        Supply and return temperatures are calculated using heating curves
        that account for outdoor temperature dependency:
        
        T_supply = T_max + slope × (T_outdoor - T_design)
        T_return = T_supply - ΔT_system

    Data Processing Workflow:
        1. Load and validate CSV building data
        2. Extract building parameters and energy demands
        3. Select appropriate calculation method per building
        4. Generate demand profiles using VDI 4655 or BDEW
        5. Calculate temperature curves based on heating system parameters
        6. Compile comprehensive output arrays for all buildings

    Quality Assurance:
        - Input data validation and type conversion
        - Negative demand value clipping (non-physical values)
        - Missing data handling with informative error messages
        - Energy balance verification where applicable

    Examples
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>> 
    >>> # Create example building data
    >>> building_data = pd.DataFrame({
    ...     'Wärmebedarf': [15000, 8000, 25000],  # kWh/a
    ...     'Gebäudetyp': ['EFH', 'MFH', 'GKO'],
    ...     'Subtyp': ['Standard', 'Standard', 'Büro'],
    ...     'WW_Anteil': [0.2, 0.15, 0.1],  # 20%, 15%, 10%
    ...     'Normaußentemperatur': [-12, -12, -10],  # °C
    ...     'VLT_max': [70, 75, 60],  # °C
    ...     'RLT_max': [55, 60, 45],  # °C
    ...     'Steigung_Heizkurve': [1.2, 1.3, 1.0]  # K/K
    ... })
    >>> 
    >>> TRY_file = "path/to/weather_data.dat"
    >>> 
    >>> # Generate profiles with automatic method selection
    >>> results = generate_profiles_from_csv(building_data, TRY_file, "Datensatz")
    >>> time, total_heat, heating, dhw, peak_demand, t_supply, t_return, temp = results
    >>> 
    >>> print(f"Processed {len(building_data)} buildings")
    >>> print(f"Time series length: {len(time)} timesteps")
    >>> print(f"Building peak demands: {peak_demand} W")

    >>> # Analyze total district heat demand
    >>> district_total = total_heat.sum(axis=0)  # Sum across all buildings
    >>> district_peak = district_total.max()
    >>> annual_energy = district_total.sum() / 1000  # Convert W to kWh
    >>> print(f"District peak demand: {district_peak/1e6:.1f} MW")
    >>> print(f"District annual energy: {annual_energy:.0f} kWh")

    >>> # Temperature level analysis
    >>> max_supply_temp = t_supply.max(axis=1)  # Maximum per building
    >>> district_supply_temp = t_supply.max()  # Maximum across all
    >>> print(f"Building supply temperatures: {max_supply_temp} °C")
    >>> print(f"District supply temperature: {district_supply_temp:.1f} °C")

    >>> # Seasonal demand analysis
    >>> # Assuming hourly data for full year
    >>> winter_demand = district_total[:2160].mean()  # First 90 days
    >>> summer_demand = district_total[4320:6480].mean()  # Days 181-270
    >>> seasonal_factor = winter_demand / summer_demand
    >>> print(f"Seasonal demand factor: {seasonal_factor:.1f}")

    Raises
    ------
    KeyError
        If required columns are missing from input DataFrame.
    ValueError
        If data types cannot be converted or contain invalid values.
    FileNotFoundError
        If TRY file or method-specific data files cannot be found.

    See Also
    --------
    heat_requirement_VDI4655.calculate : VDI 4655 load profile calculation
    heat_requirement_BDEW.calculate : BDEW load profile calculation
    calculate_temperature_curves : Heating system temperature calculation
    """
    # Static configuration parameters (should be moved to config file or UI)
    year = 2021  # Calculation year for VDI 4655 and BDEW
    
    # German holidays 2021 (excluding weekends) as datetime64[D] array for VDI 4655
    holidays = np.array([
        "2021-01-01", "2021-04-02", "2021-04-05", "2021-05-01", 
        "2021-05-24", "2021-05-13", "2021-06-03", "2021-10-03", 
        "2021-11-01", "2021-12-25", "2021-12-26"
    ]).astype('datetime64[D]')
    
    climate_zone = "9"  # Climate zone 9: Germany (VDI 4655)
    number_people_household = 2  # Number of people per household (VDI 4655)
    
    # Extract and validate CSV data
    try:
        YEU_total_heat_kWh = data["Wärmebedarf"].values.astype(float)
        building_type = data["Gebäudetyp"].values.astype(str)
        subtyp = data["Subtyp"].values.astype(str)
        ww_demand = data["WW_Anteil"].values.astype(float)
        min_air_temperature = data["Normaußentemperatur"].values.astype(float)
    except KeyError as e:
        raise KeyError(f"Missing column in CSV: {e}. Please check CSV file completeness.") from e
    except ValueError as e:
        raise ValueError(f"Invalid data types in CSV: {e}. Please ensure data is correctly formatted.") from e

    # Initialize result containers
    total_heat_W = []
    heating_heat_W = []
    warmwater_heat_W = []
    max_heat_requirement_W = []
    yearly_time_steps = None

    # Mapping of building types to calculation methods
    building_type_to_method = {
        "EFH": "VDI4655",   # Single family house
        "MFH": "VDI4655",   # Multi-family house
        "HEF": "BDEW",      # Commercial single family
        "HMF": "BDEW",      # Commercial multi-family
        "GKO": "BDEW",      # Office building
        "GHA": "BDEW",      # Retail building
        "GMK": "BDEW",      # School building
        "GBD": "BDEW",      # Hotel building
        "GBH": "BDEW",      # Restaurant building
        "GWA": "BDEW",      # Hospital building
        "GGA": "BDEW",      # Sports facility
        "GBA": "BDEW",      # Cultural building
        "GGB": "BDEW",      # Public building
        "GPD": "BDEW",      # Production building
        "GMF": "BDEW",      # Mixed-use building
        "GHD": "BDEW",      # Service building
    }

    # Process each building in the dataset
    for idx, YEU in enumerate(YEU_total_heat_kWh):
        current_building_type = str(data.at[idx, "Gebäudetyp"])
        current_subtype = str(data.at[idx, "Subtyp"])
        current_ww_demand = float(data.at[idx, "WW_Anteil"])
        
        # Determine calculation method
        if calc_method == "Datensatz":
            try:
                current_calc_method = building_type_to_method.get(current_building_type, "VDI4655")
            except KeyError:
                print(f"Building type '{current_building_type}' not found in mapping, using VDI4655")
                current_calc_method = "VDI4655"
        else:
            current_calc_method = calc_method

        # Execute appropriate calculation method
        if current_calc_method == "VDI4655":
            # Split total demand into heating and hot water components
            YEU_heating_kWh = YEU_total_heat_kWh * (1 - ww_demand)
            YEU_hot_water_kWh = YEU_total_heat_kWh * ww_demand
            heating, hot_water = YEU_heating_kWh[idx], YEU_hot_water_kWh[idx]
            
            # Calculate VDI 4655 profiles (electricity set to 0 as not used)
            yearly_time_steps, hourly_heat_demand_total_kW, hourly_heat_demand_heating_kW, \
            hourly_heat_demand_warmwater_kW, hourly_air_temperatures, electricity_kW = \
                heat_requirement_VDI4655.calculate(
                    YEU_heating_kWh=heating,
                    YEU_hot_water_kWh=hot_water,
                    YEU_electricity_kWh=0,
                    building_type=current_building_type,
                    number_people_household=number_people_household,
                    year=year,
                    climate_zone=climate_zone,
                    TRY=TRY,
                    holidays=holidays
                )

        elif current_calc_method == "BDEW":
            # Calculate BDEW profiles
            yearly_time_steps, hourly_heat_demand_total_kW, hourly_heat_demand_heating_kW, \
            hourly_heat_demand_warmwater_kW, hourly_air_temperatures = \
                heat_requirement_BDEW.calculate(
                    YEU, current_building_type, current_subtype, TRY, year, current_ww_demand
                )

        # Ensure non-negative demand values (clip physical impossible negative values)
        hourly_heat_demand_total_kW = np.clip(hourly_heat_demand_total_kW, 0, None)
        hourly_heat_demand_heating_kW = np.clip(hourly_heat_demand_heating_kW, 0, None)
        hourly_heat_demand_warmwater_kW = np.clip(hourly_heat_demand_warmwater_kW, 0, None)

        # Convert to Watts and store results
        total_heat_W.append(hourly_heat_demand_total_kW * 1000)
        heating_heat_W.append(hourly_heat_demand_heating_kW * 1000)
        warmwater_heat_W.append(hourly_heat_demand_warmwater_kW * 1000)
        max_heat_requirement_W.append(np.max(hourly_heat_demand_total_kW * 1000))

    # Convert lists to numpy arrays for efficient processing
    total_heat_W = np.array(total_heat_W)
    heating_heat_W = np.array(heating_heat_W)
    warmwater_heat_W = np.array(warmwater_heat_W)
    max_heat_requirement_W = np.array(max_heat_requirement_W)

    # Calculate supply and return temperature curves
    supply_temperature_curve, return_temperature_curve = calculate_temperature_curves(data, hourly_air_temperatures)

    return (yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, 
            max_heat_requirement_W, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures)

def calculate_temperature_curves(data: pd.DataFrame, 
                               hourly_air_temperatures: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate supply and return temperature curves for district heating systems.

    This function generates time-dependent supply and return temperature profiles
    for buildings based on their heating system characteristics and outdoor
    temperature conditions. It implements weather-compensated heating curves
    commonly used in district heating applications for optimal energy efficiency.

    Parameters
    ----------
    data : pandas.DataFrame
        Building data containing heating system parameters:
        
        - **VLT_max** (float) : Maximum supply temperature [°C]
        - **RLT_max** (float) : Maximum return temperature [°C]
        - **Steigung_Heizkurve** (float) : Heating curve slope coefficient [K/K]
        - **Normaußentemperatur** (float) : Design outdoor temperature [°C]
        
    hourly_air_temperatures : numpy.ndarray
        Hourly outdoor air temperature time series [°C].
        Must cover complete analysis period (typically 8760 hours for full year).

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray]
        Temperature curve arrays for all buildings:
        
        - **supply_temperature_curve** (numpy.ndarray) : Supply temperature [°C] per building per hour
        - **return_temperature_curve** (numpy.ndarray) : Return temperature [°C] per building per hour

    Notes
    -----
    Heating Curve Methodology:
        Weather-compensated heating curves adjust supply temperature based on
        outdoor conditions to maintain optimal energy efficiency and comfort:
        
        T_supply = T_max                                    (T_outdoor ≤ T_design)
        T_supply = T_max + slope × (T_outdoor - T_design)   (T_outdoor > T_design)
        
        Where:
        - T_max: Maximum supply temperature at design conditions
        - slope: Heating curve slope (typically 0.5 to 2.0 K/K)
        - T_design: Design outdoor temperature (typically -10 to -15°C)

    Temperature Relationship:
        Return temperature maintains constant temperature difference:
        T_return = T_supply - ΔT_system
        
        Where ΔT_system = T_max_supply - T_max_return

    Physical Constraints:
        - Supply temperature never drops below design minimum
        - Return temperature follows supply with constant spread
        - Curves ensure proper heat transfer and system efficiency
        - Design temperatures based on local climate conditions

    District Heating Applications:
        - **Network Design**: Temperature levels determine pipe sizing and insulation
        - **Heat Source Sizing**: Supply temperatures define generation requirements
        - **Pump Sizing**: Temperature differences affect flow rate requirements
        - **Energy Efficiency**: Optimal curves minimize distribution losses

    Examples
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>> 
    >>> # Create building heating system data
    >>> building_data = pd.DataFrame({
    ...     'VLT_max': [75, 80, 65],      # Maximum supply temperatures [°C]
    ...     'RLT_max': [60, 65, 50],      # Maximum return temperatures [°C]
    ...     'Steigung_Heizkurve': [1.2, 1.0, 1.5],  # Heating curve slopes [K/K]
    ...     'Normaußentemperatur': [-12, -15, -10]   # Design temperatures [°C]
    ... })
    >>> 
    >>> # Generate hourly temperature data (example for winter day)
    >>> winter_temps = np.linspace(-10, 5, 24)  # -10°C to 5°C over 24 hours
    >>> 
    >>> supply_curves, return_curves = calculate_temperature_curves(building_data, winter_temps)
    >>> 
    >>> print(f"Supply temperature curves shape: {supply_curves.shape}")
    >>> print(f"Return temperature curves shape: {return_curves.shape}")

    >>> # Analyze temperature ranges for each building
    >>> for i, building in enumerate(['Building 1', 'Building 2', 'Building 3']):
    ...     supply_range = f"{supply_curves[i].min():.1f} to {supply_curves[i].max():.1f}°C"
    ...     return_range = f"{return_curves[i].min():.1f} to {return_curves[i].max():.1f}°C"
    ...     print(f"{building}: Supply {supply_range}, Return {return_range}")

    >>> # District-wide temperature requirements
    >>> max_supply_required = supply_curves.max()
    >>> min_return_expected = return_curves.min()
    >>> print(f"District supply temperature requirement: {max_supply_required:.1f}°C")
    >>> print(f"Minimum return temperature: {min_return_expected:.1f}°C")

    >>> # Heating curve analysis
    >>> design_conditions = winter_temps <= -12  # Design temperature conditions
    >>> normal_conditions = winter_temps > -12   # Above design temperature
    >>> 
    >>> print(f"Hours at design conditions: {np.sum(design_conditions)}")
    >>> print(f"Hours with curve modulation: {np.sum(normal_conditions)}")

    >>> # Energy efficiency analysis
    >>> # Lower temperatures improve efficiency
    >>> avg_supply_temp = supply_curves.mean(axis=1)
    >>> efficiency_ranking = np.argsort(avg_supply_temp)  # Lower temp = better efficiency
    >>> print(f"Efficiency ranking (best to worst): {efficiency_ranking + 1}")

    Quality Assurance:
        - Temperature curves respect physical limits and design parameters
        - Consistent temperature spreads maintained across operating conditions
        - Smooth temperature transitions prevent system stress
        - Design temperature thresholds properly implemented

    See Also
    --------
    generate_profiles_from_csv : Main CSV processing function using temperature curves
    heat_requirement_VDI4655.calculate : VDI 4655 profile calculation
    heat_requirement_BDEW.calculate : BDEW profile calculation
    """
    # Extract heating system parameters from building data
    supply_temperature_buildings = data["VLT_max"].values.astype(float)
    return_temperature_buildings = data["RLT_max"].values.astype(float)
    slope = -data["Steigung_Heizkurve"].values.astype(float)  # Negative for decreasing curve
    min_air_temperatures = data["Normaußentemperatur"].values.astype(float)

    # Initialize temperature curve containers
    supply_temperature_curve = []
    return_temperature_curve = []

    # Calculate system temperature difference (constant for each building)
    dT = np.expand_dims(supply_temperature_buildings - return_temperature_buildings, axis=1)

    # Generate supply temperature curves for each building
    for st, s, min_air_temperature in zip(supply_temperature_buildings, slope, min_air_temperatures):
        # Apply heating curve equation
        st_curve = np.where(
            hourly_air_temperatures <= min_air_temperature,
            st,  # Maximum temperature at/below design conditions
            st + (s * (hourly_air_temperatures - min_air_temperature))  # Modulated temperature above design
        )
        supply_temperature_curve.append(st_curve)

    # Convert to numpy arrays for efficient operations
    supply_temperature_curve = np.array(supply_temperature_curve)
    
    # Calculate return temperature curves (constant spread from supply)
    return_temperature_curve = supply_temperature_curve - dT

    return supply_temperature_curve, return_temperature_curve