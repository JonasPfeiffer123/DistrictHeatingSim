"""
Pandapipes Time Series Simulation Module
========================================

This module provides comprehensive time series simulation capabilities for district heating
networks using the pandapipes framework.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-05-15

It handles the complete workflow of thermohydraulic
network simulation including controller updates, temperature control, pump operations, and
result processing for both static and dynamic network configurations.

The module supports various network configurations including cold networks with heat pumps,
traditional hot water networks, and hybrid systems with multiple heat generators. It includes
sophisticated temperature control strategies and comprehensive result analysis capabilities.
"""

from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Union, Any

from districtheatingsim.net_simulation_pandapipes.utilities import COP_WP
from districtheatingsim.net_simulation_pandapipes.controllers import MinimumSupplyTemperatureController
from districtheatingsim.utilities.test_reference_year import import_TRY

def update_heat_consumer_qext_controller(net, qext_w_profiles: List[np.ndarray], 
                                       time_steps: range, start: int, end: int) -> None:
    """
    Update constant controls with new data sources for time series simulation.

    This function updates the external heat demand controllers for all heat consumers
    in the network with time-dependent heat profiles. It creates pandas DataFrames
    with the heat demand data and assigns them as data sources to the corresponding
    ConstControl objects.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object containing all network components and controllers.
    qext_w_profiles : List[np.ndarray]
        List of external heat demand profiles for each heat consumer [W].
        Each array should have the same length as the simulation period.
    time_steps : range
        Range object defining the time steps for the current simulation period.
    start : int
        Start index for slicing the heat demand profiles.
    end : int
        End index for slicing the heat demand profiles.

    Notes
    -----
    - Updates only ConstControl objects with element 'heat_consumer' and variable 'qext_w'
    - Creates individual DataFrames for each heat consumer profile
    - Time steps must match the length of the sliced profiles
    - Heat demand values should be in Watts [W]

    Examples
    --------
    >>> # Update heat consumers for simulation period
    >>> heat_profiles = [np.array([5000, 6000, 4500]), np.array([3000, 3500, 2800])]
    >>> time_steps = range(0, 3)
    >>> update_heat_consumer_qext_controller(net, heat_profiles, time_steps, 0, 3)
    
    See Also
    --------
    update_heat_consumer_temperature_controller : Update temperature controllers
    update_heat_consumer_return_temperature_controller : Update return temperature controllers
    """
    for i, qext_w_profile in enumerate(qext_w_profiles):
        df = pd.DataFrame(index=time_steps, data={f'qext_w_{i}': qext_w_profile[start:end]})
        data_source = DFData(df)
        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ConstControl) and ctrl.element_index == i and ctrl.variable == 'qext_w':
                ctrl.data_source = data_source

def update_heat_consumer_temperature_controller(net, min_supply_temperature_heat_consumer: Union[np.ndarray, List], 
                                              time_steps: range, start: int, end: int) -> None:
    """
    Update minimum supply temperature controllers with new data sources for time series simulation.

    This function updates MinimumSupplyTemperatureController instances with time-dependent
    or static minimum supply temperature requirements. It handles both scalar values
    (constant temperatures) and time series arrays (variable temperatures).

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object.
    min_supply_temperature_heat_consumer : Union[np.ndarray, List]
        Minimum supply temperature profiles for heat consumers [°C].
        Can be scalar values, single-element arrays, or full time series.
    time_steps : range
        Range of time steps for the simulation.
    start : int
        Start index for slicing the temperature profiles.
    end : int
        End index for slicing the temperature profiles.

    Notes
    -----
    - Handles both static (scalar) and dynamic (array) temperature requirements
    - Automatically detects data type and creates appropriate time series
    - Temperature values should be in degrees Celsius [°C]
    - Updates only MinimumSupplyTemperatureController instances

    Examples
    --------
    >>> # Static temperature requirement
    >>> min_temp = [60.0, 55.0]  # °C for two consumers
    >>> update_heat_consumer_temperature_controller(net, min_temp, time_steps, 0, 100)
    
    >>> # Dynamic temperature requirement
    >>> min_temp = [np.array([60, 58, 62]), np.array([55, 53, 57])]
    >>> update_heat_consumer_temperature_controller(net, min_temp, time_steps, 0, 3)
    
    See Also
    --------
    MinimumSupplyTemperatureController : Custom temperature controller class
    """
    controller_count = 0
    for ctrl in net.controller.object.values:
        if isinstance(ctrl, MinimumSupplyTemperatureController):
            profile = min_supply_temperature_heat_consumer[controller_count]
            # Check if static or time-dependent
            if np.isscalar(profile) or (isinstance(profile, np.ndarray) and profile.ndim == 0):
                # Single value: repeat for all time steps
                values = np.full(len(time_steps), profile)
            elif isinstance(profile, np.ndarray) and profile.ndim == 1 and len(profile) == 1:
                values = np.full(len(time_steps), profile[0])
            else:
                # Time series: take correct slice
                values = profile[start:end]
            df_return_temp = pd.DataFrame(index=time_steps, data={
                'min_supply_temperature': values
            })
            data_source_return_temp = DFData(df_return_temp)
            ctrl.data_source = data_source_return_temp
            controller_count += 1

def update_heat_consumer_return_temperature_controller(net, return_temperature_heat_consumer: Union[np.ndarray, List], 
                                                     time_steps: range, start: int, end: int) -> None:
    """
    Update return temperature controllers with new data sources for time series simulation.

    This function updates ConstControl objects that control the return temperature
    of heat consumers. It handles both static and dynamic return temperature profiles
    and automatically converts temperatures from Celsius to Kelvin for internal use.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object.
    return_temperature_heat_consumer : Union[np.ndarray, List]
        Return temperature profiles for heat consumers [°C].
        Can be scalar values, single-element arrays, or full time series.
    time_steps : range
        Range of time steps for the simulation.
    start : int
        Start index for slicing the temperature profiles.
    end : int
        End index for slicing the temperature profiles.

    Notes
    -----
    - Automatically converts temperatures from °C to K (adds 273.15)
    - Handles both static and dynamic temperature profiles
    - Updates ConstControl objects with element='heat_consumer' and variable='treturn_k'
    - Creates individual controllers for each heat consumer

    Examples
    --------
    >>> # Static return temperatures
    >>> return_temps = [45.0, 40.0]  # °C
    >>> update_heat_consumer_return_temperature_controller(net, return_temps, time_steps, 0, 100)
    
    >>> # Dynamic return temperatures
    >>> return_temps = [np.array([45, 43, 47]), np.array([40, 38, 42])]
    >>> update_heat_consumer_return_temperature_controller(net, return_temps, time_steps, 0, 3)
    """
    for i, return_temp_profile in enumerate(return_temperature_heat_consumer):
        # Check if static or time-dependent
        if np.isscalar(return_temp_profile) or (isinstance(return_temp_profile, np.ndarray) and return_temp_profile.ndim == 0):
            # Single value: repeat for all time steps
            values = np.full(len(time_steps), return_temp_profile + 273.15)
        elif isinstance(return_temp_profile, np.ndarray) and return_temp_profile.ndim == 1 and len(return_temp_profile) == 1:
            values = np.full(len(time_steps), return_temp_profile[0] + 273.15)
        else:
            # Time series: take correct slice and convert
            values = return_temp_profile[start:end] + 273.15

        # Build DataFrame for all time steps
        df_return_temp = pd.DataFrame(index=time_steps, data={
            f'treturn_k_{i}': values
        })
        data_source_return_temp = DFData(df_return_temp)

        for ctrl in net.controller.object.values:
            if (isinstance(ctrl, ConstControl) and ctrl.element == 'heat_consumer' and ctrl.element_index == i and ctrl.variable == 'treturn_k'):
                # Update the data source of the existing ConstControl
                ctrl.data_source = data_source_return_temp

def update_secondary_producer_controller(net, secondary_producers: List[Any], 
                                       time_steps: range, start: int, end: int) -> None:
    """
    Update secondary producer controls with new data sources for time series simulation.

    This function updates mass flow controllers for secondary heat producers in the network.
    Secondary producers are additional heat sources that feed into the district heating
    network alongside the main heat generator.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object.
    secondary_producers : List[Dict[str, Any]]
        List of secondary producer configuration dictionaries.
        Each dictionary should contain 'index' and 'mass_flow' keys.
    time_steps : range
        Range of time steps for the simulation.
    start : int
        Start index for slicing the mass flow profiles.
    end : int
        End index for slicing the mass flow profiles.

    Notes
    -----
    - Updates both circulation pump mass controllers and flow control controllers
    - Each secondary producer requires an index and mass flow profile
    - Mass flow values should be in kg/s
    - Creates separate DataFrames for pump control and flow control

    Examples
    --------
    >>> # Define secondary producers
    >>> secondary_producers = [
    ...     {"index": 0, "mass_flow": np.array([1.5, 1.8, 1.2])},
    ...     {"index": 1, "mass_flow": np.array([2.0, 2.3, 1.7])}
    ... ]
    >>> update_secondary_producer_controller(net, secondary_producers, time_steps, 0, 3)

    See Also
    --------
    time_series_preprocessing : Calculates mass flow for secondary producers
    """
    for producer in secondary_producers:
        producer_index = producer.index if hasattr(producer, 'index') else 0
        mass_flow_data = producer.mass_flow if hasattr(producer, 'mass_flow') else np.zeros(len(time_steps))
        
        # Stelle sicher, dass mass_flow_data die richtige Form hat
        if np.isscalar(mass_flow_data):
            mass_flow_slice = np.full(len(time_steps), mass_flow_data)
        elif isinstance(mass_flow_data, np.ndarray):
            mass_flow_slice = mass_flow_data[start:end]
        else:
            mass_flow_slice = np.full(len(time_steps), mass_flow_data)

        print(f"Mass flow for secondary producer {producer_index}: {mass_flow_slice}")
        
        df_secondary_producer = pd.DataFrame(index=time_steps, data={
            f'mdot_flow_kg_per_s_{producer_index}': mass_flow_slice
        })
        data_source_secondary_producer = DFData(df_secondary_producer)

        df_secondary_producer_flow_control = pd.DataFrame(index=time_steps, data={
            f'controlled_mdot_kg_per_s_{producer_index}': mass_flow_slice
        })
        data_source_secondary_producer_flow_control = DFData(df_secondary_producer_flow_control)

        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ConstControl) and ctrl.element == 'circ_pump_mass' and ctrl.variable == 'mdot_flow_kg_per_s':
                ctrl.data_source = data_source_secondary_producer
            elif isinstance(ctrl, ConstControl) and ctrl.element == 'flow_control' and ctrl.variable == 'controlled_mdot_kg_per_s':
                ctrl.data_source = data_source_secondary_producer_flow_control
            
def update_heat_generator_supply_temperature_controller(net, supply_temperature: np.ndarray, 
                                                      time_steps: range, start: int, end: int) -> None:
    """
    Update supply temperature controls with new data sources for time series simulation.

    This function updates the supply temperature controllers for heat generators
    (both pressure and mass circulation pumps) with time-dependent temperature profiles.
    It automatically converts temperatures from Celsius to Kelvin.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object.
    supply_temperature : np.ndarray
        Supply temperature profile for heat generators [°C].
    time_steps : range
        Range of time steps for the simulation.
    start : int
        Start index for slicing the temperature profile.
    end : int
        End index for slicing the temperature profile.

    Notes
    -----
    - Automatically converts temperatures from °C to K (adds 273.15)
    - Updates both circulation pump pressure and mass controllers
    - Temperature profile should cover the entire simulation period
    - Used for implementing sliding supply temperature control strategies

    Examples
    --------
    >>> # Supply temperature profile for sliding control
    >>> supply_temp = np.array([80, 78, 82, 75, 73])  # °C
    >>> update_heat_generator_supply_temperature_controller(net, supply_temp, time_steps, 0, 5)

    See Also
    --------
    time_series_preprocessing : Calculates supply temperature profiles
    """
    if np.isscalar(supply_temperature):
        # If a single value is provided, repeat it for all time steps
        supply_temperature = np.full(len(time_steps), supply_temperature)

    # Create the DataFrame for the supply temperature
    df_supply_temp = pd.DataFrame(index=time_steps, data={'supply_temperature': supply_temperature[start:end] + 273.15})
    data_source_supply_temp = DFData(df_supply_temp)
    for ctrl in net.controller.object.values:
        if isinstance(ctrl, ConstControl) and ctrl.element == 'circ_pump_pressure' and ctrl.variable == 't_flow_k':
            ctrl.data_source = data_source_supply_temp
        elif isinstance(ctrl, ConstControl) and ctrl.element == 'circ_pump_mass' and ctrl.variable == 't_flow_k':
            ctrl.data_source = data_source_supply_temp

def create_log_variables(net) -> List[Tuple[str, str]]:
    """
    Create a list of variables to log during the time series simulation.

    This function defines which network variables should be logged during
    the time series simulation. It automatically adapts the logging configuration
    based on the available network components.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object to analyze for available components.

    Returns
    -------
    List[Tuple[str, str]]
        List of tuples where each tuple contains (table_name, variable_name)
        representing the variables to be logged during simulation.

    Notes
    -----
    - Always logs junction pressures, temperatures, and heat consumer data
    - Conditionally logs circulation pump mass data if available
    - Results are stored in the OutputWriter for post-processing
    - Logged variables are essential for result analysis and validation

    Examples
    --------
    >>> log_vars = create_log_variables(net)
    >>> print(f"Logging {len(log_vars)} variables")
    >>> for table, var in log_vars:
    ...     print(f"  {table}.{var}")

    See Also
    --------
    pandapower.timeseries.OutputWriter : Handles result logging
    """
    log_variables = [
        ('res_junction', 'p_bar'),
        ('res_junction', 't_k'),
        ('heat_consumer', 'qext_w'),
        ('res_heat_consumer', 'vdot_m3_per_s'),
        ('res_heat_consumer', 't_from_k'),
        ('res_heat_consumer', 't_to_k'),
        ('res_heat_consumer', 'mdot_from_kg_per_s'),
        ('res_circ_pump_pressure', 'mdot_from_kg_per_s'),
        ('res_circ_pump_pressure', 'p_to_bar'),
        ('res_circ_pump_pressure', 'p_from_bar'),
        ('res_circ_pump_pressure', 't_to_k'),
        ('res_circ_pump_pressure', 't_from_k')
    ]

    if 'circ_pump_mass' in net:
        log_variables.extend([
            ('res_circ_pump_mass', 'mdot_from_kg_per_s'),
            ('res_circ_pump_mass', 'p_to_bar'),
            ('res_circ_pump_mass', 'p_from_bar'),
            ('res_circ_pump_mass', 't_to_k'),
            ('res_circ_pump_mass', 't_from_k')
        ])

    return log_variables

def time_series_preprocessing(NetworkGenerationData) -> Any:
    """
    Preprocess time series data for the thermal and hydraulic network simulation.

    This function performs comprehensive preprocessing of network data including
    temperature control strategy implementation, heat pump coefficient of performance
    calculations, and mass flow calculations for secondary producers. It handles
    different network configurations and temperature control modes.

    Parameters
    ----------
    NetworkGenerationData : object
        Network generation data object containing all necessary simulation parameters
        including network configuration, temperature profiles, heat demands, and
        control strategies.

    Returns
    -------
    NetworkGenerationData
        Updated NetworkGenerationData object with preprocessed time series data
        including calculated supply temperatures, adjusted heat demands, and
        prepared controller data.

    Notes
    -----
    - Implements both static and sliding supply temperature control
    - Handles cold network configurations with heat pump calculations
    - Calculates COP-based power consumption for heat pumps
    - Applies minimum load constraints (2% of maximum)
    - Calculates mass flows for secondary heat producers
    - Converts power values from W to kW for network simulation

    Network Configuration Types:
        - "kaltes Netz": Cold network with decentralized heat pumps
        - Traditional hot water networks with central heat generation
        - Hybrid systems with multiple heat sources

    Temperature Control Strategies:
        - "Statisch": Constant supply temperature
        - "Gleitend": Outdoor temperature-dependent sliding control

    Examples
    --------
    >>> # Preprocess network data for simulation
    >>> processed_data = time_series_preprocessing(network_data)
    >>> print(f"Total heat demand: {np.sum(processed_data.waerme_ges_kW):.1f} kW")
    >>> print(f"Supply temperature control: {processed_data.supply_temperature_control}")

    See Also
    --------
    COP_WP : Heat pump coefficient of performance calculation
    import_TRY : Weather data import for sliding temperature control
    """
    print(f"Maximale Vorlauftemperatur Netz: {NetworkGenerationData.max_supply_temperature_heat_generator} °C")
    print(f"Mindestvorlauftemperatur HAST: {NetworkGenerationData.min_supply_temperature_heat_consumer} °C")
    print(f"Rücklauftemperatur HAST: {NetworkGenerationData.return_temperature_heat_consumer} °C")
    print(f"Vorlauftemperatur Gebäude: {NetworkGenerationData.supply_temperature_buildings} °C")
    print(f"Rücklauftemperatur Gebäude: {NetworkGenerationData.return_temperature_buildings} °C")
    print(f"building_temperature_checked: {NetworkGenerationData.building_temperature_checked}")
    print(f"Netconfiguration: {NetworkGenerationData.netconfiguration}")

    COP_file_values = np.genfromtxt(NetworkGenerationData.COP_filename, delimiter=';')

    # Supply temperature control strategy implementation
    if NetworkGenerationData.supply_temperature_control == "Statisch":
        NetworkGenerationData.supply_temperature_heat_generator = NetworkGenerationData.max_supply_temperature_heat_generator # Type: float in °C
    
    if NetworkGenerationData.supply_temperature_control == "Gleitend":
        air_temperature_data, _, _, _, _ = import_TRY(NetworkGenerationData.TRY_filename)

        # Calculate slope of linear equation for sliding control
        slope = (NetworkGenerationData.max_supply_temperature_heat_generator - NetworkGenerationData.min_supply_temperature_heat_generator) / (NetworkGenerationData.min_air_temperature_heat_generator - NetworkGenerationData.max_air_temperature_heat_generator)

        air_temperature_data = np.array(air_temperature_data)
        NetworkGenerationData.supply_temperature_heat_generator = np.where(
            air_temperature_data <= NetworkGenerationData.min_air_temperature_heat_generator,
            NetworkGenerationData.max_supply_temperature_heat_generator,
            np.where(
                air_temperature_data >= NetworkGenerationData.max_air_temperature_heat_generator,
                NetworkGenerationData.min_supply_temperature_heat_generator,
                NetworkGenerationData.max_supply_temperature_heat_generator + slope * (air_temperature_data - NetworkGenerationData.min_air_temperature_heat_generator)
            )
        )
    print(f"Vorlauftemperatur Netz: {NetworkGenerationData.supply_temperature_heat_generator} °C")

    # Temperature processing based on network configuration
    ### if building_temperature_checked is True, the time dependent building temperatures are used
    ### if netconfiguration is not "kaltes Netz", no changes are made to the heat demand and no power consumption is calculated
    if NetworkGenerationData.building_temperature_checked == True and NetworkGenerationData.netconfiguration != "kaltes Netz":
        NetworkGenerationData.min_supply_temperature_heat_consumer = NetworkGenerationData.supply_temperature_buildings_curve + NetworkGenerationData.dT_RL
        NetworkGenerationData.return_temperature_heat_consumer = NetworkGenerationData.return_temperature_buildings_curve + NetworkGenerationData.dT_RL

    ### if building_temperature_checked is True, the time dependent building temperatures are used
    ### if netconfiguration is "kaltes Netz", the heat demand and power consumption are calculated using the COP calculation
    elif NetworkGenerationData.building_temperature_checked == True and NetworkGenerationData.netconfiguration == "kaltes Netz":
        NetworkGenerationData.min_supply_temperature_heat_consumer = NetworkGenerationData.return_temperature_heat_consumer + NetworkGenerationData.dT_RL
        NetworkGenerationData.return_temperature_heat_consumer = NetworkGenerationData.return_temperature_buildings_curve + NetworkGenerationData.dT_RL

        # Calculate COP, electricity consumption, and adjusted heat demand
        cop, _ = COP_WP(NetworkGenerationData.supply_temperature_buildings_curve, NetworkGenerationData.return_temperature_heat_consumer, COP_file_values)
        strom_wp = NetworkGenerationData.waerme_hast_ges_W / cop
        waerme_hast = NetworkGenerationData.waerme_hast_ges_W - strom_wp

        NetworkGenerationData.waerme_hast_ges_W = waerme_hast
        NetworkGenerationData.strombedarf_hast_ges_W = strom_wp
    ### if building_temperature_checked is False, the time dependent building temperatures are not used
    ### if netconfiguration is not "kaltes Netz", the heat demand and power consumption are calculated using the COP calculation
    elif NetworkGenerationData.building_temperature_checked == False and NetworkGenerationData.netconfiguration == "kaltes Netz":
        cop, _ = COP_WP(NetworkGenerationData.supply_temperature_buildings, NetworkGenerationData.return_temperature_heat_consumer, COP_file_values)

        strom_wp = NetworkGenerationData.waerme_hast_ges_W / cop
        waerme_hast = NetworkGenerationData.waerme_hast_ges_W - strom_wp

        NetworkGenerationData.waerme_hast_ges_W = waerme_hast
        NetworkGenerationData.strombedarf_hast_ges_W = strom_wp

    # Apply minimum load constraints (2% of maximum)
    max_heat = np.max(NetworkGenerationData.waerme_hast_ges_W)
    max_power = np.max(NetworkGenerationData.strombedarf_hast_ges_W)
    NetworkGenerationData.waerme_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_heat, NetworkGenerationData.waerme_hast_ges_W)
    NetworkGenerationData.strombedarf_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_power, NetworkGenerationData.strombedarf_hast_ges_W)

    # Convert power values from W to kW
    NetworkGenerationData.waerme_hast_ges_kW = np.where(NetworkGenerationData.waerme_hast_ges_W == 0, 0, NetworkGenerationData.waerme_hast_ges_W / 1000)
    NetworkGenerationData.strombedarf_hast_ges_kW = np.where(NetworkGenerationData.strombedarf_hast_ges_W == 0, 0, NetworkGenerationData.strombedarf_hast_ges_W / 1000)

    # Calculate total heat and electricity demand profiles
    NetworkGenerationData.waerme_ges_kW = np.sum(NetworkGenerationData.waerme_hast_ges_kW, axis=0)
    NetworkGenerationData.strombedarf_ges_kW = np.sum(NetworkGenerationData.strombedarf_hast_ges_kW, axis=0)

    # Calculate mass flow for secondary producers
    if NetworkGenerationData.secondary_producers:
        # Calculate mass flow with cp = 4.18 kJ/kgK
        cp = 4.18  # kJ/kgK
        avg_return_temperature = np.mean(NetworkGenerationData.return_temperature_heat_consumer)
        mass_flow = NetworkGenerationData.waerme_ges_kW / (cp * (NetworkGenerationData.supply_temperature_heat_generator - avg_return_temperature))  # kW / (kJ/kgK * K) = kg/s

        print(f"Mass flow of main producer: {mass_flow} kg/s")

        # Update each secondary producer's dictionary with calculated mass flow
        for secondary_producer in NetworkGenerationData.secondary_producers:
            secondary_producer.mass_flow = secondary_producer.load_percentage/100 * mass_flow
            print(f"Mass flow of secondary producer {secondary_producer.index}: {secondary_producer.mass_flow} kg/s")

    return NetworkGenerationData
    
def thermohydraulic_time_series_net(NetworkGenerationData) -> Any:
    """
    Run a thermohydraulic time series simulation for the district heating network.

    This function orchestrates the complete time series simulation workflow including
    controller updates, network solving, and result collection. It handles different
    network configurations and control strategies automatically.

    Parameters
    ----------
    NetworkGenerationData : object
        Network generation data object containing the preprocessed network model,
        time series data, and simulation parameters.

    Returns
    -------
    NetworkGenerationData
        Updated NetworkGenerationData object with simulation results including
        network states, pump operations, and performance metrics.

    Notes
    -----
    - Updates all relevant controllers before simulation
    - Runs bidirectional thermohydraulic simulation
    - Uses adaptive iteration limits for convergence
    - Collects comprehensive result data for analysis
    - Handles both static and dynamic control strategies

    Simulation Features:
        - Bidirectional flow calculation
        - Temperature and pressure coupling
        - Dynamic controller updates
        - Comprehensive result logging
        - Convergence monitoring

    Examples
    --------
    >>> # Run complete time series simulation
    >>> results = thermohydraulic_time_series_net(network_data)
    >>> print(f"Simulation completed for {len(results.pump_results)} time steps")
    >>> 
    >>> # Access pump results
    >>> main_pump = results.pump_results["Heizentrale Haupteinspeisung"][0]
    >>> print(f"Max heat generation: {np.max(main_pump['qext_kW']):.1f} kW")

    See Also
    --------
    run_time_series.run_timeseries : pandapipes time series solver
    calculate_results : Result processing and structuring
    """
    # Update the ConstControl
    time_steps = range(0, len(NetworkGenerationData.waerme_hast_ges_W[0][NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step]))
    
    update_heat_consumer_qext_controller(NetworkGenerationData.net, NetworkGenerationData.waerme_hast_ges_W, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)

    # Update secondary producer controls
    if NetworkGenerationData.secondary_producers:
        update_secondary_producer_controller(NetworkGenerationData.net, NetworkGenerationData.secondary_producers, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)

    # Update temperature controllers if applicable
    if NetworkGenerationData.min_supply_temperature_heat_consumer is not None and np.any(np.array(NetworkGenerationData.min_supply_temperature_heat_consumer) != 0) and isinstance(NetworkGenerationData.min_supply_temperature_heat_consumer, np.ndarray):
        print("Update TemperatureController")
        update_heat_consumer_temperature_controller(NetworkGenerationData.net, NetworkGenerationData.min_supply_temperature_heat_consumer, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)
    
    if NetworkGenerationData.return_temperature_heat_consumer is not None and isinstance(NetworkGenerationData.return_temperature_heat_consumer, np.ndarray):
        print("Update Return Temperature Const Control")
        update_heat_consumer_return_temperature_controller(NetworkGenerationData.net, NetworkGenerationData.return_temperature_heat_consumer, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)

    # Update supply temperature controller if dynamic
    if NetworkGenerationData.supply_temperature_heat_generator is not None and isinstance(NetworkGenerationData.supply_temperature_heat_generator, np.ndarray):
        update_heat_generator_supply_temperature_controller(NetworkGenerationData.net, NetworkGenerationData.supply_temperature_heat_generator, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)
    
    if NetworkGenerationData.supply_temperature_control == "Statisch":
        # Erstelle Array für statische Temperatur
        static_temp_array = np.full(len(time_steps), NetworkGenerationData.supply_temperature_heat_generator)
        update_heat_generator_supply_temperature_controller(NetworkGenerationData.net, 
                                            static_temp_array, 
                                            time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)

    # Configure logging and run simulation
    log_variables = create_log_variables(NetworkGenerationData.net)
    ow = OutputWriter(NetworkGenerationData.net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(NetworkGenerationData.net, time_steps, mode="bidirectional", iter=100, alpha=0.5)
    
    NetworkGenerationData.net_results = ow.np_results
    NetworkGenerationData.pump_results = calculate_results(NetworkGenerationData.net, NetworkGenerationData.net_results)
    
    return NetworkGenerationData

def calculate_results(net, net_results: Dict, cp_kJ_kgK: float = 4.2) -> Dict[str, Dict[int, Dict[str, np.ndarray]]]:
    """
    Calculate and structure the thermohydraulic simulation results.

    This function processes the raw simulation results from pandapipes and structures
    them into a comprehensive format for analysis and visualization. It calculates
    derived quantities such as heat generation rates and pressure differences.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object containing component definitions.
    net_results : Dict
        Raw results dictionary from the time series simulation containing
        all logged variables and their time series values.
    cp_kJ_kgK : float, optional
        Specific heat capacity of water [kJ/kg·K]. Default is 4.2.

    Returns
    -------
    Dict[str, Dict[int, Dict[str, np.ndarray]]]
        Structured results dictionary with the following hierarchy:
        
        - Level 1: Producer type ("Heizentrale Haupteinspeisung", "weitere Einspeisung")
        - Level 2: Producer index (0, 1, 2, ...)
        - Level 3: Parameter name with time series arrays:
            - "mass_flow": Mass flow rate [kg/s]
            - "flow_pressure": Supply pressure [bar]
            - "return_pressure": Return pressure [bar]
            - "deltap": Pressure difference [bar]
            - "return_temp": Return temperature [°C]
            - "flow_temp": Supply temperature [°C]
            - "qext_kW": Heat generation rate [kW]

    Notes
    -----
    - Automatically converts temperatures from Kelvin to Celsius
    - Calculates heat generation from mass flow and temperature difference
    - Handles both pressure pumps (main) and mass pumps (secondary)
    - Results maintain time series structure for temporal analysis

    Examples
    --------
    >>> results = calculate_results(net, simulation_results)
    >>> 
    >>> # Access main heat generator results
    >>> main_gen = results["Heizentrale Haupteinspeisung"][0]
    >>> max_heat = np.max(main_gen["qext_kW"])
    >>> print(f"Maximum heat generation: {max_heat:.1f} kW")
    >>> 
    >>> # Plot temperature profile
    >>> import matplotlib.pyplot as plt
    >>> plt.plot(main_gen["flow_temp"], label="Supply")
    >>> plt.plot(main_gen["return_temp"], label="Return")

    See Also
    --------
    save_results_csv : Export results to CSV format
    import_results_csv : Import results from CSV files
    """
    # Prepare data structure
    pump_results = {
        "Heizentrale Haupteinspeisung": {},
        "weitere Einspeisung": {}
    }

    # Add results for the Pressure Pump (main heat generator)
    if 'circ_pump_pressure' in net:
        for idx, row in net.circ_pump_pressure.iterrows():
            pump_results["Heizentrale Haupteinspeisung"][idx] = {
                "mass_flow": net_results["res_circ_pump_pressure.mdot_from_kg_per_s"][:, 0],
                "flow_pressure": net_results["res_circ_pump_pressure.p_to_bar"][:, idx],
                "return_pressure": net_results["res_circ_pump_pressure.p_from_bar"][:, idx],
                "deltap": net_results["res_circ_pump_pressure.p_to_bar"][:, idx] - net_results["res_circ_pump_pressure.p_from_bar"][:, idx],
                "return_temp": net_results["res_circ_pump_pressure.t_from_k"][:, idx] - 273.15,
                "flow_temp": net_results["res_circ_pump_pressure.t_to_k"][:, idx] - 273.15,
                "qext_kW": net_results["res_circ_pump_pressure.mdot_from_kg_per_s"][:, idx] * cp_kJ_kgK * (net_results["res_circ_pump_pressure.t_to_k"][:, idx] - net_results["res_circ_pump_pressure.t_from_k"][:, idx])
            }

    # Add results for the Mass Pumps (secondary producers)
    if 'circ_pump_mass' in net:
        for idx, row in net.circ_pump_mass.iterrows():
            pump_results["weitere Einspeisung"][idx] = {
                "mass_flow": net_results["res_circ_pump_mass.mdot_from_kg_per_s"][:, idx],
                "flow_pressure": net_results["res_circ_pump_mass.p_to_bar"][:, idx],
                "return_pressure": net_results["res_circ_pump_mass.p_from_bar"][:, idx],
                "deltap": net_results["res_circ_pump_mass.p_to_bar"][:, idx] - net_results["res_circ_pump_mass.p_from_bar"][:, idx],
                "return_temp": net_results["res_circ_pump_mass.t_from_k"][:, idx] - 273.15,
                "flow_temp": net_results["res_circ_pump_mass.t_to_k"][:, idx] - 273.15,
                "qext_kW": net_results["res_circ_pump_mass.mdot_from_kg_per_s"][:, idx] * cp_kJ_kgK * (net_results["res_circ_pump_mass.t_to_k"][:, idx] - net_results["res_circ_pump_mass.t_from_k"][:, idx])
            }

    return pump_results

def save_results_csv(time_steps: np.ndarray, total_heat_KW: np.ndarray, strom_wp_kW: np.ndarray, 
                    pump_results: Dict, filename: str) -> None:
    """
    Save the thermohydraulic simulation results to a CSV file.

    This function exports comprehensive simulation results to a CSV file with
    German column headers and semicolon separation for compatibility with
    German Excel installations and further analysis tools.

    Parameters
    ----------
    time_steps : np.ndarray
        Array of time step values (typically datetime objects).
    total_heat_KW : np.ndarray
        Total building heat demand time series [kW].
    strom_wp_kW : np.ndarray
        Heat pump electrical consumption time series [kW].
    pump_results : Dict
        Structured pump results from calculate_results function.
    filename : str
        Path to the output CSV file.

    Notes
    -----
    - Uses German column names for compatibility
    - Semicolon separated values (CSV) format
    - Includes comprehensive pump operation data
    - Maintains time series structure with timestamps
    - Compatible with German regional settings

    CSV Structure:
        - Zeit: Time stamps
        - Gesamtwärmebedarf_Gebäude_kW: Total building heat demand
        - Gesamtheizlast_Gebäude_kW: Total building heating load
        - Gesamtstrombedarf_Wärmepumpen_Gebäude_kW: Total heat pump power
        - Wärmeerzeugung_[type]_[index]_kW: Heat generation by producer
        - Massenstrom_[type]_[index]_kg/s: Mass flow rates
        - Delta p_[type]_[index]_bar: Pressure differences
        - Vorlauftemperatur_[type]_[index]_°C: Supply temperatures
        - Rücklauftemperatur_[type]_[index]_°C: Return temperatures
        - [Vorlauf/Rücklauf]druck_[type]_[index]_bar: Pressures

    Examples
    --------
    >>> # Save simulation results
    >>> save_results_csv(time_array, heat_demand, power_consumption, 
    ...                  pump_data, "simulation_results.csv")
    >>> 
    >>> # Verify saved file
    >>> import pandas as pd
    >>> df = pd.read_csv("simulation_results.csv", sep=';')
    >>> print(f"Saved {len(df)} time steps with {len(df.columns)} variables")

    See Also
    --------
    import_results_csv : Import results from CSV files
    calculate_results : Generate pump results structure
    """
    # Convert arrays to pandas DataFrame
    df = pd.DataFrame({
        'Zeit': time_steps,
        'Gesamtwärmebedarf_Gebäude_kW': total_heat_KW,
        'Gesamtheizlast_Gebäude_kW': total_heat_KW + strom_wp_kW,
        'Gesamtstrombedarf_Wärmepumpen_Gebäude_kW': strom_wp_kW
    })

    # Add pump data columns
    for pump_type, pumps in pump_results.items():
        for idx, pump_data in pumps.items():
            df[f"Wärmeerzeugung_{pump_type}_{idx+1}_kW"] = pump_data['qext_kW']
            df[f'Massenstrom_{pump_type}_{idx+1}_kg/s'] = pump_data['mass_flow']
            df[f'Delta p_{pump_type}_{idx+1}_bar'] = pump_data['deltap']
            df[f'Vorlauftemperatur_{pump_type}_{idx+1}_°C'] = pump_data['flow_temp']
            df[f'Rücklauftemperatur_{pump_type}_{idx+1}_°C'] = pump_data['return_temp']
            df[f"Vorlaufdruck_{pump_type}_{idx+1}_bar"] = pump_data['flow_pressure']
            df[f"Rücklaufdruck_{pump_type}_{idx+1}_bar"] = pump_data['return_pressure']

    # Save DataFrame as CSV with German formatting
    df.to_csv(filename, sep=';', date_format='%Y-%m-%d %H:%M:%S', index=False, encoding='utf-8-sig')

def import_results_csv(filename: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
    """
    Import thermohydraulic simulation results from a CSV file.

    This function reads and parses CSV files created by save_results_csv,
    reconstructing the original data structure for further analysis or
    visualization. It handles the German CSV format and column naming.

    Parameters
    ----------
    filename : str
        Path to the input CSV file containing simulation results.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]
        A tuple containing:
        
        - **time_steps** (np.ndarray) : Time step array as datetime64 objects
        - **total_heat_KW** (np.ndarray) : Total building heat demand [kW]
        - **strom_wp_kW** (np.ndarray) : Heat pump power consumption [kW]
        - **pump_results** (Dict) : Structured pump results matching calculate_results format

    Raises
    ------
    FileNotFoundError
        If the specified CSV file cannot be found.
    pd.errors.ParserError
        If the CSV file format is invalid or corrupted.
    KeyError
        If required columns are missing from the CSV file.

    Notes
    -----
    - Automatically parses German CSV format (semicolon separated)
    - Reconstructs the hierarchical pump results structure
    - Handles datetime parsing for time stamps
    - Converts data types to appropriate numpy arrays
    - Validates column naming and structure

    Examples
    --------
    >>> # Import previously saved results
    >>> time_data, heat_data, power_data, pump_data = import_results_csv("results.csv")
    >>> 
    >>> # Analyze imported data
    >>> print(f"Time period: {time_data[0]} to {time_data[-1]}")
    >>> print(f"Max heat demand: {np.max(heat_data):.1f} kW")
    >>> 
    >>> # Access specific pump data  
    >>> main_pump = pump_data["Heizentrale Haupteinspeisung"][0]
    >>> avg_supply_temp = np.mean(main_pump["flow_temp"])

    See Also
    --------
    save_results_csv : Export results to CSV format
    calculate_results : Original result structure generation
    """
    # Load data from CSV file
    data = pd.read_csv(filename, sep=';', parse_dates=['Zeit'])

    # Extract general time series and heat data
    time_steps = data["Zeit"].values.astype('datetime64')
    total_heat_KW = data["Gesamtwärmebedarf_Gebäude_kW"].values.astype('float64')
    strom_wp_kW = data["Gesamtstrombedarf_Wärmepumpen_Gebäude_kW"].values.astype('float64')

    # Create dictionary to store pump data
    pump_results = {}

    # Mapping of German column prefixes to result keys
    pump_data = {
        'Wärmeerzeugung': 'qext_kW',
        'Massenstrom': 'mass_flow',
        'Delta p': 'deltap',
        'Vorlauftemperatur': 'flow_temp',
        'Rücklauftemperatur': 'return_temp',
        'Vorlaufdruck': 'flow_pressure',
        'Rücklaufdruck': 'return_pressure'
    }

    # Parse pump data columns
    for column in data.columns:
        if any(prefix in column for prefix in ['Wärmeerzeugung', 'Massenstrom', 'Delta p', 'Vorlauftemperatur', 'Rücklauftemperatur', 'Vorlaufdruck', 'Rücklaufdruck']):
            parts = column.split('_')
            if len(parts) >= 4:
                # Expected structure: [prefix, pump_type, index, parameter]
                prefix, pump_type, idx, parameter = parts[0], parts[1], int(parts[2])-1, "_".join(parts[3:])

                value = pump_data[prefix]

                # Initialize nested dictionary structure
                if pump_type not in pump_results:
                    pump_results[pump_type] = {}
                if idx not in pump_results[pump_type]:
                    pump_results[pump_type][idx] = {}

                # Add parameter data to corresponding pump
                pump_results[pump_type][idx][value] = data[column].values.astype('float64')
            else:
                print(f"Warning: Column name '{column}' has an unexpected format and is ignored.")

    return time_steps, total_heat_KW, strom_wp_kW, pump_results