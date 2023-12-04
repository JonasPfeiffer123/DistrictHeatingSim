from net_simulation_pandapipes import net_simulation
from heat_requirement import heat_requirement_VDI4655
import matplotlib.pyplot as plt

# net = initialize_net()
# test_net = initialize_test_net()

# time_series_net(net)

# net = initialize_net()
# nsp.calculate_worst_point(net)

JEB_Wärme_ges_kWh = 50000
JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh = JEB_Wärme_ges_kWh*0.2, JEB_Wärme_ges_kWh*0.8
time_15min, _, _, _, waerme_ges_kW = heat_requirement_VDI4655.calculate(JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh)

plt.plot(time_15min[2000:3000], waerme_ges_kW[2000:3000], label="Wärmeleistung gesamt")
plt.title("Jahresdauerlinie")
plt.legend()
plt.xlabel("Zeit in 15 min Schritten")
plt.ylabel("Wärmebedarf in kW / 15 min")
plt.show()

net = net_simulation.initialize_net()
net_simulation.time_series_net(net, waerme_ges_kW)