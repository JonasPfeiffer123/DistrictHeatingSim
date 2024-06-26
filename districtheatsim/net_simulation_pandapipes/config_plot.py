import numpy as np
import matplotlib.pyplot as plt
import pandapipes.plotting as pp_plot

def config_plot(net, ax, show_junctions=True, show_pipes=True, show_flow_controls=True, show_heat_exchangers=True, show_heat_consumers=True, show_pump=True, show_plot=False):
    ax.clear()  # Vorherige Plots bereinigen

    data_annotations = []  # Zum Speichern der Annotations-Referenzen und Daten

    # Funktion zum Erstellen einer Annotation
    def make_annotation(text, x, y, obj_type, obj_id=None, line_points=None, visible=False):
        # Anpassung des Abstands basierend auf dem Typ
        if obj_type in ["flow_control", "heat_exchanger", "pump"]:
            xytext = (50, 50)  # Erhöhen Sie den Abstand für bessere Sichtbarkeit
        else:
            xytext = (10, 10)
            
        ann = ax.annotate(text, xy=(x, y), xytext=xytext,
                        textcoords='offset points', ha='center', va='bottom',
                        fontsize=8, visible=visible,
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        return {"annotation": ann, "x": x, "y": y, "obj_type": obj_type, "obj_id": obj_id, "line_points": line_points}

    # Hinzufügen der Objekte mit entsprechenden Anpassungen
    # Junctions
    if show_junctions:
        for junction in net.junction.index:
            x, y = net.junction_geodata.loc[junction, ['x', 'y']]
            name = net.junction.loc[junction, 'name']
            pressure = net.res_junction.loc[junction, 'p_bar']
            temperature = net.res_junction.loc[junction, 't_k']
            text = f"{name}\nP: {pressure:.2f} bar\nT: {temperature - 273.15:.2f} °C"
            ann = make_annotation(text, x, y, "junction", junction)
            data_annotations.append(ann)

    # Pipes
    if show_pipes:
        for pipe in net.pipe.index:
            from_junction = net.pipe.at[pipe, 'from_junction']
            to_junction = net.pipe.at[pipe, 'to_junction']
            from_x, from_y = net.junction_geodata.loc[from_junction, ['x', 'y']]
            to_x, to_y = net.junction_geodata.loc[to_junction, ['x', 'y']]
            mid_x = (from_x + to_x) / 2
            mid_y = (from_y + to_y) / 2
            pipe_type = net.pipe.loc[pipe, 'std_type']
            pipe_length_km = net.pipe.loc[pipe, 'length_km']
            mdot = net.res_pipe.loc[pipe, 'mdot_from_kg_per_s']
            v = net.res_pipe.loc[pipe, 'v_mean_m_per_s']
            text = f"Pipe: {pipe_type}\nLength: {pipe_length_km:.2f} km\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s"
            ann = make_annotation(text, mid_x, mid_y, "pipe", pipe, [(from_x, from_y), (to_x, to_y)])
            data_annotations.append(ann)

    if show_heat_consumers:
        for hx in net.heat_consumer.index:
            x, y = net.junction_geodata.loc[net.heat_consumer.at[hx, 'from_junction'], ['x', 'y']]
            mdot = net.res_heat_consumer.loc[hx, 'mdot_from_kg_per_s']
            v = net.res_heat_consumer.loc[hx, 'v_mean_m_per_s']
            qext = net.heat_consumer.loc[hx, 'qext_w']
            text = f"Heat Consumer\nMdot: {mdot:.2f} kg/s\nV: {v:.2f} m/s\nQext: {qext:.2f} W"
            ann = make_annotation(text, x, y, "heat_consumer", hx)
            data_annotations.append(ann)

    if show_pump:
        for pump in net.circ_pump_pressure.index:
            x, y = net.junction_geodata.loc[net.circ_pump_pressure.at[pump, 'return_junction'], ['x', 'y']]
            text = f"Circulation Pump Pressure"
            ann = make_annotation(text, x, y, "pump", pump)
            data_annotations.append(ann)

    pp_plot.simple_plot(net, junction_size=0.01, heat_consumer_size=0.1, pump_size=0.1, 
                        pump_color='green', pipe_color='black', heat_consumer_color="blue", ax=ax, show_plot=False)

    # Event-Handling für die Interaktivität
    def on_move(event):
        if event.inaxes != ax:
            return
        for ann_data in data_annotations:
            if ann_data['obj_type'] == 'pipe':
                # Berechnen Sie den Abstand zur Linie
                p1 = np.array(ann_data['line_points'][0])
                p2 = np.array(ann_data['line_points'][1])
                p3 = np.array([event.xdata, event.ydata])
                dist = np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)
            else:
                # Berechnen Sie den direkten Abstand zum Punkt
                dist = np.hypot(event.xdata - ann_data['x'], event.ydata - ann_data['y'])

            # Sichtbarkeit basierend auf dem Abstand anpassen
            if dist < 0.5:  # Abstandsschwelle
                ann_data['annotation'].set_visible(True)
            else:
                ann_data['annotation'].set_visible(False)
        ax.figure.canvas.draw_idle()

    def on_scroll(event):
        base_scale = 1.5
        # get the current x and y limits
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        cur_xrange = (cur_xlim[1] - cur_xlim[0]) * .5
        cur_yrange = (cur_ylim[1] - cur_ylim[0]) * .5
        xdata = event.xdata  # get event x location
        ydata = event.ydata  # get event y location

        if event.button == 'up':
            # deal with zoom in
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            # deal with zoom out
            scale_factor = base_scale
        else:
            # deal with something that should never happen
            scale_factor = 1
            print(event.button)

        # set new limits
        ax.set_xlim([xdata - cur_xrange * scale_factor,
                    xdata + cur_xrange * scale_factor])
        ax.set_ylim([ydata - cur_yrange * scale_factor,
                    ydata + cur_yrange * scale_factor])
        plt.draw()  # redraw the figure


    ax.figure.canvas.mpl_connect('motion_notify_event', on_move)
    ax.figure.canvas.mpl_connect('scroll_event', on_scroll)

    if show_plot:
        plt.show()