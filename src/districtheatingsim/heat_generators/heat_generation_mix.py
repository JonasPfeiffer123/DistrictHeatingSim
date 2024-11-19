"""
Filename: heat_generator_classes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
Description: Contains functions for calculating economic factors and optimizing the energy generation mix.

"""

import numpy as np

from scipy.optimize import minimize

from districtheatingsim.heat_generators.heat_pumps import *
from districtheatingsim.heat_generators.chp import CHP
from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler
from districtheatingsim.heat_generators.gas_boiler import GasBoiler
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat
from districtheatingsim.heat_generators.solar_thermal import SolarThermal

from districtheatingsim.heat_generators.annuity import annuität

def calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum):
    """
    Calculate economic factors for energy generation mix optimization.

    Args:
        Kapitalzins (float): Capital interest rate as a percentage.
        Preissteigerungsrate (float): Inflation rate as a percentage.
        Betrachtungszeitraum (int): Consideration period in years.

    Returns:
        tuple: Calculated factors q (interest rate factor), r (inflation rate factor), and T (consideration period).
    """
    q = 1 + Kapitalzins / 100
    r = 1 + Preissteigerungsrate / 100
    T = Betrachtungszeitraum
    return q, r, T

def Berechnung_Erzeugermix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables=[], variables_order=[], kapitalzins=5, preissteigerungsrate=3, betrachtungszeitraum=20, stundensatz=45):
    """
    Calculate the optimal energy generation mix for a given set of technologies and parameters.

    Args:
        tech_order (list): List of technology objects to be considered.
        initial_data (tuple): Initial data including time steps, load profile, flow temperature, and return temperature.
        start (int): Start time step for the calculation.
        end (int): End time step for the calculation.
        TRY (object): Test Reference Year data for temperature and solar radiation.
        COP_data (object): Coefficient of Performance data for heat pumps.
        Gaspreis (float): Gas price in €/kWh.
        Strompreis (float): Electricity price in €/kWh.
        Holzpreis (float): Biomass price in €/kWh.
        BEW (float): Specific CO2 emissions for electricity in kg CO2/kWh.
        variables (list, optional): List of variable values for optimization. Defaults to [].
        variables_order (list, optional): List of variable names for optimization. Defaults to [].
        kapitalzins (int, optional): Capital interest rate in percentage. Defaults to 5.
        preissteigerungsrate (int, optional): Inflation rate in percentage. Defaults to 3.
        betrachtungszeitraum (int, optional): Consideration period in years. Defaults to 20.
        stundensatz (int, optional): Hourly rate for labor in €/h. Defaults to 45.

    Returns:
        dict: Results of the energy generation mix calculation, including heat demand, cost, emissions, and other metrics.
    """
    q, r, T = calculate_factors(kapitalzins, preissteigerungsrate, betrachtungszeitraum)
    time_steps, Last_L, VLT_L, RLT_L = initial_data

    duration = np.diff(time_steps[0:2]) / np.timedelta64(1, 'h')
    duration = duration[0]

    general_results = {
        'time_steps': time_steps,
        'Last_L': Last_L,
        'VLT_L': VLT_L,
        'RLT_L': RLT_L,
        'Jahreswärmebedarf': (np.sum(Last_L)/1000) * duration,
        'WGK_Gesamt': 0,
        'Restwärmebedarf': (np.sum(Last_L)/1000) * duration,
        'Restlast_L': Last_L.copy(),
        'Wärmeleistung_L': [],
        'colors': [],
        'Wärmemengen': [],
        'Anteile': [],
        'WGK': [],
        'Strombedarf': 0,
        'Strommenge': 0,
        'el_Leistungsbedarf_L': np.zeros_like(Last_L),
        'el_Leistung_L': np.zeros_like(Last_L),
        'el_Leistung_ges_L': np.zeros_like(Last_L),
        'specific_emissions_L': [],
        'primärenergie_L': [],
        'specific_emissions_Gesamt': 0,
        'primärenergiefaktor_Gesamt': 0,
        'techs': [],
        'tech_classes': []
    }

    for idx, tech in enumerate(tech_order.copy()):
        if len(variables) > 0:
            if tech.name.startswith("Solarthermie"):
                tech.bruttofläche_STA = variables[variables_order.index(f"bruttofläche_STA_{idx}")]
                tech.vs = variables[variables_order.index(f"vs_{idx}")]
            elif tech.name.startswith("Abwärme") or tech.name.startswith("Abwasserwärme"):
                tech.Kühlleistung_Abwärme = variables[variables_order.index(f"Kühlleistung_Abwärme_{idx}")]
            elif tech.name.startswith("Flusswasser"):
                tech.Wärmeleistung_FW_WP = variables[variables_order.index(f"Wärmeleistung_FW_WP_{idx}")]
            elif tech.name.startswith("Geothermie"):
                tech.Fläche = variables[variables_order.index(f"Fläche_{idx}")]
                tech.Bohrtiefe = variables[variables_order.index(f"Bohrtiefe_{idx}")]
            elif tech.name.startswith("BHKW") or tech.name.startswith("Holzgas-BHKW"):
                tech.th_Leistung_BHKW = variables[variables_order.index(f"th_Leistung_BHKW_{idx}")]
                if tech.speicher_aktiv:
                    tech.Speicher_Volumen_BHKW = variables[variables_order.index(f"Speicher_Volumen_BHKW_{idx}")]
            elif tech.name.startswith("Biomassekessel"):
                tech.P_BMK = variables[variables_order.index(f"P_BMK_{idx}")]

        if tech.name.startswith("Solarthermie"):
            tech_results = tech.calculate(VLT_L, RLT_L, TRY, time_steps, start, end, q, r, T, BEW, stundensatz, duration, general_results)
        elif tech.name.startswith("Abwärme") or tech.name.startswith("Abwasserwärme"):
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
        elif tech.name.startswith("Flusswasser"):
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
        elif tech.name.startswith("Geothermie"):
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
        elif tech.name.startswith("AqvaHeat"):
            tech_results = tech.calculate(VLT_L, COP_data, duration, general_results)
        elif tech.name.startswith("BHKW") or tech.name.startswith("Holzgas-BHKW"):
            tech_results = tech.calculate(Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
        elif tech.name.startswith("Biomassekessel"):
            tech_results = tech.calculate(Holzpreis, q, r, T, BEW, stundensatz, duration, general_results)
        elif tech.name.startswith("Gaskessel"):
            tech_results = tech.calculate(Gaspreis, q, r, T, BEW, stundensatz, duration, general_results)
        elif tech.name.startswith("Power-to-Heat"):
            tech_results = tech.calculate(Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
        else:
            tech_order.remove(tech)
            print(f"{tech.name} ist kein gültiger Erzeugertyp und wird daher nicht betrachtet.")

        if tech_results['Wärmemenge'] > 0:
            general_results['Wärmeleistung_L'].append(tech_results['Wärmeleistung_L'])
            general_results['Wärmemengen'].append(tech_results['Wärmemenge'])
            general_results['Anteile'].append(tech_results['Wärmemenge']/general_results['Jahreswärmebedarf'])
            general_results['WGK'].append(tech_results['WGK'])
            general_results['specific_emissions_L'].append(tech_results['spec_co2_total'])
            general_results['primärenergie_L'].append(tech_results['primärenergie'])
            general_results['colors'].append(tech_results['color'])
            general_results['Restlast_L'] -= tech_results['Wärmeleistung_L']
            general_results['Restwärmebedarf'] -= tech_results['Wärmemenge']
            general_results['WGK_Gesamt'] += (tech_results['Wärmemenge']*tech_results['WGK'])/general_results['Jahreswärmebedarf']
            general_results['specific_emissions_Gesamt'] += (tech_results['Wärmemenge']*tech_results['spec_co2_total'])/general_results['Jahreswärmebedarf']
            general_results['primärenergiefaktor_Gesamt'] += tech_results['primärenergie']/general_results['Jahreswärmebedarf']

            if tech.name.startswith("BHKW") or tech.name.startswith("Holzgas-BHKW"):
                general_results['Strommenge'] += tech_results["Strommenge"]
                general_results['el_Leistung_L'] += tech_results["el_Leistung_L"]
                general_results['el_Leistung_ges_L'] += tech_results["el_Leistung_L"]

            if tech.name.startswith("Abwärme") or tech.name.startswith("Abwasserwärme") or tech.name.startswith("Flusswasser") or tech.name.startswith("Geothermie"):
                general_results['Strombedarf'] += tech_results["Strombedarf"]
                general_results['el_Leistungsbedarf_L'] += tech_results["el_Leistung_L"]
                general_results['el_Leistung_ges_L'] -= tech_results['el_Leistung_L']

            if "Wärmeleistung_Speicher_L" in tech_results.keys():
                general_results['Restlast_L'] -= tech_results['Wärmeleistung_Speicher_L']

        else:
            tech_order.remove(tech)
            print(f"{tech.name} wurde durch die Optimierung entfernt.")

    for tech in tech_order:
        general_results['techs'].append(tech.name)
        general_results['tech_classes'].append(tech)

    return general_results

def optimize_mix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins, preissteigerungsrate, betrachtungszeitraum, stundensatz, weights):
    """
    Optimize the energy generation mix for minimal cost, emissions, and primary energy use.

    Args:
        tech_order (list): List of technology objects to be considered.
        initial_data (tuple): Initial data including time steps, load profile, flow temperature, and return temperature.
        start (int): Start time step for the optimization.
        end (int): End time step for the optimization.
        TRY (object): Test Reference Year data for temperature and solar radiation.
        COP_data (object): Coefficient of Performance data for heat pumps.
        Gaspreis (float): Gas price in €/kWh.
        Strompreis (float): Electricity price in €/kWh.
        Holzpreis (float): Biomass price in €/kWh.
        BEW (float): Specific CO2 emissions for electricity in kg CO2/kWh.
        kapitalzins (float): Capital interest rate in percentage.
        preissteigerungsrate (float): Inflation rate in percentage.
        betrachtungszeitraum (int): Consideration period in years.
        stundensatz (float): Hourly rate for labor in €/h.
        weights (dict): Weights for different optimization criteria.

    Returns:
        list: Optimized list of technology objects with updated parameters.
    """
    initial_values = []
    variables_order = []
    bounds = []
    for idx, tech in enumerate(tech_order):
        if isinstance(tech, SolarThermal):
            initial_values.append(tech.bruttofläche_STA)
            variables_order.append(f"bruttofläche_STA_{idx}")
            bounds.append((tech.opt_area_min, tech.opt_area_max))

            initial_values.append(tech.vs)
            variables_order.append(f"vs_{idx}")
            bounds.append((tech.opt_volume_min, tech.opt_volume_max))

        elif isinstance(tech, CHP):
            initial_values.append(tech.th_Leistung_BHKW)
            variables_order.append(f"th_Leistung_BHKW_{idx}")
            bounds.append((tech.opt_BHKW_min, tech.opt_BHKW_max))

            if tech.speicher_aktiv == True:
                initial_values.append(tech.Speicher_Volumen_BHKW)
                variables_order.append(f"Speicher_Volumen_BHKW_{idx}")
                bounds.append((tech.opt_BHKW_Speicher_min, tech.opt_BHKW_Speicher_max))

        elif isinstance(tech, BiomassBoiler):
            initial_values.append(tech.P_BMK)
            variables_order.append(f"P_BMK_{idx}")
            bounds.append((tech.opt_BMK_min, tech.opt_BMK_max))

            if tech.speicher_aktiv == True:
                initial_values.append(tech.Speicher_Volumen)
                variables_order.append(f"Speicher_Volumen_{idx}")
                bounds.append((tech.opt_Speicher_min, tech.opt_Speicher_max))

        elif isinstance(tech, Geothermal):
            initial_values.append(tech.Fläche)
            variables_order.append(f"Fläche_{idx}")
            min_area_geothermal = 0
            max_area_geothermal = 5000
            bounds.append((min_area_geothermal, max_area_geothermal))

            initial_values.append(tech.Bohrtiefe)
            variables_order.append(f"Bohrtiefe_{idx}")
            min_area_depth = 0
            max_area_depth = 400
            bounds.append((min_area_depth, max_area_depth))

        elif isinstance(tech, WasteHeatPump):
            initial_values.append(tech.Kühlleistung_Abwärme)
            variables_order.append(f"Kühlleistung_Abwärme_{idx}")
            min_cooling = 0
            max_cooling = 500
            bounds.append((min_cooling, max_cooling))

        elif isinstance(tech, RiverHeatPump):
            initial_values.append(tech.Wärmeleistung_FW_WP)
            variables_order.append(f"Wärmeleistung_FW_WP_{idx}")
            min_power_river = 0
            max_power_river = 1000
            bounds.append((min_power_river, max_power_river))


    def objective(variables):
        general_results = Berechnung_Erzeugermix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables, variables_order, \
                                            kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum, stundensatz=stundensatz)
        
        # Skalierung der Zielgrößen basierend auf ihren erwarteten Bereichen
        wgk_scale = 1.0  # Annahme: Wärmegestehungskosten liegen im Bereich von 0 bis 300 €/MWh
        co2_scale = 1000  # Annahme: Spezifische Emissionen liegen im Bereich von 0 bis 1 tCO2/MWh
        primary_energy_scale = 100.0  # Annahme: Primärenergiefaktor liegt im Bereich von 0 bis 3

        weighted_sum = (weights['WGK_Gesamt'] * general_results['WGK_Gesamt'] * wgk_scale +
                        weights['specific_emissions_Gesamt'] * general_results['specific_emissions_Gesamt'] * co2_scale +
                        weights['primärenergiefaktor_Gesamt'] * general_results['primärenergiefaktor_Gesamt'] * primary_energy_scale)
        
        return weighted_sum
    
    # optimization
    result = minimize(objective, initial_values, method='SLSQP', bounds=bounds, options={'maxiter': 100})

    if result.success:
        optimized_values = result.x
        optimized_objective = objective(optimized_values)
        print(f"Optimierte Werte: {optimized_values}")
        print(f"Minimierte gewichtete Summe: {optimized_objective:.2f}")

        for idx, tech in enumerate(tech_order):
            if isinstance(tech, SolarThermal):
                tech.bruttofläche_STA = optimized_values[variables_order.index(f"bruttofläche_STA_{idx}")]
                tech.vs = optimized_values[variables_order.index(f"vs_{idx}")]
            elif isinstance(tech, BiomassBoiler):
                tech.P_BMK = optimized_values[variables_order.index(f"P_BMK_{idx}")]
                if tech.speicher_aktiv:
                    tech.Speicher_Volumen = optimized_values[variables_order.index(f"Speicher_Volumen_{idx}")]
            elif isinstance(tech, CHP):
                tech.th_Leistung_BHKW = optimized_values[variables_order.index(f"th_Leistung_BHKW_{idx}")]
                if tech.speicher_aktiv:
                    tech.Speicher_Volumen_BHKW = optimized_values[variables_order.index(f"Speicher_Volumen_BHKW_{idx}")]
            elif isinstance(tech, Geothermal):
                tech.Fläche = optimized_values[variables_order.index(f"Fläche_{idx}")]
                tech.Bohrtiefe = optimized_values[variables_order.index(f"Bohrtiefe_{idx}")]
            elif isinstance(tech, WasteHeatPump):
                tech.Kühlleistung_Abwärme = optimized_values[variables_order.index(f"Kühlleistung_Abwärme_{idx}")]
            elif isinstance(tech, RiverHeatPump):
                tech.Wärmeleistung_FW_WP = optimized_values[variables_order.index(f"Wärmeleistung_FW_WP_{idx}")]

        return tech_order
    else:
        print("Optimierung nicht erfolgreich")
        print(result.message)
