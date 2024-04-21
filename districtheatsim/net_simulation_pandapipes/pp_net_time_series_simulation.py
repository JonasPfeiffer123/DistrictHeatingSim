from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import pandas as pd
import numpy as np

from net_simulation_pandapipes.controllers import ReturnTemperatureController

def update_const_controls(net, qext_w_profiles, time_steps, start, end):
    for i, qext_w_profile in enumerate(qext_w_profiles):
        df = pd.DataFrame(index=time_steps, data={f'qext_w_{i}': qext_w_profile[start:end]})
        data_source = DFData(df)
        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ConstControl) and ctrl.element_index == i and ctrl.variable == 'qext_w':
                ctrl.data_source = data_source

def update_return_temperature_controller(net, return_temperature, time_steps, start, end):
    controller_count = 0
    for ctrl in net.controller.object.values:
        if isinstance(ctrl, ReturnTemperatureController) :
            # Create the DataFrame for the return temperature
            df_return_temp = pd.DataFrame(index=time_steps, data={'return_temperature': return_temperature[controller_count][start:end]})
            data_source_return_temp = DFData(df_return_temp)

            ctrl.data_source = data_source_return_temp
            controller_count += 1

def update_supply_temperature_controls(net, supply_temperature, time_steps, start, end):
    # Create the DataFrame for the supply temperature
    df_supply_temp = pd.DataFrame(index=time_steps, data={'supply_temperature': supply_temperature[start:end] + 273.15})
    data_source_supply_temp = DFData(df_supply_temp)

    # Check whether a suitable ConstControl exists
    control_exists = False
    for ctrl in net.controller.object.values:
        if (isinstance(ctrl, ConstControl) and ctrl.element == 'circ_pump_pressure'):
            control_exists = True
            # Update the data source of the existing ConstControl
            ctrl.data_source = data_source_supply_temp
            ctrl.profile_name = 'supply_temperature'
            break

    # If no suitable ConstControl exists, create a new one
    if not control_exists:
        ConstControl(net, element='circ_pump_pressure', variable='t_flow_k', element_index=0, 
                     data_source=data_source_supply_temp, profile_name='supply_temperature')

def create_log_variables():
    log_variables = [
        ('res_junction', 'p_bar'), 
        ('res_junction', 't_k'),
        ('heat_exchanger', 'qext_w'),
        ('res_heat_exchanger', 'v_mean_m_per_s'),
        ('res_heat_exchanger', 't_from_k'),
        ('res_heat_exchanger', 't_to_k'),
        ('circ_pump_pressure', 't_flow_k'),
        ('res_heat_exchanger', 'mdot_from_kg_per_s'),
        ('res_circ_pump_pressure', 'mdot_flow_kg_per_s'),
        ('res_circ_pump_pressure', 'deltap_bar')
    ]
    return log_variables

def thermohydraulic_time_series_net(net, yearly_time_steps, qext_w_profiles, start, end, supply_temperature=None, return_temperature=60):
    # Prepare time series calculation
    yearly_time_steps = yearly_time_steps[start:end]

    # Update the ConstControl
    time_steps = range(0, len(qext_w_profiles[0][start:end]))
    update_const_controls(net, qext_w_profiles, time_steps, start, end)

    # If return_temperature data exists, update corresponding ReturnTemperatureController
    if return_temperature is not None and isinstance(return_temperature, np.ndarray) and return_temperature.ndim == 2:
        update_return_temperature_controller(net, return_temperature, time_steps, start, end)

    # If supply_temperature data exists, update corresponding ReturnTemperatureController
    if supply_temperature is not None and isinstance(supply_temperature, np.ndarray):
        update_supply_temperature_controls(net, supply_temperature, time_steps, start, end)

    # Log variables and run time series calculation
    log_variables = create_log_variables()
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)
    run_time_series.run_timeseries(net, time_steps, mode="all")

    return yearly_time_steps, net, ow.np_results

def calculate_results(net, net_results):
    ### Plotting results pump / feed ###
    mass_flow_circ_pump = net_results["res_circ_pump_pressure.mdot_flow_kg_per_s"][:, 0]
    deltap_circ_pump =  net_results["res_circ_pump_pressure.deltap_bar"][:, 0]


    rj_circ_pump = net.circ_pump_pressure["return_junction"][0]
    fj_circ_pump = net.circ_pump_pressure["flow_junction"][0]

    return_temp_circ_pump = net_results["res_junction.t_k"][:, rj_circ_pump] - 273.15
    flow_temp_circ_pump = net_results["res_junction.t_k"][:, fj_circ_pump] - 273.15

    return_pressure_circ_pump = net_results["res_junction.p_bar"][:, rj_circ_pump]
    flows_pressure_circ_pump = net_results["res_junction.p_bar"][:, fj_circ_pump]

    pressure_junctions = net_results["res_junction.p_bar"]

    cp_kJ_kgK = 4.2 # kJ/kgK

    qext_kW = mass_flow_circ_pump * cp_kJ_kgK * (flow_temp_circ_pump -return_temp_circ_pump)

    return mass_flow_circ_pump, deltap_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions

def save_results_csv(time_steps, qext_kW, total_heat_KW, flow_temp_circ_pump, return_temp_circ_pump, mass_flow_circ_pump, deltap_circ_pump, return_pressure_circ_pump, flow_pressure_circ_pump, filename):

    # Converting the arrays into a Pandas DataFrame
    df = pd.DataFrame({'Zeit': time_steps, 
                       'Heizlast_Netz_kW': qext_kW,
                       'Gesamtwärmebedarf_Gebäude_kW': total_heat_KW,
                       'Vorlauftemperatur_Netz_°C': flow_temp_circ_pump, 
                       'Rücklauftemperatur_Netz_°C': return_temp_circ_pump,
                       'Massenstrom_Netzpumpe_kg_s': mass_flow_circ_pump,
                       'Delta_p_Netzpumpe_bar': deltap_circ_pump,
                       'Rücklaufdruck_Netzpumpe_bar': return_pressure_circ_pump,
                       'Vorlaufdruck_Netzpumpe_bar': flow_pressure_circ_pump})

    # Save the DataFrame as CSV
    df.to_csv(filename, sep=';', date_format='%Y-%m-%d %H:%M:%S', index=False)

def import_results_csv(filename):
    data = pd.read_csv(filename, sep=';', parse_dates=['Zeit'])
    time_steps = data["Zeit"].values.astype('datetime64')
    qext_kW = data["Heizlast_Netz_kW"].values.astype('float64')
    total_heat_KW = data["Gesamtwärmebedarf_Gebäude_kW"].values.astype('float64')
    flow_temp_circ_pump = data['Vorlauftemperatur_Netz_°C'].values.astype('float64')
    return_temp_circ_pump = data['Rücklauftemperatur_Netz_°C'].values.astype('float64')
    mass_flow_circ_pump = data["Massenstrom_Netzpumpe_kg_s"].values.astype('float64')
    deltap_circ_pump = data["Delta_p_Netzpumpe_bar"].values.astype('float64')
    return_pressure_circ_pump = data["Rücklaufdruck_Netzpumpe_bar"].values.astype('float64')
    flow_pressure_circ_pump = data["Vorlaufdruck_Netzpumpe_bar"].values.astype('float64')

    return time_steps, qext_kW, total_heat_KW, flow_temp_circ_pump, return_temp_circ_pump, mass_flow_circ_pump, deltap_circ_pump, return_pressure_circ_pump, flow_pressure_circ_pump