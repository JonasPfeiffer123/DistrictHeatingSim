from net_simulation_pandapipes import net_simulation
from net_simulation_pandapipes import net_simulation_calculation
from heat_requirement import heat_requirement_VDI4655
import matplotlib.pyplot as plt
import pandapipes.plotting as pp_plot
from net_simulation_pandapipes.net_generation_test import initialize_test_net


### Definition der Wärmebedarfe ###
JEB_Wärme_ges_kWh = 50000
JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh = JEB_Wärme_ges_kWh*0.2, JEB_Wärme_ges_kWh*0.8
time_15min, _, _, _, waerme_ges_kW = heat_requirement_VDI4655.calculate(JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh)

waerme_ges_W = waerme_ges_kW * 1000

calc1 = 0
calc2 = 96

### Netzgenerierung und initiale Berechnung ###
net = net_simulation.initialize_net()

#print(net)
#print(net.flow_control)
#print(net.controller)
#print(net.circ_pump_pressure)
#print(net.res_heat_exchanger)
#print(net.res_flow_control)
#print(net.res_circ_pump_pressure)

dp_min, idx_dp_min = net_simulation_calculation.calculate_worst_point(net)
print(f"Der niedrigste Differnezdruck beträgt: {dp_min} am Wärmeübertrager {idx_dp_min}")

dp_min_soll = 1

t_rl_soll = 60

circ_pump_pressure_idx = 0
net, net_results = net_simulation.time_series_net(net, idx_dp_min, dp_min_soll, t_rl_soll, circ_pump_pressure_idx, waerme_ges_W[calc1:calc2])

dp_min, idx_dp_min = net_simulation_calculation.calculate_worst_point(net)
print(f"Der niedrigste Differnezdruck beträgt: {dp_min} am Wärmeübertrager {idx_dp_min}")

### Ausgabe der Netzstruktur ###
pp_plot.simple_plot(net, junction_size=0.2, heat_exchanger_size=0.2, pump_size=0.2, pump_color='green',
                     pipe_color='black', heat_exchanger_color='blue')

# Erstellen Sie eine Figur und ein erstes Achsenobjekt
fig, ax1 = plt.subplots()

# Plot für Wärmeleistung auf der ersten Y-Achse
ax1.plot(time_15min[calc1:calc2], waerme_ges_kW[calc1:calc2], 'b-', label="Wärmeleistung gesamt")
ax1.set_xlabel("Zeit in 15 min Schritten")
ax1.set_ylabel("Wärmebedarf in kW / 15 min", color='g')
ax1.tick_params('y', colors='b')
ax1.legend(loc='upper left')

# Zweite Y-Achse für die Temperatur
ax2 = ax1.twinx()
#ax2.plot(time_15min[calc1:calc2], net_results["res_heat_exchanger.t_from_k"][calc1:calc2, 6] - 273.15, 'r-o', label="heat exchanger 6 t_from")
#ax2.plot(time_15min[calc1:calc2], net_results["res_heat_exchanger.t_to_k"][calc1:calc2, 6] - 273.15, 'b-o', label="heat exchanger 6 t_to")
ax2.plot(time_15min[calc1:calc2], net_results["res_heat_exchanger.t_from_k"][calc1:calc2, ] - 273.15, 'm-o', label="heat exchangers t_from")
ax2.plot(time_15min[calc1:calc2], net_results["res_heat_exchanger.t_to_k"][calc1:calc2, ] - 273.15, 'c-o', label="heat exchangers t_to")
ax2.set_ylabel("temperature [°C]", color='g')
ax2.tick_params('y', colors='g')
ax2.legend(loc='upper right')
ax2.set_ylim(0,100)

# Dritte Y-Achse für den Massenstrom
ax3 = ax1.twinx()
#ax3.plot(time_15min[calc1:calc2], net_results["res_heat_exchanger.mdot_from_kg_per_s"][calc1:calc2, 6], 'y-o', label="heat exchanger 6 mass flow")
ax3.plot(time_15min[calc1:calc2], net_results["res_heat_exchanger.mdot_from_kg_per_s"][calc1:calc2, ], 'y-o', label="heat exchangers mass flow")
ax3.set_ylabel("mass flow kg/s", color='r')
ax3.spines['right'].set_position(('outward', 60))  # Verschiebung der dritten Y-Achse nach rechts
ax3.tick_params('y', colors='r')
ax3.legend(loc='lower right')

# Titel und Raster hinzufügen
plt.title("Jahresdauerlinie und Temperaturprofil Wärmeübertrager")
plt.grid(True)

# Zeigen Sie das kombinierte Diagramm an
plt.show()

"""### Ausgabe des Leistungsbedarfes ###
plt.plot(time_15min[calc1:calc2], waerme_ges_kW[calc1:calc2], label="Wärmeleistung gesamt")
plt.title("Jahresdauerlinie")
plt.legend()
plt.xlabel("Zeit in 15 min Schritten")
plt.ylabel("Wärmebedarf in kW / 15 min")
plt.show()


### Ausgabe des zeitlichen Temperaturverlaufs des Wärmeübertragers am Schlechtpunkt ###
x = time_15min[calc1:calc2]

y1 = net_results["res_heat_exchanger.t_from_k"] - 273.15
y2 = net_results["res_heat_exchanger.t_to_k"] - 273.15
y3 = net_results["res_heat_exchanger.mdot_from_kg_per_s"]

plt.xlabel("time step")
plt.ylabel("temperature [°C]")
plt.title("temperature profile heat exchangers")
plt.plot(x, y1[:,6], "g-o")
plt.plot(x, y2[:,6], "b-o")
plt.legend(["heat exchanger 6 t_from", "heat exchanger 6 t_to"], loc='lower left')
plt.grid()
plt.show()

plt.xlabel("time step")
plt.ylabel("mass flow kg/s")
plt.title("mass flow heat exchangers")
plt.plot(x, y3[:,6], "r-o")
plt.legend(["heat exchanger 6 mass flow"], loc='lower left')
plt.grid()
plt.show()"""