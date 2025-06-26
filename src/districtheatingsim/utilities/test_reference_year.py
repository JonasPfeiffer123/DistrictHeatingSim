"""
Filename: test_reference_year.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Import function for the Test Reference Year (TRY) files.

This module provides functionality to import and parse German Test Reference Year (TRY) 
weather data files. TRY files contain standardized meteorological data used for building 
energy simulations and district heating system calculations.
"""

import pandas as pd

def import_TRY(filename):
    """
    Read and parse TRY (Test Reference Year) weather data file.

    This function imports German Test Reference Year weather data files and extracts
    relevant meteorological parameters for district heating simulations. The TRY format
    is a fixed-width format with specific column definitions.

    Parameters
    ----------
    filename : str
        Path to the TRY file to be imported. Should be a valid TRY format file
        with fixed-width columns as specified by the German weather service.

    Returns
    -------
    tuple of numpy.ndarray
        A tuple containing the following meteorological data arrays:
        
        - **temperature** (numpy.ndarray) : Air temperature values in degrees Celsius [°C]
          measured at 2m height above ground level
        - **windspeed** (numpy.ndarray) : Wind speed values in meters per second [m/s]
          measured at 10m height above ground level  
        - **direct_radiation** (numpy.ndarray) : Direct solar radiation on horizontal 
          surface [W/m²], downward directed (positive values)
        - **global_radiation** (numpy.ndarray) : Global solar radiation [W/m²], 
          calculated as sum of direct and diffuse radiation
        - **cloud_cover** (numpy.ndarray) : Cloud coverage in eighths [0-8], 
          where 0 = clear sky, 8 = completely overcast, 9 = not observable

    Raises
    ------
    FileNotFoundError
        If the specified TRY file cannot be found.
    ValueError
        If the file format is invalid or cannot be parsed.
    pd.errors.EmptyDataError
        If the file is empty or contains no valid data.

    Notes
    -----
    - The function automatically skips the first 34 header rows of the TRY file
    - TRY files use a fixed-width format with predefined column widths
    - The function calculates global radiation as the sum of direct and diffuse radiation
    - All returned arrays have the same length (typically 8760 hours for a full year)
    - Missing or invalid values in the original file are preserved as NaN

    Examples
    --------
    >>> # Import TRY data for Berlin
    >>> temp, wind, direct_rad, global_rad, clouds = import_TRY('TRY_Berlin.dat')
    >>> print(f"Temperature range: {temp.min():.1f} to {temp.max():.1f} °C")
    Temperature range: -12.3 to 34.7 °C
    
    >>> # Check data completeness
    >>> print(f"Data points: {len(temp)} hours")
    Data points: 8760 hours
    
    >>> # Calculate annual solar radiation sum
    >>> annual_radiation = np.sum(global_rad) / 1000  # Convert to kWh/m²
    >>> print(f"Annual global radiation: {annual_radiation:.0f} kWh/m²")
    Annual global radiation: 1089 kWh/m²

    See Also
    --------
    pandas.read_fwf : Read fixed-width formatted lines into DataFrame
    numpy.ndarray : The NumPy ndarray class used for return values
    
    References
    ----------
    .. [1] Deutscher Wetterdienst (DWD): Test Reference Years (TRY) for Germany
    .. [2] DIN 4710: Statistics of meteorological data for calculating the energy 
           demand of air conditioning systems in Germany
    """
    # Define column widths for fixed-width format
    col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]
    
    # Define column names according to TRY specification
    col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]

    # Read the TRY file (skip first 34 header rows)
    data = pd.read_fwf(filename, widths=col_widths, names=col_names, skiprows=34)

    # Extract relevant meteorological parameters as numpy arrays
    temperature = data['t'].values          # Air temperature [°C]
    windspeed = data['WG'].values          # Wind speed [m/s]  
    direct_radiation = data['B'].values     # Direct solar radiation [W/m²]
    diffuse_radiation = data['D'].values    # Diffuse solar radiation [W/m²]
    global_radiation = direct_radiation + diffuse_radiation  # Global radiation [W/m²]
    cloud_cover = data['N'].values         # Cloud coverage [eighths]

    return temperature, windspeed, direct_radiation, global_radiation, cloud_cover


# TRY File Format Specification
# =============================
"""
Complete parameter list and data format specification for German TRY files:

+-----+--------------------------------------------------+----------+---------------------------+
| Col | Parameter Description                            | Unit     | Valid Range               |
+=====+==================================================+==========+===========================+
| RW  | Rechtswert (Easting coordinate)                  | [m]      | {3670500..4389500}       |
+-----+--------------------------------------------------+----------+---------------------------+
| HW  | Hochwert (Northing coordinate)                   | [m]      | {2242500..3179500}       |
+-----+--------------------------------------------------+----------+---------------------------+
| MM  | Monat (Month)                                    | [-]      | {1..12}                  |
+-----+--------------------------------------------------+----------+---------------------------+
| DD  | Tag (Day)                                        | [-]      | {1..28,30,31}            |
+-----+--------------------------------------------------+----------+---------------------------+
| HH  | Stunde (Hour, MEZ/CET)                           | [-]      | {1..24}                  |
+-----+--------------------------------------------------+----------+---------------------------+
| t   | Lufttemperatur in 2m Höhe über Grund            | [°C]     | Continuous               |
+-----+--------------------------------------------------+----------+---------------------------+
| p   | Luftdruck in Standorthöhe                        | [hPa]    | Continuous               |
+-----+--------------------------------------------------+----------+---------------------------+
| WR  | Windrichtung in 10m Höhe über Grund             | [°]      | {0..360; 999=variable}   |
+-----+--------------------------------------------------+----------+---------------------------+
| WG  | Windgeschwindigkeit in 10m Höhe über Grund      | [m/s]    | Continuous               |
+-----+--------------------------------------------------+----------+---------------------------+
| N   | Bedeckungsgrad                                   | [/8]     | {0..8; 9=not observable}|
+-----+--------------------------------------------------+----------+---------------------------+
| x   | Wasserdampfgehalt, Mischungsverhältnis           | [g/kg]   | Continuous               |
+-----+--------------------------------------------------+----------+---------------------------+
| RF  | Relative Feuchte in 2m Höhe über Grund          | [%]      | {1..100}                 |
+-----+--------------------------------------------------+----------+---------------------------+
| B   | Direkte Sonnenbestrahlungsstärke (horiz. Ebene) | [W/m²]   | ≥0 (downward positive)   |
+-----+--------------------------------------------------+----------+---------------------------+
| D   | Diffuse Sonnenbestrahlungsstärke (horiz. Ebene) | [W/m²]   | ≥0 (downward positive)   |
+-----+--------------------------------------------------+----------+---------------------------+
| A   | Bestrahlungsstärke d. atm. Wärmestrahlung       | [W/m²]   | ≥0 (downward positive)   |
+-----+--------------------------------------------------+----------+---------------------------+
| E   | Bestrahlungsstärke d. terr. Wärmestrahlung      | [W/m²]   | ≤0 (upward negative)     |
+-----+--------------------------------------------------+----------+---------------------------+
| IL  | Qualitätsbit bezüglich der Auswahlkriterien     | [-]      | {0,1,2,3,4}              |
+-----+--------------------------------------------------+----------+---------------------------+

Quality indicators (IL):
- 0: Measured data
- 1: Interpolated data  
- 2: Estimated data
- 3: Climatological data
- 4: Missing data

Notes:
- All radiation values are given for horizontal surfaces
- Time stamps are in Central European Time (MEZ/CET)
- Coordinate system: Gauss-Krüger with Bessel ellipsoid
- File typically contains 8760 hourly values for a complete year
"""