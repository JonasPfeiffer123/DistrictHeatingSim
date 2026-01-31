"""
Gas Boiler System Module
========================

Gas-fired boiler system with economic analysis and environmental assessment.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Union

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class GasBoiler(BaseHeatGenerator):
    """
    Gas-fired boiler system for backup and peak load.

    :param name: Unique identifier
    :type name: str
    :param thermal_capacity_kW: Nominal thermal power [kW]
    :type thermal_capacity_kW: float
    :param spez_Investitionskosten: Specific investment costs [€/kW], defaults to 30
    :type spez_Investitionskosten: float, optional
    :param Nutzungsgrad: Thermal efficiency [-], defaults to 0.9
    :type Nutzungsgrad: float, optional
    :param active: Initial operational state, defaults to True
    :type active: bool, optional

    .. note::
       Simple load-following operation without minimum load constraints.
    """

    def __init__(self, name: str, thermal_capacity_kW: float, spez_Investitionskosten: float = 30, 
                 Nutzungsgrad: float = 0.9, active: bool = True):
        """
        Initialize gas boiler system.

        :param name: System identifier
        :type name: str
        :param thermal_capacity_kW: Thermal power [kW]
        :type thermal_capacity_kW: float
        :param spez_Investitionskosten: Specific costs [€/kW], defaults to 30
        :type spez_Investitionskosten: float
        :param Nutzungsgrad: Efficiency [-], defaults to 0.9
        :type Nutzungsgrad: float
        :param active: Operational state, defaults to True
        :type active: bool
        """
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.active = active
        
        # System specifications based on gas boiler standards
        self.Nutzungsdauer = 20  # Operational lifespan [years]
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0  # Installation and maintenance factors
        self.co2_factor_fuel = 0.201  # tCO2/MWh for natural gas
        self.primärenergiefaktor = 1.1  # Primary energy factor for natural gas

        # Initialize control strategy
        self.strategy = GasBoilerStrategy(70)

        # Initialize operational arrays
        self.init_operation(8760)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational arrays.

        :param hours: Simulation hours
        :type hours: int
        """
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if calculation is complete

    def calculate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate gas boiler with load-following strategy.

        :param Last_L: Thermal load [kW]
        :type Last_L: numpy.ndarray

        .. note::
           Simple on/off without minimum load constraints.
        """
        # Operate whenever there is heat demand
        self.betrieb_mask = Last_L > 0
        
        # Calculate heat output limited by boiler capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.thermal_capacity_kW
        )

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat for time step.

        :param t: Time step index
        :type t: int
        :param remaining_load: Remaining demand [kW]
        :type remaining_load: float
        :return: (heat_output [kW], electricity_output [kW])
        :rtype: tuple
        """
        remaining_load = kwargs.get('remaining_load', 0)

        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = min(remaining_load, self.thermal_capacity_kW)
        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
        
        return self.Wärmeleistung_kW[t], 0  # Heat output, no electricity generation
        
    def calculate_results(self, duration: float) -> None:
        """
        Calculate operational metrics.

        :param duration: Time step [hours]
        :type duration: float
        """
        # Calculate annual energy generation and fuel consumption
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Brennstoffbedarf_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad
        
        # Analyze start-stop cycles and operational hours
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)

    def calculate_heat_generation_cost(self, economic_parameters: Dict) -> None:
        """
        Calculate heat generation costs.

        :param economic_parameters: Economic parameters (prices, rates)
        :type economic_parameters: dict

        .. note::
           Low investment costs but high fuel costs.
        """
        # Extract economic parameters
        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']
        self.Holzpreis = economic_parameters['wood_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.hourly_rate = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh > 0:
            # Calculate investment costs
            self.Investitionskosten = self.spez_Investitionskosten * self.thermal_capacity_kW

            # Calculate annuity including all cost components
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
                energy_cost_per_unit=self.Gaspreis,
                annual_revenue=0,
                hourly_rate=self.hourly_rate
            )
            
            # Calculate heat generation cost
            self.WGK = self.A_N / self.Wärmemenge_MWh
        else:
            # Handle case with no heat generation
            self.Investitionskosten = 0
            self.A_N = 0
            self.WGK = float('inf')

    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact metrics.

        .. note::
           Natural gas: 0.201 tCO2/MWh, primary energy factor 1.1
        """
        # Calculate CO2 emissions from natural gas consumption
        self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel  # tCO2
        
        # Calculate specific CO2 emissions per unit heat generated
        self.spec_co2_total = (self.co2_emissions / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat
        
        # Calculate primary energy consumption
        self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor

    def calculate(self, economic_parameters: Dict, duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict:
        """
        Comprehensive system analysis.

        :param economic_parameters: Economic parameters
        :type economic_parameters: dict
        :param duration: Time step [hours]
        :type duration: float
        :param load_profile: Load profile [kW]
        :type load_profile: numpy.ndarray
        :return: Results dictionary
        :rtype: dict

        .. note::
           Includes thermal simulation, economic and environmental analysis.
        """
        # Perform thermal simulation if not already calculated
        if self.calculated == False:
            self.calculate_operation(load_profile)

        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Perform economic and environmental analysis
        self.calculate_heat_generation_cost(economic_parameters)
        self.calculate_environmental_impact()

        # Compile comprehensive results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Brennstoffbedarf_MWh,
            'WGK': self.WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            "color": "saddlebrown"  # Brown color for gas technology
        }

        return results
    
    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters.

        .. note::
           Gas boiler typically has no optimization parameters (fixed capacity).
        """
        pass

    def add_optimization_parameters(self, idx: int) -> Tuple[List[float], List[str], List[Tuple[float, float]]]:
        """
        Define optimization parameters.

        :param idx: Technology index
        :type idx: int
        :return: Empty (no optimization for gas boiler)
        :rtype: tuple
        """
        return [], [], []

    def get_display_text(self) -> str:
        """
        Generate display text for GUI.

        :return: Formatted configuration text
        :rtype: str
        """
        return (f"{self.name}: Nennleistung: {self.thermal_capacity_kW:.1f} kW, "
                f"Nutzungsgrad: {self.Nutzungsgrad:.2f}, "
                f"spez. Investitionskosten: {self.spez_Investitionskosten:.1f} €/kW")
    
    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting.

        :return: (name, dimensions, costs, full_costs)
        :rtype: tuple
        """
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

class GasBoilerStrategy(BaseStrategy):
    """
    Control strategy for gas boiler backup operation.

    :param charge_on: Temperature threshold for activation [°C]
    :type charge_on: float
    :param charge_off: Temperature threshold for deactivation [°C], optional
    :type charge_off: float, optional
    """
    
    def __init__(self, charge_on: float, charge_off: Optional[float] = None):
        """
        Initialize control strategy.

        :param charge_on: Activation temperature [°C]
        :type charge_on: float
        :param charge_off: Deactivation temperature [°C]
        :type charge_off: float
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: float, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide gas boiler operation based on storage and demand.

        :param current_state: Current state
        :type current_state: float
        :param upper_storage_temp: Storage temperature [°C]
        :type upper_storage_temp: float
        :param lower_storage_temp: Lower storage temperature [°C]
        :type lower_storage_temp: float
        :param remaining_demand: Remaining demand [kW]
        :type remaining_demand: float
        :return: True if boiler should operate
        :rtype: bool

        .. note::
           Activates if storage temp < threshold AND demand exists.
        """
        # Activate gas boiler if storage temperature is low AND demand exists
        if upper_storage_temp < self.charge_on and remaining_demand > 0:
            return True  # Turn gas boiler on
        else:
            return False  # Keep gas boiler off