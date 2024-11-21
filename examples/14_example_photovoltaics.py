"""
Filename: 14_example_photovoltaics.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-21
Description: 

"""

from districtheatingsim.heat_generators.photovoltaics import Calculate_PV

if __name__ == '__main__':
    # Define the input parameters for the photovoltaic calculation.
    TRY_data = "examples\\data\\TRY\\TRY_511676144222\\TRY2015_511676144222_Jahr.dat"
    Gross_area = 100 # m²
    Longitude = 11.581981
    STD_Longitude = 15
    Latitude = 48.135125
    Albedo = 0.2
    East_West_collector_azimuth_angle = 90
    Collector_tilt_angle = 30

    # Calculate the photovoltaic power output.
    Annual_PV_yield, Max_power, Power_output = Calculate_PV(TRY_data, Gross_area, Longitude, STD_Longitude, Latitude, Albedo,
                                                            East_West_collector_azimuth_angle, Collector_tilt_angle)

    print(f'Annual PV yield: {Annual_PV_yield} kWh')
    print(f'Maximum power: {Max_power} kW')
    print(f'Power output array: {Power_output} W')