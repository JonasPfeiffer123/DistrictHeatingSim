import matplotlib.pyplot as plt
import pandapipes.plotting as pp_plot
import random
import numpy as np
import pandas as pd
import geopandas as gpd
from matplotlib.figure import Figure

from net_simulation_pandapipes import net_simulation
from net_simulation_pandapipes import net_simulation_calculation
from heat_requirement import heat_requirement_VDI4655
from heat_requirement import heat_requirement_BDEW
from net_simulation_pandapipes.net_generation_test import initialize_test_net
from heat_generators.heat_generator_classes import *
from net_test import config_plot

def import_TRY(dateiname):
    # Import TRY
    # Spaltenbreiten definieren
    col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]
    # Spaltennamen definieren
    col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]

    # Die Datei lesen
    data = pd.read_fwf(dateiname, widths=col_widths, names=col_names,
                       skiprows=34)

    # Speichern der Spalten als Numpy-Arrays
    temperature = data['t'].values
    windspeed = data['WG'].values
    direktstrahlung = data['B'].values
    diffusstrahlung = data['D'].values
    globalstrahlung = direktstrahlung + diffusstrahlung

    return temperature, windspeed, direktstrahlung, globalstrahlung

#Berechnung_Erzeugermix
def initialize_net_profile_calculation(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type="MFH", calc_method="VDI4655"):
    ### define the heat requirement ###
    try:
        JEB_Wärme_ges_kWh = gdf_HAST["Wärmebedarf"].values.astype(float)
    except KeyError:
        print("Herauslesen des Wärmebedarfs aus geojson nicht möglich.")
        return None

    JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh = JEB_Wärme_ges_kWh * 0.2, JEB_Wärme_ges_kWh * 0.8

    waerme_ges_W = []
    max_waerme_ges_W = []
    yearly_time_steps = None

    # Zuordnung von Gebäudetypen zu Berechnungsmethoden
    building_type_to_method = {
        "EFH": "VDI4655",
        "MFH": "VDI4655",
        "HEF": "BDEW",
        "HMF": "BDEW",
        "GKO": "BDEW",
        "GHA": "BDEW",
        "GMK": "BDEW",
        "GBD": "BDEW",
        "GBH": "BDEW",
        "GWA": "BDEW",
        "GGA": "BDEW",
        "GBA": "BDEW",
        "GGB": "BDEW",
        "GPD": "BDEW",
        "GMF": "BDEW",
        "GHD": "BDEW",
        # ... Fügen Sie hier weitere Zuordnungen hinzu, falls nötig
    }

    for idx, JWB in enumerate(JEB_Wärme_ges_kWh):
        if calc_method == "Datensatz":
            try:
                current_building_type = gdf_HAST.at[idx, "Gebäudetyp"]
                current_calc_method = building_type_to_method.get(current_building_type, "StandardMethode")
            except KeyError:
                print("Gebäudetyp-Spalte nicht in gdf_HAST gefunden.")
                current_calc_method = "StandardMethode"
        else:
            current_building_type = building_type
            current_calc_method = calc_method

        # Wärmebedarfsberechnung basierend auf dem Gebäudetyp und der Berechnungsmethode
        if current_calc_method == "VDI4655":
            hw, tww = JEB_Heizwärme_kWh[idx], JEB_Trinkwarmwasser_kWh[idx]
            yearly_time_steps, _, _, _, waerme_ges_kW = heat_requirement_VDI4655.calculate(hw, tww, building_type=current_building_type)
        elif current_calc_method == "BDEW":
            yearly_time_steps, waerme_ges_kW  = heat_requirement_BDEW.calculate(JWB, current_building_type, subtyp="03")

        waerme_ges_W.append(waerme_ges_kW * 1000)
        max_waerme_ges_W.append(np.max(waerme_ges_kW * 1000))

    waerme_ges_W = np.array(waerme_ges_W)
    max_waerme_ges_W = np.array(max_waerme_ges_W)

    ### generates the pandapipes net and initializes it ###
    net = net_simulation.initialize_net(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, max_waerme_ges_W)
    
    return net, yearly_time_steps, waerme_ges_W

def thermohydraulic_time_series_net_calculation(net, yearly_time_steps, waerme_ges_W, calc1, calc2, t_rl_soll=60):
    ### time series calculation ###

    time_steps = yearly_time_steps[calc1:calc2]
    net, net_results = net_simulation.time_series_net(net, t_rl_soll, waerme_ges_W, calc1, calc2)

    return time_steps, net, net_results

def calculate_results(net, net_results):
    ### Plotten Ergebnisse Pumpe / Einspeisung ###
    mass_flow_circ_pump = net_results["res_circ_pump_pressure.mdot_flow_kg_per_s"][:, 0]
    deltap_circ_pump =  net_results["res_circ_pump_pressure.deltap_bar"][:, 0]


    rj_circ_pump = net.circ_pump_pressure["return_junction"][0]
    fj_circ_pump = net.circ_pump_pressure["flow_junction"][0]

    return_temp_circ_pump = net_results["res_junction.t_k"][:, rj_circ_pump] - 273.15
    flow_temp_circ_pump = net_results["res_junction.t_k"][:, fj_circ_pump] - 273.15

    return_pressure_circ_pump = net_results["res_junction.p_bar"][:, rj_circ_pump]
    flows_pressure_circ_pump = net_results["res_junction.p_bar"][:, fj_circ_pump]

    pressure_junctions = net_results["res_junction.p_bar"]

    cp_kJ_kgK = 4.2 # kJ/kgK

    qext_kW = mass_flow_circ_pump * cp_kJ_kgK * (flow_temp_circ_pump -return_temp_circ_pump)

    return mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions

def plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, deltap_circ_pump, junction_pressure):
    # Erstellen Sie eine Figur und ein erstes Achsenobjekt
    fig, ax1 = plt.subplots()

    # Plot für Wärmeleistung auf der ersten Y-Achse
    ax1.plot(time_steps, qext_kW, 'b-', label="Gesamtlast")
    ax1.set_xlabel("Zeit in 15 min Schritten")
    ax1.set_ylabel("Wärmebedarf in kW / 15 min", color='b')
    ax1.tick_params('y', colors='b')
    ax1.legend(loc='upper right')

    # Zweite Y-Achse für die Temperatur
    ax2 = ax1.twinx()
    ax2.plot(time_steps, return_temp_circ_pump, 'm-o', label="circ pump return temperature")
    ax2.plot(time_steps, flow_temp_circ_pump, 'c-o', label="circ pump flow temperature")
    ax2.set_ylabel("temperature [°C]", color='m')
    ax2.tick_params('y', colors='m')
    ax2.legend(loc='upper right')
    ax2.set_ylim(0,100)

    # Zweite Y-Achse für die Temperatur
    ax3 = ax1.twinx()
    ax3.plot(time_steps, return_pressure_circ_pump, label="circ pump return pressure")
    ax3.plot(time_steps, flows_pressure_circ_pump, label="circ pump flow pressure")
    ax3.plot(time_steps, deltap_circ_pump, label="circ pump delta p")
    ax3.plot(time_steps, junction_pressure)
    ax3.set_ylabel("pressure [bar]")
    ax3.tick_params('y')
    ax3.legend(loc='upper left')

    # Titel und Raster hinzufügen
    plt.title("Lastgang Wärmenetz")
    plt.grid(True)

    # Zeigen Sie das kombinierte Diagramm an
    plt.show()

def save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, filename):
    # Umwandeln von time_steps in ein allgemeineres datetime64[ns]-Format
    time_steps_ns = time_steps.astype('datetime64[ns]')
    
    # Konvertieren der Arrays in ein Pandas DataFrame
    df = pd.DataFrame({'Zeitpunkt': time_steps_ns, 
                       'Heizlast_Netz_kW': qext_kW, 
                       'Vorlauftemperatur_Netz_°C': flow_temp_circ_pump, 
                       'Rücklauftemperatur_Netz_°C': return_temp_circ_pump})

    # Speichern des DataFrames als CSV
    df.to_csv(filename, sep=';', index=False)

def import_results_csv(filename):
    data = pd.read_csv(filename, sep=';', parse_dates=['Zeitpunkt'])
    time_steps = data["Zeitpunkt"].values.astype('datetime64[15m]')
    qext_kW = data["Heizlast_Netz_kW"].values.astype('float64')
    flow_temp_circ_pump = data['Vorlauftemperatur_Netz_°C'].values.astype('float64')
    return_temp_circ_pump = data['Rücklauftemperatur_Netz_°C'].values.astype('float64')
    return time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump

def generate_net(calc1=0, calc2=35040, filename='results_time_series_net1.csv'):
    gdf_vl = gpd.read_file('net_generation_QGIS/Beispiel Zittau/Vorlauf.geojson')
    gdf_rl = gpd.read_file('net_generation_QGIS/Beispiel Zittau/Rücklauf.geojson')
    gdf_HAST = gpd.read_file('net_generation_QGIS/Beispiel Zittau/HAST.geojson')
    gdf_WEA = gpd.read_file('net_generation_QGIS/Beispiel Zittau/Erzeugeranlagen.geojson')

    net, yearly_time_steps, waerme_ges_W = initialize_net_profile_calculation(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type="EFH", calc_method="VDI4655")
    time_steps, net, net_results = thermohydraulic_time_series_net_calculation(net, yearly_time_steps, waerme_ges_W, calc1, calc2)

    mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
        return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

    ###!!!!!this will overwrite the current csv file!!!!!#
    save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, filename)

    junction_pressure = net_results["res_junction.p_bar"]
    plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, deltap_circ_pump, junction_pressure)
    
    dp_min, idx_dp_min = net_simulation_calculation.calculate_worst_point(net)
    print(f"Der Schlechtpunkt des Netzes liegt am Wärmeübertrager {idx_dp_min}. Der Differenzdruck beträgt {dp_min:.3f} bar.")

    #config_plot(net)

def auslegung_erzeuger(calc1=0, calc2=35040, filename='results_time_series_net.csv', optimize=False, load_scale_factor=1, Gaspreis=70, Strompreis=150, Holzpreis=50, BEW="Nein"):
    time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump = import_results_csv(filename)
    qext_kW = qext_kW * load_scale_factor #MWh
    #plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)

    initial_data = time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump

    TRY = import_TRY('heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat')
    COP_data = np.genfromtxt('heat_generators/Kennlinien WP.csv', delimiter=';')

    solar_thermal = SolarThermal(name="Solarthermie", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor")
    geothermal = Geothermal(name="Geothermie", Fläche=100, Bohrtiefe=100, Temperatur_Geothermie=10)
    waste_heat = WasteHeatPump(name="Abwärme", Kühlleistung_Abwärme=20, Temperatur_Abwärme=30)
    biomass_boiler1 = BiomassBoiler(name="Biomassekessel", P_BMK=30)
    biomass_boiler2 = BiomassBoiler(name="Biomassekessel", P_BMK=60)
    wood_chp = CHP(name="BHKW", th_Leistung_BHKW=40)
    chp2 = CHP(name="Holzgas-BHKW", th_Leistung_BHKW=40)
    gas_boiler = GasBoiler(name="Gaskessel")

    techs = [solar_thermal, wood_chp, biomass_boiler1, gas_boiler]

    if optimize == True:
        techs = optimize_mix(techs, initial_data, calc1, calc2, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW)

    WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, Wärmemengen, WGK, Anteile, specific_emissions  = \
        Berechnung_Erzeugermix(techs, initial_data, calc1, calc2, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW)
    
    print(f"Jahreswärmebedarf:", f"{Jahreswärmebedarf:.2f} MWh")
    print(f"Wärmegestehungskosten Gesamt:", f"{WGK_Gesamt:.2f} €/MWh")

    for tech, wärmemenge, anteil, wgk in zip(techs, Wärmemengen, Anteile, WGK):
        print(f"Wärmemenge {tech.name}:", f"{wärmemenge:.2f} MWh")
        print(f"Wärmegestehungskosten {tech.name}:", f"{wgk:.2f} €/MWh")
        print(f"Anteil an Wärmeversorgung {tech.name}:", f"{anteil:.2f}")

    def Jahresdauerlinie(t, Last_L, data_L, data_labels_L):
        fig, ax = plt.subplots()

        #ax.plot(t, Last_L, color="black", linewidth=0.1, label="Last in kW")
        ax.stackplot(t, data_L, labels=data_labels_L)
        ax.set_title("Jahresdauerlinie")
        ax.set_xlabel("Jahresstunden")
        ax.set_ylabel("thermische Leistung in kW")
        ax.legend(loc='upper center')

        plt.title("Jahresdauerlinie Wärmenetz")
        plt.grid(True)
        
        plt.show()

    def Kreisdiagramm(data_labels_L, Anteile):
        pie, ax1 = plt.subplots()
        ax1.pie(Anteile, labels=data_labels_L, autopct='%1.1f%%', startangle=90)
        ax1.set_title("Anteile Wärmeerzeugung")
        ax1.legend(loc='center right')
        ax1.axis("equal")
        ax1.plot

        plt.title("Zusammensetzung Wärmeerzeugung")
        plt.grid(True)
        
        plt.show()

    Jahresdauerlinie(time_steps, Last_L, data_L, data_labels_L)

    Kreisdiagramm(data_labels_L, Anteile)

#generate_net(calc1=0, calc2=87, filename='results_time_series_net1.csv') 
#auslegung_erzeuger(calc1=0, calc2= 8760, filename="heat_requirement/Summenlastgang_Scenocalc_skaliert_1MWh.csv", \
#                   optimize=True, load_scale_factor=3000000, Gaspreis=70, Strompreis=150, Holzpreis=50, BEW="Ja")
