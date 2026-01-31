"""
Biomass Boiler System Module
============================

Biomass boiler system with storage integration, economic analysis and BEW subsidy support.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Union

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class BiomassBoiler(BaseHeatGenerator):
    """
    Biomass boiler system with storage and efficiency modeling.

    :param name: Unique identifier
    :type name: str
    :param thermal_capacity_kW: Nominal thermal power [°kW]
    :type thermal_capacity_kW: float
    :param Größe_Holzlager: Wood storage capacity [tons], defaults to 40
    :type Größe_Holzlager: float, optional
    :param spez_Investitionskosten: Specific investment costs [€/kW], defaults to 200
    :type spez_Investitionskosten: float, optional
    :param Nutzungsgrad_BMK: Thermal efficiency [-], defaults to 0.8
    :type Nutzungsgrad_BMK: float, optional
    :param speicher_aktiv: Enable thermal storage, defaults to False
    :type speicher_aktiv: bool, optional
    :param Speicher_Volumen: Storage volume [m³], defaults to 20
    :type Speicher_Volumen: float, optional

    .. note::
       Supports BEW subsidy calculation and part-load operation constraints.
    """
    
    def __init__(self, name: str, thermal_capacity_kW: float, Größe_Holzlager: float = 40, 
                 spez_Investitionskosten: float = 200, spez_Investitionskosten_Holzlager: float = 400, 
                 Nutzungsgrad_BMK: float = 0.8, min_Teillast: float = 0.3,
                 speicher_aktiv: bool = False, Speicher_Volumen: float = 20, 
                 T_vorlauf: float = 90, T_ruecklauf: float = 60, 
                 initial_fill: float = 0.0, min_fill: float = 0.2, max_fill: float = 0.8, 
                 spez_Investitionskosten_Speicher: float = 750, active: bool = True, 
                 opt_BMK_min: float = 0, opt_BMK_max: float = 1000, 
                 opt_Speicher_min: float = 0, opt_Speicher_max: float = 100):
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
        self.Größe_Holzlager = Größe_Holzlager
        self.spez_Investitionskosten = spez_Investitionskosten
        self.spez_Investitionskosten_Holzlager = spez_Investitionskosten_Holzlager
        self.Nutzungsgrad_BMK = Nutzungsgrad_BMK
        self.min_Teillast = min_Teillast
        self.speicher_aktiv = speicher_aktiv
        self.Speicher_Volumen = Speicher_Volumen
        self.T_vorlauf = T_vorlauf
        self.T_ruecklauf = T_ruecklauf
        self.initial_fill = initial_fill
        self.min_fill = min_fill
        self.max_fill = max_fill
        self.spez_Investitionskosten_Speicher = spez_Investitionskosten_Speicher
        self.active = active
        self.opt_BMK_min = opt_BMK_min
        self.opt_BMK_max = opt_BMK_max
        self.opt_Speicher_min = opt_Speicher_min
        self.opt_Speicher_max = opt_Speicher_max
        
        # System specifications based on biomass boiler standards
        self.Nutzungsdauer = 15  # Operational lifespan [years]
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 3, 3, 0  # Installation and maintenance factors
        self.co2_factor_fuel = 0.036  # tCO2/MWh for wood pellets (carbon-neutral)
        self.primärenergiefaktor = 0.2  # Primary energy factor for biomass
        self.Anteil_Förderung_BEW = 0.4  # BEW subsidy percentage (40%)

        # Initialize control strategy
        self.strategy = BiomassBoilerStrategy(75, 70)

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

    def simulate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate boiler operation without storage.

        :param Last_L: Thermal load [kW]
        :type Last_L: numpy.ndarray

        .. note::
           Considers minimum part-load constraints.
        """
        # Determine operational periods based on minimum part-load constraint
        self.betrieb_mask = Last_L >= self.thermal_capacity_kW * self.min_Teillast
        
        # Calculate heat output limited by boiler capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.thermal_capacity_kW
        )

    def simulate_storage(self, Last_L: np.ndarray, duration: float) -> None:
        """
        Simulate boiler with thermal storage.

        :param Last_L: Thermal load [kW]
        :type Last_L: numpy.ndarray
        :param duration: Time step [hours]
        :type duration: float

        .. note::
           Includes storage charging/discharging with hysteresis control.
        """
        # Calculate thermal storage capacity based on water storage
        speicher_kapazitaet = (self.Speicher_Volumen * 4186 * 
                              (self.T_vorlauf - self.T_ruecklauf) / 3600)  # kWh
        
        # Initialize storage state and operational limits
        speicher_fill = self.initial_fill * speicher_kapazitaet
        min_speicher_fill = self.min_fill * speicher_kapazitaet
        max_speicher_fill = self.max_fill * speicher_kapazitaet

        # Initialize storage-related arrays
        self.Wärmeleistung_Speicher_kW = np.zeros_like(Last_L)
        self.Speicher_Fuellstand = np.zeros_like(Last_L)

        # Simulate hourly storage operation
        for i in range(len(Last_L)):
            if self.active:
                # Check if storage is full
                if speicher_fill >= max_speicher_fill:
                    self.active = False
                else:
                    # Operate boiler at nominal capacity
                    self.Wärmeleistung_kW[i] = self.thermal_capacity_kW
                    
                    # Manage storage charging/discharging
                    if Last_L[i] < self.thermal_capacity_kW:
                        # Charge storage with excess heat
                        self.Wärmeleistung_Speicher_kW[i] = Last_L[i] - self.thermal_capacity_kW
                        speicher_fill += (self.thermal_capacity_kW - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        # No storage charging when load exceeds boiler capacity
                        self.Wärmeleistung_Speicher_kW[i] = 0
            else:
                # Check if storage needs recharging
                if speicher_fill <= min_speicher_fill:
                    self.active = True
            
            # Storage discharge mode when boiler inactive
            if not self.active:
                self.Wärmeleistung_kW[i] = 0
                self.Wärmeleistung_Speicher_kW[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            # Update storage fill level percentage
            self.Speicher_Fuellstand[i] = speicher_fill / speicher_kapazitaet * 100  # %

        # Update operational mask based on boiler operation
        self.betrieb_mask = self.Wärmeleistung_kW > 0

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat for time step.

        :param t: Time step index
        :type t: int
        :return: (heat_output [kW], electricity_output [kW])
        :rtype: tuple
        """
        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = self.thermal_capacity_kW
        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0

        return self.Wärmeleistung_kW[t], 0  # Heat output, electricity output
    
    def calculate_results(self, duration: float) -> None:
        """
        Calculate operational metrics.

        :param duration: Time step [hours]
        :type duration: float
        """
        # Calculate annual energy generation and fuel consumption
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Brennstoffbedarf_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad_BMK

        # Analyze start-stop cycles and operational hours
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)

    def calculate_heat_generation_costs(self, economic_parameters: Dict) -> float:
        """
        Calculate heat generation costs with BEW subsidies.

        :param economic_parameters: Economic parameters (prices, rates, subsidies)
        :type economic_parameters: dict
        :return: Heat generation cost [€/MWh]
        :rtype: float

        .. note::
           Includes BEW subsidy (40%) if eligible.
        """
        # Extract economic parameters
        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']
        self.Holzpreis = economic_parameters['wood_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.stundensatz = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh == 0:
            return 0
        
        # Calculate component investment costs
        self.Investitionskosten_Kessel = self.spez_Investitionskosten * self.thermal_capacity_kW
        self.Investitionskosten_Holzlager = self.spez_Investitionskosten_Holzlager * self.Größe_Holzlager
        if self.speicher_aktiv:
            self.Investitionskosten_Speicher = self.spez_Investitionskosten_Speicher * self.Speicher_Volumen
        else:
            self.Investitionskosten_Speicher = 0
        self.Investitionskosten = (self.Investitionskosten_Kessel + 
                                  self.Investitionskosten_Holzlager + 
                                  self.Investitionskosten_Speicher)

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
            energy_cost_per_unit=self.Holzpreis,
            annual_revenue=0,
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
            energy_cost_per_unit=self.Holzpreis,
            annual_revenue=0,
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
        Calculate environmental impact metrics.

        .. note::
           Biomass: 0.036 tCO2/MWh, primary energy factor 0.2
        """
        # Calculate CO2 emissions from biomass fuel consumption
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
        :return: Results dictionary with thermal, economic and environmental data
        :rtype: dict

        .. note::
           Includes thermal simulation, economic and environmental analysis.
        """
        # Perform thermal simulation if not already calculated
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

        # Compile comprehensive results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Brennstoffbedarf_MWh,
            'WGK': WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "green"  # Green color for renewable biomass
        }

        # Add storage-specific results if thermal storage is active
        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_kW
            results['Speicherfüllstand_L'] = self.Speicher_Fuellstand

        return results
    
    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
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
            self.thermal_capacity_kW = variables[variables_order.index(f"P_BMK_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[List[float], List[str], List[Tuple[float, float]]]:
        """
        Define optimization parameters for system sizing.

        :param idx: Technology index
        :type idx: int
        :return: (initial_values, variables_order, bounds)
        :rtype: tuple

        .. note::
           Includes boiler capacity and storage volume (if active).
        """
        # Initialize with boiler capacity optimization
        initial_values = [self.thermal_capacity_kW]
        variables_order = [f"P_BMK_{idx}"]
        bounds = [(self.opt_BMK_min, self.opt_BMK_max)]

        # Add storage optimization if thermal storage is active
        if self.speicher_aktiv:
            initial_values.append(self.Speicher_Volumen)
            variables_order.append(f"Speicher_Volumen_{idx}")
            bounds.append((self.opt_Speicher_min, self.opt_Speicher_max))

        return initial_values, variables_order, bounds

    def get_display_text(self) -> str:
        """
        Generate display text for GUI.

        :return: Formatted system configuration text
        :rtype: str
        """
        return (f"{self.name}: th. Leistung: {self.thermal_capacity_kW:.1f}, "
                f"Größe Holzlager: {self.Größe_Holzlager:.1f} t, "
                f"spez. Investitionskosten Kessel: {self.spez_Investitionskosten:.1f} €/kW, "
                f"spez. Investitionskosten Holzlager: {self.spez_Investitionskosten_Holzlager:.1f} €/t")
    
    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting.

        :return: (name, dimensions, costs, full_costs)
        :rtype: tuple
        """
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW, Größe Holzlager: {self.Größe_Holzlager:.1f} t"
        costs = (f"Investitionskosten Kessel: {self.Investitionskosten_Kessel:.1f} €, "
                f"Investitionskosten Holzlager: {self.Investitionskosten_Holzlager:.1f} €")
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

class BiomassBoilerStrategy(BaseStrategy):
    """
    Control strategy for biomass boiler with storage.

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