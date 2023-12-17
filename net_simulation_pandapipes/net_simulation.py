from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import pandas as pd
import pandapipes as pp
import numpy as np

from net_simulation_pandapipes.net_simulation_calculation import *
from net_simulation_pandapipes.my_controllers import ReturnTemperatureController

from net_test import config_plot

def init_timeseries_opt(net, qext_w, time_steps=3, target_temperature=60):
        qext_w_profile = np.array([qext_w] * time_steps)
        data = {}
        for i in range(len(net.heat_exchanger)):
            data[f'qext_w_{i}'] = qext_w_profile

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

def initialize_net(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w=80000, pipe_creation_mode="type"):
    # net generation from gis data
    net = create_network(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w, pipe_creation_mode)
    net = create_controllers(net, qext_w)
    net = correct_flow_directions(net)
    net = init_timeseries_opt(net, qext_w=qext_w, time_steps=3, target_temperature=60)

    if pipe_creation_mode == "diameter":
        net = optimize_diameter_parameters(net)

    if pipe_creation_mode == "type":
        net = optimize_diameter_types(net)

    net = optimize_diameter_parameters(net, element="heat_exchanger", v_max=1.5, v_min=1.25)
    net = optimize_diameter_parameters(net, element="flow_control", v_max=1.5, v_min=1.25)

    export_net_geojson(net)

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

    run_time_series.run_timeseries(net, time_steps, mode="all")

    return net, ow.np_results