from pandapower.control.basic_controller import BasicCtrl

# currently not used
class MassFlowController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, circ_pump_pressure_idx, target_pressure, tolerance=0.05, proportional_gain=0.2, **kwargs):
        super(MassFlowController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_pressure = target_pressure
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

    def time_step(self, net, time_step):
        return time_step

    def is_converged(self, net):
        current_dp = net.res_heat_exchanger["p_from_bar"].at[self.heat_exchanger_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]
        return abs(current_dp- self.target_pressure) < self.tolerance

    def control_step(self, net):
        current_dp = net.res_heat_exchanger["p_from_bar"].at[self.heat_exchanger_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]

        dp_error = self.target_pressure - current_dp
    
        pressure_lift_adjustment = dp_error * self.proportional_gain

        current_pressure_lift = net.res_circ_pump_pressure["deltap_bar"].at[self.circ_pump_pressure_idx]

        new_pressure_lift = max(0, current_pressure_lift + pressure_lift_adjustment)
        
        net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx] = new_pressure_lift

        return super(MassFlowController, self).control_step(net)
    
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
        
        """print(self.heat_exchanger_idx)
        print(self.target_temperature)
        print(current_temperature)
        print(current_mass_flow)
        print(mass_flow_adjustment)
        print(new_mass_flow)"""
        
        return super(ReturnTemperatureController, self).control_step(net)