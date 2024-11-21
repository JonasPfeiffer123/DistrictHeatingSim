"""
Filename: renovation_analysis.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-09
Description: Contains the calculation model for the renovation cost analysis.
"""

import numpy_financial as npf
from districtheatingsim.utilities.test_reference_year import import_TRY

class Building:
    """
    The Building class models a building and provides methods to calculate its heat demand.
    """
    STANDARD_U_VALUES = {
        'ground_u': 0.31, 'wall_u': 0.23, 'roof_u': 0.19,
        'window_u': 1.3, 'door_u': 1.3, 'air_change_rate': 0.5,
        'floors': 4, 'fracture_windows': 0.10, 'fracture_doors': 0.01,
        'Normaußentemperatur': -15, 'room_temp': 20, 'max_air_temp_heating': 15,
        'ww_demand_kWh_per_m2': 12.8
    }

    def __init__(self, ground_area, wall_area, roof_area, building_volume, u_values=None):
        """
        Initializes a Building instance.

        Args:
            ground_area (float): The ground area of the building.
            wall_area (float): The wall area of the building.
            roof_area (float): The roof area of the building.
            building_volume (float): The volume of the building.
            u_values (dict, optional): U-values for various components of the building. Defaults to standard values.
        """
        self.ground_area = ground_area
        self.wall_area = wall_area
        self.roof_area = roof_area
        self.building_volume = building_volume
        self.u_values = u_values if u_values else self.STANDARD_U_VALUES.copy()
        self.window_area = wall_area * self.u_values["fracture_windows"]
        self.door_area = wall_area * self.u_values["fracture_doors"]

    def calc_heat_demand(self):
        """
        Calculates the maximum heat demand of the building.
        """
        self.real_wall_area = self.wall_area - self.window_area - self.door_area

        heat_loss_per_K = {
            'wall': self.real_wall_area * self.u_values["wall_u"],
            'ground': self.ground_area * self.u_values["ground_u"],
            'roof': self.roof_area * self.u_values["roof_u"],
            'window': self.window_area * self.u_values["window_u"],
            'door': self.door_area * self.u_values["door_u"]
        }

        self.total_heat_loss_per_K = sum(heat_loss_per_K.values())
        self.dT_max_K = self.u_values["room_temp"] - self.u_values["Normaußentemperatur"]
        self.transmission_heat_loss = self.total_heat_loss_per_K * self.dT_max_K
        self.ventilation_heat_loss = 0.34 * self.u_values["air_change_rate"] * self.building_volume * self.dT_max_K
        self.max_heating_demand = self.transmission_heat_loss + self.ventilation_heat_loss

    def calc_yearly_heating_demand(self, temperature_data):
        """
        Calculates the yearly heating demand based on temperature data.

        Args:
            temperature_data (list): A list of temperature values.
        """
        m = self.max_heating_demand / (self.u_values["Normaußentemperatur"] - self.u_values["max_air_temp_heating"])
        b = -m * self.u_values["max_air_temp_heating"]
        self.yearly_heating_demand = sum(max(m * temp + b, 0) for temp in temperature_data if temp < self.u_values["max_air_temp_heating"]) / 1000

    def calc_yearly_warm_water_demand(self):
        """
        Calculates the yearly warm water demand.
        """
        self.yearly_warm_water_demand = self.u_values["ww_demand_kWh_per_m2"] * self.ground_area * self.u_values["floors"]

    def calc_yearly_heat_demand(self, temperature_data):
        """
        Calculates the total yearly heat demand.

        Args:
            temperature_data (list): A list of temperature values.
        """
        self.calc_heat_demand()
        self.calc_yearly_heating_demand(temperature_data)
        self.calc_yearly_warm_water_demand()
        self.yearly_heat_demand = self.yearly_heating_demand + self.yearly_warm_water_demand
    
class SanierungsAnalyse:
    """
    The SanierungsAnalyse class performs economic analysis for renovation projects.
    """
    def __init__(self, ref_heat_demand, san_heat_demand, energiepreis_ist, energiepreis_saniert, diskontierungsrate, jahre):
        """
        Initializes a SanierungsAnalyse instance.

        Args:
            ref_heat_demand (float): The reference heat demand.
            san_heat_demand (float): The heat demand after renovation.
            energiepreis_ist (float): The energy price before renovation.
            energiepreis_saniert (float): The energy price after renovation.
            diskontierungsrate (float): The discount rate.
            jahre (int): The number of years for the analysis.
        """
        self.ref_heat_demand = ref_heat_demand
        self.san_heat_demand = san_heat_demand
        self.energiepreis_ist = energiepreis_ist
        self.energiepreis_saniert = energiepreis_saniert
        self.diskontierungsrate = diskontierungsrate
        self.jahre = jahre

    def berechne_kosteneinsparungen(self):
        """
        Calculates the cost savings from the renovation.

        Returns:
            float: The cost savings.
        """
        kosten_ist = self.ref_heat_demand * self.energiepreis_ist
        kosten_saniert = self.san_heat_demand * self.energiepreis_saniert
        return kosten_ist - kosten_saniert

    def berechne_amortisationszeit(self, investitionskosten, foerderquote=0):
        """
        Calculates the payback period for the renovation.

        Args:
            investitionskosten (float): The investment costs.
            foerderquote (float, optional): The subsidy rate. Defaults to 0.

        Returns:
            float: The payback period.
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen()
        return effektive_investitionskosten / kosteneinsparung

    def berechne_npv(self, investitionskosten, foerderquote=0):
        """
        Calculates the net present value (NPV) of the renovation.

        Args:
            investitionskosten (float): The investment costs.
            foerderquote (float, optional): The subsidy rate. Defaults to 0.

        Returns:
            float: The NPV.
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen()
        cashflows = [-effektive_investitionskosten] + [kosteneinsparung] * self.jahre
        return npf.npv(self.diskontierungsrate, cashflows)

    def lcca(self, investitionskosten, betriebskosten, instandhaltungskosten, restwert, foerderquote=0):
        """
        Performs a life-cycle cost analysis (LCCA) for the renovation.

        Args:
            investitionskosten (float): The investment costs.
            betriebskosten (float): The operating costs.
            instandhaltungskosten (float): The maintenance costs.
            restwert (float): The residual value.
            foerderquote (float, optional): The subsidy rate. Defaults to 0.

        Returns:
            float: The NPV from the LCCA.
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        cashflows = [-effektive_investitionskosten] + [betriebskosten + instandhaltungskosten] * self.jahre + [restwert]
        return npf.npv(self.diskontierungsrate, cashflows)
    
    def berechne_roi(self, investitionskosten, foerderquote=0):
        """
        Calculates the return on investment (ROI) for the renovation.

        Args:
            investitionskosten (float): The investment costs.
            foerderquote (float, optional): The subsidy rate. Defaults to 0.

        Returns:
            float: The ROI.
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen() * self.jahre
        return (kosteneinsparung - effektive_investitionskosten) / effektive_investitionskosten

def calculate_all_results(length, width, floors, floor_height, u_ground, u_wall, u_roof, u_window, u_door,
                          energy_price_ist, energy_price_saniert, discount_rate, years, cold_rent, target_u_ground,
                          target_u_wall, target_u_roof, target_u_window, target_u_door,
                          cost_ground, cost_wall, cost_roof, cost_window, cost_door,
                          fracture_windows, fracture_doors, air_change_rate, min_air_temp, room_temp, max_air_temp_heating,
                          warmwasserbedarf, betriebskosten, instandhaltungskosten, restwert_anteile, foerderquote, try_filename):
    """
    Calculates all renovation results based on the provided parameters.

    Args:
        length (float): Length of the building.
        width (float): Width of the building.
        floors (int): Number of floors.
        floor_height (float): Height of each floor.
        u_ground (float): U-value of the ground.
        u_wall (float): U-value of the walls.
        u_roof (float): U-value of the roof.
        u_window (float): U-value of the windows.
        u_door (float): U-value of the doors.
        energy_price_ist (float): Energy price before renovation.
        energy_price_saniert (float): Energy price after renovation.
        discount_rate (float): Discount rate.
        years (int): Number of years for the analysis.
        cold_rent (float): Cold rent price per square meter.
        target_u_ground (float): Target U-value for the ground after renovation.
        target_u_wall (float): Target U-value for the walls after renovation.
        target_u_roof (float): Target U-value for the roof after renovation.
        target_u_window (float): Target U-value for the windows after renovation.
        target_u_door (float): Target U-value for the doors after renovation.
        cost_ground (float): Cost for renovating the ground per square meter.
        cost_wall (float): Cost for renovating the walls per square meter.
        cost_roof (float): Cost for renovating the roof per square meter.
        cost_window (float): Cost for renovating the windows per square meter.
        cost_door (float): Cost for renovating the doors per square meter.
        fracture_windows (float): Fraction of wall area that is windows.
        fracture_doors (float): Fraction of wall area that is doors.
        air_change_rate (float): Air change rate.
        min_air_temp (float): Minimum outside temperature.
        room_temp (float): Room temperature.
        max_air_temp_heating (float): Maximum air temperature for heating.
        warmwasserbedarf (float): Warm water demand per square meter per year.
        betriebskosten (dict): Operating costs for various building components.
        instandhaltungskosten (dict): Maintenance costs for various building components.
        restwert_anteile (dict): Residual value fractions for various building components.
        foerderquote (float): Subsidy rate.
        try_filename (str): File name of the test reference year data.

    Returns:
        dict: A dictionary containing the results of the renovation analysis.
    """
    temperature_data, _, _, _, _ = import_TRY(try_filename)

    grundflaeche = length * width
    wall_area_pro_stockwerk = (2*length + 2*width) * floor_height
    ground_area = grundflaeche
    wall_area = wall_area_pro_stockwerk * floors
    roof_area = grundflaeche
    building_volume = ground_area * floor_height * floors
    wohnflaeche = ground_area * floors

    ref_u_values = {
        'ground_u': u_ground,
        'wall_u': u_wall,
        'roof_u': u_roof,
        'window_u': u_window,
        'door_u': u_door,
        'air_change_rate': air_change_rate,
        'floors': floors,
        'fracture_windows': fracture_windows,
        'fracture_doors': fracture_doors,
        'Normaußentemperatur': min_air_temp,
        'room_temp': room_temp,
        'max_air_temp_heating': max_air_temp_heating,
        'ww_demand_kWh_per_m2': warmwasserbedarf
    }

    ref_building = Building(ground_area, wall_area, roof_area, building_volume, ref_u_values)
    ref_building.calc_yearly_heat_demand(temperature_data)
    alter_waermebedarf = ref_building.yearly_heat_demand

    ziel_u_wert = {
        'ground_u': target_u_ground,
        'wall_u': target_u_wall,
        'roof_u': target_u_roof,
        'window_u': target_u_window,
        'door_u': target_u_door
    }

    kosten = {
        'ground_u': cost_ground,
        'wall_u': cost_wall,
        'roof_u': cost_roof,
        'window_u': cost_window,
        'door_u': cost_door
    }

    investitionskosten = {
        'ground_u': kosten['ground_u'] * ground_area,
        'wall_u': kosten['wall_u'] * wall_area,
        'roof_u': kosten['roof_u'] * roof_area,
        'window_u': kosten['window_u'] * wall_area * fracture_windows,
        'door_u': kosten['door_u'] * wall_area * fracture_doors
    }

    restwert = {
        'ground_u': investitionskosten['ground_u'] * restwert_anteile['ground_u'],
        'wall_u': investitionskosten['wall_u'] * restwert_anteile['wall_u'],
        'roof_u': investitionskosten['roof_u'] * restwert_anteile['roof_u'],
        'window_u': investitionskosten['window_u'] * restwert_anteile['window_u'],
        'door_u': investitionskosten['door_u'] * restwert_anteile['door_u']
    }

    varianten = ['Bodensanierung', 'Fassadensanierung', 'Dachsanierung', 'Fenstersanierung', 'Türsanierung', 'Komplettsanierung']

    komponenten_u_wert = {
        'Bodensanierung': 'ground_u',
        'Fassadensanierung': 'wall_u',
        'Dachsanierung': 'roof_u',
        'Fenstersanierung': 'window_u',
        'Türsanierung': 'door_u'
    }

    ergebnisse = {}
    kaltmieten_pro_m2 = {}
    warmmieten_pro_m2 = {}

    ref_warmmiete_pro_m2 = cold_rent + ((ref_building.yearly_heat_demand / 12) / wohnflaeche) * energy_price_ist

    for komponente in varianten:
        san_building = Building(ground_area, wall_area, roof_area, building_volume, u_values=ref_building.u_values.copy())
        
        if komponente == 'Komplettsanierung':
            san_building.u_values.update(ziel_u_wert)
        else:
            san_building.u_values[komponenten_u_wert[komponente]] = ziel_u_wert[komponenten_u_wert[komponente]]

        san_building.calc_yearly_heat_demand(temperature_data)
        neuer_waermebedarf = san_building.yearly_heat_demand
        analyse = SanierungsAnalyse(alter_waermebedarf, neuer_waermebedarf, energy_price_ist, energy_price_saniert, discount_rate, years)

        if komponente == 'Komplettsanierung':
            investitionskosten_komponente = sum(investitionskosten.values())
            betriebskosten_komponente = sum(betriebskosten.values())
            instandhaltungskosten_komponente = sum(instandhaltungskosten.values())
            restwert_komponente = sum(restwert.values())
        else:
            investitionskosten_komponente = investitionskosten[komponenten_u_wert[komponente]]
            betriebskosten_komponente = betriebskosten[komponenten_u_wert[komponente]]
            instandhaltungskosten_komponente = instandhaltungskosten[komponenten_u_wert[komponente]]
            restwert_komponente = restwert[komponenten_u_wert[komponente]]

        amortisationszeit = analyse.berechne_amortisationszeit(investitionskosten_komponente, foerderquote)
        npv = analyse.berechne_npv(investitionskosten_komponente, foerderquote)
        lcca = analyse.lcca(investitionskosten_komponente,
                            betriebskosten_komponente,
                            instandhaltungskosten_komponente,
                            restwert_komponente,
                            foerderquote)
        roi = analyse.berechne_roi(investitionskosten_komponente, foerderquote)

        neue_kaltmiete_pro_m2 = cold_rent + investitionskosten_komponente / (amortisationszeit * 12 * wohnflaeche) if amortisationszeit != 0 else 0
        neue_warmmiete_pro_m2 = neue_kaltmiete_pro_m2 + ((neuer_waermebedarf / 12) / wohnflaeche) * energy_price_saniert

        kaltmieten_pro_m2[komponente] = neue_kaltmiete_pro_m2
        warmmieten_pro_m2[komponente] = neue_warmmiete_pro_m2

        ergebnisse[komponente] = {
            'Investitionskosten': investitionskosten_komponente,
            'Amortisationszeit': amortisationszeit,
            'NPV': npv,
            'LCCA': lcca,
            'Neuer Wärmebedarf': neuer_waermebedarf,
            'Kosteneinsparung': analyse.berechne_kosteneinsparungen(),
            'ROI': roi
        }       

    energieeinsparung = [ref_building.yearly_heat_demand - ergebnisse[komponente]['Neuer Wärmebedarf'] for komponente in varianten]
    gesamtenergiebedarf = [ref_building.yearly_heat_demand] + [ergebnisse[komponente]['Neuer Wärmebedarf'] for komponente in varianten]


    results = {
        "Investitionskosten in €": {k: v['Investitionskosten'] for k, v in ergebnisse.items()},
        "Gesamtenergiebedarf in kWh/a": dict(zip(['Referenz'] + varianten, gesamtenergiebedarf)),
        "Energieeinsparung in kWh/a": dict(zip(varianten, energieeinsparung)),
        "Kosteneinsparung in €/a": {k: v['Kosteneinsparung'] for k, v in ergebnisse.items()},
        "Kaltmieten in €/m²": {"Referenz": cold_rent, **kaltmieten_pro_m2},
        "Warmmieten in €/m²": {"Referenz": ref_warmmiete_pro_m2, **warmmieten_pro_m2},
        "Amortisationszeit in a": {k: v['Amortisationszeit'] for k, v in ergebnisse.items()},
        "NPV in €": {k: v['NPV'] for k, v in ergebnisse.items()},
        "LCCA in €": {k: v['LCCA'] for k, v in ergebnisse.items()},
        "ROI": {k: v['ROI'] for k, v in ergebnisse.items()}
    }

    return results
