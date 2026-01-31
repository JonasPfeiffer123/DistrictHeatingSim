"""
Pandapipes time series simulation for district heating networks including controller updates,
temperature control, and result processing.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
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
    Update external heat demand controllers with time-dependent profiles.
    
    :param net: Pandapipes network with controllers
    :type net: pandapipes.pandapipesNet
    :param qext_w_profiles: List of heat demand profiles for each consumer [W]
    :type qext_w_profiles: List[np.ndarray]
    :param time_steps: Time steps for simulation period
    :type time_steps: range
    :param start: Start index for slicing profiles
    :type start: int
    :param end: End index for slicing profiles
    :type end: int
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
    Update minimum supply temperature controllers with static or time-dependent profiles.
    
    :param net: Pandapipes network object
    :type net: pandapipes.pandapipesNet
    :param min_supply_temperature_heat_consumer: Min supply temperature profiles [°C]
    :type min_supply_temperature_heat_consumer: Union[np.ndarray, List]
    :param time_steps: Time steps range
    :type time_steps: range
    :param start: Start index for slicing
    :type start: int
    :param end: End index for slicing
    :type end: int
    
    .. note::
       Handles both scalar (static) and array (dynamic) temperature requirements.
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
    Update return temperature controllers with static or dynamic profiles.
    
    :param net: Pandapipes network object
    :type net: pandapipes.pandapipesNet
    :param return_temperature_heat_consumer: Return temperature profiles [°C]
    :type return_temperature_heat_consumer: Union[np.ndarray, List]
    :param time_steps: Time steps range
    :type time_steps: range
    :param start: Start index for slicing
    :type start: int
    :param end: End index for slicing
    :type end: int
    
    .. note::
       Automatically converts temperatures from °C to K (adds 273.15).
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
    Update secondary producer mass flow controllers for time series simulation.
    
    :param net: Pandapipes network object
    :type net: pandapipes.pandapipesNet
    :param secondary_producers: List of producer configs with index and mass_flow
    :type secondary_producers: List[Any]
    :param time_steps: Time steps range
    :type time_steps: range
    :param start: Start index for slicing
    :type start: int
    :param end: End index for slicing
    :type end: int
    
    .. note::
       Updates both circ_pump_mass and flow_control controllers for each producer.
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
    Update supply temperature controllers for heat generators with time-dependent profiles.
    
    :param net: Pandapipes network object
    :type net: pandapipes.pandapipesNet
    :param supply_temperature: Supply temperature profile [°C]
    :type supply_temperature: np.ndarray
    :param time_steps: Time steps range
    :type time_steps: range
    :param start: Start index for slicing
    :type start: int
    :param end: End index for slicing
    :type end: int
    
    .. note::
       Converts °C to K, updates both circ_pump_pressure and circ_pump_mass controllers.
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
    Create list of variables to log during time series simulation.
    
    :param net: Pandapipes network to analyze for available components
    :type net: pandapipes.pandapipesNet
    :return: List of (table_name, variable_name) tuples to log
    :rtype: List[Tuple[str, str]]
    
    .. note::
       Logs junction pressures/temperatures, heat consumer data, and conditionally circ_pump_mass.
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
    Preprocess time series data including temperature control and COP calculations.
    
    :param NetworkGenerationData: Network data with simulation parameters and profiles
    :type NetworkGenerationData: object
    :return: Updated NetworkGenerationData with preprocessed time series
    :rtype: Any
    
    .. note::
       Implements static/sliding temperature control, COP calculations for cold networks,
       applies 2% minimum load, calculates secondary producer mass flows. Converts W to kW.
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
    Run thermohydraulic time series simulation with controller updates.
    
    :param NetworkGenerationData: Network data with preprocessed model and parameters
    :type NetworkGenerationData: object
    :return: Updated NetworkGenerationData with simulation results and pump operations
    :rtype: Any
    
    .. note::
       Runs bidirectional simulation with iter=100, alpha=0.5. Updates all controllers
       (heat demand, temperatures, secondary producers). Logs junction, heat consumer,
       and pump data.
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

def simplified_time_series_net(NetworkGenerationData) -> Any:
    """
    Run simplified time series by scaling design state with building heat demand.
    
    :param NetworkGenerationData: Network data with design state from initialization
    :type NetworkGenerationData: object
    :return: Updated NetworkGenerationData with scaled load profiles
    :rtype: Any
    
    .. note::
       No pipeflow calculation. Uses design state from net.res_*, scales with demand.
       Constant temperatures/pressures from design. Losses scaled proportionally.
       Much faster than thermohydraulic_time_series_net.
    """
    
    print("Starte vereinfachte Zeitreihenberechnung (basierend auf Auslegung)...")
    
    # Get time steps for selected simulation range
    time_steps = range(0, len(NetworkGenerationData.waerme_hast_ges_W[0][NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step]))
    n_steps = len(time_steps)
    
    # Find design point (maximum load)
    max_load_idx = np.argmax(NetworkGenerationData.waerme_ges_kW)
    total_building_demand_design = NetworkGenerationData.waerme_ges_kW[max_load_idx]
    
    print(f"Nutze Auslegungszustand bei max. Last: {total_building_demand_design:.1f} kW")
    
    # Extract design state results from already calculated network
    # (these were calculated during initialization)
    design_results = {
        "Heizentrale Haupteinspeisung": {},
        "weitere Einspeisung": {}
    }
    
    # Get design state from pressure pumps (main generators)
    if hasattr(NetworkGenerationData.net, 'res_circ_pump_pressure') and len(NetworkGenerationData.net.res_circ_pump_pressure) > 0:
        for idx in NetworkGenerationData.net.res_circ_pump_pressure.index:
            res = NetworkGenerationData.net.res_circ_pump_pressure.loc[idx]
            design_results["Heizentrale Haupteinspeisung"][idx] = {
                "mass_flow_design": res["mdot_from_kg_per_s"],
                "flow_pressure_design": res["p_to_bar"],
                "return_pressure_design": res["p_from_bar"],
                "deltap_design": res["p_to_bar"] - res["p_from_bar"],
                "return_temp_design": res["t_from_k"] - 273.15,
                "flow_temp_design": res["t_to_k"] - 273.15,
                "qext_kW_design": res["mdot_from_kg_per_s"] * 4.2 * (res["t_to_k"] - res["t_from_k"])
            }
            print(f"  Haupteinspeisung {idx}: {design_results['Heizentrale Haupteinspeisung'][idx]['qext_kW_design']:.1f} kW Auslegungsleistung")
    
    # Get design state from mass pumps (secondary producers)
    if hasattr(NetworkGenerationData.net, 'res_circ_pump_mass') and len(NetworkGenerationData.net.res_circ_pump_mass) > 0:
        for idx in NetworkGenerationData.net.res_circ_pump_mass.index:
            res = NetworkGenerationData.net.res_circ_pump_mass.loc[idx]
            design_results["weitere Einspeisung"][idx] = {
                "mass_flow_design": res["mdot_from_kg_per_s"],
                "flow_pressure_design": res["p_to_bar"],
                "return_pressure_design": res["p_from_bar"],
                "deltap_design": res["p_to_bar"] - res["p_from_bar"],
                "return_temp_design": res["t_from_k"] - 273.15,
                "flow_temp_design": res["t_to_k"] - 273.15,
                "qext_kW_design": res["mdot_from_kg_per_s"] * 4.2 * (res["t_to_k"] - res["t_from_k"])
            }
            print(f"  Weitere Einspeisung {idx}: {design_results['weitere Einspeisung'][idx]['qext_kW_design']:.1f} kW Auslegungsleistung")
    
    # Calculate design losses (difference between generated and consumed heat)
    total_generation_design = sum([data["qext_kW_design"] for pump_type in design_results.values() 
                                   for data in pump_type.values()])
    design_losses_kW = total_generation_design - total_building_demand_design
    design_loss_factor = design_losses_kW / total_building_demand_design if total_building_demand_design > 0 else 0
    
    print(f"Auslegungsverluste: {design_losses_kW:.1f} kW ({design_loss_factor*100:.2f}%)")
    
    # Create time series by scaling with building demand
    NetworkGenerationData.pump_results = {
        "Heizentrale Haupteinspeisung": {},
        "weitere Einspeisung": {}
    }
    
    # Get building demand series for the selected time range
    building_demand_series = NetworkGenerationData.waerme_ges_kW[NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step]
    
    # Handle supply temperature (static or sliding)
    if isinstance(NetworkGenerationData.supply_temperature_heat_generator, np.ndarray):
        # Gleitende Vorlauftemperatur
        supply_temp_series = NetworkGenerationData.supply_temperature_heat_generator[NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step]
        print("Verwende gleitende Vorlauftemperatur")
    else:
        # Statische Vorlauftemperatur
        supply_temp_series = np.full(n_steps, NetworkGenerationData.supply_temperature_heat_generator)
        print(f"Verwende statische Vorlauftemperatur: {NetworkGenerationData.supply_temperature_heat_generator:.1f} °C")
    
    # Scale results for each time step
    for pump_type, pumps in design_results.items():
        for idx, design_data in pumps.items():
            # Calculate heat generation: building demand + constant losses
            # Losses stay approximately constant (independent of load)
            share_of_generation = design_data["qext_kW_design"] / total_generation_design if total_generation_design > 0 else 1.0
            producer_losses = design_losses_kW * share_of_generation
            qext_series = building_demand_series * share_of_generation + producer_losses
            
            # Calculate mass flow from heat and temperature difference
            # q = m * cp * dT  =>  m = q / (cp * dT)
            cp = 4.2  # kJ/kgK
            delta_T = supply_temp_series - design_data["return_temp_design"]
            mass_flow_series = qext_series / (cp * delta_T)
            
            # Temperature handling
            if isinstance(NetworkGenerationData.supply_temperature_heat_generator, np.ndarray):
                # Gleitende Vorlauftemperatur - verwende zeitabhängige Werte
                flow_temp_series = supply_temp_series
            else:
                # Statische Vorlauftemperatur
                flow_temp_series = np.full(n_steps, design_data["flow_temp_design"])
            
            # Store results
            NetworkGenerationData.pump_results[pump_type][idx] = {
                "mass_flow": mass_flow_series,
                "flow_pressure": np.full(n_steps, design_data["flow_pressure_design"]),
                "return_pressure": np.full(n_steps, design_data["return_pressure_design"]),
                "deltap": np.full(n_steps, design_data["deltap_design"]),
                "return_temp": np.full(n_steps, design_data["return_temp_design"]),
                "flow_temp": flow_temp_series,
                "qext_kW": qext_series
            }
    
    print(f"Vereinfachte Berechnung erfolgreich abgeschlossen ({n_steps} Zeitschritte).")
    
    return NetworkGenerationData

def calculate_results(net, net_results: Dict, cp_kJ_kgK: float = 4.2) -> Dict[str, Dict[int, Dict[str, np.ndarray]]]:
    """
    Process and structure raw simulation results from pandapipes.
    
    :param net: Pandapipes network with component definitions
    :type net: pandapipes.pandapipesNet
    :param net_results: Raw results dictionary from time series simulation
    :type net_results: Dict
    :param cp_kJ_kgK: Specific heat capacity of water [kJ/kg·K], defaults to 4.2
    :type cp_kJ_kgK: float
    :return: Structured results dict: {producer_type: {index: {parameter: time_series}}}
    :rtype: Dict[str, Dict[int, Dict[str, np.ndarray]]]
    
    .. note::
       Converts K→°C, calculates heat from mass flow and ΔT. Parameters: mass_flow,
       flow_pressure, return_pressure, deltap, return_temp, flow_temp, qext_kW.
       Handles circ_pump_pressure (main) and circ_pump_mass (secondary).
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
    Export simulation results to CSV file with German column headers.
    
    :param time_steps: Time step array
    :type time_steps: np.ndarray
    :param total_heat_KW: Building heat demand time series [kW]
    :type total_heat_KW: np.ndarray
    :param strom_wp_kW: Heat pump electrical consumption [kW]
    :type strom_wp_kW: np.ndarray
    :param pump_results: Structured pump results from calculate_results
    :type pump_results: Dict
    :param filename: Output CSV file path
    :type filename: str
    
    .. note::
       Semicolon-separated CSV with German column names. Includes Zeit,
       Gesamtwärmebedarf_Gebäude_kW, pump data (Wärmeerzeugung, Massenstrom,
       Delta p, temperatures, pressures). UTF-8-sig encoding.
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
    Import simulation results from CSV file created by save_results_csv.
    
    :param filename: Input CSV file path
    :type filename: str
    :return: (time_steps, total_heat_KW, strom_wp_kW, pump_results)
    :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]
    :raises FileNotFoundError: If CSV file cannot be found
    :raises pd.errors.ParserError: If CSV format is invalid
    :raises KeyError: If required columns are missing
    
    .. note::
       Parses German semicolon-separated CSV. Reconstructs pump_results dict
       structure. Converts dtypes to datetime64/float64. Returns time_steps as
       datetime, heat/power as kW arrays, pump_results matching calculate_results.
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