import numpy as np
import geopandas as gpd
import pandapipes as pp

from heat_requirement import heat_requirement_VDI4655, heat_requirement_BDEW
from net_simulation_pandapipes.utilities import create_controllers, correct_flow_directions, COP_WP, init_diameter_types

def initialize_geojson(vorlauf, ruecklauf, hast, erzeugeranlagen, calc_method, building_type, return_temperature, \
                       supply_temperature, flow_pressure_pump, lift_pressure_pump, netconfiguration, pipetype, dT_RL, \
                       v_max_pipe, material_filter, insulation_filter, mass_flow_secondary_producers=0.5):
        
    vorlauf = gpd.read_file(vorlauf, driver='GeoJSON')
    ruecklauf = gpd.read_file(ruecklauf, driver='GeoJSON')
    hast = gpd.read_file(hast, driver='GeoJSON')
    erzeugeranlagen = gpd.read_file(erzeugeranlagen, driver='GeoJSON')

    print(f"Vorlauftemperatur Netz: {supply_temperature} °C")

    supply_temperature_buildings = hast["VLT_max"].values.astype(float)
    print(f"Vorlauftemperatur Gebäude: {supply_temperature_buildings} °C")

    return_temperature_buildings = hast["RLT_max"].values.astype(float)
    print(f"Rücklauftemperatur Gebäude: {return_temperature_buildings} °C")

    if return_temperature == None:
        return_temperature = return_temperature_buildings + dT_RL
        print(f"Rücklauftemperatur HAST: {return_temperature} °C")
    else:
        return_temperature = np.full_like(return_temperature_buildings, return_temperature)
        print(f"Rücklauftemperatur HAST: {return_temperature} °C")

    if np.any(return_temperature >= supply_temperature):
        raise ValueError("Rücklauftemperatur darf nicht höher als die Vorlauftemperatur sein. Bitte überprüfen sie die Eingaben.")

    yearly_time_steps, waerme_gebaeude_ges_W, max_waerme_gebaeude_ges_W, supply_temperature_building_curve, \
    return_temperature_building_curve = generate_profiles_from_geojson(hast, building_type, calc_method, \
                                                                            supply_temperature_buildings, return_temperature_buildings)

    waerme_hast_ges_W = []
    max_waerme_hast_ges_W = []
    if netconfiguration == "kaltes Netz":
        COP, _ = COP_WP(supply_temperature_buildings, return_temperature)
        print(f"COP dezentrale Wärmepumpen Gebäude: {COP}")

        for waerme_gebaeude, leistung_gebaeude, cop in zip(waerme_gebaeude_ges_W, max_waerme_gebaeude_ges_W, COP):
            strom_wp = waerme_gebaeude/cop
            waerme_hast = waerme_gebaeude - strom_wp
            waerme_hast_ges_W.append(waerme_hast)

            stromleistung_wp = leistung_gebaeude/cop
            waerme_leistung_hast = leistung_gebaeude - stromleistung_wp
            max_waerme_hast_ges_W.append(waerme_leistung_hast)

        waerme_hast_ges_W = np.array(waerme_hast_ges_W)
        max_waerme_hast_ges_W = np.array(max_waerme_hast_ges_W)

    else:
        waerme_hast_ges_W = waerme_gebaeude_ges_W
        max_waerme_hast_ges_W = max_waerme_gebaeude_ges_W

    net = create_network(vorlauf, ruecklauf, hast, erzeugeranlagen, max_waerme_hast_ges_W, return_temperature, \
                            supply_temperature, flow_pressure_pump, lift_pressure_pump, pipetype, \
                            v_max_pipe, material_filter, insulation_filter, mass_flow_secondary_producers=mass_flow_secondary_producers)
    
    return net, yearly_time_steps, waerme_hast_ges_W, return_temperature, supply_temperature_buildings, return_temperature_buildings, \
        supply_temperature_building_curve, return_temperature_building_curve 
        
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
            YEU_heating_kWh, YEU_hot_water_kWh = YEU_total_heat_kWh * 0.8, YEU_total_heat_kWh * 0.2
            heating, hot_water = YEU_heating_kWh[idx], YEU_hot_water_kWh[idx]
            yearly_time_steps, electricity_kW, heating_kW, hot_water_kW, total_heat_kW, hourly_temperatures = heat_requirement_VDI4655.calculate(heating, hot_water, building_type=current_building_type)

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

def get_line_coords_and_lengths(gdf):
    all_line_coords, all_line_lengths = [], []
    # Berechnung der Länge jeder Linie
    gdf['length'] = gdf.geometry.length
    for index, row in gdf.iterrows():
        line = row['geometry']
        
        if line.geom_type == 'LineString':
            coords = list(line.coords)
            length = row['length']
            all_line_coords.append(coords)
            all_line_lengths.append(length)
        else:
            print(f"Geometrie ist kein LineString: {line.type}")

    return all_line_coords, all_line_lengths

def get_all_point_coords_from_line_cords(all_line_coords):
    point_coords = [koordinate for paar in all_line_coords for koordinate in paar]
    unique_point_coords = list(set(point_coords))
    return unique_point_coords

def create_network(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, return_temperature=60, supply_temperature=85, 
                   flow_pressure_pump=4, lift_pressure_pump=1.5, pipetype="KMR 100/250-2v", v_max_pipe=1, material_filter="KMR", insulation_filter="2v", 
                   pipe_creation_mode="type", v_max_m_s=2, main_producer_location_index=0, mass_flow_secondary_producers=0.5):
    net = pp.create_empty_network(fluid="water")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")

    properties = pipe_std_types.loc[pipetype]
    diameter_mm  = properties['inner_diameter_mm']
    k = properties['RAU']
    alpha = properties['WDZAHL']

    initial_mdot_guess_kg_s = qext_w / (4170*(supply_temperature-return_temperature))
    initial_Vdot_guess_m3_s = initial_mdot_guess_kg_s/1000
    area_m2 = initial_Vdot_guess_m3_s/(v_max_m_s*(1/1.5))       # Safety factor of 1.1
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
        for i, (coords, q, t, m, d) in enumerate(zip(all_coords, qext_w, return_temperature, initial_mdot_guess_kg_s, initial_dimension_guess_m)):
            pp.create_heat_consumer(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]], controlled_mdot_kg_per_s=m, diameter_m=d, 
                                    loss_coefficient=0, qext_w=q, name=f"{name_prefix} {i}") # treturn_k=t when implemented in function


    def create_circulation_pump_pressure(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")
            
    def create_circulation_pump_mass_flow(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            mid_coord = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
            mid_junction_idx = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {name_prefix}", geodata=mid_coord)

            pp.create_circ_pump_const_mass_flow(net_i, junction_dict[coords[1]], mid_junction_idx,
                                               p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=mass_flow_secondary_producers,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")
            pp.create_flow_control(net, mid_junction_idx, junction_dict[coords[0]], controlled_mdot_kg_per_s=mass_flow_secondary_producers, diameter_m=0.1)

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
    
    # heat producer preprocessing for multiple pumps
    all_heat_producer_coords, all_heat_producer_lengths = get_line_coords_and_lengths(gdf_heat_producer)
    # Sicherstellen, dass mindestens ein Koordinatenpaar vorhanden ist
    if all_heat_producer_coords:
        # creates the circulation pump const pressure for the first heat producer location // might implement some functionality to choose which one is main producer
        create_circulation_pump_pressure(net, [all_heat_producer_coords[main_producer_location_index]], {**junction_dict_vl, **junction_dict_rl}, "heat source")

        # creates circulation pump const mass flow for the remaining producer locations
        for i in range(len(all_heat_producer_coords)):
            if i != main_producer_location_index:
                create_circulation_pump_mass_flow(net, [all_heat_producer_coords[i]], {**junction_dict_vl, **junction_dict_rl}, "heat source slave")

    net = create_controllers(net, qext_w, return_temperature)
    net = correct_flow_directions(net)
    net = init_diameter_types(net, v_max_pipe=v_max_pipe, material_filter=material_filter, insulation_filter=insulation_filter)

    return net