"""
Filename: 07_example_timeseries_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-06
Description: Script for testing the pandapipes net simulation functions.
Usage: Run the script to generate a simple pandapipes network.
Functions:
    initialize_test_net(qext_w=np.array([100000, 100000, 100000, 100000]),
                        return_temperature=np.array([55, 60, 50, 60]),
                        supply_temperature=85,
                        flow_pressure_pump=4,
                        lift_pressure_pump=1.5,
                        pipetype="110/202 PLUS")
    timeseries_test(net)
    create_controllers(net, qext_w)
    update_const_controls(net, qext_w_profiles, time_steps, start, end)
    create_log_variables(net)
Classes:
    WorstPointPressureController(BasicCtrl)
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
from pandapower.timeseries import DFData
from pandapower.control.controller.const_control import ConstControl
from pandapower.control.basic_controller import BasicCtrl

# from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import update_const_controls, create_log_variables
# districtheatingsim.net_simulation_pandapipes.utilities import create_controllers

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot

class WorstPointPressureController(BasicCtrl):
    """
    A controller for maintaining the pressure difference at the worst point in the network.
    
    Args:
        net (pandapipesNet): The pandapipes network.
        circ_pump_pressure_idx (int, optional): Index of the circulation pump. Defaults to 0.
        target_dp_min_bar (float, optional): Target minimum pressure difference in bar. Defaults to 1.
        tolerance (float, optional): Tolerance for pressure difference. Defaults to 0.2.
        proportional_gain (float, optional): Proportional gain for the controller. Defaults to 0.2.
        **kwargs: Additional keyword arguments.
    """
    def __init__(self, net, circ_pump_pressure_idx=0, target_dp_min_bar=1, tolerance=0.2, proportional_gain=0.2, **kwargs):
        super(WorstPointPressureController, self).__init__(net, **kwargs)
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_dp_min_bar = target_dp_min_bar
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

        self.iteration = 0  # Add iteration counter

    def calculate_worst_point(self, net):
        """Calculate the worst point in the heating network, defined as the heat exchanger with the lowest pressure difference.

        Args:
            net (pandapipesNet): The pandapipes network.

        Returns:
            tuple: The minimum pressure difference and the index of the worst point.
        """
        
        dp = []

        for idx, qext, p_from, p_to in zip(net.heat_consumer.index, net.heat_consumer["qext_w"], net.res_heat_consumer["p_from_bar"], net.res_heat_consumer["p_to_bar"]):
            if qext != 0:
                dp_diff = p_from - p_to
                dp.append((dp_diff, idx))

        # Find the minimum delta p where the heat flow is not zero
        if dp:
            dp_min, idx_min = min(dp, key=lambda x: x[0])
        else:
            dp_min, idx_min = float('inf'), -1  # Default values when no qext is greater than 0

        return dp_min, idx_min

    def time_step(self, net, time_step):
        """Reset the iteration counter at the start of each time step.

        Args:
            net (pandapipesNet): The pandapipes network.
            time_step (int): The current time step.

        Returns:
            int: The current time step.
        """
        self.iteration = 0  # reset iteration counter
        self.dp_min, self.heat_consumer_idx = self.calculate_worst_point(net)

        return time_step

    def is_converged(self, net):
        """Check if the controller has converged.

        Args:
            net (pandapipesNet): The pandapipes network.

        Returns:
            bool: True if converged, False otherwise.
        """
        
        if self.heat_consumer_idx == -1:
            return True  # No valid heat consumer index, consider it converged

        current_dp_bar = net.res_heat_consumer["p_from_bar"].at[self.heat_consumer_idx] - net.res_heat_consumer["p_to_bar"].at[self.heat_consumer_idx]

        # Check if the pressure difference is within tolerance
        dp_within_tolerance = abs(current_dp_bar - self.target_dp_min_bar) < self.tolerance

        if dp_within_tolerance == True:
            return dp_within_tolerance

    def control_step(self, net):
        """Adjust the pump pressure to maintain the target pressure difference.

        Args:
            net (pandapipesNet): The pandapipes network.
        """
        # Increment iteration counter
        self.iteration += 1

        # Check whether the heat flow in the heat exchanger is zero
        current_dp_bar = net.res_heat_consumer["p_from_bar"].at[self.heat_consumer_idx] - net.res_heat_consumer["p_to_bar"].at[self.heat_consumer_idx]
        current_plift_bar = net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx]
        current_pflow_bar = net.circ_pump_pressure["p_flow_bar"].at[self.circ_pump_pressure_idx]

        dp_error = self.target_dp_min_bar - current_dp_bar
        
        plift_adjustment = dp_error * self.proportional_gain
        pflow_adjustment = dp_error * self.proportional_gain        

        new_plift = current_plift_bar + plift_adjustment
        new_pflow = current_pflow_bar + pflow_adjustment
        
        net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx] = new_plift
        net.circ_pump_pressure["p_flow_bar"].at[self.circ_pump_pressure_idx] = new_pflow

        return super(WorstPointPressureController, self).control_step(net)

def create_controllers(net, qext_w):
    """Create controllers for the network to manage heat consumers.

    Args:
        net (pandapipesNet): The pandapipes network.
        qext_w (array-like): External heat values for heat consumers.

    Returns:
        pandapipesNet: The pandapipes network with controllers added.
    """

    # Creates controllers for the network
    for i in range(len(net.heat_consumer)):
        # Create a simple DFData object for qext_w with the specific value for this pass
        placeholder_df = pd.DataFrame({f'qext_w_{i}': [qext_w[i]]})
        placeholder_data_source = DFData(placeholder_df)

        ConstControl(net, element='heat_consumer', variable='qext_w', element_index=i, data_source=placeholder_data_source, profile_name=f'qext_w_{i}')

    #dp_min, idx_dp_min = calculate_worst_point(net)  # This function must be defined
    dp_controller = WorstPointPressureController(net)#, idx_dp_min)  # This class must be defined
    net.controller.loc[len(net.controller)] = [dp_controller, True, -1, -1, False, False]

    return net

def update_const_controls(net, qext_w_profiles, time_steps, start, end):
    """Update constant controls with new data sources for time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.
        qext_w_profiles (list of arrays): List of external heat profiles.
        time_steps (range): Range of time steps for the simulation.
        start (int): Start index for slicing the profiles.
        end (int): End index for slicing the profiles.
    """
    for i, qext_w_profile in enumerate(qext_w_profiles):
        df = pd.DataFrame(index=time_steps, data={f'qext_w_{i}': qext_w_profile[start:end]})
        data_source = DFData(df)
        for ctrl in net.controller.object.values:
            if isinstance(ctrl, ConstControl) and ctrl.element_index == i and ctrl.variable == 'qext_w':
                ctrl.data_source = data_source

def create_log_variables(net):
    """Create a list of variables to log during the time series simulation.

    Args:
        net (pandapipesNet): The pandapipes network.

    Returns:
        list: List of tuples representing the variables to log.
    """
    log_variables = [
        ('res_junction', 'p_bar'), 
        ('res_junction', 't_k'),
        ('heat_consumer', 'qext_w'),
        ('res_heat_consumer', 'vdot_m3_per_s'),
        ('res_heat_consumer', 't_from_k'),
        ('res_heat_consumer', 't_to_k'),
        ('res_heat_consumer', 'mdot_from_kg_per_s'),
        ('res_circ_pump_pressure', 'mdot_from_kg_per_s'),
        ('res_circ_pump_pressure', 'p_to_bar'),
        ('res_circ_pump_pressure', 'p_from_bar')
    ]

    if 'circ_pump_mass' in net:
        log_variables.append(('res_circ_pump_mass', 'mdot_from_kg_per_s'))
        log_variables.append(('res_circ_pump_mass', 'p_to_bar'))
        log_variables.append(('res_circ_pump_mass', 'p_from_bar'))

    return log_variables

def initialize_test_net(qext_w=np.array([100000, 100000, 100000]),
                        return_temperature=np.array([55, 60, 50]),
                        supply_temperature=85,
                        flow_pressure_pump=4, 
                        lift_pressure_pump=1.5,
                        pipetype="110/202 PLUS"):
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
    net = create_controllers(net, qext_w)

    return net


def timeseries_test(net):
    start = 0
    end = 8 # 8760 hours in a year

    # time steps with start and end
    time_steps = np.arange(start, end, 1)	# time steps in hours

    # yearly time steps with dates beginning at 01.01.2021 00:00:00
    yearly_time_steps = pd.date_range(start="2021-01-01 00:00:00", periods=end, freq="H")

    # np.random.seed() is used to make the random numbers predictable
    np.random.seed(0)
    # for every time step for every heat consumer qext_w needs to be defined and saved in a two-dimensional array, not zeros random numbers in range 0 to 100000
    qext_w_profiles = np.random.randint(0, 100000, size=(4, end)) # Structure is two-dimensional array with shape (n_profiles, n_time_steps)
    print(f"qext_w_profiles: {qext_w_profiles}") # Structure is two-dimensional array with shape (n_profiles, n_time_steps)

    # set some time steps to zero
    qext_w_profiles[0, 7] = 0
    #qext_w_profiles[1, 7] = 0
    #qext_w_profiles[2, 7] = 0

    #qext_w_profiles[2, 306] = 1000

    print(f"qext_w_profiles: {qext_w_profiles}") # Structure is two-dimensional array with shape (n_profiles, n_time_steps)

    print(f"qext_w_profiles[0][7]: {qext_w_profiles[0][7]}") # Structure is two-dimensional array with shape (n_profiles, n_time_steps)
    print(f"qext_w_profiles[1][7]: {qext_w_profiles[1][7]}") # Structure is two-dimensional array with shape (n_profiles, n_time_steps)
    print(f"qext_w_profiles[2][7]: {qext_w_profiles[2][7]}") # Structure is two-dimensional array with shape (n_profiles, n_time_steps)

    update_const_controls(net, qext_w_profiles, time_steps, start, end)

    # Log variables and run time series calculation
    log_variables = create_log_variables(net)
    ow = OutputWriter(net, time_steps, output_path=None, log_variables=log_variables)

    run_time_series.run_timeseries(net, time_steps, mode="bidirectional", iter=100, alpha=0.2)

    return yearly_time_steps, net, ow.np_results


if __name__ == "__main__":
    try:
        print("Running the heat consumer result extraction test.")
        net = initialize_test_net()

        print(net)
        print(net.junction)
        print(net.pipe)
        print(net.heat_consumer)
        print(net.circ_pump_pressure)

        print(net.res_junction)
        print(net.res_pipe)
        print(net.res_heat_consumer)
        print(net.res_circ_pump_pressure)

        yearly_time_steps, net, np_results = timeseries_test(net)

        print(net)
        print(net.junction)
        print(net.pipe)
        print(net.heat_consumer)
        print(net.circ_pump_pressure)

        print(net.res_junction)
        print(net.res_pipe)
        print(net.res_heat_consumer)
        print(net.res_circ_pump_pressure)

        fig, ax = plt.subplots()
        
        config_plot(net=net, ax=ax, show_junctions=True, show_pipes=True, 
                    show_heat_consumers=True, show_pump=True, show_plot=False, 
                    show_basemap=False, map_type="OSM")

        plt.show()

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e