"""
Base Heat Pump Classes
========================

Base classes for heat pump modeling with COP calculations and economic analysis.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from typing import Dict, Tuple, Union, Optional, Any

import CoolProp.CoolProp as CP

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class HeatPump(BaseHeatGenerator):
    """
    Comprehensive heat pump model for district heating applications.

    :param name: Unique identifier
    :type name: str
    :param spezifische_Investitionskosten_WP: Specific investment costs [€/kW], defaults to 1000
    :type spezifische_Investitionskosten_WP: float, optional
    :param active: Initial operational status, defaults to True
    :type active: bool, optional

    .. note::
       Supports geothermal, waste heat, wastewater, and river sources with BEW subsidy (40%).
    """

    def __init__(self, name: str, spezifische_Investitionskosten_WP: float = 1000, active: bool = True) -> None:
        """
        Initialize heat pump system.

        :param name: Unique identifier
        :type name: str
        :param spezifische_Investitionskosten_WP: Specific investment costs [€/kW], defaults to 1000
        :type spezifische_Investitionskosten_WP: float
        :param active: Initial operational status, defaults to True
        :type active: bool
        """
        super().__init__(name)
        self.spezifische_Investitionskosten_WP = spezifische_Investitionskosten_WP
        self.active = active
        self.Nutzungsdauer_WP = 20
        self.f_Inst_WP, self.f_W_Insp_WP, self.Bedienaufwand_WP = 1, 1.5, 0
        self.f_Inst_WQ, self.f_W_Insp_WQ, self.Bedienaufwand_WQ = 0.5, 0.5, 0
        self.Nutzungsdauer_WQ_dict = {
            "Abwärmepumpe": 20, 
            "Abwasserwärmepumpe": 20, 
            "Flusswärmepumpe": 20, 
            "Geothermie": 30
        }
        self.co2_factor_electricity = 0.4  # tCO2/MWh electricity
        self.primärenergiefaktor = 1.8

        self.Anteil_Förderung_BEW = 0.4  # 40% subsidy for BEW program

        self.strategy = HeatPumpStrategy(75, 70)
        
        self.init_operation(8760)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational arrays for simulation period.

        :param hours: Number of simulation hours
        :type hours: int
        """
        self.betrieb_mask = np.zeros(hours, dtype=bool)
        self.Wärmeleistung_kW = np.zeros(hours, dtype=float)
        self.el_Leistung_kW = np.zeros(hours, dtype=float)
        self.Kühlleistung_kW = np.zeros(hours, dtype=float)
        self.VLT_WP = np.zeros(hours, dtype=float)
        self.COP = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Strommenge_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if the calculation is done

    def calculate_COP(self, VLT_L: np.ndarray, QT: Union[float, np.ndarray], 
                     COP_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate Coefficient of Performance using manufacturer data interpolation.

        :param VLT_L: Flow temperature array [°C]
        :type VLT_L: numpy.ndarray
        :param QT: Source temperature(s) [°C]
        :type QT: float or numpy.ndarray
        :param COP_data: COP lookup table
        :type COP_data: numpy.ndarray
        :return: (COP_L, VLT_L_adjusted)
        :rtype: tuple
        """
        # Extract interpolation data from COP table
        values = COP_data
        row_header = values[0, 1:]  # Flow temperatures from first row
        col_header = values[1:, 0]  # Source temperatures from first column
        values = values[1:, 1:]     # COP values matrix

        # Create interpolation function
        f = RegularGridInterpolator(
            (col_header, row_header), values, 
            method='linear', bounds_error=False, fill_value=None
        )

        # Apply technical limitation: maximum temperature lift of 75 K
        VLT_L = np.minimum(VLT_L, 75 + QT)

        # Handle scalar or array source temperature
        try:
            # Try to use QT as array
            if len(QT) != len(VLT_L):
                raise ValueError(
                    "QT must be either a single number or an array with the same length as VLT_L."
                )
            QT_array = np.asarray(QT)
        except (TypeError, AttributeError):
            # QT is scalar (no len() method)
            QT_array = np.full_like(VLT_L, QT)

        # Prepare input array for interpolation
        input_array = np.column_stack((QT_array, VLT_L))

        # Initialize COP array with NaN for invalid value marking
        COP_L = np.full_like(VLT_L, np.nan)

        try:
            # Calculate COPs for all values
            COP_L = f(input_array)
            
            # Handle out-of-bounds values by setting COP to 0
            out_of_bounds_mask = np.isnan(COP_L)
            COP_L[out_of_bounds_mask] = 0
            
            if np.any(out_of_bounds_mask):
                print("Some values were outside the valid range and were set to 0.")
                
        except ValueError as e:
            print(f"Interpolation error: {e}. Setting COP to 0 for values out of bounds.")
            COP_L = np.zeros_like(VLT_L)

        return COP_L, VLT_L

    def calculate_heat_generation_costs(self, Wärmeleistung: float, Wärmemenge_MWh: float, 
                                      Strombedarf: float, spez_Investitionskosten_WQ: float, 
                                      economic_parameters: Dict[str, Any]) -> float:
        """
        Calculate heat generation costs (WGK).

        :param Wärmeleistung: Thermal capacity [kW]
        :type Wärmeleistung: float
        :param Wärmemenge_MWh: Annual heat production [MWh]
        :type Wärmemenge_MWh: float
        :param Strombedarf: Annual electricity consumption [MWh]
        :type Strombedarf: float
        :param spez_Investitionskosten_WQ: Specific heat source costs [€/kW]
        :type spez_Investitionskosten_WQ: float
        :param economic_parameters: Economic parameters dict
        :type economic_parameters: dict
        :return: Heat generation costs [€/MWh]
        :rtype: float
        """
        # Extract economic parameters
        self.Strompreis = economic_parameters['electricity_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.stundensatz = economic_parameters['hourly_rate']

        if Wärmemenge_MWh == 0:
            return 0

        # Heat pump investment costs
        spezifische_Investitionskosten_WP = self.spezifische_Investitionskosten_WP
        Investitionskosten_WP = spezifische_Investitionskosten_WP * round(Wärmeleistung, 0)
        
        # Calculate annuity for heat pump without subsidies
        E1_WP = self.annuity(
            initial_investment_cost=Investitionskosten_WP,
            asset_lifespan_years=self.Nutzungsdauer_WP,
            installation_factor=self.f_Inst_WP,
            maintenance_inspection_factor=self.f_W_Insp_WP,
            operational_effort_h=self.Bedienaufwand_WP,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=self.Strommenge_MWh,
            energy_cost_per_unit=self.Strompreis,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        WGK_WP = E1_WP / Wärmemenge_MWh

        # Calculate annuity for heat pump with BEW subsidies
        Eigenanteil = 1 - self.Anteil_Förderung_BEW
        Investitionskosten_WP_BEW = Investitionskosten_WP * Eigenanteil
        Annuität_WP_BEW = self.annuity(
            initial_investment_cost=Investitionskosten_WP_BEW,
            asset_lifespan_years=self.Nutzungsdauer_WP,
            installation_factor=self.f_Inst_WP,
            maintenance_inspection_factor=self.f_W_Insp_WP,
            operational_effort_h=self.Bedienaufwand_WP,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=self.Strommenge_MWh,
            energy_cost_per_unit=self.Strompreis,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        WGK_WP_BEW = Annuität_WP_BEW / Wärmemenge_MWh

        # Heat source costs
        base_name = self.name.split('_')[0]
        
        if base_name not in self.Nutzungsdauer_WQ_dict:
            raise KeyError(f"{base_name} is not a valid key in Nutzungsdauer_WQ_dict")
        
        Investitionskosten_WQ = spez_Investitionskosten_WQ * Wärmeleistung
        
        # Calculate annuity for heat source without subsidies
        E1_WQ = self.annuity(
            initial_investment_cost=Investitionskosten_WQ,
            asset_lifespan_years=self.Nutzungsdauer_WQ_dict[base_name],
            installation_factor=self.f_Inst_WQ,
            maintenance_inspection_factor=self.f_W_Insp_WQ,
            operational_effort_h=self.Bedienaufwand_WQ,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=0,
            energy_cost_per_unit=self.Strompreis,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        WGK_WQ = E1_WQ / Wärmemenge_MWh

        # Calculate annuity for heat source with BEW subsidies
        Investitionskosten_WQ_BEW = Investitionskosten_WQ * Eigenanteil
        Annuität_WQ_BEW = self.annuity(
            initial_investment_cost=Investitionskosten_WQ_BEW,
            asset_lifespan_years=self.Nutzungsdauer_WQ_dict[base_name],
            installation_factor=self.f_Inst_WQ,
            maintenance_inspection_factor=self.f_W_Insp_WQ,
            operational_effort_h=self.Bedienaufwand_WQ,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=0,
            energy_cost_per_unit=self.Strompreis,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )

        WGK_WQ_BEW = Annuität_WQ_BEW / Wärmemenge_MWh

        # Total heat generation costs
        WGK = WGK_WP + WGK_WQ
        WGK_BEW = WGK_WP_BEW + WGK_WQ_BEW
        
        # Return appropriate cost based on subsidy eligibility
        if self.BEW == "Nein":
            return WGK
        elif self.BEW == "Ja":
            return WGK_BEW
    
    def calculate_environmental_impact(self) -> None:
        """
        Calculate CO2 emissions and primary energy consumption.

        .. note::
           Uses German grid emission factors and primary energy factor.
        """
        # CO2 emissions due to electricity usage
        self.co2_emissions = self.Strommenge_MWh * self.co2_factor_electricity  # tCO2
        
        # Specific emissions per unit heat delivered
        self.spec_co2_total = (self.co2_emissions / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat

        # Primary energy consumption including conversion losses
        self.primärenergie = self.Strommenge_MWh * self.primärenergiefaktor

class HeatPumpStrategy(BaseStrategy):
    """
    Control strategy for heat pump operation with hysteresis.

    :param charge_on: Temperature threshold for activation [°C]
    :type charge_on: float
    :param charge_off: Temperature threshold for deactivation [°C]
    :type charge_off: float
    """
    
    def __init__(self, charge_on: float, charge_off: float) -> None:
        """
        Initialize heat pump control strategy.

        :param charge_on: Temperature threshold for activation [°C]
        :type charge_on: float
        :param charge_off: Temperature threshold for deactivation [°C]
        :type charge_off: float
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: bool, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide heat pump operation based on storage temperature and demand.

        :param current_state: Current operational state
        :type current_state: bool
        :param upper_storage_temp: Upper storage temperature [°C]
        :type upper_storage_temp: float
        :param lower_storage_temp: Lower storage temperature [°C]
        :type lower_storage_temp: float
        :param remaining_demand: Remaining heat demand [kW]
        :type remaining_demand: float
        :return: Operational decision (True=run, False=stop)
        :rtype: bool
        """
        # Check current operational state
        if current_state:
            # Heat pump is currently operating
            if lower_storage_temp < self.charge_off and remaining_demand > 0:
                return True  # Continue operation
            else:
                return False  # Stop operation (overheating protection or no demand)
        else:
            # Heat pump is currently stopped
            if upper_storage_temp <= self.charge_on and remaining_demand > 0:
                return True  # Start operation (low storage temp and demand present)
            else:
                return False  # Remain stopped (sufficient storage temp or no demand)