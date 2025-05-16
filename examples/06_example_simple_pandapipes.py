"""
Filename: 06_example_simple_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-12
Description: Script for testing the pandapipes net simulation functions.
Usage: Run the script to generate a simple pandapipes network.

Example:
    $ python 06_example_simple_pandapipes.py
"""

# needs fixes due to updated functions

import logging

import matplotlib.pyplot as plt
import numpy as np
import traceback
import pandapipes as pp
import pandapipes.plotting as pp_plot

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot
from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import *
from districtheatingsim.net_simulation_pandapipes.utilities import *
from districtheatingsim.heat_requirement import heat_requirement_calculation_csv

# Initialize logging
logging.basicConfig(level=logging.INFO)

def test_heat_consumer_result_extraction():
    print("Running the heat consumer result extraction script.")
    # Create a simple pandapipes network
    net = pp.create_empty_network("net", add_stdtypes=False, fluid="water")

    juncs = pp.create_junctions(
        net,
        nr_junctions=6,
        pn_bar=5,
        tfluid_k=85+273.15,
        system=["flow"] * 3 + ["return"] * 3,
        geodata=[
            (0, 0),    # Junction 0 (Startpunkt)
            (10, 0),   # Junction 1 (Vorlauf)
            (20, 0),   # Junction 2 (Vorlauf)
            (20, -10), # Junction 3 (Rücklauf)
            (10, -10), # Junction 4 (Rücklauf)
            (0, -10),  # Junction 5 (Endpunkt Rücklauf)
        ],
        name=[
            "Junction 0",      # Junction 0
            "Junction 1", # Junction 1
            "Junction 2", # Junction 2
            "Junction 3", # Junction 3
            "Junction 4", # Junction 4
            "Junction 5"         # Junction 5
        ]
    )
    pp.create_pipes_from_parameters(net, juncs[[0, 1, 3, 4]], juncs[[1, 2, 4, 5]], k_mm=0.1, length_km=0.5,
                                            diameter_m=0.1022, system=["flow"] * 2 + ["return"] * 2, alpha_w_per_m2k=0.4,
                                            text_k=273.15, name=[
            "Flow Pipe 1",  # Pipe von Source zu Flow Node 1
            "Flow Pipe 2",  # Pipe von Flow Node 1 zu Flow Node 2
            "Return Pipe 1", # Pipe von Return Node 1 zu Return Node 2
            "Return Pipe 2"  # Pipe von Return Node 2 zu Sink
        ])
    pp.create_circ_pump_const_pressure(net, juncs[-1], juncs[0], 5, 2, 85+273.15, type='auto', name="Pump 1")
    pp.create_heat_consumer(net, juncs[1], juncs[4], treturn_k=60+273.15, qext_w=7500, name="Heat Consumer 1")
    pp.create_heat_consumer(net, juncs[2], juncs[3], treturn_k=77+273.15, qext_w=7500, name="Heat Consumer 2")

    pp.pipeflow(net, mode="bidirectional", iter=100, alpha=0.2)

    return net

def initialize_test_net(qext_w=np.array([100000, 200000]),
                        return_temperature=np.array([55, 60]),
                        supply_temperature=85, 
                        flow_pressure_pump=4,
                        lift_pressure_pump=1.5,
                        pipetype="110/202 PLUS",
                        v_max_m_s=1.5):
    print("Running the test network initialization script.")
    net = pp.create_empty_network(fluid="water")

    k = 0.1 # roughness defaults to 0.1

    suply_temperature_k = supply_temperature + 273.15
    return_temperature_k = return_temperature + 273.15

    # Junctions for pump
    j1 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 1", geodata=(0, 10))
    j2 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 2", geodata=(0, 0))

    # Junctions for connection pipes forward line
    j3 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 3", geodata=(10, 0))
    j4 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 4", geodata=(60, 0))

    # Junctions for heat exchangers
    j5 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 5", geodata=(85, 0))
    j6 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 6", geodata=(85, 10))
    
    # Junctions for connection pipes return line
    j7 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 7", geodata=(60, 10))
    j8 = pp.create_junction(net, pn_bar=1.05, tfluid_k=suply_temperature_k, name="Junction 8", geodata=(10, 10))

    pump1 = pp.create_circ_pump_const_pressure(net, j1, j2, p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump, 
                                               t_flow_k=suply_temperature_k, type="auto", name="pump1")

    pipe1 = pp.create_pipe(net, j2, j3, std_type=pipetype, length_km=0.01, k_mm=k, name="pipe1", sections=5, text_k=283)
    pipe2 = pp.create_pipe(net, j3, j4, std_type=pipetype, length_km=0.05, k_mm=k, name="pipe2", sections=5, text_k=283)
    pipe3 = pp.create_pipe(net, j4, j5, std_type=pipetype, length_km=0.025,k_mm=k, name="pipe3", sections=5, text_k=283)

    heat_cosnumer1 = pp.create_heat_consumer(net, from_junction=j5, to_junction=j6, loss_coefficient=0, qext_w=qext_w[0], 
                                             treturn_k=return_temperature_k[0], name="heat_consumer_1") # treturn_k=t when implemented in function
    

    heat_cosnumer2 = pp.create_heat_consumer(net, from_junction=j4, to_junction=j7, loss_coefficient=0, qext_w=qext_w[1], 
                                             treturn_k=return_temperature_k[1], name="heat_consumer_2") # treturn_k=t when implemented in function
    
    pipe4 = pp.create_pipe(net, j6, j7, std_type=pipetype, length_km=0.25, k_mm=k, name="pipe4", sections=5, text_k=283)
    pipe5 = pp.create_pipe(net, j7, j8, std_type=pipetype, length_km=0.05, k_mm=k, name="pipe5", sections=5, text_k=283)
    pipe6 = pp.create_pipe(net, j8, j1, std_type=pipetype, length_km=0.01, k_mm=k, name="pipe6", sections=5, text_k=283)

    pp.pipeflow(net, mode="bidirectional", iter=100)
    
    net = create_controllers(net, qext_w, supply_temperature, None, return_temperature, None)
    net = correct_flow_directions(net)
    net = init_diameter_types(net, v_max_pipe=v_max_m_s, material_filter="PEXa", k=k)
    net = optimize_diameter_types(net, v_max=v_max_m_s, material_filter="PEXa", k=k)

    return net


def initialize_complex_test_net(qext_w=np.array([20000, 15000, 10000, 25000]),
                                return_temperature=np.array([55, 60, 50, 65]),
                                supply_temperature=85,
                                flow_pressure_pump=4,
                                lift_pressure_pump=1.5,
                                pipetype="110/202 PLUS",
                                v_max_m_s=1.5):
    print("Running the complex test network initialization script.")
    net = pp.create_empty_network(fluid="water")
    
    k = 0.1  # roughness
    supply_temperature_k = supply_temperature + 273.15  # convert to Kelvin
    return_temperature_k = return_temperature + 273.15  # convert to Kelvin

    # Define junctions
    j1 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Pump Supply", geodata=(0, 0))
    j2 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Main Split Supply", geodata=(10, 0))
    j12 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Main Split Return", geodata=(10, 10))
    j13 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Pump Return", geodata=(0, 10))

    # Additional junctions for new branches
    j3 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Consumer B Supply", geodata=(20, 0))
    j4 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Consumer B Return", geodata=(20, 10))
    j5 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Consumer C Supply", geodata=(30, 0))
    j6 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Consumer C Return", geodata=(30, 10))

    # Pump
    pp.create_circ_pump_const_pressure(net, j13, j1, p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump, 
                                       t_flow_k=supply_temperature_k, type="auto", name="Main Pump")

    # Pipes for supply line
    pp.create_pipe(net, j1, j2, std_type=pipetype, length_km=0.02, k_mm=k, name="Main Pipe Supply")
    pp.create_pipe(net, j2, j3, std_type=pipetype, length_km=0.03, k_mm=k, name="Branch B Pipe Supply")
    pp.create_pipe(net, j3, j5, std_type=pipetype, length_km=0.03, k_mm=k, name="Branch C Pipe Supply")

    # Pipes for return line
    pp.create_pipe(net, j6, j4, std_type=pipetype, length_km=0.03, k_mm=k, name="Branch C Pipe Return")
    pp.create_pipe(net, j4, j12, std_type=pipetype, length_km=0.03, k_mm=k, name="Branch B Pipe Return")
    pp.create_pipe(net, j12, j13, std_type=pipetype, length_km=0.02, k_mm=k, name="Main Pipe Return")

    # Heat consumers
    pp.create_heat_consumer(net, from_junction=j2, to_junction=j12, qext_w=qext_w[0], treturn_k=return_temperature_k[0], name="Consumer A")
    pp.create_heat_consumer(net, from_junction=j3, to_junction=j4, qext_w=qext_w[1], treturn_k=return_temperature_k[1], name="Consumer B")
    pp.create_heat_consumer(net, from_junction=j5, to_junction=j6, qext_w=qext_w[2], treturn_k=return_temperature_k[2], name="Consumer C")

    # Simulate pipe flow
    pp.pipeflow(net, mode="bidirectional", iter=100, alpha=0.2)

    # Placeholder functions for additional processing
    net = create_controllers(net, qext_w, supply_temperature, None, return_temperature, None)
    net = correct_flow_directions(net)
    net = init_diameter_types(net, v_max_pipe=v_max_m_s, material_filter="PEXa", k=k)
    net = optimize_diameter_types(net, v_max=v_max_m_s, material_filter="PEXa", k=k)

    return net

def initialize_test_net_two_pumps(qext_w=np.array([50000, 20000]),
                                  return_temperature=np.array([60,55]),
                                  supply_temperature=85,
                                  flow_pressure_pump=4,
                                  lift_pressure_pump=1.5,
                                  pipetype="110/202 PLUS",
                                  v_max_m_s=1.5,
                                  mass_pump_mass_flow=0.5):
    print("Running the test network with two pumps initialization script.")
    net = pp.create_empty_network(fluid="water")

    ### get pipe properties
    k = 0.1

    supply_temperature_k = supply_temperature + 273.15  # convert to Kelvin
    return_temperature_k = return_temperature + 273.15  # convert to Kelvin

    # Junctions for pump
    j1 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 1", geodata=(0, 10))
    j2 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 2", geodata=(0, 0))

    # Junctions for connection pipes forward line
    j3 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 3", geodata=(10, 0))
    j4 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 4", geodata=(60, 0))

    # Junctions for heat exchangers
    j5 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 5", geodata=(85, 0))
    j6 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 6", geodata=(85, 10))
    
    # Junctions for connection pipes return line
    j7 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 7", geodata=(60, 10))
    j8 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 8", geodata=(10, 10))

    pump1 = pp.create_circ_pump_const_pressure(net, j1, j2, p_flow_bar=flow_pressure_pump,
                                               plift_bar=lift_pressure_pump, t_flow_k=supply_temperature_k,
                                               type="auto", name="pump1")

    pipe1 = pp.create_pipe(net, j2, j3, std_type=pipetype, length_km=0.01, k_mm=k, name="pipe1", sections=5, text_k=283)
    pipe2 = pp.create_pipe(net, j3, j4, std_type=pipetype, length_km=0.05, k_mm=k, name="pipe2", sections=5, text_k=283)
    pipe3 = pp.create_pipe(net, j4, j5, std_type=pipetype, length_km=0.025, k_mm=k, name="pipe3", sections=5, text_k=283)

    pp.create_heat_consumer(net, from_junction=j5, to_junction=j6, qext_w=qext_w[0], treturn_k=return_temperature_k[0], name="Consumer A")
    pp.create_heat_consumer(net, from_junction=j4, to_junction=j7, qext_w=qext_w[1], treturn_k=return_temperature_k[1], name="Consumer B")
    
    pipe4 = pp.create_pipe(net, j6, j7, std_type=pipetype, length_km=0.25, k_mm=k, name="pipe4", sections=5, text_k=283)
    pipe5 = pp.create_pipe(net, j7, j8, std_type=pipetype, length_km=0.05, k_mm=k, name="pipe5", sections=5, text_k=283)
    pipe6 = pp.create_pipe(net, j8, j1, std_type=pipetype, length_km=0.01, k_mm=k, name="pipe6", sections=5, text_k=283)
    
    ### here comes the part with the additional circ_pump_const_mass_flow ###
    # first of, the junctions
    j9 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 9", geodata=(100, 0))
    j10 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 10", geodata=(100, 10))
    j11 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 11", geodata=(100, 5))

    pipe7 = pp.create_pipe(net, j5, j9, std_type=pipetype, length_km=0.05, k_mm=k, name="pipe7", sections=5, text_k=283)
    pipe8 = pp.create_pipe(net, j10, j6, std_type=pipetype, length_km=0.01, k_mm=k, name="pipe8", sections=5, text_k=283)

    pump2 = pp.create_circ_pump_const_mass_flow(net, j10, j11, p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=mass_pump_mass_flow, 
                                                t_flow_k=supply_temperature_k, type="auto", name="pump2")
    
    flow_control_pump2 = pp.create_flow_control(net, j11, j9, controlled_mdot_kg_per_s=mass_pump_mass_flow)

    # Simulate pipe flow
    pp.pipeflow(net, mode="bidirectional", iter=100)

    # Placeholder functions for additional processing
    net = create_controllers(net, qext_w, supply_temperature, None, return_temperature, None)
    net = correct_flow_directions(net)
    net = init_diameter_types(net, v_max_pipe=v_max_m_s, material_filter="PEXa", k=k)
    net = optimize_diameter_types(net, v_max=v_max_m_s, material_filter="PEXa", k=k)

    return net

def test_profile_initiation():
    print("Running the heat requirement script.")
        
    data = pd.read_csv("examples/data/data_ETRS89.csv", sep=";")
    TRY_filename = "src/districtheatingsim/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
    calc_method = "Datensatz"

    print(f"Data: {data}")

    # if data in column "Subtyp" is just one digit, add a leading zero
    data["Subtyp"] = data["Subtyp"].apply(lambda x: f"0{x}" if len(str(x)) == 1 else x)

    yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_requirement_W, supply_temperature_curve, \
        return_temperature_curve, hourly_air_temperatures = heat_requirement_calculation_csv.generate_profiles_from_csv(data, TRY_filename, calc_method)

    print("Initializing Net:")

    # qext_w is the max heat requirement in W
    qext_w = max_heat_requirement_W
    # return_temperature is the return temperature in °C, same size as qext_w array
    # np.fill like qext_w with 55
    return_temperature = np.full_like(qext_w, 55)
    supply_temperature = 85
    flow_pressure_pump = 4
    lift_pressure_pump = 1.5
    pipetype = "KMR 100/250-2v"
    v_max_m_s = 1.5

    net = initialize_test_net(qext_w=qext_w, return_temperature=return_temperature, supply_temperature=supply_temperature, 
                            flow_pressure_pump=flow_pressure_pump, lift_pressure_pump=lift_pressure_pump, pipetype=pipetype, 
                            v_max_m_s=v_max_m_s)

    return net

if __name__ == "__main__":
    try:
        #net = test_heat_consumer_result_extraction()
        #net = initialize_test_net()
        #net = initialize_complex_test_net()
        net = initialize_test_net_two_pumps()
        #net = test_profile_initiation()

        print(net)
        print(net.junction)
        print(net.pipe)
        print(net.heat_consumer)
        print(net.circ_pump_pressure)

        print(net.res_junction)
        print(net.res_pipe)
        print(net.res_heat_consumer)
        print(net.res_circ_pump_pressure)

        # create ax for config_plot
        fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse
        #pp_plot.simple_plot(net, junction_size=0.01, heat_consumer_size=0.1, pump_size=0.1, 
        #                    pump_color='green', pipe_color='black', heat_consumer_color="blue", ax=ax, show_plot=True)
        
        config_plot(net, ax, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_pump=True, show_plot=True)

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e