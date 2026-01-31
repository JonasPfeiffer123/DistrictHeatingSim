"""
Photovoltaics Module
====================

Photovoltaic power generation modeling based on EU PVGIS methodology.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Tuple, Union, List, Optional

from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation

# Constant for degree-radian conversion
DEG_TO_RAD = np.pi / 180

def Calculate_PV(TRY_data: str, Gross_area: float, Longitude: float, STD_Longitude: float, 
                Latitude: float, Albedo: float, East_West_collector_azimuth_angle: float, 
                Collector_tilt_angle: float) -> Tuple[float, float, np.ndarray]:
    """
    Calculate photovoltaic power output based on EU PVGIS methodology.

    :param TRY_data: Path to Test Reference Year data
    :type TRY_data: str
    :param Gross_area: PV system area [m²]
    :type Gross_area: float
    :param Longitude: Geographic longitude [degrees]
    :type Longitude: float
    :param STD_Longitude: Standard longitude for time zone [degrees]
    :type STD_Longitude: float
    :param Latitude: Geographic latitude [degrees]
    :type Latitude: float
    :param Albedo: Ground reflection coefficient [-]
    :type Albedo: float
    :param East_West_collector_azimuth_angle: Azimuth angle [degrees]
    :type East_West_collector_azimuth_angle: float
    :param Collector_tilt_angle: Tilt angle from horizontal [degrees]
    :type Collector_tilt_angle: float
    :return: (yield_kWh, P_max, P_L)
    :rtype: tuple
    """
    # Import Test Reference Year meteorological data
    Ta_L, W_L, D_L, G_L, _ = import_TRY(TRY_data)

    # Define photovoltaic system constants based on EU PVGIS methodology
    eff_nom = 0.199  # Nominal PV module efficiency under STC conditions [-]
    sys_loss = 0.14  # Total system losses including inverter, cabling, soiling [-]
    U0 = 26.9        # Thermal loss coefficient constant [W/(°C·m²)]
    U1 = 6.2         # Thermal loss coefficient wind-dependent [W·s/(°C·m³)]

    # EU PVGIS efficiency model coefficients for crystalline silicon
    k1, k2, k3, k4, k5, k6 = -0.017237, -0.040465, -0.004702, 0.000149, 0.000170, 0.000005

    # Generate annual hourly time series (8760 hours)
    start_date = np.datetime64('2024-01-01T00:00')
    time_steps = start_date + np.arange(8760) * np.timedelta64(1, 'h')
    
    # Calculate day of year for solar position calculations
    Day_of_Year_L = np.array([
        datetime.fromtimestamp(
            t.astype('datetime64[s]').astype(np.int64), 
            tz=timezone.utc
        ).timetuple().tm_yday 
        for t in time_steps
    ])

    # Calculate solar irradiation on tilted PV surface
    GT_L, _, _, _ = calculate_solar_radiation(
        time_steps, G_L, D_L,
        Longitude, STD_Longitude, Latitude, Albedo,
        East_West_collector_azimuth_angle, Collector_tilt_angle
    )

    # Convert irradiation from W/m² to kW/m² for efficiency calculations
    G1 = GT_L / 1000

    # Calculate PV module temperature using thermal model
    # Accounts for ambient temperature, solar heating, and wind cooling
    Tm = Ta_L + GT_L / (U0 + U1 * W_L)
    T1m = Tm - 25  # Temperature difference from Standard Test Conditions

    # Calculate relative efficiency based on irradiation and temperature
    eff_rel = np.ones_like(G1)
    non_zero_mask = G1 != 0
    
    # Apply EU PVGIS efficiency model for non-zero irradiation periods
    eff_rel[non_zero_mask] = (
        1 + k1 * np.log(G1[non_zero_mask]) 
        + k2 * np.log(G1[non_zero_mask]) ** 2 
        + k3 * T1m[non_zero_mask] 
        + k4 * T1m[non_zero_mask] * np.log(G1[non_zero_mask]) 
        + k5 * Tm[non_zero_mask] * np.log(G1[non_zero_mask]) ** 2 
        + k6 * Tm[non_zero_mask] ** 2
    )
    
    # Set efficiency to zero for no irradiation periods
    eff_rel[~non_zero_mask] = 0
    eff_rel = np.nan_to_num(eff_rel, nan=0)

    # Calculate instantaneous PV power output [kW]
    # P = Irradiation × Area × Nominal_Efficiency × Relative_Efficiency × (1 - System_Losses)
    P_L = G1 * Gross_area * eff_nom * eff_rel * (1 - sys_loss)

    # Calculate performance metrics
    P_max = np.max(P_L)  # Maximum instantaneous power [kW]
    E = np.sum(P_L)      # Total annual energy [kWh]

    # Round results for practical use
    yield_kWh = round(E, 2)
    P_max = round(P_max, 2)

    return yield_kWh, P_max, P_L

def azimuth_angle(direction: str) -> Optional[float]:
    """
    Convert cardinal direction to azimuth angle.

    :param direction: Cardinal direction (N, S, E, W, O, NE, etc.)
    :type direction: str
    :return: Azimuth angle [degrees] or None
    :rtype: float or None
    """
    # Azimuth angle mapping for PV system orientations
    # Following solar energy conventions: 0° = South, 90° = West
    azimuths = {
        'N': 180,   # North - minimal irradiation
        'W': 90,    # West - afternoon energy production
        'S': 0,     # South - optimal for Northern Hemisphere
        'O': 270,   # East ("Ost" in German) - morning energy production
        'NO': 225,  # Northeast ("Nordost") - morning-biased production
        'SO': 315,  # Southeast ("Südost") - morning-optimal production
        'SW': 45,   # Southwest - afternoon-optimal production
        'NW': 135   # Northwest - afternoon-biased production
    }
    
    return azimuths.get(direction.upper(), None)

def calculate_building(TRY_data: str, building_data: str, output_filename: str) -> None:
    """
    Calculate photovoltaic yield for multiple buildings.

    :param TRY_data: Path to Test Reference Year data
    :type TRY_data: str
    :param building_data: Path to building CSV (building_id, roof_area, orientation)
    :type building_data: str
    :param output_filename: Path for results CSV output
    :type output_filename: str
    """
    # Load building data from CSV file with robust error handling
    try:
        gdata = np.genfromtxt(
            building_data, 
            delimiter=";", 
            skip_header=1, 
            dtype=None, 
            encoding='utf-8'
        )
    except Exception as e:
        raise ValueError(f"Error loading building data from {building_data}: {e}")

    # Location parameters for PV calculation (customizable)
    # Default: Munich, Germany - Central European location
    Longitude = 11.576       # Munich longitude [degrees]
    STD_Longitude = 15.0     # Central European Time standard longitude [degrees]
    Latitude = 48.137        # Munich latitude [degrees]
    
    # PV system parameters
    Albedo = 0.2            # Typical ground reflection coefficient [-]
    Collector_tilt_angle = 36  # Optimal tilt angle for latitude [degrees]
    
    # Initialize time series for annual hourly data
    Annual_hours = np.arange(1, 8761)  # Hours 1-8760 for full year

    # Initialize results DataFrame with time column
    df = pd.DataFrame()
    df['Annual Hours'] = Annual_hours

    print("Calculating PV yield for buildings...")
    print(f"Processing {len(gdata)} building systems...")

    # Process each building in the input data
    for idx, (building, area, direction) in enumerate(gdata):
        try:
            # Convert numpy types to Python native types
            building = str(building)
            area = float(area)
            direction = str(direction)
            
            print(f"Processing {building}: {area:.1f} m² {direction}-facing")
            
            # Get azimuth angle for the specified direction
            current_azimuth = azimuth_angle(direction)

            # Handle East-West (OW) configuration with split installation
            if current_azimuth is None and direction.upper() == "OW":
                # Split area equally between East and West orientations
                area_split = area / 2
                directions = ["O", "W"]  # East and West in German notation
                print(f"  → East-West configuration: {area_split:.1f} m² each direction")
            else:
                # Single orientation configuration
                directions = [direction]

            # Calculate PV performance for each orientation
            for orientation in directions:
                current_azimuth = azimuth_angle(orientation)
                
                if current_azimuth is not None:
                    # Use split area for EW systems, full area for single orientation
                    system_area = area_split if direction.upper() == "OW" else area
                    
                    # Calculate PV performance using EU PVGIS methodology
                    yield_kWh, max_power, P_L = Calculate_PV(
                        TRY_data, system_area, Longitude, STD_Longitude, 
                        Latitude, Albedo, current_azimuth, Collector_tilt_angle
                    )

                    # Generate appropriate column suffix for EW systems
                    suffix = f" {orientation}" if direction.upper() == "OW" else ""
                    
                    # Display calculation results
                    print(f"  → PV yield {building}{suffix}: {yield_kWh/1000:.1f} MWh")
                    print(f"  → Maximum power {building}{suffix}: {max_power:.1f} kW")
                    
                    # Add results to DataFrame with descriptive column name
                    column_name = f'{building}{suffix} {system_area:.1f} m² [kW]'
                    df[column_name] = P_L
                else:
                    print(f"  → Warning: Invalid orientation '{orientation}' for {building}")
                    
        except Exception as e:
            print(f"  → Error processing {building}: {e}")
            continue

    # Save comprehensive results to CSV file
    try:
        df.to_csv(output_filename, index=False, sep=';', encoding='utf-8-sig')
        print(f"\nResults successfully saved to: {output_filename}")
        
        # Calculate and display summary statistics
        pv_columns = [col for col in df.columns if '[kW]' in col]
        total_systems = len(pv_columns)
        total_capacity = df[pv_columns].max().sum()
        annual_yield = df[pv_columns].sum().sum() / 1000  # Convert to MWh
        
        print(f"Summary:")
        print(f"  → Total systems processed: {total_systems}")
        print(f"  → Total PV capacity: {total_capacity:.1f} kW")
        print(f"  → Annual district yield: {annual_yield:.1f} MWh")
        print(f"  → Average capacity factor: {annual_yield*1000/(total_capacity*8760):.2f}")
        
    except Exception as e:
        raise IOError(f"Error saving results to {output_filename}: {e}")