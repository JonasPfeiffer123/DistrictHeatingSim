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

        #print(current_dp)
        dp_error = self.target_pressure - current_dp
        
        # Berechnung der notwendigen Anpassung des Massenstroms
        # Der Proportionalitätsfaktor bestimmt, wie stark der Massenstrom angepasst wird
        pressure_lift_adjustment = dp_error * self.proportional_gain

        # Ermittlung des aktuellen Massenstroms
        current_pressure_lift = net.res_circ_pump_pressure["deltap_bar"].at[self.circ_pump_pressure_idx]
        #print(current_pressure_lift)

        # Ermittlung des neuen Massenstroms
        new_pressure_lift = max(0, current_pressure_lift + pressure_lift_adjustment)
        
        #print(new_pressure_lift)
        # Aktualisierung des Massenstroms im Netzmodell
        net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx] = new_pressure_lift

        return super(MassFlowController, self).control_step(net)
    
class ReturnTemperatureController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, target_temperature, tolerance=2, proportional_gain=0.001, **kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.flow_control_idx = heat_exchanger_idx
        self.target_temperature = target_temperature
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

    def time_step(self, net, time_step):
        # wird bei jedem Zeitschritt aufgerufen
        return time_step

    def is_converged(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        return abs(current_temperature - self.target_temperature) < self.tolerance

    def control_step(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        
        #print(self.target_temperature)
        print(current_temperature)
        
        temperature_error = self.target_temperature - current_temperature
        
        #print(temperature_error)
        
        # Berechnung der notwendigen Anpassung des Massenstroms
        # Der Proportionalitätsfaktor bestimmt, wie stark der Massenstrom angepasst wird
        mass_flow_adjustment = temperature_error * self.proportional_gain
        
        #print(mass_flow_adjustment)
        
        # Ermittlung des aktuellen Massenstroms
        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]
        
        #print(current_mass_flow)
        
        # Ermittlung des neuen Massenstroms
        new_mass_flow = max(0, current_mass_flow + mass_flow_adjustment)

        print(new_mass_flow)

        print(net.res_heat_exchanger["p_from_bar"].at[self.heat_exchanger_idx])
        print(net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx])

        # Aktualisierung des Massenstroms im Netzmodell
        net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = new_mass_flow
        
        return super(ReturnTemperatureController, self).control_step(net)