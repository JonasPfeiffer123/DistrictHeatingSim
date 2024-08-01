"""
Filename: heat_requirement_BDEW.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains functions to calculate heat demand profiles with the BDEW SLP methods
"""

import pandas as pd
import numpy as np
import os
import sys

def get_resource_path(relative_path):
    """
    Get the absolute path to the resource, works for development and for PyInstaller.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def import_TRY(filename):
    """
    Import Test Reference Year (TRY) data for weather conditions.

    Args:
        filename (str): The path to the TRY data file.

    Returns:
        array: Numpy array containing temperature data.
    """
    col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]
    col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]
    data = pd.read_fwf(filename, widths=col_widths, names=col_names, skiprows=34)
    temperature = data['t'].values
    return temperature

def generate_year_months_days_weekdays(year):
    """
    Generate arrays for days, months, and weekdays for a given year.

    Args:
        year (int): The year for which to generate the arrays.

    Returns:
        tuple: Arrays containing days of the year, months, days, and weekdays.
    """
    start_date = np.datetime64(f'{year}-01-01')
    num_days = 366 if np.datetime64(f'{year}-12-31') - np.datetime64(f'{year}-01-01') == np.timedelta64(365, 'D') else 365
    days_of_year = np.arange(start_date, start_date + np.timedelta64(num_days, 'D'), dtype='datetime64[D]')
    months = days_of_year.astype('datetime64[M]').astype(int) % 12 + 1
    days = days_of_year - days_of_year.astype('datetime64[M]') + 1
    weekdays = ((days_of_year.astype('datetime64[D]').astype(int) + 4) % 7) + 1
    return days_of_year, months, days, weekdays

def calculate_daily_averages(temperature):
    """
    Calculate daily averages for temperature.

    Args:
        temperature (array): Hourly temperature data.

    Returns:
        array: Array containing daily average temperature.
    """
    num_hours = temperature.size
    num_days = num_hours // 24
    daily_temperature = temperature.reshape((num_days, 24))
    daily_avg_temperature = np.mean(daily_temperature, axis=1)
    return daily_avg_temperature

def calculate_hourly_intervals(year):
    """
    Calculate hourly intervals for a given year.

    Args:
        year (int): The year for which to calculate the intervals.

    Returns:
        array: Array of hourly intervals.
    """
    start_date = np.datetime64(f'{year}-01-01')
    num_days = 366 if np.datetime64(f'{year}-12-31') - np.datetime64(f'{year}-01-01') == np.timedelta64(365, 'D') else 365
    num_hours = num_days * 24
    return np.arange(start_date, start_date + np.timedelta64(num_hours, 'h'), dtype='datetime64[h]')

def get_coefficients(profiletype, subtype, daily_data):
    """
    Get the coefficients for a given profile type and subtype.

    Args:
        profiletype (str): The profile type.
        subtype (str): The profile subtype.
        daily_data (DataFrame): DataFrame containing daily coefficients.

    Returns:
        tuple: Coefficients A, B, C, D, mH, bH, mW, bW.
    """
    profile = profiletype + subtype
    row = daily_data[daily_data['Standardlastprofil'] == profile].iloc[0]
    return float(row['A']), float(row['B']), float(row['C']), float(row['D']), float(row['mH']), float(row['bH']), float(row['mW']), float(row['bW'])

def get_weekday_factor(daily_weekdays, profiletype, subtype, daily_data):
    """
    Get the weekday factor for a given profile type and subtype.

    Args:
        daily_weekdays (array): Array of daily weekdays.
        profiletype (str): The profile type.
        subtype (str): The profile subtype.
        daily_data (DataFrame): DataFrame containing daily coefficients.

    Returns:
        array: Array of weekday factors.
    """
    profile = profiletype + subtype
    profile_row = daily_data[daily_data['Standardlastprofil'] == profile]
    if profile_row.empty:
        raise ValueError("Profile not found")
    return np.array([profile_row.iloc[0][str(day)] for day in daily_weekdays]).astype(float)

def calculation_load_profile(TRY, JWB_kWh, profiletype, subtype, holidays, year, real_ww_share=None):
    """
    Calculate load profiles based on the BDEW SLP methods.

    Args:
        TRY (str): Path to the TRY data file.
        JWB_kWh (float): Yearly heat demand in kWh.
        profiletype (str): The profile type.
        subtype (str): The profile subtype.
        holidays (array): Array of holiday dates.
        year (int): Year for the calculation.
        real_ww_share (float, optional): Real warm water share. Defaults to None.

    Returns:
        tuple: Arrays of hourly intervals, total heat demand, heating demand, warm water demand, and temperature.
    """
    days_of_year, months, days, daily_weekdays = generate_year_months_days_weekdays(year)
    hourly_temperature = import_TRY(TRY)
    daily_avg_temperature = np.round(calculate_daily_averages(hourly_temperature), 1)
    daily_reference_temperature = np.round((daily_avg_temperature + 2.5) * 2, -1) / 2 - 2.5

    daily_data = pd.read_csv(get_resource_path('data/BDEW profiles/daily_coefficients.csv'), delimiter=';')
    h_A, h_B, h_C, h_D, mH, bH, mW, bW = get_coefficients(profiletype, subtype, daily_data)
    lin_H = np.nan_to_num(mH * daily_avg_temperature + bH) if mH != 0 or bH != 0 else 0
    lin_W = np.nan_to_num(mW * daily_avg_temperature + bW) if mW != 0 or bW != 0 else 0

    h_T_heating = h_A / (1 + (h_B / (daily_avg_temperature - 40)) ** h_C) + lin_H
    F_D = get_weekday_factor(daily_weekdays, profiletype, subtype, daily_data)
    h_T_F_D_heating = h_T_heating * F_D
    sum_h_T_F_D_heating = np.sum(h_T_F_D_heating)
    KW_kWh_heating = JWB_kWh / sum_h_T_F_D_heating if sum_h_T_F_D_heating != 0 else 0
    daily_heat_demand_heating = h_T_F_D_heating * KW_kWh_heating

    h_T_warmwater = lin_W + h_D
    h_T_F_D_warmwater = h_T_warmwater * F_D
    sum_h_T_F_D_warmwater = np.sum(h_T_F_D_warmwater)
    KW_kWh_warmwater = JWB_kWh / sum_h_T_F_D_warmwater if sum_h_T_F_D_warmwater != 0 else 0
    daily_heat_demand_warmwater = h_T_F_D_warmwater * KW_kWh_warmwater

    hourly_reference_temperature = np.round((hourly_temperature + 2.5) * 2, -1) / 2 - 2.5
    hourly_reference_temperature_2 = np.where(hourly_reference_temperature > hourly_temperature, hourly_reference_temperature - 5,
                                              np.where(hourly_reference_temperature > 27.5, 27.5, hourly_reference_temperature + 5))

    upper_limit = np.where(hourly_reference_temperature_2 > hourly_reference_temperature, hourly_reference_temperature_2, hourly_reference_temperature)
    lower_limit = np.where(hourly_reference_temperature_2 > hourly_reference_temperature, hourly_reference_temperature, hourly_reference_temperature_2)

    daily_hours = np.tile(np.arange(24), len(days_of_year))
    hourly_weekdays = np.repeat(daily_weekdays, 24)
    hourly_daily_heat_demand_heating = np.repeat(daily_heat_demand_heating, 24)
    hourly_daily_heat_demand_warmwater = np.repeat(daily_heat_demand_warmwater, 24)

    hourly_data = pd.read_csv(get_resource_path('data/BDEW profiles/hourly_coefficients.csv'), delimiter=';')
    filtered_hourly_data = hourly_data[hourly_data["Typ"] == profiletype]

    hourly_conditions = pd.DataFrame({
        'Wochentag': hourly_weekdays,
        'TemperaturLower': lower_limit,
        'TemperaturUpper': upper_limit,
        'Stunde': daily_hours
    })

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

    hour_factor_T1 = merged_data_T1["Stundenfaktor"].values.astype(float)
    hour_factor_T2 = merged_data_T2["Stundenfaktor"].values.astype(float)

    hour_factor_interpolation = hour_factor_T2 + (hour_factor_T1 - hour_factor_T2) * ((hourly_temperature - upper_limit) / 5)
    hourly_heat_demand_heating = np.nan_to_num((hourly_daily_heat_demand_heating * hour_factor_interpolation) / 100).astype(float)
    hourly_heat_demand_warmwater = np.nan_to_num((hourly_daily_heat_demand_warmwater * hour_factor_interpolation) / 100).astype(float)

    hourly_heat_demand_heating_normed = np.nan_to_num((hourly_heat_demand_heating / np.sum(hourly_heat_demand_heating)) * JWB_kWh)
    hourly_heat_demand_warmwater_normed = np.nan_to_num((hourly_heat_demand_warmwater / np.sum(hourly_heat_demand_warmwater)) * JWB_kWh)

    initial_ww_share = np.sum(hourly_heat_demand_warmwater_normed) / (np.sum(hourly_heat_demand_heating_normed) + np.sum(hourly_heat_demand_warmwater_normed))

    if real_ww_share is not None:
        ww_correction_factor = real_ww_share / initial_ww_share
        heating_correction_factor = (1 - real_ww_share) / (1 - initial_ww_share)
        hourly_heat_demand_warmwater_normed *= ww_correction_factor
        hourly_heat_demand_heating_normed *= heating_correction_factor
        total_demand = hourly_heat_demand_heating_normed + hourly_heat_demand_warmwater_normed
        scale_factor = JWB_kWh / np.sum(total_demand)
        hourly_heat_demand_heating_normed *= scale_factor
        hourly_heat_demand_warmwater_normed *= scale_factor

    hourly_heat_demand_total_normed = hourly_heat_demand_heating_normed + hourly_heat_demand_warmwater_normed
    hourly_intervals = calculate_hourly_intervals(year)

    return hourly_intervals, hourly_heat_demand_total_normed, hourly_heat_demand_heating_normed.astype(float), hourly_heat_demand_warmwater_normed.astype(float), hourly_temperature

def calculate(YEU_kWh=10000, building_type="HMF", subtyp="03", TRY=get_resource_path('data\\TRY\\TRY_511676144222\\TRY2015_511676144222_Jahr.dat'), year=2021, real_ww_share=None):
    """
    Calculate heat demand profiles using BDEW SLP methods.

    Args:
        YEU_kWh (int, optional): Yearly energy usage in kWh. Defaults to 10000.
        building_type (str, optional): Type of building. Defaults to "HMF".
        subtyp (str, optional): Subtype of building. Defaults to "03".
        TRY (str, optional): Path to the TRY data file. Defaults to get_resource_path('data\\TRY\\TRY_511676144222\\TRY2015_511676144222_Jahr.dat').
        year (int, optional): Year for the calculation. Defaults to 2021.
        real_ww_share (float, optional): Real warm water share. Defaults to None.

    Returns:
        tuple: Arrays of hourly intervals, total heat demand, heating demand, warm water demand, and temperature.
    """
    holidays = np.array(["2021-01-01", "2021-04-02", "2021-04-05", "2021-05-01", "2021-05-24", "2021-05-13", 
                         "2021-06-03", "2021-10-03", "2021-11-01", "2021-12-25", "2021-12-26"]).astype('datetime64[D]')
    hourly_intervals, hourly_heat_demand_total, hourly_heat_demand_heating, hourly_heat_demand_warmwater, hourly_temperature = calculation_load_profile(TRY, YEU_kWh, building_type, subtyp, holidays, year, real_ww_share)
    return hourly_intervals, hourly_heat_demand_total, hourly_heat_demand_heating, hourly_heat_demand_warmwater, hourly_temperature
