"""
Waste Heat Pump Module
================================

Waste heat pump modeling with variable source temperatures and heat recovery.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_pumps import HeatPump

class WasteHeatPump(HeatPump):
    """
    Waste heat pump utilizing industrial/data center waste heat.

    :param name: Unique identifier
    :type name: str
    :param Kühlleistung_Abwärme: Waste heat cooling capacity [kW]
    :type Kühlleistung_Abwärme: float
    :param Temperatur_Abwärme: Waste heat temperature [°C]
    :type Temperatur_Abwärme: float
    :param spez_Investitionskosten_Abwärme: Waste heat system costs [€/kW], defaults to 500
    :type spez_Investitionskosten_Abwärme: float, optional

    .. note::
       High COP due to elevated source temperatures.
    """

    def __init__(self, name: str, Kühlleistung_Abwärme: float, 
                 Temperatur_Abwärme: float, spez_Investitionskosten_Abwärme: float = 500, 
                 spezifische_Investitionskosten_WP: float = 1000, min_Teillast: float = 0.2,
                 opt_cooling_min: float = 0, opt_cooling_max: float = 500) -> None:
        """
        Initialize waste heat pump system.

        Parameters
        ----------
        name : str
            Unique identifier for the waste heat pump system.
        Kühlleistung_Abwärme : float
            Waste heat cooling capacity available for extraction [kW].
        Temperatur_Abwärme : float
            Waste heat source temperature [°C].
        spez_Investitionskosten_Abwärme : float, optional
            Specific investment costs for waste heat recovery system [€/kW]. Default is 500.
        spezifische_Investitionskosten_WP : float, optional
            Specific investment costs for heat pump unit [€/kW]. Default is 1000.
        min_Teillast : float, optional
            Minimum part-load ratio [-]. Default is 0.2.
        opt_cooling_min : float, optional
            Minimum cooling capacity for optimization [kW]. Default is 0.
        opt_cooling_max : float, optional
            Maximum cooling capacity for optimization [kW]. Default is 500.
        """
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Kühlleistung_Abwärme = Kühlleistung_Abwärme
        self.Temperatur_Abwärme = Temperatur_Abwärme
        self.spez_Investitionskosten_Abwärme = spez_Investitionskosten_Abwärme
        self.min_Teillast = min_Teillast
        self.opt_cooling_min = opt_cooling_min
        self.opt_cooling_max = opt_cooling_max

    def calculate_heat_pump(self, VLT_L: np.ndarray, COP_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate heat pump performance for waste heat operation.

        :param VLT_L: Required flow temperature array [°C].
        :type VLT_L: numpy.ndarray
        :param COP_data: COP lookup table for performance interpolation.
        :type COP_data: numpy.ndarray
        :return: Heat output [kW], electrical power [kW], achievable flow temps [°C], COP [-].
        :rtype: tuple of numpy.ndarray

        .. note:: Uses waste heat temperature as source for COP calculation.
        """
        # Calculate COP based on waste heat temperature and flow temperature
        COP_L, VLT_WP_L = self.calculate_COP(VLT_L, self.Temperatur_Abwärme, COP_data)
        
        # Calculate heat output based on waste heat extraction and COP
        Wärmeleistung_kW = self.Kühlleistung_Abwärme / (1 - (1 / COP_L))
        
        # Calculate electrical power consumption
        el_Leistung_kW = Wärmeleistung_kW - self.Kühlleistung_Abwärme

        return Wärmeleistung_kW, el_Leistung_kW, VLT_WP_L, COP_L

    def calculate_operation(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                           COP_data: np.ndarray) -> None:
        """
        Calculate operational performance considering waste heat availability.

        :param Last_L: Heat load demand time series [kW].
        :type Last_L: numpy.ndarray
        :param VLT_L: Required flow temperature time series [°C].
        :type VLT_L: numpy.ndarray
        :param COP_data: COP lookup table for performance interpolation.
        :type COP_data: numpy.ndarray

        .. note:: Heat output limited by waste heat capacity and load demand.
                  Updates time-series attributes for simulation period.
        """
        if self.Kühlleistung_Abwärme > 0:
            # Calculate heat pump performance for all time steps
            self.Wärmeleistung_kW, self.el_Leistung_kW, self.VLT_WP, self.COP = self.calculate_heat_pump(VLT_L, COP_data)

            # Determine operational constraints
            # Heat pump operates when load demand exceeds minimum part-load threshold
            self.betrieb_mask = Last_L >= self.Wärmeleistung_kW * self.min_Teillast
            
            # Adjust heat output to match actual demand (limited by capacity)
            self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
                Last_L[self.betrieb_mask], 
                self.Wärmeleistung_kW[self.betrieb_mask]
            )
            
            # Calculate corresponding electrical consumption
            self.el_Leistung_kW[self.betrieb_mask] = (
                self.Wärmeleistung_kW[self.betrieb_mask] - 
                self.Kühlleistung_Abwärme
            )
            
            # Set outputs to zero when not operating
            self.Wärmeleistung_kW[~self.betrieb_mask] = 0
            self.el_Leistung_kW[~self.betrieb_mask] = 0
            self.VLT_WP[~self.betrieb_mask] = 0
            self.COP[~self.betrieb_mask] = 0
            
            # Initialize waste heat extraction array
            self.Kühlleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.Kühlleistung_kW[self.betrieb_mask] = self.Kühlleistung_Abwärme
        else:
            # No waste heat available - set all outputs to zero
            self.betrieb_mask = np.zeros_like(Last_L, dtype=bool)
            self.Wärmeleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.Kühlleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.el_Leistung_kW = np.zeros_like(Last_L, dtype=float)
            self.VLT_WP = np.zeros_like(Last_L, dtype=float)
            self.COP = np.zeros_like(Last_L, dtype=float)

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat at specific time step with waste heat constraints.

        :param t: Current time step index.
        :type t: int
        :param kwargs: Additional parameters (VLT_L, COP_data).
        :type kwargs: dict
        :return: Heat generation [kW] and electricity consumption [kW].
        :rtype: tuple of float

        .. note:: Checks waste heat availability and operational constraints.
        """
        VLT = kwargs.get('VLT_L', 0)
        COP_data = kwargs.get('COP_data', None)

        # Calculate performance for current time step
        self.Wärmeleistung_kW[t], self.el_Leistung_kW[t], self.VLT_WP[t], self.COP[t] = self.calculate_heat_pump(VLT, COP_data)

        # Check operational constraints
        if (self.active and 
            self.VLT_WP[t] >= VLT and 
            self.Kühlleistung_Abwärme > 0):
            # Waste heat pump can operate - generate heat
            self.betrieb_mask[t] = True
            self.Kühlleistung_kW[t] = self.Kühlleistung_Abwärme
        else:
            # Cannot operate - set outputs to zero
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
            self.el_Leistung_kW[t] = 0
            self.Kühlleistung_kW[t] = 0
            self.VLT_WP[t] = 0
            self.COP[t] = 0

        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]
    
    def calculate_results(self, duration: float) -> None:
        """
        Calculate aggregated performance metrics from simulation results.

        :param duration: Time step duration [hours].
        :type duration: float

        .. note:: Calculates energy totals, SCOP, and operational statistics.
        """
        # Calculate total energy production and consumption
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration
        
        # Calculate Seasonal Coefficient of Performance
        self.SCOP = self.Wärmemenge_MWh / self.Strommenge_MWh if self.Strommenge_MWh > 0 else 0

        # Determine maximum heat output
        self.max_Wärmeleistung = np.max(self.Wärmeleistung_kW)
        
        # Calculate operational statistics
        starts = np.diff(self.betrieb_mask.astype(int)) > 0  # Start-up events
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)
    
    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive calculation of waste heat pump performance and economics.

        :param economic_parameters: Economic analysis parameters.
        :type economic_parameters: dict
        :param duration: Simulation time step duration [hours].
        :type duration: float
        :param load_profile: Heat demand time series [kW].
        :type load_profile: numpy.ndarray
        :param kwargs: Additional parameters (VLT_L, COP_data).
        :type kwargs: dict
        :return: Performance, economic, and environmental results.
        :rtype: dict

        .. note:: Integrates waste heat recovery with heat pump performance and lifecycle cost analysis.
        """
        # Extract required parameters
        VLT_L = kwargs.get('VLT_L')
        COP_data = kwargs.get('COP_data')

        # Perform operational calculation if not already done
        if not self.calculated:
            self.calculate_operation(load_profile, VLT_L, COP_data)
            self.calculated = True
        
        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Economic evaluation with waste heat specific costs
        self.WGK = self.calculate_heat_generation_costs(
            self.max_Wärmeleistung, 
            self.Wärmemenge_MWh, 
            self.Strommenge_MWh, 
            self.spez_Investitionskosten_Abwärme, 
            economic_parameters
        )
        
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
            'color': "grey"  # Visualization color coding
        }

        return results
    
    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
        """
        Set optimization parameters for the waste heat pump system.

        :param variables: List of optimization variable values.
        :type variables: list
        :param variables_order: List defining variable order and identification.
        :type variables_order: list
        :param idx: Technology index for parameter identification.
        :type idx: int

        .. note:: Updates waste heat cooling capacity from optimization variables.
        """
        try:
            # Extract waste heat capacity from optimization variables
            capacity_var = f"Kühlleistung_Abwärme_{idx}"
            if capacity_var in variables_order:
                capacity_index = variables_order.index(capacity_var)
                self.Kühlleistung_Abwärme = variables[capacity_index]
        except ValueError as e:
            print(f"Error setting parameters for {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for waste heat pump system.

        :param idx: Technology index for unique variable identification.
        :type idx: int
        :return: Initial values, variable names, and bounds for optimization.
        :rtype: tuple

        .. note:: Returns waste heat cooling capacity bounds and initial value.
        """
        initial_values = [self.Kühlleistung_Abwärme]
        variables_order = [f"Kühlleistung_Abwärme_{idx}"]
        bounds = [(self.opt_cooling_min, self.opt_cooling_max)]

        return initial_values, variables_order, bounds
    
    def get_display_text(self) -> str:
        """
        Generate human-readable display text for system configuration.

        :return: Formatted display text with system parameters.
        :rtype: str

        .. note:: Includes waste heat capacity, temperature, and investment costs.
        """
        return (f"{self.name}: Kühlleistung Abwärme: {self.Kühlleistung_Abwärme} kW, "
                f"Temperatur Abwärme: {self.Temperatur_Abwärme} °C, spez. Investitionskosten Abwärme: "
                f"{self.spez_Investitionskosten_Abwärme} €/kW, spez. Investitionskosten Wärmepumpe: "
                f"{self.spezifische_Investitionskosten_WP} €/kW")
    
    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting and analysis.

        :return: Name, technical dimensions, cost breakdown, and total investment.
        :rtype: tuple of str

        .. note:: Includes waste heat capacity, source temperature, and component costs.
        """
        # Technical specifications
        dimensions = (f"Kühlleistung Abwärme: {self.Kühlleistung_Abwärme:.1f} kW, "
                     f"Temperatur Abwärme: {self.Temperatur_Abwärme:.1f} °C, "
                     f"th. Leistung: {self.max_Wärmeleistung:.1f} kW")
        
        # Detailed cost breakdown
        waste_heat_cost = self.spez_Investitionskosten_Abwärme * self.max_Wärmeleistung
        hp_cost = self.spezifische_Investitionskosten_WP * self.max_Wärmeleistung
        costs = (f"Investitionskosten Abwärmenutzung: {waste_heat_cost:.1f} €, "
                f"Investitionskosten Wärmepumpe: {hp_cost:.1f} €")
        
        # Total investment costs
        full_costs = f"{waste_heat_cost + hp_cost:.1f}"
        
        return self.name, dimensions, costs, full_costs