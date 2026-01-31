"""
Pandapipes network utility functions for district heating simulation, optimization,
and analysis including heat pump calculations, controller creation, and diameter optimization.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
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

from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

from typing import Optional, List, Tuple, Dict, Any, Union

# Initialize logging
logging.basicConfig(level=logging.INFO)

def validate_minimum_pressure_difference(net, target_dp_min_bar: float = 1.0, 
                                        verbose: bool = True) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate that all heat consumers meet minimum pressure difference requirements.
    
    :param net: Network with current pipeflow results
    :type net: pandapipes.pandapipesNet
    :param target_dp_min_bar: Minimum required pressure difference [bar]
    :type target_dp_min_bar: float
    :param verbose: Print detailed warnings for violations
    :type verbose: bool
    :return: (all_ok, violations) - True if all consumers meet requirements, list of violations
    :rtype: Tuple[bool, List[Dict[str, Any]]]
    
    .. note::
       Design validation only - does NOT modify pump parameters like BadPointPressureLiftController.
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
    Calculate heat pump Coefficient of Performance (COP) based on supply and source temperatures.
    
    :param VLT_L: Supply temperature(s) for heat pump [°C]
    :type VLT_L: Union[float, np.ndarray]
    :param QT: Source temperature(s) for heat pump [°C]
    :type QT: Union[float, np.ndarray]
    :param values: Heat pump performance data matrix (default loads from CSV)
    :type values: Optional[np.ndarray]
    :return: (COP values [-], adjusted supply temperatures [°C])
    :rtype: Tuple[np.ndarray, np.ndarray]
    :raises ValueError: If QT array length doesn't match VLT_L length
    :raises FileNotFoundError: If default COP data file not found
    
    .. note::
       Technical constraints: max temp lift 75°C (VLT_L ≤ QT + 75°C), min supply temp 35°C.
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
    
    :param net: Pandapipes network object
    :type net: pandapipes.pandapipesNet
    :param qext_w: External heat demand values for each consumer [W]
    :type qext_w: np.ndarray
    :param supply_temperature_heat_generator: Supply temperature setpoint for main generator [°C]
    :type supply_temperature_heat_generator: float
    :param min_supply_temperature_heat_consumer: Minimum required supply temperatures [°C] (None if no constraints)
    :type min_supply_temperature_heat_consumer: Optional[np.ndarray]
    :param return_temperature_heat_consumer: Return temperature setpoints for consumers [°C]
    :type return_temperature_heat_consumer: np.ndarray
    :param secondary_producers: List of secondary producer objects with index, mass_flow, load_percentage
    :type secondary_producers: Optional[List[Dict[str, Any]]]
    :return: Network with all controllers added
    :rtype: pandapipes.pandapipesNet
    
    .. note::
       Controllers include heat consumer demand, temperature regulation, secondary producers, and pressure management.
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
    Correct hydraulic flow directions by analyzing velocities and swapping junction connections.
    
    :param net: Network with potentially incorrect flow directions
    :type net: pandapipes.pandapipesNet
    :return: Network with corrected flow directions
    :rtype: pp.pandapipesNet
    
    .. note::
       Identifies pipes with negative velocities and swaps from_junction/to_junction for proper flow representation.
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
    Optimize network element diameters to meet maximum velocity constraints using continuous adjustment.
    
    :param net: Pandapipes network to optimize
    :type net: pandapipes.pandapipesNet
    :param element: Network element type (default 'pipe')
    :type element: str
    :param v_max: Maximum allowable velocity [m/s]
    :type v_max: float
    :param dx: Diameter adjustment step size [m]
    :type dx: float
    :param safety_factor: Safety factor applied to v_max
    :type safety_factor: float
    :return: Network with optimized diameters
    :rtype: pp.pandapipesNet
    
    .. note::
       Iteratively adjusts diameters with step size dx. Effective v_max = v_max / safety_factor.
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
    
    :param net: Pandapipes network to initialize
    :type net: pandapipes.pandapipesNet
    :param v_max_pipe: Maximum allowable velocity in pipes [m/s]
    :type v_max_pipe: float
    :param material_filter: Pipe material filter for standard types
    :type material_filter: str
    :param k: Pipe roughness coefficient [mm]
    :type k: float
    :return: Network with initialized standard pipe types
    :rtype: pp.pandapipesNet
    
    .. note::
       Selects closest available standard type from filtered catalog based on required diameter.
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
    
    :param net: Pandapipes network to optimize
    :type net: pandapipes.pandapipesNet
    :param v_max: Maximum allowable velocity [m/s]
    :type v_max: float
    :param material_filter: Pipe material filter for standard types
    :type material_filter: str
    :param k: Pipe surface roughness [mm]
    :type k: float
    :return: Network with optimized standard pipe types
    :rtype: pp.pandapipesNet
    
    .. note::
       Iteratively adjusts standard types: upsize pipes exceeding v_max, attempt downsizing below v_max.
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

def export_net_geojson(net, filename: str) -> dict:
    """
    Export pandapipes network data to unified GeoJSON format (Version 2.0).
    
    :param net: Pandapipes network with topology, geodata, and component properties
    :type net: pandapipes.pandapipesNet
    :param filename: Output file path for GeoJSON export
    :type filename: str
    :return: Feature counts {'flow': int, 'return': int, 'building': int, 'generator': int}
    :rtype: dict
    
    .. note::
       Creates single file with flow/return lines, building connections, and generator connections.
    """
    print(f"\n{'='*80}")
    print(f"EXPORT_NET_GEOJSON: Starting export to {filename}")
    print(f"{'='*80}\n")
    
    # Extract flow and return lines from pipes
    flow_features = []
    return_features = []
    
    print(f"Checking pipe_geodata... hasattr: {hasattr(net, 'pipe_geodata')}")
    if hasattr(net, 'pipe_geodata'):
        print(f"pipe_geodata empty: {net.pipe_geodata.empty}")
    
    if hasattr(net, 'pipe_geodata') and not net.pipe_geodata.empty:
        pipe_count = len(net.pipe)
        
        for idx, row in net.pipe_geodata.iterrows():
            pipe_data = net.pipe.loc[idx]
            geometry = LineString(row['coords'])
            
            # Split pipes into flow and return (first half = flow, second half = return)
            feature_data = {
                'geometry': geometry,
                'segment_id': f"{'flow' if idx < pipe_count/2 else 'return'}_{idx:03d}",
                'diameter_mm': pipe_data.get('diameter_m', 0) * 1000,
                'std_type': pipe_data.get('std_type', ''),
                'length_m': pipe_data.get('length_km', 0) * 1000
            }
            
            if idx < pipe_count / 2:
                flow_features.append(feature_data)
            else:
                return_features.append(feature_data)
    
    # Create GeoDataFrames
    flow_gdf = gpd.GeoDataFrame(flow_features, crs="EPSG:25833") if flow_features else gpd.GeoDataFrame()
    return_gdf = gpd.GeoDataFrame(return_features, crs="EPSG:25833") if return_features else gpd.GeoDataFrame()
    
    # Extract building connections from heat consumers
    building_features = []
    if hasattr(net, 'heat_consumer') and not net.heat_consumer.empty:
        for idx, consumer in net.heat_consumer.iterrows():
            from_junction = net.junction_geodata.loc[consumer['from_junction']]
            to_junction = net.junction_geodata.loc[consumer['to_junction']]
            
            geometry = LineString([
                (from_junction['x'], from_junction['y']),
                (to_junction['x'], to_junction['y'])
            ])
            
            building_features.append({
                'geometry': geometry,
                'connection_id': f"hast_{idx:03d}",
                'heat_demand_W': consumer.get('qext_w', 0)
            })
    
    building_gdf = gpd.GeoDataFrame(building_features, crs="EPSG:25833") if building_features else gpd.GeoDataFrame()
    
    # Extract generator connections from circulation pumps
    generator_features = []
    if hasattr(net, 'circ_pump_pressure') and not net.circ_pump_pressure.empty:
        for idx, pump in net.circ_pump_pressure.iterrows():
            return_junction = net.junction_geodata.loc[pump['return_junction']]
            flow_junction = net.junction_geodata.loc[pump['flow_junction']]
            
            geometry = LineString([
                (return_junction['x'], return_junction['y']),
                (flow_junction['x'], flow_junction['y'])
            ])
            
            generator_features.append({
                'geometry': geometry,
                'generator_id': f"gen_{idx:03d}"
            })
    
    generator_gdf = gpd.GeoDataFrame(generator_features, crs="EPSG:25833") if generator_features else gpd.GeoDataFrame()
    
    print(f"\nExtracted features:")
    print(f"  Flow: {len(flow_features)}")
    print(f"  Return: {len(return_features)}")
    print(f"  Buildings: {len(building_features)}")
    print(f"  Generators: {len(generator_features)}")
    print(f"\nCalling create_network_geojson...")
    
    # Create unified GeoJSON using NetworkGeoJSONSchema
    # (calculated data is automatically included from GeoDataFrame columns)
    unified_geojson = NetworkGeoJSONSchema.create_network_geojson(
        flow_lines=flow_gdf,
        return_lines=return_gdf,
        building_connections=building_gdf,
        generator_connections=generator_gdf,
        state='dimensioned'
    )
    
    print(f"Exporting network to unified GeoJSON format: {filename}")
    logging.info(f"Created unified GeoJSON with {len(unified_geojson.get('features', []))} total features")

    # Export to file
    NetworkGeoJSONSchema.export_to_file(unified_geojson, filename)
    
    logging.info(
        f"Network exported to unified GeoJSON: {filename} "
        f"(Flow: {len(flow_features)}, Return: {len(return_features)}, "
        f"Buildings: {len(building_features)}, Generators: {len(generator_features)})"
    )
    
    return {
        'flow': len(flow_features),
        'return': len(return_features),
        'building': len(building_features),
        'generator': len(generator_features)
    }