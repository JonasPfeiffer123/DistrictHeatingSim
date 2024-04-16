import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os
import sys

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

# Klimazonen
    # Zone	Beschreibung
    #  1    Nordseeküste
    #  2    Ostseeküste
    #  3	Nordwestdeutsches Tiefland
    #  4	Nordostdeutsches Tiefland
    #  5	Niederrheinisch-westfälische Bucht und Emsland
    #  6	Nördliche und westliche Mittelgebirge, Randgebiete
    #  7	Nördliche und westliche Mittelgebirge, zentrale Bereiche
    #  8	Oberharz und Schwarzwald (mittlere Lagen)
    #  9	Thüringer Becken und Sächsisches Hügelland
    # 10	Südöstliches Mittelgebirge bis 1000m
    # 11	Ergebirge, Böhmer und Schwarzwald oberhalb 1000m
    # 12	Oberrheingraben und unteres Neckartal
    # 13	Schwäbisch-fränkisches Stufenland und Alpenvorland
    # 14	Schwäbische Alb und Baar
    # 15	Alpenrand und -täler


def import_TRY(filename):
    # Import TRY
    # Define column widths
    col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]
    # Define column names
    col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]

    # Read the file
    data = pd.read_fwf(filename, widths=col_widths, names=col_names, skiprows=34)

    # Store the columns as numpy arrays
    temperature = data['t'].values
    cloud_cover = data['N'].values

    return temperature, cloud_cover

def import_csv(filename):
    data = pd.read_csv(filename, sep=';')
    return data

def generate_year_months_days_weekdays(year):
    # First day of the year
    start_date = np.datetime64(f'{year}-01-01')
    # Number of days in the year (consider leap year)
    num_days = 366 if np.datetime64(f'{year}-12-31') - np.datetime64(f'{year}-01-01') == np.timedelta64(365, 'D') else 365

    # Create an array with all days of the year
    days_of_year = np.arange(start_date, start_date + np.timedelta64(num_days, 'D'), dtype='datetime64[D]')
    # Extract month (values between 1 and 12)
    months = days_of_year.astype('datetime64[M]').astype(int) % 12 + 1
    # Extract day of the month
    days = days_of_year - days_of_year.astype('datetime64[M]') + 1

    # Extract weekday (Sunday=1, Saturday=7)
    weekdays = ((days_of_year.astype('datetime64[D]').astype(int) + 4) % 7) + 1

    return days_of_year, months, days, weekdays

def calculate_daily_averages(temperature, cloud_cover):
    # Assumption: The length of each array corresponds to the number of hours in a year
    num_hours = temperature.size
    num_days = num_hours // 24

    # Reshape the arrays to get daily data
    daily_temperature = temperature.reshape((num_days, 24))
    daily_cloud_cover = cloud_cover.reshape((num_days, 24))

    # Calculate daily averages
    daily_avg_temperature = np.mean(daily_temperature, axis=1)
    daily_avg_cloud_cover = np.mean(daily_cloud_cover, axis=1)

    return daily_avg_temperature, daily_avg_cloud_cover

def calculate_quarter_hourly_intervals(year):
    # First day of the year
    start_date = np.datetime64(f'{year}-01-01')
    # Number of days in the year (consider leap year)
    num_days = 366 if np.datetime64(f'{year}-12-31') - np.datetime64(f'{year}-01-01') == np.timedelta64(365, 'D') else 365

    # Number of quarter-hour intervals in the year
    num_quarter_hours = num_days * 24 * 4

    # Create an array with all quarter-hourly intervals for the year
    quarter_hourly_intervals = np.arange(start_date, 
                                        start_date + np.timedelta64(num_quarter_hours, '15m'), 
                                        dtype='datetime64[15m]')

    return quarter_hourly_intervals

def quarter_hourly_data(data):
    # Number of quarter-hours in the year
    num_quarter_hours_per_day = 24 * 4

    # Create an array with quarter-hourly data for the year
    quarter_hourly_intervals = np.repeat(data, num_quarter_hours_per_day)

    return quarter_hourly_intervals

def standardized_quarter_hourly_profile(year, building_type, days_of_year, type_days):
    quarter_hourly_intervals = calculate_quarter_hourly_intervals(year)

    # Vectorized conversion to daily dates and matching with days_of_year
    daily_dates = np.array([np.datetime64(dt, 'D') for dt in quarter_hourly_intervals])
    indices = np.searchsorted(days_of_year, daily_dates)
    quarterly_type_days = type_days[indices % len(type_days)]  # Modulo for safety
    
    all_type_days = np.unique(quarterly_type_days)

    # Read all CSV files once and filter as needed
    all_data = {f"{building_type}{type_day}": import_csv(get_resource_path(f'heat_requirement\VDI 4655 load profiles\{building_type}{type_day}.csv')) 
                for type_day in all_type_days}

    profile_days = np.char.add(building_type, quarterly_type_days)

    # Convert to a string and extract the time
    times_str = np.datetime_as_string(quarter_hourly_intervals, unit='m')
    times = np.array([t.split('T')[1] for t in times_str])

    # Create a DataFrame from repeated_times and profile_days
    times_profile_df = pd.DataFrame({
        'Datum': np.repeat(days_of_year, 24*4),  # Create a date for each hour of the day
        'Zeit': times,
        'ProfileDay': profile_days})
    
    # Combine all DataFrames in dataframes_type_days into one DataFrame
    combined_df = pd.concat([df.assign(ProfileDay=profile_day) for profile_day, df in all_data.items()])

    # Perform a left merge to maintain the structure of times_profile_df
    merged_df = pd.merge(times_profile_df, combined_df, on=['Zeit', 'ProfileDay'], how='left')

    # Extract the required columns
    electricity_demand = merged_df['Strombedarf normiert'].values
    heating_demand = merged_df['Heizwärme normiert'].values
    hot_water_demand = merged_df['Warmwasser normiert'].values

    return quarter_hourly_intervals, electricity_demand, heating_demand, hot_water_demand

# YEU - yearly energy usage
def calculation_load_profile(TRY, factors, building_type, number_people_household, YEU_electricity_kWh, 
                       YEU_heating_kWh, YEU_hot_water_kWh, holidays, climate_zone="9", year=2019):

    days_of_year, months, days, weekdays = generate_year_months_days_weekdays(year)

    # import weather data
    temperature, degree_of_coverage = import_TRY(TRY)

    daily_avg_temperature, daily_avg_degree_of_coverage = calculate_daily_averages(temperature, degree_of_coverage)
    
    season = np.where(daily_avg_temperature < 5, "W", np.where((daily_avg_temperature >= 5) & (daily_avg_temperature <= 15), "Ü", "S"))
    day_type = np.where((weekdays == 1) | np.isin(days_of_year, holidays), "S", "W")
    degree_of_coverage = np.where(season == "S", "X", np.where((daily_avg_degree_of_coverage >= 0) & (daily_avg_degree_of_coverage < 4), "H", "B"))
    
    type_day = np.char.add(np.char.add(season, day_type), degree_of_coverage)
    profile_day = np.char.add((building_type + climate_zone), type_day)

    factor_data = import_csv(factors)

    # vetorized calculation of the neccessary factors
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

# YEU - yearly energy usage
def calculate(YEU_heating_kWh, YEU_hot_water_kWh, YEU_electricity_kWh=1, building_type="MFH", number_people_household=2, year=2019, climate_zone="9"):
    # holidays
    Neujahr = "2019-01-01"
    Karfreitag = "2019-04-19"
    Ostermontag = "2019-04-22"
    Maifeiertag = "2019-05-01"
    Pfingstmontag = "2019-05-30"
    Christi_Himmelfahrt = "2019-06-10"
    Fronleichnam = "2019-06-20"
    Tag_der_deutschen_Einheit = "2019-10-03"
    Allerheiligen = "2019-11-01"
    Weihnachtsfeiertag1 = "2019-12-25"
    Weihnachtsfeiertag2 = "2019-12-26"

    holidays = np.array([Neujahr, Karfreitag, Ostermontag, Maifeiertag, Pfingstmontag, 
                Christi_Himmelfahrt, Fronleichnam, Tag_der_deutschen_Einheit, 
                Allerheiligen, Weihnachtsfeiertag1, Weihnachtsfeiertag2]).astype('datetime64[D]')
    
    TRY = get_resource_path('heat_requirement\TRY_511676144222\TRY2015_511676144222_Jahr.dat')
    factors = get_resource_path('heat_requirement\VDI 4655 data\Faktoren.csv')

    time_15min, electricity_kWh_15min, heating_kWh_15min, hot_water_kWh_15min, temperature = calculation_load_profile(TRY, factors, building_type, number_people_household, \
                                                                                                  YEU_electricity_kWh, YEU_heating_kWh, YEU_hot_water_kWh, \
                                                                                                    holidays, climate_zone, year)
    total_heat_kWh_15min = heating_kWh_15min + hot_water_kWh_15min
    electricity_kW, heating_kW, hot_water_kW, total_heat_kW = electricity_kWh_15min * 4, heating_kWh_15min * 4, hot_water_kWh_15min * 4, total_heat_kWh_15min * 4

    return time_15min, electricity_kW, heating_kW, hot_water_kW, total_heat_kW, temperature