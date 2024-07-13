# Erstellt von Jonas Pfeiffer
import time
import logging
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import matplotlib.pyplot as plt
import numpy as np
import pandapipes as pp
from pandapipes.control.run_control import run_control

from net_simulation_pandapipes.config_plot import config_plot

from net_simulation_pandapipes.pp_net_initialisation_geojson import *
from net_simulation_pandapipes.utilities import *

# Initialize logging
logging.basicConfig(level=logging.INFO)

def initialize_test_net(qext_w=np.array([50000, 100000]), return_temperature=60, supply_temperature=85, flow_pressure_pump=4, lift_pressure_pump=1.5, 
                        pipetype="KMR 100/250-2v",  pipe_creation_mode="type", v_max_m_s=1.5):
    
    net = pp.create_empty_network(fluid="water")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")

    ### get pipe properties
    properties = pipe_std_types.loc[pipetype]
    diameter_mm  = properties['inner_diameter_mm']
    k = properties['RAU']
    alpha = properties['WDZAHL']


    initial_mdot_guess_kg_s = qext_w / (4170*(supply_temperature-return_temperature))
    initial_Vdot_guess_m3_s = initial_mdot_guess_kg_s/1000
    area_m2 = initial_Vdot_guess_m3_s/v_max_m_s
    initial_dimension_guess_m = np.round(np.sqrt(area_m2 *(4/np.pi)), 3)

    # Junctions for pump
    j1 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 1", geodata=(0, 10))
    j2 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 2", geodata=(0, 0))

    # Junctions for connection pipes forward line
    j3 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 3", geodata=(10, 0))
    j4 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 4", geodata=(60, 0))

    # Junctions for heat exchangers
    j5 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 5", geodata=(85, 0))
    j6 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 6", geodata=(85, 10))
    
    # Junctions for connection pipes return line
    j7 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 7", geodata=(60, 10))
    j8 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 8", geodata=(10, 10))

    pump1 = pp.create_circ_pump_const_pressure(net, j1, j2, p_flow_bar=flow_pressure_pump,
                                               plift_bar=lift_pressure_pump, t_flow_k=273.15+supply_temperature,
                                               type="auto", name="pump1")

    pipe1 = pp.create_pipe(net, j2, j3, std_type=pipetype, length_km=0.01,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe1", sections=5,
                           text_k=283)
    pipe2 = pp.create_pipe(net, j3, j4, std_type=pipetype, length_km=0.05,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe2", sections=5,
                           text_k=283)
    pipe3 = pp.create_pipe(net, j4, j5, std_type=pipetype, length_km=0.025,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe3", sections=5,
                           text_k=283)
    
    j10 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 10", geodata=(85, 5))

    heat_exchanger1 = pp.create_heat_exchanger(net, j10, j6, diameter_m=initial_dimension_guess_m[0],
                                               loss_coefficient=0, qext_w=qext_w[0],
                                               name="heat_exchanger1")
    
    flow_control2 = pp.create_flow_control(net, j5, j10, controlled_mdot_kg_per_s=initial_mdot_guess_kg_s[0], diameter_m=initial_dimension_guess_m[0])
    
    j9 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 9", geodata=(60, 5))
    
    heat_exchanger2 = pp.create_heat_exchanger(net, j9, j7, diameter_m=initial_dimension_guess_m[1],
                                               loss_coefficient=0, qext_w=qext_w[1],
                                               name="heat_exchanger1")
    
    flow_control1 = pp.create_flow_control(net, j4, j9, controlled_mdot_kg_per_s=initial_mdot_guess_kg_s[1], diameter_m=initial_dimension_guess_m[1])

    pipe4 = pp.create_pipe(net, j6, j7, std_type=pipetype, length_km=0.25,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe4", sections=5,
                           text_k=283)
    pipe5 = pp.create_pipe(net, j7, j8, std_type=pipetype, length_km=0.05,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe5", sections=5,
                           text_k=283)
    pipe6 = pp.create_pipe(net, j8, j1, std_type=pipetype, length_km=0.01,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe6", sections=5,
                           text_k=283)
    
    net = create_controllers(net, qext_w, return_temperature)
    net = correct_flow_directions(net)

    return net

def get_test_net():
    qext_w = np.array([50000, 100000])
    return_temperature = np.array([55, 45])

    v_max_pipe = 1
    v_max_heat_exchanger = 2
    
    net = initialize_test_net(qext_w=qext_w, return_temperature=return_temperature, v_max_m_s=v_max_heat_exchanger)

    run_control(net, mode="all")

    net = optimize_diameter_types(net, v_max=v_max_pipe)
    net = optimize_diameter_parameters(net, element="heat_exchanger", v_max=v_max_heat_exchanger)
    net = optimize_diameter_parameters(net, element="flow_control", v_max=v_max_heat_exchanger)

    run_control(net, mode="all")

    fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse
    config_plot(net, ax, show_junctions=True, show_pipes=True, show_flow_controls=True, show_heat_exchangers=True, show_pump=True, show_plot=True)

def initialize_test_net_two_pumps(qext_w=np.array([50000, 100000]), return_temperature=60, supply_temperature=85, flow_pressure_pump=4, lift_pressure_pump=1.5, 
                        pipetype="KMR 100/250-2v",  pipe_creation_mode="type", v_max_m_s=1.5, mass_pump_mass_flow=0.1):
    
    net = pp.create_empty_network(fluid="water")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")

    ### get pipe properties
    properties = pipe_std_types.loc[pipetype]
    diameter_mm  = properties['inner_diameter_mm']
    k = properties['RAU']
    alpha = properties['WDZAHL']


    initial_mdot_guess_kg_s = qext_w / (4170*(supply_temperature-return_temperature))
    initial_Vdot_guess_m3_s = initial_mdot_guess_kg_s/1000
    area_m2 = initial_Vdot_guess_m3_s/v_max_m_s
    initial_dimension_guess_m = np.round(np.sqrt(area_m2 *(4/np.pi)), 3)

    # Junctions for pump
    j1 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 1", geodata=(0, 10))
    j2 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 2", geodata=(0, 0))

    # Junctions for connection pipes forward line
    j3 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 3", geodata=(10, 0))
    j4 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 4", geodata=(60, 0))

    # Junctions for heat exchangers
    j5 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 5", geodata=(85, 0))
    j6 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 6", geodata=(85, 10))
    
    # Junctions for connection pipes return line
    j7 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 7", geodata=(60, 10))
    j8 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 8", geodata=(10, 10))

    pump1 = pp.create_circ_pump_const_pressure(net, j1, j2, p_flow_bar=flow_pressure_pump,
                                               plift_bar=lift_pressure_pump, t_flow_k=273.15+supply_temperature,
                                               type="auto", name="pump1")

    pipe1 = pp.create_pipe(net, j2, j3, std_type=pipetype, length_km=0.01,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe1", sections=5,
                           text_k=283)
    pipe2 = pp.create_pipe(net, j3, j4, std_type=pipetype, length_km=0.05,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe2", sections=5,
                           text_k=283)
    pipe3 = pp.create_pipe(net, j4, j5, std_type=pipetype, length_km=0.025,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe3", sections=5,
                           text_k=283)
    
    j10 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 10", geodata=(85, 5))

    heat_exchanger1 = pp.create_heat_exchanger(net, j10, j6, diameter_m=initial_dimension_guess_m[0],
                                               loss_coefficient=0, qext_w=qext_w[0],
                                               name="heat_exchanger1")
    
    flow_control2 = pp.create_flow_control(net, j5, j10, controlled_mdot_kg_per_s=initial_mdot_guess_kg_s[0], diameter_m=initial_dimension_guess_m[0])
    
    j9 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 9", geodata=(60, 5))
    
    heat_exchanger2 = pp.create_heat_exchanger(net, j9, j7, diameter_m=initial_dimension_guess_m[1],
                                               loss_coefficient=0, qext_w=qext_w[1],
                                               name="heat_exchanger1")
    
    flow_control1 = pp.create_flow_control(net, j4, j9, controlled_mdot_kg_per_s=initial_mdot_guess_kg_s[1], diameter_m=initial_dimension_guess_m[1])

    pipe4 = pp.create_pipe(net, j6, j7, std_type=pipetype, length_km=0.25,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe4", sections=5,
                           text_k=283)
    pipe5 = pp.create_pipe(net, j7, j8, std_type=pipetype, length_km=0.05,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe5", sections=5,
                           text_k=283)
    pipe6 = pp.create_pipe(net, j8, j1, std_type=pipetype, length_km=0.01,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe6", sections=5,
                           text_k=283)
    
    ### here comes the part with the additional circ_pump_const_mass_flow ###
    # first of, the junctions
    j10 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 10", geodata=(100, 0))
    j11 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 11", geodata=(100, 10))

    pipe7 = pp.create_pipe(net, j5, j10, std_type=pipetype, length_km=0.05,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe7", sections=5,
                           text_k=283)
    pipe8 = pp.create_pipe(net, j11, j6, std_type=pipetype, length_km=0.01,
                           k_mm=k, alpha_w_per_m2k=alpha, name="pipe8", sections=5,
                           text_k=283)
    
    j12 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 11", geodata=(100, 5))

    
    pump2 = pp.create_circ_pump_const_mass_flow(net, j11, j12, p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=mass_pump_mass_flow, 
                                                t_flow_k=273.15+supply_temperature, type="auto", name="pump2")
    flow_control3 = pp.create_flow_control(net, j12, j10, controlled_mdot_kg_per_s=mass_pump_mass_flow, diameter_m=0.1)

    net = create_controllers(net, qext_w, return_temperature)
    net = correct_flow_directions(net)

    return net

def get_test_net_2():
    qext_w = np.array([50000, 100000])
    return_temperature = np.array([60, 30])
    v_max_pipe = 1
    v_max_heat_exchanger = 2

    net = initialize_test_net_two_pumps(qext_w=qext_w, return_temperature=return_temperature, v_max_m_s=v_max_heat_exchanger)

    run_control(net, mode="all")

    net = optimize_diameter_types(net, v_max=v_max_pipe)
    net = optimize_diameter_parameters(net, element="heat_exchanger", v_max=v_max_heat_exchanger)
    net = optimize_diameter_parameters(net, element="flow_control", v_max=v_max_heat_exchanger)

    run_control(net, mode="all")

    fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse
    config_plot(net, ax, show_junctions=True, show_pipes=True, show_flow_controls=True, show_heat_exchangers=True, show_pump=True, show_plot=True)

def check_controllers(net):
    for controller in net.controller.index:
        ctrl = net.controller.at[controller, 'object']
        if hasattr(ctrl, 'is_converged'):
            converged = ctrl.is_converged(net)
            logging.info(f"Controller {controller}: {ctrl}, Converged: {converged}")
            if not converged:
                logging.info(f"Controller {controller} details: {ctrl}")
        else:
            logging.info(f"Controller {controller}: {ctrl}, Converged attribute not found")

### hier noch weitere Tests mit der geojson-basierten Erstellungsmethode ###
# Example
def initialize_net_geojson():
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gdf_flow_line = gpd.read_file(f"{base_path}\project_data\Bad Muskau\Wärmenetz\Vorlauf.geojson", driver='GeoJSON')
    gdf_return_line = gpd.read_file(f"{base_path}\project_data\Bad Muskau\Wärmenetz\Rücklauf.geojson", driver='GeoJSON')
    gdf_heat_exchanger = gpd.read_file(f"{base_path}\project_data\Bad Muskau\Wärmenetz\HAST.geojson", driver='GeoJSON')
    gdf_heat_producer = gpd.read_file(f"{base_path}\project_data\Bad Muskau\Wärmenetz\Erzeugeranlagen.geojson", driver='GeoJSON')

    #gdf_flow_line = gpd.read_file(f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\Vorlauf.geojson", driver='GeoJSON')
    #gdf_return_line = gpd.read_file(f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\Rücklauf.geojson", driver='GeoJSON')
    #gdf_heat_exchanger = gpd.read_file(f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\HAST.geojson", driver='GeoJSON')
    #gdf_heat_producer = gpd.read_file(f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\Erzeugeranlagen.geojson", driver='GeoJSON')

    
    # Set a fixed random seed for reproducibility
    np.random.seed(42)

    #return_temperature = return_temperature_building_curve
    qext_w = np.random.randint(500, 1000000, size=len(gdf_heat_exchanger))
    return_temperature = np.random.randint(30, 60, size=len(gdf_heat_exchanger))

    v_max_pipe = 1
    v_max_heat_exchanger = 2
    
    # net generation from gis data
    net = create_network(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, return_temperature, supply_temperature=85, flow_pressure_pump=4, lift_pressure_pump=2, 
                        pipetype="KMR 100/250-2v",  pipe_creation_mode="type", v_max_m_s=v_max_heat_exchanger, v_max_pipe=v_max_pipe, material_filter="KMR", insulation_filter="2v")
    
    run_control(net, mode="all")

    logging.info("Starting pipe optimization")
    start_time = time.time()
    net = optimize_diameter_types(net, v_max=v_max_pipe, material_filter="KMR", insulation_filter="2v")
    logging.info(f"Pipe optimization finished in {time.time() - start_time:.2f} seconds")

    logging.info("Starting heat consumer optimization")
    start_time = time.time()
    net = optimize_diameter_parameters(net, element="heat_consumer", v_max=v_max_heat_exchanger)
    logging.info(f"Heat consumer optimization finished in {time.time() - start_time:.2f} seconds")

    # recalculate maximum and minimum mass flows in the controller
    net = recalculate_all_mass_flow_limits(net)

    run_control(net, mode="all")

    fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse
    # heat_consumer doesnt work at this point
    config_plot(net, ax, show_junctions=True, show_pipes=True,  show_heat_consumers=True, show_pump=True, show_plot=True)

    return net

def initialize_net_geojson2():
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vorlauf = f"{base_path}\project_data\Bad Muskau\Wärmenetz\Vorlauf.geojson"
    ruecklauf = f"{base_path}\project_data\Bad Muskau\Wärmenetz\Rücklauf.geojson"
    hast = f"{base_path}\project_data\Bad Muskau\Wärmenetz\HAST.geojson"
    erzeugeranlagen = f"{base_path}\project_data\Bad Muskau\Wärmenetz\Erzeugeranlagen.geojson"

    #vorlauf = f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\Vorlauf.geojson"
    #ruecklauf = f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\Rücklauf.geojson"
    #hast = f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\HAST.geojson"
    #erzeugeranlagen = f"H:/Arbeit/01_SMWK-NEUES Bearbeitung/04_Projekt Bad Muskau/03_Bearbeitung/Projektordner/Bad Muskau Quartier 3\Wärmenetz\Erzeugeranlagen.geojson"

    calc_method = "Datensatz" 
    #calc_method = "BDEW"
    #calc_method = "VDI4655"
    building_type = None
    #return_temperature_heat_consumer = None # 60, Erklärung
    return_temperature_heat_consumer = 55 # 60, Erklärung
    supply_temperature_net = 85 # alternative ist Gleitende Temperatur
    #supply_temperature = np.array([...]) # alternative ist Gleitende Temperatur
    min_supply_temperature_building = 65
    flow_pressure_pump = 4
    lift_pressure_pump = 1.5
    netconfiguration = "Niedertemperaturnetz"
    #netconfiguration = "wechselwarmes Netz"
    #netconfiguration = "kaltes Netz"
    pipetype = "KMR 100/250-2v"
    dT_RL = 5
    v_max_pipe = 1
    material_filter = "KMR"
    insulation_filter = "2v"
    v_max_heat_consumer = 1.5
    mass_flow_secondary_producers = 0.1 #placeholder
    TRY_filename = f"{base_path}\heat_requirement\TRY_511676144222\TRY2015_511676144222_Jahr.dat"
    COP_filename = f"{base_path}\heat_generators\Kennlinien WP.csv"

    net, yearly_time_steps, waerme_hast_ges_W, return_temperature_heat_consumer, supply_temperature_buildings, return_temperature_buildings, \
        supply_temperature_building_curve, return_temperature_building_curve, strombedarf_hast_ges_W, max_el_leistung_hast_ges_W = initialize_geojson(vorlauf, ruecklauf, hast, erzeugeranlagen, \
                                                                                TRY_filename, COP_filename, calc_method, building_type, \
                                                                                min_supply_temperature_building, return_temperature_heat_consumer, \
                                                                                supply_temperature_net, flow_pressure_pump, lift_pressure_pump, \
                                                                                netconfiguration, pipetype, dT_RL, v_max_pipe, material_filter, \
                                                                                insulation_filter, v_max_heat_consumer, mass_flow_secondary_producers)
    
    net = net_optimization(net, v_max_pipe, v_max_heat_consumer, material_filter, insulation_filter)

    fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse
    # heat_consumer doesnt work at this point
    config_plot(net, ax, show_junctions=True, show_pipes=True,  show_heat_consumers=True, show_pump=True, show_plot=True)

    return net

#get_test_net()
#get_test_net_2()
#initialize_net_geojson()
initialize_net_geojson2()