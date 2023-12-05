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


### Netzgenerierung und initiale Berechnung ###
net = net_simulation.initialize_net()

#print(net)
#print(net.flow_control)
#print(net.controller)
#print(net.circ_pump_pressure)
print(net.res_heat_exchanger)
#print(net.res_flow_control)
#print(net.res_circ_pump_pressure)

dp_min, idx_dp_min = net_simulation_calculation.calculate_worst_point(net)
print(f"Der niedrigste Differnezdruck beträgt: {dp_min} am Wärmeübertrager {idx_dp_min}")

dp_min_soll = 1

t_rl_soll = 60

circ_pump_pressure_idx = 0
net, net_results = net_simulation.time_series_net(net, idx_dp_min, dp_min_soll, t_rl_soll, circ_pump_pressure_idx, waerme_ges_W[:96])

dp_min, idx_dp_min = net_simulation_calculation.calculate_worst_point(net)
print(f"Der niedrigste Differnezdruck beträgt: {dp_min} am Wärmeübertrager {idx_dp_min}")


### Ausgabe der Netzstruktur ###
pp_plot.simple_plot(net, junction_size=0.2, heat_exchanger_size=0.2, pump_size=0.2, pump_color='green',
                     pipe_color='black', heat_exchanger_color='blue')


### Ausgabe des Leistungsbedarfes ###
plt.plot(time_15min[:96], waerme_ges_kW[:96], label="Wärmeleistung gesamt")
plt.title("Jahresdauerlinie")
plt.legend()
plt.xlabel("Zeit in 15 min Schritten")
plt.ylabel("Wärmebedarf in kW / 15 min")
plt.show()


### Ausgabe des zeitlichen Temperaturverlaufs des Wärmeübertragers am Schlechtpunkt ###
x = time_15min[:96]

y1 = net_results["res_heat_exchanger.t_from_k"] - 273.15
y2 = net_results["res_heat_exchanger.t_to_k"] - 273.15

plt.xlabel("time step")
plt.ylabel("temperature [K]")
plt.title("temperature profile heat exchangers")
plt.plot(x, y1[:,6], "g-o")
plt.plot(x, y2[:,6], "b-o")
plt.legend(["heat exchanger 1 from", "heat exchanger 1 to"], loc='lower left')
plt.grid()
plt.show()