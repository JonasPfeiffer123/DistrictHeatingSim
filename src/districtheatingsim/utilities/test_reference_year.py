"""
Test Reference Year (TRY) import module for German weather data.

This module provides functionality to import and parse standardized meteorological
data files used for building energy simulations and district heating calculations.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import pandas as pd

def import_TRY(filename):
    """
    Read and parse TRY (Test Reference Year) weather data file.

    :param filename: Path to TRY file in fixed-width format
    :type filename: str
    :return: Tuple of (temperature, windspeed, direct_radiation, global_radiation, cloud_cover)
    :rtype: tuple of numpy.ndarray
    :raises FileNotFoundError: If TRY file cannot be found
    :raises ValueError: If file format is invalid
    
    .. note::
        - File contains 8760 hourly values for a complete year
        - Temperature in °C (at 2m height)
        - Wind speed in m/s (at 10m height)
        - Radiation values in W/m² (horizontal surface)
        - Cloud cover in eighths (0-8, where 9=not observable)
        - Global radiation is calculated as sum of direct and diffuse radiation
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
