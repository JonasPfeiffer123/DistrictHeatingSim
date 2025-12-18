"""
Pandapipes Network Utility Functions
========================================

This module provides essential utility functions for district heating network simulation,
optimization, and analysis using the pandapipes framework.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-17

It includes heat pump performance calculations, network controller creation, pipe diameter optimization, flow direction
correction, and GeoJSON export capabilities.

The module supports various network optimization strategies including automatic pipe sizing,
velocity-based diameter selection, and hydraulic flow direction correction. It integrates
custom control systems for temperature management and multi-producer coordination in
complex district heating networks.
"""

import time
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from scipy.interpolate import RegularGridInterpolator

import pandapipes as pp
from pandapipes.control.run_control import run_control

from pandapower.timeseries import DFData
from pandapower.control.controller.const_control import ConstControl

from districtheatingsim.utilities.utilities import get_resource_path
from districtheatingsim.net_simulation_pandapipes.controllers import MinimumSupplyTemperatureController, BadPointPressureLiftController

from typing import Optional, List, Tuple, Dict, Any, Union

# Initialize logging
logging.basicConfig(level=logging.INFO)

def validate_minimum_pressure_difference(net, target_dp_min_bar: float = 1.0, 
                                        verbose: bool = True) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate that all heat consumers meet minimum pressure difference requirements.
    
    This function checks the design without modifying pump parameters. It's intended
    for use after pipe diameter optimization to ensure the design meets requirements.
    Unlike the BadPointPressureLiftController, this does NOT adjust the network,
    it only reports violations.
    
    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The network to validate (must have current pipeflow results)
    target_dp_min_bar : float
        Minimum required pressure difference [bar]
    verbose : bool
        If True, print detailed warnings for violations
        
    Returns
    -------
    Tuple[bool, List[Dict[str, Any]]]
        - all_ok (bool): True if all consumers meet requirements
        - violations (list): List of violation dictionaries with details
        
    Examples
    --------
    >>> # After diameter optimization
    >>> pp.pipeflow(net, mode="bidirectional")
    >>> all_ok, violations = validate_minimum_pressure_difference(net, target_dp_min_bar=1.0)
    >>> if not all_ok:
    ...     print(f"Design has {len(violations)} pressure violations")
    ...     # Adjust pump parameters or pipe diameters
    """
    violations = []
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"VALIDATING MINIMUM PRESSURE DIFFERENCE")
        print(f"Target: dp_min >= {target_dp_min_bar} bar")
        print(f"{'='*80}\n")
    
    # Check each active heat consumer
    for idx in net.heat_consumer.index:
        qext = net.heat_consumer.at[idx, 'qext_w']
        
        # Only check active consumers
        if qext == 0:
            continue
            
        p_from = net.res_heat_consumer.at[idx, 'p_from_bar']
        p_to = net.res_heat_consumer.at[idx, 'p_to_bar']
        dp = p_from - p_to
        
        consumer_name = net.heat_consumer.at[idx, 'name'] if 'name' in net.heat_consumer.columns else f"Consumer {idx}"
        
        if dp < target_dp_min_bar:
            violation = {
                'index': idx,
                'name': consumer_name,
                'dp_bar': dp,
                'deficit_bar': target_dp_min_bar - dp,
                'p_from_bar': p_from,
                'p_to_bar': p_to,
                'qext_w': qext
            }
            violations.append(violation)
            
            if verbose:
                print(f"⚠ WARNING: {consumer_name}")
                print(f"  Pressure difference: {dp:.3f} bar < {target_dp_min_bar} bar")
                print(f"  Deficit: {target_dp_min_bar - dp:.3f} bar")
                print(f"  p_from: {p_from:.3f} bar, p_to: {p_to:.3f} bar")
                print(f"  Heat demand: {qext/1000:.1f} kW\n")
        else:
            if verbose:
                print(f"✓ OK: {consumer_name} - dp={dp:.3f} bar >= {target_dp_min_bar} bar")
    
    all_ok = len(violations) == 0
    
    if verbose:
        print(f"\n{'='*80}")
        if all_ok:
            print(f"✓ VALIDATION PASSED - All consumers meet minimum pressure requirements")
        else:
            print(f"✗ VALIDATION FAILED - {len(violations)} consumers below minimum pressure")
            print(f"\nRecommendations:")
            print(f"  1. Increase pump pressure (p_flow_bar or plift_bar)")
            print(f"  2. Use larger pipe diameters")
            print(f"  3. Reduce pipe lengths if possible")
            print(f"  4. Check for flow restrictions")
        print(f"{'='*80}\n")
    
    return all_ok, violations


def COP_WP(VLT_L: Union[float, np.ndarray], QT: Union[float, np.ndarray], 
          values: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate the Coefficient of Performance (COP) for heat pumps based on supply and source temperatures.

    This function determines heat pump efficiency using interpolation of manufacturer performance
    data. It enforces technical operating limits and handles both scalar and array inputs for
    flexible application in time series simulations and steady-state calculations.

    Parameters
    ----------
    VLT_L : Union[float, np.ndarray]
        Supply temperature(s) for the heat pump system [°C].
        Can be single value or array for time series calculations.
    QT : Union[float, np.ndarray]
        Source temperature(s) for the heat pump [°C].
        For ground source: typically 8-12°C constant.
        For air source: variable outdoor air temperature.
    values : Optional[np.ndarray], optional
        Heat pump performance data matrix with temperature grid and COP values.
        Default loads manufacturer data from 'data/COP/Kennlinien WP.csv'.
        First row contains supply temperatures, first column contains source temperatures.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        A tuple containing:
        
        - **COP_L** (np.ndarray) : Coefficient of Performance values [-]
        - **VLT_L** (np.ndarray) : Adjusted supply temperatures [°C] (within technical limits)

    Raises
    ------
    ValueError
        If QT array length doesn't match VLT_L array length.
    FileNotFoundError
        If default COP data file cannot be found.

    Notes
    -----
    Technical Constraints:
        - Maximum temperature lift: 75°C (VLT_L ≤ QT + 75°C)
        - Minimum supply temperature: 35°C
        - Interpolation method: Linear interpolation between data points
        - Extrapolation: Uses boundary values for out-of-range conditions

    Performance Data Format:
        - CSV file with semicolon separation
        - First row (excluding [0,0]): Supply temperatures [°C]
        - First column (excluding [0,0]): Source temperatures [°C]
        - Data matrix: COP values [-]

    Typical COP Values:
        - Air source heat pumps: 2.5-4.5 (temperature dependent)
        - Ground source heat pumps: 3.5-5.5 (more stable)
        - Water source heat pumps: 4.0-6.0 (highest efficiency)

    Examples
    --------
    >>> # Single operating point
    >>> cop, supply_temp = COP_WP(45.0, 10.0)
    >>> print(f"COP: {cop[0]:.2f}, Supply temp: {supply_temp[0]:.1f}°C")
    COP: 4.20, Supply temp: 45.0°C

    >>> # Time series calculation for air source heat pump
    >>> outdoor_temps = np.array([-5, 0, 5, 10, 15])  # °C
    >>> supply_temps = np.array([55, 50, 45, 40, 35])  # °C
    >>> cops, adjusted_temps = COP_WP(supply_temps, outdoor_temps)
    >>> print(f"Average COP: {np.mean(cops):.2f}")

    >>> # Cold network application
    >>> building_supply = np.array([35, 40, 45])  # Building heating temperature
    >>> ground_temp = 8.0  # Constant ground source temperature
    >>> cop_values, _ = COP_WP(building_supply, ground_temp)
    >>> electrical_power = heat_demand / cop_values  # kW

    See Also
    --------
    initialize_geojson : Uses COP calculation for cold network processing
    RegularGridInterpolator : Scipy interpolation method used internally
    """
    # Load default COP data if not provided
    if values is None:
        values = np.genfromtxt(get_resource_path('data/COP/Kennlinien WP.csv'), delimiter=';')
    
    # Extract temperature grids and COP matrix
    row_header = values[0, 1:]  # Supply temperatures [°C]
    col_header = values[1:, 0]  # Source temperatures [°C]  
    cop_matrix = values[1:, 1:]  # COP values [-]
    
    # Create interpolation function
    f = RegularGridInterpolator((col_header, row_header), cop_matrix, method='linear')

    # Apply technical limits of heat pump operation
    VLT_L = np.minimum(VLT_L, 75 + QT)  # Maximum temperature lift constraint
    VLT_L = np.maximum(VLT_L, 35)       # Minimum supply temperature constraint

    # Handle scalar vs array input for source temperature
    if np.isscalar(QT):
        QT_array = np.full_like(VLT_L, QT)
    else:
        if len(QT) != len(VLT_L):
            raise ValueError("QT must either be a single number or an array with the same length as VLT_L.")
        QT_array = QT

    # Calculate COP using bilinear interpolation
    COP_L = f(np.column_stack((QT_array, VLT_L)))

    return COP_L, VLT_L

def create_controllers(net, qext_w: np.ndarray, supply_temperature_heat_generator: float, 
                      min_supply_temperature_heat_consumer: Optional[np.ndarray], 
                      return_temperature_heat_consumer: np.ndarray, 
                      secondary_producers: Optional[List[Dict[str, Any]]] = None):
    """
    Create comprehensive control systems for district heating network operation.

    This function establishes all necessary controllers for network operation including
    heat consumer demand control, temperature regulation, secondary producer coordination,
    and system pressure management. It creates both static and dynamic controllers
    based on the network configuration and operational requirements.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object to which controllers will be added.
    qext_w : np.ndarray
        External heat demand values for each heat consumer [W].
        Array length must match the number of heat consumers.
    supply_temperature_heat_generator : float
        Supply temperature setpoint for the main heat generator [°C].
    min_supply_temperature_heat_consumer : Optional[np.ndarray]
        Minimum required supply temperatures for heat consumers [°C].
        None if no minimum temperature constraints are needed.
    return_temperature_heat_consumer : np.ndarray
        Return temperature setpoints for heat consumers [°C].
        Array length must match the number of heat consumers.
    secondary_producers : Optional[List[SecondaryProducer]], optional
    List of secondary producer objects, each containing:

        - **index** (int) : Producer identification index
        - **mass_flow** (float) : Design mass flow rate [kg/s]
        - **load_percentage** (float) : Load percentage of total demand [%]

    Returns
    -------
    pandapipes.pandapipesNet
        The network object with all controllers added and configured.

    Notes
    -----
    Controller Types Created:
        - **Heat Consumer Controllers** : Demand and return temperature control
        - **Temperature Controllers** : Minimum supply temperature enforcement
        - **Heat Generator Controllers** : Main producer supply temperature control
        - **Secondary Producer Controllers** : Mass flow and temperature control
        - **Pressure Controllers** : System pressure management and bad point control

    Control Strategy:
        - Heat consumers: Constant heat demand with fixed return temperature
        - Main producer: Pressure-controlled with temperature setpoint
        - Secondary producers: Mass flow-controlled with coordinated temperature
        - System pressure: Automatic bad point pressure lift control (if enabled)
        
    Design Phase vs Operation:
        - Design Phase: enable_pressure_controller=False
          → Controllers created but inactive for stable diameter optimization
        - Operation Phase: enable_pressure_controller=True
          → Full dynamic control including pressure regulation

    Data Source Integration:
        - Uses pandapower DFData for time series compatibility
        - Placeholder DataFrames for static control values
        - Extensible for dynamic time series control

    Examples
    --------
    >>> # Design phase: Controllers inactive for diameter optimization
    >>> net_with_controls = create_controllers(
    ...     net=network,
    ...     qext_w=np.array([50000, 75000, 30000]),
    ...     supply_temperature_heat_generator=80.0,
    ...     min_supply_temperature_heat_consumer=None,
    ...     return_temperature_heat_consumer=np.array([45, 50, 40])  # Return temps
    ... )

    >>> # Network with secondary producers
    >>> secondary_config = [
    ...     {"index": 1, "mass_flow": 2.5},  # Solar thermal plant
    ...     {"index": 2, "mass_flow": 1.8}   # CHP unit
    ... ]
    >>> net_with_controls = create_controllers(
    ...     net, heat_demands, 75.0, min_temps, return_temps, secondary_config
    ... )

    >>> # Cold network with minimum temperature constraints
    >>> min_supply_temps = np.array([35, 40, 38])  # Minimum temperatures for heat pumps
    >>> net_with_controls = create_controllers(
    ...     net, demands, 45.0, min_supply_temps, returns
    ... )

    See Also
    --------
    MinimumSupplyTemperatureController : Custom temperature control implementation
    BadPointPressureLiftController : Pressure management controller
    ConstControl : pandapower constant value controller
    validate_minimum_pressure_difference : Design validation without control
    """
    # Create controllers for each heat consumer
    for i in range(len(net.heat_consumer)):
        # Heat demand controller
        placeholder_df_qext = pd.DataFrame({f'qext_w_{i}': [qext_w[i]]})
        placeholder_data_source_qext = DFData(placeholder_df_qext)
        ConstControl(net, element='heat_consumer', variable='qext_w', element_index=i, 
                    data_source=placeholder_data_source_qext, profile_name=f'qext_w_{i}')

        # Return temperature controller  
        placeholder_df_treturn = pd.DataFrame({f'treturn_k_{i}': [return_temperature_heat_consumer[i] + 273.15]})
        placeholder_data_source_treturn = DFData(placeholder_df_treturn)
        ConstControl(net, element='heat_consumer', variable='treturn_k', element_index=i, 
                    data_source=placeholder_data_source_treturn, profile_name=f'treturn_k_{i}')

        # Minimum supply temperature controller (if required)
        if min_supply_temperature_heat_consumer is not None and np.any(np.array(min_supply_temperature_heat_consumer) != 0):
            print(f"Creating temperature controller for heat consumer {i} with min supply temperature {min_supply_temperature_heat_consumer[i]} °C")
            
            min_supply_temp_profile = pd.DataFrame({
                f'min_supply_temperature': [min_supply_temperature_heat_consumer[i]]
            })
            min_supply_temp_data_source = DFData(min_supply_temp_profile)
            
            T_controller = MinimumSupplyTemperatureController(
                net,
                heat_consumer_idx=i,
                min_supply_temperature=min_supply_temperature_heat_consumer[i]
            )
            T_controller.data_source = min_supply_temp_data_source
            # Manual registration required (BasicCtrl doesn't auto-register)
            net.controller.loc[len(net.controller)] = [T_controller, True, -1, -1, False, False, None]

    # Main heat generator supply temperature controller
    placeholder_df_supply_temp = pd.DataFrame({'supply_temperature': [supply_temperature_heat_generator + 273.15]})
    placeholder_data_source_supply_temp = DFData(placeholder_df_supply_temp)
    ConstControl(net, element='circ_pump_pressure', variable='t_flow_k', element_index=0, 
                data_source=placeholder_data_source_supply_temp, profile_name='supply_temperature')

    # Secondary producer controllers
    if secondary_producers:
        for producer in secondary_producers:
            # KORRIGIERT: Verwende Attribut-Zugriff statt Dictionary-Zugriff
            mass_flow = producer.mass_flow if hasattr(producer, 'mass_flow') else 0
            producer_index = producer.index if hasattr(producer, 'index') else 0
            
            # Mass flow controller for circulation pump
            placeholder_df = pd.DataFrame({f'mdot_flow_kg_per_s_{producer_index}': [mass_flow]})
            placeholder_data_source = DFData(placeholder_df)
            ConstControl(net, element='circ_pump_mass', variable='mdot_flow_kg_per_s', element_index=0,
                        data_source=placeholder_data_source, profile_name=f'mdot_flow_kg_per_s_{producer_index}')

            # Flow control for producer
            placeholder_df_flow = pd.DataFrame({f'controlled_mdot_kg_per_s_{producer_index}': [mass_flow]})
            placeholder_data_source_flow = DFData(placeholder_df_flow)
            ConstControl(net, element='flow_control', variable='controlled_mdot_kg_per_s', element_index=0,
                        data_source=placeholder_data_source_flow, profile_name=f'controlled_mdot_kg_per_s_{producer_index}')

            # Supply temperature for secondary producers
            ConstControl(net, element='circ_pump_mass', variable='t_flow_k', element_index=0, 
                        data_source=placeholder_data_source_supply_temp, profile_name='supply_temperature')


    # System pressure management controller
    dp_controller = BadPointPressureLiftController(net)
    # Manual registration required (BasicCtrl doesn't auto-register)
    net.controller.loc[len(net.controller)] = [dp_controller, True, -1, -1, False, False, None]

    return net

def correct_flow_directions(net) -> pp.pandapipesNet:
    """
    Correct hydraulic flow directions in the network by analyzing velocities and swapping connections.

    This function identifies pipes with negative flow velocities (reverse flow) and corrects
    the network topology by swapping junction connections. This ensures proper flow direction
    representation for accurate hydraulic analysis and visualization.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object with potentially incorrect flow directions.

    Returns
    -------
    pandapipes.pandapipesNet
        The network object with corrected flow directions and updated hydraulic results.

    Notes
    -----
    Correction Algorithm:
        1. Performs initial bidirectional pipeflow calculation
        2. Identifies pipes with negative mean velocities
        3. Swaps from_junction and to_junction for negative flow pipes
        4. Recalculates pipeflow to obtain corrected results

    Why Flow Direction Matters:
        - Proper visualization of flow patterns
        - Correct heat transfer calculations
        - Accurate pressure drop analysis
        - Consistent result interpretation

    Technical Background:
        - Junction swapping aligns pipe orientation with actual flow

    Examples
    --------
    >>> # Correct flow directions after network creation
    >>> corrected_net = correct_flow_directions(network)
    >>> 
    >>> # Check flow directions in results
    >>> positive_flows = (corrected_net.res_pipe.v_mean_m_per_s >= 0).sum()
    >>> total_pipes = len(corrected_net.res_pipe)
    >>> print(f"Positive flow directions: {positive_flows}/{total_pipes}")

    >>> # Analyze flow patterns after correction
    >>> max_velocity = corrected_net.res_pipe.v_mean_m_per_s.max()
    >>> avg_velocity = corrected_net.res_pipe.v_mean_m_per_s.mean()
    >>> print(f"Max velocity: {max_velocity:.2f} m/s")
    >>> print(f"Average velocity: {avg_velocity:.2f} m/s")

    See Also
    --------
    pp.pipeflow : pandapipes hydraulic calculation function
    create_network : Network creation where this function is typically applied
    """
    # Initial pipeflow calculation to determine actual flow directions
    pp.pipeflow(net, mode="bidirectional", iter=100)

    # Identify and correct pipes with reverse flow
    corrections_made = 0
    for pipe_idx in net.pipe.index:
        if net.res_pipe.v_mean_m_per_s[pipe_idx] < 0:
            # Swap junction connections for reverse flow pipes
            from_junction = net.pipe.at[pipe_idx, 'from_junction']
            to_junction = net.pipe.at[pipe_idx, 'to_junction']
            net.pipe.at[pipe_idx, 'from_junction'] = to_junction
            net.pipe.at[pipe_idx, 'to_junction'] = from_junction
            corrections_made += 1

    # Recalculate with corrected flow directions
    pp.pipeflow(net, mode="bidirectional", iter=100)
    
    if corrections_made > 0:
        logging.info(f"Corrected flow directions for {corrections_made} pipes")

    return net

def optimize_diameter_parameters(net, element: str = "pipe", v_max: float = 2.0, 
                               dx: float = 0.001, safety_factor: float = 1.5) -> pp.pandapipesNet:
    """
    Optimize network element diameters to meet specified maximum velocity constraints.

    This function iteratively adjusts pipe diameters to achieve optimal hydraulic performance
    while respecting velocity limits. It uses a continuous diameter adjustment approach
    with configurable step size and safety factors for robust optimization.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object to optimize.
    element : str, optional
        Network element type to optimize. Default is "pipe".
        Currently supports "pipe" elements.
    v_max : float, optional
        Maximum allowable velocity [m/s]. Default is 2.0 m/s.
        Typical values: 1.0-2.5 m/s for district heating.
    dx : float, optional
        Diameter adjustment step size [m]. Default is 0.001 m (1 mm).
        Smaller values provide finer optimization but longer computation time.
    safety_factor : float, optional
        Safety factor applied to maximum velocity. Default is 1.5.
        Effective v_max = v_max / safety_factor for conservative design.

    Returns
    -------
    pandapipes.pandapipesNet
        The network object with optimized diameters.

    Notes
    -----
    Optimization Algorithm:
        1. Calculate initial flow velocities
        2. For each element exceeding v_max: increase diameter by dx
        3. For each element below v_max: attempt diameter reduction
        4. Validate reduction doesn't exceed v_max
        5. Repeat until no changes needed

    Velocity Calculation:
        - Uses volumetric flow rate divided by cross-sectional area
        - More accurate than mean velocity for optimization
        - Accounts for actual flow conditions

    Design Considerations:
        - Higher velocities: Lower material costs, higher pressure losses, lower thermal losses
        - Lower velocities: Higher material costs, lower pressure losses, higher thermal losses
        - Safety factor prevents operation too close to limits

    Examples
    --------
    >>> # Standard optimization for district heating
    >>> optimized_net = optimize_diameter_parameters(
    ...     net, v_max=1.5, safety_factor=1.2
    ... )

    >>> # Fine optimization with small steps
    >>> optimized_net = optimize_diameter_parameters(
    ...     net, v_max=2.0, dx=0.0005, safety_factor=1.3
    ... )

    >>> # Check optimization results
    >>> max_velocity = optimized_net.res_pipe.v_mean_m_per_s.max()
    >>> print(f"Maximum velocity after optimization: {max_velocity:.2f} m/s")

    See Also
    --------
    init_diameter_types : Initialize with standard pipe types
    optimize_diameter_types : Optimize using discrete standard sizes
    """
    # Apply safety factor to velocity limit
    effective_v_max = v_max / safety_factor
    
    # Initial flow calculation
    pp.pipeflow(net, mode="bidirectional", iter=100)
    run_control(net, mode="bidirectional", iter=100)
    element_df = getattr(net, element)
    res_df = getattr(net, f"res_{element}")
            
    iteration_count = 0
    change_made = True
    
    while change_made:
        change_made = False
        iteration_count += 1
        
        for idx in element_df.index:
            # Calculate velocity using volumetric flow and cross-sectional area
            current_velocity = res_df.vdot_m3_per_s[idx] / (np.pi * (element_df.at[idx, 'diameter_m'] / 2)**2)
            current_diameter = element_df.at[idx, 'diameter_m']
            
            # Increase diameter if velocity exceeds limit
            if current_velocity > effective_v_max:
                element_df.at[idx, 'diameter_m'] += dx
                change_made = True

            # Attempt diameter reduction if below limit
            elif current_velocity < effective_v_max:
                element_df.at[idx, 'diameter_m'] -= dx
                
                # Validate reduction doesn't violate constraints
                pp.pipeflow(net, mode="bidirectional", iter=100)
                run_control(net, mode="bidirectional", iter=100)
                element_df = getattr(net, element)
                res_df = getattr(net, f"res_{element}")
                
                new_velocity = res_df.vdot_m3_per_s[idx] / (np.pi * (element_df.at[idx, 'diameter_m'] / 2)**2)

                if new_velocity > effective_v_max:
                    # Revert if reduction violates constraint
                    element_df.at[idx, 'diameter_m'] = current_diameter
                else:
                    change_made = True
        
        # Recalculate only if changes were made
        if change_made:
            pp.pipeflow(net, mode="bidirectional", iter=100)
            run_control(net, mode="bidirectional", iter=100)
            element_df = getattr(net, element)
            res_df = getattr(net, f"res_{element}")

    logging.info(f"Diameter optimization completed in {iteration_count} iterations")
    return net

def init_diameter_types(net, v_max_pipe: float = 1.0, material_filter: str = "KMR", 
                       k: float = 0.1) -> pp.pandapipesNet:
    """
    Initialize pipe diameters using standard pipe types based on velocity requirements.

    This function selects appropriate standard pipe types from available catalogs
    based on calculated flow velocities and design constraints. It provides the
    initial pipe sizing for network optimization and detailed design phases.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object to initialize.
    v_max_pipe : float, optional
        Maximum allowable velocity in pipes [m/s]. Default is 1.0 m/s.
        Conservative value suitable for initial design.
    material_filter : str, optional
        Pipe material filter for standard type selection. Default is "KMR".
        Common options: "KMR" (steel), "PE" (polyethylene), "PEX" (cross-linked PE).
    k : float, optional
        Pipe roughness coefficient [mm]. Default is 0.1 mm.
        Typical values: 0.1-0.5 mm for new pipes, 0.5-2.0 mm for aged pipes.

    Returns
    -------
    pandapipes.pandapipesNet
        The network object with initialized standard pipe types and properties.

    Notes
    -----
    Initialization Process:
        1. Calculate required diameter based on current velocity and target velocity
        2. Select closest available standard pipe type from filtered catalog
        3. Update pipe properties (diameter, thermal conductivity, roughness)
        4. Perform final hydraulic calculation with new pipe properties

    Standard Pipe Selection:
        - Uses pandapipes standard type libraries
        - Filters by material type for consistency
        - Selects closest match to required diameter
        - Maintains thermal and hydraulic properties

    Pipe Properties Updated:
        - inner_diameter_mm: From standard type catalog
        - u_w_per_m2k: Thermal conductivity from standard type
        - k_mm: Surface roughness (user-specified)

    Examples
    --------
    >>> # Initialize with conservative velocity limit
    >>> initialized_net = init_diameter_types(
    ...     net, v_max_pipe=0.8, material_filter="KMR", k=0.1
    ... )

    >>> # Initialize for polyethylene pipes
    >>> initialized_net = init_diameter_types(
    ...     net, v_max_pipe=1.2, material_filter="PE", k=0.05
    ... )

    >>> # Check initialized pipe types
    >>> pipe_types = initialized_net.pipe.std_type.unique()
    >>> print(f"Selected pipe types: {pipe_types}")

    See Also
    --------
    optimize_diameter_types : Iterative optimization with standard types
    pp.std_types.available_std_types : Access pandapipes standard type catalogs
    """
    start_time = time.time()
    
    # Initial hydraulic calculation
    print(f"\n{'='*80}")
    print(f"INIT_DIAMETER_TYPES: Initial calculation (pipeflow + control)")
    print(f"{'='*80}")
    # Step 1: Calculate velocities with current diameters
    pp.pipeflow(net, mode="bidirectional", iter=100)
    # Step 2: Let controller adjust pump parameters for proper pressures
    run_control(net, mode="bidirectional", iter=100)

    # Load and filter standard pipe types
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    filtered_by_material = pipe_std_types[pipe_std_types['material'] == material_filter]

    if filtered_by_material.empty:
        raise ValueError(f"No standard pipe types found for material filter: {material_filter}")

    # Initialize pipe diameters based on velocity requirements
    print(f"\n{'='*80}")
    print(f"INIT_DIAMETER_TYPES: Initializing {len(net.pipe)} pipes")
    print(f"v_max_pipe = {v_max_pipe} m/s, material = {material_filter}")
    print(f"Available types: {filtered_by_material.index.tolist()}")
    print(f"{'='*80}\n")
    
    for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
        current_diameter = net.pipe.at[pipe_idx, 'diameter_m']
        pipe_name = net.pipe.at[pipe_idx, 'name'] if 'name' in net.pipe.columns else f"Pipe {pipe_idx}"
        
        # Calculate required diameter using continuity equation
        required_diameter = current_diameter * (velocity / v_max_pipe)**0.5
        
        # Find closest available standard type
        closest_type = min(
            filtered_by_material.index, 
            key=lambda x: abs(filtered_by_material.loc[x, 'inner_diameter_mm'] / 1000 - required_diameter)
        )
        
        # Update pipe properties
        properties = filtered_by_material.loc[closest_type]
        selected_diameter = properties['inner_diameter_mm'] / 1000
        
        net.pipe.std_type.at[pipe_idx] = closest_type
        net.pipe.at[pipe_idx, 'diameter_m'] = selected_diameter
        net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
        net.pipe.at[pipe_idx, 'k_mm'] = k

    # Final hydraulic calculation with updated pipe properties
    print(f"\n{'='*80}")
    print(f"INIT_DIAMETER_TYPES: Final calculation with new diameters")
    print(f"{'='*80}")
    # Step 1: Calculate velocities with new diameters
    pp.pipeflow(net, mode="bidirectional", iter=100)
    
    # Step 2: Adjust pump parameters to meet pressure requirements
    run_control(net, mode="bidirectional", iter=100)
    if hasattr(net, 'circ_pump_pressure') and len(net.circ_pump_pressure) > 0:
        print(f"Final pump pressure: {net.circ_pump_pressure.at[0, 'p_flow_bar']:.2f} bar")
        print(f"Final pump lift: {net.circ_pump_pressure.at[0, 'plift_bar']:.2f} bar")
    print(f"{'='*80}\n")
    
    total_time = time.time() - start_time
    logging.info(f"Pipe diameter initialization completed in {total_time:.2f} seconds")

    return net

def optimize_diameter_types(net, v_max: float = 1.0, material_filter: str = "KMR", 
                           k: float = 0.1) -> pp.pandapipesNet:
    """
    Optimize pipe diameters using discrete standard pipe types through iterative adjustment.

    This function performs comprehensive pipe diameter optimization by iteratively
    selecting standard pipe types that minimize material costs while meeting
    velocity constraints. It provides the most realistic optimization approach
    using commercially available pipe sizes.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object to optimize.
    v_max : float, optional
        Maximum allowable velocity in pipes [m/s]. Default is 1.0 m/s.
        Balance between pressure losses and material costs.
    material_filter : str, optional
        Pipe material filter for standard type selection. Default is "KMR".
        Ensures consistent material properties throughout network.
    k : float, optional
        Pipe surface roughness [mm]. Default is 0.1 mm.
        Affects friction losses and hydraulic performance.

    Returns
    -------
    pandapipes.pandapipesNet
        The network object with optimized standard pipe types and properties.

    Notes
    -----
    Optimization Algorithm:
        1. Initial diameter sizing based on velocity requirements
        2. Iterative adjustment using discrete standard types
        3. Upsize pipes exceeding velocity limit
        4. Attempt downsizing for pipes below velocity limit
        5. Validate downsizing doesn't violate constraints
        6. Continue until all pipes meet requirements

    Standard Type Management:
        - Maintains position tracking in type catalog
        - Ensures valid type transitions (adjacent sizes only)
        - Preserves material consistency throughout network
        - Updates all pipe properties consistently

    Convergence Criteria:
        - All pipes within velocity limits
        - No further beneficial size reductions possible
        - System hydraulically balanced

    Performance Tracking:
        - Logs iteration progress and timing
        - Reports pipes within/outside target velocity
        - Monitors optimization convergence

    Examples
    --------
    >>> # Standard optimization for district heating
    >>> optimized_net = optimize_diameter_types(
    ...     net, v_max=1.2, material_filter="KMR", k=0.15
    ... )

    >>> # High-performance optimization
    >>> optimized_net = optimize_diameter_types(
    ...     net, v_max=0.8, material_filter="PE", k=0.05
    ... )

    >>> # Check optimization results
    >>> velocities = optimized_net.res_pipe.v_mean_m_per_s
    >>> over_limit = (velocities > v_max).sum()
    >>> print(f"Pipes over velocity limit: {over_limit}")

    >>> # Analyze pipe type distribution
    >>> type_counts = optimized_net.pipe.std_type.value_counts()
    >>> print("Pipe type distribution:")
    >>> print(type_counts)

    See Also
    --------
    init_diameter_types : Initial pipe type selection
    optimize_diameter_parameters : Continuous diameter optimization
    run_control : pandapipes control system execution
    """
    start_time = time.time()

    # Load and filter standard pipe types
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    filtered_by_material = pipe_std_types[pipe_std_types['material'] == material_filter]

    if filtered_by_material.empty:
        raise ValueError(f"No standard pipe types found for material filter: {material_filter}")

    # Create type position mapping for optimization
    type_position_dict = {type_name: i for i, type_name in enumerate(filtered_by_material.index)}

    # Initial system state calculation
    print(f"\n{'='*80}")
    print(f"OPTIMIZE_DIAMETER_TYPES: Starting optimization")
    print(f"v_max = {v_max} m/s, material = {material_filter}")
    print(f"Available types: {filtered_by_material.index.tolist()}")
    print(f"{'='*80}")
    
    # Calculate current state (assumes init_diameter_types was called before)
    pp.pipeflow(net, mode="bidirectional", iter=100)
    run_control(net, mode="bidirectional", iter=100)

    # Initialize optimization tracking
    net.pipe['optimized'] = False
    change_made = True
    iteration_count = 0

    # Iterative optimization loop
    print(f"\n{'='*80}")
    print(f"OPTIMIZE_DIAMETER_TYPES: Starting iterative optimization")
    print(f"{'='*80}\n")
    
    while change_made:
        iteration_start = time.time()
        change_made = False
        pipes_within_target = 0
        pipes_outside_target = 0
        
        print(f"\n--- Iteration {iteration_count + 1} ---")

        for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
            # Skip already optimized pipes within limits
            if net.pipe.at[pipe_idx, 'optimized'] and velocity <= v_max:
                pipes_within_target += 1
                continue

            current_type = net.pipe.std_type.at[pipe_idx]
            current_position = type_position_dict[current_type]

            # Upsize pipes exceeding velocity limit
            if velocity > v_max and current_position < len(filtered_by_material) - 1:
                new_type = filtered_by_material.index[current_position + 1]
                properties = filtered_by_material.loc[new_type]
                pipe_name = net.pipe.at[pipe_idx, 'name'] if 'name' in net.pipe.columns else f"Pipe {pipe_idx}"
                
                print(f"  {pipe_name}: UPSIZE v={velocity:.3f} > {v_max} m/s | {current_type} → {new_type}")
                
                net.pipe.std_type.at[pipe_idx] = new_type
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
                net.pipe.at[pipe_idx, 'k_mm'] = k
                
                change_made = True
                pipes_outside_target += 1

            # Attempt downsizing for pipes within limits
            elif velocity <= v_max and current_position > 0:
                new_type = filtered_by_material.index[current_position - 1]
                properties = filtered_by_material.loc[new_type]
                pipe_name = net.pipe.at[pipe_idx, 'name'] if 'name' in net.pipe.columns else f"Pipe {pipe_idx}"
                
                # Temporarily apply smaller diameter
                net.pipe.std_type.at[pipe_idx] = new_type
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
                net.pipe.at[pipe_idx, 'k_mm'] = k

                # Validate downsizing doesn't violate constraints
                print(f"    Testing downsize: {current_type} → {new_type}")
                # Step 1: Calculate new velocities
                pp.pipeflow(net, mode="bidirectional", iter=100)
                # Step 2: Adjust pump if needed
                run_control(net, mode="bidirectional", iter=100)
                new_velocity = net.res_pipe.v_mean_m_per_s[pipe_idx]
                print(f"    New velocity: {new_velocity:.3f} m/s")

                if new_velocity <= v_max:
                    print(f"  {pipe_name}: DOWNSIZE v={velocity:.3f} ≤ {v_max} m/s | {current_type} → {new_type} (new v={new_velocity:.3f})")
                    change_made = True
                else:
                    print(f"  {pipe_name}: REVERT v={velocity:.3f} → {new_velocity:.3f} > {v_max} m/s | {new_type} → {current_type}")
                    # Revert to previous size and mark as optimized
                    properties = filtered_by_material.loc[current_type]
                    net.pipe.std_type.at[pipe_idx] = current_type
                    net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                    net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
                    net.pipe.at[pipe_idx, 'k_mm'] = k
                    
                    net.pipe.at[pipe_idx, 'optimized'] = True
                    pipes_within_target += 1
            else:
                # Mark as optimized if no further changes possible
                net.pipe.at[pipe_idx, 'optimized'] = True
                pipes_within_target += 1

        iteration_count += 1
        
        # Recalculate if changes were made
        if change_made:
            print(f"\nRecalculating network after changes...")
            # Step 1: Calculate velocities
            pp.pipeflow(net, mode="bidirectional", iter=100)
            # Step 2: Adjust pump parameters
            run_control(net, mode="bidirectional", iter=100)
            print(f"Network recalculated with adjusted pump parameters")
        
        iteration_time = time.time() - iteration_start
        print(f"\nIteration {iteration_count} summary: {pipes_within_target} pipes OK, {pipes_outside_target} pipes adjusted ({iteration_time:.2f}s)")
        logging.info(f"Iteration {iteration_count}: {pipes_within_target} pipes within target, "
                    f"{pipes_outside_target} pipes outside target ({iteration_time:.2f}s)")
        
        if not change_made:
            print(f"\n{'='*80}")
            print(f"OPTIMIZATION CONVERGED after {iteration_count} iterations")
            print(f"{'='*80}\n")

    # Final calculation with optimized parameters
    print(f"\n{'='*80}")
    print(f"OPTIMIZE: Final calculation")
    print(f"{'='*80}")
    # Step 1: Calculate final velocities
    pp.pipeflow(net, mode="bidirectional", iter=100)
    print(f"Final velocities: {net.res_pipe.v_mean_m_per_s.values}")
    
    # Step 2: Final pump adjustment
    run_control(net, mode="bidirectional", iter=100)
    print(f"\nOptimization complete!")
    if hasattr(net, 'circ_pump_pressure') and len(net.circ_pump_pressure) > 0:
        print(f"Optimized pump pressure: {net.circ_pump_pressure.at[0, 'p_flow_bar']:.2f} bar")
        print(f"Optimized pump lift: {net.circ_pump_pressure.at[0, 'plift_bar']:.2f} bar")
    print(f"Optimized pipe types: {net.pipe.std_type.unique()}")
    print(f"{'='*80}")
    
    total_time = time.time() - start_time
    logging.info(f"Total optimization time: {total_time:.2f} seconds")

    return net

def export_net_geojson(net, filename: str) -> None:
    """
    Export pandapipes network data to GeoJSON format for GIS integration and visualization.

    This function converts a pandapipes network into GeoJSON format, enabling integration
    with Geographic Information Systems (GIS) and web mapping applications. It preserves
    geometric information, component properties, and technical specifications for
    comprehensive spatial analysis.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object containing topology, geodata, and component properties.
    filename : str
        Output file path for the GeoJSON export. Should have .geojson extension.

    Returns
    -------
    None
        Function creates GeoJSON file at specified location.

    Notes
    -----
    Exported Components:
        - **Pipes** : LineString geometries with diameter, type, and length information
        - **Heat Consumers** : LineString connections with heat demand data
        - **Circulation Pumps** : LineString representations of pump connections
        - **Junction data** : Preserved in component geometries

    GeoJSON Structure:
        - Feature Collection format
        - EPSG:25833 coordinate reference system
        - Component properties as feature attributes
        - LineString geometries for all network elements

    Component Properties:
        - **Pipes** : name, diameter_mm, std_type, length_m
        - **Heat Consumers** : name, qext_W (heat demand)
        - **Pumps** : name, geometry (connection line)

    Applications:
        - GIS analysis and spatial planning
        - Web mapping and visualization
        - Integration with urban planning tools
        - Stakeholder presentation and reporting

    Examples
    --------
    >>> # Export network for GIS analysis
    >>> export_net_geojson(network, "network_layout.geojson")

    >>> # Export optimized network
    >>> optimized_net = optimize_diameter_types(network)
    >>> export_net_geojson(optimized_net, "optimized_network.geojson")

    >>> # Verify export with geopandas
    >>> import geopandas as gpd
    >>> gdf = gpd.read_file("network_layout.geojson")
    >>> print(f"Exported {len(gdf)} network features")
    >>> print(f"Feature types: {gdf.geometry.geom_type.unique()}")

    Raises
    ------
    AttributeError
        If network lacks required geodata components.
    ValueError
        If coordinate data is invalid or missing.

    See Also
    --------
    create_network : Network creation with geodata integration
    geopandas.GeoDataFrame.to_file : Underlying export functionality
    """
    features = []  # Collect GeoDataFrames for all network components
    
    # Export pipe data
    if hasattr(net, 'pipe_geodata') and not net.pipe_geodata.empty:
        # Create LineString geometries from coordinate data
        geometry_lines = [LineString(coords) for coords in net.pipe_geodata['coords']]
        gdf_lines = gpd.GeoDataFrame(net.pipe_geodata, geometry=geometry_lines)
        del gdf_lines['coords']  # Remove coordinate list column
        
        # Add pipe technical properties
        gdf_lines['name'] = net.pipe['name']
        gdf_lines['diameter_mm'] = net.pipe['diameter_m'] * 1000
        gdf_lines['std_type'] = net.pipe['std_type']
        gdf_lines['length_m'] = net.pipe['length_km'] * 1000
        
        features.append(gdf_lines)

    # Export circulation pump data
    if hasattr(net, 'circ_pump_pressure') and not net.circ_pump_pressure.empty:
        # Create pump connection lines
        pump_lines = []
        for index, pump in net.circ_pump_pressure.iterrows():
            return_coords = net.junction_geodata.loc[pump['return_junction']]
            flow_coords = net.junction_geodata.loc[pump['flow_junction']]
            line = LineString([
                (return_coords['x'], return_coords['y']),
                (flow_coords['x'], flow_coords['y'])
            ])
            pump_lines.append(line)
        
        # Create GeoDataFrame with pump properties
        relevant_columns = ['name']
        pump_data = net.circ_pump_pressure[relevant_columns].copy()
        gdf_pumps = gpd.GeoDataFrame(pump_data, geometry=pump_lines)
        
        features.append(gdf_pumps)

    # Export heat consumer data
    if hasattr(net, 'heat_consumer') and not net.heat_consumer.empty:
        for idx, heat_consumer in net.heat_consumer.iterrows():
            # Get connection coordinates
            start_coords = net.junction_geodata.loc[heat_consumer['from_junction']]
            end_coords = net.junction_geodata.loc[heat_consumer['to_junction']]

            # Create connection line geometry
            line = LineString([
                (start_coords['x'], start_coords['y']), 
                (end_coords['x'], end_coords['y'])
            ])
            
            # Create feature with heat consumer properties
            gdf_component = gpd.GeoDataFrame({
                'name': ["HAST"],            
                'qext_W': [f"{heat_consumer['qext_w']:.0f}"],
                'geometry': [line]
            }, crs="EPSG:25833")
            
            features.append(gdf_component)

    # Set consistent coordinate reference system
    for feature in features:
        if not feature.crs:
            feature.set_crs(epsg=25833, inplace=True)

    # Combine all features and export
    if features:
        gdf_all = gpd.GeoDataFrame(pd.concat(features, ignore_index=True), crs="EPSG:25833")
        gdf_all.to_file(filename, driver='GeoJSON')
        logging.info(f"Network exported to GeoJSON: {filename} ({len(gdf_all)} features)")
    else:
        logging.warning("No geographical data available in the network for export")