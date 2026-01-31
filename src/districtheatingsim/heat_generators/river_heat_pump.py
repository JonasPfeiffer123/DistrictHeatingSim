"""
River Water Heat Pump System Module
===================================

River water heat pump modeling with temperature-dependent performance and intake costs.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_pumps import HeatPump

class RiverHeatPump(HeatPump):
    """
    River water heat pump with intake infrastructure.

    :param name: Unique identifier
    :type name: str
    :param Wärmeleistung_FW_WP: Thermal capacity [kW]
    :type Wärmeleistung_FW_WP: float
    :param Temperatur_FW_WP: River water temperature [°C], constant or time-series
    :type Temperatur_FW_WP: float or numpy.ndarray
    :param spez_Investitionskosten_Flusswasser: River system costs [€/kW], defaults to 1000
    :type spez_Investitionskosten_Flusswasser: float, optional

    .. note::
       Supports variable river temperature profiles for seasonal analysis.
    """

    def __init__(self, name: str, Wärmeleistung_FW_WP: float, 
                 Temperatur_FW_WP: Union[float, np.ndarray], dT: float = 0, 
                 spez_Investitionskosten_Flusswasser: float = 1000, 
                 spezifische_Investitionskosten_WP: float = 1000, 
                 min_Teillast: float = 0.2, opt_power_min: float = 0, 
                 opt_power_max: float = 500) -> None:
        """
        Initialize river water heat pump.

        :param name: System identifier
        :type name: str
        :param Wärmeleistung_FW_WP: Thermal capacity [kW]
        :type Wärmeleistung_FW_WP: float
        :param Temperatur_FW_WP: River water temperature [°C]
        :type Temperatur_FW_WP: float or numpy.ndarray
        :param spez_Investitionskosten_Flusswasser: River system costs [€/kW], defaults to 1000
        :type spez_Investitionskosten_Flusswasser: float
        """
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Wärmeleistung_FW_WP = Wärmeleistung_FW_WP
        self.Temperatur_FW_WP = np.array(Temperatur_FW_WP)
        self.dT = dT
        self.spez_Investitionskosten_Flusswasser = spez_Investitionskosten_Flusswasser
        self.min_Teillast = min_Teillast
        self.opt_power_min = opt_power_min
        self.opt_power_max = opt_power_max

    def calculate_heat_pump(self, VLT_L: np.ndarray, COP_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate heat pump performance.

        :param VLT_L: Required flow temperature [°C]
        :type VLT_L: numpy.ndarray
        :param COP_data: COP lookup table
        :type COP_data: numpy.ndarray
        :return: (cooling_power, electric_power, achievable_temp, COP)
        :rtype: tuple

        .. note::
           Uses river water temperature as heat source.
        """
        # Calculate COP based on river water temperature and flow temperature
        if isinstance(self.Temperatur_FW_WP, list):
            self.Temperatur_FW_WP = np.array(self.Temperatur_FW_WP)
        COP_L, VLT_WP_L = self.calculate_COP(VLT_L, self.Temperatur_FW_WP, COP_data)
        
        # Calculate heat extraction from river (cooling load)
        Kühlleistung_L = self.Wärmeleistung_FW_WP * (1 - (1 / COP_L))
        
        # Calculate electrical power consumption
        el_Leistung_L = self.Wärmeleistung_FW_WP - Kühlleistung_L

        return Kühlleistung_L, el_Leistung_L, VLT_WP_L, COP_L

    def calculate_operation(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                           COP_data: np.ndarray) -> None:
        """
        Calculate operation with load and temperature constraints.

        :param Last_L: Heat load [kW]
        :type Last_L: numpy.ndarray
        :param VLT_L: Flow temperature [°C]
        :type VLT_L: numpy.ndarray
        :param COP_data: COP lookup table
        :type COP_data: numpy.ndarray
        """
        # Determine actual heat output (limited by capacity and demand)
        self.Wärmeleistung_kW = np.minimum(Last_L, self.Wärmeleistung_FW_WP)
        
        # Calculate heat pump performance for all time steps
        self.Kühlleistung_kW, self.el_Leistung_kW, self.VLT_WP, self.COP = self.calculate_heat_pump(VLT_L, COP_data)

        # Determine operational constraints
        # Heat pump operates when:
        # 1. It can achieve required flow temperature (within tolerance)
        # 2. Load demand exceeds minimum part-load threshold
        self.betrieb_mask = np.logical_and(
            self.VLT_WP >= VLT_L - self.dT,  # Temperature delivery capability
            Last_L >= self.Wärmeleistung_FW_WP * self.min_Teillast  # Minimum load requirement
        )

        # Set outputs to zero when not operating
        self.Wärmeleistung_kW[~self.betrieb_mask] = 0
        self.Kühlleistung_kW[~self.betrieb_mask] = 0
        self.el_Leistung_kW[~self.betrieb_mask] = 0
        self.VLT_WP[~self.betrieb_mask] = 0
        self.COP[~self.betrieb_mask] = 0

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat for time step.

        :param t: Time step index
        :type t: int
        :param VLT_L: Required flow temperature [°C]
        :type VLT_L: float
        :return: (heat_output [kW], electricity_consumption [kW])
        :rtype: tuple
        """
        VLT = kwargs.get('VLT_L', 0)
        COP_data = kwargs.get('COP_data', None)

        # Calculate performance for current time step
        self.Kühlleistung_kW[t], self.el_Leistung_kW[t], self.VLT_WP[t], self.COP[t] = self.calculate_heat_pump(VLT, COP_data)

        # Check operational constraints
        if (self.active and 
            self.VLT_WP[t] >= VLT - self.dT and 
            self.Wärmeleistung_FW_WP > 0):
            # Heat pump can operate - generate heat
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = self.Wärmeleistung_FW_WP
        else:
            # Heat pump cannot operate - set outputs to zero
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
            self.Kühlleistung_kW[t] = 0
            self.el_Leistung_kW[t] = 0
            self.VLT_WP[t] = 0
            self.COP[t] = 0

        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]

    def calculate_results(self, duration: float) -> None:
        """
        Calculate performance metrics.

        :param duration: Time step [hours]
        :type duration: float
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
        Comprehensive river heat pump analysis.

        :param economic_parameters: Economic parameters
        :type economic_parameters: dict
        :param duration: Time step [hours]
        :type duration: float
        :param load_profile: Load profile [kW]
        :type load_profile: numpy.ndarray
        :return: Results dictionary
        :rtype: dict

        .. note::
           Includes performance, economic and environmental analysis.
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
        
        # Economic evaluation
        self.WGK = self.calculate_heat_generation_costs(
            self.Wärmeleistung_FW_WP, 
            self.Wärmemenge_MWh, 
            self.Strommenge_MWh, 
            self.spez_Investitionskosten_Flusswasser, 
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
            'color': "blue"  # Visualization color coding
        }

        return results

    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
        """
        Set optimization parameters.

        :param variables: Optimization variable values
        :type variables: list
        :param variables_order: Variable order
        :type variables_order: list
        :param idx: Technology index
        :type idx: int
        """
        try:
            # Extract heat pump capacity from optimization variables
            capacity_var = f"Wärmeleistung_FW_WP_{idx}"
            if capacity_var in variables_order:
                var_index = variables_order.index(capacity_var)
                self.Wärmeleistung_FW_WP = variables[var_index]
        except ValueError as e:
            print(f"Error setting parameters for {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for capacity sizing.

        :param idx: Technology index
        :type idx: int
        :return: (initial_values, variables_order, bounds)
        :rtype: tuple
        """
        initial_values = [self.Wärmeleistung_FW_WP]
        variables_order = [f"Wärmeleistung_FW_WP_{idx}"]
        bounds = [(self.opt_power_min, self.opt_power_max)]
        
        return initial_values, variables_order, bounds

    def get_display_text(self) -> str:
        """
        Generate human-readable display text.

        :return: Formatted display text with system parameters
        :rtype: str
        """
        # Handle temperature display based on data type
        if isinstance(self.Temperatur_FW_WP, (np.ndarray, list)):
            # Array data - indicate dataset is loaded
            text_temperture = "Datensatz Temperaturen geladen. "
        elif isinstance(self.Temperatur_FW_WP, (float, int)):
            # Single value - display actual temperature
            text_temperture = f"Temperatur FW WP: {self.Temperatur_FW_WP:.1f} °C, "
        else:
            text_temperture = f"Fehlerhaftes Datenformat: {type(self.Temperatur_FW_WP)} "

        return (f"{self.name}: Wärmeleistung FW WP: {self.Wärmeleistung_FW_WP:.1f} kW, "
                f"{text_temperture}dT: {self.dT:.1f} K, "
                f"spez. Investitionskosten Flusswärme: {self.spez_Investitionskosten_Flusswasser:.1f} €/kW, "
                f"spez. Investitionskosten Wärmepumpe: {self.spezifische_Investitionskosten_WP:.1f} €/kW")

    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting.

        :return: (name, dimensions, costs, full_costs)
        :rtype: tuple of str
        """
        # Technical specifications
        dimensions = f"th. Leistung: {self.Wärmeleistung_FW_WP:.1f} kW"
        
        # Detailed cost breakdown
        river_cost = self.spez_Investitionskosten_Flusswasser * self.Wärmeleistung_FW_WP
        hp_cost = self.spezifische_Investitionskosten_WP * self.Wärmeleistung_FW_WP
        costs = (f"Investitionskosten Flusswärmenutzung: {river_cost:.1f} €, "
                f"Investitionskosten Wärmepumpe: {hp_cost:.1f} €")
        
        # Total investment costs
        full_costs = f"{river_cost + hp_cost:.1f}"
        
        return self.name, dimensions, costs, full_costs