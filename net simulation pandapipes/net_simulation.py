import pandapipes as pp
from pandapipes.timeseries import run_time_series
from pandapower.control.controller.const_control import ConstControl
from pandapower.timeseries import OutputWriter
from pandapower.timeseries import DFData

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

import net_simulation_pandapipes as nsp
from net_generation_test import initialize_test_net
from heat_requirement_VDI4655 import calculate

def initialize_net():
    # GeoJSON-Dateien einlesen
    gdf_vl = gpd.read_file('net generation QGIS/geoJSON_Vorlauf.geojson')
    gdf_rl = gpd.read_file('net generation QGIS/geoJSON_Rücklauf.geojson')
    gdf_HAST = gpd.read_file('net generation QGIS/geoJSON_HAST.geojson')
    gdf_WEA = gpd.read_file('net generation QGIS/geoJSON_Erzeugeranlagen.geojson')

    pipe_creation_mode = "type"
    # pipe_creation_mode = "diameter"

    qext_w = 60000
    net = nsp.create_network(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w, pipe_creation_mode)
    net = nsp.correct_flow_directions(net)

    if pipe_creation_mode == "diameter":
        net = nsp.optimize_diameter_parameters(net)

    if pipe_creation_mode == "type":
        net = nsp.optimize_diameter_types(net)

    #plot.simple_plot(net, junction_size=0.2, heat_exchanger_size=0.2, pump_size=0.2, pump_color='green',
     #                pipe_color='black', heat_exchanger_color='blue')

    nsp.export_net_geojson(net)

    # print(net.junction)
    # print(net.junction_geodata)
    # print(net.pipe)
    # print(net.heat_exchanger)
    # print(net.circ_pump_pressure)

    # print(net.res_junction)
    # print(net.res_pipe)
    # print(net.res_heat_exchanger)
    # print(net.res_circ_pump_pressure)

    return(net)

def time_series_net(net, qext_w_profile=[50000] * 3 + [60000] * 6 + [70000] * 9 + [80000] * 6):
    time_steps = range(0, len(qext_w_profile))  # hourly time steps
    df = pd.DataFrame(index=time_steps)

    for i in range(1):

        df = pd.DataFrame(index=time_steps, data={'qext_w_'+str(i): qext_w_profile})

        data_source = DFData(df)
        ConstControl(net, element='heat_exchanger', variable='qext_w', element_index=[i], data_source=data_source, profile_name='qext_w_'+str(i))

    log_variables = [('res_junction', 'p_bar'), ('res_pipe', 'v_mean_m_per_s'),
                     ('res_pipe', 'reynolds'), ('res_pipe', 'lambda'), ('heat_exchanger', 'qext_w'),
                     ('res_heat_exchanger', 'v_mean_m_per_s'), ('res_heat_exchanger', 't_from_k'),
                     ('res_heat_exchanger', 't_to_k'), ('circ_pump_pressure', 't_flow_k'), ('res_junction', 't_k')]
    
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(net, time_steps, mode="all")

    # print("temperature:")
    # print(ow.np_results["res_junction.t_k"])

    x = time_steps
    y1 = ow.np_results["res_heat_exchanger.t_from_k"]
    y2 = ow.np_results["res_heat_exchanger.t_to_k"]
    
    plt.xlabel("time step")
    plt.ylabel("temperature [K]")
    plt.title("temperature profile heat exchangers")
    plt.plot(x, y1[:,0], "g-o")
    plt.plot(x, y2[:,0], "b-o")
    plt.legend(["heat exchanger 1 from", "heat exchanger 1 to"], loc='lower left')
    plt.grid()
    plt.show()


net = initialize_net()
# test_net = initialize_test_net()

print(net.res_junction)
time_series_net(net)

net = initialize_net()
nsp.calculate_worst_point(net)

JEB_Wärme_ges_kWh = 50000
JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh = JEB_Wärme_ges_kWh*0.2, JEB_Wärme_ges_kWh*0.8
time_15min, _, _, _, waerme_ges_kW = calculate(JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh)

plt.plot(time_15min[2000:3000], waerme_ges_kW[2000:3000], label="Wärmeleistung gesamt")
plt.title("Jahresdauerlinie")
plt.legend()
plt.xlabel("Zeit in 15 min Schritten")
plt.ylabel("Wärmebedarf in kW / 15 min")
plt.show()