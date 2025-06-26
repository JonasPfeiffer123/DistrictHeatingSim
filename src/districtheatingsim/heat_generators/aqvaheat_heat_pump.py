"""
Filename: heat_pumps.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains classes for different types of heat pumps and methods to calculate performance and economic metrics.

"""

import numpy as np

import CoolProp.CoolProp as CP

from districtheatingsim.heat_generators.base_heat_pumps import HeatPump

class AqvaHeat(HeatPump):
    """
    This class represents a AqvaHeat-solution (vacuum ice slurry generator with attached heat pump) and provides methods to calculate various performance and economic metrics.

    Args:
        HeatPump (_type_): Base class for the heat pump.

    Attributes:
        Wärmeleistung_FW_WP (float): Heat output of the river water heat pump.
        Temperatur_FW_WP (float): Temperature of the river water.
        dT (float): Temperature difference. Default is 0.
        spez_Investitionskosten_Flusswasser (float): Specific investment costs for river water heat pump per kW. Default is 1000.
        spezifische_Investitionskosten_WP (float): Specific investment costs of the heat pump per kW. Default is 1000.
        min_Teillast (float): Minimum partial load. Default is 0.2.

    Methods:
        Berechnung_WP(self.Wärmeleistung_kW, VLT_L, COP_data): Calculates the cooling load, electric power consumption, and adjusted flow temperatures.
        abwärme(Last_L, VLT_L, COP_data, duration): Calculates the waste heat and other performance metrics.
        calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results): Calculates the economic and environmental metrics for the heat pump.
        to_dict(): Converts the object attributes to a dictionary.
        from_dict(data): Creates an object from a dictionary of attributes.
    """
    def __init__(self, name, nominal_power=100, temperature_difference=0):

        self.name = name
        self.nominal_power = nominal_power
        self.min_partial_load = 1  # no partial load for now (0..1)
        self.temperature_difference = 2.5  # difference over heat exchanger
        self.Wärmeleistung_FW_WP = nominal_power

    def calculate(self, economic_parameters, duration, load_profile, **kwargs):
        VLT_L = kwargs.get('VLT_L')
        COP_data = kwargs.get('COP_data')

        """
        Calculates the economic and environmental metrics for the AqvaHeat-solution.
        Args:
            VLT_L (array): Flow temperatures.
            COP_data (array): COP data for interpolation.
            economic_parameters (dict): Economic parameters dictionary containing fuel costs, capital interest rate, inflation rate, time period, and operational costs.
            duration (float): Time duration.
            load_profile (array): Load profile of the system in kW.

        Returns:
            dict: Dictionary containing calculated metrics and results.
        """

        residual_powers = load_profile
        effective_powers = np.zeros_like(residual_powers)

        intermediate_temperature = 12  # °C

        # calculate power in time steps where operation of aggregate is possible due to minimal partial load
        operation_mask = residual_powers >= self.nominal_power * self.min_partial_load
        effective_powers[operation_mask] = np.minimum(residual_powers[operation_mask], self.nominal_power)

        # HEAT PUMP
        # calculate first the heat pump (from 12°C to supply temperature)
        COP, effective_output_temperatures = self.calculate_COP(VLT_L, intermediate_temperature, COP_data)
        cooling_powers = effective_powers * (1 - (1 / COP))
        electrical_powers = effective_powers - cooling_powers

        # disable heat pump when not reaching supply temperature
        operation_mask = effective_output_temperatures >= VLT_L - self.temperature_difference  # TODO: verify direction of difference
        effective_powers[~operation_mask] = 0
        cooling_powers[~operation_mask] = 0
        electrical_powers[~operation_mask] = 0

        # sum energy over whole lifetime
        # convert to MWh
        heat_supplied = np.sum(effective_powers / 1000) * duration
        cooling_supplied = np.sum(cooling_powers / 1000) * duration

        # VACUUM ICE GENERATOR
        # now the vacuum ice generator, needs to supply 12°C from river water to the heatpump
        # cooling supplied by heat pump is heat supplied by vacuum ice process 

        isentropic_efficiency = 0.7  # Adjust this value based on the actual compressor efficiency
        fluid = 'Water'
        molar_mass_water = 18.01528  # in g/mol

        # Triple point conditions for water
        # temperature_triple_point = 273.16  # Temperature in Kelvin
        # pressure_triple_point = 611.657  # Pressure in Pascal

        # Define initial conditions
        triple_point_pressure =  CP.PropsSI('ptriple', 'T', 0, 'P', 0, fluid) + 0.01 # in Pascal, delta because of validity range
        triple_point_temperature = CP.PropsSI('T', 'Q', 0, 'P', triple_point_pressure + 1, fluid)  # Triple point temperature

        initial_pressure = triple_point_pressure
        initial_temperature = triple_point_temperature

        # Define final conditions after first compression
        final_temperature = 12 + 273.15  # Convert to Kelvin
        final_pressure = CP.PropsSI('P', 'T', final_temperature, 'Q', 0, fluid)

        # mass flow from condensing vapor at 12°C, 14hPa
        mass_flows = effective_powers / (CP.PropsSI('H','P',14000,'Q',1,'Water') - 
                                        CP.PropsSI('H','P',14000,'Q',0,'Water'))
        # electrical power needed compressing vapor from triple point 
        energy_compression = (CP.PropsSI('H', 'T', final_temperature, 'P', final_pressure, fluid) -
                                      CP.PropsSI('H', 'T', initial_temperature, 'P', initial_pressure, fluid)) / isentropic_efficiency

        electrical_powers += mass_flows * energy_compression / 1000  # W -> kW

        self.Wärmemenge_AqvaHeat = heat_supplied
        self.Wärmeleistung_kW = effective_powers

        electricity_consumed = np.sum(electrical_powers / 1000) * duration
        self.Strombedarf_AqvaHeat = electricity_consumed

        self.el_Leistung_kW = electrical_powers

        WGK_Abwärme = -1
        self.primärenergie = self.Strombedarf_AqvaHeat * self.primärenergiefaktor

        self.spec_co2_total = -1


        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_AqvaHeat,  # heat energy for whole duration
            'Wärmeleistung_L': self.Wärmeleistung_kW,  # vector length time steps with actual power supplied
            'Strombedarf': self.Strombedarf_AqvaHeat,  # electrical energy consumed during whole duration
            'el_Leistung_L': self.el_Leistung_kW,  # vector length time steps with actual electrical power consumed
            'WGK': WGK_Abwärme,
            'spec_co2_total': self.spec_co2_total,  # tCO2/MWh_heat
            'primärenergie': self.primärenergie,
            'color': "blue"
        }

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        pass

    def add_optimization_parameters(self, idx):
        """
        AqvaHeat hat keine Optimierungsparameter. Diese Methode gibt leere Listen zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Leere Listen für initial_values, variables_order und bounds.
        """
        return [], [], []

    def get_display_text(self):
        return f"Name: {self.name}, Nennleistung: {self.nominal_power} kW, Temperaturdifferenz: {self.temperature_difference} K"
    
    def extract_tech_data(self):
        dimensions = f"Nennleistung: {self.nominal_power:.1f} kW, Temperaturdifferenz: {self.temperature_difference:.1f} K"
        costs = "Keine spezifischen Kosten"
        full_costs = "Keine spezifischen Kosten"
        return self.name, dimensions, costs, full_costs