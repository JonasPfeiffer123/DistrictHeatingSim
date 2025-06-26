"""
Filename: 07_example_timeseries_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-12
Description: Script for testing the pandapipes net simulation functions.
Usage: Run the script to generate a simple pandapipes network.

Example:
    $ python 07_example_timeseries_pandapipes.py
"""

import traceback
import logging
# Initialize logging
logging.basicConfig(level=logging.INFO)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import pandapipes as pp
import pandapipes.plotting as pp_plot
from pandapipes.timeseries import run_time_series
from pandapower.timeseries import OutputWriter

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot
from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import *
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import *
from districtheatingsim.net_simulation_pandapipes.utilities import *

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot

def initialize_test_net(qext_w=np.array([100000, 100000, 100000]),
                        return_temperature=np.array([55, 60, 50]),
                        supply_temperature=85,
                        flow_pressure_pump=4, 
                        lift_pressure_pump=1.5,
                        pipetype="110/202 PLUS",
                        v_max_m_s=1.5):
    print("Initializing test network...")
    # Initialize the pandapipes network
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
    pp.create_pipe(net, j1, j2, std_type=pipetype, length_km=0.2, k_mm=k, name="Main Pipe Supply")
    pp.create_pipe(net, j2, j3, std_type=pipetype, length_km=0.3, k_mm=k, name="Branch B Pipe Supply")
    pp.create_pipe(net, j3, j5, std_type=pipetype, length_km=0.3, k_mm=k, name="Branch C Pipe Supply")

    # Pipes for return line
    pp.create_pipe(net, j12, j13, std_type=pipetype, length_km=0.2, k_mm=k, name="Main Pipe Return")
    pp.create_pipe(net, j4, j12, std_type=pipetype, length_km=0.3, k_mm=k, name="Branch B Pipe Return")
    pp.create_pipe(net, j6, j4, std_type=pipetype, length_km=0.3, k_mm=k, name="Branch C Pipe Return")

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


def timeseries_test(net):
    print("Running time series test...")
    start = 0
    end = 8 # 8760 hours in a year

    # time steps with start and end
    time_steps = np.arange(start, end, 1)	# time steps in hours

    # yearly time steps with dates beginning at 01.01.2021 00:00:00
    yearly_time_steps = pd.date_range(start="2021-01-01 00:00:00", periods=end, freq="H")

    # np.random.seed() is used to make the random numbers predictable
    np.random.seed(0)
    # for every time step for every heat consumer qext_w needs to be defined and saved in a two-dimensional array, not zeros random numbers in range 0 to 100000
    qext_w_profiles = np.random.randint(0, 100000, size=(3, end)) # Structure is two-dimensional array with shape (n_profiles, n_time_steps)
    print(f"qext_w_profiles: {qext_w_profiles}") # Structure is two-dimensional array with shape (n_profiles, n_time_steps)

    return_temperature = np.linspace(50, 60, end).reshape(1, -1).repeat(3, axis=0)  # Generate time-dependent return temperatures as a linear gradient
    if qext_w_profiles.shape != return_temperature.shape:
        raise ValueError("The shape of return_temperature_profiles must match the shape of qext_w_profiles.")
    supply_temperature = np.full_like(time_steps, 85)  # Supply temperature is constant
    print(f"supply_temperature: {supply_temperature}") # Structure is one-dimensional array with shape (n_time_steps,)
    
    print(net.controller)

    update_heat_consumer_qext_controller(net, qext_w_profiles, time_steps, start, end)
    update_heat_consumer_return_temperature_controller(net, return_temperature, time_steps, start, end)
    update_heat_generator_supply_temperature_controller(net, supply_temperature, time_steps, start, end)

    print(net)
    print(net.controller)
    print(net.heat_consumer)
    print(net.circ_pump_pressure)
    #print(net.res_controller)
    print(net.res_heat_consumer)
    print(net.res_circ_pump_pressure)

    # Log variables and run time series calculation
    log_variables = create_log_variables(net)
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(net, time_steps, mode="bidirectional", iter=100, alpha=0.2)

    return yearly_time_steps, net, ow.np_results

def print_results(net):
    print(net)
    print(net.junction)
    print(net.pipe)
    print(net.heat_consumer)
    print(net.circ_pump_pressure)

    print(net.res_junction)
    print(net.res_pipe)
    print(net.res_heat_consumer)
    print(net.res_circ_pump_pressure)


if __name__ == "__main__":
    try:
        net = initialize_test_net()

        print_results(net)

        print("Test network initialized successfully."
              " Running time series simulation..." )
        

        yearly_time_steps, net, np_results = timeseries_test(net)

        print_results(net)

        print("Time series simulation completed successfully.")
        print("Results:")
        print(yearly_time_steps)
        print(np_results)

        fig, ax = plt.subplots()
        
        config_plot(net=net, ax=ax, show_junctions=True, show_pipes=True, 
                    show_heat_consumers=True, show_pump=True, show_plot=False, 
                    show_basemap=False, map_type="OSM")

        plt.show()

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e