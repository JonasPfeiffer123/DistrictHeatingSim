from pandapower.control.basic_controller import BasicCtrl

class MassFlowController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, circ_pump_mass_idx, target_pressure, tolerance=0.05, proportional_gain=0.2, **kwargs):
        super(MassFlowController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.circ_pump_mass_idx = circ_pump_mass_idx
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
        mass_flow_adjustment = dp_error * self.proportional_gain

        # Ermittlung des aktuellen Massenstroms
        current_mass_flow = net.res_circ_pump_mass["mdot_flow_kg_per_s"].at[self.circ_pump_mass_idx]

        # Ermittlung des neuen Massenstroms
        new_mass_flow = max(0, current_mass_flow + mass_flow_adjustment)
        
        # Aktualisierung des Massenstroms im Netzmodell
        net.circ_pump_mass["mdot_flow_kg_per_s"].at[self.circ_pump_mass_idx] = new_mass_flow
        
        return super(MassFlowController, self).control_step(net)
    
class ReturnTemperatureController(BasicCtrl):
    def __init__(self, net, heat_exchanger_idx, target_temperature, tolerance=0.2, proportional_gain=0.2, **kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.target_temperature = target_temperature
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

    def time_step(self, net, time_step):
        # wird bei jedem Zeitschritt aufgerufen
        return time_step

    def is_converged(self, net):
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx]
        return abs(current_temperature - self.target_temperature) < self.tolerance

    def control_step(self, net):
        print(net.heat_exchanger["loss_coefficient"].at[self.heat_exchanger_idx])
        current_temperature = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx]
        print(current_temperature)

        temperature_error = self.target_temperature - current_temperature
        
        # Berechnung der notwendigen Anpassung des Massenstroms
        # Der Proportionalitätsfaktor bestimmt, wie stark der Massenstrom angepasst wird
        loss_coefficient_adjustment = temperature_error * self.proportional_gain

        # Ermittlung des aktuellen Massenstroms
        current_loss_coefficient = net.heat_exchanger["loss_coefficient"].at[self.heat_exchanger_idx]

        # Ermittlung des neuen Massenstroms
        new_loss_coefficient = max(0, current_loss_coefficient + loss_coefficient_adjustment)
        
        # Aktualisierung des Massenstroms im Netzmodell
        net.heat_exchanger["loss_coefficient"].at[self.heat_exchanger_idx] = new_loss_coefficient
        
        return super(ReturnTemperatureController, self).control_step(net)