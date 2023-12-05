import pandapipes as pp
import geopandas as gpd
from shapely.geometry import LineString

# Zugriff auf die Koordinaten jeder Linie
def get_line_coords_and_lengths(gdf):
    all_line_coords, all_line_lengths = [], []
    # Berechnung der Länge jeder Linie
    gdf['length'] = gdf.geometry.length
    for index, row in gdf.iterrows():
        line = row['geometry']
        
        # Überprüfen, ob die Geometrie ein LineString ist
        if line.geom_type == 'LineString':
            # Zugriff auf die Koordinatenpunkte
            coords = list(line.coords)
            length = row['length']
            all_line_coords.append(coords)
            all_line_lengths.append(length)
        else:
            print(f"Geometrie ist kein LineString: {line.type}")

    return all_line_coords, all_line_lengths


def get_all_point_coords_from_line_cords(all_line_coords):
    point_coords = [koordinate for paar in all_line_coords for koordinate in paar]
    # Entfernen von Duplikaten
    unique_point_coords = list(set(point_coords))
    return unique_point_coords


def create_network(gdf_vorlauf, gdf_rl, gdf_hast, gdf_wea, qext_w=50000, pipe_creation_mode="diameter", supply_temperature=85,
                   flow_pressure_pump=4, lift_pressure_pump=1.5, massflow_mass_pump=4, diameter_mm=100, pipetype = "110_PE_100_SDR_17", k=0.1, alpha=10):

    def create_junctions_from_coords(net_i, all_coords):
        junction_dict = {}
        for i, coords in enumerate(all_coords, start=0):
            junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {i}", geodata=coords) # pn_bar and tfluid_k just for initialization
            junction_dict[coords] = junction_id
        return junction_dict

    def create_pipes_diameter(net_i, all_line_coords, all_line_lengths, junction_dict, pipe_type, diameter_mm):
        for coords, length_m, i in zip(all_line_coords, all_line_lengths, range(0, len(all_line_coords))):
            pp.create_pipe_from_parameters(net_i, from_junction=junction_dict[coords[0]],
                                           to_junction=junction_dict[coords[1]], length_km=length_m/1000,
                                           diameter_m=diameter_mm/1000, k_mm=k, alpha_w_per_m2k=alpha, name=f"{pipe_type} Pipe {i}",
                                           geodata=coords, sections=5, text_k=283)

    def create_pipes_type(net_i, all_line_coords, all_line_lengths, junction_dict, line_type, pipetype):
        for coords, length_m, i in zip(all_line_coords, all_line_lengths, range(0, len(all_line_coords))):
            pp.create_pipe(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]],
                           std_type=pipetype, length_km=length_m/1000, k_mm=k, alpha_w_per_m2k=alpha,
                           name=f"{line_type} Pipe {i}", geodata=coords, sections=5, text_k=283)

    def create_heat_exchangers(net_i, all_coords, q_heat_exchanger, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            # Berechnung der mittleren Koordinate
            mid_coord = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)

            # Sie müssen hier eine Funktion haben, um eine neue Junction an mid_coord zu erstellen
            mid_junction_idx = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {name_prefix}", geodata=mid_coord)
            pp.create_flow_control(net_i, from_junction=junction_dict[coords[0]], to_junction=mid_junction_idx, controlled_mdot_kg_per_s=0.5, diameter_m=0.02)

            pp.create_heat_exchanger(net_i, from_junction=mid_junction_idx, to_junction=junction_dict[coords[1]], diameter_m=0.02, loss_coefficient=500,
                                     qext_w=q_heat_exchanger, name=f"{name_prefix} {i}")

    def create_circulation_pump_pressure(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")

    net = pp.create_empty_network(fluid="water")

    # Verarbeiten von Vorlauf und Rücklauf
    junction_dict_vl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_vorlauf)[0]))
    junction_dict_rl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_rl)[0]))

    # Erstellen der Pipes
    if pipe_creation_mode == "diameter":
        create_pipes_diameter(net, *get_line_coords_and_lengths(gdf_vorlauf), junction_dict_vl, "forward line", diameter_mm)
        create_pipes_diameter(net, *get_line_coords_and_lengths(gdf_rl), junction_dict_rl, "return line", diameter_mm)

    if pipe_creation_mode == "type":
        create_pipes_type(net, *get_line_coords_and_lengths(gdf_vorlauf), junction_dict_vl, "forward line", pipetype)
        create_pipes_type(net, *get_line_coords_and_lengths(gdf_rl), junction_dict_rl, "retunr line", pipetype)

    # Erstellen der Heat Exchangers
    create_heat_exchangers(net, get_line_coords_and_lengths(gdf_hast)[0], qext_w,
                           {**junction_dict_vl, **junction_dict_rl}, "heat exchanger")
    
    # Erstellen der circulation pump pressure
    create_circulation_pump_pressure(net, get_line_coords_and_lengths(gdf_wea)[0], {**junction_dict_vl, **junction_dict_rl}, "heat source")

    return net


def correct_flow_directions(net):
    # initiale Pipeflow-Berechnung
    pp.pipeflow(net, mode="all")

    # Überprüfen Sie die Geschwindigkeiten in jeder Pipe und tauschen Sie die Junctions bei Bedarf
    for pipe_idx in net.pipe.index:
        # Überprüfen Sie die mittlere Geschwindigkeit in der Pipe
        if net.res_pipe.v_mean_m_per_s[pipe_idx] < 0:
            # Tauschen Sie die Junctions
            from_junction = net.pipe.at[pipe_idx, 'from_junction']
            to_junction = net.pipe.at[pipe_idx, 'to_junction']
            net.pipe.at[pipe_idx, 'from_junction'] = to_junction
            net.pipe.at[pipe_idx, 'to_junction'] = from_junction

    # Führen Sie die Pipeflow-Berechnung erneut durch, um aktualisierte Ergebnisse zu erhalten
    pp.pipeflow(net, mode="all")

    return net


def optimize_diameter_parameters(initial_net, v_max=1, v_min=0.8, dx=0.001):
    pp.pipeflow(initial_net, mode="all")
    velocities = list(initial_net.res_pipe.v_mean_m_per_s)
    
    while max(velocities) > v_max or min(velocities) < v_min:
        for pipe_idx in initial_net.pipe.index:
            # Überprüfen Sie die mittlere Geschwindigkeit in der Pipe
            if initial_net.res_pipe.v_mean_m_per_s[pipe_idx] > v_max:
                # Durchmesser vergrößern
                initial_net.pipe.at[pipe_idx, 'diameter_m'] = initial_net.pipe.at[pipe_idx, 'diameter_m'] + dx
            elif initial_net.res_pipe.v_mean_m_per_s[pipe_idx] < v_min:
                # Durchmesser verkleinern
                initial_net.pipe.at[pipe_idx, 'diameter_m'] = initial_net.pipe.at[pipe_idx, 'diameter_m'] - dx
        pp.pipeflow(initial_net, mode="all")
        velocities = list(initial_net.res_pipe.v_mean_m_per_s)

    return initial_net

def optimize_diameter_types(net, v_max=1.1, v_min=0.7):
    pp.pipeflow(net, mode="all")
    velocities = list(net.res_pipe.v_mean_m_per_s)

    # Auflisten aller verfügbaren Standardtypen für Rohre
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    # Filtern nach einem bestimmten Material, z.B. "PE 100"
    filtered_pipe_types = pipe_std_types[pipe_std_types['material'] == 'PE 100']

    # Erstellen eines Dictionarys, das die Position jedes Rohrtyps im gefilterten DataFrame enthält
    type_position_dict = {type_name: i for i, type_name in enumerate(filtered_pipe_types.index)}
    
    while any(v > v_max or v < v_min for v in net.res_pipe.v_mean_m_per_s):
        for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
            current_type = net.pipe.std_type.at[pipe_idx]
            current_type_position = type_position_dict[current_type]

            if velocity > v_max and current_type_position > 0:
                 # Aktualisieren Sie den Rohrtyp auf den vorherigen Typ
                new_type = filtered_pipe_types.index[current_type_position + 1]
                net.pipe.std_type.at[pipe_idx] = new_type
                # Aktualisieren Sie die Eigenschaften des Rohres
                properties = filtered_pipe_types.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000

            elif velocity < v_min and current_type_position < len(filtered_pipe_types) - 1:
                # Aktualisieren Sie den Rohrtyp auf den nächsten Typ
                new_type = filtered_pipe_types.index[current_type_position - 1]
                net.pipe.std_type.at[pipe_idx] = new_type
                # Aktualisieren Sie die Eigenschaften des Rohres
                properties = filtered_pipe_types.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                
        pp.pipeflow(net, mode="all")
        velocities = list(net.res_pipe.v_mean_m_per_s)

    return net

def export_net_geojson(net):
    # check ig geographical data is available
    if 'pipe_geodata' in net and not net.pipe_geodata.empty:
        # convert the data to a GeoDataFrame
        gdf = gpd.GeoDataFrame(net.pipe_geodata)
        gdf['geometry'] = gdf['coords'].apply(lambda x: LineString(x))
        del gdf['coords']

        # adding attribute 'diameter_m'
        gdf['diameter_mm'] = net.pipe['diameter_m'] / 1000
    
        # set crs (here EPSG:4326)
        gdf.set_crs(epsg=25833, inplace=True)

        # export as GeoJSON
        gdf.to_file("pipes_network.geojson", driver='GeoJSON')
    else:
        print("No geographical data available in the network.")

def calculate_worst_point(net):
    # with this function, the worst point in the heating network is being calculated
    # specificially the worst point is defined as the heat exchanger with the lowest pressure difference between the forward and the return line, resulting in a lower mass flow
    # after finding the worst point a differential pressure control for the circulation pump could be implemented

    dp = []

    for idx, p_from, p_to in zip(net.heat_exchanger.index, net.res_heat_exchanger["p_from_bar"], net.res_heat_exchanger["p_to_bar"]):
        dp_diff = p_from - p_to
        dp_diff = p_from - p_to
        dp.append((dp_diff, idx))

    # Finden der minimalen Druckdifferenz und des zugehörigen Index
    dp_min, idx_min = min(dp, key=lambda x: x[0])

    return dp_min, idx_min