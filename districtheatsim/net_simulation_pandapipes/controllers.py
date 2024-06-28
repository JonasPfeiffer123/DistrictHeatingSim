from pandapower.control.basic_controller import BasicCtrl
from math import pi
import numpy as np

class WorstPointPressureController(BasicCtrl):
    def __init__(self, net, worst_point_idx, circ_pump_pressure_idx=0, target_dp_min_bar=1, tolerance=0.2, proportional_gain=0.2,**kwargs):
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
        self.iteration = 0  # reset iteration counter
        return time_step

    def is_converged(self, net):
        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        if qext_w <= 400:
            return True
        current_dp_bar = net.res_heat_consumer["p_from_bar"].at[self.heat_consumer_idx] - net.res_heat_consumer["p_to_bar"].at[self.heat_consumer_idx]

        # check, if the temperature converged
        dp_within_tolerance = abs(current_dp_bar - self.target_dp_min_bar) < self.tolerance

        if dp_within_tolerance == True:
            return dp_within_tolerance
    
    def control_step(self, net):
        # incrementation iteration counter
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

"""
class ReturnTemperatureController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, target_temperature, debug=False, tolerance=2, min_velocity=0.01, max_velocity=2, **kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.flow_control_idx = heat_exchanger_idx
        self.heat_consumer_idx = heat_exchanger_idx
        self.target_temperature = target_temperature
        self.initial_target_temperature = target_temperature
        self.debug = debug
        self.tolerance = tolerance
        self.min_velocity = min_velocity
        self.max_velocity = max_velocity

        self.iteration = 0  # Add iteration counter
        self.calculate_mass_flow_limits(net)
        self.previous_temperatures = {}

        self.at_min_mass_flow_limit = False
        self.at_max_mass_flow_limit = False

        self.data_source = None
        self.cp = 4190 # Specific heat capacity in J/(kg K)

    def time_step(self, net, time_step):
        self.iteration = 0  # reset iteration counter
        self.previous_temperatures = {}
        if self.at_min_mass_flow_limit:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.min_mass_flow * 1.05
        if self.at_max_mass_flow_limit:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.max_mass_flow * 0.95

        # Check if a data source exists and get the target temperature for the current time step
        if self.data_source is not None:
            self.target_temperature = self.data_source.df.at[time_step, 'return_temperature']
        
        return time_step

    def update_state(self, net):
        # Update the state variable with the current inlet temperatures
        self.previous_temperatures[self.heat_consumer_idx] = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx]

    def calculate_mass_flow_limits(self, net):
        diameter = net.heat_consumer["diameter_m"].at[self.heat_consumer_idx]
        area = (pi / 4) * (diameter ** 2)

        self.min_mass_flow = self.min_velocity * area * 1000
        self.max_mass_flow = self.max_velocity * area * 1000

    def is_converged(self, net):
        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        if qext_w <= 400:
            return True

        # Check whether the temperatures have changed within the specified tolerance
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx]
        previous_T_in = self.previous_temperatures.get(self.heat_consumer_idx)

        # Testing for convergence
        temperature_change = abs(current_T_in - previous_T_in) if previous_T_in is not None else float('inf')
        converged_T_in = temperature_change < self.tolerance

        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        temperature_diff = abs(current_T_out - self.target_temperature)
        converged_T_out = temperature_diff < self.tolerance

        # Update temperature for next run
        self.previous_temperatures[self.heat_consumer_idx] = current_T_in

        current_mass_flow = net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx]

        # Check whether the mass flow limits have been reached
        self.at_min_mass_flow_limit = current_mass_flow <= self.min_mass_flow
        self.at_max_mass_flow_limit = current_mass_flow >= self.max_mass_flow

        if self.at_min_mass_flow_limit and self.iteration > 10:
            return True
        
        if self.at_max_mass_flow_limit and self.iteration > 10:
            return True
        
        if converged_T_in and converged_T_out:
            if self.debug == True:# and self.heat_consumer_idx == 3:
                print(f'Regler konvergiert: heat_consumer_idx: {self.heat_consumer_idx}, qext_w: {qext_w}, current_temperature: {current_T_in}, previous_temperature: {previous_T_in}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}')
            return True
        
    def control_step(self, net):
        # incrementation iteration counter
        self.iteration += 1
        self.calculate_mass_flow_limits(net)

        # Heat output of the heat exchanger
        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]

        # Check if the heat output is low enough to not make an adjustment
        if qext_w <= 400:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = 0
            return super(ReturnTemperatureController, self).control_step(net)

        # Current outlet temperature of the fluid
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15 # Inlet temperature in °C

        current_mass_flow = net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx]
        
        if self.debug == True:# and self.heat_consumer_idx == 3:
            print(f"min mass flow: {self.min_mass_flow}, Max mass flow: {self.max_mass_flow}")
            print(f'ReturnTemperatureController vor control_step: Iteration: {self.iteration}, Heat Consumer ID: {self.heat_consumer_idx}, current_massflow={current_mass_flow}, qext_w={qext_w}, target_temperature_out={self.target_temperature}, current_temperature_out={current_T_out}, current_temperature_in={current_T_in}')
        
        # Make sure the target temperature is not the same as the inlet temperature to avoid division by zero
        if abs(self.target_temperature-current_T_in) >= 0.1 and abs(current_T_out - current_T_in) >= 0.1:
            calculated_current_mass_flow = (qext_w / self.cp) * (1 / (current_T_in - current_T_out))
            # required mass flow is defined by qext, cp in W and the dT between current_T_in and current_T_out
            calculated_required_mass_flow = (qext_w / self.cp) * (1 / (current_T_in - self.target_temperature))

            mass_flow_corr_factor = calculated_current_mass_flow / calculated_required_mass_flow
            required_mass_flow = current_mass_flow / mass_flow_corr_factor

            if self.debug == True:# and self.heat_consumer_idx == 3:
                print(f"Calculated cp: {qext_w / (current_mass_flow * (current_T_in - current_T_out))}")
                print(f"Calculated current mass flow: {calculated_current_mass_flow}")
                print(f"calculated required mass flow: {calculated_required_mass_flow}")
                print(f"required mass flow: {required_mass_flow}")
        
        else:
            # If the target temperature has already been reached, the mass flow does not need to be adjusted
            required_mass_flow = current_mass_flow

        # Add damping factor (e.g. 0.5)
        damping_factor = 0.5

        # Calculated mass flow taking damping into account, is required to prevent big flow rate changes in the network
        new_mass_flow = (damping_factor * current_mass_flow) + ((1 - damping_factor) * required_mass_flow)
        #new_mass_flow = required_mass_flow

        # Check mass flow limits and update mass flow in network model
        new_mass_flow = max(min(new_mass_flow, self.max_mass_flow), self.min_mass_flow)
        net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = new_mass_flow
        
        if self.debug == True:# and self.heat_consumer_idx == 3:
            print(f'ReturnTemperatureController nach control_step: Iteration: {self.iteration}, Heat Consumer ID: {self.heat_consumer_idx}, new_mass_flow={new_mass_flow}')

        return super(ReturnTemperatureController, self).control_step(net)
"""

class ReturnTemperatureController(BasicCtrl):
    def __init__(self, net, heat_consumer_idx, target_temperature, kp=1, ki=0.0, kd=0.0, tolerance=2, min_velocity=0.01, max_velocity=2, max_iterations=100, debug=False, **kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_consumer_idx = heat_consumer_idx
        self.target_temperature = target_temperature
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
        self.previous_temperatures = {}
        self.original_target_temperature = self.target_temperature

        self.data_source = None
        self.debug = debug

        self.calculate_mass_flow_limits(net)
        self.at_min_mass_flow_limit = False
        self.at_max_mass_flow_limit = False

    def time_step(self, net, time_step):
        self.iteration = 0  # reset iteration counter
        self.previous_temperatures = {}
        self.integral = 0
        self.last_error = None
        self.target_temperature = self.original_target_temperature

        if self.at_min_mass_flow_limit:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.min_mass_flow * 1.05
        if self.at_max_mass_flow_limit:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.max_mass_flow * 0.95

        # Check if a data source exists and get the target temperature for the current time step
        if self.data_source is not None:
            self.target_temperature = self.data_source.df.at[time_step, 'return_temperature']
        
        return time_step
    
    def calculate_mass_flow_limits(self, net):
        diameter = net.heat_consumer["diameter_m"].at[self.heat_consumer_idx]
        area = (pi / 4) * (diameter ** 2)

        self.min_mass_flow = self.min_velocity * area * 1000
        self.max_mass_flow = self.max_velocity * area * 1000

    def calculate_error(self, net):
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        error = self.target_temperature - current_T_out
        return error

    def update_integral(self, error):
        self.integral += error

    def calculate_derivative(self, error):
        if self.last_error is None:
            derivative = 0
        else:
            derivative = error - self.last_error
        self.last_error = error
        return derivative

    def control_step(self, net):
        # Incrementation iteration counter
        self.iteration += 1

        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        # not converging under that value
        if qext_w <= 500:
            net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = self.min_mass_flow
            return super(ReturnTemperatureController, self).control_step(net)

        # Calculate new mass flow
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15
        current_mass_flow = net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx]
        #calculated_cp = qext_w / (current_mass_flow * (current_T_in-current_T_out))

        if self.debug:
            print(f"heat_consumer_idx: {self.heat_consumer_idx}, Iteration: {self.iteration}, qext_w: {qext_w}, current_T_in: {current_T_in},  target_T_out: {self.target_temperature}, current_T_out: {current_T_out}, current_mass_flow: {current_mass_flow}")
        
        # Ensure not to divide by zero
        if current_T_in == self.target_temperature:
            self.target_temperature += 0.1  # Adjust target slightly to avoid division by zero

        # necessary
        if current_T_in < self.target_temperature + 15:
            self.target_temperature = current_T_in - 15

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

        # adjusted_delta_T = current_T_in - current_T_out + pid_output # pid = target-out 
        adjusted_delta_T = current_T_in - (current_T_out + pid_output) # pid = target-out 
        if adjusted_delta_T == 0:
            adjusted_delta_T = 0.1  # Adjust slightly to avoid division by zero
        
        # at the first Iteration the massflow from the previous is taken, which leads to problems when correcting the mass flow
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

        # Apply physical limits
        new_mass_flow = np.clip(new_mass_flow, self.min_mass_flow, self.max_mass_flow)  # Clipped to avoid too low or too high mass flow

        net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx] = new_mass_flow

        if self.debug:
            print(f"heat_consumer_idx: {self.heat_consumer_idx}, delta_T: {delta_T}, adjusted_delta_T: {adjusted_delta_T}, Error: {error}, Integral: {self.integral}, Derivative: {derivative}, PID output: {pid_output}, mass_flow_correction: {mass_flow_correction}, New mass flow: {new_mass_flow}")

        return super(ReturnTemperatureController, self).control_step(net)

    def is_converged(self, net):
        qext_w = net.heat_consumer["qext_w"].at[self.heat_consumer_idx]
        # not converging under that value
        if qext_w <= 500:
            return True
        
        # Check whether the temperatures have changed within the specified tolerance
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx]
        previous_T_in = self.previous_temperatures.get(self.heat_consumer_idx)

        # Testing for convergence
        temperature_change = abs(current_T_in - previous_T_in) if previous_T_in is not None else float('inf')
        converged_T_in = temperature_change < self.tolerance

        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        temperature_diff = abs(current_T_out - self.target_temperature)
        converged_T_out = temperature_diff < self.tolerance

        # Update temperature for next run
        self.previous_temperatures[self.heat_consumer_idx] = current_T_in

        current_mass_flow = net.heat_consumer["controlled_mdot_kg_per_s"].at[self.heat_consumer_idx]

        # Check whether the mass flow limits have been reached
        self.at_min_mass_flow_limit = current_mass_flow <= self.min_mass_flow
        self.at_max_mass_flow_limit = current_mass_flow >= self.max_mass_flow

        if self.at_min_mass_flow_limit and self.iteration > 10:
            if self.debug:
                print(f"Min mass flow limit reached for heat_consumer_idx: {self.heat_consumer_idx}, current_temperature: {current_T_in-273.15}, target_T_out: {self.target_temperature}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}")
            return True
        
        if self.at_max_mass_flow_limit and self.iteration > 10:
            if self.debug:
                print(f"Max mass flow limit reached for heat_consumer_idx: {self.heat_consumer_idx}, current_temperature: {current_T_in-273.15}, target_T_out: {self.target_temperature}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}")
            return True
        
        if converged_T_in and converged_T_out:
            if self.debug:
                print(f'Regler konvergiert: heat_consumer_idx: {self.heat_consumer_idx}, current_temperature: {current_T_in-273.15}, target_T_out: {self.target_temperature}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}')
            return True

        # Check if the maximum number of iterations has been reached
        if self.iteration >= self.max_iterations:
            if self.debug:
                print(f"Max iterations reached for heat_consumer_idx: {self.heat_consumer_idx}")
            #return True

        return False
