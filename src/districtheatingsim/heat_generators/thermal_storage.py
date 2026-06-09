"""
Thermal Storage Adapter Module
================================

Wrapper around ThermalStorage1D from the thermal-energy-storage-1d package,
exposing the interface required by EnergySystem and the GUI.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging
import numpy as np
from typing import Optional

from thermal_energy_storage_model import (
    ThermalStorage1D,
    StorageConfig,
    StorageInputs,
    CylinderGeometry,
    TruncatedConeGeometry,
    TruncatedPyramidGeometry,
    ConstantAmbientLoss,
    SplitAmbientLoss,
    GroundTemperatureLoss,
    WaterProperties,
    ConstantFluidProperties,
)

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

logger = logging.getLogger(__name__)

# Keys that identify an old (pre-1D) saved config – used for migration detection.
_OLD_CONFIG_KEYS = {"storage_type", "dimensions", "lambda_top", "lambda_side", "lambda_bottom"}


class ThermalStorageAdapter(BaseHeatGenerator):
    """
    Seasonal / large-scale thermal storage backed by ThermalStorage1D.

    Exposes the interface expected by EnergySystem.calculate_mix() and the GUI,
    while delegating all physics to the 1D stratified model.

    Parameters
    ----------
    name : str
        Display name.
    volume : float
        Tank volume [m³].
    height : float
        Tank height [m].
    T_min : float
        Minimum useful temperature for SOC calculation [°C].
    T_max : float
        Maximum operating temperature [°C].
    initial_temp : float
        Uniform initial temperature [°C].
    n_nodes : int
        Number of vertical nodes (default 50).
    geometry_type : str
        ``"cylinder"``, ``"truncated_cone"``, or ``"truncated_pyramid"``.
    loss_model_type : str
        ``"constant"``, ``"split"``, or ``"ground"``.
    U_loss : float
        Overall heat-loss coefficient [W/m²K] (used for ``"constant"``).
    U_top, U_side, U_bottom : float
        Surface-specific U-values [W/m²K] (used for ``"split"``).
    T_ambient : float
        Ambient / ground-surface temperature [°C].
    z_ground : float
        Depth of tank bottom below ground [m] (used for ``"ground"``).
    fluid_type : str
        ``"water"`` (temperature-dependent) or ``"constant"``.
    rho, cp, lambda_fluid : float
        Constant fluid properties (used when ``fluid_type="constant"``).
    solver : str
        ``"implicit"`` (default, unconditionally stable) or ``"explicit"``.
    advection_scheme : str
        ``"tvd"`` (default) or ``"upwind"``.
    buoyancy : bool
        Enable convective mixing correction (default True).
    spez_Investitionskosten : float
        Specific investment cost [€/m³] for cost calculation.
    hours : int
        Simulation horizon [h] (default 8760).
    """

    def __init__(
        self,
        name: str,
        volume: float = 1000.0,
        height: float = 10.0,
        T_min: float = 40.0,
        T_max: float = 95.0,
        initial_temp: float = 60.0,
        n_nodes: int = 50,
        geometry_type: str = "cylinder",
        loss_model_type: str = "constant",
        U_loss: float = 0.3,
        U_top: float = 0.3,
        U_side: float = 0.06,
        U_bottom: float = 0.4,
        T_ambient: float = 10.0,
        z_ground: float = 2.0,
        fluid_type: str = "water",
        rho: float = 977.8,
        cp: float = 4187.0,
        lambda_fluid: float = 0.663,
        solver: str = "implicit",
        advection_scheme: str = "tvd",
        buoyancy: bool = True,
        lambda_eff_factor: float = 5.0,
        spez_Investitionskosten: float = 50.0,
        Nutzungsdauer: int = 30,
        f_Inst: float = 1.0,
        f_W_Insp: float = 1.0,
        Bedienaufwand: float = 0.0,
        hours: int = 8760,
        T_charge: float = 90.0,
        T_discharge_return: float = 50.0,
    ):
        super().__init__(name)

        self.volume = volume
        self.height = height
        self.T_min = T_min
        self.T_max = T_max
        self.initial_temp = initial_temp
        self.n_nodes = n_nodes
        self.geometry_type = geometry_type
        self.loss_model_type = loss_model_type
        self.U_loss = U_loss
        self.U_top = U_top
        self.U_side = U_side
        self.U_bottom = U_bottom
        self.T_ambient = T_ambient
        self.z_ground = z_ground
        self.fluid_type = fluid_type
        self.rho = rho
        self.cp = cp
        self.lambda_fluid = lambda_fluid
        self.solver = solver
        self.advection_scheme = advection_scheme
        self.buoyancy = buoyancy
        self.lambda_eff_factor = lambda_eff_factor
        self.spez_Investitionskosten = spez_Investitionskosten
        # VDI 2067 cost factors. f_W_Insp is the annual maintenance/inspection cost as a
        # percentage of the investment (folded into the annuity by annuity()).
        self.Nutzungsdauer = Nutzungsdauer
        self.f_Inst = f_Inst
        self.f_W_Insp = f_W_Insp
        self.Bedienaufwand = Bedienaufwand
        self.hours = hours
        # Fixed generator-side temperatures for charge/discharge mass-flow calculation.
        # T_charge: temperature at which generators supply heat to storage (independent of
        #   the variable network supply temperature VLT_L, which is the consumer side).
        # T_discharge_return: expected network return temperature used as discharge inlet.
        self.T_charge = T_charge
        self.T_discharge_return = T_discharge_return

        # Build the 1D model
        self._model = self._build_model()
        self._state = self._model.initialize(T_init=initial_temp)

        # Per-timestep result arrays (indexed by t, filled during simulation)
        self.Q_loss = np.zeros(hours)                          # kW  (converted from W)
        self._T_supply = np.full(hours, initial_temp)          # °C – top node (upper)
        self._T_middle = np.full(hours, initial_temp)          # °C – middle node
        self._T_return = np.full(hours, initial_temp)          # °C – bottom node (lower)
        self._soc = np.zeros(hours)
        self._Q_net_storage_flow = np.zeros(hours)  # kW: positive = discharge, negative = charge

        # Performance tracking (filled by calculate_efficiency)
        self.efficiency: float = 0.0
        self.excess_heat: float = 0.0
        self.unmet_demand: float = 0.0

        # Cost results (filled by calculate_costs)
        self.A_N: float = 0.0
        self.WGK: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_model(self) -> ThermalStorage1D:
        geometry = self._make_geometry()
        loss_model = self._make_loss_model()
        fluid = WaterProperties() if self.fluid_type == "water" else ConstantFluidProperties(
            rho=self.rho, cp=self.cp, lambda_fluid=self.lambda_fluid
        )
        config = StorageConfig(
            volume=self.volume,
            height=self.height,
            n_nodes=self.n_nodes,
            geometry=geometry,
            loss_model=loss_model,
            fluid=fluid,
            solver=self.solver,
            advection_scheme=self.advection_scheme,
            buoyancy=self.buoyancy,
            lambda_eff_factor=self.lambda_eff_factor,
        )
        return ThermalStorage1D(config)

    def _make_geometry(self):
        if self.geometry_type == "truncated_cone":
            # Infer top/bottom radius from volume and height (frustum with 20% taper)
            r_mean = (self.volume * 3 / (np.pi * self.height)) ** (1 / 3)
            return TruncatedConeGeometry(r_bottom=r_mean * 1.1, r_top=r_mean * 0.9, height=self.height)
        elif self.geometry_type == "truncated_pyramid":
            a_mean = (self.volume / self.height) ** 0.5
            return TruncatedPyramidGeometry(
                a_bottom=a_mean * 1.1, b_bottom=a_mean * 1.1,
                a_top=a_mean * 0.9, b_top=a_mean * 0.9,
                height=self.height,
            )
        else:
            radius = (self.volume / (np.pi * self.height)) ** 0.5
            return CylinderGeometry(radius=radius, height=self.height)

    def _make_loss_model(self):
        if self.loss_model_type == "split":
            # SplitAmbientLoss uses U_lid (top) and U_wall (side+bottom averaged)
            U_wall = (self.U_side + self.U_bottom) / 2.0
            return SplitAmbientLoss(U_lid=self.U_top, U_wall=U_wall, T_ambient=self.T_ambient)
        elif self.loss_model_type == "ground":
            return GroundTemperatureLoss(
                U_loss=self.U_top,
                burial_depth=self.z_ground,
                T_surface=self.T_ambient,
                T_deep=self.T_ambient - 2.0,
            )
        else:
            return ConstantAmbientLoss(U_loss=self.U_loss, T_ambient=self.T_ambient)

    def _cp_effective(self) -> float:
        """Return cp [J/kgK] at current mean storage temperature."""
        if self.fluid_type == "water":
            return WaterProperties().cp(self._state.T_mean)
        return self.cp

    def _rho_effective(self) -> float:
        """Return rho [kg/m³] at current mean storage temperature."""
        if self.fluid_type == "water":
            return WaterProperties().rho(self._state.T_mean)
        return self.rho

    # ------------------------------------------------------------------
    # EnergySystem interface
    # ------------------------------------------------------------------

    def simulate_stratified_temperature_mass_flows(
        self,
        t: int,
        Q_in: float,
        Q_out: float,
        T_Q_in_flow: float,   # noqa: ARG002 – network supply temp, kept for interface compat
        T_Q_out_return: float,  # noqa: ARG002 – network return temp, kept for interface compat
    ) -> None:
        """
        Advance storage by one timestep (dt = 3600 s).

        Parameters
        ----------
        t : int
            Current simulation timestep index.
        Q_in : float
            Total heat delivered by all generators [kW].
        Q_out : float
            Total network heat demand [kW].
        T_Q_in_flow : float
            Network supply temperature passed by EnergySystem [°C].
            Not used for mass-flow calculation — the fixed ``self.T_charge``
            (generator-side temperature) is used instead, so that a variable
            network supply curve ("Gleitung") does not inadvertently cool the
            storage in summer.
        T_Q_out_return : float
            Network return temperature passed by EnergySystem [°C].
            Not used directly — ``self.T_discharge_return`` is used instead.

        Notes
        -----
        The storage is either charging or discharging in a given timestep:

        * **Charging** (generators over-produce): excess ``Q_in − Q_out``
          enters the storage at the top at ``self.T_charge`` (fixed generator
          supply temperature, e.g. 90 °C).
        * **Discharging** (demand exceeds generation): deficit ``Q_out − Q_in``
          is drawn from the storage top; cold return enters at the bottom at
          ``self.T_discharge_return``.

        Port assignments (StorageInputs.two_port):
          - charge_in     : z = height (top),   m_dot > 0, T_in = T_charge
          - charge_out    : z = 0 (bottom),      m_dot < 0  → outlet T = T_bottom
          - discharge_in  : z = 0 (bottom),      m_dot > 0, T_in = T_discharge_return
          - discharge_out : z = height (top),    m_dot < 0  → outlet T = T_top
        """
        cp = self._cp_effective()

        # Net heat flow: positive → net charge into storage, negative → net discharge
        Q_net = Q_in - Q_out
        Q_charge = max(0.0, Q_net)      # kW entering storage (generators over-produce)
        Q_discharge = max(0.0, -Q_net)  # kW leaving storage (demand exceeds generation)

        # Use fixed generator-side temperature for charging (independent of the variable
        # network supply temperature T_Q_in_flow, which represents the consumer side and
        # can drop in summer due to "Gleitung"). This prevents the storage from being
        # cooled down in summer when VLT_L < T_storage_top.
        T_charge_in = self.T_charge
        T_discharge_in = self.T_discharge_return  # fixed return temperature for discharge

        # Mass flows [kg/s]
        # Charge loop: generator supplies at T_charge_in at top, return exits at bottom.
        dT_charge = max(T_charge_in - self._state.T_bottom, 0.5)
        m_dot_charge = (Q_charge * 1000.0) / (cp * dT_charge) if Q_charge > 0 else 0.0

        # Discharge loop: cold return enters at bottom at T_discharge_in, hot exits at top.
        dT_discharge = max(self._state.T_top - T_discharge_in, 0.5)
        m_dot_discharge = (Q_discharge * 1000.0) / (cp * dT_discharge) if Q_discharge > 0 else 0.0

        inputs = StorageInputs.two_port(
            m_dot_charge=m_dot_charge,
            T_charge_in=T_charge_in,
            m_dot_discharge=m_dot_discharge,
            T_discharge_in=T_discharge_in,
            height=self.height,
        )

        outputs = self._model.step(self._state, dt=3600.0, inputs=inputs)
        self._state = outputs.state

        # Store results (W → kW for Q_loss)
        self.Q_loss[t] = outputs.Q_loss / 1000.0
        # Temperatures read from state — independent of port ordering.
        temps = self._state.temperatures
        n = len(temps)
        self._T_supply[t] = self._state.T_top
        self._T_middle[t] = float(temps[n // 2])
        self._T_return[t] = self._state.T_bottom
        self._soc[t] = self._model.get_soc(self._state, self.T_min, self.T_max)
        # Net storage flow [kW]: positive = discharge (storage helps network),
        # negative = charge (generators fill storage).
        self._Q_net_storage_flow[t] = Q_out - Q_in

    @property
    def Q_net_storage_flow(self) -> np.ndarray:
        """Net heat flow [kW]: positive = discharge, negative = charge."""
        return self._Q_net_storage_flow

    def current_storage_temperatures(self, t: int) -> tuple:
        """
        Return (upper_temp, lower_temp) [°C] at timestep t, used by generator
        control strategies via EnergySystem.calculate_mix().

        upper_temp = T_top  (hot side – used for charge_on threshold).
        lower_temp = T_middle (middle node – strategy turn-off threshold,
                    better indicator of overall charge state than T_bottom).
        """
        return float(self._T_supply[t]), float(self._T_middle[t])

    def current_storage_state(self, t: int, T_Q_out_return: float, T_Q_in_flow: float) -> tuple:
        """
        Return (storage_fraction, available_energy_kWh, max_energy_kWh) at timestep t.
        """
        soc = float(self._soc[t])
        cp = self._cp_effective()
        rho = self._rho_effective()
        max_energy = self.volume * rho * cp * max(T_Q_in_flow - T_Q_out_return, 0) / 3.6e6
        available_energy = soc * max_energy
        return soc, available_energy, max_energy

    def calculate_efficiency(self, Q_in_array: np.ndarray) -> None:
        """Compute round-trip efficiency and store on self.efficiency."""
        Q_in_total = float(np.sum(Q_in_array))
        Q_loss_total = float(np.sum(self.Q_loss))
        if Q_in_total > 0:
            self.efficiency = max(0.0, (Q_in_total - Q_loss_total) / Q_in_total)
        else:
            self.efficiency = 0.0

    # ------------------------------------------------------------------
    # Cost calculation
    # ------------------------------------------------------------------

    def calculate_costs(self, Wärmemenge_MWh: float, economic_parameters: dict) -> None:
        """
        Compute the storage's annuity and heat-generation cost (VDI 2067).

        Capital-bound costs come from the tank investment (``volume`` ×
        ``spez_Investitionskosten``); the annual maintenance share is the
        ``f_W_Insp`` factor folded into the annuity. There are no demand-bound
        (fuel) costs – the energy to cover the storage losses is paid for on the
        generator side, so charging it here too would double-count.

        :param Wärmemenge_MWh: Annual heat discharged from the storage [MWh].
        :param economic_parameters: Shared economic-parameters dict.
        """
        self.load_economic_parameters(economic_parameters)
        self.Wärmemenge_MWh = Wärmemenge_MWh
        self.Investitionskosten = self.volume * self.spez_Investitionskosten
        self.A_N = self.annuity(
            initial_investment_cost=self.Investitionskosten,
            asset_lifespan_years=self.Nutzungsdauer,
            installation_factor=self.f_Inst,
            maintenance_inspection_factor=self.f_W_Insp,
            operational_effort_h=self.Bedienaufwand,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T,
            annual_energy_demand=0,
            energy_cost_per_unit=0,
            annual_revenue=0,
            hourly_rate=self.stundensatz,
        )
        self.WGK = self.A_N / Wärmemenge_MWh if Wärmemenge_MWh > 0 else float("inf")

    # ------------------------------------------------------------------
    # GUI helpers
    # ------------------------------------------------------------------

    def get_display_text(self) -> str:
        return (
            f"Thermal Storage (1D): {self.volume:.0f} m³, h={self.height:.1f} m, "
            f"T {self.T_min:.0f}–{self.T_max:.0f} °C, nodes={self.n_nodes}"
        )

    def extract_tech_data(self) -> tuple:
        tech_type = f"ThermalStorage1D ({self.geometry_type})"
        dimensions = f"V={self.volume:.0f} m³, h={self.height:.1f} m, nodes={self.n_nodes}"
        return tech_type, dimensions, getattr(self, "WGK", 0), getattr(self, "A_N", 0)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "tech_type": self.__class__.__name__,
            "name": self.name,
            "volume": self.volume,
            "height": self.height,
            "T_min": self.T_min,
            "T_max": self.T_max,
            "initial_temp": self.initial_temp,
            "n_nodes": self.n_nodes,
            "geometry_type": self.geometry_type,
            "loss_model_type": self.loss_model_type,
            "U_loss": self.U_loss,
            "U_top": self.U_top,
            "U_side": self.U_side,
            "U_bottom": self.U_bottom,
            "T_ambient": self.T_ambient,
            "z_ground": self.z_ground,
            "fluid_type": self.fluid_type,
            "rho": self.rho,
            "cp": self.cp,
            "lambda_fluid": self.lambda_fluid,
            "solver": self.solver,
            "advection_scheme": self.advection_scheme,
            "buoyancy": self.buoyancy,
            "lambda_eff_factor": self.lambda_eff_factor,
            "spez_Investitionskosten": self.spez_Investitionskosten,
            "Nutzungsdauer": self.Nutzungsdauer,
            "f_Inst": self.f_Inst,
            "f_W_Insp": self.f_W_Insp,
            "Bedienaufwand": self.Bedienaufwand,
            "hours": self.hours,
            "T_charge": self.T_charge,
            "T_discharge_return": self.T_discharge_return,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional["ThermalStorageAdapter"]:
        """
        Deserialize from a saved dict.

        Returns None and logs a warning when an old-format config is detected,
        so the caller can inform the user to re-configure the storage.
        """
        if _OLD_CONFIG_KEYS.intersection(data.keys()):
            logger.warning(
                "Thermal storage config '%s' uses an outdated format and cannot be loaded. "
                "Please re-configure the storage in the GUI.",
                data.get("name", "<unknown>"),
            )
            return None

        data = {k: v for k, v in data.items() if k != "tech_type"}
        return cls(**data)


# ---------------------------------------------------------------------------
# Buffer storage for generator-attached short-term tanks (CHP, BiomassBoiler)
# ---------------------------------------------------------------------------

class BufferStorage:
    """
    Simple buffer tank backed by ThermalStorage1D.

    Replaces the inline scalar energy-bucket (speicher_fill / speicher_kapazitaet)
    previously embedded in CHP and BiomassBoiler dispatch loops.

    Parameters
    ----------
    volume : float
        Tank volume [m³].
    T_flow : float
        Generator supply temperature [°C] (sets T_max for SOC).
    T_return : float
        Generator return temperature [°C] (sets T_min for SOC).
    U_loss : float
        Heat-loss coefficient [W/m²K] (default 0.5, well-insulated steel tank).
    T_ambient : float
        Ambient temperature [°C] (default 15).
    """

    def __init__(
        self,
        volume: float,
        T_flow: float = 90.0,
        T_return: float = 60.0,
        U_loss: float = 0.5,
        T_ambient: float = 15.0,
    ):
        self.volume = volume
        self.T_flow = T_flow
        self.T_return = T_return
        self.T_min = T_return
        self.T_max = T_flow

        # Derive a reasonable height from volume (aspect ratio ~2: h = (2V/π)^(1/3))
        height = (2 * volume / np.pi) ** (1 / 3)

        config = StorageConfig(
            volume=volume,
            height=height,
            n_nodes=10,
            loss_model=ConstantAmbientLoss(U_loss=U_loss, T_ambient=T_ambient),
            fluid=WaterProperties(),
            solver="implicit",
            advection_scheme="tvd",
            buoyancy=True,
        )
        self._model = ThermalStorage1D(config)
        self._state = self._model.initialize(T_init=(T_flow + T_return) / 2.0)
        self._height = height

        self._last_Q_loss_kw: float = 0.0

        # Per-timestep history (appended on every step() call)
        self.soc_history: list[float] = []
        self.T_top_history: list[float] = []
        self.T_middle_history: list[float] = []
        self.T_bottom_history: list[float] = []
        self.Q_loss_history: list[float] = []
        self.Q_net_history: list[float] = []

    def step(self, Q_net_kw: float, dt_h: float = 1.0) -> None:
        """
        Advance buffer by one timestep.

        Parameters
        ----------
        Q_net_kw : float
            Net power into the tank [kW]. Positive = charging, negative = discharging.
        dt_h : float
            Timestep duration [h] (default 1).
        """
        dt = dt_h * 3600.0
        cp = WaterProperties().cp(self._state.T_mean)
        dT = max(self.T_max - self.T_min, 1.0)
        m_dot = abs(Q_net_kw) * 1000.0 / (cp * dT)

        if Q_net_kw >= 0:
            inputs = StorageInputs.two_port(
                m_dot_charge=m_dot, T_charge_in=self.T_flow,
                m_dot_discharge=0.0, T_discharge_in=self.T_return,
                height=self._height,
            )
        else:
            inputs = StorageInputs.two_port(
                m_dot_charge=0.0, T_charge_in=self.T_flow,
                m_dot_discharge=m_dot, T_discharge_in=self.T_return,
                height=self._height,
            )

        outputs = self._model.step(self._state, dt=dt, inputs=inputs)
        self._state = outputs.state
        self._last_Q_loss_kw = outputs.Q_loss / 1000.0

        # Record history
        temps = self._state.temperatures
        n = len(temps)
        self.soc_history.append(self._model.get_soc(self._state, self.T_min, self.T_max))
        self.T_top_history.append(float(self._state.T_top))
        self.T_middle_history.append(float(temps[n // 2]))
        self.T_bottom_history.append(float(self._state.T_bottom))
        self.Q_loss_history.append(self._last_Q_loss_kw)
        self.Q_net_history.append(Q_net_kw)

    def reset_history(self) -> None:
        """Clear all per-timestep history lists (call after pre-charge, before main loop)."""
        self.soc_history.clear()
        self.T_top_history.clear()
        self.T_middle_history.clear()
        self.T_bottom_history.clear()
        self.Q_loss_history.clear()
        self.Q_net_history.clear()

    def get_soc(self) -> float:
        """State of charge in [0, 1]."""
        return self._model.get_soc(self._state, self.T_min, self.T_max)

    def get_capacity_kwh(self) -> float:
        """Usable capacity [kWh]."""
        cp = WaterProperties().cp((self.T_max + self.T_min) / 2)
        rho = WaterProperties().rho((self.T_max + self.T_min) / 2)
        return self.volume * rho * cp * (self.T_max - self.T_min) / 3.6e6

    def get_heat_loss_kw(self) -> float:
        """Heat loss during last timestep [kW]."""
        return self._last_Q_loss_kw
