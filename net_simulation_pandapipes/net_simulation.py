from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import pandas as pd
import numpy as np

from net_simulation_pandapipes.net_simulation_calculation import *
from net_simulation_pandapipes.controllers import ReturnTemperatureController
from heat_requirement import heat_requirement_VDI4655, heat_requirement_BDEW

def generate_profiles_from_geojson(gdf_heat_exchanger, building_type="HMF", calc_method="BDEW", max_supply_temperature=70, max_return_temperature=55):
    ### define the heat requirement ###
    try:
        YEU_total_heat_kWh = gdf_heat_exchanger["Wärmebedarf"].values.astype(float)
    except KeyError:
        print("Herauslesen des Wärmebedarfs aus geojson nicht möglich.")
        return None

    total_heat_W = []
    max_heat_requirement_W = []
    yearly_time_steps = None

    # Assignment of building types to calculation methods
    building_type_to_method = {
        "EFH": "VDI4655",
        "MFH": "VDI4655",
        "HEF": "BDEW",
        "HMF": "BDEW",
        "GKO": "BDEW",
        "GHA": "BDEW",
        "GMK": "BDEW",
        "GBD": "BDEW",
        "GBH": "BDEW",
        "GWA": "BDEW",
        "GGA": "BDEW",
        "GBA": "BDEW",
        "GGB": "BDEW",
        "GPD": "BDEW",
        "GMF": "BDEW",
        "GHD": "BDEW",
    }

    for idx, YEU in enumerate(YEU_total_heat_kWh):
        if calc_method == "Datensatz":
            try:
                current_building_type = gdf_heat_exchanger.at[idx, "Gebäudetyp"]
                current_calc_method = building_type_to_method.get(current_building_type, "StandardMethode")
            except KeyError:
                print("Gebäudetyp-Spalte nicht in gdf_HAST gefunden.")
                current_calc_method = "StandardMethode"
        else:
            current_building_type = building_type
            current_calc_method = calc_method

        # Heat demand calculation based on building type and calculation method
        if current_calc_method == "VDI4655":
            YEU_heating_kWh, YEU_hot_water_kWh = YEU_total_heat_kWh * 0.2, YEU_total_heat_kWh * 0.8
            heating, hot_water = YEU_heating_kWh[idx], YEU_hot_water_kWh[idx]
            yearly_time_steps, electricity_kW, heating_kW, hot_water_kW, total_heat_kW, hourly_temperature = heat_requirement_VDI4655.calculate(heating, hot_water, building_type=current_building_type)

        elif current_calc_method == "BDEW":
            yearly_time_steps, total_heat_kW, hourly_temperatures  = heat_requirement_BDEW.calculate(YEU, current_building_type, subtyp="03")

        total_heat_kW = np.where(total_heat_kW<0, 0, total_heat_kW)
        total_heat_W.append(total_heat_kW * 1000)
        max_heat_requirement_W.append(np.max(total_heat_kW * 1000))

    total_heat_W = np.array(total_heat_W)
    max_heat_requirement_W = np.array(max_heat_requirement_W)

    # Calculation of the temperature curve based on the selected settings
    supply_temperature_curve = []
    return_temperature_curve = []

    # get slope of heat exchanger
    slope = -gdf_heat_exchanger["Steigung_Heizkurve"].values.astype(float)

    min_air_temperature = -12 # aka design temperature

    for st, rt, s in zip(max_supply_temperature, max_return_temperature, slope):
        # Calculation of the temperature curves for flow and return
        st_curve = np.where(hourly_temperatures <= min_air_temperature, st, st + (s * (hourly_temperatures - min_air_temperature)))
        rt_curve = np.where(hourly_temperatures <= min_air_temperature, rt, rt + (s * (hourly_temperatures - min_air_temperature)))
        
        supply_temperature_curve.append(st_curve)
        return_temperature_curve.append(rt_curve)


    supply_temperature_curve = np.array(supply_temperature_curve)
    return_temperature_curve = np.array(return_temperature_curve)

    return yearly_time_steps, total_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve

def initialize_net_geojson(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, return_temperature=60, supply_temperature=85, \
                           flow_pressure_pump=4, lift_pressure_pump=1.5, diameter_mm=107.1, pipetype="KMR 100/250-2v", k=0.0470, alpha=0.61, pipe_creation_mode="type"):
    # net generation from gis data
    net = create_network(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, return_temperature, supply_temperature, flow_pressure_pump, \
                         lift_pressure_pump, diameter_mm, pipetype, k, alpha, pipe_creation_mode)
    net = create_controllers(net, qext_w, return_temperature)
    net = correct_flow_directions(net)

    net = init_timeseries_opt(net, qext_w, return_temperature)

    if pipe_creation_mode == "diameter":
        net = optimize_diameter_parameters(net)

    if pipe_creation_mode == "type":
        net = optimize_diameter_types(net)

    net = optimize_diameter_parameters(net, element="heat_exchanger")
    net = optimize_diameter_parameters(net, element="flow_control")

    return net

def init_timeseries_opt(net, qext_w, return_temperature, time_steps=3):
        # Check whether qext_w is one-dimensional and the length matches the number of heat exchangers
        if qext_w.ndim != 1 or len(qext_w) != len(net.heat_exchanger):
            raise ValueError("qext_w muss ein eindimensionales Array mit einer Länge gleich der Anzahl der Wärmetauscher sein.")

        # Create a DataFrame where each column is a time series for a heat exchanger
        data = {f'qext_w_{i}': [qext_w[i]] * time_steps for i in range(len(qext_w))}
        df = pd.DataFrame(data, index=range(time_steps))
        data_source = DFData(df)

        # Update data source for ConstControl controllers
        for i in range(len(net.heat_exchanger)):
            for ctrl in net.controller.object.values:
                if isinstance(ctrl, ConstControl) and ctrl.element_index == i and ctrl.variable == 'qext_w':
                    ctrl.data_source = data_source
        
        # Updating the custom controllers
        i_rt = 0
        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ReturnTemperatureController):
                ctrl.target_temperature = return_temperature[i_rt]  # update target temperature if necessary
                i_rt += 1
        
        log_variables = [('res_junction', 'p_bar'), ('res_junction', 't_k'), ('heat_exchanger', 'qext_w'), \
                         ('res_heat_exchanger', 'v_mean_m_per_s'), ('res_heat_exchanger', 't_to_k'), 
                        ('circ_pump_pressure', 't_flow_k'),  ('res_heat_exchanger', 'mdot_from_kg_per_s'),
                        ('res_circ_pump_pressure', 'mdot_flow_kg_per_s'), ('res_circ_pump_pressure', 'deltap_bar')]
        
        ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

        run_time_series.run_timeseries(net, time_steps, mode="all")
        
        return net

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