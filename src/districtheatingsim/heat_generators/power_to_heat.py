"""
Power-to-Heat System Module
===========================

Electric heating system modeling with storage integration and control strategies.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class PowerToHeat(BaseHeatGenerator):
    """
    Electric heating system with grid integration.

    :param name: Unique identifier
    :type name: str
    :param thermal_capacity_kW: Maximum thermal capacity [kW], defaults to 1000
    :type thermal_capacity_kW: float, optional
    :param spez_Investitionskosten: Specific investment costs [€/kW], defaults to 30
    :type spez_Investitionskosten: float, optional
    :param Nutzungsgrad: Electric heating efficiency [-], defaults to 0.9
    :type Nutzungsgrad: float, optional

    .. note::
       Near-instantaneous response for demand response and grid services.
    """

    def __init__(self, name: str, thermal_capacity_kW: float = 1000, 
                 spez_Investitionskosten: float = 30, Nutzungsgrad: float = 0.9, 
                 active: bool = True) -> None:
        """
        Initialize power-to-heat system.

        :param name: Unique identifier
        :type name: str
        :param thermal_capacity_kW: Thermal capacity [kW], defaults to 1000
        :type thermal_capacity_kW: float
        :param spez_Investitionskosten: Specific investment costs [€/kW], defaults to 30
        :type spez_Investitionskosten: float
        :param Nutzungsgrad: Electric heating efficiency [-], defaults to 0.9
        :type Nutzungsgrad: float
        :param active: Activation status, defaults to True
        :type active: bool
        """
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.Nutzungsdauer = 20  # years system lifetime
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0  # Economic factors
        self.co2_factor_fuel = 0.4  # tCO2/MWh electricity grid mix
        self.primärenergiefaktor = 2.4  # Primary energy factor for electricity
        self.active = active

        # Initialize control strategy for storage integration
        self.strategy = PowerToHeatStrategy(75)  # Charge below 75°C

        # Initialize operational arrays
        self.init_operation(8760)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational data arrays for simulation.

        :param hours: Number of simulation hours.
        :type hours: int

        .. note:: Initializes time-series arrays and resets calculation flags.
        """
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.array([0.0] * hours)
        self.el_Leistung_kW = np.array([0.0] * hours)
        self.Wärmemenge_MWh = 0.0
        self.Strommenge_MWh = 0.0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0.0
        self.Betriebsstunden_pro_Start = 0.0

        self.calculated = False  # Flag to indicate if calculation is complete

    def simulate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate power-to-heat system operation for given load profile.

        :param Last_L: Thermal load demand time series [kW].
        :type Last_L: numpy.ndarray

        .. note:: System operates when demand exists, limited by thermal capacity.
                  Electrical consumption calculated using efficiency factor.
        """
        # Determine operational periods (when load demand exists)
        self.betrieb_mask = Last_L > 0
        
        # Calculate heat output limited by system capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.thermal_capacity_kW
        )
        
        # Calculate electrical consumption based on efficiency
        self.el_Leistung_kW[self.betrieb_mask] = (
            self.Wärmeleistung_kW[self.betrieb_mask] / self.Nutzungsgrad
        )

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate thermal power for specific time step.

        :param t: Current time step index.
        :type t: int
        :param kwargs: Additional parameters (remaining_load).
        :type kwargs: dict
        :return: Heat generation [kW] and electricity consumption [kW].
        :rtype: tuple of float

        .. note:: Heat output limited by thermal_capacity_kW and remaining demand.
        """
        remaining_load = kwargs.get('remaining_load', 0)
        
        if self.active and remaining_load > 0:
            # System active and demand exists - operate
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = min(remaining_load, self.thermal_capacity_kW)
            self.el_Leistung_kW[t] = self.Wärmeleistung_kW[t] / self.Nutzungsgrad
        else:
            # System inactive or no demand - shutdown
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0.0
            self.el_Leistung_kW[t] = 0.0
        
        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]
        
    def calculate_results(self, duration: float) -> None:
        """
        Calculate aggregated performance metrics.

        :param duration: Time step duration [hours]
        :type duration: float
        """
        # Calculate total energy production and consumption
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration
        
        # Calculate operational statistics
        starts = np.diff(self.betrieb_mask.astype(int)) > 0  # Detect start-up events
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (
            self.Betriebsstunden / self.Anzahl_Starts 
            if self.Anzahl_Starts > 0 else 0
        )
    
    def calculate_heat_generation_cost(self, economic_parameters: Dict[str, Any]) -> None:
        """
        Calculate heat generation costs using VDI 2067 methodology.

        :param economic_parameters: Economic analysis parameters.
        :type economic_parameters: dict

        .. note:: Includes capital costs, electricity costs, and operational expenses.
                  Uses annuity method for levelized cost calculation.
        """
        # Extract economic parameters
        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']  # Not used for P2H
        self.Holzpreis = economic_parameters['wood_price']  # Not used for P2H
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.stundensatz = economic_parameters['hourly_rate']
        
        if self.Wärmemenge_MWh > 0:
            # Calculate investment costs
            self.Investitionskosten = self.spez_Investitionskosten * self.thermal_capacity_kW

            # Calculate annuity using VDI 2067 methodology
            self.A_N = self.annuity(
                initial_investment_cost=self.Investitionskosten,
                asset_lifespan_years=self.Nutzungsdauer,
                installation_factor=self.f_Inst,
                maintenance_inspection_factor=self.f_W_Insp,
                operational_effort_h=self.Bedienaufwand,
                interest_rate_factor=self.q,
                inflation_rate_factor=self.r,
                consideration_time_period_years=self.T, 
                annual_energy_demand=self.Strommenge_MWh,
                energy_cost_per_unit=self.Strompreis,
                annual_revenue=0,  # No revenue for basic P2H operation
                hourly_rate=self.stundensatz
            )
            
            # Calculate levelized cost of heat generation
            self.WGK = self.A_N / self.Wärmemenge_MWh
        else:
            # No heat production - set costs to zero/infinite
            self.Investitionskosten = 0
            self.A_N = 0
            self.WGK = float('inf')

    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact of power-to-heat operation.

        .. note:: CO2 emissions from electricity grid and primary energy consumption.
                  Uses grid emission factor and primary energy factor.
        """
        # CO2 emissions from electricity consumption
        self.co2_emissions = self.Strommenge_MWh * self.co2_factor_fuel  # tCO2
        
        # Specific CO2 emissions per MWh of heat produced
        self.spec_co2_total = (
            self.co2_emissions / self.Wärmemenge_MWh 
            if self.Wärmemenge_MWh > 0 else 0
        )  # tCO2/MWh_heat
        
        # Primary energy consumption
        self.primärenergie = self.Strommenge_MWh * self.primärenergiefaktor

    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive calculation of power-to-heat performance and economics.

        :param economic_parameters: Economic analysis parameters.
        :type economic_parameters: dict
        :param duration: Simulation time step duration [hours].
        :type duration: float
        :param load_profile: Thermal load demand time series [kW].
        :type load_profile: numpy.ndarray
        :param kwargs: Additional parameters.
        :type kwargs: dict
        :return: Performance, economic, and environmental results.
        :rtype: dict

        .. note:: Performs operational simulation, economic evaluation, and environmental assessment.
        """
        # Perform operational simulation if not already done
        if not self.calculated:
            self.simulate_operation(load_profile)
            self.calculated = True
        
        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Economic evaluation
        self.calculate_heat_generation_cost(economic_parameters)
        
        # Environmental impact assessment
        self.calculate_environmental_impact()

        # Compile comprehensive results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Strombedarf': self.Strommenge_MWh,
            'el_Leistung_L': self.el_Leistung_kW,
            'WGK': self.WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            "color": "saddlebrown"  # Visualization color coding
        }

        return results
    
    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
        """
        Set optimization parameters (interface compatibility).

        :param variables: Optimization variable values
        :type variables: list
        :param variables_order: Variable order
        :type variables_order: list
        :param idx: Technology index
        :type idx: int
        """
        pass  # No optimization parameters for power-to-heat systems
    
    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for power-to-heat system.

        :param idx: Technology index.
        :type idx: int
        :return: Empty lists for initial values, variable names, and bounds.
        :rtype: tuple

        .. note:: No optimization parameters for basic power-to-heat systems.
        """
        return [], [], []  # No optimization parameters

    def get_display_text(self) -> str:
        """
        Generate human-readable display text for system configuration.

        :return: Formatted display text with system parameters.
        :rtype: str

        .. note:: Includes system name and specific investment costs.
        """
        return f"{self.name}: spez. Investitionskosten: {self.spez_Investitionskosten:.1f} €/kW"
    
    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting and analysis.

        :return: Name, technical dimensions, cost breakdown, and total investment.
        :rtype: tuple of str

        .. note:: Includes thermal capacity and investment costs.
        """
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        
        return self.name, dimensions, costs, full_costs


class PowerToHeatStrategy(BaseStrategy):
    """
    Control strategy for power-to-heat with storage.

    :param charge_on: Temperature threshold for activation [°C]
    :type charge_on: float
    :param charge_off: Temperature threshold for deactivation [°C], optional
    :type charge_off: float, optional
    """

    def __init__(self, charge_on: float, charge_off: Optional[float] = None) -> None:
        """
        Initialize power-to-heat control strategy.

        :param charge_on: Activation temperature threshold [°C]
        :type charge_on: float
        :param charge_off: Deactivation temperature threshold [°C], defaults to None
        :type charge_off: float, optional
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: float, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide whether to operate power-to-heat system based on control strategy.

        :param current_state: Current system state (reserved).
        :type current_state: float
        :param upper_storage_temp: Current upper storage temperature [°C].
        :type upper_storage_temp: float
        :param lower_storage_temp: Current lower storage temperature [°C].
        :type lower_storage_temp: float
        :param remaining_demand: Remaining heat demand [kW].
        :type remaining_demand: float
        :return: True if system should operate, False otherwise.
        :rtype: bool

        .. note:: Operates if temperature below charge_on threshold and demand exists.
        """
        # Check if storage temperature is below charging threshold and demand exists
        if upper_storage_temp < self.charge_on and remaining_demand > 0:
            return True  # Activate power-to-heat system
        else:
            return False  # Keep power-to-heat system off