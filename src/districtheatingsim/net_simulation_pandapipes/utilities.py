"""
Filename: utilities.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-06
Description: Script with different functionalities used in the pandapipes functions.
"""

import time
import logging
import sys
import os

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from scipy.interpolate import RegularGridInterpolator

import pandapipes as pp
from pandapipes.control.run_control import run_control

from pandapower.timeseries import DFData
from pandapower.control.controller.const_control import ConstControl
from pandapower.control.basic_controller import BasicCtrl

# Initialize logging
logging.basicConfig(level=logging.INFO)

def get_resource_path(relative_path):
    """Get the absolute path to the resource, works for dev and for PyInstaller.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # When the application is frozen, the base path is the temp folder where PyInstaller extracts everything
        base_path = sys._MEIPASS
    else:
        # When the application is not frozen, the base path is the directory of the main file
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def COP_WP(VLT_L, QT, values=np.genfromtxt(get_resource_path('data/COP/Kennlinien WP.csv'), delimiter=';')):
    """Calculate the Coefficient of Performance (COP) for a heat pump based on supply and source temperatures.

    Args:
        VLT_L (array-like): Array of supply temperatures.
        QT (float or array-like): Source temperature or array of source temperatures.
        values (np.ndarray): COP values loaded from a CSV file. Defaults to loading from 'heat_generators\Kennlinien WP.csv'.

    Returns:
        tuple: COP values and possibly adjusted supply temperatures.
    """
    row_header = values[0, 1:]  # Supply temperatures
    col_header = values[1:, 0]  # Source temperatures
    values = values[1:, 1:]
    f = RegularGridInterpolator((col_header, row_header), values, method='linear')

    # Technical limit of the heat pump is a temperature range of 75 °C
    VLT_L = np.minimum(VLT_L, 75 + QT)
    VLT_L = np.maximum(VLT_L, 35)

    # Check whether QT is a number or an array
    if np.isscalar(QT):
        # If QT is a number, we create an array with that number
        QT_array = np.full_like(VLT_L, QT)
    else:
        # If QT is already an array, we check if it has the same length as VLT_L
        if len(QT) != len(VLT_L):
            raise ValueError("QT must either be a single number or an array with the same length as VLT_L.")
        QT_array = QT

    # Calculation of COP_L
    COP_L = f(np.column_stack((QT_array, VLT_L)))

    return COP_L, VLT_L

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
    def __init__(self, net, circ_pump_pressure_idx=0, target_dp_min_bar=1, tolerance=0.2, proportional_gain=0.2, min_plift=1.5, min_pflow=3.5, **kwargs):
        super(WorstPointPressureController, self).__init__(net, **kwargs)
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_dp_min_bar = target_dp_min_bar
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

        self.min_plift = min_plift  # Minimum pressure in bar
        self.min_pflow = min_pflow  # Minimum lift pressure in bar

        self.iteration = 0  # Add iteration counter

        self.dp_min, self.heat_consumer_idx = self.calculate_worst_point(net)

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

        if not dp:
            return 0, -1

        # Find the minimum delta p where the heat flow is not zero
        dp_min, idx_min = min(dp, key=lambda x: x[0])

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

        if all(net.heat_consumer["qext_w"] == 0):
            return True
        
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

        """Adjust the pump pressure or switch to standby mode when heat flow is zero."""
        if all(net.heat_consumer["qext_w"] == 0):
            # Switch to standby mode
            print("No heat flow detected. Switching to standby mode.")
            net.circ_pump_pressure["plift_bar"].iloc[:] = self.min_plift  # Minimum lift pressure
            net.circ_pump_pressure["p_flow_bar"].iloc[:] = self.min_pflow  # Minimum flow pressure
            return super(WorstPointPressureController, self).control_step(net)

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
    
class TemperatureController(BasicCtrl):
    """
    A controller for maintaining the min supply temperature of the heat consumers in the network.
    
    Args:
        net (pandapipesNet): The pandapipes network.
        heat_consumer_idx (int): Index of the heat consumer.
        min_supply_temperature (float, optional): Minimum supply temperature. Defaults to 65.
        kp (float, optional): Proportional gain. Defaults to 0.95.
        ki (float, optional): Integral gain. Defaults to 0.0.
        kd (float, optional): Derivative gain. Defaults to 0.0.
        tolerance (float, optional): Tolerance for temperature difference. Defaults to 2.
        min_velocity (float, optional): Minimum velocity in m/s. Defaults to 0.01.
        max_velocity (float, optional): Maximum velocity in m/s. Defaults to 2.
        max_iterations (int, optional): Maximum number of iterations. Defaults to 100.
        temperature_adjustment_step (float, optional): Step to adjust the target return temperature. Defaults to 1.
        debug (bool, optional): Flag to enable debug output. Defaults to False.
        **kwargs: Additional keyword arguments.
    """
    def __init__(self, net, heat_consumer_idx, min_supply_temperature=65, kp=0.95, ki=0.0, kd=0.0, tolerance=2, max_iterations=100, temperature_adjustment_step=1, debug=False, **kwargs):
        super(TemperatureController, self).__init__(net, **kwargs)
        self.heat_consumer_idx = heat_consumer_idx
        self.min_supply_temperature = min_supply_temperature
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0
        self.last_error = None
        self.cp = 4190  # Specific heat capacity in J/(kg K)
        self.tolerance = tolerance
        self.max_iterations = max_iterations

        self.iteration = 0  # Add iteration counter
        self.previous_temperatures = []  # Use a list to store previous temperatures

        self.data_source = None
        self.debug = debug

        self.temperature_adjustment_step = temperature_adjustment_step  # Step to adjust the target return temperature

    def time_step(self, net, time_step):
        """Reset the controller parameters at the start of each time step.

        Args:
            net (pandapipesNet): The pandapipes network.
            time_step (int): The current time step.

        Returns:
            int: The current time step.
        """
        self.iteration = 0  # reset iteration counter
        self.previous_temperatures = []  # Reset to an empty list
        self.integral = 0
        self.last_error = None

        if time_step == 0:
            # Store the standard return temperature for the heat consumer
            self.standard_return_temperature = net.heat_consumer["treturn_k"].at[self.heat_consumer_idx]

        else:
            # Restore the standard return temperature for the heat consumer
            net.heat_consumer["treturn_k"].at[self.heat_consumer_idx] = self.standard_return_temperature

        # Check if a data source exists and get the target temperature for the current time step
        if self.data_source is not None:
            self.min_supply_temperature = self.data_source.df.at[time_step, 'min_supply_temperature']
        
        return time_step

    def update_integral(self, error):
        """Update the integral component of the PID controller.

        Args:
            error (float): The current error.
        """
        self.integral += error

    def calculate_derivative(self, error):
        """Calculate the derivative component of the PID controller.

        Args:
            error (float): The current error.

        Returns:
            float: The derivative of the error.
        """
        if self.last_error is None:
            derivative = 0
        else:
            derivative = error - self.last_error
        self.last_error = error
        return derivative

    def get_weighted_average_temperature(self):
        """Calculate the weighted average of the previous temperatures.

        Returns:
            float: The weighted average temperature.
        """
        if len(self.previous_temperatures) == 0:
            return None
        weights = np.arange(1, len(self.previous_temperatures) + 1)
        weighted_avg = np.dot(self.previous_temperatures, weights) / weights.sum()
        return weighted_avg

    def control_step(self, net):
        """Adjust the mass flow to maintain the target return temperature.

        Args:
            net (pandapipesNet): The pandapipes network.
        """
        # Increment iteration counter
        self.iteration += 1
        
        if all(net.heat_consumer["qext_w"] == 0):
            # Switch to standby mode
            print("No heat flow detected. Switching to standby mode.")
            return super(TemperatureController, self).control_step(net)

        # Calculate new mass flow
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15

        weighted_avg_T_in = self.get_weighted_average_temperature()
        if weighted_avg_T_in is not None:
            current_T_in = weighted_avg_T_in

        current_mass_flow = net.res_heat_consumer["mdot_from_kg_per_s"].at[self.heat_consumer_idx]

        # Ensure the supply temperature does not fall below the minimum supply temperature
        if current_T_in < self.min_supply_temperature:
            new_T_out = net.heat_consumer["treturn_k"].at[self.heat_consumer_idx] + self.temperature_adjustment_step
            net.heat_consumer["treturn_k"].at[self.heat_consumer_idx] = new_T_out
            
            if self.debug:
                print(f"Minimum supply temperature not met. Adjusted target output temperature to {new_T_out} °C.")
            return super(TemperatureController, self).control_step(net)

    def is_converged(self, net):
        """Check if the controller has converged.

        Args:
            net (pandapipesNet): The pandapipes network.

        Returns:
            bool: True if converged, False otherwise.
        """
        # not converging under that value
        if all(net.heat_consumer["qext_w"] == 0):
            return True
        
        # Check whether the temperatures have changed within the specified tolerance
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15
        previous_T_in = self.previous_temperatures[-1] if self.previous_temperatures else None

        # Testing for convergence
        temperature_change = abs(current_T_in - previous_T_in) if previous_T_in is not None else float('inf')
        converged_T_in = temperature_change < self.tolerance

        # Update the list of previous temperatures
        self.previous_temperatures.append(current_T_in)
        if len(self.previous_temperatures) > 2:  # Keep the last two temperatures
            self.previous_temperatures.pop(0)

        current_mass_flow = net.res_heat_consumer["mdot_from_kg_per_s"].at[self.heat_consumer_idx]
        
        # Convergence based on the minimum supply temperature
        if current_T_in < self.min_supply_temperature:
            if self.debug:
                print(f"Supply temperature not met for heat_consumer_idx: {self.heat_consumer_idx}. current_temperature_in: {current_T_in}), current_temperature_out: {current_T_out}), current_mass_flow: {current_mass_flow}")
            return False
        
        if converged_T_in:
            if self.debug:
                print(f'Regler konvergiert: heat_consumer_idx: {self.heat_consumer_idx}, current_temperature_in: {current_T_in}), current_temperature_out: {current_T_out}), current_mass_flow: {current_mass_flow}')
            return True

        # Check if the maximum number of iterations has been reached
        if self.iteration >= self.max_iterations:
            if self.debug:
                print(f"Max iterations reached for heat_consumer_idx: {self.heat_consumer_idx}")
            return True

        return False

def create_controllers(net, qext_w, min_supply_temperature_heat_consumer):
    """Create controllers for the network to manage heat consumers.

    Args:
        net (pandapipesNet): The pandapipes network.
        qext_w (array-like): External heat values for heat consumers.
        min_supply_temperature_heat_consumer (array-like): Minimum supply temperatures for heat consumers.

    Returns:
        pandapipesNet: The pandapipes network with controllers added.
    """

    # Creates controllers for the network
    for i in range(len(net.heat_consumer)):
        # Create a simple DFData object for qext_w with the specific value for this pass
        placeholder_df = pd.DataFrame({f'qext_w_{i}': [qext_w[i]]})
        placeholder_data_source = DFData(placeholder_df)

        ConstControl(net, element='heat_consumer', variable='qext_w', element_index=i, data_source=placeholder_data_source, profile_name=f'qext_w_{i}')

        # Adjustment for using return_temperature as an array
        T_controller = TemperatureController(net, heat_consumer_idx=i, min_supply_temperature=min_supply_temperature_heat_consumer[i])
        net.controller.loc[len(net.controller)] = [T_controller, True, -1, -1, False, False]

    if hasattr(net, 'circ_pump_mass'):
        for i in range(len(net.circ_pump_mass)):
            # qext_w / number of circ_pump_mass + circ_pump_pressure --> equal heat distribution
            # Calculate the mass flow from qext_w
            qext_i = np.sum(qext_w) / (len(net.circ_pump_mass) + len(net.circ_pump_pressure))
            cp = 4190  # Specific heat capacity in J/(kg K)
            delta_T = 35  # Assumed temperature difference in K
            mass_flow = qext_i / (cp * delta_T)  # Mass flow in kg/s

            print(f"Mass flow for circ_pump_mass_{i}: {mass_flow} kg/s")

            placeholder_df = pd.DataFrame({f'mdot_kg_per_s_{i}': [mass_flow]})
            placeholder_data_source = DFData(placeholder_df)

            ConstControl(net, element='circ_pump_mass', variable='mdot_kg_per_s', element_index=i, data_source=placeholder_data_source, profile_name=f'mdot_kg_per_s_{i}')
            
    dp_controller = WorstPointPressureController(net)
    net.controller.loc[len(net.controller)] = [dp_controller, True, -1, -1, False, False]

    return net

def correct_flow_directions(net):
    """Correct the flow directions in the network by swapping junctions if necessary.

    Args:
        net (pandapipesNet): The pandapipes network.

    Returns:
        pandapipesNet: The pandapipes network with corrected flow directions.
    """
    # Initial pipeflow calculation
    pp.pipeflow(net, mode="bidirectional")

    # Check the velocities in each pipe and swap the junctions if necessary
    for pipe_idx in net.pipe.index:
        # Check the average velocity in the pipe
        if net.res_pipe.v_mean_m_per_s[pipe_idx] < 0:
            # Swap the junctions
            from_junction = net.pipe.at[pipe_idx, 'from_junction']
            to_junction = net.pipe.at[pipe_idx, 'to_junction']
            net.pipe.at[pipe_idx, 'from_junction'] = to_junction
            net.pipe.at[pipe_idx, 'to_junction'] = from_junction

    # Perform the pipeflow calculation again to obtain updated results
    pp.pipeflow(net, mode="bidirectional")

    return net

def optimize_diameter_parameters(net, element="pipe", v_max=2, dx=0.001, safety_factor=1.5):
    """Optimize the diameters of the network elements to meet the specified maximum velocity.

    Args:
        net (pandapipesNet): The pandapipes network.
        element (str): The element type to optimize (default is "pipe").
        v_max (float): Maximum allowed velocity in the elements (default is 2 m/s).
        dx (float): Step size for diameter adjustments (default is 0.001 m).

    Returns:
        pandapipesNet: The optimized pandapipes network.
    """
    v_max /= safety_factor # Adjust the maximum velocity based on the safety factor

    pp.pipeflow(net, mode="bidirectional")
    element_df = getattr(net, element)  # Access the element's DataFrame
    res_df = getattr(net, f"res_{element}")  # Access the result DataFrame
            
    change_made = True
    while change_made:
        change_made = False
        
        for idx in element_df.index:
            #current_velocity = res_df.v_mean_m_per_s[idx]
            # new implementation over vdot and diameter
            current_velocity = res_df.vdot_m3_per_s[idx] / (np.pi * (element_df.at[idx, 'diameter_m'] / 2)**2)
            current_diameter = element_df.at[idx, 'diameter_m']
            
            # Enlarge if speed > v_max
            if current_velocity > v_max:
                element_df.at[idx, 'diameter_m'] += dx
                change_made = True

           # Shrink as long as speed < v_max and check
            elif current_velocity < v_max:
                element_df.at[idx, 'diameter_m'] -= dx
                pp.pipeflow(net, mode="bidirectional")
                element_df = getattr(net, element)  # Access the element's DataFrame
                res_df = getattr(net, f"res_{element}")  # Access the result DataFrame
                #new_velocity = res_df.v_mean_m_per_s[idx]
                # new implementation over vdot and diameter
                new_velocity = res_df.vdot_m3_per_s[idx] / (np.pi * (element_df.at[idx, 'diameter_m'] / 2)**2)

                if new_velocity > v_max:
                    # Reset if new speed exceeds v_max
                    element_df.at[idx, 'diameter_m'] = current_diameter
                else:
                    change_made = True
        
        if change_made:
            pp.pipeflow(net, mode="bidirectional")  # Recalculation only if changes were made
            element_df = getattr(net, element)
            res_df = getattr(net, f"res_{element}")

    return net

def init_diameter_types(net, v_max_pipe=1.0, material_filter="KMR", k=0.1):
    """Initialize the diameters and types of pipes in the network based on the specified velocity and filters.

    Args:
        net (pandapipesNet): The pandapipes network.
        v_max_pipe (float): Maximum allowed velocity in pipes.
        material_filter (str): Material filter for pipe initialization.
        insulation_filter (str): Insulation filter for pipe initialization.

    Returns:
        pandapipesNet: The pandapipes network with initialized diameters and types.
    """
    start_time_total = time.time()
    pp.pipeflow(net, mode="bidirectional")
    logging.info(f"Initial pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    filtered_by_material = pipe_std_types[pipe_std_types['material'] == material_filter]

    type_position_dict = {type_name: i for i, type_name in enumerate(filtered_by_material.index)}

    # Initial diameter adjustment
    for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
        current_diameter = net.pipe.at[pipe_idx, 'diameter_m']
        required_diameter = current_diameter * (velocity / v_max_pipe)**0.5
        # Find the closest available standard type
        closest_type = min(filtered_by_material.index, key=lambda x: abs(filtered_by_material.loc[x, 'inner_diameter_mm'] / 1000 - required_diameter))
        net.pipe.std_type.at[pipe_idx] = closest_type
        properties = filtered_by_material.loc[closest_type]
        net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
        net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
        net.pipe.at[pipe_idx, 'k_mm'] = k

    pp.pipeflow(net, mode="bidirectional")
    logging.info(f"Post-initial diameter adjustment pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    return net

def optimize_diameter_types(net, v_max=1.0, material_filter="KMR", k=0.1):
    """Optimize the diameters and types of pipes in the network based on the specified velocity and filters.

    Args:
        net (pandapipesNet): The pandapipes network.
        v_max (float): Maximum allowed velocity in pipes.
        material_filter (str): Material filter for pipe optimization.
        insulation_filter (str): Insulation filter for pipe optimization.

    Returns:
        pandapipesNet: The optimized pandapipes network.
    """
    start_time_total = time.time()

    run_control(net, mode="bidirectional")
    pp.pipeflow(net, mode="bidirectional")

    logging.info(f"Initial pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    filtered_by_material = pipe_std_types[pipe_std_types['material'] == material_filter]

    type_position_dict = {type_name: i for i, type_name in enumerate(filtered_by_material.index)}

    # Initial diameter adjustment
    for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
        current_diameter = net.pipe.at[pipe_idx, 'diameter_m']
        required_diameter = current_diameter * (velocity / v_max)**0.5
        # Find the closest available standard type
        closest_type = min(filtered_by_material.index, key=lambda x: abs(filtered_by_material.loc[x, 'inner_diameter_mm'] / 1000 - required_diameter))
        net.pipe.std_type.at[pipe_idx] = closest_type
        properties = filtered_by_material.loc[closest_type]
        net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
        net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
        net.pipe.at[pipe_idx, 'k_mm'] = k

    pp.pipeflow(net, mode="bidirectional")
    logging.info(f"Post-initial diameter adjustment pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    # Add a column to track if a pipe is optimized
    net.pipe['optimized'] = False

    change_made = True
    iteration_count = 0

    while change_made:
        iteration_start_time = time.time()
        change_made = False

        # Track the number of pipes within and outside the desired velocity range
        pipes_within_target = 0
        pipes_outside_target = 0

        for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
            if net.pipe.at[pipe_idx, 'optimized'] and velocity <= v_max:
                pipes_within_target += 1
                continue

            current_type = net.pipe.std_type.at[pipe_idx]
            current_type_position = type_position_dict[current_type]

            if velocity > v_max and current_type_position < len(filtered_by_material) - 1:
                new_type = filtered_by_material.index[current_type_position + 1]
                net.pipe.std_type.at[pipe_idx] = new_type
                properties = filtered_by_material.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
                net.pipe.at[pipe_idx, 'k_mm'] = k
                change_made = True
                pipes_outside_target += 1

            elif velocity <= v_max and current_type_position > 0:
                new_type = filtered_by_material.index[current_type_position - 1]
                net.pipe.std_type.at[pipe_idx] = new_type
                properties = filtered_by_material.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
                net.pipe.at[pipe_idx, 'k_mm'] = k

                pp.pipeflow(net, mode="bidirectional")
                new_velocity = net.res_pipe.v_mean_m_per_s[pipe_idx]

                if new_velocity <= v_max:
                    change_made = True
                else:
                    net.pipe.std_type.at[pipe_idx] = current_type
                    properties = filtered_by_material.loc[current_type]
                    net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                    net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
                    net.pipe.at[pipe_idx, 'k_mm'] = k
                    
                    net.pipe.at[pipe_idx, 'optimized'] = True
                    pipes_within_target += 1
            else:
                net.pipe.at[pipe_idx, 'optimized'] = True
                pipes_within_target += 1

        iteration_count += 1
        if change_made:
            iteration_pipeflow_start = time.time()
            pp.pipeflow(net, mode="bidirectional")
        
        logging.info(f"Iteration {iteration_count}: {pipes_within_target} pipes within target velocity, {pipes_outside_target} pipes outside target velocity")
        logging.info(f"Iteration {iteration_count} took {time.time() - iteration_start_time:.2f} seconds")

    logging.info(f"Total optimization time: {time.time() - start_time_total:.2f} seconds")

    run_control(net, mode="bidirectional")

    return net

def export_net_geojson(net, filename):
    """Export the network data to a GeoJSON file.

    Args:
        net (pandapipesNet): The pandapipes network.
        filename (str): The file path where the GeoJSON data will be saved.

    Returns:
        None
    """
    features = []  # List to collect GeoDataFrames of all components
    
    # Process lines
    if 'pipe_geodata' in net and not net.pipe_geodata.empty:
        geometry_lines = [LineString(coords) for coords in net.pipe_geodata['coords']]
        gdf_lines = gpd.GeoDataFrame(net.pipe_geodata, geometry=geometry_lines)
        del gdf_lines['coords']  # Remove the 'coords' column
        # Add attributes
        gdf_lines['name'] = net.pipe['name']
        gdf_lines['diameter_mm'] = net.pipe['diameter_m'] * 1000
        gdf_lines['std_type'] = net.pipe['std_type']
        gdf_lines['length_m'] = net.pipe['length_km'] * 1000
        features.append(gdf_lines)

    if 'circ_pump_pressure' in net and not net.circ_pump_pressure.empty:
        # Calculate the geometry
        pump_lines = [LineString([
            (net.junction_geodata.loc[pump['return_junction']]['x'], net.junction_geodata.loc[pump['return_junction']]['y']),
            (net.junction_geodata.loc[pump['flow_junction']]['x'], net.junction_geodata.loc[pump['flow_junction']]['y'])
        ]) for index, pump in net.circ_pump_pressure.iterrows()]
        
        # Filter only relevant columns (adapted to actual data)
        relevant_columns = ['name', 'geometry']
        gdf_pumps = gpd.GeoDataFrame(net.circ_pump_pressure, geometry=pump_lines)[relevant_columns]
        
        features.append(gdf_pumps)

    if 'heat_exchanger' in net and not net.heat_exchanger.empty and 'flow_control' in net and not net.flow_control.empty:
        # Iterate through each pair of heat_exchanger and flow_control
        for idx, heat_exchanger in net.heat_exchanger.iterrows():
            # Since flow_controls and heat_exchangers are created together, we assume that they
            # have the same order or can be linked via logic that must be implemented here
            flow_control = net.flow_control.loc[net.flow_control['to_junction'] == heat_exchanger['from_junction']].iloc[0]

            # Get the coordinates for flow_control's start and heat_exchanger's end coordinates
            start_coords = net.junction_geodata.loc[flow_control['from_junction']]
            end_coords = net.junction_geodata.loc[heat_exchanger['to_junction']]

            # Create a line between these points
            line = LineString([(start_coords['x'], start_coords['y']), (end_coords['x'], end_coords['y'])])
            
            # Create a GeoDataFrame for this combined component
            gdf_component = gpd.GeoDataFrame({
                'name': "HAST",
                'diameter_mm': f"{heat_exchanger['diameter_m']*1000:.1f}",
                'qext_W': f"{heat_exchanger['qext_w']:.0f}",
                'geometry': [line]
            }, crs="EPSG:25833")  # Set crs to EPSG:25833
            
            features.append(gdf_component)

    if 'heat_consumer' in net and not net.heat_consumer.empty:
        # Iterate through each pair of heat_exchanger and flow_control
        for idx, heat_consumer in net.heat_consumer.iterrows():
            # Get the coordinates for flow_control's start and heat_exchanger's end coordinates
            start_coords = net.junction_geodata.loc[heat_consumer['from_junction']]
            end_coords = net.junction_geodata.loc[heat_consumer['to_junction']]

            # Create a line between these points
            line = LineString([(start_coords['x'], start_coords['y']), (end_coords['x'], end_coords['y'])])
            
            # Create a GeoDataFrame for this combined component
            gdf_component = gpd.GeoDataFrame({
                'name': "HAST",
                'diameter_mm': f"{heat_consumer['diameter_m']*1000:.1f}",
                'qext_W': f"{heat_consumer['qext_w']:.0f}",
                'geometry': [line]
            }, crs="EPSG:25833")  # Set crs to EPSG:25833
            
            features.append(gdf_component)

    # Set the coordinate system (CRS) for all GeoDataFrames and merge them
    for feature in features:
        feature.set_crs(epsg=25833, inplace=True)

    # Combine all GeoDataFrames into a FeatureCollection
    gdf_all = gpd.GeoDataFrame(pd.concat(features, ignore_index=True), crs="EPSG:25833")

    # Export as GeoJSON
    if not gdf_all.empty:
        gdf_all.to_file(filename, driver='GeoJSON')
    else:
        print("No geographical data available in the network.")