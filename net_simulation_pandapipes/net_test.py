import pandapipes.plotting as pp_plot
import geopandas as gpd
import pandapipes as pp

from net_simulation_pandapipes.net_simulation_calculation import correct_flow_directions, optimize_diameter_parameters, optimize_diameter_types
import net_simulation_pandapipes.net_simulation_calculation as nsp

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

def config_plot(net, ax, show_junctions=True, show_pipes=True, show_flow_controls=True, show_heat_exchangers=True, show_plot=False):
    if not ax:
        raise ValueError("Achsenobjekt 'ax' darf nicht False oder None sein")
    
    # Kombinieren Sie die Ergebnisse und Namen, und zeigen Sie sie im Plot an
    if show_junctions == True:
        for junction in net.junction.index:
            # Holen Sie sich die Koordinaten
            x, y = net.junction_geodata.loc[junction, ['x', 'y']]
            # Holen Sie sich den Namen
            name = net.junction.loc[junction, 'name']
            # Holen Sie sich die Ergebnisse
            pressure = net.res_junction.loc[junction, 'p_bar']
            temperature = net.res_junction.loc[junction, 't_k']
            # Erstellen Sie die Anzeigezeichenkette
            display_text = f"{name}\nP: {pressure:.2f} bar\nT: {temperature - 273.15:.2f} °C"
            # Zeigen Sie den Text im Plot an
            ax.text(x, y, display_text, ha='center', va='bottom', fontsize=8)

    # Massenstrom und Strömungsgeschwindigkeit an Pipes anzeigen
    if show_pipes == True:
        for pipe in net.pipe.index:
            # Finde die Start- und End-Junction der Pipe
            from_junction = net.pipe.at[pipe, 'from_junction']
            to_junction = net.pipe.at[pipe, 'to_junction']
            
            # Finde die Koordinaten der Start- und End-Junction
            from_x, from_y = net.junction_geodata.loc[from_junction, ['x', 'y']]
            to_x, to_y = net.junction_geodata.loc[to_junction, ['x', 'y']]
            
            # Berechne den Mittelpunkt der Pipe
            mid_x = (from_x + to_x) / 2
            mid_y = (from_y + to_y) / 2
            
            # pipe type
            pipe_type = net.pipe.loc[pipe, 'std_type']

            # Länge Pipe
            pipe_length_km = net.pipe.loc[pipe, 'length_km']

            # Ergebnisse für die Pipe abrufen
            mdot = net.res_pipe.loc[pipe, 'mdot_from_kg_per_s']
            v = net.res_pipe.loc[pipe, 'v_mean_m_per_s']
            
            # Anzeigezeichenkette erstellen
            display_text = f"type: {pipe_type}\nlength: {pipe_length_km:.2f} km\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s"
            
            # Text im Plot anzeigen
            ax.text(mid_x, mid_y, display_text, ha='center', va='top', fontsize=8, color='red')

    # Informationen für flow_controls anzeigen
    if show_flow_controls == True:
        for fc in net.flow_control.index:
            # Koordinaten des flow_controls
            x, y = net.junction_geodata.loc[net.flow_control.at[fc, 'from_junction'], ['x', 'y']]
            
            # Ergebnisse abrufen
            mdot = net.res_flow_control.loc[fc, 'mdot_from_kg_per_s']
            v = net.res_flow_control.loc[fc, 'v_mean_m_per_s']
            
            # Anzeigezeichenkette erstellen
            display_text = f"Flow Control\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s"
            
            # Text im Plot anzeigen
            ax.text(x, y, display_text, ha='center', va='top', fontsize=8, color='blue')

    # Informationen für heat_exchangers anzeigen
    if show_heat_exchangers == True:
        for hx in net.heat_exchanger.index:
            # Koordinaten des heat_exchangers
            x, y = net.junction_geodata.loc[net.heat_exchanger.at[hx, 'from_junction'], ['x', 'y']]
            
            # Ergebnisse abrufen
            mdot = net.res_heat_exchanger.loc[hx, 'mdot_from_kg_per_s']
            v = net.res_heat_exchanger.loc[hx, 'v_mean_m_per_s']
            qext = net.heat_exchanger.loc[hx, 'qext_w']
            
            # Anzeigezeichenkette erstellen
            display_text = f"Heat Exchanger\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s\nQext: {qext:.2f} W"
            
            # Text im Plot anzeigen
            ax.text(x, y, display_text, ha='center', va='top', fontsize=8, color='green')
    

    pp_plot.simple_plot(net, junction_size=0.01, heat_exchanger_size=0.1, pump_size=0.1, \
                        pump_color='green', pipe_color='black', heat_exchanger_color='blue', ax=ax, \
                        show_plot=show_plot)  # Setzen Sie show_plot auf False, um den Plot später anzuzeigen

def generate_net(qext_w=83000, pipe_creation_mode="type"):
    gdf_vl = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Vorlauf.geojson')
    gdf_rl = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Rücklauf.geojson')
    gdf_HAST = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/HAST.geojson')
    gdf_WEA = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Erzeugeranlagen.geojson')

    net = nsp.create_network(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, qext_w, pipe_creation_mode)

    net_corrected_flow = correct_flow_directions(net)
    net_optimized_diameters = optimize_diameter_types(net_corrected_flow)
    net_optimized_diameters = optimize_diameter_parameters(net_optimized_diameters, element="heat_exchanger", v_max=2, v_min=1.8)
    net_optimized_diameters = optimize_diameter_parameters(net_optimized_diameters, element="flow_control", v_max=2, v_min=1.8)

    

    return net, net_corrected_flow, net_optimized_diameters

def generate_test_net():
    net = initialize_test_net()
    config_plot(net)

    optimized_net = optimize_diameter_types(net)
    config_plot(optimized_net)

    optimized_net = optimize_diameter_parameters(optimized_net, element="heat_exchanger", v_max=2, v_min=1.8)
    optimized_net = optimize_diameter_parameters(optimized_net, element="flow_control", v_max=2, v_min=1.8)

    config_plot(optimized_net)

#generate_test_net()

#gis_net, gis_net_corrected_flow, gis_net_optimized_diameters = generate_net()

#config_plot(gis_net_optimized_diameters)

