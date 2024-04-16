import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os
import sys

def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

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

    return temperature

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

def calculate_daily_averages(temperature):
    # Assumption: The length of each array corresponds to the number of hours in a year
    num_hours = temperature.size
    num_days = num_hours // 24

    # Reshape the arrays to get daily data
    daily_temperature = temperature.reshape((num_days, 24))

    # Calculate daily averages
    daily_avg_temperature = np.mean(daily_temperature, axis=1)

    return daily_avg_temperature

def calculate_hourly_intervals(year):
    # First day of the year
    start_date = np.datetime64(f'{year}-01-01')
    # Number of days in the year (consider leap year)
    num_days = 366 if np.datetime64(f'{year}-12-31') - np.datetime64(f'{year}-01-01') == np.timedelta64(365, 'D') else 365

    # Number of quarter-hour intervals in the year
    num_hours = num_days * 24

    # Create an array with all quarter-hourly intervals for the year
    hourly_intervals = np.arange(start_date, start_date + np.timedelta64(num_hours, 'h'), dtype='datetime64[h]')

    return hourly_intervals

# function for getting the coefficients
def get_coefficients(profiletype, subtype, daily_data):
    profile = profiletype + subtype
    row = daily_data[daily_data['Standardlastprofil'] == profile].iloc[0]
    return float(row['A']), float(row['B']), float(row['C']), float(row['D']), float(row['mH']), float(row['bH']), float(row['mW']), float(row['bW'])

# function for getting the weekday factor
def get_weekday_factor(daily_weekdays, profiletype, subtype, daily_data):
    profil = profiletype + subtype
    profil_row = daily_data[daily_data['Standardlastprofil'] == profil]

    if profil_row.empty:
        raise ValueError("Profil nicht gefunden")

    weekday_factors = np.array([profil_row.iloc[0][str(day)] for day in daily_weekdays]).astype(float)

    return weekday_factors

def calculation_load_profile(TRY, JWB_kWh, profiletype, subtype, holidays, year):
    days_of_year, months, days, daily_weekdays = generate_year_months_days_weekdays(year)

    # import weather data
    hourly_temperature = import_TRY(TRY)

    # process temperature data
    daily_avg_temperature = np.round(calculate_daily_averages(hourly_temperature), 1)
    daily_reference_temperature = np.round((daily_avg_temperature+2.5)*2, -1)/2-2.5

    daily_data = pd.read_csv(get_resource_path('heat_requirement\BDEW factors\daily_coefficients.csv'), delimiter=';')

    # calculate daily factors
    h_A, h_B, h_C, h_D, mH, bH, mW, bW = get_coefficients(profiletype, subtype, daily_data)
    lin = mH + bH + mW + bW
    h_T = h_A/(1+(h_B/(daily_avg_temperature-40))**h_C)+h_D+lin

    # calculate weekday factors
    F_D = get_weekday_factor(daily_weekdays, profiletype, subtype, daily_data)
    h_T_F_D = h_T * F_D
    sum_h_T_F_D = np.sum(h_T_F_D)
    KW_kWh = JWB_kWh/sum_h_T_F_D
    daily_heat_demand = h_T_F_D * KW_kWh

    # calculate hourly data
    hourly_reference_temperature = np.round((hourly_temperature+2.5)*2, -1)/2-2.5
    hourly_reference_temperature_2 = np.where(hourly_reference_temperature>hourly_temperature, hourly_reference_temperature-5, \
                                              np.where(hourly_reference_temperature>27.5, 27.5, hourly_reference_temperature+5))
    
    upper_limit = np.where(hourly_reference_temperature_2>hourly_reference_temperature, hourly_reference_temperature_2, hourly_reference_temperature)
    lower_limit = np.where(hourly_reference_temperature_2>hourly_reference_temperature, hourly_reference_temperature, hourly_reference_temperature_2)

    daily_hours = np.tile(np.arange(24), len(days_of_year))
    hourly_weekdays = np.repeat(daily_weekdays, 24)
    hourly_daily_heat_demand = np.repeat(daily_heat_demand, 24)
    
    hourly_data = pd.read_csv(get_resource_path('heat_requirement\BDEW factors\hourly_coefficients.csv'), delimiter=';')
    filtered_hourly_data = hourly_data[hourly_data["Typ"]==profiletype]

    # create dataframe
    hourly_conditions = pd.DataFrame({
        'Wochentag': hourly_weekdays,
        'TemperaturLower': lower_limit,
        'TemperaturUpper': upper_limit,
        'Stunde': daily_hours
    })

    # merging data
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

    # final calculation
    hour_factor_interpolation = hour_factor_T2+(hour_factor_T1-hour_factor_T2)*((hourly_temperature-upper_limit)/(5))
    hourly_heat_demand = np.nan_to_num((hourly_daily_heat_demand*hour_factor_interpolation)/100).astype(float)
    hourly_heat_demand_normed = (hourly_heat_demand / np.sum(hourly_heat_demand)) * JWB_kWh
    hourly_intervals = calculate_hourly_intervals(year)

    return hourly_intervals, hourly_heat_demand_normed.astype(float), hourly_temperature

def calculate(JWB_kWh=10000, profiletype="HMF", subtyp="03", year=2021):
    # holidays
    Neujahr = "2021-01-01"
    Karfreitag = "2021-04-02"
    Ostermontag = "2021-04-05"
    Maifeiertag = "2021-05-01"
    Pfingstmontag = "2021-05-24"
    Christi_Himmelfahrt = "2021-05-13"
    Fronleichnam = "2021-06-03"
    Tag_der_deutschen_Einheit = "2021-10-03"
    Allerheiligen = "2021-11-01"
    Weihnachtsfeiertag1 = "2021-12-25"
    Weihnachtsfeiertag2 = "2021-12-26"

    Feiertage = np.array([Neujahr, Karfreitag, Ostermontag, Maifeiertag, Pfingstmontag, 
                Christi_Himmelfahrt, Fronleichnam, Tag_der_deutschen_Einheit, 
                Allerheiligen, Weihnachtsfeiertag1, Weihnachtsfeiertag2]).astype('datetime64[D]')

    TRY = get_resource_path('heat_requirement\TRY_511676144222\TRY2015_511676144222_Jahr.dat')

    hourly_intervals, hourly_heat_demand, hourly_temperature = calculation_load_profile(TRY, JWB_kWh, profiletype, subtyp, Feiertage, year)

    return hourly_intervals, hourly_heat_demand, hourly_temperature
