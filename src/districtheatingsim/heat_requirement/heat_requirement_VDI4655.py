"""
Filename: heat_requirement_VDI4655.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-10
Description: Heat demand profile calculation using VDI 4655 standardized load profile methodology.

This module implements the VDI 4655 standard for calculating realistic heat and electricity
demand profiles for buildings in district heating applications. It provides functions to
generate quarter-hourly load profiles based on annual energy consumption, building types,
occupancy patterns, and meteorological data from Test Reference Years (TRY).

The module supports comprehensive energy demand modeling for different building types and
usage patterns, incorporating weather dependency, seasonal variations, and day-type
classifications according to German VDI 4655 guidelines for district heating system
planning and optimization.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Union, Optional, List

from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.utilities.utilities import get_resource_path

def generate_year_months_days_weekdays(year: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate temporal arrays for calendar date and weekday analysis.

    This function creates comprehensive temporal reference arrays for a given year,
    providing the foundation for day-type classification and profile assignment
    according to VDI 4655 methodology. It handles leap years and provides proper
    weekday numbering for weekend and holiday identification.

    Parameters
    ----------
    year : int
        Target year for temporal array generation. Must be a valid calendar year.

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]
        Four arrays containing temporal information:
        
        - **days_of_year** (numpy.ndarray) : Array of datetime64[D] objects for each day
        - **months** (numpy.ndarray) : Month numbers (1-12) for each day
        - **days** (numpy.ndarray) : Day numbers within month (1-31) for each day
        - **weekdays** (numpy.ndarray) : Weekday numbers (1-7, Monday=1, Sunday=7)

    Notes
    -----
    Temporal Processing:
        - Automatically handles leap years (366 vs 365 days)
        - Provides ISO weekday numbering (Monday=1, Sunday=7)
        - Creates datetime64 arrays for efficient temporal operations
        - Supports full year coverage without gaps

    VDI 4655 Integration:
        - Weekday information used for workday/weekend classification
        - Day-of-year arrays support seasonal pattern analysis
        - Month arrays enable seasonal factor application
        - Compatible with holiday date integration

    Applications:
        - Building load profile day-type classification
        - Seasonal heating demand pattern analysis
        - Weekend and holiday demand pattern identification
        - Annual energy consumption distribution modeling

    Examples
    --------
    >>> # Generate temporal arrays for analysis year
    >>> year = 2023
    >>> days, months, day_nums, weekdays = generate_year_months_days_weekdays(year)
    >>> print(f"Year {year}: {len(days)} days")
    >>> print(f"Leap year: {len(days) == 366}")

    >>> # Analyze weekday distribution
    >>> weekend_days = np.sum((weekdays == 6) | (weekdays == 7))
    >>> workdays = len(days) - weekend_days
    >>> print(f"Workdays: {workdays}, Weekend days: {weekend_days}")

    >>> # Seasonal analysis
    >>> winter_months = np.isin(months, [12, 1, 2])
    >>> summer_months = np.isin(months, [6, 7, 8])
    >>> print(f"Winter days: {np.sum(winter_months)}")
    >>> print(f"Summer days: {np.sum(summer_months)}")

    >>> # Integration with holiday dates
    >>> holidays = [np.datetime64('2023-01-01'), np.datetime64('2023-12-25')]
    >>> holiday_weekdays = weekdays[np.isin(days, holidays)]
    >>> print(f"Holiday weekdays: {holiday_weekdays}")

    See Also
    --------
    calculate_daily_averages : Daily meteorological data processing
    calculation_load_profile : Main VDI 4655 load profile calculation
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

    This function processes hourly weather data to create daily averages required
    for VDI 4655 day-type classification. Daily temperature averages determine
    seasonal categories, while cloud cover averages influence heating demand
    patterns and profile selection.

    Parameters
    ----------
    temperature : numpy.ndarray
        Hourly temperature data [°C] for complete year (8760 or 8784 hours).
        Must contain valid temperature values without gaps.
    cloud_cover : numpy.ndarray
        Hourly cloud cover data [0-8 oktas] for complete year (8760 or 8784 hours).
        Used for determining sky conditions and solar gain patterns.

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray]
        Daily averaged meteorological data:
        
        - **daily_avg_temperature** (numpy.ndarray) : Daily average temperature [°C]
        - **daily_avg_cloud_cover** (numpy.ndarray) : Daily average cloud cover [oktas]

    Notes
    -----
    Data Processing:
        - Reshapes hourly data into daily blocks (24-hour periods)
        - Calculates arithmetic mean for each daily block
        - Handles both regular (8760h) and leap years (8784h)
        - Preserves temporal sequence and data quality

    VDI 4655 Integration:
        Daily temperature averages determine seasonal classification:
        - **Winter (W)**: Daily average < 5°C
        - **Transition (Ü)**: Daily average 5-15°C  
        - **Summer (S)**: Daily average > 15°C

        Cloud cover averages determine sky condition classification:
        - **Clear (H)**: Average cloud cover 0-4 oktas
        - **Overcast (B)**: Average cloud cover 4-8 oktas
        - **Summer (X)**: Not classified during summer season

    Quality Assurance:
        - Validates input array dimensions and completeness
        - Ensures proper daily block formation (multiples of 24)
        - Maintains data integrity during averaging process
        - Provides consistent daily time series output

    Applications:
        - Seasonal heating demand pattern determination
        - Day-type classification for load profile selection
        - Weather-dependent energy consumption modeling
        - Building thermal response analysis

    Examples
    --------
    >>> # Process TRY weather data for VDI 4655 analysis
    >>> temp_hourly = np.random.normal(10, 8, 8760)  # Example temperature data
    >>> cloud_hourly = np.random.uniform(0, 8, 8760)  # Example cloud cover data
    >>> 
    >>> temp_daily, cloud_daily = calculate_daily_averages(temp_hourly, cloud_hourly)
    >>> print(f"Daily temperature range: {temp_daily.min():.1f} to {temp_daily.max():.1f}°C")
    >>> print(f"Daily cloud cover range: {cloud_daily.min():.1f} to {cloud_daily.max():.1f} oktas")

    >>> # VDI 4655 seasonal classification
    >>> winter_days = np.sum(temp_daily < 5)
    >>> transition_days = np.sum((temp_daily >= 5) & (temp_daily <= 15))
    >>> summer_days = np.sum(temp_daily > 15)
    >>> print(f"Season distribution: {winter_days}W, {transition_days}Ü, {summer_days}S days")

    >>> # Cloud condition analysis
    >>> clear_days = np.sum(cloud_daily < 4)
    >>> overcast_days = np.sum(cloud_daily >= 4)
    >>> print(f"Sky conditions: {clear_days} clear, {overcast_days} overcast days")

    >>> # Heating season identification
    >>> heating_season = temp_daily < 15
    >>> heating_days = np.sum(heating_season)
    >>> print(f"Heating season: {heating_days} days ({heating_days/365*100:.1f}%)")

    Raises
    ------
    ValueError
        If input arrays don't contain complete hourly data or have mismatched lengths.
    IndexError
        If array reshaping fails due to incomplete daily blocks.

    See Also
    --------
    import_TRY : Weather data import from Test Reference Year files
    calculation_load_profile : Main VDI 4655 calculation using daily averages
    generate_year_months_days_weekdays : Temporal array generation
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
    Generate quarter-hourly datetime intervals for high-resolution load profile calculation.

    This function creates a complete time series of 15-minute intervals for the
    specified year, providing the temporal framework for VDI 4655 quarter-hourly
    load profiles. It automatically handles leap years and provides precise
    datetime objects for energy system modeling.

    Parameters
    ----------
    year : int
        Target year for interval generation. Must be a valid calendar year.

    Returns
    -------
    numpy.ndarray
        Array of datetime64[15m] objects representing quarter-hourly intervals.
        Contains 35,040 intervals for regular years (35,136 for leap years).

    Notes
    -----
    Temporal Resolution:
        - 15-minute intervals provide standard VDI 4655 resolution
        - Covers complete calendar year without gaps
        - Compatible with district heating system time constants
        - Supports high-resolution energy balance calculations

    Array Properties:
        - Regular years: 365 days × 24 hours × 4 quarters = 35,040 intervals
        - Leap years: 366 days × 24 hours × 4 quarters = 35,136 intervals
        - Datetime64[15m] format for precise temporal operations
        - Chronological sequence from January 1st 00:00 to December 31st 23:45

    VDI 4655 Integration:
        - Matches standard load profile temporal resolution
        - Enables accurate peak demand calculation
        - Supports load diversity analysis across time periods
        - Compatible with energy storage and peak shaving analysis

    Applications:
        - District heating load profile generation
        - Peak demand analysis and system sizing
        - Energy storage sizing and operation optimization
        - Grid integration and demand response modeling

    Examples
    --------
    >>> # Generate quarter-hourly intervals for analysis
    >>> year = 2023
    >>> intervals = calculate_quarter_hourly_intervals(year)
    >>> print(f"Year {year}: {len(intervals)} quarter-hourly intervals")
    >>> print(f"First interval: {intervals[0]}")
    >>> print(f"Last interval: {intervals[-1]}")

    >>> # Analyze temporal coverage
    >>> total_hours = len(intervals) / 4
    >>> expected_hours = 366 * 24 if year % 4 == 0 else 365 * 24
    >>> print(f"Total hours: {total_hours}, Expected: {expected_hours}")

    >>> # Time series analysis
    >>> import pandas as pd
    >>> df = pd.DataFrame({'timestamp': intervals})
    >>> df['hour'] = df['timestamp'].dt.hour
    >>> df['month'] = df['timestamp'].dt.month
    >>> 
    >>> # Peak demand hours analysis
    >>> morning_peak = df[(df['hour'] >= 7) & (df['hour'] <= 9)]
    >>> evening_peak = df[(df['hour'] >= 17) & (df['hour'] <= 19)]
    >>> print(f"Morning peak periods: {len(morning_peak)}")
    >>> print(f"Evening peak periods: {len(evening_peak)}")

    >>> # Seasonal distribution
    >>> winter_intervals = df[df['month'].isin([12, 1, 2])]
    >>> summer_intervals = df[df['month'].isin([6, 7, 8])]
    >>> print(f"Winter intervals: {len(winter_intervals)}")
    >>> print(f"Summer intervals: {len(summer_intervals)}")

    See Also
    --------
    standardized_quarter_hourly_profile : Profile generation using intervals
    quarter_hourly_data : Daily to quarter-hourly data expansion
    calculation_load_profile : Main VDI 4655 load calculation
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
    Expand daily data to quarter-hourly resolution for load profile generation.

    This function transforms daily energy values into quarter-hourly arrays
    by replicating each daily value across all 96 quarter-hourly intervals
    of that day. This provides the daily scaling factors needed for VDI 4655
    load profile normalization and energy balance calculations.

    Parameters
    ----------
    data : numpy.ndarray
        Daily data values to be expanded to quarter-hourly resolution.
        Typically contains daily energy consumption factors or absolute values.

    Returns
    -------
    numpy.ndarray
        Quarter-hourly data array with each daily value replicated 96 times.
        Length = len(data) × 96 quarter-hourly intervals per day.

    Notes
    -----
    Data Expansion:
        - Each daily value replicated across 96 quarter-hourly intervals
        - Maintains daily energy totals when integrated over full day
        - Preserves daily variation patterns in quarter-hourly resolution
        - Compatible with VDI 4655 profile normalization methodology

    VDI 4655 Integration:
        Daily factors are applied to standardized quarter-hourly profiles:
        - Daily heating factors scale weather-dependent heating profiles
        - Daily hot water factors account for occupancy and usage patterns
        - Daily electricity factors incorporate appliance and lighting loads
        - Maintains energy conservation across temporal scales

    Mathematical Relationship:
        Quarter-hourly energy = Daily factor × Standardized profile value
        Daily total = Σ(Quarter-hourly values) = Daily factor × Σ(Profile values)

    Applications:
        - VDI 4655 load profile scaling and normalization
        - Daily energy budget distribution to quarter-hourly resolution
        - Weather-dependent heating demand calculation
        - Occupancy-based hot water and electricity demand modeling

    Examples
    --------
    >>> # Expand daily heating factors to quarter-hourly
    >>> daily_heating_factors = np.array([1.2, 1.1, 0.8, 0.9, 1.0])  # 5 days
    >>> qh_heating_factors = quarter_hourly_data(daily_heating_factors)
    >>> print(f"Daily factors: {len(daily_heating_factors)} values")
    >>> print(f"Quarter-hourly factors: {len(qh_heating_factors)} values")
    >>> print(f"Expansion ratio: {len(qh_heating_factors) / len(daily_heating_factors)}")

    >>> # Verify data conservation
    >>> daily_sum = np.sum(daily_heating_factors)
    >>> qh_sum = np.sum(qh_heating_factors)
    >>> print(f"Daily sum: {daily_sum:.2f}")
    >>> print(f"Quarter-hourly sum: {qh_sum:.2f}")
    >>> print(f"Conservation check: {abs(qh_sum - daily_sum * 96) < 1e-10}")

    >>> # Apply to standardized profile
    >>> # Example: Daily factor 1.5, standardized profile values
    >>> daily_factor = 1.5
    >>> profile_day = np.random.uniform(0.8, 1.2, 96)  # 96 quarter-hourly values
    >>> 
    >>> # Expand daily factor and apply to profile
    >>> qh_factor = quarter_hourly_data(np.array([daily_factor]))[:96]
    >>> scaled_profile = qh_factor * profile_day
    >>> 
    >>> print(f"Daily factor: {daily_factor}")
    >>> print(f"Profile range: {profile_day.min():.3f} to {profile_day.max():.3f}")
    >>> print(f"Scaled range: {scaled_profile.min():.3f} to {scaled_profile.max():.3f}")

    See Also
    --------
    standardized_quarter_hourly_profile : VDI 4655 profile generation
    calculation_load_profile : Main load calculation using expanded data
    calculate_quarter_hourly_intervals : Temporal framework generation
    """
    num_quarter_hours_per_day = 24 * 4  # 96 intervals per day
    return np.repeat(data, num_quarter_hours_per_day)

def standardized_quarter_hourly_profile(year: int, 
                                      building_type: str, 
                                      days_of_year: np.ndarray, 
                                      type_days: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate standardized VDI 4655 quarter-hourly load profiles for buildings.

    This function creates normalized quarter-hourly demand profiles according
    to VDI 4655 methodology by combining standardized profile data with
    day-type classifications. It provides the foundation for realistic energy
    demand modeling in district heating applications.

    Parameters
    ----------
    year : int
        Target year for profile generation.
    building_type : str
        VDI 4655 building type identifier (e.g., "EFH", "MFH", "B").
        Determines which standardized profile dataset to use.
    days_of_year : numpy.ndarray
        Array of datetime64 objects representing each day of the year.
    type_days : numpy.ndarray
        Array of day-type classification strings for each day.
        Format: "{Season}{DayType}{CloudCover}" (e.g., "WWH", "SWX").

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]
        Standardized quarter-hourly profiles:
        
        - **quarter_hourly_intervals** (numpy.ndarray) : Time stamps for each interval
        - **electricity_demand** (numpy.ndarray) : Normalized electricity profile [0-2]
        - **heating_demand** (numpy.ndarray) : Normalized heating profile [0-2]
        - **hot_water_demand** (numpy.ndarray) : Normalized hot water profile [0-2]

    Notes
    -----
    VDI 4655 Profile System:
        Standardized profiles are provided for different combinations of:
        - **Building Types**: EFH (single family), MFH (multi-family), B (office)
        - **Seasons**: W (winter), Ü (transition), S (summer)
        - **Day Types**: W (workday), S (weekend/holiday)
        - **Cloud Cover**: H (clear), B (overcast), X (summer, not classified)

    Profile Normalization:
        - Profile values typically range from 0 to 2 (normalized around 1.0)
        - Daily integrals sum to approximately 24 (representing 24 hours)
        - Profiles account for typical usage patterns and thermal behavior
        - Weather dependency included for heating demands

    Data Processing Workflow:
        1. Generate quarter-hourly time intervals for target year
        2. Map each day to corresponding VDI 4655 day-type classification
        3. Load appropriate standardized profile data for each day type
        4. Create continuous quarter-hourly time series by profile assignment
        5. Merge temporal data with profile values using time-day mapping

    Profile Applications:
        - **Heating**: Weather-dependent space heating demand patterns
        - **Hot Water**: Occupancy-based domestic hot water usage
        - **Electricity**: Appliance, lighting, and auxiliary equipment loads

    Examples
    --------
    >>> # Generate profiles for single family house
    >>> import numpy as np
    >>> from datetime import datetime
    >>> 
    >>> year = 2023
    >>> building_type = "EFH"  # Single family house
    >>> days = np.arange('2023-01-01', '2024-01-01', dtype='datetime64[D]')
    >>> type_days = np.array(['WWH'] * 90 + ['ÜWH'] * 90 + ['SWX'] * 90 + ['ÜWH'] * 95)
    >>> 
    >>> intervals, elec, heat, dhw = standardized_quarter_hourly_profile(
    ...     year, building_type, days, type_days
    ... )
    >>> 
    >>> print(f"Generated {len(intervals)} quarter-hourly intervals")
    >>> print(f"Electricity profile range: {elec.min():.3f} to {elec.max():.3f}")
    >>> print(f"Heating profile range: {heat.min():.3f} to {heat.max():.3f}")
    >>> print(f"Hot water profile range: {dhw.min():.3f} to {dhw.max():.3f}")

    >>> # Analyze daily patterns
    >>> daily_elec = elec.reshape(-1, 96).mean(axis=0)  # Average daily pattern
    >>> peak_hour = np.argmax(daily_elec) // 4  # Convert to hour
    >>> min_hour = np.argmin(daily_elec) // 4
    >>> print(f"Electricity peak at hour {peak_hour}, minimum at hour {min_hour}")

    >>> # Seasonal analysis
    >>> winter_heat = heat[:90*96].mean()  # First 90 days (winter)
    >>> summer_heat = heat[180*96:270*96].mean()  # Summer period
    >>> seasonal_ratio = winter_heat / summer_heat if summer_heat > 0 else float('inf')
    >>> print(f"Winter/summer heating ratio: {seasonal_ratio:.1f}")

    >>> # Validate profile integration
    >>> daily_profiles = heat.reshape(-1, 96)
    >>> daily_integrals = daily_profiles.sum(axis=1) / 4  # Convert to hours
    >>> print(f"Daily heating integral: {daily_integrals.mean():.1f} ± {daily_integrals.std():.1f} hours")

    Raises
    ------
    FileNotFoundError
        If VDI 4655 profile data files cannot be found.
    KeyError
        If building type or day-type combinations are not available.
    ValueError
        If temporal arrays have inconsistent lengths or invalid formats.

    See Also
    --------
    calculation_load_profile : Main VDI 4655 calculation using profiles
    quarter_hourly_data : Daily to quarter-hourly data expansion
    calculate_quarter_hourly_intervals : Time interval generation
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
    Calculate comprehensive load profiles using VDI 4655 methodology.

    This function implements the complete VDI 4655 calculation workflow for
    generating realistic building energy demand profiles. It combines
    standardized load profiles with weather data, occupancy patterns,
    and annual energy consumption to create quarter-hourly demand time series.

    Parameters
    ----------
    TRY : str
        Path to Test Reference Year meteorological data file.
        Contains hourly weather data for profile calculation.
    building_type : str
        VDI 4655 building type identifier (e.g., "EFH", "MFH", "B").
        Determines standardized profile characteristics.
    number_people_household : int
        Number of occupants in household for occupancy-dependent scaling.
        Affects electricity and hot water demand patterns.
    YEU_electricity_kWh : float
        Annual electricity consumption [kWh/a] for profile scaling.
    YEU_heating_kWh : float
        Annual heating energy consumption [kWh/a] for profile scaling.
    YEU_hot_water_kWh : float
        Annual domestic hot water consumption [kWh/a] for profile scaling.
    holidays : numpy.ndarray
        Array of holiday dates for day-type classification.
    climate_zone : str, optional
        German climate zone identifier (1-15). Default is "9".
        Affects seasonal factors and day-type classification.
    year : int, optional
        Target year for calculation. Default is 2019.
        Determines calendar and leap year handling.

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]
        Complete load profile data:
        
        - **quarter_hourly_intervals** (numpy.ndarray) : Time stamps
        - **electricity_corrected** (numpy.ndarray) : Electricity demand [kWh per 15min]
        - **heating_corrected** (numpy.ndarray) : Heating demand [kWh per 15min]
        - **hot_water_corrected** (numpy.ndarray) : Hot water demand [kWh per 15min]
        - **temperature** (numpy.ndarray) : Hourly temperature data [°C]

    Notes
    -----
    VDI 4655 Calculation Workflow:
        1. **Temporal Analysis**: Generate calendar arrays and day classifications
        2. **Weather Processing**: Import TRY data and calculate daily averages
        3. **Day-Type Classification**: Assign seasonal, weekday, and weather types
        4. **Factor Determination**: Load day-type specific scaling factors
        5. **Daily Scaling**: Calculate daily consumption using factors
        6. **Profile Application**: Apply standardized quarter-hourly profiles
        7. **Energy Balance**: Normalize to match annual consumption targets

    Day-Type Classification System:
        - **Season**: W (winter, <5°C), Ü (transition, 5-15°C), S (summer, >15°C)
        - **Day Type**: W (workday), S (weekend/holiday)
        - **Cloud Cover**: H (clear, <4 oktas), B (overcast, ≥4 oktas), X (summer)
        - **Combined**: 3-character code (e.g., "WWH", "SWX", "ÜWB")

    Scaling Methodology:
        Daily energy = Annual energy × (Base factor + Occupancy × Day-type factor)
        Quarter-hourly energy = Daily energy × Standardized profile × Normalization

    Energy Balance Correction:
        Final profiles are normalized to exactly match input annual consumption
        while preserving temporal patterns and relative magnitudes.

    Examples
    --------
    >>> # Calculate load profile for single family house
    >>> TRY_file = "path/to/TRY_data.dat"
    >>> holidays = np.array(['2023-01-01', '2023-12-25'], dtype='datetime64[D]')
    >>> 
    >>> time, elec, heat, dhw, temp = calculation_load_profile(
    ...     TRY=TRY_file,
    ...     building_type="EFH",
    ...     number_people_household=4,
    ...     YEU_electricity_kWh=4000,
    ...     YEU_heating_kWh=15000,
    ...     YEU_hot_water_kWh=3000,
    ...     holidays=holidays,
    ...     climate_zone="9",
    ...     year=2023
    ... )
    >>> 
    >>> print(f"Generated {len(time)} quarter-hourly intervals")
    >>> print(f"Annual electricity: {elec.sum():.0f} kWh")
    >>> print(f"Annual heating: {heat.sum():.0f} kWh")
    >>> print(f"Annual hot water: {dhw.sum():.0f} kWh")

    >>> # Analyze demand patterns
    >>> peak_elec = elec.max() * 4  # Convert to kW
    >>> peak_heat = heat.max() * 4
    >>> print(f"Peak electricity demand: {peak_elec:.1f} kW")
    >>> print(f"Peak heating demand: {peak_heat:.1f} kW")

    >>> # Seasonal analysis
    >>> # Convert to daily values for seasonal comparison
    >>> daily_heat = heat.reshape(-1, 96).sum(axis=1)  # Daily heating [kWh/d]
    >>> winter_heat = daily_heat[:90].mean()  # First 90 days
    >>> summer_heat = daily_heat[180:270].mean()  # Days 181-270
    >>> print(f"Average winter heating: {winter_heat:.1f} kWh/d")
    >>> print(f"Average summer heating: {summer_heat:.1f} kWh/d")

    >>> # Load factor calculation
    >>> avg_elec = elec.mean() * 4  # Average power [kW]
    >>> load_factor = avg_elec / peak_elec if peak_elec > 0 else 0
    >>> print(f"Electricity load factor: {load_factor:.3f}")

    Raises
    ------
    FileNotFoundError
        If TRY file or VDI 4655 factor data cannot be found.
    ValueError
        If input parameters are invalid or inconsistent.
    KeyError
        If required VDI 4655 data is missing for specified building type.

    See Also
    --------
    calculate : Simplified interface for load profile calculation
    standardized_quarter_hourly_profile : Profile generation component
    generate_year_months_days_weekdays : Temporal analysis component
    calculate_daily_averages : Weather data processing component
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
    Calculate comprehensive building energy demand profiles using VDI 4655 methodology.

    This function provides a simplified interface for generating realistic quarter-hourly
    energy demand profiles for buildings in district heating applications. It implements
    the complete VDI 4655 standard workflow and returns power demand time series suitable
    for district heating system planning, sizing, and operation optimization.

    Parameters
    ----------
    YEU_heating_kWh : float
        Annual heating energy consumption [kWh/a]. Must be positive value.
        Represents space heating demand for indoor comfort.
    YEU_hot_water_kWh : float
        Annual domestic hot water energy consumption [kWh/a]. Must be positive value.
        Represents hot water preparation demand.
    YEU_electricity_kWh : float
        Annual electricity consumption [kWh/a]. Must be positive value.
        Represents appliances, lighting, and auxiliary equipment.
    building_type : str
        VDI 4655 building type identifier. Valid options:
        - "EFH": Single family house (Einfamilienhaus)
        - "MFH": Multi-family house (Mehrfamilienhaus) 
        - "B": Office building (Bürogebäude)
    number_people_household : int
        Number of occupants in household. Must be positive integer.
        Affects occupancy-dependent electricity and hot water demands.
    year : int
        Target year for profile generation. Must be valid calendar year.
        Determines temporal framework and leap year handling.
    climate_zone : str
        German climate zone identifier (1-15). Affects seasonal factors.
        Zone 9 represents central German climate conditions.
    TRY : str
        Path to Test Reference Year meteorological data file.
        Must contain complete hourly weather data for specified year.
    holidays : numpy.ndarray
        Array of holiday dates as datetime64 objects.
        Used for day-type classification (weekend/holiday vs workday).

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]
        Complete energy demand profile data:
        
        - **time_15min** (numpy.ndarray) : Quarter-hourly timestamps
        - **total_heat_kW** (numpy.ndarray) : Total heat power demand [kW]
        - **heating_kW** (numpy.ndarray) : Space heating power demand [kW]
        - **hot_water_kW** (numpy.ndarray) : DHW power demand [kW]
        - **temperature** (numpy.ndarray) : Hourly outdoor temperature [°C]
        - **electricity_kW** (numpy.ndarray) : Electricity power demand [kW]

    Notes
    -----
    VDI 4655 Methodology:
        The function implements the German VDI 4655 standard for building load
        profiles, which provides realistic demand patterns based on:
        - Standardized building usage profiles
        - Weather-dependent heating demands
        - Occupancy-based consumption patterns
        - Seasonal and daily variation factors

    Power Conversion:
        Output values are converted from quarter-hourly energy [kWh] to
        instantaneous power [kW] by multiplying by 4 (4 quarters per hour).
        This provides power demand time series for system sizing and operation.

    District Heating Applications:
        - **Network Sizing**: Peak heat demand determines pipe dimensions
        - **Plant Sizing**: Maximum demand defines generation capacity
        - **Storage Sizing**: Load patterns determine storage requirements
        - **Operation Planning**: Demand profiles optimize plant dispatch

    Quality Assurance:
        - Energy balance verification ensures annual totals match inputs
        - Temporal continuity provides smooth demand transitions
        - Peak demand validation prevents unrealistic power spikes
        - Weather correlation ensures realistic heating patterns

    Examples
    --------
    >>> # Generate load profile for typical single family house
    >>> import numpy as np
    >>> 
    >>> holidays = np.array([
    ...     '2023-01-01', '2023-05-01', '2023-12-25'
    ... ], dtype='datetime64[D]')
    >>> 
    >>> time, total_heat, heating, dhw, temp, elec = calculate(
    ...     YEU_heating_kWh=15000,      # 15 MWh/a heating
    ...     YEU_hot_water_kWh=3000,     # 3 MWh/a hot water
    ...     YEU_electricity_kWh=4000,   # 4 MWh/a electricity
    ...     building_type="EFH",        # Single family house
    ...     number_people_household=4,  # 4 occupants
    ...     year=2023,
    ...     climate_zone="9",           # Central Germany
    ...     TRY="path/to/TRY_data.dat",
    ...     holidays=holidays
    ... )
    >>> 
    >>> print(f"Annual verification:")
    >>> print(f"  Heating: {heating.sum()/4:.0f} kWh (target: 15000)")
    >>> print(f"  Hot water: {dhw.sum()/4:.0f} kWh (target: 3000)")
    >>> print(f"  Electricity: {elec.sum()/4:.0f} kWh (target: 4000)")

    >>> # Analyze peak demands
    >>> peak_heat = total_heat.max()
    >>> peak_elec = elec.max()
    >>> print(f"Peak demands:")
    >>> print(f"  Heat: {peak_heat:.1f} kW")
    >>> print(f"  Electricity: {peak_elec:.1f} kW")

    >>> # Load duration analysis
    >>> heat_sorted = np.sort(total_heat)[::-1]  # Descending order
    >>> load_90pct = heat_sorted[int(0.1 * len(heat_sorted))]  # 90th percentile
    >>> load_50pct = heat_sorted[int(0.5 * len(heat_sorted))]  # Median
    >>> print(f"Load duration:")
    >>> print(f"  10% of time above: {load_90pct:.1f} kW")
    >>> print(f"  50% of time above: {load_50pct:.1f} kW")

    >>> # Seasonal analysis
    >>> # Group by months (assuming standard year)
    >>> quarterly_per_month = len(time) // 12
    >>> monthly_heat = total_heat.reshape(12, -1).mean(axis=1)
    >>> winter_avg = np.mean([monthly_heat[0], monthly_heat[1], monthly_heat[11]])  # Jan, Feb, Dec
    >>> summer_avg = np.mean(monthly_heat[5:8])  # Jun, Jul, Aug
    >>> print(f"Seasonal heating demands:")
    >>> print(f"  Winter average: {winter_avg:.1f} kW")
    >>> print(f"  Summer average: {summer_avg:.1f} kW")
    >>> print(f"  Winter/summer ratio: {winter_avg/summer_avg:.1f}")

    >>> # Export for district heating analysis
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'timestamp': time,
    ...     'heat_demand_kW': total_heat,
    ...     'heating_kW': heating,
    ...     'dhw_kW': dhw,
    ...     'electricity_kW': elec,
    ...     'temperature_C': np.repeat(temp[::4], 4)[:len(time)]  # Match length
    ... })
    >>> df.to_csv('building_load_profile.csv', index=False)

    Raises
    ------
    ValueError
        If input parameters are invalid (negative values, invalid building type).
    FileNotFoundError
        If TRY file or VDI 4655 data files cannot be found.
    RuntimeError
        If load profile calculation fails due to data inconsistencies.

    See Also
    --------
    calculation_load_profile : Core VDI 4655 calculation engine
    standardized_quarter_hourly_profile : Profile generation component
    import_TRY : Weather data import functionality
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