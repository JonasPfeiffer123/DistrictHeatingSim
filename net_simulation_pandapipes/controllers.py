from pandapower.control.basic_controller import BasicCtrl
from math import pi

class WorstPointPressureController(BasicCtrl):
    def __init__(self, net, worst_point_idx, circ_pump_pressure_idx=0, target_dp_min_bar=1, tolerance=0.2, proportional_gain=0.2,**kwargs):
        super(WorstPointPressureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = worst_point_idx
        self.flow_control_idx = worst_point_idx
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_dp_min_bar = target_dp_min_bar
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain

        self.iteration = 0  # Iterationszähler hinzufügen


    def time_step(self, net, time_step):
        self.iteration = 0  # Iterationszähler reset
        return time_step

    def is_converged(self, net):
        qext_w = net.heat_exchanger["qext_w"].at[self.heat_exchanger_idx]
        if qext_w <= 300:
            return True
        current_dp_bar = net.res_flow_control["p_from_bar"].at[self.flow_control_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]

        # check, if the temperature converged
        dp_within_tolerance = abs(current_dp_bar - self.target_dp_min_bar) < self.tolerance

        if dp_within_tolerance == True:
            return dp_within_tolerance
    
    def control_step(self, net):
        # Inkrementieren des Iterationszählers
        self.iteration += 1

        # Überprüfe, ob der Wärmestrom im Wärmeübertrager null ist
        qext_w = net.heat_exchanger["qext_w"].at[self.heat_exchanger_idx]
        current_dp_bar = net.res_flow_control["p_from_bar"].at[self.flow_control_idx] - net.res_heat_exchanger["p_to_bar"].at[self.heat_exchanger_idx]
        current_plift_bar = net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx]
        current_pflow_bar = net.circ_pump_pressure["p_flow_bar"].at[self.circ_pump_pressure_idx]

        if qext_w <= 300:
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
    def __init__(self, net, heat_exchanger_idx, target_temperature, tolerance=2, min_velocity=0.001, max_velocity=2, **kwargs):
        super(ReturnTemperatureController, self).__init__(net, **kwargs)
        self.heat_exchanger_idx = heat_exchanger_idx
        self.flow_control_idx = heat_exchanger_idx
        self.target_temperature = target_temperature
        self.initial_target_temperature = target_temperature
        self.tolerance = tolerance
        self.min_velocity = min_velocity
        self.max_velocity = max_velocity

        self.iteration = 0  # Iterationszähler hinzufügen
        self.calculate_mass_flow_limits(net)
        self.previous_temperatures = {}

        self.at_min_mass_flow_limit = False
        self.at_max_mass_flow_limit = False

        self.data_source = None

    def time_step(self, net, time_step):
        self.iteration = 0  # Iterationszähler reset
        self.previous_temperatures = {}
        if self.at_min_mass_flow_limit:
            net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = self.min_mass_flow * 1.05
        if self.at_max_mass_flow_limit:
            net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = self.max_mass_flow * 0.95

        # Überprüfen, ob eine Datenquelle vorhanden ist und die Zieltemperatur für den aktuellen Zeitschritt abrufen
        if self.data_source is not None:
            self.target_temperature = self.data_source.df.at[time_step, 'return_temperature']
        
        return time_step

    def update_state(self, net):
        # Aktualisieren Sie die Zustandsvariable mit den aktuellen Eintrittstemperaturen
        self.previous_temperatures[self.heat_exchanger_idx] = net.res_heat_exchanger["t_from_k"].at[self.heat_exchanger_idx]

    def calculate_mass_flow_limits(self, net):
        diameter = net.heat_exchanger["diameter_m"].at[self.heat_exchanger_idx]
        area = (pi / 4) * (diameter ** 2)

        self.min_mass_flow = self.min_velocity * area * 1000
        self.max_mass_flow = self.max_velocity * area * 1000

    def is_converged(self, net):
        qext_w = net.heat_exchanger["qext_w"].at[self.heat_exchanger_idx]
        if qext_w == 0:
            return True

        # Prüfen Sie, ob sich die Temperaturen innerhalb der festgelegten Toleranz geändert haben
        current_T_in = net.res_heat_exchanger["t_from_k"].at[self.heat_exchanger_idx]
        previous_T_in = self.previous_temperatures.get(self.heat_exchanger_idx)

        # Prüfung auf Konvergenz
        temperature_change = abs(current_T_in - previous_T_in) if previous_T_in is not None else float('inf')
        converged_T_in = temperature_change < self.tolerance

        current_T_out = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        temperature_diff = abs(current_T_out - self.target_temperature)
        converged_T_out = temperature_diff < self.tolerance

        # Aktualisieren Sie die Temperatur für den nächsten Durchlauf
        self.previous_temperatures[self.heat_exchanger_idx] = current_T_in

        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]

        # Überprüfe, ob die Massenstromgrenzen erreicht sind
        self.at_min_mass_flow_limit = current_mass_flow <= self.min_mass_flow
        self.at_max_mass_flow_limit = current_mass_flow >= self.max_mass_flow

        if self.at_min_mass_flow_limit and self.iteration > 10:
            return True
        
        if self.at_max_mass_flow_limit and self.iteration > 10:
            return True
        
        if converged_T_in and converged_T_out:
            #print(f'Regler konvergiert: heat_exchanger_idx: {self.heat_exchanger_idx}, qext_w: {qext_w}, current_temperature: {current_T_in}, previous_temperature: {previous_T_in}, to_temperature: {current_T_out}, current_mass_flow: {current_mass_flow}')
            return True
        
    def control_step(self, net):
        # Inkrementieren des Iterationszählers
        self.iteration += 1
        self.calculate_mass_flow_limits(net)

        # Wärmeleistung des Wärmeübertragers
        qext_w = net.heat_exchanger["qext_w"].at[self.heat_exchanger_idx]
        #print(qext_w)
        # Überprüfen, ob die Wärmeleistung niedrig genug ist, um keine Anpassung vorzunehmen
        if qext_w == 0:
            net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = 0
            return super(ReturnTemperatureController, self).control_step(net)

        # Aktuelle Austrittstemperatur des Fluids
        current_T_out = net.res_heat_exchanger["t_to_k"].at[self.heat_exchanger_idx] - 273.15
        cp = 4190 # Spezifische Wärmekapazität in J/(kg·K)
        current_T_in = net.res_heat_exchanger["t_from_k"].at[self.heat_exchanger_idx] - 273.15 # Eintrittstemperatur in °C

        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]
        
        #if self.heat_exchanger_idx == 3:
        #print(f'ReturnTemperatureController vor control_step: Iteration: {self.iteration}, Heat Exchanger ID: {self.heat_exchanger_idx}, current_massflow={current_mass_flow}, qext_w={qext_w}, target_temperature_out={self.target_temperature}, current_temperature_out={current_T_out}, current_temperature_in={current_T_in}')

        # Sicherstellen, dass die Zieltemperatur nicht gleich der Eintrittstemperatur ist, um Division durch Null zu vermeiden
        if abs(self.target_temperature-current_T_in) >= 0.1 and abs(current_T_out - current_T_in) >= 0.1:
            required_mass_flow = current_mass_flow - (qext_w / cp) * ((-self.target_temperature + current_T_out)/((current_T_in - current_T_out) * (current_T_in - self.target_temperature)))
        else:
            # Wenn die Zieltemperatur bereits erreicht ist, muss der Massenstrom nicht angepasst werden
            required_mass_flow = current_mass_flow

        # Dämpfungsfaktor hinzufügen (z.B. 0.5)
        damping_factor = 0.5
        # Aktueller Massenstrom
        current_mass_flow = net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx]

        # Berechneter Massenstrom unter Berücksichtigung der Dämpfung
        new_mass_flow = (damping_factor * current_mass_flow) + ((1 - damping_factor) * required_mass_flow)

        # Überprüfen der Massenstromgrenzen und Aktualisieren des Massenstroms im Netzwerkmodell
        new_mass_flow = max(min(new_mass_flow, self.max_mass_flow), self.min_mass_flow)
        net.flow_control["controlled_mdot_kg_per_s"].at[self.flow_control_idx] = new_mass_flow
        
        #if self.heat_exchanger_idx == 3:
        #print(f'ReturnTemperatureController nach control_step: Iteration: {self.iteration}, Heat Exchanger ID: {self.heat_exchanger_idx}, new_mass_flow={new_mass_flow}')

        return super(ReturnTemperatureController, self).control_step(net)