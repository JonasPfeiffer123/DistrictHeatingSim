# Erstellt von Jonas Pfeiffer

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import matplotlib.pyplot as plt

import pandapipes as pp

from net_simulation_pandapipes.config_plot import config_plot


def initialize_test_net():
    net = pp.create_empty_network(fluid="water")

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

    pump1 = pp.create_circ_pump_const_pressure(net, j1, j2, p_flow_bar=4,
                                               plift_bar=1.5, t_flow_k=273.15 + 90,
                                               type="auto", name="pump1")

    pipe1 = pp.create_pipe(net, j2, j3, std_type="110_PE_100_SDR_17", length_km=0.01,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe1", sections=5,
                           text_k=283)
    pipe2 = pp.create_pipe(net, j3, j4, std_type="110_PE_100_SDR_17", length_km=0.05,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe2", sections=5,
                           text_k=283)
    pipe3 = pp.create_pipe(net, j4, j5, std_type="110_PE_100_SDR_17", length_km=0.025,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe3", sections=5,
                           text_k=283)
    
    j10 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 10", geodata=(85, 5))

    heat_exchanger1 = pp.create_heat_exchanger(net, j10, j6, diameter_m=0.04,
                                               loss_coefficient=100, qext_w=50000,
                                               name="heat_exchanger1")
    
    flow_control2 = pp.create_flow_control(net, j5, j10, controlled_mdot_kg_per_s=1, diameter_m=0.04)
    
    j9 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 9", geodata=(60, 5))
    
    heat_exchanger2 = pp.create_heat_exchanger(net, j9, j7, diameter_m=0.03,
                                               loss_coefficient=100, qext_w=50000,
                                               name="heat_exchanger1")
    
    flow_control1 = pp.create_flow_control(net, j4, j9, controlled_mdot_kg_per_s=2, diameter_m=0.03)

    pipe4 = pp.create_pipe(net, j6, j7, std_type="110_PE_100_SDR_17", length_km=0.25,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe4", sections=5,
                           text_k=283)
    pipe5 = pp.create_pipe(net, j7, j8, std_type="110_PE_100_SDR_17", length_km=0.05,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe5", sections=5,
                           text_k=283)
    pipe6 = pp.create_pipe(net, j8, j1, std_type="110_PE_100_SDR_17", length_km=0.01,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe6", sections=5,
                           text_k=283)

    pp.pipeflow(net, mode="all")
    return net

net = initialize_test_net()
print(net)

fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse

config_plot(net, ax, show_plot=True)

### hier noch weitere Tests mit der geojson-basierten Erstellungsmethode ###