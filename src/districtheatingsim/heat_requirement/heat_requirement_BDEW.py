"""
BDEW Standard Load Profile heat demand calculation module.

Implements BDEW methodology for commercial and public buildings with
temperature-dependent profiles and weekday variations.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import pandas as pd
import numpy as np
import math
import os
import sys
from typing import Tuple, Optional, Union
from datetime import date as _date, timedelta as _timedelta

from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.utilities.utilities import get_resource_path

def get_resource_path(relative_path: str) -> str:
    """
    Get absolute resource path for development and PyInstaller.

    :param relative_path: Relative path from package root
    :type relative_path: str
    :return: Absolute path to resource file
    :rtype: str
    
    .. note::
        Automatically detects PyInstaller frozen state and adjusts paths.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        # Check if this is a path that should be outside _internal
        data_folders_outside = ['data', 'project_data', 'images', 'leaflet']
        first_component = relative_path.split(os.sep)[0].split('/')[0].split('\\')[0]
        if first_component in data_folders_outside:
            base_path = os.path.dirname(sys._MEIPASS)
        else:
            base_path = sys._MEIPASS
    else:
        # Running in development environment
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def generate_year_months_days_weekdays(year: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate temporal arrays for BDEW calculations.

    :param year: Target year
    :type year: int
    :return: Tuple of (days_of_year, months, days, weekdays) with weekday 1=Monday, 7=Sunday
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    
    .. note::
        Handles leap years automatically. Weekdays use ISO numbering.
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
    weekdays = ((days_of_year.astype('datetime64[D]').astype(int) + 4) % 7) + 1
    
    return days_of_year, months, days, weekdays

def calculate_daily_averages(temperature: np.ndarray) -> np.ndarray:
    """
    Calculate daily average temperatures from hourly data.

    :param temperature: Hourly temperature [°C] for complete year (8760/8784 hours)
    :type temperature: np.ndarray
    :return: Daily average temperatures [°C]
    :rtype: np.ndarray
    :raises ValueError: If temperature array not divisible by 24
    
    .. note::
        Used for BDEW sigmoid function temperature dependencies.
    """
    num_hours = temperature.size
    num_days = num_hours // 24
    
    # Validate complete daily blocks
    if num_hours % 24 != 0:
        raise ValueError(f"Temperature data incomplete: {num_hours} hours not divisible by 24")
    
    # Reshape to daily blocks and calculate averages
    daily_temperature = temperature[:num_days*24].reshape((num_days, 24))
    daily_avg_temperature = np.mean(daily_temperature, axis=1)
    
    return daily_avg_temperature

def calculate_allokationstemperatur(daily_avg_temperature: np.ndarray) -> np.ndarray:
    """
    Calculate Allokationstemperatur (BDEW weighted moving average of daily temperatures).

    :param daily_avg_temperature: Daily mean temperatures [°C]
    :type daily_avg_temperature: np.ndarray
    :return: Allokationstemperatur for each day [°C]
    :rtype: np.ndarray

    .. note::
        Formula (Leitfaden S. 43-44):
        T_allo(D) = (T_D·8 + T_{D-1}·4 + T_{D-2}·2 + T_{D-3}·1) / 15
    """
    weights = np.array([8.0, 4.0, 2.0, 1.0]) / 15.0
    n = len(daily_avg_temperature)
    result = np.empty(n)
    for i in range(n):
        result[i] = (
            weights[0] * daily_avg_temperature[i]
            + weights[1] * daily_avg_temperature[max(i - 1, 0)]
            + weights[2] * daily_avg_temperature[max(i - 2, 0)]
            + weights[3] * daily_avg_temperature[max(i - 3, 0)]
        )
    return result

def compute_holidays(year: int) -> set:
    """
    Compute statutory German public holidays per BDEW Leitfaden Kap. 6.1.1.

    :param year: Target year
    :type year: int
    :return: Set of holiday dates
    :rtype: set

    .. note::
        Holidays are treated as Sundays (weekday 7) in FWT lookup.
        Bundesweite Feiertage: Neujahr, Karfreitag, Ostermontag, 01.05.,
        Christi Himmelfahrt, Pfingstmontag, 03.10., 25.12., 26.12.
    """
    a = year % 19
    b = year % 4
    c = year % 7
    k = year // 100
    p = (13 + 8 * k) // 25
    q = k // 4
    M = (15 - p + k - q) % 30
    N = (4 + k - q) % 7
    d = (19 * a + M) % 30
    e = (2 * b + 4 * c + 6 * d + N) % 7
    if d == 29 and e == 6:
        easter_offset = 50
    elif d == 28 and e == 6 and (11 * M + 11) % 30 < 19:
        easter_offset = 49
    else:
        easter_offset = d + e + 22
    easter = _date(year, 3, 1) + _timedelta(days=easter_offset - 1)
    return {
        _date(year, 1, 1),                       # Neujahr
        easter + _timedelta(days=-2),             # Karfreitag
        easter + _timedelta(days=1),              # Ostermontag
        _date(year, 5, 1),                        # Tag der Arbeit
        easter + _timedelta(days=39),             # Christi Himmelfahrt
        easter + _timedelta(days=50),             # Pfingstmontag
        _date(year, 10, 3),                       # Tag der deutschen Einheit
        _date(year, 12, 25),                      # 1. Weihnachtstag
        _date(year, 12, 26),                      # 2. Weihnachtstag
    }

def calculate_hourly_intervals(year: int) -> np.ndarray:
    """
    Generate hourly datetime intervals for full year.

    :param year: Target year
    :type year: int
    :return: Hourly datetime64 intervals (8760 or 8784 for leap year)
    :rtype: np.ndarray
    """
    start_date = np.datetime64(f'{year}-01-01', 'h')
    
    # Determine number of days (handle leap years) - use datetime64[D] for both dates
    end_date_day = np.datetime64(f'{year}-12-31', 'D')
    start_date_day = np.datetime64(f'{year}-01-01', 'D')
    num_days = (end_date_day - start_date_day).astype(int) + 1
    
    # Calculate total number of hourly intervals
    num_hours = num_days * 24
    
    # Generate hourly interval array
    intervals = np.arange(
        start_date, 
        start_date + np.timedelta64(num_hours, 'h'), 
        dtype='datetime64[h]'
    )
    
    return intervals

def get_coefficients(profiletype: str, 
                    subtype: str, 
                    daily_data: pd.DataFrame) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    Extract BDEW profile coefficients for load calculation.

    :param profiletype: BDEW building type (GKO, GHA, GMK, GBD, GBH, GWA, GGA, GBA, GGB, GPD, GMF, GHD)
    :type profiletype: str
    :param subtype: Building subtype for detailed classification
    :type subtype: str
    :param daily_data: BDEW daily coefficients DataFrame
    :type daily_data: pd.DataFrame
    :return: Tuple of (A, B, C, D, mH, bH, mW, bW) sigmoid and linear coefficients
    :rtype: Tuple[float, float, float, float, float, float, float, float]
    :raises ValueError: If profile not found in data
    :raises KeyError: If coefficient columns missing
    
    .. note::
        Sigmoid: h_T = A/(1+(B/(T-40))^C) + mH*T + bH. DHW: mW*T + bW + D
    """
    # Combine profile type and subtype for lookup
    profile = profiletype + subtype
    
    # Find matching profile row in coefficient data
    profile_row = daily_data[daily_data['Standardlastprofil'] == profile]
    
    if profile_row.empty:
        raise ValueError(f"Profile '{profile}' not found in BDEW coefficient data")
    
    # Extract coefficients from first matching row
    row = profile_row.iloc[0]
    
    try:
        A = float(row['A'])
        B = float(row['B']) 
        C = float(row['C'])
        D = float(row['D'])
        mH = float(row['mH'])
        bH = float(row['bH'])
        mW = float(row['mW'])
        bW = float(row['bW'])
    except KeyError as e:
        raise KeyError(f"Missing coefficient column in BDEW data: {e}") from e
    except ValueError as e:
        raise ValueError(f"Invalid coefficient value in BDEW data: {e}") from e
    
    return A, B, C, D, mH, bH, mW, bW

def get_weekday_factor(daily_weekdays: np.ndarray, 
                      profiletype: str, 
                      subtype: str, 
                      daily_data: pd.DataFrame) -> np.ndarray:
    """
    Extract weekday-specific load factors from BDEW data.

    :param daily_weekdays: Weekday numbers (1=Monday to 7=Sunday) for each day
    :type daily_weekdays: np.ndarray
    :param profiletype: BDEW building type
    :type profiletype: str
    :param subtype: Building subtype
    :type subtype: str
    :param daily_data: BDEW coefficients DataFrame with weekday columns '1'-'7'
    :type daily_data: pd.DataFrame
    :return: Weekday factors for each day (typically 0.5-1.5)
    :rtype: np.ndarray
    :raises ValueError: If profile not found
    :raises KeyError: If weekday columns missing
    
    .. note::
        Accounts for different operation patterns: offices high Mon-Fri, schools minimal weekends.
    """
    # Combine profile type and subtype for lookup
    profile = profiletype + subtype
    
    # Find matching profile row in coefficient data
    profile_row = daily_data[daily_data['Standardlastprofil'] == profile]
    
    if profile_row.empty:
        raise ValueError(f"Profile '{profile}' not found in BDEW coefficient data")
    
    # Extract weekday factors for each day
    try:
        weekday_factors = np.array([
            profile_row.iloc[0][str(day)] for day in daily_weekdays
        ]).astype(float)
    except KeyError as e:
        raise KeyError(f"Missing weekday column in BDEW data: {e}") from e
    except ValueError as e:
        raise ValueError(f"Invalid weekday factor value: {e}") from e
    
    return weekday_factors

def calculate(JWB_kWh: float, 
             profiletype: str, 
             subtype: str, 
             TRY_file_path: str, 
             year: int, 
             real_ww_share: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate heat demand profiles using BDEW Standard Load Profile methodology.

    :param JWB_kWh: Annual heat demand [kWh/a]
    :type JWB_kWh: float
    :param profiletype: BDEW building type (GKO, GHA, GMK, etc.)
    :type profiletype: str
    :param subtype: Building subtype
    :type subtype: str
    :param TRY_file_path: Path to Test Reference Year weather data
    :type TRY_file_path: str
    :param year: Calculation year
    :type year: int
    :param real_ww_share: Optional DHW share override (0-1)
    :type real_ww_share: Optional[float]
    :return: Tuple of (time_steps, total_heat_kW, heating_kW, dhw_kW, temperatures)
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    :raises FileNotFoundError: If TRY or BDEW data files not found
    :raises ValueError: If profile not found or invalid parameters
    
    .. note::
        Combines sigmoid temperature function, weekday factors, and hourly patterns.
    """
    # Load BDEW coefficient data files
    # Input validation
    if JWB_kWh <= 0:
        raise ValueError("Annual heat demand must be positive")
    
    if not isinstance(year, int) or year < 1900 or year > 2100:
        raise ValueError("Year must be valid integer between 1900 and 2100")
    
    # Generate temporal arrays for calculation
    days_of_year, months, days, daily_weekdays = generate_year_months_days_weekdays(year)

    # Import and process meteorological data
    hourly_temperature, _, _, _, _ = import_TRY(TRY_file_path)
    daily_avg_temperature = np.round(calculate_daily_averages(hourly_temperature), 1)

    # Allokationstemperatur (BDEW Leitfaden S. 43-44):
    # T_allo(D) = (T_D*8 + T_{D-1}*4 + T_{D-2}*2 + T_{D-3}*1) / 15
    daily_allo_temperature = calculate_allokationstemperatur(daily_avg_temperature)

    # Override weekday to 7 (Sunday) for statutory holidays (Leitfaden Kap. 6.1.1)
    holiday_dates = compute_holidays(year)
    for i, d in enumerate(days_of_year):
        if _date.fromisoformat(str(d)) in holiday_dates:
            daily_weekdays[i] = 7

    # Load BDEW coefficient data
    daily_data = pd.read_csv(
        get_resource_path('data/BDEW profiles/daily_coefficients.csv'), 
        delimiter=';'
    )
    
    # Extract building-specific coefficients
    h_A, h_B, h_C, h_D, mH, bH, mW, bW = get_coefficients(profiletype, subtype, daily_data)
    
    # Linear temperature corrections based on Allokationstemperatur (Leitfaden S. 41-42)
    lin_H = (np.nan_to_num(mH * daily_allo_temperature + bH)
             if mH != 0 or bH != 0 else np.zeros(len(daily_allo_temperature)))
    lin_W = (np.nan_to_num(mW * daily_allo_temperature + bW)
             if mW != 0 or bW != 0 else np.zeros(len(daily_allo_temperature)))

    # SigLinDe: h_total = sigmoid + D + max(mH*T+bH, mW*T+bW)
    # DHW component:     h_dhw  = D + mW*T + bW  (warm water baseline)
    # Heating component: h_total - h_dhw  (temperature-dependent space heating)
    h_T_sigmoid = h_A / (1 + (h_B / (daily_allo_temperature - 40)) ** h_C)
    h_T_dhw     = h_D + lin_W
    h_T_total   = h_T_sigmoid + h_D + np.maximum(lin_H, lin_W)

    # Apply weekday factors
    F_D = get_weekday_factor(daily_weekdays, profiletype, subtype, daily_data)

    # Single KW normalization on combined total (Leitfaden S. 42)
    # Fixes: old code applied separate KW to heating AND dhw -> sum = 2*JWB
    sum_h_T_F_D_total = np.sum(h_T_total * F_D)
    KW_kWh = JWB_kWh / sum_h_T_F_D_total if sum_h_T_F_D_total != 0 else 0

    # Daily demands - proportional split, sum = JWB_kWh exactly
    daily_heat_demand_heating   = (h_T_total - h_T_dhw) * F_D * KW_kWh
    daily_heat_demand_warmwater = h_T_dhw * F_D * KW_kWh

    # Process hourly temperature data for interpolation
    hourly_reference_temperature = np.round((hourly_temperature + 2.5) * 2, -1) / 2 - 2.5
    
    # Calculate temperature bounds for interpolation
    hourly_reference_temperature_2 = np.where(
        hourly_reference_temperature > hourly_temperature, 
        hourly_reference_temperature - 5,
        np.where(
            hourly_reference_temperature > 27.5, 
            27.5, 
            hourly_reference_temperature + 5
        )
    )

    # Determine upper and lower temperature limits for interpolation
    upper_limit = np.where(
        hourly_reference_temperature_2 > hourly_reference_temperature, 
        hourly_reference_temperature_2, 
        hourly_reference_temperature
    )
    lower_limit = np.where(
        hourly_reference_temperature_2 > hourly_reference_temperature, 
        hourly_reference_temperature, 
        hourly_reference_temperature_2
    )

    # Expand daily data to hourly resolution
    daily_hours = np.tile(np.arange(24), len(days_of_year))
    hourly_weekdays = np.repeat(daily_weekdays, 24)
    hourly_daily_heat_demand_heating = np.repeat(daily_heat_demand_heating, 24)
    hourly_daily_heat_demand_warmwater = np.repeat(daily_heat_demand_warmwater, 24)

    # Load BDEW hourly coefficient data
    hourly_data = pd.read_csv(
        get_resource_path('data/BDEW profiles/hourly_coefficients.csv'), 
        delimiter=';'
    )
    filtered_hourly_data = hourly_data[hourly_data["Typ"] == profiletype]

    # Create conditions dataframe for coefficient lookup
    hourly_conditions = pd.DataFrame({
        'Wochentag': hourly_weekdays,
        'TemperaturLower': lower_limit,
        'TemperaturUpper': upper_limit,
        'Stunde': daily_hours
    })

    # Merge hourly conditions with coefficient data for interpolation bounds
    merged_data_T1 = pd.merge(
        hourly_conditions,
        filtered_hourly_data,
        how='left',
        left_on=['Wochentag', 'TemperaturLower', 'Stunde'],
        right_on=['Wochentag', 'Temperatur', 'Stunde']
    )

    merged_data_T2 = pd.merge(
        hourly_conditions,
        filtered_hourly_data,
        how='left',
        left_on=['Wochentag', 'TemperaturUpper', 'Stunde'],
        right_on=['Wochentag', 'Temperatur', 'Stunde']
    )

    # Extract hourly factors for interpolation
    hour_factor_T1 = merged_data_T1["Stundenfaktor"].values.astype(float)
    hour_factor_T2 = merged_data_T2["Stundenfaktor"].values.astype(float)

    # Perform linear interpolation between temperature bounds
    hour_factor_interpolation = hour_factor_T2 + (hour_factor_T1 - hour_factor_T2) * (
        (hourly_temperature - upper_limit) / 5
    )
    
    # Calculate hourly heat demands
    hourly_heat_demand_heating = np.nan_to_num(
        (hourly_daily_heat_demand_heating * hour_factor_interpolation) / 100
    ).astype(float)
    
    hourly_heat_demand_warmwater = np.nan_to_num(
        (hourly_daily_heat_demand_warmwater * hour_factor_interpolation) / 100
    ).astype(float)

    total = hourly_heat_demand_heating + hourly_heat_demand_warmwater
    scale_factor = JWB_kWh / np.sum(total) if np.sum(total) > 0 else 1
    hourly_heat_demand_heating_normed = hourly_heat_demand_heating * scale_factor
    hourly_heat_demand_warmwater_normed = hourly_heat_demand_warmwater * scale_factor

    # Calculate initial hot water share
    initial_ww_share = (
        np.sum(hourly_heat_demand_warmwater_normed) / 
        (np.sum(hourly_heat_demand_heating_normed) + np.sum(hourly_heat_demand_warmwater_normed))
    )

    # Apply hot water share correction if specified
    #print(f"Initial DHW share: {initial_ww_share:.3f}")
    #print(f"real_ww_share: {real_ww_share}")
    if real_ww_share is not None and not math.isnan(real_ww_share):
        if 0 <= real_ww_share <= 1:
            # Calculate correction factors
            ww_correction_factor = real_ww_share / initial_ww_share if initial_ww_share > 0 else 1
            heating_correction_factor = (1 - real_ww_share) / (1 - initial_ww_share) if initial_ww_share < 1 else 1
            
            # Apply corrections
            hourly_heat_demand_warmwater_normed *= ww_correction_factor
            hourly_heat_demand_heating_normed *= heating_correction_factor
            
            # Renormalize to maintain annual total
            total_demand = hourly_heat_demand_heating_normed + hourly_heat_demand_warmwater_normed
            scale_factor = JWB_kWh / np.sum(total_demand) if np.sum(total_demand) > 0 else 1
            hourly_heat_demand_heating_normed *= scale_factor
            hourly_heat_demand_warmwater_normed *= scale_factor
        else:
            print(f"Warning: Invalid DHW share {real_ww_share}, using calculated value {initial_ww_share:.3f}")

    # Calculate total heat demand
    hourly_heat_demand_total_normed = hourly_heat_demand_heating_normed + hourly_heat_demand_warmwater_normed

    #print(f"BDEW calculation complete for {profiletype} ({subtype}) in {year}")
    #print(f"  Annual total demand: {hourly_heat_demand_total_normed.sum():.0f} kWh (target: {JWB_kWh})")
    #print(f"  Annual heating demand: {hourly_heat_demand_heating_normed.sum():.0f} kWh")
    #print(f"  Annual DHW demand: {hourly_heat_demand_warmwater_normed.sum():.0f} kWh") 
    
    # Generate hourly time intervals
    hourly_intervals = calculate_hourly_intervals(year)

    return (hourly_intervals, 
            hourly_heat_demand_total_normed, 
            hourly_heat_demand_heating_normed.astype(float), 
            hourly_heat_demand_warmwater_normed.astype(float), 
            hourly_temperature)