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
            # Create the DataFrame for the return temperature
            df_return_temp = pd.DataFrame(index=time_steps, data={
                'min_supply_temperature': min_supply_temperature_heat_consumer[controller_count][start:end]
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
        # Create the DataFrame for the return temperature
        df_return_temp = pd.DataFrame(index=time_steps, data={
            f'treturn_k_{i}': return_temp_profile[start:end] + 273.15
        })
        data_source_return_temp = DFData(df_return_temp)

        # Check whether a suitable ConstControl exists
        control_exists = False
        for ctrl in net.controller.object.values:
            if (
                isinstance(ctrl, ConstControl)
                and ctrl.element == 'heat_consumer'
                and ctrl.element_index == i
                and ctrl.variable == 'treturn_k'
            ):
                control_exists = True
                # Update the data source of the existing ConstControl
                ctrl.data_source = data_source_return_temp
                ctrl.profile_name = f'treturn_k_{i}'
                break

        # If no suitable ConstControl exists, create a new one
        if not control_exists:
            ConstControl(
                net,
                element='heat_consumer',
                variable='treturn_k',
                element_index=i,
                data_source=data_source_return_temp,
                profile_name=f'treturn_k_{i}'
            )

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

def time_series_preprocessing(supply_temperature, supply_temperature_heat_consumer, return_temperature_heat_consumer, \
                              supply_temperature_buildings, return_temperature_buildings, building_temp_checked, \
                              netconfiguration, total_heat_W, return_temperature_buildings_curve, dT_RL, 
                              supply_temperature_buildings_curve, COP_filename):
    """Preprocess time series data for the thermal and hydraulic network simulation.

    Args:
        supply_temperature (float): Supply temperature of the network.
        supply_temperature_heat_consumer (float): Minimum supply temperature for heat consumers.
        return_temperature_heat_consumer (float): Return temperature for heat consumers.
        supply_temperature_buildings (float): Supply temperature for buildings.
        return_temperature_buildings (float): Return temperature for buildings.
        building_temp_checked (bool): Flag indicating if building temperatures are time-varying.
        netconfiguration (str): Network configuration type.
        total_heat_W (array): Total heat demand.
        return_temperature_buildings_curve (array): Time-varying return temperature for buildings.
        dT_RL (float): Temperature difference for the return line.
        supply_temperature_buildings_curve (array): Time-varying supply temperature for buildings.
        COP_filename (str): Path to the COP data file.

    Returns:
        tuple: Preprocessed heat demand, power consumption, supply temperature, and return temperature.
    """
    print(f"Vorlauftemperatur Netz: {supply_temperature} °C")
    print(f"Mindestvorlauftemperatur HAST: {supply_temperature_heat_consumer} °C")
    print(f"Rücklauftemperatur HAST: {return_temperature_heat_consumer} °C")
    print(f"Vorlauftemperatur Gebäude: {supply_temperature_buildings} °C")
    print(f"Rücklauftemperatur Gebäude: {return_temperature_buildings} °C")

    #print(len(total_heat_W))
    # replace all values in total_heat_W with 2 % of the maximum value if the value is smaller than 2 % of the maximum value
    max_heat = np.max(total_heat_W)
    total_heat_W = np.where(total_heat_W < 0.02 * max_heat, 0.02 * max_heat, total_heat_W)

    waerme_hast_ges_W = []
    strom_hast_ges_W = []
    
    COP_file_values = np.genfromtxt(COP_filename, delimiter=';')

    print(f"Building_temp_checked: {building_temp_checked}")
    print(f"Netconfiguration: {netconfiguration}")

    if building_temp_checked == False and netconfiguration != "kaltes Netz":
        waerme_hast_ges_W = total_heat_W
        strom_hast_ges_W = np.zeros_like(waerme_hast_ges_W)

    elif building_temp_checked == False and netconfiguration == "kaltes Netz":
        supply_temperature_heat_consumer = return_temperature_heat_consumer + dT_RL
        COP, _ = COP_WP(supply_temperature_buildings, return_temperature_heat_consumer, COP_file_values)
        print(f"COP dezentrale Wärmepumpen Gebäude: {COP}")

        for waerme_gebaeude, cop in zip(total_heat_W, COP):
            strom_wp = waerme_gebaeude/cop
            waerme_hast = waerme_gebaeude - strom_wp

            waerme_hast_ges_W.append(waerme_hast)
            strom_hast_ges_W.append(strom_wp)

        waerme_hast_ges_W = np.array(waerme_hast_ges_W)
        strom_hast_ges_W = np.array(strom_hast_ges_W)
    
    if building_temp_checked == True and netconfiguration != "kaltes Netz":
        supply_temperature_heat_consumer = supply_temperature_buildings_curve + dT_RL
        return_temperature_heat_consumer = return_temperature_buildings_curve + dT_RL
        waerme_hast_ges_W = total_heat_W
        strom_hast_ges_W = np.zeros_like(waerme_hast_ges_W)

    elif building_temp_checked == True and netconfiguration == "kaltes Netz":
        supply_temperature_heat_consumer = return_temperature_heat_consumer + dT_RL
        for st, rt, waerme_gebaeude in zip(supply_temperature_buildings_curve, return_temperature_heat_consumer, total_heat_W):
            cop, _ = COP_WP(st, rt, COP_file_values)

            strom_wp = waerme_gebaeude/cop
            waerme_hast = waerme_gebaeude - strom_wp

            waerme_hast_ges_W.append(waerme_hast)
            strom_hast_ges_W.append(strom_wp)

        waerme_hast_ges_W = np.array(waerme_hast_ges_W)
        strom_hast_ges_W = np.array(strom_hast_ges_W)

        print(f"Rücklauftemperatur HAST: {return_temperature_heat_consumer} °C")

    return waerme_hast_ges_W, strom_hast_ges_W, supply_temperature_heat_consumer, return_temperature_heat_consumer 
    
def thermohydraulic_time_series_net(net, yearly_time_steps, qext_w_profiles, start, end, supply_temperature=85, 
                                    min_supply_temperature_heat_consumer=65, return_temperature_heat_consumer=60, 
                                    secondary_producers=None):
    """Run a thermohydraulic time series simulation for the network.

    Args:
        net (pandapipesNet): The pandapipes network.
        yearly_time_steps (array): Array of yearly time steps.
        qext_w_profiles (list of arrays): List of external heat profiles.
        start (int): Start index for the simulation.
        end (int): End index for the simulation.
        supply_temperature (float, optional): Supply temperature. Defaults to 85.
        min_supply_temperature_heat_consumer (float, optional): Minimum supply temperature for heat consumers. Defaults to 65.
        return_temperature_heat_consumer (float, optional): Return temperature for heat consumers. Defaults to 60.
        secondary_producers (list, optional): List of secondary producers. Defaults to None.

    Returns:
        tuple: Updated yearly time steps, network, and results.
    """
    # Prepare time series calculation
    yearly_time_steps = yearly_time_steps[start:end]

    # Update the ConstControl
    time_steps = range(0, len(qext_w_profiles[0][start:end]))
    update_heat_consumer_qext_controller(net, qext_w_profiles, time_steps, start, end)

    # Update secondary producer controls
    if secondary_producers:
        update_secondary_producer_controller(net, secondary_producers, time_steps, start, end)

    # If return_temperature data exists, update corresponding TemperatureController
    if min_supply_temperature_heat_consumer is not None and isinstance(min_supply_temperature_heat_consumer, np.ndarray) and min_supply_temperature_heat_consumer.ndim == 2:
        update_heat_consumer_temperature_controller(net, min_supply_temperature_heat_consumer, time_steps, start, end)
    
    if return_temperature_heat_consumer is not None and isinstance(return_temperature_heat_consumer, np.ndarray) and return_temperature_heat_consumer.ndim == 2:
        update_heat_consumer_return_temperature_controller(net, return_temperature_heat_consumer, time_steps, start, end)

    # If supply_temperature data exists, update corresponding ConstControl
    if supply_temperature is not None and isinstance(supply_temperature, np.ndarray):
        update_heat_generator_supply_temperature_controller(net, supply_temperature, time_steps, start, end)
    
    # Log variables and run time series calculation
    log_variables = create_log_variables(net)
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(net, time_steps, mode="bidirectional", iter=100)

    return yearly_time_steps, net, ow.np_results

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