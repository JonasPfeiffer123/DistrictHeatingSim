"""
Controllers Module
==================

This module provides specialized controllers for district heating network operation using
the pandapipes framework.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-25

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
    Controller for maintaining adequate pressure difference at the network's worst point.
    
    This controller implements the German concept of "Differenzdruckregelung im Schlechtpunkt"
    (differential pressure control at the bad point), which ensures that the heat consumer
    with the lowest pressure difference receives adequate pressure for proper operation.
    The controller dynamically adjusts pump pressures to maintain target pressure differences
    throughout the network.
    
    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object containing all network components and topology.
    circ_pump_pressure_idx : int, optional
        Index of the circulation pump to control. Default is 0.
        Refers to the main circulation pump in the network.
    target_dp_min_bar : float, optional
        Target minimum pressure difference at the worst point [bar]. Default is 1.0.
        Ensures adequate pressure for heat transfer at all consumers.
    tolerance : float, optional
        Acceptable tolerance for pressure difference control [bar]. Default is 0.2.
        Controller considers system converged when within this tolerance.
    proportional_gain : float, optional
        Proportional gain factor for controller response. Default is 0.2.
        Higher values provide faster response but may cause instability.
    min_plift : float, optional
        Minimum pump lift pressure during standby operation [bar]. Default is 1.5.
        Maintains circulation during no-load conditions.
    min_pflow : float, optional
        Minimum flow pressure during standby operation [bar]. Default is 3.5.
        Ensures adequate system pressure during standby.
    **kwargs
        Additional keyword arguments passed to the base controller.
        
    Attributes
    ----------
    iteration : int
        Current iteration counter within each time step.
    dp_min : float
        Current minimum pressure difference in the network [bar].
    heat_consumer_idx : int
        Index of the heat consumer representing the worst point.
        
    Notes
    -----
    Control Algorithm:
        1. Identifies worst point (lowest pressure difference) among active consumers
        2. Calculates pressure difference error from target value
        3. Applies proportional control to adjust pump pressures
        4. Maintains minimum pressures during standby operation
        
    Bad Point Identification:
        - Only considers heat consumers with non-zero heat demand
        - Calculates pressure difference: p_from - p_to
        - Selects consumer with minimum pressure difference
        - Updates bad point location dynamically each time step
        
    Standby Operation:
        - Activates when all heat consumers have zero demand
        - Maintains minimum circulation to prevent stagnation
        - Reduces energy consumption during idle periods
        
    Examples
    --------
    >>> # Create pressure controller for main circulation pump
    >>> pressure_controller = BadPointPressureLiftController(
    ...     net=network,
    ...     target_dp_min_bar=1.2,
    ...     proportional_gain=0.15,
    ...     tolerance=0.1
    ... )
    
    >>> # Add controller to network
    >>> net.controller.loc[len(net.controller)] = [
    ...     pressure_controller, True, -1, -1, False, False
    ... ]
    
    >>> # Controller automatically manages pressure during simulation
    >>> pp.pipeflow(net, mode="bidirectional")
    
    See Also
    --------
    MinimumSupplyTemperatureController : Temperature control system
    pandapower.control.basic_controller.BasicCtrl : Base controller class
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
        Calculate the worst point in the heating network.
        
        The worst point is defined as the heat consumer with the lowest pressure
        difference (p_from - p_to) among all consumers with active heat demand.
        This represents the most hydraulically disadvantaged point in the network.
        
        Parameters
        ----------
        net : pandapipes.pandapipesNet
            The pandapipes network object with current simulation results.
            
        Returns
        -------
        Tuple[float, int]
            A tuple containing:
            - **dp_min** (float) : Minimum pressure difference found [bar]
            - **idx_min** (int) : Index of heat consumer at worst point
            
        Notes
        -----
        Algorithm:
            1. Iterates through all heat consumers
            2. Excludes consumers with zero heat demand
            3. Calculates pressure difference for active consumers
            4. Returns consumer with minimum pressure difference
            
        Edge Cases:
            - Returns (0, -1) if no active consumers found
            - Handles empty heat consumer list gracefully
            
        Examples
        --------
        >>> dp_min, worst_idx = controller.calculate_worst_point(network)
        >>> print(f"Worst point pressure difference: {dp_min:.2f} bar")
        >>> print(f"Located at heat consumer index: {worst_idx}")
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
        Initialize controller state for each time step.
        
        This method is called at the beginning of each time step to reset
        controller parameters and update the worst point location based on
        current network conditions.
        
        Parameters
        ----------
        net : pandapipes.pandapipesNet
            The pandapipes network object.
        time_step : int
            Current simulation time step index.
            
        Returns
        -------
        int
            The current time step (pass-through).
            
        Notes
        -----
        Reset Operations:
            - Iteration counter reset to 0
            - Worst point recalculated for current conditions
            - Controller prepared for new time step optimization
            
        Examples
        --------
        >>> # Called automatically during time series simulation
        >>> current_step = controller.time_step(network, 100)
        >>> print(f"Controller initialized for time step {current_step}")
        """
        self.iteration = 0
        self.dp_min, self.heat_consumer_idx = self.calculate_worst_point(net)
        return time_step

    def is_converged(self, net) -> bool:
        """
        Check if the pressure controller has reached convergence.
        
        Convergence is achieved when the pressure difference at the worst point
        is within the specified tolerance of the target value, or when the
        system is in standby mode (no heat demand).
        
        Parameters
        ----------
        net : pandapipes.pandapipesNet
            The pandapipes network object with current simulation results.
            
        Returns
        -------
        bool
            True if controller has converged, False otherwise.
            
        Notes
        -----
        Convergence Criteria:
            - All heat consumers have zero demand (standby mode), OR
            - Pressure difference at worst point within tolerance
            
        Tolerance Check:
            |current_dp - target_dp| < tolerance
            
        Examples
        --------
        >>> if controller.is_converged(network):
        ...     print("Pressure controller has converged")
        ... else:
        ...     print("Pressure controller still adjusting")
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
        Execute one control step to adjust pump pressures.
        
        This method implements the core control logic, adjusting circulation pump
        pressures based on the pressure difference error at the worst point. It
        handles both normal operation and standby mode switching.
        
        Parameters
        ----------
        net : pandapipes.pandapipesNet
            The pandapipes network object to control.
            
        Notes
        -----
        Control Logic:
            1. Increment iteration counter
            2. Check for standby mode (zero heat demand)
            3. Calculate pressure difference error
            4. Apply proportional control adjustments
            5. Update pump pressure setpoints
            
        Standby Mode:
            - Activated when all consumers have zero demand
            - Sets minimum pump pressures for circulation
            - Reduces energy consumption during idle periods
            
        Proportional Control:
            - Error = target_dp - current_dp
            - Adjustment = error × proportional_gain
            - Applied to both lift and flow pressures
            
        Examples
        --------
        >>> # Called automatically during simulation iterations
        >>> controller.control_step(network)
        >>> 
        >>> # Check pump adjustments
        >>> current_lift = net.circ_pump_pressure["plift_bar"].iloc[0]
        >>> current_flow = net.circ_pump_pressure["p_flow_bar"].iloc[0]
        >>> print(f"Pump pressures: lift={current_lift:.2f}, flow={current_flow:.2f}")
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
    Controller for maintaining minimum supply temperatures at heat consumers.
    
    This controller ensures that each heat consumer receives adequate supply temperature
    for proper operation by dynamically adjusting the return temperature setpoint.
    It is particularly important for cold networks with heat pumps where minimum
    supply temperatures are critical for heat pump operation and building heating.
    
    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object containing all network components.
    heat_consumer_idx : int
        Index of the specific heat consumer to control.
        Each consumer requires its own temperature controller instance.
    min_supply_temperature : float, optional
        Minimum required supply temperature [°C]. Default is 65°C.
        Critical threshold for adequate heat delivery.
    tolerance : float, optional
        Temperature tolerance for convergence [°C]. Default is 2°C.
        Controller considers system converged within this range.
    max_iterations : int, optional
        Maximum iterations per time step before forced convergence. Default is 100.
        Prevents infinite control loops in difficult conditions.
    temperature_adjustment_step : float, optional
        Temperature adjustment step size [°C]. Default is 1°C.
        Controls aggressiveness of temperature corrections.
    debug : bool, optional
        Enable debug output for controller diagnostics. Default is False.
        Useful for troubleshooting control behavior.
    **kwargs
        Additional keyword arguments passed to the base controller.
        
    Attributes
    ----------
    data_source : Optional[Any]
        External data source for time-varying temperature setpoints.
    iteration : int
        Current iteration counter within each time step.
    previous_temperatures : List[float]
        History of recent supply temperatures for stability analysis.
    standard_return_temperature : float
        Original return temperature setpoint for restoration.
        
    Notes
    -----
    Control Strategy:
        1. Monitors actual supply temperature at heat consumer
        2. Compares with minimum required temperature
        3. Adjusts return temperature setpoint to increase supply temperature
        4. Uses weighted averaging for temperature stability
        
    Temperature Control Logic:
        - If supply temperature < minimum: increase return temperature setpoint
        - Higher return temperature → increased mass flow → higher supply temperature
        - Iterative adjustment until minimum temperature achieved
        
    Weighted Averaging:
        - Uses recent temperature history for stable control
        - Prevents oscillations in temperature control
        - Weights recent values more heavily than older ones
        
    Time Series Integration:
        - Supports dynamic minimum temperature requirements
        - Integrates with pandapower data source framework
        - Resets to standard conditions each time step
        
    Examples
    --------
    >>> # Create temperature controller for heat consumer
    >>> temp_controller = MinimumSupplyTemperatureController(
    ...     net=network,
    ...     heat_consumer_idx=0,
    ...     min_supply_temperature=40.0,  # For cold network
    ...     tolerance=1.0,
    ...     debug=True
    ... )
    
    >>> # Add to network control system
    >>> net.controller.loc[len(net.controller)] = [
    ...     temp_controller, True, -1, -1, False, False
    ... ]
    
    >>> # Controller manages temperature during simulation
    >>> pp.pipeflow(net, mode="bidirectional")
    
    See Also
    --------
    BadPointPressureLiftController : Pressure control system
    pandapower.control.basic_controller.BasicCtrl : Base controller class
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
        Initialize controller state for each time step.
        
        This method resets controller parameters and handles time-varying setpoints
        from external data sources. It ensures consistent starting conditions for
        each time step while preserving the ability to restore original settings.
        
        Parameters
        ----------
        net : pandapipes.pandapipesNet
            The pandapipes network object.
        time_step : int
            Current simulation time step index.
            
        Returns
        -------
        int
            The current time step (pass-through).
            
        Notes
        -----
        Reset Operations:
            - Iteration counter reset to 0
            - Temperature history cleared
            - Return temperature restored to standard value
            - Time-varying setpoints updated from data source
            
        Data Source Integration:
            - Checks for external temperature setpoint data
            - Updates minimum temperature requirement dynamically
            - Supports time series temperature control strategies
            
        Examples
        --------
        >>> # Called automatically during time series simulation
        >>> current_step = controller.time_step(network, 50)
        >>> print(f"Temperature controller ready for step {current_step}")
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
        Calculate weighted average of recent supply temperatures.
        
        This method provides temperature smoothing to prevent control oscillations
        by giving more weight to recent temperature measurements while considering
        historical trends for stability.
        
        Returns
        -------
        Optional[float]
            Weighted average temperature [°C], or None if no history available.
            
        Notes
        -----
        Weighting Strategy:
            - Linear weighting: recent values weighted more heavily
            - Weight = position in history (1, 2, 3, ...)
            - Prevents rapid oscillations in control response
            
        Calculation:
            weighted_avg = Σ(temperature[i] × weight[i]) / Σ(weight[i])
            
        Examples
        --------
        >>> # Get smoothed temperature for control
        >>> avg_temp = controller.get_weighted_average_temperature()
        >>> if avg_temp is not None:
        ...     print(f"Weighted average supply temperature: {avg_temp:.1f}°C")
        """
        if len(self.previous_temperatures) == 0:
            return None
            
        weights = np.arange(1, len(self.previous_temperatures) + 1)
        weighted_avg = np.dot(self.previous_temperatures, weights) / weights.sum()
        return weighted_avg

    def control_step(self, net) -> None:
        """
        Execute one temperature control step.
        
        This method implements the core temperature control logic by monitoring
        the actual supply temperature and adjusting the return temperature setpoint
        to ensure minimum temperature requirements are met.
        
        Parameters
        ----------
        net : pandapipes.pandapipesNet
            The pandapipes network object to control.
            
        Notes
        -----
        Control Logic:
            1. Increment iteration counter
            2. Check for standby mode (zero heat demand)
            3. Monitor actual supply temperature
            4. Apply weighted averaging for stability
            5. Adjust return temperature if below minimum
            
        Temperature Adjustment:
            - Increases return temperature setpoint when supply too low
            - Higher return temperature increases mass flow rate
            - Increased mass flow improves heat transfer and supply temperature
            
        Standby Handling:
            - No control action when heat demand is zero
            - Prevents unnecessary adjustments during idle periods
            
        Examples
        --------
        >>> # Called automatically during simulation iterations
        >>> controller.control_step(network)
        >>> 
        >>> # Check temperature adjustment
        >>> current_return = net.heat_consumer["treturn_k"].iloc[0] - 273.15
        >>> print(f"Current return temperature setpoint: {current_return:.1f}°C")
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
        Check if the temperature controller has reached convergence.
        
        Convergence is achieved when the supply temperature meets the minimum
        requirement and the temperature change between iterations is within
        the specified tolerance, or when maximum iterations are reached.
        
        Parameters
        ----------
        net : pandapipes.pandapipesNet
            The pandapipes network object with current simulation results.
            
        Returns
        -------
        bool
            True if controller has converged, False otherwise.
            
        Notes
        -----
        Convergence Criteria:
            1. All heat consumers have zero demand (standby mode), OR
            2. Supply temperature ≥ minimum requirement AND temperature stable, OR
            3. Maximum iterations reached (forced convergence)
            
        Temperature Stability:
            - Compares current temperature with previous iteration
            - Considers converged when change < tolerance
            - Maintains history for weighted averaging
            
        Forced Convergence:
            - Prevents infinite control loops
            - Ensures simulation progress in difficult conditions
            - Logs warning when maximum iterations reached
            
        Examples
        --------
        >>> if controller.is_converged(network):
        ...     print("Temperature controller has converged")
        ... else:
        ...     print("Temperature controller still adjusting")
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