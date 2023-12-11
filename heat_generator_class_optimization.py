import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
from math import pi

from heat_generators.Solarthermie import Berechnung_STA
from heat_generators.heat_generators import aw, Geothermie, BHKW, Biomassekessel, Gaskessel
from heat_generators.Wirtschaftlichkeitsbetrachtung import WGK_WP, WGK_BHKW, WGK_Biomassekessel, WGK_Gaskessel, WGK_STA

class ConventionalHeatProducer:
    def __init__(self, name, max_capacity, min_load, efficiency, fuel_cost):
        self.name = name
        self.max_capacity = max_capacity
        self.min_load = min_load
        self.efficiency = efficiency
        self.fuel_cost = fuel_cost

    def calculate(self, load_L, VLT_L):
        raise NotImplementedError("Subclass must implement this method")

class HeatPump:
    def __init__(self, name, max_capacity, min_load, fuel_cost, source_temp, COP_data):
        self.name = name
        self.max_capacity = max_capacity
        self.min_load = min_load
        self.fuel_cost = fuel_cost
        self.source_temp = source_temp
        self.COP_data = COP_data

class WasteHeatPump:
    def __init__(self, name, cooling_load, min_load, fuel_cost, source_temp, COP_data):
        self.name = name
        self.min_load = min_load
        self.fuel_cost = fuel_cost
        self.source_temp = source_temp
        self.COP_data = COP_data
        self.cooling_load = cooling_load

    def calculate_COP(self, VLT_L):
        values = self.COP_data
        row_header = values[0, 1:]
        col_header = values[1:, 0]
        values = values[1:, 1:]
        f = RegularGridInterpolator((col_header, row_header), values, method='linear')
        VLT_L = np.minimum(VLT_L, 75)
        QT_array = np.full_like(VLT_L, self.source_temp)
        COP_L = f(np.column_stack((QT_array, VLT_L)))
        return COP_L
    
    def calculate(self, load_L, VLT_L):
        if self.cooling_load == 0:
            return 0, 0, np.zeros_like(load_L), np.zeros_like(VLT_L), 0
        
        COP_L = self.calculate_COP(VLT_L)
        heat_output_L = self.cooling_load / (1 - (1 / COP_L))
        el_power_L = heat_output_L - self.cooling_load

        heat_output_sum = np.sum(heat_output_L / 1000)
        el_power_sum = np.sum(el_power_L / 1000)

        max_heat_output = np.max(heat_output_L)

        return el_power_sum, heat_output_sum, heat_output_L

class Geothermal:
    def __init__(self, name, min_load, fuel_cost, source_temp, COP_data, area, borehole_depth, spec_drilling_cost=120, spec_extraction_power=50, full_usage_hours=2400, probe_distance=10):
        self.name = name
        self.min_load = min_load
        self.fuel_cost = fuel_cost
        self.source_temp = source_temp
        self.COP_data = COP_data
        self.area = area
        self.borehole_depth = borehole_depth
        self.spec_drilling_cost = spec_drilling_cost
        self.spec_extraction_power = spec_extraction_power
        self.full_usage_hours = full_usage_hours
        self.probe_distance = probe_distance
        self.max_capacity = 0

    def calculate_COP(self, VLT_L):
        values = self.COP_data
        row_header = values[0, 1:]
        col_header = values[1:, 0]
        values = values[1:, 1:]
        f = RegularGridInterpolator((col_header, row_header), values, method='linear')
        VLT_L = np.minimum(VLT_L, 75)
        QT_array = np.full_like(VLT_L, self.source_temp)
        COP_L = f(np.column_stack((QT_array, VLT_L)))
        return COP_L
    
    def calculate(self, load_L, VLT_L):
        COP_L = self.calculate_COP(VLT_L)

        if self.area == 0 or self.borehole_depth == 0:
            return 0, 0, np.zeros_like(load_L), np.zeros_like(VLT_L), 0, 0

        probe_area = (pi/4) * (2*self.probe_distance)**2
        number_of_probes = round(self.area / probe_area, 0)  # 22

        extraction_power_2400 = self.borehole_depth * self.spec_extraction_power * number_of_probes / 1000
        # kW for 2400 h, 22 probes, 50 W/m: 220 kW
        extracted_heat_amount = extraction_power_2400 * self.full_usage_hours / 1000  # MWh
        investment_costs_probes = self.borehole_depth * self.spec_drilling_cost * number_of_probes

        # The actual number of operating hours of the heat pump depends on the heat output,
        # which is related to the extraction power from the assumed number of operating hours
        B_min = 1
        B_max = 8760
        tolerance = 0.5
        while B_max - B_min > tolerance:
            B = (B_min + B_max) / 2
            # Calculate the extraction power
            extraction_power = extracted_heat_amount * 1000 / B  # kW
            # Calculate the heat output and electrical power
            heat_output_L = extraction_power / (1 - (1 / COP_L))
            electrical_power_L = heat_output_L - extraction_power

            # Determine the portion that is actually used
            portion = np.minimum(1, load_L / heat_output_L)

            # Calculate the actual values
            actual_heat_output_L = heat_output_L * portion
            actual_electrical_power_L = electrical_power_L * portion
            actual_extraction_power_L = actual_heat_output_L - actual_electrical_power_L
            extracted_heat = np.sum(actual_extraction_power_L) / 1000
            heat_amount = np.sum(actual_heat_output_L) / 1000
            electricity_demand = np.sum(actual_electrical_power_L) / 1000
            operating_hours = np.count_nonzero(actual_heat_output_L)

            # If there is no usage, the result is 0
            if operating_hours == 0:
                actual_heat_output_L = np.array([0])
                actual_electrical_power_L = np.array([0])

            if extracted_heat > extracted_heat_amount:
                B_min = B
            else:
                B_max = B

        max_heat_output = max(actual_heat_output_L)
        self.max_capacity = max_heat_output

        COP = heat_amount / electricity_demand

        return electricity_demand, heat_amount, actual_heat_output_L

class CHP(ConventionalHeatProducer):
    def __init__(self, name, max_capacity, min_load, efficiency, fuel_cost, electrical_efficiency):
        super().__init__(name, max_capacity, min_load, fuel_cost, efficiency)
        self.electrical_efficiency = electrical_efficiency

    def calculate(self, load_L, VLT_L):
        electrical_output_CHP = self.max_capacity*self.electrical_efficiency
        heat_output_CHP_L = np.where(load_L >= self.max_capacity, self.max_capacity, load_L)
        electrical_output_CHP_L = np.where(load_L >= self.max_capacity, electrical_output_CHP,
                                           electrical_output_CHP * (load_L / self.max_capacity))
        
        heat_output_CHP_sum = np.sum(heat_output_CHP_L / 1000)
        electrical_output_CHP_sum = np.sum(electrical_output_CHP_L / 1000)

        fuel_demand_sum = (heat_output_CHP_sum + electrical_output_CHP_sum) / self.efficiency

        return fuel_demand_sum, heat_output_CHP_sum, heat_output_CHP_L

class BiomassBoiler(ConventionalHeatProducer):
    def __init__(self, name, max_capacity, min_load, efficiency, fuel_cost):
        super().__init__(name, max_capacity, min_load, efficiency, fuel_cost)

    def calculate(self, load_L, VLT_L):
        heat_output_L = np.where(load_L >= self.max_capacity, self.max_capacity, load_L)
        total_heat= np.sum(heat_output_L / 1000)
        fuel_demand_sum = total_heat / self.efficiency
        return fuel_demand_sum, total_heat, heat_output_L

class GasBoiler(ConventionalHeatProducer):
    def __init__(self, name, max_capacity, min_load, efficiency, fuel_cost):
        super().__init__(name, max_capacity, min_load, efficiency, fuel_cost)

    def calculate(self, load_L, VLT_L):
        generated_heat_L = np.where(load_L >= self.max_capacity, self.max_capacity, load_L)
        total_heat = np.sum(generated_heat_L) / 1000
        fuel_demand_sum = total_heat / self.efficiency

        return fuel_demand_sum, total_heat, generated_heat_L

### ###
def calculate_solar_thermal(bruttofläche_STA, vs, Typ, Last_L, VLT_L, RLT_L, TRY, \
                            time_steps, calc1, calc2, Restlast_L, Restwärmebedarf, Jahreswärmebedarf, \
                            data, colors, q, r, T, BEW, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration):
    # Hier fügen Sie die spezifische Logik für die Solarthermie-Berechnung ein
    Wärmemenge_Solarthermie, Wärmeleistung_Solarthermie_L = Berechnung_STA(
        bruttofläche_STA, vs, Typ, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration)
    
    Restlast_L -= Wärmeleistung_Solarthermie_L
    Restwärmebedarf -= Wärmemenge_Solarthermie
    Anteil_Solarthermie = Wärmemenge_Solarthermie / Jahreswärmebedarf

    data.append(Wärmeleistung_Solarthermie_L)
    colors.append("red")

    WGK_Solarthermie = WGK_STA(bruttofläche_STA, vs, Typ, Wärmemenge_Solarthermie, q, r, T, BEW)
    WGK_Gesamt += Wärmemenge_Solarthermie * WGK_Solarthermie

    Wärmemengen.append(Wärmemenge_Solarthermie)
    Anteile.append(Anteil_Solarthermie)
    WGK.append(WGK_Solarthermie)

    return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_geothermal(Restlast_L, VLT_L, Fläche, Bohrtiefe, Temperatur_Geothermie, \
                         COP_data,el_Leistung_ges_L, Restwärmebedarf, Strombedarf_WP, \
                         Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                         tech, Strompreis, q, r, T, duration):
    # Hier fügen Sie die spezifische Logik für die Geothermie-Berechnung ein
    Wärmemenge_Geothermie, Strombedarf_Geothermie, Wärmeleistung_Geothermie_L, el_Leistung_Geothermie_L, \
    max_Wärmeleistung, Investitionskosten_Sonden = Geothermie(Restlast_L, VLT_L, Fläche, Bohrtiefe, Temperatur_Geothermie, COP_data, duration)

    spez_Investitionskosten_Erdsonden = Investitionskosten_Sonden / max_Wärmeleistung

    el_Leistung_ges_L -= el_Leistung_Geothermie_L
    Restlast_L -= Wärmeleistung_Geothermie_L

    Restwärmebedarf -= Wärmemenge_Geothermie
    Strombedarf_WP += Strombedarf_Geothermie

    Anteil_Geothermie = Wärmemenge_Geothermie / Jahreswärmebedarf

    data.append(Wärmeleistung_Geothermie_L)
    colors.append("blue")

    WGK_Geothermie = WGK_WP(max_Wärmeleistung, Wärmemenge_Geothermie, Strombedarf_Geothermie, tech,
                            spez_Investitionskosten_Erdsonden, Strompreis, q, r, T)
    WGK_Gesamt += Wärmemenge_Geothermie * WGK_Geothermie

    Wärmemengen.append(Wärmemenge_Geothermie)
    Anteile.append(Anteil_Geothermie)
    WGK.append(WGK_Geothermie)

    return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_wasteheat(Restlast_L, VLT_L, Kühlleistung_Abwärme, Temperatur_Abwärme, \
                         COP_data, el_Leistung_ges_L, Restwärmebedarf, Strombedarf_WP, \
                         Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                         tech, Strompreis, q, r, T, duration):
    
    Wärmemenge_Abwärme, Strombedarf_Abwärme, Wärmeleistung_Abwärme_L, el_Leistung_Abwärme_L, \
                max_Wärmeleistung_Abwärme, Betriebsstunden_Abwärme = aw(Restlast_L, VLT_L, Kühlleistung_Abwärme,
                                                                        Temperatur_Abwärme, COP_data, duration)

    el_Leistung_ges_L += el_Leistung_Abwärme_L
    Restlast_L -= Wärmeleistung_Abwärme_L

    Restwärmebedarf -= Wärmemenge_Abwärme
    Strombedarf_WP += Strombedarf_Abwärme

    Anteil_Abwärme = Wärmemenge_Abwärme / Jahreswärmebedarf

    data.append(Wärmeleistung_Abwärme_L)
    colors.append("grey")

    WGK_Abwärme = WGK_WP(max_Wärmeleistung_Abwärme, Wärmemenge_Abwärme, Strombedarf_Abwärme, tech, 0,
                            Strompreis, q, r, T)
    WGK_Gesamt += Wärmemenge_Abwärme * WGK_Abwärme

    Wärmemengen.append(Wärmemenge_Abwärme)
    Anteile.append(Anteil_Abwärme)
    WGK.append(WGK_Abwärme)

    return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_chp(Restlast_L, th_Leistung_BHKW, Gaspreis, Holzpreis, tech, Restwärmebedarf, \
                  Jahreswärmebedarf, data, colors, Strompreis, q, r, T, Wärmemengen, Anteile, WGK, \
                  el_Leistung_ges_L, Strommenge_BHKW, WGK_Gesamt, duration):
    
    Wärmeleistung_BHKW, Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge_BHKW, Strommenge_BHKW, \
    Brennstoffbedarf_BHKW = BHKW(th_Leistung_BHKW, Restlast_L, duration)

    if tech == "BHKW":
        Brennstoffpreis = Gaspreis
    elif tech == "Holzgas-BHKW":
        Brennstoffpreis = Holzpreis

    Restlast_L -= Wärmeleistung_BHKW_L
    Restwärmebedarf -= Wärmemenge_BHKW
    el_Leistung_ges_L += el_Leistung_BHKW_L

    Anteil_BHKW = Wärmemenge_BHKW / Jahreswärmebedarf

    data.append(Wärmeleistung_BHKW_L)
    colors.append("yellow")

    if tech == "BHKW":
        Brennstoffpreis = Gaspreis
    elif tech == "Holzgas-BHKW":
        Brennstoffpreis = Holzpreis

    wgk_BHKW = WGK_BHKW(Wärmeleistung_BHKW, Wärmemenge_BHKW, Strommenge_BHKW, tech, Brennstoffbedarf_BHKW,
                        Brennstoffpreis, Strompreis, q, r, T)
    WGK_Gesamt += Wärmemenge_BHKW * wgk_BHKW

    Wärmemengen.append(Wärmemenge_BHKW)
    Anteile.append(Anteil_BHKW)
    WGK.append(wgk_BHKW)

    return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strommenge_BHKW, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_biomass_boiler(Restlast_L, P_BMK, Restwärmebedarf, Jahreswärmebedarf, data, \
                             colors, Holzpreis, q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration):
    # Hier fügen Sie die spezifische Logik für die Biomassekessel-Berechnung ein
    Wärmeleistung_BMK_L, Wärmemenge_BMK = Biomassekessel(Restlast_L, P_BMK, duration)

    Restlast_L -= Wärmeleistung_BMK_L
    Restwärmebedarf -= Wärmemenge_BMK

    Anteil_BMK = Wärmemenge_BMK / Jahreswärmebedarf

    data.append(Wärmeleistung_BMK_L)
    colors.append("green")

    Nutzungsgrad_BMK = 0.8
    Brennstoffbedarf_BMK = Wärmemenge_BMK/Nutzungsgrad_BMK
    WGK_BMK = WGK_Biomassekessel(P_BMK, Wärmemenge_BMK, Brennstoffbedarf_BMK, Holzpreis, q, r, T)
    WGK_Gesamt += Wärmemenge_BMK * WGK_BMK

    Wärmemengen.append(Wärmemenge_BMK)
    Anteile.append(Anteil_BMK)
    WGK.append(WGK_BMK)

    return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_gas_boiler(Restlast_L, Restwärmebedarf, Jahreswärmebedarf, data, colors, Gaspreis, \
                         q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, Last_L, duration):
    # Hier fügen Sie die spezifische Logik für die Gaskessel-Berechnung ein
    Wärmemenge_GK, Wärmeleistung_GK_L, Gasbedarf = Gaskessel(Restlast_L, duration)
    P_max = max(Last_L) * 1
    WGK_GK = WGK_Gaskessel(P_max, Wärmemenge_GK, Gasbedarf, Gaspreis, q, r, T)

    Restlast_L -= Wärmeleistung_GK_L
    Restwärmebedarf -= Wärmemenge_GK

    Anteil_GK = Wärmemenge_GK / Jahreswärmebedarf

    data.append(Wärmeleistung_GK_L)
    colors.append("purple")

    WGK_Gesamt += Wärmemenge_GK * WGK_GK

    Wärmemengen.append(Wärmemenge_GK)
    Anteile.append(Anteil_GK)
    WGK.append(WGK_GK)

    return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum):
    q = 1 + Kapitalzins / 100
    r = 1 + Preissteigerungsrate / 100
    T = Betrachtungszeitraum
    return q, r, T

def Berechnung_Erzeugermix(time_steps, calc1, calc2, bruttofläche_STA, vs, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, P_BMK, Gaspreis,
                           Strompreis, Holzpreis, initial_data, TRY, tech_order, BEW, th_Leistung_BHKW, Kühlleistung_Abwärme,
                           Temperatur_Abwärme, COP_data, Kapitalzins=5, Preissteigerungsrate=3, Betrachtungszeitraum=20):

    # Kapitalzins und Preissteigerungsrate in % -> Umrechung in Zinsfaktor und Preissteigerungsfaktor
    q, r, T = calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum)
    Last_L, VLT_L, RLT_L = initial_data

    duration = np.diff(time_steps[0:2]) / np.timedelta64(1, 'h')
    duration = duration[0]

    Jahreswärmebedarf = (np.sum(Last_L)/1000) * duration

    Restlast_L, Restwärmebedarf, WGK_Gesamt = Last_L.copy(), Jahreswärmebedarf, 0
    data, colors, Wärmemengen, Anteile, WGK = [], [], [], [], []

    Strombedarf_WP, Strommenge_BHKW = 0, 0
    el_Leistung_ges_L = np.zeros_like(Last_L)

    # zunächst Berechnung der Erzeugung
    for tech in tech_order:
        if tech == "Solarthermie":
            Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_solar_thermal(bruttofläche_STA, vs, Typ, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, Restlast_L, \
                                        Restwärmebedarf, Jahreswärmebedarf, data, colors, q, r, T, BEW, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration)
        
        elif tech == "Abwärme" or tech == "Abwasserwärme":
            el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_wasteheat(Restlast_L, VLT_L, Kühlleistung_Abwärme, Temperatur_Abwärme, COP_data, el_Leistung_ges_L, \
                                    Restwärmebedarf, Strombedarf_WP, Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                                    tech, Strompreis, q, r, T, duration)
            
        elif tech == "Geothermie":
            el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_geothermal(Restlast_L, VLT_L, Fläche, Bohrtiefe, Temperatur_Geothermie, COP_data,el_Leistung_ges_L, \
                                     Restwärmebedarf, Strombedarf_WP, Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                                     tech, Strompreis, q, r, T, duration)
            
        elif tech == "BHKW" or tech == "Holzgas-BHKW":
            el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strommenge_BHKW, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_chp(Restlast_L, th_Leistung_BHKW, Gaspreis, Holzpreis, tech, Restwärmebedarf, Jahreswärmebedarf, data, colors, \
                              Strompreis, q, r, T, Wärmemengen, Anteile, WGK, el_Leistung_ges_L, Strommenge_BHKW, WGK_Gesamt, duration)
            
        elif tech == "Biomassekessel":
            Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = calculate_biomass_boiler(
                Restlast_L, P_BMK, Restwärmebedarf, Jahreswärmebedarf, data, colors, Holzpreis, q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration)
            
        elif tech == "Gaskessel":
            Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = calculate_gas_boiler(
                Restlast_L, Restwärmebedarf, Jahreswärmebedarf, data, colors, Gaspreis, q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, Last_L, duration)

    WGK_Gesamt /= Jahreswärmebedarf
    
    return WGK_Gesamt, Jahreswärmebedarf, Last_L, data, tech_order, colors, Wärmemengen, WGK, Anteile

def optimize_mix(initial_values, time_steps, calc1, calc2, initial_data, TRY, COP_data, Typ, Gaspreis, Strompreis, Holzpreis, BEW, tech_order):
    def objective(variables):
        bruttofläche_STA, vs, P_BMK, th_Leistung_BHKW = variables

        WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, colors_L, Wärmemengen, WGK, Anteile = \
            Berechnung_Erzeugermix(time_steps, calc1, calc2, bruttofläche_STA, vs, Typ, 0, 0, 0, P_BMK, Gaspreis, Strompreis, \
                                        Holzpreis, initial_data, TRY, tech_order, BEW, \
                                        th_Leistung_BHKW, 0, 0, COP_data)
        
        print(bruttofläche_STA, vs, P_BMK, th_Leistung_BHKW)
        print(WGK_Gesamt)
        return WGK_Gesamt

    # Optimierung durchführen
    #result = minimize(objective, initial_values, method='SLSQP', bounds=[(0, 1000), (0, 100), (0, 500), (0, 500)], options={'maxiter': 1000})
    result = minimize(objective, initial_values, method='L-BFGS-B', bounds=[(0, 1000), (0, 100), (0, 500), (0, 500)], options={'maxiter': 1000})
    #result = minimize(objective, initial_values, method='TNC', bounds=[(0, 1000), (0, 100), (0, 500), (0, 500)], options={'maxiter': 1000})

    if result.success:
        optimized_values = result.x
        optimized_WGK_Gesamt = objective(optimized_values)
        print(f"Optimierte Werte: {optimized_values}")
        print(f"Minimale Wärmegestehungskosten: {optimized_WGK_Gesamt:.2f} €/MWh")
    else:
        print("Optimierung nicht erfolgreich")
        print(result.message)



#####################################
COP_data = np.loadtxt('heat_generators/Kennlinien WP.csv', delimiter=';')

waste_heat_pump = WasteHeatPump(name="Waste Heat Pump", cooling_load=50, min_load=0.5, fuel_cost=0.2, source_temp=5, COP_data=COP_data)
geothermal = Geothermal(name="Geothermal", min_load=0.5, fuel_cost=0.2, source_temp=15, COP_data=COP_data, area=200, borehole_depth=200, spec_drilling_cost=120, spec_extraction_power=50, full_usage_hours=2400, probe_distance=10)
chp = CHP(name="CHP Unit", max_capacity=20, min_load=0.5, efficiency=0.9, fuel_cost=0.05, electrical_efficiency=0.33)
biomass_boiler = BiomassBoiler(name="Biomass Boiler", max_capacity=100, min_load=0.3, efficiency=0.85, fuel_cost=0.08)
gas_boiler = GasBoiler(name="Gas Boiler", max_capacity=150, min_load=0.3, efficiency=0.9, fuel_cost=0.05)

producers = [biomass_boiler, chp]

# Jahreslastgang aus CSV-Datei laden
load_profile = pd.read_csv('results_time_series_net.csv', delimiter=';', parse_dates=['Zeitpunkt'])
load_profile.set_index('Zeitpunkt', inplace=True)

if __name__ == "__main__":
    main(load_profile, producers)
#####################################