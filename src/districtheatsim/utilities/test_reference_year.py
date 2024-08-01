"""
Filename: test_reference_year.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Import function for the Test Reference Year files.

"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd

def import_TRY(filename):
    """Reads the TRY file content of the given filename

    Args:
        filename (str): TRY filename

    Returns:
        tuple: A tuple containing the following elements:
            - temperature (np.ndarray): Array of temperature values.
            - windspeed (np.ndarray): Array of wind speed values.
            - direct_radiation (np.ndarray): Array of direct radiation values.
            - global_radition (np.ndarray): Array of global radiation values.
    """
    # Import TRY
    # Spaltenbreiten definieren
    col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]
    # Spaltennamen definieren
    col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]

    # Die Datei lesen
    data = pd.read_fwf(filename, widths=col_widths, names=col_names, skiprows=34)

    # Speichern der Spalten als Numpy-Arrays
    temperature = data['t'].values
    windspeed = data['WG'].values
    direct_radiation = data['B'].values
    diffuse_radiation = data['D'].values
    global_radition = direct_radiation + diffuse_radiation

    return temperature, windspeed, direct_radiation, global_radition

### Available data points of TRY files ###
"""
Reihenfolge der Parameter:
RW Rechtswert                                                    [m]       {3670500;3671500..4389500}
HW Hochwert                                                      [m]       {2242500;2243500..3179500}
MM Monat                                                                   {1..12}
DD Tag                                                                     {1..28,30,31}
HH Stunde (MEZ)                                                            {1..24}
t  Lufttemperatur in 2m Hoehe ueber Grund                        [GradC]
p  Luftdruck in Standorthoehe                                    [hPa]
WR Windrichtung in 10 m Hoehe ueber Grund                        [Grad]    {0..360;999}
WG Windgeschwindigkeit in 10 m Hoehe ueber Grund                 [m/s]
N  Bedeckungsgrad                                                [Achtel]  {0..8;9}
x  Wasserdampfgehalt, Mischungsverhaeltnis                       [g/kg]
RF Relative Feuchte in 2 m Hoehe ueber Grund                     [Prozent] {1..100}
B  Direkte Sonnenbestrahlungsstaerke (horiz. Ebene)              [W/m^2]   abwaerts gerichtet: positiv
D  Diffuse Sonnenbetrahlungsstaerke (horiz. Ebene)               [W/m^2]   abwaerts gerichtet: positiv
A  Bestrahlungsstaerke d. atm. Waermestrahlung (horiz. Ebene)    [W/m^2]   abwaerts gerichtet: positiv
E  Bestrahlungsstaerke d. terr. Waermestrahlung                  [W/m^2]   aufwaerts gerichtet: negativ
IL Qualitaetsbit bezueglich der Auswahlkriterien                           {0;1;2;3;4}
"""