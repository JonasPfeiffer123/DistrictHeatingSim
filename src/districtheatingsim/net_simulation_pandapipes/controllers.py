"""
Controllers Module
==================

This module provides specialized controllers for district heating network operation using
the pandapipes framework.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

It implements advanced control strategies for pressure management,
temperature regulation, and system optimization to ensure efficient and reliable network
operation under varying load conditions.

The controllers integrate with pandapower's control system architecture and support both
steady-state and time-series simulations. They handle complex control scenarios including
bad point pressure control, minimum temperature enforcement, and multi-producer coordination
in district heating systems.
"""

from pandapower.control.basic_controller import BasicCtrl
import numpy as np
from typing import Optional, Tuple, List, Union

class BadPointPressureLiftController(BasicCtrl):
    """
    Differential pressure controller maintaining adequate pressure at network's worst point.
    
    :param net: Pandapipes network object
    :type net: pandapipes.pandapipesNet
    :param circ_pump_pressure_idx: Main circulation pump index, defaults to 0
    :type circ_pump_pressure_idx: int
    :param target_dp_min_bar: Target minimum pressure difference [bar], defaults to 1.0
    :type target_dp_min_bar: float
    :param tolerance: Pressure difference tolerance [bar], defaults to 0.2
    :type tolerance: float
    :param proportional_gain: Proportional gain factor, defaults to 0.2
    :type proportional_gain: float
    :param min_plift: Minimum pump lift during standby [bar], defaults to 1.5
    :type min_plift: float
    :param min_pflow: Minimum flow pressure during standby [bar], defaults to 3.5
    :type min_pflow: float
    :param \\**kwargs: Additional arguments for base controller
    
    :ivar iteration: Current iteration counter
    :vartype iteration: int
    :ivar dp_min: Current minimum pressure difference [bar]
    :vartype dp_min: float
    :ivar heat_consumer_idx: Index of worst point consumer
    :vartype heat_consumer_idx: int
    
    .. note::
       German "Differenzdruckregelung im Schlechtpunkt". Identifies worst point (lowest Δp)
       among active consumers, applies proportional control to pump pressures. Standby mode
       with minimal circulation when all demands zero. Updates bad point dynamically each step.
    """
    
    def __init__(self, net, circ_pump_pressure_idx: int = 0, target_dp_min_bar: float = 1.0, 
                 tolerance: float = 0.2, proportional_gain: float = 0.2, min_plift: float = 1.5, 
                 min_pflow: float = 3.5, **kwargs):
        super(BadPointPressureLiftController, self).__init__(net, **kwargs)
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_dp_min_bar = target_dp_min_bar
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain
        self.min_plift = min_plift
        self.min_pflow = min_pflow
        self.iteration = 0
        
        # Initialize worst point calculation
        self.dp_min, self.heat_consumer_idx = self.calculate_worst_point(net)

    def calculate_worst_point(self, net) -> Tuple[float, int]:
        """
        Find heat consumer with lowest pressure difference among active consumers.
        
        :param net: Pandapipes network with current simulation results
        :type net: pandapipes.pandapipesNet
        :return: (dp_min, idx_min) - minimum pressure difference [bar] and consumer index
        :rtype: Tuple[float, int]
        
        .. note::
           Returns (0, -1) if no active consumers. Only considers consumers with qext_w != 0.
        """
        dp = []

        # Calculate pressure differences for all active heat consumers
        for idx, qext, p_from, p_to in zip(
            net.heat_consumer.index, 
            net.heat_consumer["qext_w"], 
            net.res_heat_consumer["p_from_bar"], 
            net.res_heat_consumer["p_to_bar"]
        ):
            if qext != 0:  # Only consider active consumers
                dp_diff = p_from - p_to
                dp.append((dp_diff, idx))

        if not dp:
            return 0, -1  # No active consumers found

        # Find minimum pressure difference
        dp_min, idx_min = min(dp, key=lambda x: x[0])
        return dp_min, idx_min

    def time_step(self, net, time_step: int) -> int:
        """
        Reset controller state and recalculate worst point for new time step.
        
        :param net: Pandapipes network object
        :type net: pandapipes.pandapipesNet
        :param time_step: Current simulation time step index
        :type time_step: int
        :return: Current time step (pass-through)
        :rtype: int
        
        .. note::
           Resets iteration counter to 0, recalculates worst point location.
        """
        self.iteration = 0
        self.dp_min, self.heat_consumer_idx = self.calculate_worst_point(net)
        return time_step

    def is_converged(self, net) -> bool:
        """
        Check convergence: standby or pressure within tolerance.
        
        :param net: Pandapipes network with current simulation results
        :type net: pandapipes.pandapipesNet
        :return: True if converged, False otherwise
        :rtype: bool
        
        .. note::
           Converged if: all qext_w == 0 (standby) OR |current_dp - target_dp| < tolerance
        """
        # Standby mode - all consumers inactive
        if all(net.heat_consumer["qext_w"] == 0):
            return True
        
        # Calculate current pressure difference at worst point
        current_dp_bar = (
            net.res_heat_consumer["p_from_bar"].at[self.heat_consumer_idx] - 
            net.res_heat_consumer["p_to_bar"].at[self.heat_consumer_idx]
        )

        # Check convergence within tolerance
        dp_within_tolerance = abs(current_dp_bar - self.target_dp_min_bar) < self.tolerance
        return dp_within_tolerance

    def control_step(self, net) -> None:
        """
        Adjust pump pressures based on pressure difference error at worst point.
        
        :param net: Pandapipes network to control
        :type net: pandapipes.pandapipesNet
        
        .. note::
           Standby mode if all qext_w == 0 (sets min_plift/min_pflow). Otherwise applies
           proportional control: error = target_dp - current_dp, adjustment = error × gain.
        """
        self.iteration += 1

        # Handle standby mode - no heat demand
        if all(net.heat_consumer["qext_w"] == 0):
            print("No heat flow detected. Switching to standby mode.")
            net.circ_pump_pressure["plift_bar"].iloc[:] = self.min_plift
            net.circ_pump_pressure["p_flow_bar"].iloc[:] = self.min_pflow
            return super(BadPointPressureLiftController, self).control_step(net)

        # Calculate control parameters
        current_dp_bar = (
            net.res_heat_consumer["p_from_bar"].at[self.heat_consumer_idx] - 
            net.res_heat_consumer["p_to_bar"].at[self.heat_consumer_idx]
        )
        current_plift_bar = net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx]
        current_pflow_bar = net.circ_pump_pressure["p_flow_bar"].at[self.circ_pump_pressure_idx]

        # Calculate control error and adjustments
        dp_error = self.target_dp_min_bar - current_dp_bar
        plift_adjustment = dp_error * self.proportional_gain
        pflow_adjustment = dp_error * self.proportional_gain

        # Apply pressure adjustments
        new_plift = current_plift_bar + plift_adjustment
        new_pflow = current_pflow_bar + pflow_adjustment
        
        net.circ_pump_pressure["plift_bar"].at[self.circ_pump_pressure_idx] = new_plift
        net.circ_pump_pressure["p_flow_bar"].at[self.circ_pump_pressure_idx] = new_pflow

        return super(BadPointPressureLiftController, self).control_step(net)

class MinimumSupplyTemperatureController(BasicCtrl):
    """
    Controller maintaining minimum supply temperatures at heat consumers via return temperature adjustment.
    
    :param net: Pandapipes network object
    :type net: pandapipes.pandapipesNet
    :param heat_consumer_idx: Index of heat consumer to control
    :type heat_consumer_idx: int
    :param min_supply_temperature: Minimum required supply temperature [°C], defaults to 65.0
    :type min_supply_temperature: float
    :param tolerance: Temperature tolerance for convergence [°C], defaults to 2.0
    :type tolerance: float
    :param max_iterations: Maximum iterations per time step, defaults to 100
    :type max_iterations: int
    :param temperature_adjustment_step: Temperature adjustment step [°C], defaults to 1.0
    :type temperature_adjustment_step: float
    :param debug: Enable debug output, defaults to False
    :type debug: bool
    :param \\**kwargs: Additional arguments for base controller
    
    :ivar data_source: External time-varying temperature setpoints
    :vartype data_source: Optional[Any]
    :ivar iteration: Current iteration counter
    :vartype iteration: int
    :ivar previous_temperatures: Temperature history for weighted averaging
    :vartype previous_temperatures: List[float]
    :ivar standard_return_temperature: Original return temperature setpoint
    :vartype standard_return_temperature: float
    
    .. note::
       Critical for cold networks with heat pumps. Monitors supply temperature, adjusts return
       temperature setpoint to increase supply (higher return → higher mass flow → higher supply).
       Uses weighted averaging for stability. Supports time-varying requirements via data_source.
    """
    
    def __init__(self, net, heat_consumer_idx: int, min_supply_temperature: float = 65.0, 
                 tolerance: float = 2.0, max_iterations: int = 100, 
                 temperature_adjustment_step: float = 1.0, debug: bool = False, **kwargs):
        super(MinimumSupplyTemperatureController, self).__init__(net, **kwargs)
        self.heat_consumer_idx = heat_consumer_idx
        self.min_supply_temperature = min_supply_temperature
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.temperature_adjustment_step = temperature_adjustment_step
        self.debug = debug
        
        # Controller state variables
        self.data_source = None
        self.iteration = 0
        self.previous_temperatures: List[float] = []

    def time_step(self, net, time_step: int) -> int:
        """
        Reset controller and update temperature setpoints for new time step.
        
        :param net: Pandapipes network object
        :type net: pandapipes.pandapipesNet
        :param time_step: Current simulation time step index
        :type time_step: int
        :return: Current time step (pass-through)
        :rtype: int
        
        .. note::
           Resets iteration counter and temperature history. Stores/restores standard return
           temperature. Updates min_supply_temperature from data_source if available.
        """
        self.iteration = 0
        self.previous_temperatures = []

        if time_step == 0:
            # Store original return temperature for restoration
            self.standard_return_temperature = net.heat_consumer["treturn_k"].at[self.heat_consumer_idx]
        else:
            # Restore standard return temperature at start of each step
            net.heat_consumer["treturn_k"].at[self.heat_consumer_idx] = self.standard_return_temperature

        # Update minimum temperature from external data source
        if self.data_source is not None:
            self.min_supply_temperature = self.data_source.df.at[time_step, 'min_supply_temperature']
        
        return time_step

    def get_weighted_average_temperature(self) -> Optional[float]:
        """
        Calculate weighted average of recent supply temperatures for stability.
        
        :return: Weighted average temperature [°C], or None if no history
        :rtype: Optional[float]
        
        .. note::
           Linear weighting: recent values weighted more heavily. Prevents oscillations.
        """
        if len(self.previous_temperatures) == 0:
            return None
            
        weights = np.arange(1, len(self.previous_temperatures) + 1)
        weighted_avg = np.dot(self.previous_temperatures, weights) / weights.sum()
        return weighted_avg

    def control_step(self, net) -> None:
        """
        Adjust return temperature to ensure minimum supply temperature.
        
        :param net: Pandapipes network to control
        :type net: pandapipes.pandapipesNet
        
        .. note::
           Standby mode if all qext_w == 0. Uses weighted averaging for stability.
           Increases return temp if supply < minimum (higher return → higher mass flow → higher supply).
        """
        self.iteration += 1
        
        # Handle standby mode - no heat demand
        if all(net.heat_consumer["qext_w"] == 0):
            if self.debug:
                print("No heat flow detected. Switching to standby mode.")
            return super(MinimumSupplyTemperatureController, self).control_step(net)

        # Get current temperatures
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15

        # Apply weighted averaging for stability
        weighted_avg_T_in = self.get_weighted_average_temperature()
        if weighted_avg_T_in is not None:
            current_T_in = weighted_avg_T_in

        current_mass_flow = net.res_heat_consumer["mdot_from_kg_per_s"].at[self.heat_consumer_idx]
        # Adjust return temperature if supply temperature too low
        if current_T_in < self.min_supply_temperature:
            new_T_out = net.heat_consumer["treturn_k"].at[self.heat_consumer_idx] + self.temperature_adjustment_step
            net.heat_consumer["treturn_k"].at[self.heat_consumer_idx] = new_T_out
            
            if self.debug:
                print(f"Minimum supply temperature not met. Adjusted target output temperature to {new_T_out - 273.15:.1f}°C.")
            
        return super(MinimumSupplyTemperatureController, self).control_step(net)

    def is_converged(self, net) -> bool:
        """
        Check convergence: standby, temperature met and stable, or max iterations.
        
        :param net: Pandapipes network with current simulation results
        :type net: pandapipes.pandapipesNet
        :return: True if converged, False otherwise
        :rtype: bool
        
        .. note::
           Converged if: all qext_w == 0 (standby) OR (supply >= minimum AND change < tolerance)
           OR max iterations reached. Maintains temperature history for weighted averaging.
        """
        # Standby mode - all consumers inactive
        if all(net.heat_consumer["qext_w"] == 0):
            return True
        
        # Get current temperatures and system state
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - 273.15
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - 273.15
        previous_T_in = self.previous_temperatures[-1] if self.previous_temperatures else None
        current_mass_flow = net.res_heat_consumer["mdot_from_kg_per_s"].at[self.heat_consumer_idx]

        # Check temperature stability
        temperature_change = abs(current_T_in - previous_T_in) if previous_T_in is not None else float('inf')
        converged_T_in = temperature_change < self.tolerance

        # Update temperature history (keep last 2 values)
        self.previous_temperatures.append(current_T_in)
        if len(self.previous_temperatures) > 2:
            self.previous_temperatures.pop(0)

        # Check minimum temperature requirement
        if current_T_in < self.min_supply_temperature:
            if self.debug:
                print(f"Supply temperature not met for heat_consumer_idx: {self.heat_consumer_idx}. "
                      f"current_temperature_in: {current_T_in:.1f}°C, "
                      f"current_temperature_out: {current_T_out:.1f}°C, "
                      f"current_mass_flow: {current_mass_flow:.3f} kg/s")
            return False
        
        # Check temperature stability convergence
        if converged_T_in:
            if self.debug:
                print(f'Controller converged: heat_consumer_idx: {self.heat_consumer_idx}, '
                      f'current_temperature_in: {current_T_in:.1f}°C, '
                      f'current_temperature_out: {current_T_out:.1f}°C, '
                      f'current_mass_flow: {current_mass_flow:.3f} kg/s')
            return True

        # Forced convergence after maximum iterations
        if self.iteration >= self.max_iterations:
            if self.debug:
                print(f"Max iterations reached for heat_consumer_idx: {self.heat_consumer_idx}")
            return True

        return False