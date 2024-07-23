"""
Filename: test_reference_year.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Import function for the Test Reference Year files.

"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd

def import_TRY(dateiname):
    """_summary_

    Args:
        dateiname (_type_): _description_

    Returns:
        _type_: _description_
    """
    # Import TRY
    # Spaltenbreiten definieren
    col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]
    # Spaltennamen definieren
    col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]

    # Die Datei lesen
    data = pd.read_fwf(dateiname, widths=col_widths, names=col_names,
                       skiprows=34)

    # Speichern der Spalten als Numpy-Arrays
    temperature = data['t'].values
    windspeed = data['WG'].values
    direktstrahlung = data['B'].values
    diffusstrahlung = data['D'].values
    globalstrahlung = direktstrahlung + diffusstrahlung

    return temperature, windspeed, direktstrahlung, globalstrahlung