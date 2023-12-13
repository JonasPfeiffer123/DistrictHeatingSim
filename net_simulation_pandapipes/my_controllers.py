from pandapower.control.basic_controller import BasicCtrl

class WorstPointPressureController(BasicCtrl):
    def __init__(self, net, worst_point_idx, circ_pump_pressure_idx=0, target_dp_min_bar=1, tolerance=0.1, proportional_gain=0.2,**kwargs):
        super(WorstPointPressureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = worst_point_idx
        self.flow_control_idx = worst_point_idx
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_dp_min_bar = target_dp_min_bar
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

    def time_step(self, net, time_step):
        return time_step

    def is_converged(self, net):
        current_dp_bar = net.res_flow_control["p_from_bar"].at[self.flow_control_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]

        # check, if the temperature converged
        dp_within_tolerance = abs(current_dp_bar - self.target_dp_min_bar) < self.tolerance

        if dp_within_tolerance == True:
            return dp_within_tolerance
    

    def control_step(self, net):
        current_dp_bar = net.res_flow_control["p_from_bar"].at[self.flow_control_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]
        dp_error = self.target_dp_min_bar - current_dp_bar

        current_plift_bar = net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx]
        
        plift_adjustment = dp_error * self.proportional_gain        

        new_plift = current_plift_bar + plift_adjustment
        
        """print(current_dp_bar)
        print(dp_error)
        print(current_plift_bar)
        print(plift_adjustment)
        print(new_plift)"""
        net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx] = new_plift
        
        return super(WorstPointPressureController, self).control_step(net)
    

class ReturnTemperatureController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, target_temperature, tolerance=2, lower_proportional_gain=0.0005, higher_proportional_gain=0.0025, min_mass_flow=0.005, max_mass_flow=1,**kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.flow_control_idx = heat_exchanger_idx
        self.target_temperature = target_temperature
        self.initial_target_temperature = target_temperature
        self.tolerance = tolerance
        self.lower_proportional_gain = lower_proportional_gain
        self.higher_proportional_gain = higher_proportional_gain
        self.min_mass_flow = min_mass_flow
        self.max_mass_flow = max_mass_flow

    def time_step(self, net, time_step):
        return time_step

    def is_converged(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]

        # check, if min or max massflow are reached
        at_min_mass_flow = current_mass_flow < self.min_mass_flow
        at_max_mass_flow = current_mass_flow > self.max_mass_flow

        # check, if the temperature converged
        temperature_within_tolerance = abs(current_temperature - self.target_temperature) < self.tolerance

        if temperature_within_tolerance == False and at_max_mass_flow == True:
            self.target_temperature = current_temperature - 0.5
        
        if temperature_within_tolerance == False and at_min_mass_flow == True:
            print(True)
            self.target_temperature = current_temperature + 0.5

        if temperature_within_tolerance == True:
            self.target_temperature = self.initial_target_temperature
            return temperature_within_tolerance
    

    def control_step(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        temperature_error = self.target_temperature - current_temperature

        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]

        if current_mass_flow <= 0.05:
            mass_flow_adjustment = temperature_error * self.lower_proportional_gain        
        if current_mass_flow > 0.05:
            mass_flow_adjustment = temperature_error * self.higher_proportional_gain

        new_mass_flow = current_mass_flow + mass_flow_adjustment
        new_mass_flow = max(self.min_mass_flow, min(new_mass_flow, self.max_mass_flow))
        
        net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = new_mass_flow
        
        #print(self.heat_exchanger_idx)
        #print(self.target_temperature)
        #print(current_temperature)
        #print(current_mass_flow)
        #print(mass_flow_adjustment)
        #print(new_mass_flow)
        
        return super(ReturnTemperatureController, self).control_step(net)

# useful values for p, i and d have to be figured out
"""# adaptive PID controller
class ReturnTemperatureController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, target_temperature, 
                 kp_init=0.0025, ki_init=0.0001, kd_init=0.0001, 
                 min_mass_flow=0.005, max_mass_flow=1, **kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.flow_control_idx = heat_exchanger_idx
        self.initial_target_temperature = target_temperature
        self.target_temperature = target_temperature
        self.kp = kp_init  # Proportional gain
        self.ki = ki_init  # Integral gain
        self.kd = kd_init  # Derivative gain
        self.min_mass_flow = min_mass_flow
        self.max_mass_flow = max_mass_flow
        self.previous_error = 0
        self.integral = 0
    
    def is_converged(self, net):
        tolerance = 2.0  # Setzen Sie hier Ihre gewünschte Toleranz
        
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]

        # check, if min or max massflow are reached
        at_min_mass_flow = current_mass_flow < self.min_mass_flow
        at_max_mass_flow = current_mass_flow > self.max_mass_flow

        # check, if the temperature converged
        temperature_within_tolerance = abs(current_temperature - self.target_temperature) <= tolerance

        if temperature_within_tolerance == False and at_max_mass_flow == True:
            self.target_temperature = current_temperature - 0.5
        
        if temperature_within_tolerance == False and at_min_mass_flow == True:
            self.target_temperature = current_temperature + 0.5

        if temperature_within_tolerance == True:
            self.target_temperature = self.initial_target_temperature
            return temperature_within_tolerance
    
    def control_step(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        temperature_error = self.target_temperature - current_temperature

        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]

        # Adaptive Gain-Anpassung basierend auf dem aktuellen Massenstrom
        if current_mass_flow <= 0.05:
            self.kp = self.kp * 2  # Erhöhung des P-Gains bei kleinen Strömen

        # Proportional term
        P = self.kp * temperature_error

        # Integral term
        self.integral += temperature_error
        I = self.ki * self.integral

        # Derivative term
        D = self.kd * (temperature_error - self.previous_error)
        self.previous_error = temperature_error
        
        print(P)
        print(I)
        print(D)
        # PID output
        pid_output = P + I + D

        # Adjust mass flow based on PID output
        new_mass_flow = max(self.min_mass_flow, min(current_mass_flow + pid_output, self.max_mass_flow))
        
        
        print(self.heat_exchanger_idx)
        print(current_temperature)
        print(current_mass_flow)
        print(pid_output)
        print(new_mass_flow)
        # Apply new mass flow
        net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = new_mass_flow

        return super(ReturnTemperatureController, self).control_step(net)

    def update_gains(self, new_kp, new_ki, new_kd):
        # Method to update PID gains dynamically
        self.kp = new_kp
        self.ki = new_ki
        self.kd = new_kd"""
