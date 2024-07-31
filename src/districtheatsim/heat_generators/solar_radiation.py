"""
Filename: solar_radiation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Calculates the solar irradiation input based on Test Reference Year data.

Additional Information: Yield calculation program for solar thermal energy in heating networks (calculation basis: ScenoCalc District Heating 2.0) https://www.scfw.de/)
"""

# Import Bibliotheken
import numpy as np

# Konstante für Grad-Radian-Konversion
DEG_TO_RAD = np.pi / 180

def deg_to_rad(deg):
    """
    Converts degrees to radians.

    Args:
        deg (float or np.ndarray): Angle in degrees.

    Returns:
        float or np.ndarray: Angle in radians.
    """
    return deg * DEG_TO_RAD

def Berechnung_Solarstrahlung(Globalstrahlung_L, D_L, Tag_des_Jahres_L, time_steps, Longitude, STD_Longitude, Latitude, Albedo, IAM_W, IAM_N,
                              EWCaa, CTA):    
    """
    Calculates solar radiation based on Test Reference Year data.

    Args:
        Globalstrahlung_L (np.ndarray): Global radiation data.
        D_L (np.ndarray): Direct radiation data.
        Tag_des_Jahres_L (np.ndarray): Day of the year data.
        time_steps (np.ndarray): Array of time steps.
        Longitude (float): Longitude of the location.
        STD_Longitude (float): Standard longitude for the time zone.
        Latitude (float): Latitude of the location.
        Albedo (float): Albedo value.
        IAM_W (dict): Incidence Angle Modifier for EW orientation.
        IAM_N (dict): Incidence Angle Modifier for NS orientation.
        EWCaa (float): East-West collector azimuth angle.
        CTA (float): Collector tilt angle.

    Returns:
        tuple: Contains arrays for total radiation on the inclined surface, beam radiation, diffuse radiation, and modified beam radiation.
    """
    Stunde_L = (time_steps - time_steps.astype('datetime64[D]')).astype('timedelta64[m]').astype(float) / 60

    # Berechnet den Tag des Jahres als Winkel
    B = (Tag_des_Jahres_L - 1) * 360 / 365  # °

    # Berechnet die Zeitkorrektur basierend auf dem Tageswinkel
    E = 229.2 * (0.000075 + 0.001868 * np.cos(deg_to_rad(B)) - 0.032077 * np.sin(deg_to_rad(B)) -
                 0.014615 * np.cos(2 * deg_to_rad(B)) - 0.04089 * np.sin(2 * deg_to_rad(B)))

    # Bestimmt die Sonnenzeit unter Berücksichtigung der Zeitkorrektur und der geografischen Länge
    Solar_time = ((Stunde_L - 0.5) * 3600 + E * 60 + 4 * (STD_Longitude - Longitude) * 60) / 3600

    # Berechnet die Sonnendeklination
    Solar_declination = 23.45 * np.sin(deg_to_rad(360 * (284 + Tag_des_Jahres_L) / 365))

    # Berechnet den Stundenwinkel der Sonne
    Hour_angle = -180 + Solar_time * 180 / 12

    # Berechnet den Sonnenzenitwinkel
    SZA = np.arccos(np.cos(deg_to_rad(Latitude)) * np.cos(deg_to_rad(Hour_angle)) *
                    np.cos(deg_to_rad(Solar_declination)) + np.sin(deg_to_rad(Latitude)) *
                    np.sin(deg_to_rad(Solar_declination))) / DEG_TO_RAD

    # Bestimmt den Azimutwinkel der Sonne
    EWs_az_angle = np.sign(Hour_angle) * np.arccos((np.cos(deg_to_rad(SZA)) * np.sin(deg_to_rad(Latitude)) -
                                                    np.sin(deg_to_rad(Solar_declination))) /
                                                   (np.sin(deg_to_rad(SZA)) * np.cos(deg_to_rad(Latitude)))) / \
                   DEG_TO_RAD

    # Berechnet den Einfallswinkel der Sonnenstrahlung auf den Kollektor
    IaC = np.arccos(np.cos(deg_to_rad(SZA)) * np.cos(deg_to_rad(CTA)) + np.sin(deg_to_rad(SZA)) *
                    np.sin(deg_to_rad(CTA)) * np.cos(deg_to_rad(EWs_az_angle - EWCaa))) / DEG_TO_RAD

    # Bedingung, unter welcher der Kollektor Sonnenstrahlung empfängt
    condition = (SZA < 90) & (IaC < 90)

    # Funktionen zur Berechnung der Einfallswinkel auf den Kollektor in EW und NS-Richtung
    f_EW = np.arctan(np.sin(SZA * DEG_TO_RAD) * np.sin((EWs_az_angle - EWCaa) * DEG_TO_RAD) /
                     np.cos(IaC * DEG_TO_RAD)) / DEG_TO_RAD

    f_NS = -(180 / np.pi * np.arctan(np.tan(SZA * DEG_TO_RAD) * np.cos((EWs_az_angle - EWCaa) * DEG_TO_RAD)) - CTA)

    Incidence_angle_EW = np.where(condition, f_EW, 89.999)
    Incidence_angle_NS = np.where(condition, f_NS, 89.999)

    def IAM(Incidence_angle, iam_data):
        sverweis_1 = np.abs(Incidence_angle) - np.abs(Incidence_angle) % 10
        sverweis_2 = np.vectorize(iam_data.get)(sverweis_1)
        sverweis_3 = (np.abs(Incidence_angle) + 10) - (np.abs(Incidence_angle) + 10) % 10
        sverweis_4 = np.vectorize(iam_data.get)(sverweis_3)

        ergebnis = sverweis_2 + (np.abs(Incidence_angle) - sverweis_1) / (sverweis_3 - sverweis_1) * (sverweis_4 -
                                                                                                      sverweis_2)
        return ergebnis

    # Für IAM_EW
    IAM_EW = IAM(Incidence_angle_EW, IAM_W)
    # Für IAM_NS
    IAM_NS = IAM(Incidence_angle_NS, IAM_N)

    # Berechnet das Verhältnis der Strahlungsintensität auf dem geneigten Kollektor zur horizontalen Oberfläche
    function_Rb = np.cos(deg_to_rad(IaC)) / np.cos(deg_to_rad(SZA))
    Rb = np.where(condition, function_Rb, 0)

    # Berechnet den Direktstrahlungsanteil auf horizontaler Oberfläche
    Gbhoris = D_L * np.cos(deg_to_rad(SZA))

    # Berechnung der diffusen Strahlung auf einer horizontalen Oberfläche
    Gdhoris = Globalstrahlung_L - Gbhoris

    # Berechnung des atmosphärischen Diffusanteils Ai basierend auf der horizontalen
    # Strahlungsintensität Gbhoris und weiteren Parametern
    Ai = Gbhoris / (1367 * (1 + 0.033 * np.cos(deg_to_rad(360 * Tag_des_Jahres_L / 365))) *
                    np.cos(deg_to_rad(SZA)))

    # Gesamtstrahlung GT_H_Gk auf der schrägen Oberfläche, einschließlich des direkten und
    # diffusen Beitrags sowie des durch Albedo reflektierten Beitrags
    GT_H_Gk = (Gbhoris * Rb +  # Direkte Strahlung nach Anpassung durch den Winkel
               Gdhoris * Ai * Rb +  # Diffuse Strahlung, die direkt durch den Winkel beeinflusst wird
               Gdhoris * (1 - Ai) * 0.5 * (1 + np.cos(deg_to_rad(
                CTA))) +  # Diffuse Strahlung, die indirekt durch den Winkel beeinflusst wird
               Globalstrahlung_L * Albedo * 0.5 * (
                           1 - np.cos(deg_to_rad(CTA))))  # Durch Albedo reflektierte Strahlung

    # Direkte Strahlung auf der schrägen Oberfläche
    GbT = Gbhoris * Rb

    # Diffuse Strahlung auf der schrägen Oberfläche
    GdT_H_Dk = GT_H_Gk - GbT

    # IAM_EW und IAM_NS sind wahrscheinlich Faktoren, die den Einfluss des Einstrahlungswinkels
    # auf die Strahlung beschreiben. K_beam ist das Produkt dieser beiden Faktoren.
    K_beam = IAM_EW * IAM_NS

    return GT_H_Gk, K_beam, GbT, GdT_H_Dk