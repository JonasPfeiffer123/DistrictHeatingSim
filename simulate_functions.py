import matplotlib.pyplot as plt
import pandapipes.plotting as pp_plot
import random
import numpy as np
import geopandas as gpd

from net_simulation_pandapipes import net_simulation
from net_simulation_pandapipes import net_simulation_calculation
from heat_requirement import heat_requirement_VDI4655
from net_simulation_pandapipes.net_generation_test import initialize_test_net
from heat_generators.heating_system import Berechnung_Erzeugermix


def thermohydraulic_time_series_net_calculation():
    gdf_vl = gpd.read_file('net_generation_QGIS/geoJSON_Vorlauf.geojson')
    gdf_rl = gpd.read_file('net_generation_QGIS/geoJSON_Rücklauf.geojson')
    gdf_HAST = gpd.read_file('net_generation_QGIS/geoJSON_HAST.geojson')
    gdf_WEA = gpd.read_file('net_generation_QGIS/geoJSON_Erzeugeranlagen.geojson')

    ### generates the pandapipes net and initializes it ###
    net = net_simulation.initialize_net(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA)

    ### Ausgabe der Netzstruktur ###
    #pp_plot.simple_plot(net, junction_size=0.2, heat_exchanger_size=0.2, pump_size=0.2, 
    #                    pump_color='green', pipe_color='black', heat_exchanger_color='blue')

    ### define the heat requirement ###
    n = len(net.heat_exchanger)
    min_value = 20000  # kWhre
    max_value = 70000  # kWh
    JEB_Wärme_ges_kWh = np.array([random.randint(min_value, max_value) for _ in range(n)])
    JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh = JEB_Wärme_ges_kWh*0.2, JEB_Wärme_ges_kWh*0.8

    waerme_ges_W = []

    for hw, tww in zip(JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh):
        time_15min, _, _, _, waerme_ges_kW = heat_requirement_VDI4655.calculate(hw, tww)
        waerme_ges_W.append(waerme_ges_kW * 1000)

    waerme_ges_W = np.array(waerme_ges_W)

    ### time series calculation ###
    t_rl_soll = 60

    calc1 = 18000
    calc2 = 18500
    time_steps = time_15min[calc1:calc2]
    net, net_results = net_simulation.time_series_net(net, t_rl_soll, waerme_ges_W, calc1, calc2)

    # dp_min, idx_dp_min = net_simulation_calculation.calculate_worst_point(net)
    # print(f"Der Schlechtpunkt des Netzes liegt am Wärmeübertrager {idx_dp_min}. Der Differenzdruck beträgt {dp_min:.3f} bar.")

    return time_15min, calc1, calc2, time_steps, net, net_results

def calculate_results(net_results):
    ### Plotten Ergebnisse Pumpe / Einspeisung ###
    mass_flow_circ_pump = net_results["res_circ_pump_pressure.mdot_flow_kg_per_s"][:, 0]
    deltap_circ_pump =  net_results["res_circ_pump_pressure.deltap_bar"][:, 0]


    rj_circ_pump = net.circ_pump_pressure["return_junction"][0]
    fj_circ_pump = net.circ_pump_pressure["flow_junction"][0]

    return_temp_circ_pump = net_results["res_junction.t_k"][:, rj_circ_pump] - 273.15
    flow_temp_circ_pump = net_results["res_junction.t_k"][:, fj_circ_pump] - 273.15

    return_pressure_circ_pump = net_results["res_junction.p_bar"][:, rj_circ_pump]
    flows_pressure_circ_pump = net_results["res_junction.p_bar"][:, fj_circ_pump]

    cp_kJ_kgK = 4.2 # kJ/kgK

    qext_kW = mass_flow_circ_pump * cp_kJ_kgK * (flow_temp_circ_pump -return_temp_circ_pump)

    return mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW

def plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump, mass_flow_circ_pump):
    # Erstellen Sie eine Figur und ein erstes Achsenobjekt
    fig, ax1 = plt.subplots()

    # Plot für Wärmeleistung auf der ersten Y-Achse
    ax1.plot(time_steps, qext_kW, 'b-', label="Gesamtlast")
    ax1.set_xlabel("Zeit in 15 min Schritten")
    ax1.set_ylabel("Wärmebedarf in kW / 15 min", color='b')
    ax1.tick_params('y', colors='b')
    ax1.legend(loc='upper left')

    # Zweite Y-Achse für die Temperatur
    ax2 = ax1.twinx()
    ax2.plot(time_steps, return_temp_circ_pump, 'm-o', label="circ pump return temperature")
    ax2.plot(time_steps, flow_temp_circ_pump, 'c-o', label="circ pump flow temperature")
    ax2.set_ylabel("temperature [°C]", color='m')
    ax2.tick_params('y', colors='m')
    ax2.legend(loc='upper right')
    ax2.set_ylim(0,100)

    # Dritte Y-Achse für den Massenstrom
    ax3 = ax1.twinx()
    ax3.plot(time_steps, mass_flow_circ_pump, 'y-o', label="circ pump mass flow")
    ax3.set_ylabel("mass flow kg/s", color='y')
    ax3.spines['right'].set_position(('outward', 60))  # Verschiebung der dritten Y-Achse nach rechts
    ax3.tick_params('y', colors='y')
    ax3.legend(loc='lower right')

    # Titel und Raster hinzufügen
    plt.title("Lastgang Wärmenetz")
    plt.grid(True)

    # Zeigen Sie das kombinierte Diagramm an
    plt.show()

def auslegung_erzeuger(time_steps, calc1, calc2, qext_kW, return_temp_circ_pump, flow_temp_circ_pump):
    ### Berechnung Erzeugermix ###

    # bruttufläche_STA: m²
    # vs: Solarspeichervolumen m³
    # Typ: Kollektortyp
    # ...

    bruttofläche_STA = 100
    vs = 10
    Typ = "Vakuumröhrenkollektor"
    Fläche = 0
    Bohrtiefe = 0
    Temperatur_Geothermie = 0
    P_BMK = 30
    Gaspreis = 60
    Strompreis = 100
    Holzpreis = 80
    initial_data = qext_kW, flow_temp_circ_pump, return_temp_circ_pump
    TRY_filename = 'heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat'
    tech_order = ["Solarthermie", "Holzgas-BHKW", "Biomassekessel", "Gaskessel"]
    BEW = "Nein"
    el_Leistung_BHKW = 20
    Kühlleistung_Abwärme = 0
    Temperatur_Abwärme = 0
    Kühlleistung_AWW = 0
    Temperatur_AWW = 0
    COP_data = "Kennlinien WP.csv"

    WGK_Gesamt, Jahreswärmebedarf, Deckungsanteil, Last_L, data_L, data_labels_L, colors_L, Wärmemengen, WGK, \
                Anteile = Berechnung_Erzeugermix(time_steps, calc1, calc2, bruttofläche_STA, vs, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, 
                                                P_BMK, Gaspreis, Strompreis, Holzpreis, initial_data, TRY_filename, 
                                                tech_order, BEW, el_Leistung_BHKW, Kühlleistung_Abwärme, 
                                                Temperatur_Abwärme, Kühlleistung_AWW, Temperatur_AWW, COP_data)

    print(f"Jahreswärmebedarf:", f"{Jahreswärmebedarf:.2f} MWh")

    for t, wärmemenge, anteil, wgk in zip(tech_order, Wärmemengen, Anteile, WGK):
        print(f"Wärmemenge {t}:", f"{wärmemenge:.2f} MWh")
        print(f"Wärmegestehungskosten {t}:", f"{wgk:.2f} €/MWh")
        print(f"Anteil an Wärmeversorgung {t}:", f"{anteil:.2f}")

    print(f"Wärmegestehungskosten Gesamt:", f"{WGK_Gesamt:.2f} €/MWh")

    def Jahresdauerlinie(t, Last_L, data_L, data_labels_L, colors_L):
        fig, ax = plt.subplots()

        ax.plot(t, Last_L, color="black", linewidth=0.5, label="Last in kW")
        ax.stackplot(t, data_L, labels=data_labels_L, colors=colors_L)
        ax.set_title("Jahresdauerlinie")
        ax.set_xlabel("Jahresstunden")
        ax.set_ylabel("thermische Leistung in kW")
        ax.legend(loc='upper center')

        plt.title("Jahresdauerlinie Wärmenetz")
        plt.grid(True)
        
        plt.show()

    def Kreisdiagramm(data_labels_L, colors_L, Anteile):
        pie, ax1 = plt.subplots()
        ax1.pie(Anteile, labels=data_labels_L, colors=colors_L, autopct='%1.1f%%', startangle=90)
        ax1.set_title("Anteile Wärmeerzeugung")
        ax1.legend(loc='center right')
        ax1.axis("equal")
        ax1.plot

        plt.title("Zusammensetzung Wärmeerzeugung")
        plt.grid(True)
        
        plt.show()

    Jahresdauerlinie(time_15min[calc1:calc2], Last_L, data_L, data_labels_L, colors_L)

    Kreisdiagramm(data_labels_L, colors_L, Anteile)



############## CALCULATION #################
time_15min, calc1, calc2, time_steps, net, net_results = thermohydraulic_time_series_net_calculation()

mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
    return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW = calculate_results(net_results)

plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump, mass_flow_circ_pump)

auslegung_erzeuger(time_steps, calc1, calc2, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)