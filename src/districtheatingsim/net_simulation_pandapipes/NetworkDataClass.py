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
    # Input data for the network generation
    import_type: str # type of import, currently only geoJSON, STANET is planned
    flow_line_path: str # Path to the flow line geoJSON file
    return_line_path: str # Path to the return line geoJSON file
    heat_consumer_path: str # Path to the heat consumer geoJSON file
    heat_generator_path: str # Path to the heat generator geoJSON file
    heat_demand_json_path: str # Path to the heat demand JSON file

    # Network data
    netconfiguration: str # net configuration, could be 'Niedertemperaturnetz' or 'kaltes Netz'
    supply_temperature_control: str # supply temperature control, could be 'Statisch' or 'Gleitend'
    max_supply_temperature_heat_generator: float # maximum supply temperature in °C
    min_supply_temperature_heat_generator: float # minimum supply temperature in °C
    max_air_temperature_heat_generator: float # maximum air temperature in °C
    min_air_temperature_heat_generator: float # minimum air temperature in °C
    flow_pressure_pump: float # flow pressure of the pump in bar
    lift_pressure_pump: float # lift pressure of the pump in bar
    min_supply_temperature_building_checked: bool # minimum supply temperature for the building in °C
    min_supply_temperature_building: float # in °C, if None, no minimum supply temperature is set
    fixed_return_temperature_heat_consumer_checked: bool # fixed return temperature for the heat consumer in °C
    fixed_return_temperature_heat_consumer: float # in °C, if None, no fixed return temperature is set
    dT_RL: float # temperature difference between net and building in K
    building_temperature_checked: bool # use time dependent building temperature from JSON file
    pipetype: str # pipe type

    # Optimization variables
    diameter_optimization_pipe_checked: bool # optimization variable, if the diameters of the pipes should be optimized
    max_velocity_pipe: float # optimization variable, maximum velocity in the pipe in m/s
    material_filter_pipe: str # optimization variable, material filter for the pipe
    k_mm_pipe: float # pipe roughness in mm

    # Main producer location index and secondary producers
    main_producer_location_index: int # index of the main producer location
    secondary_producers: List[SecondaryProducer] # list of secondary producers
    
    # file path for COP, added from the main data manager
    COP_filename: Optional[str] = None
    TRY_filename: Optional[str] = None

    # Results 
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

    # time series data
    start_time_step: Optional[int] = None
    end_time_step: Optional[int] = None
    results_csv_filename: Optional[str] = None

    supply_temperature_heat_generator: Optional[float | np.ndarray] = None# supply temperature of the heat generator in °C, could be a float or a numpy array of floats with the length of 8760 (8760 hours in a year)
    yearly_time_steps_start_end: Optional[np.ndarray] = None
    net_results: Optional[Dict[str, Any]] = None
    pump_results: Optional[Dict[str, Any]] = None
    plot_data: Optional[Dict[str, Any]] = None

    def calculate_results(self) -> dict:
        results = {}

        results["Anzahl angeschlossene Gebäude"] = len(self.net.heat_consumer) if hasattr(self.net, 'heat_consumer') else None

        if hasattr(self.net, 'circ_pump_pressure'):
            if hasattr(self.net, 'circ_pump_mass'):
                results["Anzahl Heizzentralen"] = len(self.net.circ_pump_pressure) + len(self.net.circ_pump_mass)
            else:
                results["Anzahl Heizzentralen"] = len(self.net.circ_pump_pressure)
        else:
            results["Anzahl Heizzentralen"] = None

        results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] = np.sum(self.waerme_ges_kW) / 1000 if self.waerme_ges_kW is not None else None
        results["max. Heizlast Gebäude [kW]"] = np.max(self.waerme_ges_kW) if self.waerme_ges_kW is not None else None

        if hasattr(self.net, 'pipe') and hasattr(self.net.pipe, 'length_km'):
            results["Trassenlänge Wärmenetz [m]"] = self.net.pipe.length_km.sum() * 1000 / 2
        else:
            results["Trassenlänge Wärmenetz [m]"] = None

        if results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] and results["Trassenlänge Wärmenetz [m]"]:
            results["Wärmebedarfsdichte [MWh/(a*m)]"] = results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] / results["Trassenlänge Wärmenetz [m]"]
        else:
            results["Wärmebedarfsdichte [MWh/(a*m)]"] = None

        if results["max. Heizlast Gebäude [kW]"] and results["Trassenlänge Wärmenetz [m]"]:
            results["Anschlussdichte [kW/m]"] = results["max. Heizlast Gebäude [kW]"] / results["Trassenlänge Wärmenetz [m]"]
        else:
            results["Anschlussdichte [kW/m]"] = None

        # Netz-Ergebnisse
        jahreswaermeerzeugung = 0
        pumpenstrom = 0
        if self.pump_results is not None:
            for pump_type, pumps in self.pump_results.items():
                for idx, pump_data in pumps.items():
                    jahreswaermeerzeugung += np.sum(pump_data['qext_kW']) / 1000
                    pumpenstrom += np.sum((pump_data['mass_flow']/1000)*(pump_data['deltap']*100)) / 1000
        results["Jahreswärmeerzeugung [MWh]"] = jahreswaermeerzeugung if jahreswaermeerzeugung != 0 else None
        results["Pumpenstrom [MWh]"] = pumpenstrom if pumpenstrom != 0 else None

        if results["Jahreswärmeerzeugung [MWh]"] and results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"]:
            verluste = results["Jahreswärmeerzeugung [MWh]"] - results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"]
            results["Verteilverluste [MWh]"] = verluste
            results["rel. Verteilverluste [%]"] = (verluste / results["Jahreswärmeerzeugung [MWh]"]) * 100
        else:
            results["Verteilverluste [MWh]"] = None
            results["rel. Verteilverluste [%]"] = None

        return results
    
    def prepare_plot_data(self):
        self.plot_data = {
            "Gesamtwärmebedarf Wärmeübertrager": {
                "data": self.waerme_ges_kW,
                "label": "Wärmebedarf Wärmeübertrager in kW",
                "axis": "left",
                "time": self.yearly_time_steps
            }
        }
        if np.sum(self.strombedarf_ges_kW) > 0:
            self.plot_data["Gesamtheizlast Gebäude"] = {
                "data": self.waerme_ges_kW + self.strombedarf_ges_kW,
                "label": "Gesamtheizlast Gebäude in kW",
                "axis": "left",
                "time": self.yearly_time_steps
            }
            self.plot_data["Gesamtstrombedarf Wärmepumpen Gebäude"] = {
                "data": self.strombedarf_ges_kW,
                "label": "Gesamtstrombedarf Wärmepumpen Gebäude in kW",
                "axis": "left",
                "time": self.yearly_time_steps
            }
        if self.pump_results is not None:
            for pump_type, pumps in self.pump_results.items():
                for idx, pump_data in pumps.items():
                    self.plot_data[f"Wärmeerzeugung {pump_type} {idx+1}"] = {
                        "data": pump_data['qext_kW'],
                        "label": "Wärmeerzeugung in kW",
                        "axis": "left",
                        "time": self.yearly_time_steps_start_end
                    }
                    self.plot_data[f"Massenstrom {pump_type} {idx+1}"] = {
                        "data": pump_data['mass_flow'],
                        "label": "Massenstrom in kg/s",
                        "axis": "right",
                        "time": self.yearly_time_steps_start_end
                    }
                    self.plot_data[f"Delta p {pump_type} {idx+1}"] = {
                        "data": pump_data['deltap'],
                        "label": "Druckdifferenz in bar",
                        "axis": "right",
                        "time": self.yearly_time_steps_start_end
                    }
                    self.plot_data[f"Vorlauftemperatur {pump_type} {idx+1}"] = {
                        "data": pump_data['flow_temp'],
                        "label": "Temperatur in °C",
                        "axis": "right",
                        "time": self.yearly_time_steps_start_end
                    }
                    self.plot_data[f"Rücklauftemperatur {pump_type} {idx+1}"] = {
                        "data": pump_data['return_temp'],
                        "label": "Temperatur in °C",
                        "axis": "right",
                        "time": self.yearly_time_steps_start_end
                    }
                    self.plot_data[f"Vorlaufdruck {pump_type} {idx+1}"] = {
                        "data": pump_data['flow_pressure'],
                        "label": "Druck in bar",
                        "axis": "right",
                        "time": self.yearly_time_steps_start_end
                    }
                    self.plot_data[f"Rücklaufdruck {pump_type} {idx+1}"] = {
                        "data": pump_data['return_pressure'],
                        "label": "Druck in bar",
                        "axis": "right",
                        "time": self.yearly_time_steps_start_end
                    }

