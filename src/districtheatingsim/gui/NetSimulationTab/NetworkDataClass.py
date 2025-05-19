"""
Filename: NetworkDataClass.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
    Date: 2025-05-17
Description: Contains the data class for network generation data.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import numpy as np

@dataclass
class SecondaryProducer:
    index: int
    load_percentage: float
    # beliebig erweiterbar

@dataclass
class NetworkGenerationData:
    flow_line_path: str # Path to the flow line file
    return_line_path: str # Path to the return line file
    heat_consumer_path: str # Path to the heat consumer file
    heat_generator_path: str # Path to the heat generator file
    heat_demand_json_path: str # Path to the heat demand JSON file
    supply_temperature_heat_generator: float | np.ndarray # supply temperature of the heat generator in °C, could be a float or a numpy array of floats with the length of 8760 (8760 hours in a year)
    flow_pressure_pump: float # flow pressure of the pump in bar
    lift_pressure_pump: float # lift pressure of the pump in bar
    netconfiguration: str # net configuration, could be 'Niedertemperaturnetz' or 'kaltes Netz'
    dT_RL: float # temperature difference between net and building in K
    building_temperature_checked: bool # 
    pipetype: str # pipe type
    max_velocity_pipe: float # optimization variable, maximum velocity in the pipe in m/s
    material_filter_pipe: str # optimization variable, material filter for the pipe
    diameter_optimization_pipe_checked: bool # optimization variable, if the diameters of the pipes should be optimized
    k_mm_pipe: float # pipe roughness in mm
    main_producer_location_index: int # index of the main producer location
    secondary_producers: List[SecondaryProducer] # list of secondary producers
    import_type: str # type of import, currently only geoJSON
    min_supply_temperature_building: Optional[float] = None # in °C, if None, no minimum supply temperature is set
    fixed_return_temperature_heat_consumer: Optional[float] = None # in °C, if None, no fixed return temperature is set

    # file paths for COP, added from the main data manager
    COP_filename: Optional[str] = None

    max_supply_temperature_heat_generator: Optional[float] = None  # int / float
    supply_temperature_buildings: Optional[float] = None  # int / float
    return_temperature_buildings: Optional[float] = None  # int / float
    yearly_time_steps: Optional[np.ndarray] = None
    waerme_gebaeude_ges_W: Optional[np.ndarray] = None
    heizwaerme_gebaeude_ges_W: Optional[np.ndarray] = None
    ww_waerme_gebaeude_ges_W: Optional[np.ndarray] = None
    supply_temperature_building_curve: Optional[np.ndarray] = None
    return_temperature_building_curve: Optional[np.ndarray] = None
    max_waerme_gebaeude_ges_W: Optional[np.ndarray] = None
    return_temperature_heat_consumer: Optional[np.ndarray] = None
    min_supply_temperature_heat_consumer: Optional[np.ndarray] = None
    waerme_hast_ges_W: Optional[np.ndarray] = None
    max_waerme_hast_ges_W: Optional[np.ndarray] = None
    strombedarf_hast_ges_W: Optional[np.ndarray] = None
    max_el_leistung_hast_ges_W: Optional[np.ndarray] = None
    net: Optional[Any] = None  # pandapipesNet

    # after initialization
    waerme_hast_ges_kW: Optional[np.ndarray] = None
    strombedarf_hast_ges_kW: Optional[np.ndarray] = None
    waerme_ges_kW: Optional[np.ndarray] = None
    strombedarf_ges_kW: Optional[np.ndarray] = None

    Anzahl_Gebäude: Optional[int] = None
    Anzahl_Heizzentralen: Optional[int] = None
    Gesamtwärmebedarf_Gebäude_MWh: Optional[float] = None
    Gesamtheizlast_Gebäude_kW: Optional[float] = None
    Trassenlänge_m: Optional[float] = None
    Wärmebedarfsdichte_MWh_a_m: Optional[float] = None
    Anschlussdichte_kW_m: Optional[float] = None
    Jahreswärmeerzeugung_MWh: Optional[float] = None
    Pumpenstrombedarf_MWh: Optional[float] = None
    Verteilverluste_kW: Optional[float] = None
    rel_Verteilverluste_percent: Optional[float] = None

    # time series data
    start_time_step: Optional[int] = None
    end_time_step: Optional[int] = None
    results_csv_filename: Optional[str] = None

    yearly_time_steps_start_end: Optional[np.ndarray] = None
    net_results: Optional[Dict[str, Any]] = None
    pump_results: Optional[Dict[str, Any]] = None
    plot_data: Optional[Dict[str, Any]] = None

