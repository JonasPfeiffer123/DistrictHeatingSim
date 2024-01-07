from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import pandas as pd
import numpy as np

from net_simulation_pandapipes.net_simulation_calculation import *
from net_simulation_pandapipes.controllers import ReturnTemperatureController
from heat_requirement import heat_requirement_VDI4655, heat_requirement_BDEW

def generate_profiles_from_geojson(gdf_HAST, building_type="MFH", calc_method="VDI4655"):
    ### define the heat requirement ###
    try:
        JEB_Wärme_ges_kWh = gdf_HAST["Wärmebedarf"].values.astype(float)
    except KeyError:
        print("Herauslesen des Wärmebedarfs aus geojson nicht möglich.")
        return None

    JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh = JEB_Wärme_ges_kWh * 0.2, JEB_Wärme_ges_kWh * 0.8

    waerme_ges_W = []
    max_waerme_ges_W = []
    yearly_time_steps = None

    # Zuordnung von Gebäudetypen zu Berechnungsmethoden
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

    for idx, JWB in enumerate(JEB_Wärme_ges_kWh):
        if calc_method == "Datensatz":
            try:
                current_building_type = gdf_HAST.at[idx, "Gebäudetyp"]
                current_calc_method = building_type_to_method.get(current_building_type, "StandardMethode")
            except KeyError:
                print("Gebäudetyp-Spalte nicht in gdf_HAST gefunden.")
                current_calc_method = "StandardMethode"
        else:
            current_building_type = building_type
            current_calc_method = calc_method

        # Wärmebedarfsberechnung basierend auf dem Gebäudetyp und der Berechnungsmethode
        if current_calc_method == "VDI4655":
            hw, tww = JEB_Heizwärme_kWh[idx], JEB_Trinkwarmwasser_kWh[idx]
            yearly_time_steps, _, _, _, waerme_ges_kW = heat_requirement_VDI4655.calculate(hw, tww, building_type=current_building_type)
        elif current_calc_method == "BDEW":
            yearly_time_steps, waerme_ges_kW  = heat_requirement_BDEW.calculate(JWB, current_building_type, subtyp="03")

        waerme_ges_W.append(waerme_ges_kW * 1000)
        max_waerme_ges_W.append(np.max(waerme_ges_kW * 1000))

    waerme_ges_W = np.array(waerme_ges_W)
    max_waerme_ges_W = np.array(max_waerme_ges_W)

    return yearly_time_steps, waerme_ges_W, max_waerme_ges_W

def initialize_net_geojson(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w, pipe_creation_mode="diameter"):
    # net generation from gis data
    net = create_network(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w, pipe_creation_mode)
    net = create_controllers(net, qext_w)
    net = correct_flow_directions(net)
    net = init_timeseries_opt(net, qext_w, time_steps=3, target_temperature=60)

    if pipe_creation_mode == "diameter":
        net = optimize_diameter_parameters(net)

    if pipe_creation_mode == "type":
        net = optimize_diameter_types(net)

    net = optimize_diameter_parameters(net, element="heat_exchanger")
    net = optimize_diameter_parameters(net, element="flow_control")
    export_net_geojson(net)

    return net

def init_timeseries_opt(net, qext_w, time_steps=3, target_temperature=60):
        # Überprüfen, ob qext_w eindimensional ist und die Länge mit der Anzahl der Wärmetauscher übereinstimmt
        if qext_w.ndim != 1 or len(qext_w) != len(net.heat_exchanger):
            raise ValueError("qext_w muss ein eindimensionales Array mit einer Länge gleich der Anzahl der Wärmetauscher sein.")

        # Erstellen eines DataFrames, wobei jede Spalte eine Zeitreihe für einen Wärmetauscher ist
        data = {f'qext_w_{i}': [qext_w[i]] * time_steps for i in range(len(qext_w))}
        df = pd.DataFrame(data, index=range(time_steps))
        data_source = DFData(df)

        # Update data source for ConstControl controllers
        for i in range(len(net.heat_exchanger)):
            for ctrl in net.controller.object.values:
                if isinstance(ctrl, ConstControl) and ctrl.element_index == i and ctrl.variable == 'qext_w':
                    ctrl.data_source = data_source
        
        # Aktualisieren der benutzerdefinierten Controller
        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ReturnTemperatureController):
                ctrl.target_temperature = target_temperature  # aktualisiere Zieltemperatur, wenn nötig
        
        log_variables = [('res_junction', 'p_bar'), ('res_junction', 't_k'), ('heat_exchanger', 'qext_w'), \
                         ('res_heat_exchanger', 'v_mean_m_per_s'), ('res_heat_exchanger', 't_to_k'), 
                        ('circ_pump_pressure', 't_flow_k'),  ('res_heat_exchanger', 'mdot_from_kg_per_s'),
                        ('res_circ_pump_pressure', 'mdot_flow_kg_per_s'), ('res_circ_pump_pressure', 'deltap_bar')]
        
        ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

        run_time_series.run_timeseries(net, time_steps, mode="all")
        
        return net

def time_series_net(net, temperature_target,  qext_w_profiles, calc1, calc2):
    time_steps = range(0, len(qext_w_profiles[0][calc1:calc2]))  # hourly time steps

    # Update data source for ConstControl controllers
    for i, qext_w_profile in enumerate(qext_w_profiles):
        qext_w_profile = qext_w_profile[calc1:calc2]
        df = pd.DataFrame(index=time_steps, data={'qext_w_' + str(i): qext_w_profile})
        data_source = DFData(df)

        # Durchlaufen aller Controller
        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ConstControl) and ctrl.element_index == i and ctrl.variable == 'qext_w':
                ctrl.data_source = data_source
    
    # Aktualisieren der benutzerdefinierten Controller
    for ctrl in net.controller.object.values:
        if isinstance(ctrl, ReturnTemperatureController):
            ctrl.target_temperature = temperature_target  # aktualisiere Zieltemperatur, wenn nötig
    
    log_variables = [('res_junction', 'p_bar'), ('res_junction', 't_k'),
                     ('heat_exchanger', 'qext_w'), ('res_heat_exchanger', 'v_mean_m_per_s'), 
                     ('res_heat_exchanger', 't_from_k'), ('res_heat_exchanger', 't_to_k'), 
                     ('circ_pump_pressure', 't_flow_k'),  ('res_heat_exchanger', 'mdot_from_kg_per_s'),
                     ('res_circ_pump_pressure', 'mdot_flow_kg_per_s'), ('res_circ_pump_pressure', 'deltap_bar')]
    
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(net, time_steps, mode="all", max_iter=50)

    return net, ow.np_results

def thermohydraulic_time_series_net_calculation(net, yearly_time_steps, waerme_ges_W, calc1, calc2, t_rl_soll=60):
    ### time series calculation ###

    time_steps = yearly_time_steps[calc1:calc2]
    net, net_results = time_series_net(net, t_rl_soll, waerme_ges_W, calc1, calc2)

    return time_steps, net, net_results

def calculate_results(net, net_results):
    ### Plotten Ergebnisse Pumpe / Einspeisung ###
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

    return mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions

def save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, filename):
    # Umwandeln von time_steps in ein allgemeineres datetime64[ns]-Format
    time_steps_ns = time_steps.astype('datetime64[ns]')
    
    # Konvertieren der Arrays in ein Pandas DataFrame
    df = pd.DataFrame({'Zeitpunkt': time_steps_ns, 
                       'Heizlast_Netz_kW': qext_kW, 
                       'Vorlauftemperatur_Netz_°C': flow_temp_circ_pump, 
                       'Rücklauftemperatur_Netz_°C': return_temp_circ_pump})

    # Speichern des DataFrames als CSV
    df.to_csv(filename, sep=';', index=False)

def import_results_csv(filename):
    data = pd.read_csv(filename, sep=';', parse_dates=['Zeitpunkt'])
    time_steps = data["Zeitpunkt"].values.astype('datetime64[15m]')
    qext_kW = data["Heizlast_Netz_kW"].values.astype('float64')
    flow_temp_circ_pump = data['Vorlauftemperatur_Netz_°C'].values.astype('float64')
    return_temp_circ_pump = data['Rücklauftemperatur_Netz_°C'].values.astype('float64')
    return time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump