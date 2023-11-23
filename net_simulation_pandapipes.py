import pandapipes as pp


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


def create_network(gdf_vorlauf, gdf_rl, gdf_hast, gdf_wea):
    def create_junctions_from_coords(net_i, all_coords):
        junction_dict = {}
        for i, coords in enumerate(all_coords, start=0):
            junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {i}", geodata=coords)
            junction_dict[coords] = junction_id
        return junction_dict

    def create_pipes(net_i, all_line_coords, all_line_lengths, junction_dict, pipe_type):
        for coords, length, i in zip(all_line_coords, all_line_lengths, range(0, len(all_line_coords))):
            pp.create_pipe_from_parameters(
                net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]],
                length_km=length / 1000, diameter_m=0.05, k_mm=.1, alpha_w_per_m2k=10, name=f"{pipe_type} Pipe {i}",
                sections=5, text_k=283)

    def create_heat_exchangers(net_i, all_coords, q_heat_exchanger, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_heat_exchanger(net_i, from_junction=junction_dict[coords[0]],
                                     to_junction=junction_dict[coords[1]], diameter_m=0.02, loss_coefficient=100,
                                     qext_w=q_heat_exchanger, name=f"{name_prefix} {i}")

    def create_circulation_pump_pressure(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=4, plift_bar=1.5, t_flow_k=273.15 + 90, type="auto",
                                               name=f"{name_prefix} {i}")

    net = pp.create_empty_network(fluid="water")

    # Verarbeiten von Vorlauf und Rücklauf
    junction_dict_vl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_vorlauf)[0]))
    junction_dict_rl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_rl)[0]))

    # Erstellen der Pipes
    create_pipes(net, *get_line_coords_and_lengths(gdf_vorlauf), junction_dict_vl, "Vorlauf")
    create_pipes(net, *get_line_coords_and_lengths(gdf_rl), junction_dict_rl, "Rücklauf")

    # Erstellen der Heat Exchangers
    create_heat_exchangers(net, get_line_coords_and_lengths(gdf_hast)[0], 60000,
                           {**junction_dict_vl, **junction_dict_rl}, "HAST")

    # Erstellen der circulation pump pressure
    create_circulation_pump_pressure(net, get_line_coords_and_lengths(gdf_wea)[0], {**junction_dict_vl,
                                                                                    **junction_dict_rl}, "WEA")
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


def optimize_diameter_types(initial_net, v_max=1, v_min=0.8):
    pp.pipeflow(initial_net, mode="all")
    velocities = list(initial_net.res_pipe.v_mean_m_per_s)

    while max(velocities) > v_max or min(velocities) < v_min:
        for pipe_idx in initial_net.pipe.index:
            # Überprüfen Sie die mittlere Geschwindigkeit in der Pipe
            if initial_net.res_pipe.v_mean_m_per_s[pipe_idx] > v_max:
                # Durchmesser vergrößern
                initial_net.pipe.at[pipe_idx, 'std_type'] = -1  # kleinerer Typ
            elif initial_net.res_pipe.v_mean_m_per_s[pipe_idx] < v_min:
                # Durchmesser verkleinern
                initial_net.pipe.at[pipe_idx, 'std_type'] = +1  # größerer Typ
        pp.pipeflow(initial_net, mode="all")
        velocities = list(initial_net.res_pipe.v_mean_m_per_s)

    return initial_net

def export_net_geojson(net):
    print("Hier könnte deine geoJSON-Datei exportiert werden.")