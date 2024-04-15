import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandapipes as pp

from net_simulation_pandapipes.config_plot import config_plot
from net_simulation_pandapipes.net_simulation_calculation import calculate_worst_point
from net_simulation_pandapipes.net_simulation import generate_profiles_from_geojson, initialize_net_geojson, thermohydraulic_time_series_net, calculate_results
from heat_generators.heat_generator_classes import *
from net_simulation_pandapipes.net_simulation import save_results_csv, import_results_csv

def initialize_test_net():
    net = pp.create_empty_network(fluid="water")

    # Junctions for pump
    j1 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 1", geodata=(0, 10))
    j2 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 2", geodata=(0, 0))

    # Junctions for connection pipes forward line
    j3 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 3", geodata=(10, 0))
    j4 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 4", geodata=(60, 0))

    # Junctions for heat exchangers
    j5 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 5", geodata=(85, 0))
    j6 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 6", geodata=(85, 10))
    
    # Junctions for connection pipes return line
    j7 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 7", geodata=(60, 10))
    j8 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 8", geodata=(10, 10))

    pump1 = pp.create_circ_pump_const_pressure(net, j1, j2, p_flow_bar=4,
                                               plift_bar=1.5, t_flow_k=273.15 + 90,
                                               type="auto", name="pump1")

    pipe1 = pp.create_pipe(net, j2, j3, std_type="110_PE_100_SDR_17", length_km=0.01,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe1", sections=5,
                           text_k=283)
    pipe2 = pp.create_pipe(net, j3, j4, std_type="110_PE_100_SDR_17", length_km=0.05,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe2", sections=5,
                           text_k=283)
    pipe3 = pp.create_pipe(net, j4, j5, std_type="110_PE_100_SDR_17", length_km=0.025,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe3", sections=5,
                           text_k=283)
    
    j10 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 10", geodata=(85, 5))

    heat_exchanger1 = pp.create_heat_exchanger(net, j10, j6, diameter_m=0.04,
                                               loss_coefficient=100, qext_w=50000,
                                               name="heat_exchanger1")
    
    flow_control2 = pp.create_flow_control(net, j5, j10, controlled_mdot_kg_per_s=1, diameter_m=0.04)
    
    j9 = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name="Junction 9", geodata=(60, 5))
    
    heat_exchanger2 = pp.create_heat_exchanger(net, j9, j7, diameter_m=0.03,
                                               loss_coefficient=100, qext_w=50000,
                                               name="heat_exchanger1")
    
    flow_control1 = pp.create_flow_control(net, j4, j9, controlled_mdot_kg_per_s=2, diameter_m=0.03)

    pipe4 = pp.create_pipe(net, j6, j7, std_type="110_PE_100_SDR_17", length_km=0.25,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe4", sections=5,
                           text_k=283)
    pipe5 = pp.create_pipe(net, j7, j8, std_type="110_PE_100_SDR_17", length_km=0.05,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe5", sections=5,
                           text_k=283)
    pipe6 = pp.create_pipe(net, j8, j1, std_type="110_PE_100_SDR_17", length_km=0.01,
                           k_mm=.1, alpha_w_per_m2k=10, name="pipe6", sections=5,
                           text_k=283)

    pp.pipeflow(net, mode="all")
    return net

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

def Jahresdauerlinie(t, Last_L, data_L, data_labels_L):
    fig, ax = plt.subplots()

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

def auslegung_erzeuger(start, end, filename, optimize, load_scale_factor, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins, preissteigerungsrate, betrachtungszeitraum):
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
        techs = optimize_mix(techs, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins, preissteigerungsrate, betrachtungszeitraum)

    general_results = Berechnung_Erzeugermix(techs, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables=[], variables_order=[], kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum)
    
    print(f"Jahreswärmebedarf:", f"{general_results['Jahreswärmebedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Gesamt:", f"{general_results['WGK_Gesamt']:.2f} €/MWh")

    for tech, wärmemenge, anteil, wgk in zip(techs, general_results["Wärmemengen"], general_results["Anteile"], general_results["WGK"]):
        print(f"Wärmemenge {tech.name}:", f"{wärmemenge:.2f} MWh")
        print(f"Wärmegestehungskosten {tech.name}:", f"{wgk:.2f} €/MWh")
        print(f"Anteil an Wärmeversorgung {tech.name}:", f"{anteil:.2f}")

    Jahresdauerlinie(time_steps, general_results["Last_L"], general_results["Wärmeleistung_L"], general_results["techs"])

    Kreisdiagramm(general_results["techs"], general_results["Anteile"])

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

def generate_net(start, end, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, filename):
    yearly_time_steps, waerme_ges_W, max_waerme_ges_W = generate_profiles_from_geojson(gdf_HAST, building_type="HMF", calc_method="BDEW")
    net = initialize_net_geojson(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, max_waerme_ges_W)
    time_steps, net, net_results = thermohydraulic_time_series_net(net, yearly_time_steps, waerme_ges_W, start, end)

    mass_flow_circ_pump, deltap_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
        return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

    ###!!!!!this will overwrite the current csv file!!!!!#
    save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, filename)

    junction_pressure = net_results["res_junction.p_bar"]
    plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump, return_pressure_circ_pump, flows_pressure_circ_pump, deltap_circ_pump, junction_pressure)
    
    dp_min, idx_dp_min = calculate_worst_point(net)
    print(f"Der Schlechtpunkt des Netzes liegt am Wärmeübertrager {idx_dp_min}. Der Differenzdruck beträgt {dp_min:.3f} bar.")

    config_plot(net)

# Example for using "generate_profiles_from_geojson", "initialize_net_geojson", "thermohydraulic_time_series_net", "calculate_results", "save_results_csv", "plot_results", "calculate_worst_point", "config_plot" with generate_net
start = 0
end = 24
#gdf_vl = gpd.read_file('project_data/Beispiel Zittau/Wärmenetz/Vorlauf.geojson')
#gdf_rl = gpd.read_file('project_data/Beispiel Zittau/Wärmenetz/Rücklauf.geojson')
#gdf_HAST = gpd.read_file('project_data/Beispiel Zittau/Wärmenetz/HAST.geojson')
#gdf_WEA = gpd.read_file('project_data/Beispiel Zittau/Wärmenetz/Erzeugeranlagen.geojson')
results_filename='results/results_main.csv'

# generate_net(start, end, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, results_filename)


# Example for using Berechnung_Erzeugermix and optimize_mix with auslegung erzeuger
start = 0
end = 8760
filename = "heat_requirement/Summenlastgang_Scenocalc_skaliert_1MWh.csv"
optimize = True
load_scale_factor = 3000
Gaspreis = 50
Strompreis = 100
Holzpreis = 60
BEW = "Nein"
kapitalzins = 5
preissteigerungsrate = 3
betrachtungszeitraum = 20

#auslegung_erzeuger(start, end, filename, optimize, load_scale_factor, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins, preissteigerungsrate, betrachtungszeitraum)
