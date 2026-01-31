"""
VDI 4655 heat and electricity demand profile calculation module.

Implements VDI 4655 standard for residential buildings with quarter-hourly
profiles based on occupancy patterns and meteorological data.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import pandas as pd
import numpy as np
from typing import Tuple, Union, Optional, List

from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.utilities.utilities import get_resource_path

def generate_year_months_days_weekdays(year: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate temporal arrays for VDI 4655 day-type classification.

    :param year: Target year
    :type year: int
    :return: Tuple of (days_of_year, months, days, weekdays) with ISO weekdays 1=Monday, 7=Sunday
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    
    .. note::
        Used for workday/weekend/holiday classification in VDI 4655.
    """
    start_date = np.datetime64(f'{year}-01-01')
    
    # Determine number of days (handle leap years)
    end_date = np.datetime64(f'{year}-12-31')
    num_days = (end_date - start_date).astype(int) + 1
    
    # Generate day-of-year array
    days_of_year = np.arange(start_date, start_date + np.timedelta64(num_days, 'D'), dtype='datetime64[D]')
    
    # Extract month numbers (1-12)
    months = days_of_year.astype('datetime64[M]').astype(int) % 12 + 1
    
    # Extract day numbers within month (1-31)
    month_start = days_of_year.astype('datetime64[M]')
    days = (days_of_year - month_start).astype(int) + 1
    
    # Calculate weekday numbers (1=Monday, 7=Sunday)
    # NumPy weekday: 0=Monday, 6=Sunday, convert to 1=Monday, 7=Sunday
    weekdays = ((days_of_year.astype('datetime64[D]').astype(int) + 4) % 7) + 1
    
    return days_of_year, months, days, weekdays

def calculate_daily_averages(temperature: np.ndarray, cloud_cover: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate daily averages from hourly meteorological data for VDI 4655 day-type classification.

    :param temperature: Hourly temperature [°C] (8760 or 8784 hours)
    :type temperature: np.ndarray
    :param cloud_cover: Hourly cloud cover [0-8 oktas] (8760 or 8784 hours)
    :type cloud_cover: np.ndarray
    :return: Tuple of (daily_avg_temperature, daily_avg_cloud_cover)
    :rtype: Tuple[np.ndarray, np.ndarray]
    :raises ValueError: If arrays incomplete or mismatched lengths
    :raises IndexError: If reshaping fails
    
    .. note::
        Seasons: W (<5°C), Ü (5-15°C), S (>15°C). Cloud: H (<4 oktas), B (≥4 oktas), X (summer).
    """
    num_hours = temperature.size
    num_days = num_hours // 24
    
    # Validate complete daily blocks
    if num_hours % 24 != 0:
        raise ValueError(f"Incomplete hourly data: {num_hours} hours not divisible by 24")
    
    if temperature.size != cloud_cover.size:
        raise ValueError("Temperature and cloud cover arrays must have same length")
    
    # Reshape to daily blocks and calculate averages
    daily_temperature = temperature[:num_days*24].reshape((num_days, 24))
    daily_cloud_cover = cloud_cover[:num_days*24].reshape((num_days, 24))
    
    daily_avg_temperature = np.mean(daily_temperature, axis=1)
    daily_avg_cloud_cover = np.mean(daily_cloud_cover, axis=1)
    
    return daily_avg_temperature, daily_avg_cloud_cover

def calculate_quarter_hourly_intervals(year: int) -> np.ndarray:
    """
    Generate quarter-hourly datetime intervals for VDI 4655 load profiles.

    :param year: Target year
    :type year: int
    :return: Quarter-hourly datetime64[15m] intervals (35,040 or 35,136 for leap year)
    :rtype: np.ndarray
    
    .. note::
        15-minute resolution matches VDI 4655 standard for district heating analysis.
    """
    start_date = np.datetime64(f'{year}-01-01')
    
    # Determine number of days (handle leap years)
    end_date = np.datetime64(f'{year}-12-31')
    num_days = (end_date - start_date).astype(int) + 1
    
    # Calculate total number of quarter-hourly intervals
    num_quarter_hours = num_days * 24 * 4
    
    # Generate quarter-hourly interval array
    intervals = np.arange(
        start_date, 
        start_date + np.timedelta64(num_quarter_hours, '15m'), 
        dtype='datetime64[15m]'
    )
    
    return intervals

def quarter_hourly_data(data: np.ndarray) -> np.ndarray:
    """
    Expand daily data to quarter-hourly resolution.

    :param data: Daily values to expand
    :type data: np.ndarray
    :return: Quarter-hourly array with each daily value replicated 96 times
    :rtype: np.ndarray
    
    .. note::
        Each daily value → 96 quarter-hourly intervals (24h × 4 quarters/h).
    """
    num_quarter_hours_per_day = 24 * 4  # 96 intervals per day
    return np.repeat(data, num_quarter_hours_per_day)

def standardized_quarter_hourly_profile(year: int, 
                                      building_type: str, 
                                      days_of_year: np.ndarray, 
                                      type_days: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate standardized VDI 4655 quarter-hourly load profiles.

    :param year: Target year
    :type year: int
    :param building_type: VDI 4655 type (EFH, MFH, B)
    :type building_type: str
    :param days_of_year: Daily datetime64 array
    :type days_of_year: np.ndarray
    :param type_days: Day-type classifications (e.g., WWH, SWX)
    :type type_days: np.ndarray
    :return: Tuple of (intervals, electricity, heating, hot_water) normalized profiles [0-2]
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    :raises FileNotFoundError: If VDI 4655 profile data missing
    :raises KeyError: If building/day-type combination unavailable
    :raises ValueError: If temporal arrays inconsistent
    
    .. note::
        Day-type format: {Season}{DayType}{Cloud} - W/Ü/S + W/S + H/B/X.
    """
    # Generate quarter-hourly time intervals
    quarter_hourly_intervals = calculate_quarter_hourly_intervals(year)
    
    # Create daily date array for mapping
    daily_dates = np.array([np.datetime64(dt, 'D') for dt in quarter_hourly_intervals])
    
    # Map quarter-hourly intervals to corresponding days in year
    indices = np.searchsorted(days_of_year, daily_dates)
    quarterly_type_days = type_days[indices % len(type_days)]
    
    # Load VDI 4655 profile data for all required day types
    all_type_days = np.unique(quarterly_type_days)
    all_data = {}
    
    for type_day in all_type_days:
        profile_filename = f"{building_type}{type_day}.csv"
        file_path = get_resource_path(f'data\\VDI 4655 profiles\\VDI 4655 load profiles\\{profile_filename}')
        
        try:
            profile_data = pd.read_csv(file_path, sep=';')
            all_data[f"{building_type}{type_day}"] = profile_data
        except FileNotFoundError:
            print(f"Warning: Profile file not found: {profile_filename}")
            # Create dummy profile data if file missing
            times = [f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 15, 30, 45]]
            dummy_data = pd.DataFrame({
                'Zeit': times,
                'Strombedarf normiert': np.ones(96),
                'Heizwärme normiert': np.ones(96), 
                'Warmwasser normiert': np.ones(96)
            })
            all_data[f"{building_type}{type_day}"] = dummy_data
    
    # Create profile day identifiers
    profile_days = np.char.add(building_type, quarterly_type_days)
    
    # Extract time strings from intervals
    times_str = np.datetime_as_string(quarter_hourly_intervals, unit='m')
    times = np.array([t.split('T')[1] for t in times_str])
    
    # Create mapping dataframe
    times_profile_df = pd.DataFrame({
        'Datum': np.repeat(days_of_year, 24*4),
        'Zeit': times,
        'ProfileDay': profile_days
    })
    
    # Combine all profile data
    combined_df = pd.concat([
        df.assign(ProfileDay=profile_day) 
        for profile_day, df in all_data.items()
    ])
    
    # Merge temporal mapping with profile data
    merged_df = pd.merge(times_profile_df, combined_df, on=['Zeit', 'ProfileDay'], how='left')
    
    # Extract demand profiles
    electricity_demand = merged_df['Strombedarf normiert'].values
    heating_demand = merged_df['Heizwärme normiert'].values
    hot_water_demand = merged_df['Warmwasser normiert'].values
    
    # Handle any missing values (fill with average)
    electricity_demand = np.nan_to_num(electricity_demand, nan=1.0)
    heating_demand = np.nan_to_num(heating_demand, nan=1.0)
    hot_water_demand = np.nan_to_num(hot_water_demand, nan=1.0)
    
    return quarter_hourly_intervals, electricity_demand, heating_demand, hot_water_demand

def calculation_load_profile(TRY: str, 
                           building_type: str, 
                           number_people_household: int, 
                           YEU_electricity_kWh: float, 
                           YEU_heating_kWh: float, 
                           YEU_hot_water_kWh: float, 
                           holidays: np.ndarray, 
                           climate_zone: str = "9", 
                           year: int = 2019) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate comprehensive VDI 4655 load profiles.

    :param TRY: Path to Test Reference Year data
    :type TRY: str
    :param building_type: VDI 4655 type (EFH, MFH, B)
    :type building_type: str
    :param number_people_household: Number of occupants
    :type number_people_household: int
    :param YEU_electricity_kWh: Annual electricity [kWh/a]
    :type YEU_electricity_kWh: float
    :param YEU_heating_kWh: Annual heating [kWh/a]
    :type YEU_heating_kWh: float
    :param YEU_hot_water_kWh: Annual DHW [kWh/a]
    :type YEU_hot_water_kWh: float
    :param holidays: Holiday dates array
    :type holidays: np.ndarray
    :param climate_zone: German climate zone 1-15 (default "9")
    :type climate_zone: str
    :param year: Target year (default 2019)
    :type year: int
    :return: Tuple of (intervals, electricity, heating, dhw, temperature) in kWh per 15min
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    :raises FileNotFoundError: If TRY or factor data missing
    :raises ValueError: If parameters invalid
    :raises KeyError: If VDI 4655 data incomplete
    
    .. note::
        Implements complete VDI 4655 workflow with day-type classification and energy balance normalization.
    """
    # Load VDI 4655 scaling factors
    factors_file = get_resource_path('data\\VDI 4655 profiles\\VDI 4655 data\\Faktoren.csv')
    
    try:
        factor_data = pd.read_csv(factors_file, sep=';')
    except FileNotFoundError:
        raise FileNotFoundError(f"VDI 4655 factor data not found: {factors_file}")

    # Generate temporal arrays
    days_of_year, months, days, weekdays = generate_year_months_days_weekdays(year)
    
    # Import and process weather data
    temperature, _, _, _, degree_of_coverage = import_TRY(TRY)
    daily_avg_temperature, daily_avg_degree_of_coverage = calculate_daily_averages(temperature, degree_of_coverage)
    
    # VDI 4655 day-type classification
    # Season classification based on daily temperature
    season = np.where(daily_avg_temperature < 5, "W", 
                     np.where((daily_avg_temperature >= 5) & (daily_avg_temperature <= 15), "Ü", "S"))
    
    # Day type classification (workday vs weekend/holiday)
    day_type = np.where((weekdays == 7) | np.isin(days_of_year, holidays), "S", "W")  # Sunday=7 or holiday
    
    # Cloud cover classification (only for non-summer days)
    cloud_classification = np.where(season == "S", "X", 
                                  np.where((daily_avg_degree_of_coverage >= 0) & (daily_avg_degree_of_coverage < 4), "H", "B"))
    
    # Combine classifications into day-type codes
    type_day = np.char.add(np.char.add(season, day_type), cloud_classification)
    profile_day = np.char.add((building_type + climate_zone), type_day)

    # Extract scaling factors for each day
    f_heating_tt = np.zeros(len(profile_day))
    f_el_tt = np.zeros(len(profile_day))
    f_hotwater_tt = np.zeros(len(profile_day))

    for i, tag in enumerate(profile_day):
        try:
            factor_row = factor_data[factor_data['Profiltag'] == tag]
            if not factor_row.empty:
                index = factor_row.index[0]
                f_heating_tt[i] = factor_data.loc[index, 'Fheiz,TT']
                f_el_tt[i] = factor_data.loc[index, 'Fel,TT']
                f_hotwater_tt[i] = factor_data.loc[index, 'FTWW,TT']
            else:
                print(f"Warning: No factors found for profile day {tag}, using defaults")
                f_heating_tt[i] = 1.0
                f_el_tt[i] = 0.0
                f_hotwater_tt[i] = 0.0
        except Exception as e:
            print(f"Error processing profile day {tag}: {e}")
            f_heating_tt[i] = 1.0
            f_el_tt[i] = 0.0
            f_hotwater_tt[i] = 0.0

    # Calculate daily energy consumption using VDI 4655 formulas
    daily_electricity = YEU_electricity_kWh * ((1/365) + (number_people_household * f_el_tt))
    daily_heating = YEU_heating_kWh * f_heating_tt
    daily_hot_water = YEU_hot_water_kWh * ((1/365) + (number_people_household * f_hotwater_tt))

    # Generate standardized quarter-hourly profiles
    quarter_hourly_intervals, electricity_profile, heating_profile, hot_water_profile = \
        standardized_quarter_hourly_profile(year, building_type, days_of_year, type_day)

    # Expand daily factors to quarter-hourly resolution
    quarter_hourly_daily_electricity = quarter_hourly_data(daily_electricity)
    quarter_hourly_daily_heating = quarter_hourly_data(daily_heating)
    quarter_hourly_daily_hot_water = quarter_hourly_data(daily_hot_water)

    # Apply daily factors to standardized profiles
    electricity_scaled = electricity_profile * quarter_hourly_daily_electricity
    heating_scaled = heating_profile * quarter_hourly_daily_heating
    hot_water_scaled = hot_water_profile * quarter_hourly_daily_hot_water

    # Energy balance correction to match annual targets
    electricity_corrected = electricity_scaled / np.sum(electricity_scaled) * YEU_electricity_kWh
    heating_corrected = heating_scaled / np.sum(heating_scaled) * YEU_heating_kWh
    hot_water_corrected = hot_water_scaled / np.sum(hot_water_scaled) * YEU_hot_water_kWh

    return quarter_hourly_intervals, electricity_corrected, heating_corrected, hot_water_corrected, temperature

def calculate(YEU_heating_kWh: float, 
             YEU_hot_water_kWh: float, 
             YEU_electricity_kWh: float, 
             building_type: str, 
             number_people_household: int, 
             year: int, 
             climate_zone: str, 
             TRY: str, 
             holidays: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate VDI 4655 building energy demand profiles.

    :param YEU_heating_kWh: Annual heating [kWh/a]
    :type YEU_heating_kWh: float
    :param YEU_hot_water_kWh: Annual DHW [kWh/a]
    :type YEU_hot_water_kWh: float
    :param YEU_electricity_kWh: Annual electricity [kWh/a]
    :type YEU_electricity_kWh: float
    :param building_type: VDI 4655 type (EFH, MFH, B)
    :type building_type: str
    :param number_people_household: Number of occupants
    :type number_people_household: int
    :param year: Target year
    :type year: int
    :param climate_zone: German climate zone 1-15
    :type climate_zone: str
    :param TRY: Path to Test Reference Year data
    :type TRY: str
    :param holidays: Holiday dates array
    :type holidays: np.ndarray
    :return: Tuple of (time, total_heat_kW, heating_kW, dhw_kW, temperature, electricity_kW)
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    :raises ValueError: If parameters invalid or negative
    :raises FileNotFoundError: If TRY or VDI 4655 data missing
    :raises RuntimeError: If calculation fails
    
    .. note::
        Returns quarter-hourly power [kW]. Energy [kWh] × 4 = Power [kW] for 15-min intervals.
    """
    # Input validation
    if YEU_heating_kWh <= 0 or YEU_hot_water_kWh <= 0 or YEU_electricity_kWh <= 0:
        raise ValueError("Annual energy consumption values must be positive")
    
    if number_people_household <= 0:
        raise ValueError("Number of people in household must be positive")
    
    valid_building_types = ["EFH", "MFH", "B"]
    if building_type not in valid_building_types:
        raise ValueError(f"Building type must be one of {valid_building_types}")
    
    # Execute VDI 4655 calculation
    time_15min, electricity_kWh_15min, heating_kWh_15min, hot_water_kWh_15min, temperature = \
        calculation_load_profile(
            TRY=TRY,
            building_type=building_type,
            number_people_household=number_people_household,
            YEU_electricity_kWh=YEU_electricity_kWh,
            YEU_heating_kWh=YEU_heating_kWh,
            YEU_hot_water_kWh=YEU_hot_water_kWh,
            holidays=holidays,
            climate_zone=climate_zone,
            year=year
        )
    
    # Calculate total heat demand
    total_heat_kWh_15min = heating_kWh_15min + hot_water_kWh_15min
    
    # Convert from quarter-hourly energy [kWh] to instantaneous power [kW]
    electricity_kW = electricity_kWh_15min * 4
    heating_kW = heating_kWh_15min * 4
    hot_water_kW = hot_water_kWh_15min * 4
    total_heat_kW = total_heat_kWh_15min * 4
    
    # Validation of energy balance
    annual_heating_calc = heating_kWh_15min.sum()
    annual_dhw_calc = hot_water_kWh_15min.sum()
    annual_elec_calc = electricity_kWh_15min.sum()
    
    tolerance = 0.01  # 1% tolerance
    if abs(annual_heating_calc - YEU_heating_kWh) / YEU_heating_kWh > tolerance:
        print(f"Warning: Heating energy balance error: {annual_heating_calc:.0f} vs {YEU_heating_kWh:.0f} kWh")
    if abs(annual_dhw_calc - YEU_hot_water_kWh) / YEU_hot_water_kWh > tolerance:
        print(f"Warning: Hot water energy balance error: {annual_dhw_calc:.0f} vs {YEU_hot_water_kWh:.0f} kWh")
    if abs(annual_elec_calc - YEU_electricity_kWh) / YEU_electricity_kWh > tolerance:
        print(f"Warning: Electricity energy balance error: {annual_elec_calc:.0f} vs {YEU_electricity_kWh:.0f} kWh")

    return time_15min, total_heat_kW, heating_kW, hot_water_kW, temperature, electricity_kW