"""
Combined Heat and Power (CHP) System Module
============================================

CHP system modeling with thermal/electrical efficiency, storage integration and electricity revenue calculation.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from districtheatingsim.constants import (
    BEW_SUBSIDY_SHARE,
    CO2_FACTOR_ELECTRICITY,
    CO2_FACTOR_GAS,
    CO2_FACTOR_WOOD,
    PRIMARY_ENERGY_FACTOR_GAS,
    PRIMARY_ENERGY_FACTOR_WOOD,
)
from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy
from districtheatingsim.heat_generators.thermal_storage import BufferStorage


class CHP(BaseHeatGenerator):
    """
    Combined Heat and Power system with storage.

    :param name: Unique identifier (prefix "BHKW" for gas, "Holzgas-BHKW" for biomass)
    :type name: str
    :param th_Leistung_kW: Nominal thermal power [kW]
    :type th_Leistung_kW: float
    :param spez_Investitionskosten_GBHKW: Gas CHP investment costs [€/kW], defaults to 1500
    :type spez_Investitionskosten_GBHKW: float, optional
    :param el_Wirkungsgrad: Electrical efficiency [-], defaults to 0.33
    :type el_Wirkungsgrad: float, optional
    :param KWK_Wirkungsgrad: Combined efficiency [-], defaults to 0.9
    :type KWK_Wirkungsgrad: float, optional
    :param speicher_aktiv: Enable thermal storage, defaults to False
    :type speicher_aktiv: bool, optional

    .. note::
       Supports BEW/KWKG subsidies and electricity revenue calculations.
    """
    
    def __init__(self, name: str, th_Leistung_kW: float, spez_Investitionskosten_GBHKW: float = 1500, 
                 spez_Investitionskosten_HBHKW: float = 1850, el_Wirkungsgrad: float = 0.33, 
                 KWK_Wirkungsgrad: float = 0.9, min_Teillast: float = 0.7, speicher_aktiv: bool = False, 
                 Speicher_Volumen_BHKW: float = 20, T_vorlauf: float = 90, T_ruecklauf: float = 60, 
                 initial_fill: float = 0.0, min_fill: float = 0.2, max_fill: float = 0.8, 
                 spez_Investitionskosten_Speicher: float = 750, active: bool = True,
                 opt_BHKW_min: float = 0, opt_BHKW_max: float = 1000,
                 opt_BHKW_Speicher_min: float = 0, opt_BHKW_Speicher_max: float = 100,
                 fuel_type: str | None = None):
        super().__init__(name)
        self.th_Leistung_kW = th_Leistung_kW
        self.spez_Investitionskosten_GBHKW = spez_Investitionskosten_GBHKW
        self.spez_Investitionskosten_HBHKW = spez_Investitionskosten_HBHKW
        self.el_Wirkungsgrad = el_Wirkungsgrad
        self.KWK_Wirkungsgrad = KWK_Wirkungsgrad
        self.min_Teillast = min_Teillast
        self.speicher_aktiv = speicher_aktiv
        self.Speicher_Volumen_BHKW = Speicher_Volumen_BHKW
        self.T_vorlauf = T_vorlauf
        self.T_ruecklauf = T_ruecklauf
        self.initial_fill = initial_fill
        self.min_fill = min_fill
        self.max_fill = max_fill
        self.spez_Investitionskosten_Speicher = spez_Investitionskosten_Speicher
        self.active = active
        self.opt_BHKW_min = opt_BHKW_min
        self.opt_BHKW_max = opt_BHKW_max
        self.opt_BHKW_Speicher_min = opt_BHKW_Speicher_min
        self.opt_BHKW_Speicher_max = opt_BHKW_Speicher_max
        
        # Calculate derived performance parameters
        self.thermischer_Wirkungsgrad = self.KWK_Wirkungsgrad - self.el_Wirkungsgrad
        self.el_Leistung_Soll = self.th_Leistung_kW / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
        
        # System specifications based on CHP technology
        self.Nutzungsdauer = 15  # Operational lifespan [years]
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 6, 2, 0  # Installation and maintenance factors
        
        # Fuel keyed off an explicit attribute, not the display name (BACKLOG C6).
        # Inferred from the name for backwards compatibility; defaults to gas.
        self.fuel_type = fuel_type if fuel_type is not None else self._infer_fuel_type(name)

        # Technology-specific emission and energy factors
        if self.fuel_type == "wood_gas":
            self.co2_factor_fuel = CO2_FACTOR_WOOD  # tCO2/MWh for wood pellets
            self.primärenergiefaktor = PRIMARY_ENERGY_FACTOR_WOOD  # Primary energy factor for biomass
        else:  # gas
            self.co2_factor_fuel = CO2_FACTOR_GAS  # tCO2/MWh for natural gas
            self.primärenergiefaktor = PRIMARY_ENERGY_FACTOR_GAS  # Primary energy factor for gas

        self.co2_factor_electricity = CO2_FACTOR_ELECTRICITY  # tCO2/MWh for grid electricity displacement
        self.Anteil_Förderung_BEW = BEW_SUBSIDY_SHARE  # BEW subsidy percentage (40%)

        # Initialize control strategy
        self.strategy = CHPStrategy(75, 70)

        # Build buffer storage model if active
        self.buffer: BufferStorage | None = (
            BufferStorage(
                volume=self.Speicher_Volumen_BHKW,
                T_flow=self.T_vorlauf,
                T_return=self.T_ruecklauf,
            )
            if self.speicher_aktiv else None
        )

        # Initialize operational arrays
        self.init_operation(8760)

    @staticmethod
    def _infer_fuel_type(name: str) -> str:
        """Map a CHP display name to its fuel. Unknown names default to ``"gas"``.

        :param name: Instance name (e.g. ``"BHKW_1"`` / ``"Holzgas-BHKW_1"``).
        :return: ``"wood_gas"`` for Holzgas units, otherwise ``"gas"``.
        """
        return "wood_gas" if name.startswith("Holzgas-BHKW") else "gas"

    def _resolve_fuel_type(self) -> str:
        """Fuel type, falling back to name inference for pre-C6 saved objects
        (``from_dict`` bypasses ``__init__``, so old dicts lack ``fuel_type``)."""
        return getattr(self, "fuel_type", None) or self._infer_fuel_type(self.name)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational arrays.

        :param hours: Simulation hours
        :type hours: int
        """
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours, dtype=float)
        self.el_Leistung_kW = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Strommenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        # Pre-initialize buffer storage arrays so they exist even when
        # simulate_storage() is skipped (e.g. per-timestep dispatch path).
        if self.speicher_aktiv:
            self.Wärmeleistung_Speicher_kW = np.zeros(hours, dtype=float)
            self.Speicher_Fuellstand = np.zeros(hours, dtype=float)

        self.calculated = False  # Flag to indicate if calculation is complete

    def simulate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate CHP operation without storage (heat-led mode).

        :param Last_L: Thermal load [kW]
        :type Last_L: numpy.ndarray

        .. note::
           Heat-led with minimum part-load constraints.
        """
        # Determine operational periods based on minimum part-load constraint
        self.betrieb_mask = Last_L >= self.th_Leistung_kW * self.min_Teillast
        
        # Calculate thermal output limited by CHP capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.th_Leistung_kW
        )
        
        # Calculate electrical output based on thermal output and efficiency ratio
        self.el_Leistung_kW[self.betrieb_mask] = (
            self.Wärmeleistung_kW[self.betrieb_mask] / 
            self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
        )

    def simulate_storage(self, Last_L: np.ndarray, duration: float) -> None:
        """
        Simulate CHP with thermal buffer storage (backed by ThermalStorage1D).

        :param Last_L: Thermal load [kW]
        :type Last_L: numpy.ndarray
        :param duration: Time step [hours]
        :type duration: float

        .. note::
           CHP runs at full nominal load; excess heat charges the buffer.
           Hysteresis control (min_fill / max_fill SOC thresholds) decides
           when to switch on/off. Buffer provides discharge when CHP is off.
        """
        self.Wärmeleistung_Speicher_kW = np.zeros_like(Last_L)
        self.Speicher_Fuellstand = np.zeros_like(Last_L)

        # Pre-charge buffer to initial_fill SOC, then clear history so it
        # only covers the actual simulation window (not the pre-charge step).
        if self.initial_fill > 0 and self.buffer is not None:
            capacity_kwh = self.buffer.get_capacity_kwh()
            self.buffer.step(self.initial_fill * capacity_kwh / duration, duration)
        self.buffer.reset_history()

        for i in range(len(Last_L)):
            soc = self.buffer.get_soc() if self.buffer else 0.0

            Q_net = 0.0  # net buffer interaction this timestep [kW], + = charge, − = discharge

            if self.active:
                if soc >= self.max_fill:
                    self.active = False
                else:
                    self.Wärmeleistung_kW[i] = self.th_Leistung_kW
                    Q_excess = self.th_Leistung_kW - Last_L[i]
                    if Q_excess > 0:
                        self.Wärmeleistung_Speicher_kW[i] = -Q_excess  # negative = charging
                        Q_net = Q_excess
                    # else: load ≥ CHP output, buffer idle this step
            else:
                if soc <= self.min_fill:
                    self.active = True

            if not self.active:
                self.Wärmeleistung_kW[i] = 0
                self.Wärmeleistung_Speicher_kW[i] = Last_L[i]  # positive = discharging
                Q_net = -Last_L[i]

            # Always advance buffer state (even if Q_net == 0) so heat losses
            # are tracked every timestep and history length == simulation length.
            self.buffer.step(Q_net, duration)

            self.el_Leistung_kW[i] = (self.Wärmeleistung_kW[i] /
                                      self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad)
            self.Speicher_Fuellstand[i] = self.buffer.get_soc() * 100.0

        self.betrieb_mask = self.Wärmeleistung_kW > 0

    def generate(self, t: int, **kwargs) -> tuple[float, float]:
        """
        Generate heat and electricity for time step.

        :param t: Time step index
        :type t: int
        :return: (heat_output [kW], electricity_output [kW])
        :rtype: tuple
        """
        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = self.th_Leistung_kW
            self.el_Leistung_kW[t] = (self.th_Leistung_kW / 
                                     self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad)
        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
            self.el_Leistung_kW[t] = 0

        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]
    
    def calculate_results(self, duration: float) -> None:
        """
        Calculate cogeneration metrics.

        :param duration: Time step [hours]
        :type duration: float
        """
        # Calculate annual energy generation
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration

        # Calculate fuel consumption based on combined efficiency
        self.Brennstoffbedarf_MWh = (self.Wärmemenge_MWh + self.Strommenge_MWh) / self.KWK_Wirkungsgrad

        # Analyze start-stop cycles and operational hours
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)
    
    def calculate_heat_generation_costs(self, economic_parameters: dict) -> float:
        """
        Calculate net heat generation costs with electricity revenue.

        :param economic_parameters: Economic parameters
        :type economic_parameters: dict
        :return: Net heat generation cost [€/MWh]
        :rtype: float

        .. note::
           Includes KWKG/BEW subsidies and electricity revenue offset.
        """
        self.load_economic_parameters(economic_parameters)

        if self.Wärmemenge_MWh == 0:
            self.WGK = 0
            return 0
        
        # Determine technology-specific costs and fuel prices by fuel type (not name).
        if self._resolve_fuel_type() == "wood_gas":
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_HBHKW  # €/kW
            self.Brennstoffpreis = self.Holzpreis
        else:  # gas
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_GBHKW  # €/kW
            self.Brennstoffpreis = self.Gaspreis

        # Calculate component investment costs
        self.Investitionskosten_BHKW = spez_Investitionskosten_BHKW * self.th_Leistung_kW
        self.Investitionskosten_Speicher = (self.spez_Investitionskosten_Speicher * 
                                           self.Speicher_Volumen_BHKW)
        self.Investitionskosten = self.Investitionskosten_BHKW + self.Investitionskosten_Speicher

        # Calculate electricity revenue
        self.Stromeinnahmen = self.Strommenge_MWh * self.Strompreis

        # Calculate standard annuity without subsidies
        self.A_N = self.annuity(
            initial_investment_cost=self.Investitionskosten,
            asset_lifespan_years=self.Nutzungsdauer,
            installation_factor=self.f_Inst,
            maintenance_inspection_factor=self.f_W_Insp,
            operational_effort_h=self.Bedienaufwand,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=self.Brennstoffbedarf_MWh,
            energy_cost_per_unit=self.Brennstoffpreis,
            annual_revenue=self.Stromeinnahmen,
            hourly_rate=self.stundensatz
        )
        
        self.WGK = self.A_N / self.Wärmemenge_MWh

        # Calculate BEW subsidy scenario
        self.Eigenanteil = 1 - self.Anteil_Förderung_BEW
        self.Investitionskosten_Gesamt_BEW = self.Investitionskosten * self.Eigenanteil
        
        self.Annuität_BEW = self.annuity(
            initial_investment_cost=self.Investitionskosten_Gesamt_BEW,
            asset_lifespan_years=self.Nutzungsdauer,
            installation_factor=self.f_Inst,
            maintenance_inspection_factor=self.f_W_Insp,
            operational_effort_h=self.Bedienaufwand,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=self.Brennstoffbedarf_MWh,
            energy_cost_per_unit=self.Brennstoffpreis,
            annual_revenue=self.Stromeinnahmen,
            hourly_rate=self.stundensatz
        )
        
        self.WGK_BEW = self.Annuität_BEW / self.Wärmemenge_MWh

        # Return appropriate cost based on subsidy eligibility
        if self.BEW == "Nein":
            return self.WGK
        elif self.BEW == "Ja":
            return self.WGK_BEW

    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact with CO2 savings.

        .. note::
           CO2 balance: fuel emissions minus grid displacement savings.
           Gas: 0.201 tCO2/MWh, Biomass: 0.036 tCO2/MWh
        """
        # Calculate CO2 emissions from fuel consumption
        self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel  # tCO2
        
        # Calculate CO2 savings from electricity generation (grid displacement)
        self.co2_savings = self.Strommenge_MWh * self.co2_factor_electricity  # tCO2
        
        # Calculate net CO2 impact (can be negative for high electricity generation)
        self.co2_total = self.co2_emissions - self.co2_savings  # tCO2
        
        # Calculate specific CO2 emissions per unit heat generated
        self.spec_co2_total = (self.co2_total / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat

        # Calculate primary energy consumption
        self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor
    
    def calculate(self, economic_parameters: dict, duration: float, 
                 load_profile: np.ndarray, **kwargs) -> dict:
        """
        Comprehensive CHP analysis.

        :param economic_parameters: Economic parameters
        :type economic_parameters: dict
        :param duration: Time step [hours]
        :type duration: float
        :param load_profile: Load profile [kW]
        :type load_profile: numpy.ndarray
        :return: Results with heat, electricity, economic and environmental data
        :rtype: dict

        .. note::
           Includes cogeneration simulation with electricity revenue.
        """
        # Perform cogeneration simulation if not already calculated
        if self.calculated == False:
            if self.speicher_aktiv:
                self.simulate_storage(load_profile, duration)
            else:
                self.simulate_operation(load_profile)
        
        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Perform economic and environmental analysis
        WGK = self.calculate_heat_generation_costs(economic_parameters)
        self.calculate_environmental_impact()

        # Compile comprehensive cogeneration results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Brennstoffbedarf_MWh,
            'WGK': WGK,
            'Strommenge': self.Strommenge_MWh,
            'el_Leistung_L': self.el_Leistung_kW,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "yellow"  # Yellow color for cogeneration systems
        }

        # Add storage-specific results if thermal storage is active
        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_kW
            results['Speicherfüllstand_L'] = self.Speicher_Fuellstand

        return results
    
    def set_parameters(self, variables: list[float], variables_order: list[str], idx: int) -> None:
        """
        Set optimization parameters.

        :param variables: Variable values
        :type variables: list
        :param variables_order: Variable names
        :type variables_order: list
        :param idx: Technology index
        :type idx: int
        """
        try:
            self.th_Leistung_kW = variables[variables_order.index(f"th_Leistung_kW_{idx}")]
            if self.speicher_aktiv:
                self.Speicher_Volumen_BHKW = variables[variables_order.index(f"Speicher_Volumen_BHKW_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> tuple[list[float], list[str], list[tuple[float, float]]]:
        """
        Define optimization parameters for CHP sizing.

        :param idx: Technology index
        :type idx: int
        :return: (initial_values, variables_order, bounds)
        :rtype: tuple

        .. note::
           Includes thermal capacity and storage volume (if active).
        """
        # Initialize with CHP thermal capacity optimization
        initial_values = [self.th_Leistung_kW]
        variables_order = [f"th_Leistung_kW_{idx}"]
        bounds = [(self.opt_BHKW_min, self.opt_BHKW_max)]

        # Add storage optimization if thermal storage is active
        if self.speicher_aktiv:
            initial_values.append(self.Speicher_Volumen_BHKW)
            variables_order.append(f"Speicher_Volumen_BHKW_{idx}")
            bounds.append((self.opt_BHKW_Speicher_min, self.opt_BHKW_Speicher_max))

        return initial_values, variables_order, bounds
    
    def get_display_text(self) -> str:
        """
        Generate display text for GUI.

        :return: Formatted configuration text
        :rtype: str
        """
        if self._resolve_fuel_type() == "wood_gas":
            return (f"{self.name}: th. Leistung: {self.th_Leistung_kW:.1f} kW, "
                    f"spez. Investitionskosten Holzgas-BHKW: {self.spez_Investitionskosten_HBHKW:.1f} €/kW")
        return (f"{self.name}: th. Leistung: {self.th_Leistung_kW:.1f} kW, "
                f"spez. Investitionskosten Erdgas-BHKW: {self.spez_Investitionskosten_GBHKW:.1f} €/kW")
        
    def extract_tech_data(self) -> tuple[str, str, str, str]:
        """
        Extract technology data for reporting.

        :return: (name, dimensions, costs, full_costs)
        :rtype: tuple
        """
        dimensions = f"th. Leistung: {self.th_Leistung_kW:.1f} kW, el. Leistung: {self.el_Leistung_Soll:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

class CHPStrategy(BaseStrategy):
    """
    Control strategy for CHP with storage.

    :param charge_on: Temperature threshold for activation [°C]
    :type charge_on: float
    :param charge_off: Temperature threshold for deactivation [°C]
    :type charge_off: float
    """
    
    def __init__(self, charge_on: float, charge_off: float):
        """
        Initialize control strategy.

        :param charge_on: Activation temperature [°C]
        :type charge_on: float
        :param charge_off: Deactivation temperature [°C]
        :type charge_off: float
        """
        super().__init__(charge_on, charge_off)