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

def create_log_variables(net):
    log_variables = [
        ('res_junction', 'p_bar'), 
        ('res_junction', 't_k'),
        #('heat_exchanger', 'qext_w'),
        #('res_heat_exchanger', 'v_mean_m_per_s'),
        #('res_heat_exchanger', 't_from_k'),
        #('res_heat_exchanger', 't_to_k'),
        #('res_heat_exchanger', 'mdot_from_kg_per_s'),
        ('heat_consumer', 'qext_w'),
        ('res_heat_consumer', 'v_mean_m_per_s'),
        ('res_heat_consumer', 't_from_k'),
        ('res_heat_consumer', 't_to_k'),
        ('res_heat_consumer', 'mdot_from_kg_per_s'),
        ('res_circ_pump_pressure', 'mdot_flow_kg_per_s'),
        ('res_circ_pump_pressure', 'deltap_bar')
    ]

    if 'circ_pump_mass' in net:
        log_variables.append(('res_circ_pump_mass', 'mdot_flow_kg_per_s'))
        log_variables.append(('res_circ_pump_mass', 'deltap_bar'))

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
    log_variables = create_log_variables(net)
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)
    run_time_series.run_timeseries(net, time_steps, mode="all")

    return yearly_time_steps, net, ow.np_results

def calculate_results(net, net_results, cp_kJ_kgK=4.2):    
    # Datenstruktur vorbereiten
    pump_results = {
        "Heizentrale Haupteinspeisung": {},
        "weitere Einspeisung": {}
    }

    # Ergebnisse für die Pressure Pump hinzufügen
    if 'circ_pump_pressure' in net:
        for idx, row in net.circ_pump_pressure.iterrows():
            pump_results["Heizentrale Haupteinspeisung"][idx] = {
                "mass_flow": net_results["res_circ_pump_pressure.mdot_flow_kg_per_s"][:, 0],
                "deltap": net_results["res_circ_pump_pressure.deltap_bar"][:, 0],
                "return_temp": net_results["res_junction.t_k"][:, net.circ_pump_pressure["return_junction"][0]] - 273.15,
                "flow_temp": net_results["res_junction.t_k"][:, net.circ_pump_pressure["flow_junction"][0]] - 273.15,
                "return_pressure": net_results["res_junction.p_bar"][:, net.circ_pump_pressure["return_junction"][0]],
                "flow_pressure": net_results["res_junction.p_bar"][:, net.circ_pump_pressure["flow_junction"][0]],
                "qext_kW": net_results["res_circ_pump_pressure.mdot_flow_kg_per_s"][:, idx] * cp_kJ_kgK * (net_results["res_junction.t_k"][:, net.circ_pump_pressure["flow_junction"][0]] - net_results["res_junction.t_k"][:, net.circ_pump_pressure["return_junction"][0]])
            }

    # Ergebnisse für die Mass Pumps hinzufügen
    if 'circ_pump_mass' in net:
        for idx, row in net.circ_pump_mass.iterrows():
            pump_results["weitere Einspeisung"][idx] = {
                "mass_flow": net_results["res_circ_pump_mass.mdot_flow_kg_per_s"][:, idx],
                "deltap": net_results["res_circ_pump_mass.deltap_bar"][:, idx],
                "return_temp": net_results["res_junction.t_k"][:, net.circ_pump_mass["return_junction"][0]] - 273.15,
                "flow_temp": net_results["res_junction.t_k"][:, net.circ_pump_mass["flow_junction"][0]] - 273.15,
                "return_pressure": net_results["res_junction.p_bar"][:, net.circ_pump_mass["return_junction"][0]],
                "flow_pressure": net_results["res_junction.p_bar"][:, net.circ_pump_mass["flow_junction"][0]],
                "qext_kW": net_results["res_circ_pump_mass.mdot_flow_kg_per_s"][:, idx] * cp_kJ_kgK * (net_results["res_junction.t_k"][:, net.circ_pump_mass["flow_junction"][0]] - net_results["res_junction.t_k"][:, net.circ_pump_mass["return_junction"][0]])
            }

    return pump_results

def save_results_csv(time_steps, total_heat_KW, pump_results, filename):

    # Converting the arrays into a Pandas DataFrame
    df = pd.DataFrame({'Zeit': time_steps,
                       'Gesamtwärmebedarf_Gebäude_kW': total_heat_KW,
    })

    # Schleife durch alle Pumpentypen und ihre Ergebnisse
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
    # Daten aus der CSV-Datei laden
    data = pd.read_csv(filename, sep=';', parse_dates=['Zeit'])

    # Extrahieren der allgemeinen Zeitreihen- und Wärmedaten
    time_steps = data["Zeit"].values.astype('datetime64')
    total_heat_KW = data["Gesamtwärmebedarf_Gebäude_kW"].values.astype('float64')

    # Erstellen eines Dictionarys, um die Pumpendaten zu speichern
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

    # Iteration über alle Spalten, um relevante Pumpendaten zu identifizieren
    for column in data.columns:
        if any(prefix in column for prefix in ['Wärmeerzeugung', 'Massenstrom', 'Delta p', 'Vorlauftemperatur', 'Rücklauftemperatur', 'Vorlaufdruck', 'Rücklaufdruck']):
            parts = column.split('_')
            if len(parts) >= 4:
                # Generelle Struktur erwartet: [Kennung, Pumpentyp, Index, Parameter]
                prefix, pump_type, idx, parameter = parts[0], parts[1], int(parts[2])-1, "_".join(parts[3:])

                value = pump_data[prefix]

                # Sicherstellen, dass Pumpentyp und Index korrekt initialisiert sind
                if pump_type not in pump_results:
                    pump_results[pump_type] = {}
                if idx not in pump_results[pump_type]:
                    pump_results[pump_type][idx] = {}

                # Parameter zu den entsprechenden Pumpen hinzufügen
                pump_results[pump_type][idx][value] = data[column].values.astype('float64')
            else:
                print(f"Warnung: Spaltenname '{column}' hat ein unerwartetes Format und wird ignoriert.")

    return time_steps, total_heat_KW, pump_results