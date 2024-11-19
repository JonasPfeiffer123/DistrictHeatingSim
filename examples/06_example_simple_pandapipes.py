"""
Filename: 06_example_simple_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Script for testing the pandapipes net simulation functions.
Usage: Run the script to generate a simple pandapipes network.
Functions:
    initialize_test_net(qext_w=np.array([50000, 100000]), return_temperature=60, supply_temperature=85, flow_pressure_pump=4, lift_pressure_pump=1.5, pipetype="KMR 100/250-2v",  pipe_creation_mode="type", v_max_m_s=1.5) -> None
        Initializes a simple pandapipes network.
    get_test_net() -> None
        Initializes a simple pandapipes network and plots it.
    initialize_test_net_two_pumps(qext_w=np.array([50000, 100000]), return_temperature=60, supply_temperature=85, flow_pressure_pump=4, lift_pressure_pump=1.5, pipetype="KMR 100/250-2v",  pipe_creation_mode="type", v_max_m_s=1.5, mass_pump_mass_flow=0.1) -> None
        Initializes a simple pandapipes network with two pumps.
    get_test_net_2() -> None
        Initializes a simple pandapipes network with two pumps and plots it.
Example:
    $ python 06_example_simple_pandapipes.py
"""

# needs fixes due to updated functions

import logging

import matplotlib.pyplot as plt
import numpy as np
import pandapipes as pp
from pandapipes.control.run_control import run_control

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import *
from districtheatingsim.net_simulation_pandapipes.utilities import *

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

if __name__ == "__main__":
    get_test_net()
    get_test_net_2()