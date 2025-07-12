"""
Network Generation Data Class Module
================================================

This module provides data structures for comprehensive district heating network simulation
and analysis.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-17

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
    Data class representing a secondary heat producer in the district heating network.
    
    Secondary producers are additional heat sources that supplement the main heat generator,
    typically used for distributed generation, renewable energy integration, or load balancing.
    Each secondary producer operates with mass flow control based on a percentage of the
    total network heat demand.
    
    Attributes
    ----------
    index : int
        Unique identifier index for the secondary producer within the network.
        Must correspond to the heat producer location index in the GeoJSON data.
    load_percentage : float
        Percentage of total network heat load handled by this producer [%].
        Values typically range from 1-50% depending on system design.
        
    Examples
    --------
    >>> # Create secondary producer handling 20% of total load
    >>> secondary = SecondaryProducer(index=1, load_percentage=20.0)
    >>> print(f"Producer {secondary.index} handles {secondary.load_percentage}% of load")
    Producer 1 handles 20.0% of load
    
    Notes
    -----
    - Load percentages across all secondary producers should not exceed 100%
    - The main producer automatically handles remaining load capacity
    - Index must match the corresponding heat producer location in GeoJSON data
    - Can be extended with additional parameters as needed (marked as extensible)
    
    See Also
    --------
    NetworkGenerationData : Main network data container
    """
    index: int
    load_percentage: float
    mass_flow: Optional[float] = None

    # could be extended with additional parameters as needed

@dataclass
class NetworkGenerationData:
    """
    Comprehensive data class for district heating network generation and simulation.
    
    This class serves as the central data container for all network simulation parameters,
    input data, processing results, and analysis outputs. It supports the complete workflow
    from GeoJSON-based network initialization through time series simulation to result
    analysis and visualization.
    
    The class handles various network configurations including traditional hot water systems,
    cold networks with heat pumps, and hybrid systems with multiple heat sources. It manages
    both static network parameters and dynamic time series data for comprehensive simulation.
    
    Parameters
    ----------
    import_type : str
        Type of network data import method.
        Currently supported: "geoJSON" (STANET import planned for future versions).
    flow_line_path : str
        File path to the GeoJSON file containing supply line geometries.
    return_line_path : str
        File path to the GeoJSON file containing return line geometries.
    heat_consumer_path : str
        File path to the GeoJSON file containing heat consumer locations and connections.
    heat_generator_path : str
        File path to the GeoJSON file containing heat producer/generator locations.
    heat_demand_json_path : str
        File path to the JSON file containing building heat demand time series data.
    netconfiguration : str
        Network configuration type defining the heating system architecture.
        Options: "Niedertemperaturnetz" (low-temperature network), "kaltes Netz" (cold network).
    supply_temperature_control : str
        Supply temperature control strategy for the heat generator.
        Options: "Statisch" (static/constant), "Gleitend" (sliding/weather-dependent).
    max_supply_temperature_heat_generator : float
        Maximum supply temperature at the main heat generator [°C].
    min_supply_temperature_heat_generator : float
        Minimum supply temperature for sliding control [°C].
    max_air_temperature_heat_generator : float
        Maximum outdoor air temperature for heating operation [°C].
    min_air_temperature_heat_generator : float
        Design outdoor air temperature for maximum heating load [°C].
    flow_pressure_pump : float
        Operating pressure at pump outlet [bar].
    lift_pressure_pump : float
        Pressure increase provided by circulation pumps [bar].
    min_supply_temperature_building_checked : bool
        Flag indicating whether minimum building supply temperature is enforced.
    min_supply_temperature_building : float
        Minimum required supply temperature at building level [°C].
    fixed_return_temperature_heat_consumer_checked : bool
        Flag for using fixed return temperature at heat consumers.
    fixed_return_temperature_heat_consumer : float
        Fixed return temperature value for heat consumers [°C].
    dT_RL : float
        Temperature difference between network and building systems [K].
    building_temperature_checked : bool
        Flag to use time-dependent building temperatures from JSON data.
    pipetype : str
        Standard pipe type designation for network pipes.
    diameter_optimization_pipe_checked : bool
        Flag enabling automatic pipe diameter optimization.
    max_velocity_pipe : float
        Maximum allowable water velocity in pipes [m/s].
    material_filter_pipe : str
        Material filter criteria for pipe selection.
    k_mm_pipe : float
        Absolute pipe roughness [mm].
    main_producer_location_index : int
        Index of the main heat producer location in the GeoJSON data.
    secondary_producers : List[SecondaryProducer]
        List of secondary heat producer configurations.
        
    Attributes
    ----------
    COP_filename : Optional[str]
        File path to heat pump coefficient of performance data.
    TRY_filename : Optional[str]
        File path to Test Reference Year weather data file.
    net : Optional[Any]
        pandapipes network object containing the complete network topology.
    yearly_time_steps : Optional[np.ndarray]
        Array of datetime64 objects representing simulation time steps.
    waerme_ges_kW : Optional[np.ndarray]
        Total network heat demand time series [kW].
    strombedarf_ges_kW : Optional[np.ndarray]
        Total electrical power consumption time series [kW].
    pump_results : Optional[Dict[str, Any]]
        Structured simulation results for all heat producers/pumps.
    plot_data : Optional[Dict[str, Any]]
        Processed data ready for visualization and plotting.
        
    Examples
    --------
    >>> # Create network configuration for cold network
    >>> network_data = NetworkGenerationData(
    ...     import_type="geoJSON",
    ...     flow_line_path="data/flow_lines.geojson",
    ...     return_line_path="data/return_lines.geojson",
    ...     heat_consumer_path="data/consumers.geojson",
    ...     heat_generator_path="data/producers.geojson",
    ...     heat_demand_json_path="data/heat_demands.json",
    ...     netconfiguration="kaltes Netz",
    ...     supply_temperature_control="Gleitend",
    ...     max_supply_temperature_heat_generator=45.0,
    ...     min_supply_temperature_heat_generator=25.0,
    ...     # ... other required parameters
    ... )
    
    >>> # Process and analyze results
    >>> results = network_data.calculate_results()
    >>> print(f"Connected buildings: {results['Anzahl angeschlossene Gebäude']}")
    >>> print(f"Annual heat demand: {results['Jahresgesamtwärmebedarf Gebäude [MWh/a]']:.1f} MWh/a")
    
    Notes
    -----
    Network Configuration Types:
        - **"kaltes Netz"** : Cold network with decentralized heat pumps at buildings
        - **"Niedertemperaturnetz"** : Low-temperature hot water network
        - **Traditional** : Standard hot water district heating network
        
    Temperature Control Strategies:
        - **"Statisch"** : Constant supply temperature operation
        - **"Gleitend"** : Weather-compensated sliding temperature control
        
    Data Flow:
        1. Input parameters define network topology and operation
        2. GeoJSON data provides geographic network layout
        3. JSON data contains building heat demands and temperatures
        4. Simulation results are stored in structured format
        5. Analysis methods calculate key performance indicators
        
    See Also
    --------
    SecondaryProducer : Secondary heat producer configuration
    initialize_geojson : Network initialization from GeoJSON data
    thermohydraulic_time_series_net : Time series simulation execution
    """
    
    # Input data for the network generation
    import_type: str
    flow_line_path: str
    return_line_path: str
    heat_consumer_path: str
    heat_generator_path: str
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

    def calculate_results(self) -> Dict[str, Union[int, float, None]]:
        """
        Calculate comprehensive key performance indicators for the district heating network.
        
        This method processes simulation results to calculate essential network performance
        metrics including energy flows, system efficiency, heat density, and distribution
        losses. It provides both absolute values and normalized indicators for network
        assessment and comparison.
        
        Returns
        -------
        Dict[str, Union[int, float, None]]
            Dictionary containing calculated performance indicators:
            
            - **"Anzahl angeschlossene Gebäude"** (int) : Number of connected buildings
            - **"Anzahl Heizzentralen"** (int) : Number of heat generation plants
            - **"Jahresgesamtwärmebedarf Gebäude [MWh/a]"** (float) : Annual building heat demand
            - **"max. Heizlast Gebäude [kW]"** (float) : Peak building heat load
            - **"Trassenlänge Wärmenetz [m]"** (float) : Total network pipe length
            - **"Wärmebedarfsdichte [MWh/(a*m)]"** (float) : Heat demand density
            - **"Anschlussdichte [kW/m]"** (float) : Connection density
            - **"Jahreswärmeerzeugung [MWh]"** (float) : Annual heat generation
            - **"Pumpenstrom [MWh]"** (float) : Annual pump electricity consumption
            - **"Verteilverluste [MWh]"** (float) : Annual distribution losses
            - **"rel. Verteilverluste [%]"** (float) : Relative distribution losses
            
        Notes
        -----
        Calculation Methods:
            - **Heat demand density** : Total annual demand divided by network length
            - **Connection density** : Peak load divided by network length
            - **Distribution losses** : Difference between generation and demand
            - **Pump consumption** : Calculated from mass flow and pressure data
            
        Data Requirements:
            - Network topology (self.net) must be available
            - Simulation results (self.pump_results) required for generation data
            - Heat demand data (self.waerme_ges_kW) needed for demand calculations
            
        Examples
        --------
        >>> # Calculate network performance indicators
        >>> network_data.net = initialized_network
        >>> network_data.pump_results = simulation_results
        >>> kpis = network_data.calculate_results()
        >>> 
        >>> # Display key metrics
        >>> print(f"Buildings connected: {kpis['Anzahl angeschlossene Gebäude']}")
        >>> print(f"Heat demand density: {kpis['Wärmebedarfsdichte [MWh/(a*m)]']:.2f} MWh/(a*m)")
        >>> print(f"Distribution losses: {kpis['rel. Verteilverluste [%]']:.1f}%")
        
        >>> # Check network efficiency
        >>> if kpis["rel. Verteilverluste [%]"] is not None:
        ...     if kpis["rel. Verteilverluste [%]"] < 15:
        ...         print("Network operates with acceptable losses")
        ...     else:
        ...         print("High distribution losses - consider optimization")
        
        See Also
        --------
        prepare_plot_data : Prepare data for visualization
        thermohydraulic_time_series_net : Run network simulation
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

        return results
    
    def prepare_plot_data(self) -> None:
        """
        Prepare and structure simulation data for visualization and plotting.
        
        This method processes simulation results into a standardized format suitable
        for various plotting libraries and visualization tools. It organizes data
        by plot type, assigns appropriate labels and axes, and handles time series
        alignment for multi-variable plots.
        
        Notes
        -----
        Plot Data Structure:
            Each entry contains:
            - **"data"** : numpy array with time series values
            - **"label"** : descriptive label for legends and axes
            - **"axis"** : preferred plot axis ("left" or "right")
            - **"time"** : corresponding time array for x-axis
            
        Generated Plot Categories:
            - **Heat demand data** : Building and heat exchanger demands
            - **Electrical data** : Heat pump power consumption (if applicable)
            - **Producer data** : Heat generation, mass flows, pressures, temperatures
            - **System pressures** : Supply and return pressures for all producers
            
        Data Handling:
            - Automatically detects cold network configuration (electrical data)
            - Handles multiple producers with indexed naming
            - Aligns time series data with simulation time steps
            - Maintains consistent units and formatting
            
        Examples
        --------
        >>> # Prepare data for plotting
        >>> network_data.prepare_plot_data()
        >>> 
        >>> # Access specific plot data
        >>> heat_demand = network_data.plot_data["Gesamtwärmebedarf Wärmeübertrager"]
        >>> print(f"Data shape: {heat_demand['data'].shape}")
        >>> print(f"Label: {heat_demand['label']}")
        >>> 
        >>> # Plot with matplotlib
        >>> import matplotlib.pyplot as plt
        >>> fig, ax1 = plt.subplots()
        >>> ax1.plot(heat_demand['time'], heat_demand['data'], 
        ...          label=heat_demand['label'])
        >>> ax1.set_ylabel(heat_demand['label'])
        
        >>> # Check available plot variables
        >>> print("Available plot data:")
        >>> for key in network_data.plot_data.keys():
        ...     print(f"  - {key}")
        
        See Also
        --------
        calculate_results : Calculate network KPIs
        thermohydraulic_time_series_net : Generate simulation results
        """
        # Initialize plot data with base heat demand
        self.plot_data = {
            "Gesamtwärmebedarf Wärmeübertrager": {
                "data": self.waerme_ges_kW,
                "label": "Wärmebedarf Wärmeübertrager in kW",
                "axis": "left",
                "time": self.yearly_time_steps
            }
        }
        
        # Add electrical data for cold networks
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