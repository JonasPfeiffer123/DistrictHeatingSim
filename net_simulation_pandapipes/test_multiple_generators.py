import pandapipes as pp
import numpy as np

from net_simulation_calculation import get_line_coords_and_lengths, get_all_point_coords_from_line_cords

def create_network(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, return_temperature=60, supply_temperature=85, 
                   flow_pressure_pump=4, lift_pressure_pump=1.5, pipetype="KMR 100/250-2v",  pipe_creation_mode="type"):
    net = pp.create_empty_network(fluid="water")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")

    properties = pipe_std_types.loc[pipetype]
    diameter_mm  = properties['inner_diameter_mm']
    k = properties['RAU']
    alpha = properties['WDZAHL']

    initial_mdot_guess_kg_s = qext_w / (4170*(supply_temperature-return_temperature))
    initial_Vdot_guess_m3_s = initial_mdot_guess_kg_s/1000
    v_max_m_s = 1.5
    area_m2 = initial_Vdot_guess_m3_s/v_max_m_s
    initial_dimension_guess_m = np.round(np.sqrt(area_m2 *(4/np.pi)), 3)

    def create_junctions_from_coords(net_i, all_coords):
        junction_dict = {}
        for i, coords in enumerate(all_coords, start=0):
            junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {i}", geodata=coords) # pn_bar and tfluid_k just for initialization
            junction_dict[coords] = junction_id
        return junction_dict

    def create_pipes(net_i, all_line_coords, all_line_lengths, junction_dict, pipe_mode, pipe_type_or_diameter, line_type):
        for coords, length_m, i in zip(all_line_coords, all_line_lengths, range(len(all_line_coords))):
            if pipe_mode == "diameter":
                diameter_mm = pipe_type_or_diameter
                pipe_name = line_type
                pp.create_pipe_from_parameters(net_i, from_junction=junction_dict[coords[0]],
                                            to_junction=junction_dict[coords[1]], length_km=length_m/1000,
                                            diameter_m=diameter_mm/1000, k_mm=k, alpha_w_per_m2k=alpha, 
                                            name=pipe_name, geodata=coords, sections=5, text_k=283)
            elif pipe_mode == "type":
                pipetype = pipe_type_or_diameter
                pipe_name = line_type
                pp.create_pipe(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]],
                            std_type=pipetype, length_km=length_m/1000, k_mm=k, alpha_w_per_m2k=alpha,
                            name=pipe_name, geodata=coords, sections=5, text_k=283)


    def create_heat_exchangers(net_i, all_coords, junction_dict, name_prefix):
        for i, (coords, q, m, d) in enumerate(zip(all_coords, qext_w, initial_mdot_guess_kg_s, initial_dimension_guess_m)):
            # creates a middle coordinate to place the flow control an the heat exchanger
            mid_coord = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
            mid_junction_idx = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {name_prefix}", geodata=mid_coord)

            pp.create_flow_control(net_i, from_junction=junction_dict[coords[0]], to_junction=mid_junction_idx, controlled_mdot_kg_per_s=m, diameter_m=d)

            pp.create_heat_exchanger(net_i, from_junction=mid_junction_idx, to_junction=junction_dict[coords[1]], diameter_m=d, loss_coefficient=0,
                                     qext_w=q, name=f"{name_prefix} {i}")

    def create_circulation_pump_pressure(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")

    # creates the junction dictonaries for the forward an return line
    junction_dict_vl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_flow_line)[0]))
    junction_dict_rl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_return_line)[0]))

    # creates the pipes
    create_pipes(net, *get_line_coords_and_lengths(gdf_flow_line), junction_dict_vl, pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "flow line")
    create_pipes(net, *get_line_coords_and_lengths(gdf_return_line), junction_dict_rl, pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "return line")
    
    # creates the heat exchangers
    create_heat_exchangers(net, get_line_coords_and_lengths(gdf_heat_exchanger)[0], {**junction_dict_vl, **junction_dict_rl}, "heat exchanger")
    
    # creates the circulation pump pressure
    create_circulation_pump_pressure(net, get_line_coords_and_lengths(gdf_heat_producer)[0], {**junction_dict_vl, **junction_dict_rl}, "heat source")

    return net