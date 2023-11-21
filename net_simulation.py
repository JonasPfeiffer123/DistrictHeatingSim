import pandapipes as pp
import pandapipes.plotting as plot
import geopandas as gpd
import net_simulation_pandapipes as nsp

# GeoJSON-Dateien einlesen
gdf_vl = gpd.read_file('Vorlauf.geojson')
gdf_rl = gpd.read_file('Rücklauf.geojson')
gdf_HAST = gpd.read_file('HAST.geojson')
gdf_WEA = gpd.read_file('Erzeugeranlagen.geojson')


net = nsp.create_network(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA)

net = nsp.correct_flow_directions(net)

net = nsp.optimize_diameter_parameters(net)

# Auflisten aller verfügbaren Standardtypen für Rohre
pipe_std_types = pp.std_types.available_std_types(net, "pipe")
# print(pipe_std_types)

# print(net.junction)
# print(net.junction_geodata)
# print(net.pipe)
# print(net.heat_exchanger)
# print(net.circ_pump_pressure)

# print(net.res_junction)
# print(net.res_pipe)
# print(net.res_heat_exchanger)
# print(net.res_circ_pump_pressure)

plot.simple_plot(net, junction_size=0.2, heat_exchanger_size=0.2, pump_size=0.2, pump_color='green',
                 pipe_color='black', heat_exchanger_color='blue')
