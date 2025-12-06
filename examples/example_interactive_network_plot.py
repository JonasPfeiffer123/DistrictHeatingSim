import numpy as np
import pandapipes as pp

from districtheatingsim.net_simulation_pandapipes.interactive_network_plot import InteractiveNetworkPlot

def initialize_test_net(qext_w=np.array([100000, 200000]),
                        return_temperature=np.array([55, 60]),
                        supply_temperature=85, 
                        flow_pressure_pump=4,
                        lift_pressure_pump=1.5,
                        pipetype="110/202 PLUS",
                        v_max_m_s=1.5):
    print("Running the test network initialization script.")
    net = pp.create_empty_network(fluid="water")

    k = 0.1 # roughness defaults to 0.1

    supply_temperature_k = supply_temperature + 273.15
    return_temperature_k = return_temperature + 273.15

    mass_pump_mass_flow = 0.2 # kg/s

    # Junctions for pump
    j1 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 1", geodata=(0, 100))
    j2 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 2", geodata=(0, 0))

    # Junctions for connection pipes forward line
    j3 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 3", geodata=(100, 0))
    j4 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 4", geodata=(600, 0))

    # Junctions for heat exchangers
    j5 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 5", geodata=(850, 0))
    j6 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 6", geodata=(850, 100))
    
    # Junctions for connection pipes return line
    j7 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 7", geodata=(600, 100))
    j8 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 8", geodata=(100, 100))

    pump1 = pp.create_circ_pump_const_pressure(net, j1, j2, p_flow_bar=flow_pressure_pump,
                                               plift_bar=lift_pressure_pump, t_flow_k=supply_temperature_k,
                                               type="auto", name="Circ Pump Pressure")

    pipe1 = pp.create_pipe(net, j2, j3, std_type=pipetype, length_km=0.01, k_mm=k, name="Pipe 1", sections=5, text_k=283)
    pipe2 = pp.create_pipe(net, j3, j4, std_type=pipetype, length_km=0.05, k_mm=k, name="Pipe 2", sections=5, text_k=283)
    pipe3 = pp.create_pipe(net, j4, j5, std_type=pipetype, length_km=0.025, k_mm=k, name="Pipe 3", sections=5, text_k=283)

    pp.create_heat_consumer(net, from_junction=j5, to_junction=j6, qext_w=qext_w[0], treturn_k=return_temperature_k[0], name="Consumer A")
    pp.create_heat_consumer(net, from_junction=j4, to_junction=j7, qext_w=qext_w[1], treturn_k=return_temperature_k[1], name="Consumer B")
    
    pipe4 = pp.create_pipe(net, j6, j7, std_type=pipetype, length_km=0.25, k_mm=k, name="Pipe 4", sections=5, text_k=283)
    pipe5 = pp.create_pipe(net, j7, j8, std_type=pipetype, length_km=0.05, k_mm=k, name="Pipe 5", sections=5, text_k=283)
    pipe6 = pp.create_pipe(net, j8, j1, std_type=pipetype, length_km=0.01, k_mm=k, name="Pipe 6", sections=5, text_k=283)
    
    ### here comes the part with the additional circ_pump_const_mass_flow ###
    # first of, the junctions
    j9 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 9", geodata=(1000, 0))
    j10 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 10", geodata=(1000, 100))
    j11 = pp.create_junction(net, pn_bar=1.05, tfluid_k=supply_temperature_k, name="Junction 11", geodata=(1000, 50))

    pipe7 = pp.create_pipe(net, j5, j9, std_type=pipetype, length_km=0.05, k_mm=k, name="Pipe 7", sections=5, text_k=283)
    pipe8 = pp.create_pipe(net, j10, j6, std_type=pipetype, length_km=0.01, k_mm=k, name="Pipe 8", sections=5, text_k=283)

    pump2 = pp.create_circ_pump_const_mass_flow(net, j10, j11, p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=mass_pump_mass_flow, 
                                                t_flow_k=supply_temperature_k, type="auto", name="Circ Pump Mass Flow")
    
    flow_control_pump2 = pp.create_flow_control(net, j11, j9, controlled_mdot_kg_per_s=mass_pump_mass_flow, name="Flow Control Pump Mass Flow")

    pp.pipeflow(net, mode="bidirectional", iter=100)

    return net

# Example usage
if __name__ == "__main__":
    # Example with test network - use a simple heat transfer network
    net = initialize_test_net()
    
    # Create interactive plot with dropdown controls
    plotter = InteractiveNetworkPlot(net)
    
    # Single plot with all visualizations in dropdown
    fig = plotter.create_interactive_plot_with_controls(colorscale='RdYlBu_r')
    fig.show()