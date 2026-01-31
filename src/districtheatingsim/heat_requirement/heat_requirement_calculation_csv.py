"""
Heat demand profile generation from CSV building data.

Integrates VDI 4655 and BDEW calculation methods for batch processing
of building portfolios with temperature curves for district heating design.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
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
    Generate heat demand profiles from CSV building data.

    :param data: Building data (Wärmebedarf, Gebäudetyp, Subtyp, WW_Anteil, Normaußentemperatur, VLT_max, RLT_max, Steigung_Heizkurve)
    :type data: pd.DataFrame
    :param TRY: Path to Test Reference Year weather data file
    :type TRY: str
    :param calc_method: Calculation method ('Datensatz', 'VDI4655', or 'BDEW')
    :type calc_method: str
    :return: Tuple of (time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_W, supply_temp, return_temp, air_temp)
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    :raises KeyError: If required CSV columns are missing
    :raises ValueError: If data types are invalid
    :raises FileNotFoundError: If TRY file not found
    
    .. note::
        'Datensatz' mode auto-selects VDI4655 for residential (EFH/MFH), BDEW for commercial buildings.
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

    :param data: Building data (VLT_max, RLT_max, Steigung_Heizkurve, Normaußentemperatur)
    :type data: pd.DataFrame
    :param hourly_air_temperatures: Hourly outdoor temperature [°C]
    :type hourly_air_temperatures: np.ndarray
    :return: Tuple of (supply_temperature_curve, return_temperature_curve)
    :rtype: Tuple[np.ndarray, np.ndarray]
    
    .. note::
        Weather-compensated curves: T_supply = T_max + slope × (T_outdoor - T_design)
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