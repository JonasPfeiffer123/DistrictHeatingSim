from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import geopandas as gpd
import pandas as pd

import net_simulation_pandapipes.net_simulation_calculation as nsp

from net_simulation_pandapipes.my_controllers import ReturnTemperatureController

def initialize_net():
    # GeoJSON-Dateien einlesen
    gdf_vl = gpd.read_file('net_generation_QGIS/geoJSON_Vorlauf.geojson')
    gdf_rl = gpd.read_file('net_generation_QGIS/geoJSON_Rücklauf.geojson')
    gdf_HAST = gpd.read_file('net_generation_QGIS/geoJSON_HAST.geojson')
    gdf_WEA = gpd.read_file('net_generation_QGIS/geoJSON_Erzeugeranlagen.geojson')

    pipe_creation_mode = "type"
    # pipe_creation_mode = "diameter"

    qext_w = 60000
    net = nsp.create_network(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w, pipe_creation_mode)
    net = nsp.correct_flow_directions(net)

    if pipe_creation_mode == "diameter":
        net = nsp.optimize_diameter_parameters(net)

    if pipe_creation_mode == "type":
        net = nsp.optimize_diameter_types(net)

    nsp.export_net_geojson(net)

    return(net)

def time_series_net(net, temperature_target=60,  qext_w_profile=[50000] * 3 + [60000] * 6 + [70000] * 9 + [80000] * 6):
    time_steps = range(0, len(qext_w_profile))  # hourly time steps
    df = pd.DataFrame(index=time_steps)

    # Erstellen und Hinzufügen des Controllers zum Netz
    for i in range(len(net.heat_exchanger)):

        df = pd.DataFrame(index=time_steps, data={'qext_w_'+str(i): qext_w_profile})

        data_source = DFData(df)
        ConstControl(net, element='heat_exchanger', variable='qext_w', element_index=[i], data_source=data_source, profile_name='qext_w_'+str(i))
        
        # TemperatureController-Objekt erstellen
        T_controller = ReturnTemperatureController(net, heat_exchanger_idx=i, target_temperature=temperature_target)
        # Hinzufügen des Controller-Objekts zum DataFrame 'controller'
        net.controller.loc[len(net.controller)] = [T_controller, True, 0, 0, False, False]

    log_variables = [('res_junction', 'p_bar'), ('res_junction', 't_k'),
                     ('heat_exchanger', 'qext_w'), ('res_heat_exchanger', 'v_mean_m_per_s'), 
                     ('res_heat_exchanger', 't_from_k'), ('res_heat_exchanger', 't_to_k'), 
                     ('circ_pump_pressure', 't_flow_k'),  ('res_heat_exchanger', 'mdot_from_kg_per_s'),
                     ('res_circ_pump_pressure', 'mdot_flow_kg_per_s'), ('res_circ_pump_pressure', 'deltap_bar')]
    
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(net, time_steps, mode="all")

    return net, ow.np_results