from pandapower.control.basic_controller import BasicCtrl

class MassFlowController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, circ_pump_pressure_idx, target_pressure, tolerance=0.05, proportional_gain=0.2, **kwargs):
        super(MassFlowController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_pressure = target_pressure
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

    def time_step(self, net, time_step):
        # wird bei jedem Zeitschritt aufgerufen
        return time_step

    def is_converged(self, net):
        current_dp = net.res_heat_exchanger["p_from_bar"].at[self.heat_exchanger_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]
        return abs(current_dp- self.target_pressure) < self.tolerance

    def control_step(self, net):
        current_dp = net.res_heat_exchanger["p_from_bar"].at[self.heat_exchanger_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]

        dp_error = self.target_pressure - current_dp
        
        # Berechnung der notwendigen Anpassung des Massenstroms
        # Der Proportionalitätsfaktor bestimmt, wie stark der Massenstrom angepasst wird
        pressure_lift_adjustment = dp_error * self.proportional_gain

        # Ermittlung des aktuellen Massenstroms
        current_pressure_lift = net.res_circ_pump_pressure["deltap_bar"].at[self.circ_pump_pressure_idx]

        # Ermittlung des neuen Massenstroms
        new_pressure_lift = max(0, current_pressure_lift + pressure_lift_adjustment)
        
        # Aktualisierung des Massenstroms im Netzmodell
        net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx] = new_pressure_lift

        return super(MassFlowController, self).control_step(net)
    
class ReturnTemperatureController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, target_temperature, tolerance=2, proportional_gain=0.0015, min_mass_flow=0.01, max_mass_flow=1,**kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.flow_control_idx = heat_exchanger_idx
        self.target_temperature = target_temperature
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain
        self.min_mass_flow = min_mass_flow
        self.max_mass_flow = max_mass_flow

    def time_step(self, net, time_step):
        # wird bei jedem Zeitschritt aufgerufen
        return time_step

    def is_converged(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]

        # Überprüfen, ob der minimale Massenstrom erreicht ist
        at_min_mass_flow = current_mass_flow <= self.min_mass_flow
        at_max_mass_flow = current_mass_flow >= self.max_mass_flow

        # Überprüfen, ob die Temperatur innerhalb der Toleranzgrenzen liegt
        temperature_within_tolerance = abs(current_temperature - self.target_temperature) < self.tolerance

        if temperature_within_tolerance == True:
            return temperature_within_tolerance
        elif temperature_within_tolerance == False and at_max_mass_flow == True:
            return at_max_mass_flow
        elif temperature_within_tolerance == False and at_min_mass_flow == True:
            return at_min_mass_flow


    def control_step(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        temperature_error = self.target_temperature - current_temperature
    
        # Berechnung der notwendigen Anpassung des Massenstroms
        # Der Proportionalitätsfaktor bestimmt, wie stark der Massenstrom angepasst wird
        mass_flow_adjustment = temperature_error * self.proportional_gain
        
        # Ermittlung des aktuellen Massenstroms
        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]
        # Ermittlung des neuen Massenstroms unter Beachtung der Grenzwerte
        new_mass_flow = current_mass_flow + mass_flow_adjustment
        new_mass_flow = max(self.min_mass_flow, min(new_mass_flow, self.max_mass_flow))  # Beschränkung auf min/max Werte
        
        # Aktualisierung des Massenstroms im Netzmodell
        net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = new_mass_flow
        
        return super(ReturnTemperatureController, self).control_step(net)