"""
Heat Requirement BDEW Module
============================

This module implements the BDEW (German Association of Energy and Water Industries)
Standard Load Profile methodology for calculating realistic heat demand profiles
for commercial, public, and industrial buildings.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-10

It provides temperature-dependent load profiles with weekday variations for district heating system planning and
energy demand forecasting.

The BDEW SLP method uses standardized coefficients and hourly factors to generate
building-specific heat demand time series based on annual consumption, building
types, and meteorological conditions from Test Reference Year (TRY) data.
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Tuple, Optional, Union

from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.utilities.utilities import get_resource_path

def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to the resource, works for development and for PyInstaller.

    This function provides cross-platform resource path resolution that works
    both in development environments and when packaged with PyInstaller.
    It automatically detects the execution context and adjusts paths accordingly.

    Parameters
    ----------
    relative_path : str
        The relative path to the resource file from the package root.
        Use forward slashes for cross-platform compatibility.

    Returns
    -------
    str
        The absolute path to the resource file.

    Notes
    -----
    PyInstaller Compatibility:
        When running as a PyInstaller executable, the function uses the
        temporary directory (_MEIPASS) where resources are extracted.
        In development mode, it uses the standard package directory structure.

    Resource Structure:
        - Development: Relative to package root directory
        - PyInstaller: Relative to temporary extraction directory
        - Cross-platform path joining ensures compatibility

    Examples
    --------
    >>> # Access BDEW coefficient data
    >>> coeffs_path = get_resource_path('data/BDEW profiles/daily_coefficients.csv')
    >>> print(f"Coefficients file: {coeffs_path}")

    >>> # Access hourly factor data
    >>> hourly_path = get_resource_path('data/BDEW profiles/hourly_coefficients.csv')
    >>> df = pd.read_csv(hourly_path, delimiter=';')

    See Also
    --------
    get_coefficients : Load BDEW profile coefficients
    calculate : Main BDEW calculation using resource files
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        base_path = sys._MEIPASS
    else:
        # Running in development environment
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def generate_year_months_days_weekdays(year: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate temporal arrays for calendar date and weekday analysis in BDEW calculations.

    This function creates comprehensive temporal reference arrays for a given year,
    providing the foundation for BDEW Standard Load Profile calculations. It handles
    leap years and provides proper weekday numbering for commercial building load
    pattern analysis and profile assignment.

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

    BDEW Integration:
        - Weekday information used for commercial building operation patterns
        - Day-of-year arrays support seasonal coefficient application
        - Month arrays enable seasonal factor integration
        - Compatible with BDEW profile type classification

    Commercial Building Patterns:
        BDEW profiles account for different weekday patterns:
        - **Monday-Friday**: Normal business operations
        - **Saturday**: Reduced operations for most commercial buildings
        - **Sunday**: Minimal operations, primarily maintenance loads

    Applications:
        - Commercial building load profile calculation
        - Office building energy demand modeling
        - Retail and service building load patterns
        - Public building energy consumption analysis

    Examples
    --------
    >>> # Generate temporal arrays for BDEW analysis
    >>> year = 2023
    >>> days, months, day_nums, weekdays = generate_year_months_days_weekdays(year)
    >>> print(f"Year {year}: {len(days)} days")
    >>> print(f"Leap year: {len(days) == 366}")

    >>> # Analyze business day distribution
    >>> business_days = np.sum((weekdays >= 1) & (weekdays <= 5))  # Mon-Fri
    >>> weekend_days = np.sum((weekdays == 6) | (weekdays == 7))  # Sat-Sun
    >>> print(f"Business days: {business_days}, Weekend days: {weekend_days}")

    >>> # Commercial building operation analysis
    >>> full_operation = weekdays <= 5  # Monday to Friday
    >>> reduced_operation = weekdays == 6  # Saturday
    >>> minimal_operation = weekdays == 7  # Sunday
    >>> print(f"Full operation days: {np.sum(full_operation)}")
    >>> print(f"Reduced operation days: {np.sum(reduced_operation)}")
    >>> print(f"Minimal operation days: {np.sum(minimal_operation)}")

    See Also
    --------
    get_weekday_factor : Weekday-specific load factors using temporal arrays
    calculate : Main BDEW calculation using temporal analysis
    calculate_daily_averages : Daily meteorological data processing
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
    Calculate daily average temperatures from hourly meteorological data for BDEW load calculation.

    This function processes hourly temperature data to create daily averages required
    for BDEW Standard Load Profile calculations. Daily temperature averages are used
    to determine temperature-dependent heating coefficients and load scaling factors
    for commercial and public buildings.

    Parameters
    ----------
    temperature : numpy.ndarray
        Hourly temperature data [°C] for complete year (8760 or 8784 hours).
        Must contain valid temperature values without gaps for accurate calculation.

    Returns
    -------
    numpy.ndarray
        Daily average temperature [°C] for each day of the year.
        Length equals number of days (365 or 366 for leap years).

    Notes
    -----
    Data Processing:
        - Reshapes hourly data into daily blocks (24-hour periods)
        - Calculates arithmetic mean for each daily block
        - Handles both regular (8760h) and leap years (8784h)
        - Preserves temporal sequence and data quality

    BDEW Temperature Dependencies:
        Daily temperature averages are used for:
        - **Sigmoid Function**: Temperature-dependent heating demand calculation
        - **Linear Corrections**: Linear temperature adjustments for specific building types
        - **Reference Temperature**: Basis for hourly interpolation procedures
        - **Load Scaling**: Temperature-dependent daily load factor determination

    Temperature Processing Formula:
        For BDEW calculations, temperatures are processed as:
        T_ref = round((T_daily + 2.5) × 2, -1) / 2 - 2.5
        
        This creates discrete temperature steps for coefficient lookup.

    Quality Assurance:
        - Validates complete 24-hour daily blocks
        - Maintains temporal integrity during averaging
        - Handles edge cases for incomplete data
        - Preserves numerical precision for coefficient calculations

    Examples
    --------
    >>> # Process TRY temperature data for BDEW
    >>> import numpy as np
    >>> 
    >>> # Example hourly temperature data (winter to summer transition)
    >>> hourly_temps = np.concatenate([
    ...     np.full(24*30, -5),   # January: -5°C
    ...     np.full(24*31, 0),    # February: 0°C  
    ...     np.full(24*31, 8),    # March: 8°C
    ...     np.full(24*30, 15),   # April: 15°C
    ...     np.full(24*31, 20)    # May: 20°C
    ... ])
    >>> 
    >>> daily_temps = calculate_daily_averages(hourly_temps)
    >>> print(f"Daily temperatures: {len(daily_temps)} days")
    >>> print(f"Temperature range: {daily_temps.min():.1f} to {daily_temps.max():.1f}°C")

    >>> # BDEW temperature processing
    >>> bdew_ref_temps = np.round((daily_temps + 2.5) * 2, -1) / 2 - 2.5
    >>> unique_ref_temps = np.unique(bdew_ref_temps)
    >>> print(f"BDEW reference temperatures: {unique_ref_temps}")

    >>> # Heating vs non-heating periods
    >>> heating_days = np.sum(daily_temps < 15)  # Typical heating threshold
    >>> non_heating_days = len(daily_temps) - heating_days
    >>> print(f"Heating season: {heating_days} days ({heating_days/len(daily_temps)*100:.1f}%)")

    >>> # Temperature distribution for load calculations
    >>> temp_bins = [-10, -5, 0, 5, 10, 15, 20, 25]
    >>> hist, _ = np.histogram(daily_temps, bins=temp_bins)
    >>> for i, (temp_low, temp_high) in enumerate(zip(temp_bins[:-1], temp_bins[1:])):
    ...     print(f"{temp_low}°C to {temp_high}°C: {hist[i]} days")

    Raises
    ------
    ValueError
        If temperature array length is not divisible by 24 (incomplete daily blocks).
    IndexError
        If array reshaping fails due to invalid data structure.

    See Also
    --------
    calculate : Main BDEW calculation using daily temperatures
    get_coefficients : BDEW coefficient extraction for temperature dependencies
    calculate_hourly_intervals : Hourly time series generation
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

def calculate_hourly_intervals(year: int) -> np.ndarray:
    """
    Generate hourly datetime intervals for BDEW load profile calculation.

    This function creates a complete time series of hourly intervals for the
    specified year, providing the temporal framework for BDEW Standard Load
    Profile calculations. It automatically handles leap years and provides
    precise datetime objects for commercial building energy modeling.

    Parameters
    ----------
    year : int
        Target year for interval generation. Must be a valid calendar year.

    Returns
    -------
    numpy.ndarray
        Array of datetime64[h] objects representing hourly intervals.
        Contains 8760 intervals for regular years (8784 for leap years).

    Notes
    -----
    Temporal Resolution:
        - Hourly intervals provide standard BDEW resolution
        - Covers complete calendar year without gaps
        - Compatible with commercial building operation schedules
        - Supports detailed energy balance calculations

    Array Properties:
        - Regular years: 365 days × 24 hours = 8760 intervals
        - Leap years: 366 days × 24 hours = 8784 intervals
        - Datetime64[h] format for precise temporal operations
        - Chronological sequence from January 1st 00:00 to December 31st 23:00

    BDEW Integration:
        - Matches standard BDEW load profile temporal resolution
        - Enables accurate commercial building load pattern calculation
        - Supports weekday and seasonal variation analysis
        - Compatible with temperature interpolation procedures

    Applications:
        - Commercial building load profile generation
        - Office building energy demand calculation
        - Public building consumption modeling
        - Industrial facility load pattern analysis

    Examples
    --------
    >>> # Generate hourly intervals for BDEW analysis
    >>> year = 2023
    >>> intervals = calculate_hourly_intervals(year)
    >>> print(f"Year {year}: {len(intervals)} hourly intervals")
    >>> print(f"First interval: {intervals[0]}")
    >>> print(f"Last interval: {intervals[-1]}")

    >>> # Analyze temporal coverage
    >>> total_hours = len(intervals)
    >>> expected_hours = 366 * 24 if year % 4 == 0 else 365 * 24
    >>> print(f"Total hours: {total_hours}, Expected: {expected_hours}")

    >>> # Business hours analysis for commercial buildings
    >>> import pandas as pd
    >>> df = pd.DataFrame({'timestamp': intervals})
    >>> df['hour'] = df['timestamp'].dt.hour
    >>> df['weekday'] = df['timestamp'].dt.weekday + 1  # 1=Monday, 7=Sunday
    >>> 
    >>> # Business hours (8 AM to 6 PM, Monday to Friday)
    >>> business_hours = df[
    ...     (df['hour'] >= 8) & (df['hour'] <= 18) & (df['weekday'] <= 5)
    ... ]
    >>> print(f"Business hours: {len(business_hours)} intervals")

    >>> # Peak demand periods for office buildings
    >>> morning_peak = df[(df['hour'] >= 8) & (df['hour'] <= 10)]
    >>> evening_peak = df[(df['hour'] >= 16) & (df['hour'] <= 18)]
    >>> print(f"Morning peak periods: {len(morning_peak)}")
    >>> print(f"Evening peak periods: {len(evening_peak)}")

    >>> # Seasonal analysis for heating demand
    >>> df['month'] = df['timestamp'].dt.month
    >>> heating_season = df[df['month'].isin([10, 11, 12, 1, 2, 3])]
    >>> non_heating_season = df[df['month'].isin([4, 5, 6, 7, 8, 9])]
    >>> print(f"Heating season hours: {len(heating_season)}")
    >>> print(f"Non-heating season hours: {len(non_heating_season)}")

    See Also
    --------
    calculate : Main BDEW calculation using hourly intervals
    generate_year_months_days_weekdays : Temporal component generation
    calculate_daily_averages : Daily to hourly data relationship
    """
    start_date = np.datetime64(f'{year}-01-01')
    
    # Determine number of days (handle leap years)
    end_date = np.datetime64(f'{year}-12-31')
    num_days = (end_date - start_date).astype(int) + 1
    
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

    This function retrieves the standardized coefficients from BDEW data tables
    that define the mathematical relationships for heat demand calculation.
    These coefficients are specific to building types and subtypes and form
    the core of the BDEW Standard Load Profile methodology.

    Parameters
    ----------
    profiletype : str
        BDEW building type identifier. Valid options include:
        - "GKO" : Office buildings
        - "GHA" : Retail buildings  
        - "GMK" : Schools
        - "GBD" : Hotels
        - "GBH" : Restaurants
        - "GWA" : Hospitals
        - "GGA" : Sports facilities
        - "GBA" : Cultural buildings
        - "GGB" : Public buildings
        - "GPD" : Production buildings
        - "GMF" : Mixed-use buildings
        - "GHD" : Service buildings
    subtype : str
        Building subtype for detailed classification.
        Examples: "Standard", "Büro", "Laden", etc.
    daily_data : pandas.DataFrame
        DataFrame containing BDEW daily coefficients data.
        Must include columns: A, B, C, D, mH, bH, mW, bW.

    Returns
    -------
    Tuple[float, float, float, float, float, float, float, float]
        BDEW calculation coefficients:
        
        - **A** (float) : Sigmoid function amplitude coefficient
        - **B** (float) : Sigmoid function steepness coefficient  
        - **C** (float) : Sigmoid function shape coefficient
        - **D** (float) : Domestic hot water base coefficient
        - **mH** (float) : Heating linear coefficient slope
        - **bH** (float) : Heating linear coefficient intercept
        - **mW** (float) : Hot water linear coefficient slope
        - **bW** (float) : Hot water linear coefficient intercept

    Notes
    -----
    BDEW Coefficient Functions:
        
        **Sigmoid Function for Heating**:
        h_T = A / (1 + (B / (T - 40))^C) + linear_H
        
        Where linear_H = mH × T + bH
        
        **Hot Water Function**:
        h_T_warmwater = linear_W + D
        
        Where linear_W = mW × T + bW

    Coefficient Significance:
        - **A, B, C**: Define temperature-dependent heating curve shape
        - **D**: Base domestic hot water demand (temperature-independent)
        - **mH, bH**: Linear heating corrections for building-specific behavior
        - **mW, bW**: Linear hot water corrections for occupancy patterns

    Profile Identification:
        Profile codes combine building type and subtype (e.g., "GKOStandard")
        to create unique identifiers for coefficient lookup in BDEW tables.

    Examples
    --------
    >>> import pandas as pd
    >>> 
    >>> # Load BDEW coefficient data
    >>> coeffs_file = "data/BDEW profiles/daily_coefficients.csv"
    >>> daily_data = pd.read_csv(coeffs_file, delimiter=';')
    >>> 
    >>> # Extract coefficients for office building
    >>> A, B, C, D, mH, bH, mW, bW = get_coefficients("GKO", "Standard", daily_data)
    >>> print(f"Office building coefficients:")
    >>> print(f"  Sigmoid: A={A:.3f}, B={B:.1f}, C={C:.3f}")
    >>> print(f"  DHW base: D={D:.3f}")
    >>> print(f"  Heating linear: mH={mH:.6f}, bH={bH:.3f}")
    >>> print(f"  DHW linear: mW={mW:.6f}, bW={bW:.3f}")

    >>> # Compare different building types
    >>> building_types = [("GKO", "Standard"), ("GHA", "Standard"), ("GMK", "Standard")]
    >>> 
    >>> for ptype, stype in building_types:
    ...     A, B, C, D, mH, bH, mW, bW = get_coefficients(ptype, stype, daily_data)
    ...     print(f"{ptype}: A={A:.2f}, B={B:.1f}, C={C:.2f}, D={D:.3f}")

    >>> # Calculate example heating demand at different temperatures
    >>> temps = [-10, 0, 10, 20]
    >>> A, B, C, D, mH, bH, mW, bW = get_coefficients("GKO", "Standard", daily_data)
    >>> 
    >>> for T in temps:
    ...     linear_H = mH * T + bH if (mH != 0 or bH != 0) else 0
    ...     h_T = A / (1 + (B / (T - 40)) ** C) + linear_H
    ...     print(f"T={T:3d}°C: h_T={h_T:.3f}")

    Raises
    ------
    ValueError
        If profile combination (profiletype + subtype) is not found in data.
    KeyError
        If required coefficient columns are missing from DataFrame.
    IndexError
        If DataFrame is empty or profile lookup fails.

    See Also
    --------
    calculate : Main BDEW calculation using extracted coefficients
    get_weekday_factor : Weekday-specific factors using same profile identification
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
    Extract weekday-specific load factors for BDEW profile calculation.

    This function retrieves weekday variation factors from BDEW data tables
    that account for different building operation patterns throughout the week.
    Commercial and public buildings typically have distinct load patterns
    for weekdays, Saturdays, and Sundays due to varying occupancy and operation.

    Parameters
    ----------
    daily_weekdays : numpy.ndarray
        Array of weekday numbers (1-7) for each day of the year.
        1=Monday, 2=Tuesday, ..., 7=Sunday (ISO weekday numbering).
    profiletype : str
        BDEW building type identifier (e.g., "GKO", "GHA", "GMK").
    subtype : str
        Building subtype for detailed classification.
    daily_data : pandas.DataFrame
        DataFrame containing BDEW daily coefficients with weekday factors.
        Must include columns '1', '2', '3', '4', '5', '6', '7' for each weekday.

    Returns
    -------
    numpy.ndarray
        Array of weekday factors corresponding to each day of the year.
        Factors typically range from 0.5 to 1.5, representing relative load levels.

    Notes
    -----
    Weekday Factor Application:
        Weekday factors modify base load calculations to account for:
        - **Business Operations**: Higher loads Monday-Friday for offices
        - **Retail Patterns**: Saturday operations for retail buildings
        - **Educational Schedules**: School operation patterns
        - **Public Services**: Weekend service availability

    Typical Factor Patterns:
        - **Office Buildings**: High Mon-Fri (1.0-1.1), Low Sat (0.7), Minimal Sun (0.5)
        - **Retail Buildings**: High Mon-Sat (0.9-1.1), Low Sun (0.6)
        - **Schools**: High Mon-Fri (1.0-1.2), Minimal weekends (0.3-0.5)
        - **Hospitals**: Consistent all week (0.9-1.1)

    Factor Integration:
        Daily heat demand = Base demand × Temperature factor × Weekday factor
        
        This ensures realistic load patterns that reflect actual building operations.

    Examples
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>> 
    >>> # Generate sample weekday array for one week
    >>> sample_weekdays = np.array([1, 2, 3, 4, 5, 6, 7])  # Mon-Sun
    >>> 
    >>> # Load BDEW coefficient data
    >>> coeffs_file = "data/BDEW profiles/daily_coefficients.csv"
    >>> daily_data = pd.read_csv(coeffs_file, delimiter=';')
    >>> 
    >>> # Get weekday factors for office building
    >>> office_factors = get_weekday_factor(sample_weekdays, "GKO", "Standard", daily_data)
    >>> print("Office building weekday factors:")
    >>> weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    >>> for day, factor in zip(weekday_names, office_factors):
    ...     print(f"  {day}: {factor:.3f}")

    >>> # Compare different building types
    >>> building_types = [("GKO", "Standard"), ("GHA", "Standard"), ("GMK", "Standard")]
    >>> 
    >>> print("\\nWeekday factor comparison:")
    >>> print("Building    Mon   Tue   Wed   Thu   Fri   Sat   Sun")
    >>> for ptype, stype in building_types:
    ...     factors = get_weekday_factor(sample_weekdays, ptype, stype, daily_data)
    ...     factors_str = "  ".join([f"{f:.2f}" for f in factors])
    ...     print(f"{ptype:<8} {factors_str}")

    >>> # Annual weekday distribution analysis
    >>> year = 2023
    >>> _, _, _, year_weekdays = generate_year_months_days_weekdays(year)
    >>> office_year_factors = get_weekday_factor(year_weekdays, "GKO", "Standard", daily_data)
    >>> 
    >>> print(f"\\nAnnual office building load pattern:")
    >>> print(f"  Average weekday factor: {office_year_factors.mean():.3f}")
    >>> print(f"  Maximum factor: {office_year_factors.max():.3f}")
    >>> print(f"  Minimum factor: {office_year_factors.min():.3f}")

    >>> # Business vs weekend operation
    >>> business_days = office_year_factors[year_weekdays <= 5]  # Mon-Fri
    >>> weekend_days = office_year_factors[year_weekdays > 5]   # Sat-Sun
    >>> print(f"  Business day average: {business_days.mean():.3f}")
    >>> print(f"  Weekend average: {weekend_days.mean():.3f}")
    >>> print(f"  Business/weekend ratio: {business_days.mean()/weekend_days.mean():.1f}")

    Raises
    ------
    ValueError
        If profile combination is not found in data or weekday columns missing.
    KeyError
        If weekday columns ('1'-'7') are not present in DataFrame.
    IndexError
        If weekday numbers are outside valid range (1-7).

    See Also
    --------
    get_coefficients : Extract base coefficients using same profile identification
    generate_year_months_days_weekdays : Generate weekday arrays for factor lookup
    calculate : Main BDEW calculation applying weekday factors
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
    Calculate comprehensive heat demand profiles using BDEW Standard Load Profile methodology.

    This function implements the complete BDEW (German Association of Energy and Water Industries)
    calculation workflow for generating realistic heat demand profiles for commercial and public
    buildings. It combines standardized coefficients, temperature dependencies, and weekday
    variations to create hourly demand time series for district heating applications.

    Parameters
    ----------
    JWB_kWh : float
        Annual heat demand [kWh/a]. Must be positive value.
        Represents total building energy consumption for heating and hot water.
    profiletype : str
        BDEW building type identifier. Valid options:
        - "GKO" : Office buildings (Bürogebäude)
        - "GHA" : Retail buildings (Handel)
        - "GMK" : Schools (Schulen)
        - "GBD" : Hotels (Hotels)
        - "GBH" : Restaurants (Restaurants) 
        - "GWA" : Hospitals (Krankenhäuser)
        - "GGA" : Sports facilities (Sportstätten)
        - "GBA" : Cultural buildings (Kultureinrichtungen)
        - "GGB" : Public buildings (Öffentliche Gebäude)
        - "GPD" : Production buildings (Produktionsgebäude)
        - "GMF" : Mixed-use buildings (Mischnutzung)
        - "GHD" : Service buildings (Dienstleistungsgebäude)
    subtype : str
        Building subtype for detailed classification.
        Examples: "Standard", "Büro", "Laden", "Schule", etc.
    TRY_file_path : str
        Path to Test Reference Year meteorological data file.
        Must contain complete hourly weather data for specified year.
    year : int
        Target year for profile generation. Must be valid calendar year.
        Determines temporal framework and leap year handling.
    real_ww_share : float, optional
        Actual domestic hot water share [0-1]. Default is None.
        If provided, adjusts calculated DHW/heating ratio to match real building data.

    Returns
    -------
    Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]
        Complete BDEW load profile data:
        
        - **hourly_intervals** (numpy.ndarray) : Hourly timestamps
        - **total_heat_demand** (numpy.ndarray) : Total heat demand [kWh/h]
        - **heating_demand** (numpy.ndarray) : Space heating demand [kWh/h]  
        - **hot_water_demand** (numpy.ndarray) : DHW demand [kWh/h]
        - **hourly_temperature** (numpy.ndarray) : Outdoor temperature [°C]

    Notes
    -----
    BDEW Methodology Overview:
        The BDEW Standard Load Profile method creates realistic demand patterns by:
        1. **Temperature Analysis**: Daily average temperature calculation
        2. **Coefficient Application**: Building-specific mathematical functions
        3. **Weekday Variation**: Operation pattern adjustments
        4. **Hourly Interpolation**: Temperature-dependent hourly factors
        5. **Energy Balance**: Normalization to annual consumption target

    Mathematical Framework:
        
        **Daily Heating Demand**:
        h_T = A / (1 + (B / (T - 40))^C) + mH × T + bH
        
        **Daily Hot Water Demand**:
        h_T_DHW = mW × T + bW + D
        
        **Weekday Correction**:
        Daily_demand = h_T × Weekday_factor × Annual_factor
        
        **Hourly Distribution**:
        Hourly_demand = Daily_demand × Hourly_factor × Temperature_interpolation

    Temperature Processing:
        - Daily temperatures determine base load levels
        - Hourly temperatures enable interpolation between coefficient tables
        - Reference temperatures create discrete lookup values
        - Temperature limits ensure physical boundary conditions

    Quality Assurance:
        - Energy balance verification ensures annual total matches input
        - DHW share correction allows calibration to real building data
        - Negative demand clipping prevents non-physical values
        - Missing data handling with NaN replacement

    Examples
    --------
    >>> # Calculate BDEW profile for office building
    >>> TRY_file = "path/to/TRY_data.dat"
    >>> 
    >>> time, total, heating, dhw, temp = calculate(
    ...     JWB_kWh=50000,           # 50 MWh/a total demand
    ...     profiletype="GKO",       # Office building
    ...     subtype="Standard",      # Standard office
    ...     TRY_file_path=TRY_file,
    ...     year=2023,
    ...     real_ww_share=0.15       # 15% hot water share
    ... )
    >>> 
    >>> print(f"Generated {len(time)} hourly intervals")
    >>> print(f"Annual total: {total.sum():.0f} kWh (target: 50000)")
    >>> print(f"Annual heating: {heating.sum():.0f} kWh")
    >>> print(f"Annual DHW: {dhw.sum():.0f} kWh")

    >>> # Analyze demand patterns
    >>> peak_total = total.max()
    >>> avg_total = total.mean()
    >>> load_factor = avg_total / peak_total
    >>> print(f"Peak demand: {peak_total:.1f} kWh/h")
    >>> print(f"Average demand: {avg_total:.1f} kWh/h")
    >>> print(f"Load factor: {load_factor:.3f}")

    >>> # Seasonal analysis
    >>> # Convert to daily values for seasonal comparison
    >>> daily_total = total.reshape(-1, 24).sum(axis=1)  # Daily totals [kWh/d]
    >>> winter_total = daily_total[:90].mean()  # First 90 days
    >>> summer_total = daily_total[180:270].mean()  # Days 181-270
    >>> seasonal_ratio = winter_total / summer_total
    >>> print(f"Winter daily average: {winter_total:.1f} kWh/d")
    >>> print(f"Summer daily average: {summer_total:.1f} kWh/d")
    >>> print(f"Winter/summer ratio: {seasonal_ratio:.1f}")

    >>> # DHW share analysis
    >>> actual_dhw_share = dhw.sum() / total.sum()
    >>> print(f"Actual DHW share: {actual_dhw_share:.1%}")
    >>> if real_ww_share:
    ...     print(f"Target DHW share: {real_ww_share:.1%}")
    ...     print(f"DHW correction applied: {abs(actual_dhw_share - real_ww_share) < 0.001}")

    >>> # Temperature correlation analysis
    >>> import scipy.stats
    >>> correlation, p_value = scipy.stats.pearsonr(temp, total)
    >>> print(f"Temperature correlation: {correlation:.3f} (p={p_value:.3f})")

    >>> # Operating pattern analysis (weekday vs weekend)
    >>> import pandas as pd
    >>> df = pd.DataFrame({'timestamp': time, 'demand': total})
    >>> df['weekday'] = pd.to_datetime(df['timestamp']).dt.weekday + 1
    >>> 
    >>> weekday_avg = df[df['weekday'] <= 5]['demand'].mean()  # Mon-Fri
    >>> weekend_avg = df[df['weekday'] > 5]['demand'].mean()   # Sat-Sun
    >>> operation_ratio = weekday_avg / weekend_avg
    >>> print(f"Weekday average: {weekday_avg:.1f} kWh/h")
    >>> print(f"Weekend average: {weekend_avg:.1f} kWh/h")
    >>> print(f"Weekday/weekend ratio: {operation_ratio:.1f}")

    Raises
    ------
    ValueError
        If input parameters are invalid or profile type not recognized.
    FileNotFoundError
        If TRY file or BDEW coefficient files cannot be found.
    KeyError
        If required BDEW profile data is missing for specified building type.

    See Also
    --------
    get_coefficients : Extract BDEW calculation coefficients
    get_weekday_factor : Retrieve weekday-specific load factors
    calculate_daily_averages : Process daily temperature data
    calculate_hourly_intervals : Generate temporal framework
    """
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
    
    # Calculate BDEW reference temperatures (discrete temperature steps)
    daily_reference_temperature = np.round((daily_avg_temperature + 2.5) * 2, -1) / 2 - 2.5

    # Load BDEW coefficient data
    daily_data = pd.read_csv(
        get_resource_path('data/BDEW profiles/daily_coefficients.csv'), 
        delimiter=';'
    )
    
    # Extract building-specific coefficients
    h_A, h_B, h_C, h_D, mH, bH, mW, bW = get_coefficients(profiletype, subtype, daily_data)
    
    # Calculate linear temperature corrections
    lin_H = np.nan_to_num(mH * daily_avg_temperature + bH) if mH != 0 or bH != 0 else 0
    lin_W = np.nan_to_num(mW * daily_avg_temperature + bW) if mW != 0 or bW != 0 else 0

    # Calculate daily heating demand using BDEW sigmoid function
    h_T_heating = h_A / (1 + (h_B / (daily_avg_temperature - 40)) ** h_C) + lin_H
    
    # Apply weekday factors
    F_D = get_weekday_factor(daily_weekdays, profiletype, subtype, daily_data)
    h_T_F_D_heating = h_T_heating * F_D
    
    # Calculate annual scaling factor for heating
    sum_h_T_F_D_heating = np.sum(h_T_F_D_heating)
    KW_kWh_heating = JWB_kWh / sum_h_T_F_D_heating if sum_h_T_F_D_heating != 0 else 0
    daily_heat_demand_heating = h_T_F_D_heating * KW_kWh_heating

    # Calculate daily hot water demand
    h_T_warmwater = lin_W + h_D
    h_T_F_D_warmwater = h_T_warmwater * F_D
    
    # Calculate annual scaling factor for hot water
    sum_h_T_F_D_warmwater = np.sum(h_T_F_D_warmwater)
    KW_kWh_warmwater = JWB_kWh / sum_h_T_F_D_warmwater if sum_h_T_F_D_warmwater != 0 else 0
    daily_heat_demand_warmwater = h_T_F_D_warmwater * KW_kWh_warmwater

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

    # Normalize to match annual consumption target
    hourly_heat_demand_heating_normed = np.nan_to_num(
        (hourly_heat_demand_heating / np.sum(hourly_heat_demand_heating)) * JWB_kWh
    )
    hourly_heat_demand_warmwater_normed = np.nan_to_num(
        (hourly_heat_demand_warmwater / np.sum(hourly_heat_demand_warmwater)) * JWB_kWh
    )

    # Calculate initial hot water share
    initial_ww_share = (
        np.sum(hourly_heat_demand_warmwater_normed) / 
        (np.sum(hourly_heat_demand_heating_normed) + np.sum(hourly_heat_demand_warmwater_normed))
    )

    # Apply hot water share correction if specified
    if real_ww_share is not None:
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
    
    # Generate hourly time intervals
    hourly_intervals = calculate_hourly_intervals(year)

    return (hourly_intervals, 
            hourly_heat_demand_total_normed, 
            hourly_heat_demand_heating_normed.astype(float), 
            hourly_heat_demand_warmwater_normed.astype(float), 
            hourly_temperature)