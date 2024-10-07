"""
Filename: controllers.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains two custom pandapipes Controllers for the net simulation.
"""

from pandapower.control.basic_controller import BasicCtrl
from math import pi
import numpy as np

class WorstPointPressureController(BasicCtrl):
    """
    A controller for maintaining the pressure difference at the worst point in the network.
    
    Args:
        net (pandapipesNet): The pandapipes network.
        worst_point_idx (int): Index of the worst point in the network.
        circ_pump_pressure_idx (int, optional): Index of the circulation pump. Defaults to 0.
        target_dp_min_bar (float, optional): Target minimum pressure difference in bar. Defaults to 1.
        tolerance (float, optional): Tolerance for pressure difference. Defaults to 0.2.
        proportional_gain (float, optional): Proportional gain for the controller. Defaults to 0.2.
        **kwargs: Additional keyword arguments.
    """
    def __init__(self, net, worst_point_idx, circ_pump_pressure_idx=0, target_dp_min_bar=1, tolerance=0.2, proportional_gain=0.2, **kwargs):
        super(WorstPointPressureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = worst_point_idx
        self.flow_control_idx = worst_point_idx
        self.heat_consumer_idx = worst_point_idx
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_dp_min_bar = target_dp_min_bar
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

        self.iteration = 0  # Add iteration counter

    def time_step(self, net, time_step):
        """Reset the iteration counter at the start of each time step.

        Args:
            net (pandapipesNet): The pandapipes network.
            time_step (int): The current time step.

        Returns:
            int: The current time step.
        """
        self.iteration = 0  # reset iteration counter
        return time_step

    def is_converged(self, net):
        """Check if the controller has converged.

        Args:
            net (pandapipesNet): The pandapipes network.

        Returns:
            bool: True if converged, False otherwise.
        """
        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        if qext_w <= 400:
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

        # Check whether the heat flow in the heat exchanger is zero
        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        current_dp_bar = net.res_heat_consumer["p_from_bar"].at[self.heat_consumer_idx] - net.res_heat_consumer["p_to_bar"].at[self.heat_consumer_idx]
        current_plift_bar = net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx]
        current_pflow_bar = net.circ_pump_pressure["p_flow_bar"].at[self.circ_pump_pressure_idx]

        if qext_w <= 400:
            return super(WorstPointPressureController, self).control_step(net)

        dp_error = self.target_dp_min_bar - current_dp_bar
        
        plift_adjustment = dp_error * self.proportional_gain
        pflow_adjustment = dp_error * self.proportional_gain        

        new_plift = current_plift_bar + plift_adjustment
        new_pflow = current_pflow_bar + pflow_adjustment
        
        net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx] = new_plift
        net.circ_pump_pressure["p_flow_bar"].at[self.circ_pump_pressure_idx] = new_pflow

        return super(WorstPointPressureController, self).control_step(net)

class ReturnTemperatureController(BasicCtrl):
    """
    A controller for maintaining the return temperature in the network.
    
    Args:
        net (pandapipesNet): The pandapipes network.
        heat_consumer_idx (int): Index of the heat consumer.
        target_return_temperature (float): Target return temperature.
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
    def __init__(self, net, heat_consumer_idx, target_return_temperature, min_supply_temperature=65, kp=0.95, ki=0.0, kd=0.0, tolerance=2, min_velocity=0.01, max_velocity=2, max_iterations=100, temperature_adjustment_step=1, debug=False, **kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_consumer_idx = heat_consumer_idx
        self.target_return_temperature = target_return_temperature
        self.min_supply_temperature = min_supply_temperature
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0
        self.last_error = None
        self.cp = 4190  # Specific heat capacity in J/(kg K)
        self.tolerance = tolerance
        self.min_velocity = min_velocity
        self.max_velocity = max_velocity
        self.max_iterations = max_iterations

        self.iteration = 0  # Add iteration counter
        self.previous_temperatures = []  # Use a list to store previous temperatures
        self.original_target_return_temperature = self.target_return_temperature

        self.data_source = None
        self.debug = debug

        self.calculate_mass_flow_limits(net)
        self.at_min_mass_flow_limit = False
        self.at_max_mass_flow_limit = False
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
        self.target_return_temperature = self.original_target_return_temperature

        if self.at_min_mass_flow_limit:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.min_mass_flow * 1.05
        if self.at_max_mass_flow_limit:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.max_mass_flow * 0.95

        # Check if a data source exists and get the target temperature for the current time step
        if self.data_source is not None:
            self.target_return_temperature = self.data_source.df.at[time_step, 'return_temperature']
            self.min_supply_temperature = self.data_source.df.at[time_step, 'min_supply_temperature']
        
        return time_step
    
    def calculate_mass_flow_limits(self, net):
        """Calculate the minimum and maximum mass flow limits.

        Args:
            net (pandapipesNet): The pandapipes network.
        """
        diameter = net.heat_consumer["diameter_m"].at[self.heat_consumer_idx]
        area = (pi / 4) * (diameter ** 2)

        self.min_mass_flow = self.min_velocity * area * 1000
        self.max_mass_flow = self.max_velocity * area * 1000

    def calculate_error(self, net):
        """Calculate the temperature error.

        Args:
            net (pandapipesNet): The pandapipes network.

        Returns:
            float: The temperature error.
        """
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        error = self.target_return_temperature - current_T_out
        return error

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

        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        # Not converging under that value
        if qext_w <= 500:  # Increase this threshold to avoid issues with very low heat demand
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.min_mass_flow
            return super(ReturnTemperatureController, self).control_step(net)

        # Calculate new mass flow
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15

        weighted_avg_T_in = self.get_weighted_average_temperature()
        if weighted_avg_T_in is not None:
            current_T_in = weighted_avg_T_in

        current_mass_flow = net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx]

        # Ensure the supply temperature does not fall below the minimum supply temperature
        if current_T_in < self.min_supply_temperature:
            error = self.min_supply_temperature - current_T_in
            pid_output = (self.kp * error) + (self.ki * self.integral) + (self.kd * self.calculate_derivative(error))
            new_mass_flow = current_mass_flow + pid_output * self.cp * (self.min_supply_temperature - current_T_out)
            new_mass_flow = np.clip(new_mass_flow, self.min_mass_flow, self.max_mass_flow)
            
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = new_mass_flow
            
            if self.debug:
                print(f"Minimum supply temperature not met. Adjusted mass flow to {new_mass_flow} kg/s.")
            return super(ReturnTemperatureController, self).control_step(net)

        if self.debug:
            print(f"heat_consumer_idx: {self.heat_consumer_idx}, Iteration: {self.iteration}, qext_w: {qext_w}, current_T_in: {current_T_in}, target_T_out: {self.target_return_temperature}, current_T_out: {current_T_out}, current_mass_flow: {current_mass_flow}")
        
        # Ensure not to divide by zero
        if current_T_in == self.target_return_temperature:
            self.target_return_temperature += 0.1  # Adjust target slightly to avoid division by zero

        error = self.calculate_error(net)
        self.update_integral(error)
        derivative = self.calculate_derivative(error)
        
        # PID calculation
        pid_output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        # Calculate new mass flow based on Q = m * cp * dT
        # Ensure not to divide by zero or cause invalid operations
        delta_T = current_T_in - current_T_out
        if delta_T == 0:
            delta_T = 0.1  # Adjust slightly to avoid division by zero

        adjusted_delta_T = current_T_in - (current_T_out + pid_output)  # pid = target-out 
        if adjusted_delta_T == 0:
            adjusted_delta_T = 0.1  # Adjust slightly to avoid division by zero
        
        # At the first iteration the mass flow from the previous is taken, which leads to problems when correcting the mass flow
        if self.iteration == 1:
            mass_flow_correction = 0
            new_mass_flow = qext_w / (self.cp * adjusted_delta_T)
        else:
            mass_flow_correction = qext_w / (self.cp * adjusted_delta_T) - (qext_w / (self.cp * delta_T))
            current_mass_flow = net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx]
            new_mass_flow = current_mass_flow + mass_flow_correction

        if self.debug:
            if new_mass_flow <= self.min_mass_flow:
                print(f"heat_consumer_idx: {self.heat_consumer_idx}, Min mass flow of {self.min_mass_flow} reached with new mass flow of {new_mass_flow}")
            if new_mass_flow >= self.max_mass_flow:
                print(f"heat_consumer_idx: {self.heat_consumer_idx}, Max mass flow of {self.max_mass_flow} reached with new mass flow of {new_mass_flow}")

                # Adjust target return temperature if max mass flow limit is reached
                self.target_return_temperature -= self.temperature_adjustment_step
                print(f"Adjusted target return temperature to {self.target_return_temperature} °C due to max mass flow limit.")

        # Apply physical limits
        new_mass_flow = np.clip(new_mass_flow, self.min_mass_flow, self.max_mass_flow)  # Clipped to avoid too low or too high mass flow

        net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = new_mass_flow

        if self.debug:
            print(f"heat_consumer_idx: {self.heat_consumer_idx}, delta_T: {delta_T}, adjusted_delta_T: {adjusted_delta_T}, Error: {error}, Integral: {self.integral}, Derivative: {derivative}, PID output: {pid_output}, mass_flow_correction: {mass_flow_correction}, New mass flow: {new_mass_flow}")

        return super(ReturnTemperatureController, self).control_step(net)

    def is_converged(self, net):
        """Check if the controller has converged.

        Args:
            net (pandapipesNet): The pandapipes network.

        Returns:
            bool: True if converged, False otherwise.
        """
        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        # Not converging under that value
        if qext_w <= 500:  # Increase this threshold to avoid issues with very low heat demand
            return True
        
        # Check whether the temperatures have changed within the specified tolerance
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15
        previous_T_in = self.previous_temperatures[-1] if self.previous_temperatures else None

        # Testing for convergence
        temperature_change = abs(current_T_in - previous_T_in) if previous_T_in is not None else float('inf')
        converged_T_in = temperature_change < self.tolerance

        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        temperature_diff = abs(current_T_out - self.target_return_temperature)
        converged_T_out = temperature_diff < self.tolerance

        # Update the list of previous temperatures
        self.previous_temperatures.append(current_T_in)
        if len(self.previous_temperatures) > 2:  # Keep the last two temperatures
            self.previous_temperatures.pop(0)

        current_mass_flow = net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx]

        # Check whether the mass flow limits have been reached
        self.at_min_mass_flow_limit = current_mass_flow <= self.min_mass_flow
        self.at_max_mass_flow_limit = current_mass_flow >= self.max_mass_flow

        if self.at_min_mass_flow_limit and self.iteration > 10:
            if self.debug:
                print(f"Min mass flow limit reached for heat_consumer_idx: {self.heat_consumer_idx}, current_temperature: {current_T_in}, target_T_out: {self.target_return_temperature}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}")
            return True
        
        if self.at_max_mass_flow_limit and self.iteration > 10:
            if self.debug:
                print(f"Max mass flow limit reached for heat_consumer_idx: {self.heat_consumer_idx}, current_temperature: {current_T_in}, target_T_out: {self.target_return_temperature}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}")

                # Adjust target return temperature if max mass flow limit is reached
                self.target_return_temperature -= self.temperature_adjustment_step
                print(f"Adjusted target return temperature to {self.target_return_temperature} °C due to max mass flow limit.")
                
            return True
        
        # Convergence based on the minimum supply temperature
        if current_T_in < self.min_supply_temperature:
            if self.debug:
                print(f"Supply temperature not met for heat_consumer_idx: {self.heat_consumer_idx}.")
            return False
        
        if converged_T_in and converged_T_out:
            if self.debug:
                print(f'Regler konvergiert: heat_consumer_idx: {self.heat_consumer_idx}, current_temperature: {current_T_in}, target_T_out: {self.target_return_temperature}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}')
            return True

        # Check if the maximum number of iterations has been reached
        if self.iteration >= self.max_iterations:
            if self.debug:
                print(f"Max iterations reached for heat_consumer_idx: {self.heat_consumer_idx}")
            return True

        return False