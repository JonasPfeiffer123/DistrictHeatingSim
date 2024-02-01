import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd

from net_simulation_pandapipes.net_simulation_calculation import calculate_worst_point
from net_simulation_pandapipes.net_simulation import generate_profiles_from_geojson, initialize_net_geojson, thermohydraulic_time_series_net, calculate_results
from heat_generators.heat_generator_classes import *
from net_simulation_pandapipes.net_simulation import save_results_csv, import_results_csv

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

def generate_net(calc1=0, calc2=35040, filename='results_time_series_net1.csv'):
    gdf_vl = gpd.read_file('net_generation/Vorlauf.geojson')
    gdf_rl = gpd.read_file('net_generation/Rücklauf.geojson')
    gdf_HAST = gpd.read_file('net_generation/HAST.geojson')
    gdf_WEA = gpd.read_file('net_generation/Erzeugeranlagen.geojson')

    yearly_time_steps, waerme_ges_W, max_waerme_ges_W = generate_profiles_from_geojson(gdf_HAST, building_type="HMF", calc_method="Datensatz")
    net = initialize_net_geojson(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, max_waerme_ges_W)
    time_steps, net, net_results = thermohydraulic_time_series_net(net, yearly_time_steps, waerme_ges_W, calc1, calc2)

    mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
        return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

    ###!!!!!this will overwrite the current csv file!!!!!#
    save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, filename)

    junction_pressure = net_results["res_junction.p_bar"]
    plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, deltap_circ_pump, junction_pressure)
    
    dp_min, idx_dp_min = calculate_worst_point(net)
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

#generate_net(calc1=0, calc2=8760, filename='results/results_time_series_net3.csv') 
#auslegung_erzeuger(calc1=0, calc2= 8760, filename="heat_requirement/Summenlastgang_Scenocalc_skaliert_1MWh.csv", \
#                   optimize=True, load_scale_factor=3000000, Gaspreis=70, Strompreis=150, Holzpreis=50, BEW="Ja")
