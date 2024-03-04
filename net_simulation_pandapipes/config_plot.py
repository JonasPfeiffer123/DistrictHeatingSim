import pandapipes.plotting as pp_plot

def config_plot(net, ax, show_junctions=True, show_pipes=True, show_flow_controls=True, show_heat_exchangers=True, show_plot=False):
    if not ax:
        raise ValueError("Achsenobjekt 'ax' darf nicht False oder None sein")
    
    # Combine the results and names and display them in the plot
    if show_junctions == True:
        for junction in net.junction.index:
            # get the coordinates
            x, y = net.junction_geodata.loc[junction, ['x', 'y']]
            # get the names
            name = net.junction.loc[junction, 'name']
            # get the results
            pressure = net.res_junction.loc[junction, 'p_bar']
            temperature = net.res_junction.loc[junction, 't_k']
            # Create the display text
            display_text = f"{name}\nP: {pressure:.2f} bar\nT: {temperature - 273.15:.2f} °C"
            # show text in plot
            ax.text(x, y, display_text, ha='center', va='bottom', fontsize=8)

    # Show mass flow and flow velocity on pipes
    if show_pipes == True:
        for pipe in net.pipe.index:
            # Find the start and end junction of the pipe
            from_junction = net.pipe.at[pipe, 'from_junction']
            to_junction = net.pipe.at[pipe, 'to_junction']
            
            # Find the coordinates of the start and end junction
            from_x, from_y = net.junction_geodata.loc[from_junction, ['x', 'y']]
            to_x, to_y = net.junction_geodata.loc[to_junction, ['x', 'y']]
            
            # Calculate the center of the pipe
            mid_x = (from_x + to_x) / 2
            mid_y = (from_y + to_y) / 2
            
            # pipe type
            pipe_type = net.pipe.loc[pipe, 'std_type']

            # pipe length
            pipe_length_km = net.pipe.loc[pipe, 'length_km']

            # get pipe results
            mdot = net.res_pipe.loc[pipe, 'mdot_from_kg_per_s']
            v = net.res_pipe.loc[pipe, 'v_mean_m_per_s']
            
            # create display text
            display_text = f"type: {pipe_type}\nlength: {pipe_length_km:.2f} km\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s"
            
            # show text in plot
            ax.text(mid_x, mid_y, display_text, ha='center', va='top', fontsize=8, color='red')

    # show informations about flow_controls
    if show_flow_controls == True:
        for fc in net.flow_control.index:
            # Coordinates of the flow_control
            x, y = net.junction_geodata.loc[net.flow_control.at[fc, 'from_junction'], ['x', 'y']]
            
            # get results
            mdot = net.res_flow_control.loc[fc, 'mdot_from_kg_per_s']
            v = net.res_flow_control.loc[fc, 'v_mean_m_per_s']
            
            # create display text
            display_text = f"Flow Control\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s"
            
            # show text in plot
            ax.text(x, y, display_text, ha='center', va='top', fontsize=8, color='blue')

    # show informations about heat_exchangers
    if show_heat_exchangers == True:
        for hx in net.heat_exchanger.index:
            # Coordinates of the heat_exchangers
            x, y = net.junction_geodata.loc[net.heat_exchanger.at[hx, 'from_junction'], ['x', 'y']]
            
            # get results
            mdot = net.res_heat_exchanger.loc[hx, 'mdot_from_kg_per_s']
            v = net.res_heat_exchanger.loc[hx, 'v_mean_m_per_s']
            qext = net.heat_exchanger.loc[hx, 'qext_w']
            
            # create display text
            display_text = f"Heat Exchanger\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s\nQext: {qext:.2f} W"
            
            # show text in plot
            ax.text(x, y, display_text, ha='center', va='top', fontsize=8, color='green')
    

    pp_plot.simple_plot(net, junction_size=0.01, heat_exchanger_size=0.1, pump_size=0.1, \
                        pump_color='green', pipe_color='black', heat_exchanger_color='blue', ax=ax, \
                        show_plot=show_plot) # Set show_plot to False to show the plot later