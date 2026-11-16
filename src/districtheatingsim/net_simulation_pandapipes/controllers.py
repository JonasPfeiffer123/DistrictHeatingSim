"""
Controllers Module
==================

This module provides specialized controllers for district heating network operation using
the pandapipes framework.

:author: M.Eng. Jonas Pfeiffer

It implements advanced control strategies for pressure management,
temperature regulation, and system optimization to ensure efficient and reliable network
operation under varying load conditions.

The controllers integrate with pandapower's control system architecture and support both
steady-state and time-series simulations. They handle complex control scenarios including
bad point pressure control, minimum temperature enforcement, and multi-producer coordination
in district heating systems.
"""

import logging

import numpy as np
from pandapower.control.basic_controller import BasicCtrl
from pandapower.control.controller.const_control import ConstControl

from districtheatingsim.constants import KELVIN_OFFSET

logger = logging.getLogger(__name__)

# Proportional gain of the bad-point pump controller (see BadPointPressureLiftController).
# Nets saved before BACKLOG G1 carry the old default 0.2 and are upgraded on load
# (net_migration.migrate_loaded_net).
DEFAULT_PUMP_CONTROLLER_GAIN = 0.6
LEGACY_PUMP_CONTROLLER_GAIN = 0.2

# Smallest supply/return difference the minimum-supply-temperature controller raises a heat
# consumer's return temperature to [K] (BACKLOG G11).
DEFAULT_MIN_TEMPERATURE_SPREAD = 2.0
# A return temperature this close to its limit counts as at the limit [K]
RETURN_LIMIT_TOLERANCE = 0.1
# Range of the supply-temperature rise per K of return raise the secant step assumes (the lower
# bound caps the step at 20 times the deficit)
MIN_SUPPLY_RESPONSE = 0.05
MAX_SUPPLY_RESPONSE = 0.9


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
    :param proportional_gain: Proportional gain factor, defaults to 0.6
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

       Every control iteration is a full pipeflow. The bad-point Δp follows the pump lift
       almost 1:1, so the gain sets how much of the error is removed per iteration: 0.2 needed
       ~3.9 pipeflows per time step, 0.6 needs ~1.9 with the same results (BACKLOG G1). Gain
       1.0 lands at the edge of the tolerance band.
    """

    def __init__(
        self,
        net,
        circ_pump_pressure_idx: int = 0,
        target_dp_min_bar: float = 1.0,
        tolerance: float = 0.2,
        proportional_gain: float = DEFAULT_PUMP_CONTROLLER_GAIN,
        min_plift: float = 1.5,
        min_pflow: float = 3.5,
        **kwargs,
    ):
        super().__init__(net, **kwargs)
        self.circ_pump_pressure_idx = circ_pump_pressure_idx
        self.target_dp_min_bar = target_dp_min_bar
        self.tolerance = tolerance
        self.proportional_gain = proportional_gain
        self.min_plift = min_plift
        self.min_pflow = min_pflow
        self.iteration = 0

        # Initialize worst point calculation
        self.dp_min, self.heat_consumer_idx = self.calculate_worst_point(net)

    def calculate_worst_point(self, net) -> tuple[float, int]:
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
            net.res_heat_consumer["p_to_bar"],
            strict=False,
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

        # The worst point is taken from the current results on every iteration. It used to be fixed
        # when the controller was created (and per time step): after the diameter sizing the
        # initialisation regulated a station that was no longer the worst - in Zittau another one
        # ended at -1.09 bar, its control valve "pumping" against the return pressure (UT-M12).
        self.dp_min, self.heat_consumer_idx = self.calculate_worst_point(net)
        current_dp_bar = self.dp_min

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
            logger.debug("No heat flow detected. Switching to standby mode.")
            net.circ_pump_pressure.loc[:, "plift_bar"] = self.min_plift
            net.circ_pump_pressure.loc[:, "p_flow_bar"] = self.min_pflow
            return super().control_step(net)

        # Calculate control parameters
        current_dp_bar = (
            net.res_heat_consumer["p_from_bar"].at[self.heat_consumer_idx]
            - net.res_heat_consumer["p_to_bar"].at[self.heat_consumer_idx]
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

        net.circ_pump_pressure.at[self.circ_pump_pressure_idx, "plift_bar"] = new_plift
        net.circ_pump_pressure.at[self.circ_pump_pressure_idx, "p_flow_bar"] = new_pflow

        return super().control_step(net)


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
    :param temperature_adjustment_step: Smallest raise of the return temperature per iteration [K],
        defaults to 1.0; a larger supply temperature deficit is raised by the deficit
    :type temperature_adjustment_step: float
    :param min_temperature_spread: Smallest difference between supply and return temperature the
        return is raised to [K], defaults to ``DEFAULT_MIN_TEMPERATURE_SPREAD``; if the minimum is not
        met there, it cannot be met at this hour and the controller stops
    :type min_temperature_spread: float
    :param debug: Log every control decision (INFO level), defaults to False
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
       A minimum that cannot be met (return at its limit, or ``max_iterations`` reached) is
       accepted for the hour instead of stopping the time series.
    """

    def __init__(
        self,
        net,
        heat_consumer_idx: int,
        min_supply_temperature: float = 65.0,
        tolerance: float = 2.0,
        max_iterations: int = 100,
        temperature_adjustment_step: float = 1.0,
        debug: bool = False,
        min_temperature_spread: float = DEFAULT_MIN_TEMPERATURE_SPREAD,
        **kwargs,
    ):
        super().__init__(net, **kwargs)
        self.heat_consumer_idx = heat_consumer_idx
        self.min_supply_temperature = min_supply_temperature
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.temperature_adjustment_step = temperature_adjustment_step
        self.min_temperature_spread = min_temperature_spread
        self.debug = debug

        # Controller state variables
        self.data_source = None
        self.iteration = 0
        self.previous_temperatures: list[float] = []
        self.return_temperature_limited = False
        self.previous_raise: tuple[float, float] | None = None  # (return, supply) before the last raise

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
           Resets iteration counter and temperature history. Undoes the previous step's raise of the
           return temperature: a return-temperature ConstControl of the heat consumer does so by
           writing its setpoint for the step; without one the setpoint of the first step is restored.
           Updates min_supply_temperature from data_source if available.
        """
        self.iteration = 0
        self.previous_temperatures = []
        self.return_temperature_limited = False
        self.previous_raise = None

        if time_step == 0:
            self.return_temperature_has_profile = self._has_return_temperature_profile(net)
            # Store original return temperature for restoration
            self.standard_return_temperature = net.heat_consumer["treturn_k"].at[self.heat_consumer_idx]
        elif not getattr(self, "return_temperature_has_profile", False):
            # Restore standard return temperature at start of each step. Not with a return-temperature
            # profile: that may be time-dependent (building temperatures, BACKLOG C47), and depending on
            # the controller order the restore overwrote it with the value of the first step.
            net.heat_consumer.at[self.heat_consumer_idx, "treturn_k"] = self.standard_return_temperature

        # Update minimum temperature from external data source
        if self.data_source is not None:
            self.min_supply_temperature = self.data_source.df.at[time_step, "min_supply_temperature"]

        return time_step

    def _has_return_temperature_profile(self, net) -> bool:
        """Whether an in-service ConstControl sets this heat consumer's return temperature."""
        if "controller" not in net:
            return False
        return any(
            isinstance(ctrl, ConstControl)
            and ctrl.element == "heat_consumer"
            and ctrl.variable == "treturn_k"
            and self.heat_consumer_idx in np.atleast_1d(ctrl.element_index)
            for ctrl, in_service in zip(net.controller["object"], net.controller["in_service"], strict=True)
            if in_service
        )

    def get_weighted_average_temperature(self) -> float | None:
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
           Increases return temp if supply < minimum (higher return → higher mass flow → higher supply),
           at least by ``temperature_adjustment_step``: first by the supply temperature deficit, then
           by a secant step (deficit / supply rise per K of the previous raise). 1 K steps needed up to
           55 pipeflows per hour at summer loads, where the supply rises by only ~0.15 K per K
           (BACKLOG G11). The return stays ``min_temperature_spread`` below the supply; closer, the
           mass flow grows without bound and the pipeflow diverges.
        """
        self.iteration += 1

        # Handle standby mode - no heat demand
        if all(net.heat_consumer["qext_w"] == 0):
            if self.debug:
                logger.info("No heat flow detected. Switching to standby mode.")
            return super().control_step(net)

        # Get current inlet temperature
        T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - KELVIN_OFFSET
        current_T_in = T_in

        # Apply weighted averaging for stability
        weighted_avg_T_in = self.get_weighted_average_temperature()
        if weighted_avg_T_in is not None:
            current_T_in = weighted_avg_T_in

        # Adjust return temperature if supply temperature too low
        if current_T_in < self.min_supply_temperature:
            T_out = net.heat_consumer.at[self.heat_consumer_idx, "treturn_k"] - KELVIN_OFFSET
            # The limit rises with the supply temperature the raise brings; once the return has
            # reached it, the minimum cannot be met at this hour.
            spread = getattr(self, "min_temperature_spread", DEFAULT_MIN_TEMPERATURE_SPREAD)
            limit = T_in - spread
            if T_out >= limit - RETURN_LIMIT_TOLERANCE:
                self.return_temperature_limited = True
            else:
                deficit = self.min_supply_temperature - T_in
                # Supply rise per K of return raise, measured on the previous raise of this time
                # step: nearly constant (larger mass flow, smaller loss on the way)
                response = None
                previous = getattr(self, "previous_raise", None)
                if previous is not None:
                    raised, gained = T_out - previous[0], T_in - previous[1]
                    if raised > 0 and gained > 0:
                        response = min(max(gained / raised, MIN_SUPPLY_RESPONSE), MAX_SUPPLY_RESPONSE)
                step = deficit / response if response is not None and deficit > 0 else deficit
                step = max(self.temperature_adjustment_step, step)
                if response is not None:
                    # aim at the return temperature where the rising supply and its limit meet
                    limit = (T_in - response * T_out - spread) / (1 - response)
                self.previous_raise = (float(T_out), float(T_in))
                T_out = min(T_out + step, limit)
                net.heat_consumer.at[self.heat_consumer_idx, "treturn_k"] = T_out + KELVIN_OFFSET

            if self.debug:
                logger.info(
                    f"Minimum supply temperature not met. Adjusted target output temperature to "
                    f"{T_out:.1f}°C{' (at its limit)' if self.return_temperature_limited else ''}."
                )

        return super().control_step(net)

    def is_converged(self, net) -> bool:
        """
        Check convergence: standby, temperature met and stable, or max iterations.

        :param net: Pandapipes network with current simulation results
        :type net: pandapipes.pandapipesNet
        :return: True if converged, False otherwise
        :rtype: bool

        .. note::
           Converged if: all qext_w == 0 (standby) OR (supply >= minimum AND change < tolerance)
           OR return temperature at its limit OR max iterations reached. Maintains temperature
           history for weighted averaging.
        """
        # Standby mode - all consumers inactive
        if all(net.heat_consumer["qext_w"] == 0):
            return True

        # Get current temperatures and system state
        current_T_out = net.res_heat_consumer["t_to_k"].at[self.heat_consumer_idx] - KELVIN_OFFSET
        current_T_in = net.res_heat_consumer["t_from_k"].at[self.heat_consumer_idx] - KELVIN_OFFSET
        previous_T_in = self.previous_temperatures[-1] if self.previous_temperatures else None
        current_mass_flow = net.res_heat_consumer["mdot_from_kg_per_s"].at[self.heat_consumer_idx]

        # Check temperature stability
        temperature_change = abs(current_T_in - previous_T_in) if previous_T_in is not None else float("inf")
        converged_T_in = temperature_change < self.tolerance

        # Update temperature history (keep last 2 values)
        self.previous_temperatures.append(current_T_in)
        if len(self.previous_temperatures) > 2:
            self.previous_temperatures.pop(0)

        # Check minimum temperature requirement
        if current_T_in < self.min_supply_temperature:
            if self.debug:
                logger.info(
                    f"Supply temperature not met for heat_consumer_idx: {self.heat_consumer_idx}. "
                    f"current_temperature_in: {current_T_in:.1f}°C, "
                    f"current_temperature_out: {current_T_out:.1f}°C, "
                    f"current_mass_flow: {current_mass_flow:.3f} kg/s"
                )
            # Not reachable at this hour: accept it (the time series reports it) instead of raising
            # the return until the pipeflow fails or pandapower stops the whole time series.
            return getattr(self, "return_temperature_limited", False) or self.iteration >= self.max_iterations

        # Check temperature stability convergence
        if converged_T_in:
            if self.debug:
                logger.info(
                    f"Controller converged: heat_consumer_idx: {self.heat_consumer_idx}, "
                    f"current_temperature_in: {current_T_in:.1f}°C, "
                    f"current_temperature_out: {current_T_out:.1f}°C, "
                    f"current_mass_flow: {current_mass_flow:.3f} kg/s"
                )
            return True

        # Forced convergence after maximum iterations
        if self.iteration >= self.max_iterations:
            if self.debug:
                logger.info(f"Max iterations reached for heat_consumer_idx: {self.heat_consumer_idx}")
            return True

        return False
