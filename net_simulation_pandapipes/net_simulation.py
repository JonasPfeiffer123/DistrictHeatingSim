from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import geopandas as gpd
import pandas as pd

import net_simulation_pandapipes.net_simulation_calculation as nsp
from net_simulation_pandapipes.my_controllers import ReturnTemperatureController

def initialize_net(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA):
    pipe_creation_mode = "type"
    # pipe_creation_mode = "diameter"

    qext_w = 60000

    # net generation from gis data
    net = nsp.create_network(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w, pipe_creation_mode)
    net = nsp.correct_flow_directions(net)

    if pipe_creation_mode == "diameter":
        net = nsp.optimize_diameter_parameters(net)

    if pipe_creation_mode == "type":
        net = nsp.optimize_diameter_types(net)

    nsp.export_net_geojson(net)

    return(net)

def time_series_net(net, temperature_target,  qext_w_profiles, calc1, calc2):
    time_steps = range(0, len(qext_w_profiles[0][calc1:calc2]))  # hourly time steps

    # creates controllers for the net
    for i, qext_w_profile in enumerate(qext_w_profiles):
        qext_w_profile = qext_w_profile[calc1:calc2]
        df = pd.DataFrame(index=time_steps, data={'qext_w_' + str(i): qext_w_profile})
        data_source = DFData(df)

        # creates the controllers for the heat exchangers which controll qext_w in the timeseies
        ConstControl(net, element='heat_exchanger', variable='qext_w', element_index=[i], data_source=data_source, profile_name='qext_w_'+str(i))
        
        # creates the controllers for the heat exchangers / flow controls which controll the heat exchanger output temperature with the mass flows of the flow controls
        T_controller = ReturnTemperatureController(net, heat_exchanger_idx=i, target_temperature=temperature_target)
        net.controller.loc[len(net.controller)] = [T_controller, True, 0, 0, False, False]

    log_variables = [('res_junction', 'p_bar'), ('res_junction', 't_k'),
                     ('heat_exchanger', 'qext_w'), ('res_heat_exchanger', 'v_mean_m_per_s'), 
                     ('res_heat_exchanger', 't_from_k'), ('res_heat_exchanger', 't_to_k'), 
                     ('circ_pump_pressure', 't_flow_k'),  ('res_heat_exchanger', 'mdot_from_kg_per_s'),
                     ('res_circ_pump_pressure', 'mdot_flow_kg_per_s'), ('res_circ_pump_pressure', 'deltap_bar')]
    
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(net, time_steps, mode="all")

    return net, ow.np_results