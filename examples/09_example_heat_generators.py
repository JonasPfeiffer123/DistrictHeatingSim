"""
Filename: 09_example_heat_generators.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Script for testing the heat generator functions.

"""

from districtheatingsim.heat_generators import solar_thermal
from districtheatingsim.heat_generators import gas_boiler
from districtheatingsim.heat_generators import biomass_boiler
from districtheatingsim.heat_generators import chp
from districtheatingsim.heat_generators import heat_pumps
from districtheatingsim.heat_generators import power_to_heat
from districtheatingsim.utilities.test_reference_year import import_TRY

import numpy as np

import matplotlib.pyplot as plt

def test_gas_boiler(Last_L, duration, economic_parameters, gBoiler=gas_boiler.GasBoiler(name="Gas_Boiler_1", spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1)):
    gBoiler.calculate_operation(Last_L, duration)
    gBoiler.calculate_heat_generation_cost(economic_parameters)
    gBoiler.calculate_environmental_impact()

    results = {
            'Wärmemenge': gBoiler.Wärmemenge_MWh,
            'Wärmeleistung_L': gBoiler.Wärmeleistung_kW,
            'Brennstoffbedarf': gBoiler.Brennstoffbedarf_MWh,
            'WGK': gBoiler.WGK_GK,
            'spec_co2_total': gBoiler.spec_co2_total,
            'primärenergie': gBoiler.primärenergie,
            "color": "saddlebrown"
        }
    
    print(f"Wärmemenge Gaskessel: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Gaskessel: {results['Wärmeleistung_L']} kW")
    print(f"Brennstoffbedarf Gaskessel: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Gaskessel: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Gaskessel: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Gaskessel: {results['primärenergie']:.2f} MWh")

def test_power_to_heat(Last_L, duration, economic_parameters, PTH=power_to_heat.PowerToHeat(name="PowerToHeat", spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1)):
    PTH.simulate_operation(Last_L, duration)
    PTH.calculate_heat_generation_cost(economic_parameters)
    PTH.calculate_environmental_impact()

    results = {
            'Wärmemenge': PTH.Wärmemenge_MWh,
            'Wärmeleistung_L': PTH.Wärmeleistung_kW,
            'Brennstoffbedarf': PTH.Strommenge_MWh,
            'WGK': PTH.WGK,
            'spec_co2_total': PTH.spec_co2_total,
            'primärenergie': PTH.primärenergie,
            "color": "saddlebrown"
        }

    print(f"Wärmemenge Power-to-Heat: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Power-to-Heat: {results['Wärmeleistung_L']} kW")
    print(f"Strombedarf Power-to-Heat: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Power-to-Heat: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Power-to-Heat: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Power-to-Heat: {results['primärenergie']:.2f} MWh")

def test_biomass_boiler(Last_L, duration, economic_parameters, bBoiler=biomass_boiler.BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400, 
                                           Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=False, Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                                           min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                           opt_Speicher_max=100)):

    bBoiler.simulate_operation(Last_L, duration)
    Wärmemenge = bBoiler.Wärmemenge_MWh
    Brennstoffbedarf = bBoiler.Brennstoffbedarf_MWh
    Wärmeleistung_kW = bBoiler.Wärmeleistung_kW
    Anzahl_Starts = bBoiler.Anzahl_Starts
    Betriebsstunden = bBoiler.Betriebsstunden
    Betriebsstunden_pro_Start = bBoiler.Betriebsstunden_pro_Start

    bBoiler.calculate_heat_generation_costs(Wärmemenge, Brennstoffbedarf, economic_parameters)
    bBoiler.calculate_environmental_impact(Brennstoffbedarf, Wärmemenge)

    results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_kW,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': bBoiler.WGK,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': bBoiler.spec_co2_total,
            'primärenergie': bBoiler.primärenergie,
            'color': "green"
        }  
    
    print(f"Wärmemenge Biomassekessel: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Biomassekessel: {results['Wärmeleistung_L']} kW")
    print(f"Brennstoffbedarf Biomassekessel: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Biomassekessel: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Biomassekessel: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Biomassekessel: {results['primärenergie']:.2f} MWh")
    print(f"Anzahl Starts Biomassekessel: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden Biomassekessel: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start Biomassekessel: {results['Betriebsstunden_pro_Start']:.2f} h")

def test_biomass_boiler_storage(Last_L, duration, economic_parameters, bBoiler=biomass_boiler.BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400, 
                                           Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=True, Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                                           min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                           opt_Speicher_max=100)):

    bBoiler.simulate_storage(Last_L, duration)
    Wärmemenge = bBoiler.Wärmemenge_Biomassekessel_Speicher
    Brennstoffbedarf = bBoiler.Brennstoffbedarf_BMK_Speicher
    Wärmeleistung_kW = bBoiler.Wärmeleistung_kW
    Anzahl_Starts = bBoiler.Anzahl_Starts_Speicher
    Betriebsstunden = bBoiler.Betriebsstunden_gesamt_Speicher
    Betriebsstunden_pro_Start = bBoiler.Betriebsstunden_pro_Start_Speicher

    bBoiler.calculate_heat_generation_costs(Wärmemenge, Brennstoffbedarf, economic_parameters)
    bBoiler.calculate_environmental_impact(Brennstoffbedarf, Wärmemenge)

    results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_kW,
            'Wärmeleistung_Speicher_L': bBoiler.Wärmeleistung_Speicher_kW,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': bBoiler.WGK,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': bBoiler.spec_co2_total,
            'primärenergie': bBoiler.primärenergie,
            'color': "green"
        }
    
    print(f"Wärmemenge Biomassekessel mit Speicher: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Biomassekessel mit Speicher: {results['Wärmeleistung_L']} kW")
    print(f"Wärmeleistung Speicher Biomassekessel: {results['Wärmeleistung_Speicher_L']} kW")
    print(f"Brennstoffbedarf Biomassekessel mit Speicher: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Biomassekessel mit Speicher: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Biomassekessel mit Speicher: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Biomassekessel mit Speicher: {results['primärenergie']:.2f} MWh")
    print(f"Anzahl Starts Biomassekessel mit Speicher: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden Biomassekessel mit Speicher: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start Biomassekessel mit Speicher: {results['Betriebsstunden_pro_Start']:.2f} h")

def test_chp(Last_L, duration, economic_parameters, chp=chp.CHP(name="BHKW", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                                                                KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, 
                                                                initial_fill=0.0, min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, 
                                                                opt_BHKW_Speicher_min=0, opt_BHKW_Speicher_max=100)):

    chp.simulate_operation(Last_L, duration)
    Wärmemenge = chp.Wärmemenge_MWh
    Strommenge = chp.Strommenge_MWh
    Brennstoffbedarf = chp.Brennstoffbedarf_MWh
    Wärmeleistung_kW = chp.Wärmeleistung_kW
    el_Leistung_BHKW = chp.el_Leistung_kW
    Anzahl_Starts = chp.Anzahl_Starts
    Betriebsstunden = chp.Betriebsstunden
    Betriebsstunden_pro_Start = chp.Betriebsstunden_pro_Start

    chp.calculate_heat_generation_costs(chp.Wärmemenge_MWh, chp.Strommenge_MWh, chp.Brennstoffbedarf_MWh, economic_parameters)
    chp.calculate_environmental_impact(Wärmemenge, Strommenge, Brennstoffbedarf)

    results = {
        'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_kW,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': chp.WGK,
            'Strommenge': Strommenge,
            'el_Leistung_L': el_Leistung_BHKW,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': chp.spec_co2_total,
            'primärenergie': chp.primärenergie,
            'color': "yellow"
        }

    print(f"Wärmemenge BHKW: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung BHKW: {results['Wärmeleistung_L']} kW")
    print(f"Brennstoffbedarf BHKW: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten BHKW: {results['WGK']:.2f} €/MWh")
    print(f"Strommenge BHKW: {results['Strommenge']:.2f} MWh")
    print(f"Stromleistung BHKW: {results['el_Leistung_L']} kW")
    print(f"Anzahl Starts BHKW: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden BHKW: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start BHKW: {results['Betriebsstunden_pro_Start']:.2f} h")
    print(f"spezifische CO2-Emissionen BHKW: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf BHKW: {results['primärenergie']:.2f} MWh")

def test_chp_storage(Last_L, duration, economic_parameters, chp=chp.CHP(name="BHKW", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                                                                        KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=True, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                                                                        min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, 
                                                                        opt_BHKW_Speicher_min=0, opt_BHKW_Speicher_max=100)):

    chp.simulate_storage(Last_L, duration)
    Wärmemenge = chp.Wärmemenge_BHKW_Speicher
    Strommenge = chp.Strommenge_BHKW_Speicher
    Brennstoffbedarf = chp.Brennstoffbedarf_BHKW_Speicher
    Wärmeleistung_kW = chp.Wärmeleistung_kW
    el_Leistung_BHKW = chp.el_Leistung_kW
    Anzahl_Starts = chp.Anzahl_Starts_Speicher
    Betriebsstunden = chp.Betriebsstunden_gesamt_Speicher
    Betriebsstunden_pro_Start = chp.Betriebsstunden_pro_Start_Speicher

    chp.calculate_heat_generation_costs(chp.Wärmemenge_BHKW_Speicher, chp.Strommenge_BHKW_Speicher, chp.Brennstoffbedarf_BHKW_Speicher, economic_parameters)
    chp.calculate_environmental_impact(Wärmemenge, Strommenge, Brennstoffbedarf)

    results = {
        'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_kW,
            'Wärmeleistung_Speicher_L': chp.Wärmeleistung_Speicher_kW,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': chp.WGK,
            'Strommenge': Strommenge,
            'el_Leistung_L': el_Leistung_BHKW,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': chp.spec_co2_total,
            'primärenergie': chp.primärenergie,
            'color': "yellow"
        }
    
    print(f"Wärmemenge BHKW mit Speicher: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung BHKW mit Speicher: {results['Wärmeleistung_L']} kW")
    print(f"Wärmeleistung Speicher BHKW: {results['Wärmeleistung_Speicher_L']} kW")
    print(f"Brennstoffbedarf BHKW mit Speicher: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten BHKW mit Speicher: {results['WGK']:.2f} €/MWh")
    print(f"Strommenge BHKW mit Speicher: {results['Strommenge']:.2f} MWh")
    print(f"Stromleistung BHKW mit Speicher: {results['el_Leistung_L']} kW")
    print(f"Anzahl Starts BHKW mit Speicher: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden BHKW mit Speicher: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start BHKW mit Speicher: {results['Betriebsstunden_pro_Start']:.2f} h")
    print(f"spezifische CO2-Emissionen BHKW mit Speicher: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf BHKW mit Speicher: {results['primärenergie']:.2f} MWh")

def test_waste_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, wasteHeatPump=heat_pumps.WasteHeatPump(name="Abwärme", Kühlleistung_Abwärme=50, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)):

    wasteHeatPump.calculate_operation(Last_L, VLT_L, COP_data, duration)
    WGK = wasteHeatPump.calculate_heat_generation_costs(wasteHeatPump.max_Wärmeleistung, wasteHeatPump.Wärmemenge_MWh, wasteHeatPump.Strommenge_MWh, wasteHeatPump.spez_Investitionskosten_Abwärme, economic_parameters)
    wasteHeatPump.calculate_environmental_impact()

    results = {
            'Wärmemenge': wasteHeatPump.Wärmemenge_MWh,
            'Wärmeleistung_L': wasteHeatPump.Wärmeleistung_kW,
            'Strombedarf': wasteHeatPump.Strommenge_MWh,
            'el_Leistung_L': wasteHeatPump.el_Leistung_kW,
            'WGK': WGK,
            'spec_co2_total': wasteHeatPump.spec_co2_total,
            'primärenergie': wasteHeatPump.primärenergie,
            'color': "grey"
        }
    
    print(f"Wärmemenge Abwärme-WP: {results['Wärmemenge']:.2f} MWh")
    print(f"Strombedarf Abwärme-WP: {results['Strombedarf']:.2f} MWh")
    print(f"Wärmeleistung Abwärme-WP: {results['Wärmeleistung_L']} kW")
    print(f"elektrische Leistung Abwärme-WP: {results['el_Leistung_L']} kW")
    print(f"Wärmegestehungskosten Abwärme-WP: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Abwärme-WP: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Abwärme-WP: {results['primärenergie']:.2f} MWh")

def test_river_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, riverHeatPump=heat_pumps.RiverHeatPump(name="Flusswasser", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=10, dT=0, spez_Investitionskosten_Flusswasser=1000, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)):   
    
    riverHeatPump.calculate_operation(Last_L, VLT_L, COP_data, duration)
    WGK = riverHeatPump.calculate_heat_generation_costs(riverHeatPump.Wärmeleistung_FW_WP, riverHeatPump.Wärmemenge_MWh, riverHeatPump.Strommenge_MWh, riverHeatPump.spez_Investitionskosten_Flusswasser, economic_parameters)
    riverHeatPump.calculate_environmental_impact()

    results = {
            'Wärmemenge': riverHeatPump.Wärmemenge_MWh,
            'Wärmeleistung_L': riverHeatPump.Wärmeleistung_kW,
            'Strombedarf': riverHeatPump.Strommenge_MWh,
            'el_Leistung_L': riverHeatPump.el_Leistung_kW,
            'WGK': WGK,
            'spec_co2_total': riverHeatPump.spec_co2_total,
            'primärenergie': riverHeatPump.primärenergie,
            'color': "grey"
        }
    
    print(f"Wärmemenge Fluss-WP: {results['Wärmemenge']:.2f} MWh")
    print(f"Strombedarf Fluss-WP: {results['Strombedarf']:.2f} MWh")
    print(f"Wärmeleistung Fluss-WP: {results['Wärmeleistung_L']} kW")
    print(f"elektrische Leistung Fluss-WP: {results['el_Leistung_L']} kW")
    print(f"Wärmegestehungskosten Fluss-WP: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Fluss-WP: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Fluss-WP: {results['primärenergie']:.2f} MWh")

def test_geothermal_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, geothermalHeatPump=heat_pumps.Geothermal(name="Geothermie", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, spez_Bohrkosten=100, spez_Entzugsleistung=50, Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)):
    
    geothermalHeatPump.calculate_operation(Last_L, VLT_L, COP_data, duration)
    geothermalHeatPump.spez_Investitionskosten_Erdsonden = geothermalHeatPump.Investitionskosten_Sonden / geothermalHeatPump.max_Wärmeleistung
    WGK = geothermalHeatPump.calculate_heat_generation_costs(geothermalHeatPump.max_Wärmeleistung, geothermalHeatPump.Wärmemenge_MWh, geothermalHeatPump.Strommenge_MWh, geothermalHeatPump.spez_Investitionskosten_Erdsonden, economic_parameters)
    geothermalHeatPump.calculate_environmental_impact()

    results = {
        'Wärmemenge': geothermalHeatPump.Wärmemenge_MWh,
        'Wärmeleistung_L': geothermalHeatPump.Wärmeleistung_kW,
        'Strombedarf': geothermalHeatPump.Strommenge_MWh,
        'el_Leistung_L': geothermalHeatPump.el_Leistung_kW,
        'WGK': WGK,
        'spec_co2_total': geothermalHeatPump.spec_co2_total,
        'primärenergie': geothermalHeatPump.primärenergie,
        'color': "darkorange"
    }

    print(f"Wärmemenge Geothermie-WP: {results['Wärmemenge']:.2f} MWh")
    print(f"Strombedarf Geothermie-WP: {results['Strombedarf']:.2f} MWh")
    print(f"Wärmeleistung Geothermie-WP: {results['Wärmeleistung_L']} kW")
    print(f"elektrische Leistung Geothermie-WP: {results['el_Leistung_L']} kW")
    print(f"Wärmegestehungskosten Geothermie-WP: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Geothermie-WP: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Geothermie-WP: {results['primärenergie']:.2f} MWh")
    
def test_aqva_heat(Last_L, duration, economic_parameters, VLT_L, COP_data, aqva_heat=heat_pumps.AqvaHeat(name="AqvaHeat", nominal_power=100, temperature_difference=0)):
    # not implemented yet

    Wärmemenge, Strombedarf, Wärmeleistung_L, el_Leistung_L = aqva_heat.calculate(Last_L, VLT_L, COP_data, duration)
    aqva_heat.Wärmeleistung = 1
    aqva_heat.spez_Investitionskosten = 1

    WGK = aqva_heat.calculate_heat_generation_costs(aqva_heat.Wärmeleistung, Wärmemenge, Strombedarf, aqva_heat.spez_Investitionskosten, economic_parameters)

def test_solar_thermal(Last_L, duration, economic_parameters, VLT_L, RLT_L, COP_data, TRY_data, solarThermal=solar_thermal.SolarThermal(name="STA", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", 
                                                                                                            kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, Tsmax=90, 
                                                                                                            Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, 
                                                                                                            Collector_tilt_angle=36, Tm_rl=60, Qsa=0, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5, 
                                                                                                            opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000)):

    # Angaben zum zu betrchtende Zeitraum
    # Erstelle ein Array mit stündlichen Zeitwerten für ein Jahr
    start_date = np.datetime64('2019-01-01')
    end_date = np.datetime64('2020-01-01', 'D')  # Enddatum ist exklusiv, daher 'D' für Tage

    # Erstelle das Array mit stündlichen Zeitwerten für ein Jahr
    time_steps = np.arange(start_date, end_date, dtype='datetime64[h]')

    # Die Berechnung der Solarthermie erfolgt niht in der Klasse sondern in einer externen Funktion
    solarThermal.Wärmemenge_MWh, solarThermal.Wärmeleistung_kW, solarThermal.Speicherinhalt, solarThermal.Speicherfüllstand = solar_thermal.Berechnung_STA(solarThermal.bruttofläche_STA, solarThermal.vs, solarThermal.Typ, Last_L, VLT_L, RLT_L, 
                                                                                                        TRY_data, time_steps, duration, solarThermal.Tsmax, solarThermal.Longitude, solarThermal.STD_Longitude, 
                                                                                                        solarThermal.Latitude, solarThermal.East_West_collector_azimuth_angle, solarThermal.Collector_tilt_angle, solarThermal.Tm_rl, 
                                                                                                        solarThermal.Qsa, solarThermal.Vorwärmung_K, solarThermal.DT_WT_Solar_K, solarThermal.DT_WT_Netz_K)


    solarThermal.WGK = solarThermal.calculate_heat_generation_costs(economic_parameters)
    solarThermal.calculate_environmental_impact()

    results = { 
        'Wärmemenge': solarThermal.Wärmemenge_MWh,
        'Wärmeleistung_L': solarThermal.Wärmeleistung_kW,
        'WGK': solarThermal.WGK,
        'spec_co2_total': solarThermal.spec_co2_total,
        'primärenergie': solarThermal.primärenergie_Solarthermie,
        'Speicherladung_L': solarThermal.Speicherinhalt,
        'Speicherfüllstand_L': solarThermal.Speicherfüllstand,
        'color': "red"
    }

    print(f"Wärmemenge Solarthermie: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Solarthermie: {results['Wärmeleistung_L']} kW")
    print(f"Wärmegestehungskosten Solarthermie: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Solarthermie: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Solarthermie: {results['primärenergie']:.2f} MWh")
    print(f"Speicherladung Solarthermie: {results['Speicherladung_L']} kW")
    print(f"Speicherfüllstand Solarthermie: {results['Speicherfüllstand_L']} MWh")

if __name__ == "__main__":
    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760).astype(float)

    # Dauer Zeitschritte 1 h
    duration = 1

    # Wirtschaftliche Randbedingungen
    electricity_price = 150 # €/MWh
    gas_price = 70 # €/MWh
    wood_price = 60 # €/MWh

    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    hourly_rate = 45

    # Arrays für Vor- und Rücklauftemperatur
    VLT_L, RLT_L = np.full(8760, 80), np.full(8760, 55)

    # Laden des COP-Kennfeldes
    COP_data = np.genfromtxt("examples/data/COP/Kennlinien WP.csv", delimiter=';')

    # Dateiname Testreferenzjahr für Wetterdaten, Dateiname muss ggf. angepasst werden
    TRY_data = import_TRY("examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat") 

    economic_parameters = {
                "gas_price": gas_price,
                "electricity_price": electricity_price,
                "wood_price": wood_price,
                "capital_interest_rate": q,
                "inflation_rate": r,
                "time_period": T,
                "hourly_rate": hourly_rate,
                "subsidy_eligibility": BEW
            }

    gBoiler = gas_boiler.GasBoiler(name="Gas_Boiler_1", spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1)
    test_gas_boiler(Last_L, duration, economic_parameters, gBoiler)

    PTH = power_to_heat.PowerToHeat(name="PowerToHeat_1", spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1)    
    test_power_to_heat(Last_L, duration, economic_parameters, PTH)

    bBoiler = biomass_boiler.BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                           spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=False, 
                                           Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                           spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                           opt_Speicher_max=100)
    test_biomass_boiler(Last_L, duration, economic_parameters, bBoiler)

    bBoiler_storage = biomass_boiler.BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                                   spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=True, 
                                                   Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                                   spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                                   opt_Speicher_max=100)
    test_biomass_boiler_storage(Last_L, duration, economic_parameters, bBoiler_storage)

    CHP = chp.CHP(name="BHKW", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                  KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                  min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
                  opt_BHKW_Speicher_max=100)    
    test_chp(Last_L, duration, economic_parameters, CHP)

    CHP_storage = chp.CHP(name="BHKW", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                          KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=True, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                          min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
                          opt_BHKW_Speicher_max=100)
    test_chp_storage(Last_L, duration, economic_parameters, CHP_storage)

    riverHeatPump = heat_pumps.WasteHeatPump(name="Abwärme", Kühlleistung_Abwärme=50, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, 
                                             spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)
    test_waste_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, riverHeatPump)

    riverHeatPump = heat_pumps.RiverHeatPump(name="Flusswasser", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=10, dT=0, spez_Investitionskosten_Flusswasser=1000, 
                                             spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)
    test_river_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, riverHeatPump) 

    geothermal_heat_pump = heat_pumps.Geothermal(name="Geothermie", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, spez_Bohrkosten=100, spez_Entzugsleistung=50,
                                                Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)
    test_geothermal_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, geothermal_heat_pump)
    
    # not implemented yet
    #aqva_heat = heat_pumps.AqvaHeat(name="AqvaHeat", nominal_power=100, temperature_difference=0)
    #test_aqva_heat(Last_L, duration, Strompreis, q, r, T, BEW, stundensatz, VLT_L, COP_data, aqva_heat)

    solarThermal = solar_thermal.SolarThermal(name="STA", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, 
                                            Tsmax=90, Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Tm_rl=60, 
                                            Qsa=0, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5, opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000)
    test_solar_thermal(Last_L, duration, economic_parameters, VLT_L, RLT_L, COP_data, TRY_data, solarThermal)
