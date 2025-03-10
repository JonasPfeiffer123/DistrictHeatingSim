"""
Filename: heat_requirement_VDI4655.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-10
Description: Contains functions to calculate heat demand profiles with the VDI 4655 methods
"""

import pandas as pd
import numpy as np

from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.utilities.utilities import get_resource_path

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

def calculate_daily_averages(temperature, cloud_cover):
    """
    Calculate daily averages for temperature and cloud cover.

    Args:
        temperature (array): Hourly temperature data.
        cloud_cover (array): Hourly cloud cover data.

    Returns:
        tuple: Arrays containing daily average temperature and cloud cover.
    """
    num_hours = temperature.size
    num_days = num_hours // 24
    daily_temperature = temperature.reshape((num_days, 24))
    daily_cloud_cover = cloud_cover.reshape((num_days, 24))
    daily_avg_temperature = np.mean(daily_temperature, axis=1)
    daily_avg_cloud_cover = np.mean(daily_cloud_cover, axis=1)
    return daily_avg_temperature, daily_avg_cloud_cover

def calculate_quarter_hourly_intervals(year):
    """
    Calculate quarter-hourly intervals for a given year.

    Args:
        year (int): The year for which to calculate the intervals.

    Returns:
        array: Array of quarter-hourly intervals.
    """
    start_date = np.datetime64(f'{year}-01-01')
    num_days = 366 if np.datetime64(f'{year}-12-31') - np.datetime64(f'{year}-01-01') == np.timedelta64(365, 'D') else 365
    num_quarter_hours = num_days * 24 * 4
    return np.arange(start_date, start_date + np.timedelta64(num_quarter_hours, '15m'), dtype='datetime64[15m]')

def quarter_hourly_data(data):
    """
    Create quarter-hourly data from daily data.

    Args:
        data (array): Daily data.

    Returns:
        array: Quarter-hourly data.
    """
    num_quarter_hours_per_day = 24 * 4
    return np.repeat(data, num_quarter_hours_per_day)

def standardized_quarter_hourly_profile(year, building_type, days_of_year, type_days):
    """
    Generate a standardized quarter-hourly profile.

    Args:
        year (int): The year for which to generate the profile.
        building_type (str): The type of building.
        days_of_year (array): Array of days in the year.
        type_days (array): Array of type days.

    Returns:
        tuple: Arrays of quarter-hourly intervals, electricity demand, heating demand, and hot water demand.
    """
    quarter_hourly_intervals = calculate_quarter_hourly_intervals(year)
    daily_dates = np.array([np.datetime64(dt, 'D') for dt in quarter_hourly_intervals])
    indices = np.searchsorted(days_of_year, daily_dates)
    quarterly_type_days = type_days[indices % len(type_days)]
    
    all_type_days = np.unique(quarterly_type_days)
    all_data = {f"{building_type}{type_day}": pd.read_csv(get_resource_path(f'data\\VDI 4655 profiles\\VDI 4655 load profiles\\{building_type}{type_day}.csv'), sep=';') for type_day in all_type_days}
    
    profile_days = np.char.add(building_type, quarterly_type_days)
    times_str = np.datetime_as_string(quarter_hourly_intervals, unit='m')
    times = np.array([t.split('T')[1] for t in times_str])
    times_profile_df = pd.DataFrame({'Datum': np.repeat(days_of_year, 24*4), 'Zeit': times, 'ProfileDay': profile_days})
    combined_df = pd.concat([df.assign(ProfileDay=profile_day) for profile_day, df in all_data.items()])
    merged_df = pd.merge(times_profile_df, combined_df, on=['Zeit', 'ProfileDay'], how='left')
    electricity_demand = merged_df['Strombedarf normiert'].values
    heating_demand = merged_df['Heizwärme normiert'].values
    hot_water_demand = merged_df['Warmwasser normiert'].values
    return quarter_hourly_intervals, electricity_demand, heating_demand, hot_water_demand

def calculation_load_profile(TRY, building_type, number_people_household, YEU_electricity_kWh, YEU_heating_kWh, YEU_hot_water_kWh, holidays, climate_zone, year):
    """
    Calculate load profiles based on the VDI 4655 methods.

    Args:
        TRY (str): Path to the TRY data file.
        building_type (str): The type of building.
        number_people_household (int): Number of people in the household.
        YEU_electricity_kWh (float): Yearly electricity usage in kWh.
        YEU_heating_kWh (float): Yearly heating usage in kWh.
        YEU_hot_water_kWh (float): Yearly hot water usage in kWh.
        holidays (array): Array of holiday dates.
        climate_zone (str, optional): Climate zone. Defaults to "9".
        year (int, optional): Year for the calculation. Defaults to 2019.

    Returns:
        tuple: Arrays of quarter-hourly intervals, electricity demand, heating demand, hot water demand, and temperature.
    """
    factors = get_resource_path('data\\VDI 4655 profiles\\VDI 4655 data\\Faktoren.csv')

    days_of_year, months, days, weekdays = generate_year_months_days_weekdays(year)
    temperature, _, _, _, degree_of_coverage = import_TRY(TRY)
    daily_avg_temperature, daily_avg_degree_of_coverage = calculate_daily_averages(temperature, degree_of_coverage)
    season = np.where(daily_avg_temperature < 5, "W", np.where((daily_avg_temperature >= 5) & (daily_avg_temperature <= 15), "Ü", "S"))
    day_type = np.where((weekdays == 1) | np.isin(days_of_year, holidays), "S", "W")
    degree_of_coverage = np.where(season == "S", "X", np.where((daily_avg_degree_of_coverage >= 0) & (daily_avg_degree_of_coverage < 4), "H", "B"))
    type_day = np.char.add(np.char.add(season, day_type), degree_of_coverage)
    profile_day = np.char.add((building_type + climate_zone), type_day)

    factor_data = pd.read_csv(factors, sep=';')
    f_heating_tt = np.zeros(len(profile_day))
    f_el_tt = np.zeros(len(profile_day))
    f_hotwater_tt = np.zeros(len(profile_day))

    for i, tag in enumerate(profile_day):
        index = factor_data[factor_data['Profiltag'] == tag].index[0]
        f_heating_tt[i] = factor_data.loc[index, 'Fheiz,TT']
        f_el_tt[i] = factor_data.loc[index, 'Fel,TT']
        f_hotwater_tt[i] = factor_data.loc[index, 'FTWW,TT']

    daily_electricity = YEU_electricity_kWh * ((1/365) + (number_people_household*f_el_tt))
    daily_heating = YEU_heating_kWh * f_heating_tt
    daily_hot_water = YEU_hot_water_kWh * ((1/365) + (number_people_household*f_hotwater_tt))

    quarter_hourly_intervals, electricity_kWh, heating_kWh, hot_water_kWh = standardized_quarter_hourly_profile(year, building_type, days_of_year, type_day)

    quarter_hourly_daily_electricity = quarter_hourly_data(daily_electricity)
    quarter_hourly_daily_heating = quarter_hourly_data(daily_heating)
    quarte_hourly_daily_hot_water = quarter_hourly_data(daily_hot_water)

    electricity_normed = electricity_kWh * quarter_hourly_daily_electricity
    heating_normed = heating_kWh * quarter_hourly_daily_heating
    hot_water_normed = hot_water_kWh * quarte_hourly_daily_hot_water

    electricity_corrected = electricity_normed/sum(electricity_normed)*YEU_electricity_kWh
    heating_corrected = heating_normed/sum(heating_normed)*YEU_heating_kWh
    hot_water_corrected = hot_water_normed/sum(hot_water_normed)*YEU_hot_water_kWh

    return quarter_hourly_intervals, electricity_corrected, heating_corrected, hot_water_corrected, temperature

def calculate(YEU_heating_kWh, YEU_hot_water_kWh, YEU_electricity_kWh, building_type, number_people_household, year, climate_zone, TRY, holidays):
    """
    Calculate heat demand profiles using VDI 4655 methods.

    Args:
        YEU_heating_kWh (float): Yearly heating usage in kWh.
        YEU_hot_water_kWh (float): Yearly hot water usage in kWh.
        YEU_electricity_kWh (float, optional): Yearly electricity usage in kWh.
        building_type (str, optional): Type of building.
        number_people_household (int, optional): Number of people in the household.
        year (int, optional): Year for the calculation.
        climate_zone (str, optional): Climate zone.
        TRY (str, optional): Path to the TRY data file.

    Returns:
        tuple: Arrays of quarter-hourly intervals, total heat demand, heating demand, hot water demand, temperature, and electricity demand.
    """

    time_15min, electricity_kWh_15min, heating_kWh_15min, hot_water_kWh_15min, temperature = calculation_load_profile(TRY, building_type, number_people_household, 
                                                                                                  YEU_electricity_kWh, YEU_heating_kWh, YEU_hot_water_kWh, 
                                                                                                  holidays, climate_zone, year)
    total_heat_kWh_15min = heating_kWh_15min + hot_water_kWh_15min
    electricity_kW, heating_kW, hot_water_kW, total_heat_kW = electricity_kWh_15min * 4, heating_kWh_15min * 4, hot_water_kWh_15min * 4, total_heat_kWh_15min * 4

    return time_15min, total_heat_kW, heating_kW, hot_water_kW, temperature, electricity_kW
