import pandapipes.plotting as pp_plot

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
