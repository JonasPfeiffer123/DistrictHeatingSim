"""
Plot-data extraction for the interactive network plot (Plotly-free, GUI-free).
=============================================================================

Pulls the data the interactive Plotly plot needs *out* of a pandapipes net into plain
Python structures, so the rendering layer (``interactive_network_plot``) no longer
mixes pandapipes queries with Plotly trace building (BACKLOG B1/B3). Being Plotly- and
GUI-free, this layer is unit-testable through the network test seam.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""


def available_plot_parameters(net) -> dict[str, list[str]]:
    """
    The result parameters available for colour-coding per component type.

    Inspects the net's ``res_*`` tables and returns the parameters the plot can offer
    for each component (junction, pipe, heat_consumer, pump, flow_control). Empty lists
    for components without results yet.

    :param net: A pandapipes network (duck-typed: read ``res_*`` tables).
    :return: ``{component_type: [parameter, …]}``.
    :rtype: dict[str, list[str]]
    """
    params: dict[str, list[str]] = {
        'junction': [],
        'pipe': [],
        'heat_consumer': [],
        'pump': [],
        'flow_control': [],
    }

    # Junction parameters - Pressure and Temperature
    if hasattr(net, 'res_junction'):
        params['junction'] = [
            'p_bar',  # Pressure [bar]
            't_k',    # Temperature [K]
        ]

    # Pipe parameters - Only most relevant ones
    if hasattr(net, 'res_pipe'):
        available_pipe_params = []
        res_pipe = net.res_pipe

        # Core flow parameters
        if 'mdot_from_kg_per_s' in res_pipe.columns:
            available_pipe_params.append('mdot_from_kg_per_s')  # Mass flow [kg/s]
        if 'v_mean_m_per_s' in res_pipe.columns:
            available_pipe_params.append('v_mean_m_per_s')      # Velocity [m/s]

        # Differential parameters (most useful for analysis)
        if 't_from_k' in res_pipe.columns and 't_to_k' in res_pipe.columns:
            available_pipe_params.append('dt_k')                # Temperature difference [K]
        if 'p_from_bar' in res_pipe.columns and 'p_to_bar' in res_pipe.columns:
            available_pipe_params.append('dp_bar')              # Pressure loss [bar]

        params['pipe'] = available_pipe_params

    # Heat consumer parameters - Only most relevant ones
    if hasattr(net, 'res_heat_consumer'):
        available_hc_params = []
        res_hc = net.res_heat_consumer

        if 'qext_w' in res_hc.columns:
            available_hc_params.append('qext_w')                # Heat demand [W]
        if 'mdot_from_kg_per_s' in res_hc.columns:
            available_hc_params.append('mdot_from_kg_per_s')    # Mass flow [kg/s]

        # Differential parameters (most useful for analysis)
        if 't_from_k' in res_hc.columns and 't_to_k' in res_hc.columns:
            available_hc_params.append('dt_k')                  # Temperature difference [K]
        if 'p_from_bar' in res_hc.columns and 'p_to_bar' in res_hc.columns:
            available_hc_params.append('dp_bar')                # Pressure drop [bar]

        params['heat_consumer'] = available_hc_params

    # Pump parameters - Only most relevant ones
    if hasattr(net, 'res_circ_pump_pressure') or hasattr(net, 'res_circ_pump_mass'):
        available_pump_params = []

        # Pressure pump results
        if hasattr(net, 'res_circ_pump_pressure') and len(net.res_circ_pump_pressure) > 0:
            res_pump = net.res_circ_pump_pressure
            if 'mdot_from_kg_per_s' in res_pump.columns:
                available_pump_params.append('mdot_from_kg_per_s')  # Mass flow [kg/s]
            if 'deltap_bar' in res_pump.columns:
                available_pump_params.append('deltap_bar')          # Pressure increase [bar]

            # Temperature difference
            if 't_from_k' in res_pump.columns and 't_to_k' in res_pump.columns:
                available_pump_params.append('dt_k')                # Temperature difference [K]

        # Mass pump results (if exists)
        if hasattr(net, 'res_circ_pump_mass') and len(net.res_circ_pump_mass) > 0:
            res_pump_mass = net.res_circ_pump_mass
            if 'mdot_from_kg_per_s' in res_pump_mass.columns and 'mdot_from_kg_per_s' not in available_pump_params:
                available_pump_params.append('mdot_from_kg_per_s')

        params['pump'] = list(set(available_pump_params))  # Remove duplicates

    # Flow control parameters
    if hasattr(net, 'res_flow_control') and len(net.flow_control) > 0:
        available_fc_params = []
        res_fc = net.res_flow_control

        if 'mdot_from_kg_per_s' in res_fc.columns:
            available_fc_params.append('mdot_from_kg_per_s')    # Mass flow [kg/s]
        if 'deltap_bar' in res_fc.columns:
            available_fc_params.append('deltap_bar')            # Pressure difference [bar]
        if 't_from_k' in res_fc.columns:
            available_fc_params.append('t_from_k')              # From temperature [K]
        if 't_to_k' in res_fc.columns:
            available_fc_params.append('t_to_k')                # To temperature [K]
        if 'p_from_bar' in res_fc.columns:
            available_fc_params.append('p_from_bar')            # From pressure [bar]
        if 'p_to_bar' in res_fc.columns:
            available_fc_params.append('p_to_bar')              # To pressure [bar]

        params['flow_control'] = available_fc_params

    return params
