"""
Network Generation Data Class Module
================================================

This module provides data structures for comprehensive district heating network simulation
and analysis.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

It defines the core data classes used throughout the simulation workflow,
including network configuration parameters, input/output data management, and result
processing capabilities.

The module supports various network configurations including traditional hot water networks,
cold networks with decentralized heat pumps, and hybrid systems with multiple heat generators.
It handles time series data, temperature control strategies, and comprehensive result analysis
with automatic calculation of key performance indicators.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
import numpy as np

@dataclass
class SecondaryProducer:
    """
    Secondary heat producer with mass flow control based on load percentage.
    
    :ivar index: Unique producer index matching GeoJSON heat producer location
    :vartype index: int
    :ivar load_percentage: Percentage of total network heat load [%]
    :vartype load_percentage: float
    :ivar mass_flow: Calculated mass flow [kg/s], set during preprocessing
    :vartype mass_flow: Optional[float]
    
    .. note::
       Load percentages across all secondary producers should not exceed 100%.
       Main producer handles remaining capacity. Extensible for additional parameters.
    """
    index: int
    load_percentage: float
    mass_flow: Optional[float] = None

    # could be extended with additional parameters as needed

@dataclass
class NetworkGenerationData:
    """
    Central data container for district heating network simulation and analysis.
    
    :ivar import_type: Import method type (currently "geoJSON")
    :vartype import_type: str
    :ivar network_geojson_path: Path to unified GeoJSON file (Wärmenetz.geojson)
    :vartype network_geojson_path: str
    :ivar heat_demand_json_path: Path to building heat demand JSON
    :vartype heat_demand_json_path: str
    :ivar netconfiguration: Network type ("kaltes Netz", "Niedertemperaturnetz")
    :vartype netconfiguration: str
    :ivar supply_temperature_control: Control strategy ("Statisch", "Gleitend")
    :vartype supply_temperature_control: str
    :ivar max_supply_temperature_heat_generator: Maximum supply temperature [°C]
    :vartype max_supply_temperature_heat_generator: float
    :ivar min_supply_temperature_heat_generator: Minimum supply temperature for sliding control [°C]
    :vartype min_supply_temperature_heat_generator: float
    :ivar max_air_temperature_heat_generator: Maximum outdoor air temperature [°C]
    :vartype max_air_temperature_heat_generator: float
    :ivar min_air_temperature_heat_generator: Design outdoor air temperature [°C]
    :vartype min_air_temperature_heat_generator: float
    :ivar flow_pressure_pump: Pump outlet pressure [bar]
    :vartype flow_pressure_pump: float
    :ivar lift_pressure_pump: Pump pressure lift [bar]
    :vartype lift_pressure_pump: float
    :ivar pipetype: Standard pipe type designation
    :vartype pipetype: str
    :ivar diameter_optimization_pipe_checked: Enable diameter optimization
    :vartype diameter_optimization_pipe_checked: bool
    :ivar max_velocity_pipe: Maximum water velocity [m/s]
    :vartype max_velocity_pipe: float
    :ivar material_filter_pipe: Pipe material filter
    :vartype material_filter_pipe: str
    :ivar k_mm_pipe: Pipe roughness [mm]
    :vartype k_mm_pipe: float
    :ivar main_producer_location_index: Main heat producer index in GeoJSON
    :vartype main_producer_location_index: int
    :ivar secondary_producers: List of secondary producers
    :vartype secondary_producers: List[SecondaryProducer]
    :ivar net: Pandapipes network object
    :vartype net: Optional[Any]
    :ivar pump_results: Structured pump simulation results
    :vartype pump_results: Optional[Dict[str, Any]]
    :ivar plot_data: Processed visualization data
    :vartype plot_data: Optional[Dict[str, Any]]
    :ivar kpi_results: Key performance indicators
    :vartype kpi_results: Optional[Dict[str, Union[int, float, None]]]
    
    .. note::
       Supports GeoJSON-based initialization, time series simulation, KPI calculation.
       Handles cold networks (heat pumps), static/sliding temperature control.
       Data flow: GeoJSON+JSON → initialization → simulation → results → KPIs.
    """
    
    # Input data for the network generation
    import_type: str
    network_geojson_path: str  # Unified GeoJSON file path
    heat_demand_json_path: str

    # Network configuration data
    netconfiguration: str
    supply_temperature_control: str
    max_supply_temperature_heat_generator: float
    min_supply_temperature_heat_generator: float
    max_air_temperature_heat_generator: float
    min_air_temperature_heat_generator: float
    flow_pressure_pump: float
    lift_pressure_pump: float
    min_supply_temperature_building_checked: bool
    min_supply_temperature_building: float
    fixed_return_temperature_heat_consumer_checked: bool
    fixed_return_temperature_heat_consumer: float
    dT_RL: float
    building_temperature_checked: bool
    pipetype: str

    # Optimization variables
    diameter_optimization_pipe_checked: bool
    max_velocity_pipe: float
    material_filter_pipe: str
    k_mm_pipe: float

    # Producer configuration
    main_producer_location_index: int
    secondary_producers: List[SecondaryProducer]
    
    # External data file paths
    COP_filename: Optional[str] = None
    TRY_filename: Optional[str] = None

    # Building and temperature data (processed from JSON)
    supply_temperature_buildings: Optional[np.ndarray] = None
    return_temperature_buildings: Optional[np.ndarray] = None
    supply_temperature_building_curve: Optional[np.ndarray] = None
    return_temperature_building_curve: Optional[np.ndarray] = None
    yearly_time_steps: Optional[np.ndarray] = None
    waerme_gebaeude_ges_W: Optional[np.ndarray] = None
    heizwaerme_gebaeude_ges_W: Optional[np.ndarray] = None
    ww_waerme_gebaeude_ges_W: Optional[np.ndarray] = None
    max_waerme_gebaeude_ges_W: Optional[np.ndarray] = None
    
    # Heat consumer data (network side)
    return_temperature_heat_consumer: Optional[np.ndarray] = None
    min_supply_temperature_heat_consumer: Optional[np.ndarray] = None
    waerme_hast_ges_W: Optional[np.ndarray] = None
    max_waerme_hast_ges_W: Optional[np.ndarray] = None
    strombedarf_hast_ges_W: Optional[np.ndarray] = None
    max_el_leistung_hast_ges_W: Optional[np.ndarray] = None

    # Aggregated system data
    waerme_hast_ges_kW: Optional[np.ndarray] = None
    strombedarf_hast_ges_kW: Optional[np.ndarray] = None
    waerme_ges_kW: Optional[np.ndarray] = None
    strombedarf_ges_kW: Optional[np.ndarray] = None

    # Network object and simulation parameters
    net: Optional[Any] = None
    start_time_step: Optional[int] = None
    end_time_step: Optional[int] = None
    results_csv_filename: Optional[str] = None

    # Simulation results
    supply_temperature_heat_generator: Optional[Union[float, np.ndarray]] = None
    net_results: Optional[Dict[str, Any]] = None
    pump_results: Optional[Dict[str, Any]] = None
    plot_data: Optional[Dict[str, Any]] = None
    
    # KPI results
    kpi_results: Optional[Dict[str, Union[int, float, None]]] = None

    def calculate_results(self) -> Dict[str, Union[int, float, None]]:
        """
        Calculate network KPIs including heat density, losses, and pump consumption.
        
        :return: Dict with KPIs (Anzahl angeschlossene Gebäude, Jahresgesamtwärmebedarf [MWh/a], max. Heizlast [kW], Trassenlänge [m], Wärmebedarfsdichte [MWh/(a*m)], Anschlussdichte [kW/m], Jahreswärmeerzeugung [MWh], Pumpenstrom [MWh], Verteilverluste [MWh], rel. Verteilverluste [%])
        :rtype: Dict[str, Union[int, float, None]]
        
        .. note::
           Density = demand/length. Losses = generation - demand. Pump power from mass flow and Δp.
           Network length divided by 2 (supply+return). Requires net, pump_results, waerme_ges_kW.
        """
        results = {}

        # Network topology metrics
        results["Anzahl angeschlossene Gebäude"] = (
            len(self.net.heat_consumer) if hasattr(self.net, 'heat_consumer') else None
        )

        # Heat generation capacity
        if hasattr(self.net, 'circ_pump_pressure'):
            if hasattr(self.net, 'circ_pump_mass'):
                results["Anzahl Heizzentralen"] = (
                    len(self.net.circ_pump_pressure) + len(self.net.circ_pump_mass)
                )
            else:
                results["Anzahl Heizzentralen"] = len(self.net.circ_pump_pressure)
        else:
            results["Anzahl Heizzentralen"] = None

        # Energy demand metrics
        results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] = (
            np.sum(self.waerme_ges_kW) / 1000 if self.waerme_ges_kW is not None else None
        )
        results["max. Heizlast Gebäude [kW]"] = (
            np.max(self.waerme_ges_kW) if self.waerme_ges_kW is not None else None
        )

        # Network infrastructure metrics
        if hasattr(self.net, 'pipe') and hasattr(self.net.pipe, 'length_km'):
            # Divide by 2 for single-pipe equivalent length (supply + return)
            results["Trassenlänge Wärmenetz [m]"] = self.net.pipe.length_km.sum() * 1000 / 2
        else:
            results["Trassenlänge Wärmenetz [m]"] = None

        # Density calculations
        if (results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] is not None and 
            results["Trassenlänge Wärmenetz [m]"] is not None):
            results["Wärmebedarfsdichte [MWh/(a*m)]"] = (
                results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] / 
                results["Trassenlänge Wärmenetz [m]"]
            )
        else:
            results["Wärmebedarfsdichte [MWh/(a*m)]"] = None

        if (results["max. Heizlast Gebäude [kW]"] is not None and 
            results["Trassenlänge Wärmenetz [m]"] is not None):
            results["Anschlussdichte [kW/m]"] = (
                results["max. Heizlast Gebäude [kW]"] / 
                results["Trassenlänge Wärmenetz [m]"]
            )
        else:
            results["Anschlussdichte [kW/m]"] = None

        # Network operation results
        jahreswaermeerzeugung = 0
        pumpenstrom = 0
        if self.pump_results is not None:
            for pump_type, pumps in self.pump_results.items():
                for idx, pump_data in pumps.items():
                    # Heat generation [MWh/a]
                    jahreswaermeerzeugung += np.sum(pump_data['qext_kW']) / 1000
                    # Pump power: P = (ṁ * Δp) / ρ [MWh/a]
                    pumpenstrom += np.sum(
                        (pump_data['mass_flow']/1000) * (pump_data['deltap']*100)
                    ) / 1000

        results["Jahreswärmeerzeugung [MWh]"] = (
            jahreswaermeerzeugung if jahreswaermeerzeugung != 0 else None
        )
        results["Pumpenstrom [MWh]"] = pumpenstrom if pumpenstrom != 0 else None

        # Distribution loss calculations
        if (results["Jahreswärmeerzeugung [MWh]"] is not None and 
            results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] is not None):
            verluste = (results["Jahreswärmeerzeugung [MWh]"] - 
                       results["Jahresgesamtwärmebedarf Gebäude [MWh/a]"])
            results["Verteilverluste [MWh]"] = verluste
            results["rel. Verteilverluste [%]"] = (
                (verluste / results["Jahreswärmeerzeugung [MWh]"]) * 100
            )
        else:
            results["Verteilverluste [MWh]"] = None
            results["rel. Verteilverluste [%]"] = None

        self.kpi_results = results
        return results
    
    def prepare_plot_data(self) -> None:
        """
        Structure simulation results for visualization with labels, axes, and time alignment.
        
        .. note::
           Creates plot_data dict with entries: data (numpy array), label (string), axis
           (left/right), time (array). Includes heat demand, electrical data (cold networks),
           producer data (heat generation, mass flow, pressures, temperatures). Indexed by
           variable name and producer number.
        """
        # Determine time range for plots (use simulated range if available)
        if hasattr(self, 'start_time_step') and hasattr(self, 'end_time_step'):
            time_range = self.yearly_time_steps[self.start_time_step:self.end_time_step]
            data_range_waerme = self.waerme_ges_kW[self.start_time_step:self.end_time_step]
            data_range_strom = self.strombedarf_ges_kW[self.start_time_step:self.end_time_step]
        else:
            # Fallback: use full year
            time_range = self.yearly_time_steps
            data_range_waerme = self.waerme_ges_kW
            data_range_strom = self.strombedarf_ges_kW
        
        # Initialize plot data with base heat demand
        self.plot_data = {
            "Gesamtwärmebedarf Wärmeübertrager": {
                "data": data_range_waerme,
                "label": "Wärmebedarf Wärmeübertrager in kW",
                "axis": "left",
                "time": time_range
            }
        }
        
        # Add electrical data for cold networks
        if np.sum(data_range_strom) > 0:
            self.plot_data["Gesamtheizlast Gebäude"] = {
                "data": data_range_waerme + data_range_strom,
                "label": "Gesamtheizlast Gebäude in kW",
                "axis": "left",
                "time": time_range
            }
            self.plot_data["Gesamtstrombedarf Wärmepumpen Gebäude"] = {
                "data": data_range_strom,
                "label": "Gesamtstrombedarf Wärmepumpen Gebäude in kW",
                "axis": "left",
                "time": time_range
            }
        
        # Add detailed producer/pump data
        if self.pump_results is not None:
            for pump_type, pumps in self.pump_results.items():
                for idx, pump_data in pumps.items():
                    # Time series data for simulation period
                    time_series = self.yearly_time_steps[self.start_time_step:self.end_time_step]
                    
                    # Heat generation data
                    self.plot_data[f"Wärmeerzeugung {pump_type} {idx+1}"] = {
                        "data": pump_data['qext_kW'],
                        "label": "Wärmeerzeugung in kW",
                        "axis": "left",
                        "time": time_series
                    }
                    
                    # Hydraulic data
                    self.plot_data[f"Massenstrom {pump_type} {idx+1}"] = {
                        "data": pump_data['mass_flow'],
                        "label": "Massenstrom in kg/s",
                        "axis": "right",
                        "time": time_series
                    }
                    
                    self.plot_data[f"Delta p {pump_type} {idx+1}"] = {
                        "data": pump_data['deltap'],
                        "label": "Druckdifferenz in bar",
                        "axis": "right",
                        "time": time_series
                    }
                    
                    # Temperature data
                    self.plot_data[f"Vorlauftemperatur {pump_type} {idx+1}"] = {
                        "data": pump_data['flow_temp'],
                        "label": "Temperatur in °C",
                        "axis": "right",
                        "time": time_series
                    }
                    
                    self.plot_data[f"Rücklauftemperatur {pump_type} {idx+1}"] = {
                        "data": pump_data['return_temp'],
                        "label": "Temperatur in °C",
                        "axis": "right",
                        "time": time_series
                    }
                    
                    # Pressure data
                    self.plot_data[f"Vorlaufdruck {pump_type} {idx+1}"] = {
                        "data": pump_data['flow_pressure'],
                        "label": "Druck in bar",
                        "axis": "right",
                        "time": time_series
                    }
                    
                    self.plot_data[f"Rücklaufdruck {pump_type} {idx+1}"] = {
                        "data": pump_data['return_pressure'],
                        "label": "Druck in bar",
                        "axis": "right",
                        "time": time_series
                    }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize network data including KPIs for saving.
        
        :return: Dictionary with all object attributes including kpi_results
        :rtype: Dict[str, Any]
        """
        data = self.__dict__.copy()
        # Only include serializable fields
        if hasattr(self, 'kpi_results') and self.kpi_results is not None:
            data['kpi_results'] = self.kpi_results
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkGenerationData':
        """
        Deserialize network data from saved dictionary.
        
        :param data: Dictionary with serialized network data
        :type data: Dict[str, Any]
        :return: Reconstructed NetworkGenerationData object with KPIs
        :rtype: NetworkGenerationData
        """
        # Extract kpi_results before creating object
        kpi_results = data.pop('kpi_results', None)
        
        # Create object with remaining data
        obj = cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
        
        # Restore kpi_results
        if kpi_results is not None:
            obj.kpi_results = kpi_results
            
        return obj