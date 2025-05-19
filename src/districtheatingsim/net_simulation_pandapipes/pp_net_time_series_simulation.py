"""
Filename: pp_net_time_series_simulation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-05-15
Description: Script with functions for the implemented time series calculation.
"""

from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import pandas as pd
import numpy as np

from districtheatingsim.net_simulation_pandapipes.utilities import COP_WP, TemperatureController

def update_heat_consumer_qext_controller(net, qext_w_profiles, time_steps, start, end):
    """Update constant controls with new data sources for time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.
        qext_w_profiles (list of arrays): List of external heat profiles.
        time_steps (range): Range of time steps for the simulation.
        start (int): Start index for slicing the profiles.
        end (int): End index for slicing the profiles.
    """
    for i, qext_w_profile in enumerate(qext_w_profiles):
        df = pd.DataFrame(index=time_steps, data={f'qext_w_{i}': qext_w_profile[start:end]})
        data_source = DFData(df)
        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ConstControl) and ctrl.element_index == i and ctrl.variable == 'qext_w':
                ctrl.data_source = data_source

def update_heat_consumer_temperature_controller(net, min_supply_temperature_heat_consumer, time_steps, start, end):
    """Update return temperature controllers with new data sources for time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.
        min_supply_temperature_heat_consumer (array): Supply temperature profiles for heat consumers.
        time_steps (range): Range of time steps for the simulation.
        start (int): Start index for slicing the profiles.
        end (int): End index for slicing the profiles.
    """
    controller_count = 0
    for ctrl in net.controller.object.values:
        if isinstance(ctrl, TemperatureController):
            profile = min_supply_temperature_heat_consumer[controller_count]
            # Prüfe, ob statisch oder zeitabhängig
            if np.isscalar(profile) or (isinstance(profile, np.ndarray) and profile.ndim == 0):
                # Einzelwert: für alle Zeitschritte wiederholen
                values = np.full(len(time_steps), profile)
            elif isinstance(profile, np.ndarray) and profile.ndim == 1 and len(profile) == 1:
                values = np.full(len(time_steps), profile[0])
            else:
                # Zeitreihe: richtigen Ausschnitt nehmen
                values = profile[start:end]
            df_return_temp = pd.DataFrame(index=time_steps, data={
                'min_supply_temperature': values
            })
            data_source_return_temp = DFData(df_return_temp)
            ctrl.data_source = data_source_return_temp
            controller_count += 1

def update_heat_consumer_return_temperature_controller(net, return_temperature_heat_consumer, time_steps, start, end):
    """Update return temperature controllers with new data sources for time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.
        return_temperature_heat_consumer (array): Return temperature profiles for heat consumers.
        time_steps (range): Range of time steps for the simulation.
        start (int): Start index for slicing the profiles.
        end (int): End index for slicing the profiles.
    """
    for i, return_temp_profile in enumerate(return_temperature_heat_consumer):
        # Prüfe, ob statisch oder zeitabhängig
        if np.isscalar(return_temp_profile) or (isinstance(return_temp_profile, np.ndarray) and return_temp_profile.ndim == 0):
            # Einzelwert: für alle Zeitschritte wiederholen
            values = np.full(len(time_steps), return_temp_profile + 273.15)
        elif isinstance(return_temp_profile, np.ndarray) and return_temp_profile.ndim == 1 and len(return_temp_profile) == 1:
            values = np.full(len(time_steps), return_temp_profile[0] + 273.15)
        else:
            # Zeitreihe: richtigen Ausschnitt nehmen und umrechnen
            values = return_temp_profile[start:end] + 273.15

        # DataFrame für alle Zeitschritte bauen
        df_return_temp = pd.DataFrame(index=time_steps, data={
            f'treturn_k_{i}': values
        })
        data_source_return_temp = DFData(df_return_temp)

        for ctrl in net.controller.object.values:
            if (isinstance(ctrl, ConstControl) and ctrl.element == 'heat_consumer' and ctrl.element_index == i and ctrl.variable == 'treturn_k'):
                # Update the data source of the existing ConstControl
                ctrl.data_source = data_source_return_temp

# Needs to be fully implemented, also fix create controllers
def update_secondary_producer_controller(net, secondary_producers, time_steps, start, end):
    """Update secondary producer controls with new data sources for time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.
        secondary_producers (list of dict): List of secondary producer profiles.
        time_steps (range): Range of time steps for the simulation.
        start (int): Start index for slicing the profiles.
        end (int): End index for slicing the profiles.
    """
    for producer in secondary_producers:
        df_secondary_producer = pd.DataFrame(index=time_steps, data={
            f'mdot_flow_kg_per_s_{producer["index"]}': [producer["mass_flow"]] * len(time_steps)
        })
        data_source_secondary_producer = DFData(df_secondary_producer)

        df_secondary_producer_flow_control = pd.DataFrame(index=time_steps, data={
            f'controlled_mdot_kg_per_s_{producer["index"]}': [producer["mass_flow"]] * len(time_steps)
        })
        data_source_secondary_producer_flow_control = DFData(df_secondary_producer_flow_control)

        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ConstControl) and ctrl.element == 'circ_pump_mass' and ctrl.variable == 'mdot_flow_kg_per_s':
                ctrl.data_source = data_source_secondary_producer
            elif isinstance(ctrl, ConstControl) and ctrl.element == 'flow_control' and ctrl.variable == 'controlled_mdot_kg_per_s':
                ctrl.data_source = data_source_secondary_producer_flow_control
            
def update_heat_generator_supply_temperature_controller(net, supply_temperature, time_steps, start, end):
    """Update supply temperature controls with new data sources for time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.
        supply_temperature (array): Supply temperature profile.
        time_steps (range): Range of time steps for the simulation.
        start (int): Start index for slicing the profile.
        end (int): End index for slicing the profile.
    """
    # Create the DataFrame for the supply temperature
    df_supply_temp = pd.DataFrame(index=time_steps, data={'supply_temperature': supply_temperature[start:end] + 273.15})
    data_source_supply_temp = DFData(df_supply_temp)
    for ctrl in net.controller.object.values:
        if isinstance(ctrl, ConstControl) and ctrl.element == 'circ_pump_pressure' and ctrl.variable == 't_flow_k':
            ctrl.data_source = data_source_supply_temp
        elif isinstance(ctrl, ConstControl) and ctrl.element == 'circ_pump_mass' and ctrl.variable == 't_flow_k':
            ctrl.data_source = data_source_supply_temp

def create_log_variables(net):
    """Create a list of variables to log during the time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.

    Returns:
        list: List of tuples representing the variables to log.
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
        log_variables.append(('res_circ_pump_mass', 'mdot_from_kg_per_s'))
        log_variables.append(('res_circ_pump_mass', 'p_to_bar'))
        log_variables.append(('res_circ_pump_mass', 'p_from_bar'))
        log_variables.append(('res_circ_pump_mass', 't_to_k'))
        log_variables.append(('res_circ_pump_mass', 't_from_k'))

    return log_variables

def time_series_preprocessing(NetworkGenerationData):
    """Preprocess time series data for the thermal and hydraulic network simulation.

    Args:
        NetworkGenerationData (object): Network generation data object containing all necessary parameters.

    Returns:
        NetworkGenerationData: Updated NetworkGenerationData object with preprocessed data.
    """

    print(f"Vorlauftemperatur Netz: {NetworkGenerationData.supply_temperature_heat_generator} °C")
    print(f"Mindestvorlauftemperatur HAST: {NetworkGenerationData.min_supply_temperature_heat_consumer} °C")
    print(f"Rücklauftemperatur HAST: {NetworkGenerationData.return_temperature_heat_consumer} °C")
    print(f"Vorlauftemperatur Gebäude: {NetworkGenerationData.supply_temperature_buildings} °C")
    print(f"Rücklauftemperatur Gebäude: {NetworkGenerationData.return_temperature_buildings} °C")
    print(f"building_temperature_checked: {NetworkGenerationData.building_temperature_checked}")
    print(f"Netconfiguration: {NetworkGenerationData.netconfiguration}")

    COP_file_values = np.genfromtxt(NetworkGenerationData.COP_filename, delimiter=';')

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

        # Calculate COP, strom_wp, and waerme_hast as arrays
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

    # replace all values in NetworkGenerationData.waerme_hast_ges_W with 2 % of the maximum value if the value is smaller than 2 % of the maximum value
    max_heat = np.max(NetworkGenerationData.waerme_hast_ges_W)
    max_power = np.max(NetworkGenerationData.strombedarf_hast_ges_W)
    NetworkGenerationData.waerme_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_heat, NetworkGenerationData.waerme_hast_ges_W)
    NetworkGenerationData.strombedarf_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_power, NetworkGenerationData.strombedarf_hast_ges_W)

    # Convert all values in NetworkGenerationData.waerme_hast_ges_W and NetworkGenerationData.strombedarf_hast_ges_W to kW
    NetworkGenerationData.waerme_hast_ges_kW = np.where(NetworkGenerationData.waerme_hast_ges_W == 0, 0, NetworkGenerationData.waerme_hast_ges_W / 1000)
    NetworkGenerationData.strombedarf_hast_ges_kW = np.where(NetworkGenerationData.strombedarf_hast_ges_W == 0, 0, NetworkGenerationData.strombedarf_hast_ges_W / 1000)

    # Calculate the total heat and electricity demand profiles
    NetworkGenerationData.waerme_ges_kW = np.sum(NetworkGenerationData.waerme_hast_ges_kW, axis=0)
    NetworkGenerationData.strombedarf_ges_kW = np.sum(NetworkGenerationData.strombedarf_hast_ges_kW, axis=0)

    return NetworkGenerationData
    
def thermohydraulic_time_series_net(NetworkGenerationData):
    """Run a thermohydraulic time series simulation for the network.

    Args:
        NetworkGenerationData (object): Network generation data object containing all necessary parameters.

    Returns:
        NetworkGenerationData: Updated NetworkGenerationData object with simulation results.
    """
    # Prepare time series calculation
    NetworkGenerationData.yearly_time_steps_start_end = NetworkGenerationData.yearly_time_steps[NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step]

    # Update the ConstControl
    time_steps = range(0, len(NetworkGenerationData.waerme_hast_ges_W[0][NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step]))
    update_heat_consumer_qext_controller(NetworkGenerationData.net, NetworkGenerationData.waerme_hast_ges_W, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)

    # Update secondary producer controls
    if NetworkGenerationData.secondary_producers:
        update_secondary_producer_controller(NetworkGenerationData.net, NetworkGenerationData.secondary_producers, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)

    # If return_temperature data exists, update corresponding TemperatureController
    if NetworkGenerationData.min_supply_temperature_heat_consumer is not None and np.any(np.array(NetworkGenerationData.min_supply_temperature_heat_consumer) != 0) and isinstance(NetworkGenerationData.min_supply_temperature_heat_consumer, np.ndarray):
        print("Update TemperatureController")
        update_heat_consumer_temperature_controller(NetworkGenerationData.net, NetworkGenerationData.min_supply_temperature_heat_consumer, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)
    
    if NetworkGenerationData.return_temperature_heat_consumer is not None and isinstance(NetworkGenerationData.return_temperature_heat_consumer, np.ndarray):
        print("Update Return Temperature Const Control")
        update_heat_consumer_return_temperature_controller(NetworkGenerationData.net, NetworkGenerationData.return_temperature_heat_consumer, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)

    # If supply_temperature data exists and is an numpy array, update corresponding ConstControl (could also be a float (constant), therefore updating would not be necessary)
    if NetworkGenerationData.supply_temperature_heat_generator is not None and isinstance(NetworkGenerationData.supply_temperature_heat_generator, np.ndarray):
        update_heat_generator_supply_temperature_controller(NetworkGenerationData.net, NetworkGenerationData.supply_temperature_heat_generator, time_steps, NetworkGenerationData.start_time_step, NetworkGenerationData.end_time_step)
    
    # Log variables and run time series calculation
    log_variables = create_log_variables(NetworkGenerationData.net)
    ow = OutputWriter(NetworkGenerationData.net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(NetworkGenerationData.net, time_steps, mode="bidirectional", iter=100)
    
    NetworkGenerationData.net_results = ow.np_results

    NetworkGenerationData.pump_results = calculate_results(NetworkGenerationData.net, NetworkGenerationData.net_results)
    
    return NetworkGenerationData

def calculate_results(net, net_results, cp_kJ_kgK=4.2):
    """Calculate and structure the simulation results.

    Args:
        net (pandapipesNet): The pandapipes network.
        net_results (dict): Results of the time series simulation.
        cp_kJ_kgK (float, optional): Specific heat capacity of water in kJ/kg*K. Defaults to 4.2.

    Returns:
        dict: Structured results for the simulation.
    """
    # Prepare data structure
    pump_results = {
        "Heizentrale Haupteinspeisung": {},
        "weitere Einspeisung": {}
    }

    # Add results for the Pressure Pump
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

    # Add results for the Mass Pumps
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

def save_results_csv(time_steps, total_heat_KW, strom_wp_kW, pump_results, filename):
    """Save the simulation results to a CSV file.

    Args:
        time_steps (array): Array of time steps.
        total_heat_KW (array): Total heat demand in kW.
        strom_wp_kW (array): Power consumption of heat pumps in kW.
        pump_results (dict): Structured results for the simulation.
        filename (str): Path to the output CSV file.

    Returns:
        None
    """
    # Converting the arrays into a Pandas DataFrame
    df = pd.DataFrame({'Zeit': time_steps,
                       'Gesamtwärmebedarf_Gebäude_kW': total_heat_KW,
                       'Gesamtheizlast_Gebäude_kW': total_heat_KW + strom_wp_kW,
                       'Gesamtstrombedarf_Wärmepumpen_Gebäude_kW': strom_wp_kW
    })

    # Loop through all pump types and their results
    for pump_type, pumps in pump_results.items():
        for idx, pump_data in pumps.items():
            df[f"Wärmeerzeugung_{pump_type}_{idx+1}_kW"] = pump_data['qext_kW']
            df[f'Massenstrom_{pump_type}_{idx+1}_kg/s'] = pump_data['mass_flow']
            df[f'Delta p_{pump_type}_{idx+1}_bar'] = pump_data['deltap']
            df[f'Vorlauftemperatur_{pump_type}_{idx+1}_°C'] = pump_data['flow_temp']
            df[f'Rücklauftemperatur_{pump_type}_{idx+1}_°C'] = pump_data['return_temp']
            df[f"Vorlaufdruck_{pump_type}_{idx+1}_bar"] = pump_data['flow_pressure']
            df[f"Rücklaufdruck_{pump_type}_{idx+1}_bar"] = pump_data['return_pressure']

    # Save the DataFrame as CSV
    df.to_csv(filename, sep=';', date_format='%Y-%m-%d %H:%M:%S', index=False)

def import_results_csv(filename):
    """Import the simulation results from a CSV file.

    Args:
        filename (str): Path to the input CSV file.

    Returns:
        tuple: Imported time steps, total heat demand, power consumption, and pump results.
    """
    # Load data from the CSV file
    data = pd.read_csv(filename, sep=';', parse_dates=['Zeit'])

    # Extract general time series and heat data
    time_steps = data["Zeit"].values.astype('datetime64')
    total_heat_KW = data["Gesamtwärmebedarf_Gebäude_kW"].values.astype('float64')
    strom_wp_kW = data["Gesamtstrombedarf_Wärmepumpen_Gebäude_kW"].values.astype('float64')

    # Create a dictionary to store the pump data
    pump_results = {}

    pump_data = {
        'Wärmeerzeugung': 'qext_kW',
        'Massenstrom': 'mass_flow',
        'Delta p': 'deltap',
        'Vorlauftemperatur': 'flow_temp',
        'Rücklauftemperatur': 'return_temp',
        'Vorlaufdruck': 'flow_pressure',
        'Rücklaufdruck': 'return_pressure'
    }

    # Iterate over all columns to identify relevant pump data
    for column in data.columns:
        if any(prefix in column for prefix in ['Wärmeerzeugung', 'Massenstrom', 'Delta p', 'Vorlauftemperatur', 'Rücklauftemperatur', 'Vorlaufdruck', 'Rücklaufdruck']):
            parts = column.split('_')
            if len(parts) >= 4:
                # General structure expected: [prefix, pump type, index, parameter]
                prefix, pump_type, idx, parameter = parts[0], parts[1], int(parts[2])-1, "_".join(parts[3:])

                value = pump_data[prefix]

                # Ensure pump type and index are properly initialized
                if pump_type not in pump_results:
                    pump_results[pump_type] = {}
                if idx not in pump_results[pump_type]:
                    pump_results[pump_type][idx] = {}

                # Add parameters to the corresponding pumps
                pump_results[pump_type][idx][value] = data[column].values.astype('float64')
            else:
                print(f"Warning: Column name '{column}' has an unexpected format and is ignored.")

    return time_steps, total_heat_KW, strom_wp_kW, pump_results