"""
Geothermal Heat Pump System Module
==================================

Geothermal heat pump modeling with borehole field design and drilling cost analysis.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_pumps import HeatPump

class Geothermal(HeatPump):
    """
    Geothermal heat pump with borehole field modeling.

    :param name: Unique identifier
    :type name: str
    :param Fläche: Borehole field area [m²]
    :type Fläche: float
    :param Bohrtiefe: Drilling depth [m]
    :type Bohrtiefe: float
    :param Temperatur_Geothermie: Ground temperature [°C]
    :type Temperatur_Geothermie: float
    :param spez_Bohrkosten: Drilling costs [€/m], defaults to 100
    :type spez_Bohrkosten: float, optional
    :param spez_Entzugsleistung: Heat extraction [W/m], defaults to 50
    :type spez_Entzugsleistung: float, optional

    .. note::
       Stable source temperature for high seasonal efficiency.
    """

    def __init__(self, name: str, Fläche: float, Bohrtiefe: float, 
                 Temperatur_Geothermie: float, spez_Bohrkosten: float = 100, 
                 spez_Entzugsleistung: float = 50, Vollbenutzungsstunden: float = 2400, 
                 Abstand_Sonden: float = 10, spezifische_Investitionskosten_WP: float = 1000, 
                 min_Teillast: float = 0.2, min_area_geothermal: float = 0, 
                 max_area_geothermal: float = 5000, min_depth_geothermal: float = 0, 
                 max_depth_geothermal: float = 400) -> None:
        """
        Initialize geothermal heat pump.

        :param name: System identifier
        :type name: str
        :param Fläche: Available area [m²]
        :type Fläche: float
        :param Bohrtiefe: Drilling depth [m]
        :type Bohrtiefe: float
        :param Temperatur_Geothermie: Ground temperature [°C]
        :type Temperatur_Geothermie: float
        :param spez_Bohrkosten: Drilling costs [€/m], defaults to 100
        :type spez_Bohrkosten: float
        :param spez_Entzugsleistung: Extraction power [W/m], defaults to 50
        :type spez_Entzugsleistung: float
        """
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Fläche = Fläche
        self.Bohrtiefe = Bohrtiefe
        self.Temperatur_Geothermie = Temperatur_Geothermie
        self.spez_Bohrkosten = spez_Bohrkosten
        self.spez_Entzugsleistung = spez_Entzugsleistung
        self.Vollbenutzungsstunden = Vollbenutzungsstunden
        self.Abstand_Sonden = Abstand_Sonden
        self.min_Teillast = min_Teillast
        self.min_area_geothermal = min_area_geothermal
        self.max_area_geothermal = max_area_geothermal
        self.min_depth_geothermal = min_depth_geothermal
        self.max_depth_geothermal = max_depth_geothermal

        # Calculate borehole field design parameters
        self.Anzahl_Sonden = (round(np.sqrt(self.Fläche) / self.Abstand_Sonden) + 1) ** 2
        self.Entzugsleistung_VBH = self.Bohrtiefe * self.spez_Entzugsleistung * self.Anzahl_Sonden / 1000  # kW
        self.Entzugswärmemenge = self.Entzugsleistung_VBH * self.Vollbenutzungsstunden / 1000  # MWh
        self.Investitionskosten_Sonden = self.Bohrtiefe * self.spez_Bohrkosten * self.Anzahl_Sonden

    def calculate_operation(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                           COP_data: np.ndarray) -> None:
        """
        Calculate operation with thermal sustainability constraints.

        :param Last_L: Heat load [kW]
        :type Last_L: numpy.ndarray
        :param VLT_L: Flow temperature [°C]
        :type VLT_L: numpy.ndarray
        :param COP_data: COP lookup table
        :type COP_data: numpy.ndarray

        .. note::
           Uses iterative method to balance thermal extraction with sustainability.
        """
        if self.Fläche > 0 and self.Bohrtiefe > 0:
            # Calculate COP for all time steps
            self.COP, self.VLT_WP = self.calculate_COP(VLT_L, self.Temperatur_Geothermie, COP_data)

            self.Wärmeleistung_kW = np.zeros_like(Last_L)
            self.el_Leistung_kW = np.zeros_like(Last_L)
            self.betrieb_mask = np.zeros_like(Last_L, dtype=bool)

            # Iterative calculation for thermal sustainability
            # Find optimal operating hours that balance extraction with sustainability
            B_min = 1
            B_max = 8760
            tolerance = 0.5
            
            while B_max - B_min > tolerance:
                B = (B_min + B_max) / 2
                
                # Calculate heat extraction rate for these operating hours
                Entzugsleistung = self.Entzugswärmemenge * 1000 / B  # kW
                
                # Calculate corresponding heat pump capacity
                Wärmeleistung_kW = Entzugsleistung / (1 - (1 / self.COP))

                # Determine when heat pump can operate
                can_operate = Last_L >= Wärmeleistung_kW * self.min_Teillast
            
                # Reset arrays for this iteration
                Wärmeleistung_temp = np.zeros_like(Last_L)
                el_Leistung_temp = np.zeros_like(Last_L)

                # Calculate actual operation within constraints
                for i in range(len(Last_L)):
                    if can_operate[i]:
                        if Last_L[i] >= Wärmeleistung_kW[i]:
                            # Vollast
                            Wärmeleistung_temp[i] = Wärmeleistung_kW[i]
                            el_Leistung_temp[i] = Wärmeleistung_kW[i] / self.COP[i]
                        else:
                            # Teillast
                            Wärmeleistung_temp[i] = Last_L[i]
                            el_Leistung_temp[i] = Last_L[i] / self.COP[i]
                
                # Calculate actual thermal extraction
                Entzugsleistung_tat_L = Wärmeleistung_temp - el_Leistung_temp
                Entzugswärme = np.sum(Entzugsleistung_tat_L) / 1000  # MWh
                
                # Adjust operating hours based on thermal balance
                if Entzugswärme > self.Entzugswärmemenge:
                    B_min = B  # Need more operating hours (less extraction per hour)
                else:
                    B_max = B  # Can use fewer operating hours (more extraction per hour)

            # Speichere finale Werte
            self.Wärmeleistung_kW = Wärmeleistung_temp
            self.el_Leistung_kW = el_Leistung_temp
            self.betrieb_mask = can_operate
            
        else:
            # No geothermal system available - set all outputs to zero
            self.betrieb_mask = np.zeros_like(Last_L, dtype=bool)
            self.Wärmeleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.el_Leistung_kW = np.zeros_like(Last_L, dtype=float)
            self.VLT_WP = np.zeros_like(Last_L, dtype=float)
            self.COP = np.zeros_like(Last_L, dtype=float)

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat for time step.

        :param t: Time step index
        :type t: int
        :param VLT_L: Required flow temperature [°C]
        :type VLT_L: float
        :return: (heat_output [kW], electricity_consumption [kW])
        :rtype: tuple

        .. note::
           Checks sustainable extraction limits and temperature constraints.
        """
        VLT = kwargs.get('VLT_L', 0)
        COP_data = kwargs.get('COP_data', None)

        # Calculate COP for current conditions
        self.COP[t], self.VLT_WP[t] = self.calculate_COP(VLT, self.Temperatur_Geothermie, COP_data)

        # Calculate thermal extraction rate (assuming uniform distribution)
        Entzugsleistung = self.Entzugswärmemenge * 1000 / 8760  # kW
        Wärmeleistung = Entzugsleistung / (1 - (1 / self.COP[t]))
        el_Leistung = Wärmeleistung - Entzugsleistung

        # Check operational constraints
        if (self.active and 
            self.VLT_WP[t] >= VLT and 
            self.Fläche > 0 and 
            self.Bohrtiefe > 0):
            # Geothermal system can operate
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = Wärmeleistung
            self.el_Leistung_kW[t] = self.Wärmeleistung_kW[t] - (self.Wärmeleistung_kW[t] / Wärmeleistung) * el_Leistung
        else:
            # System cannot operate - set outputs to zero
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
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
        # Calculate maximum heat output and specific costs
        self.max_Wärmeleistung = max(self.Wärmeleistung_kW)
        self.spez_Investitionskosten_Erdsonden = (
            self.Investitionskosten_Sonden / self.max_Wärmeleistung 
            if self.max_Wärmeleistung > 0 else 0
        )

        # Calculate energy totals
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration
        
        # Calculate Seasonal Coefficient of Performance
        self.SCOP = self.Wärmemenge_MWh / self.Strommenge_MWh if self.Strommenge_MWh > 0 else 0
        
        # Calculate operational statistics
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (
            self.Betriebsstunden / self.Anzahl_Starts 
            if self.Anzahl_Starts > 0 else 0
        )

    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive geothermal heat pump analysis.

        :param economic_parameters: Economic parameters
        :type economic_parameters: dict
        :param duration: Time step [hours]
        :type duration: float
        :param load_profile: Load profile [kW]
        :type load_profile: numpy.ndarray
        :return: Results with performance, economic and environmental data
        :rtype: dict

        .. note::
           Includes borehole field modeling and thermal sustainability.
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
        
        # Economic evaluation with geothermal-specific costs
        self.WGK = self.calculate_heat_generation_costs(
            self.max_Wärmeleistung, 
            self.Wärmemenge_MWh, 
            self.Strommenge_MWh, 
            self.spez_Investitionskosten_Erdsonden, 
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
            'color': "darkorange"  # Visualization color coding
        }

        return results
    
    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
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
            # Extract geothermal parameters from optimization variables
            area_var = f"Fläche_{idx}"
            depth_var = f"Bohrtiefe_{idx}"
            
            if area_var in variables_order:
                area_index = variables_order.index(area_var)
                self.Fläche = variables[area_index]
            
            if depth_var in variables_order:
                depth_index = variables_order.index(depth_var)
                self.Bohrtiefe = variables[depth_index]
            
            # Recalculate dependent parameters
            self.Anzahl_Sonden = (round(np.sqrt(self.Fläche) / self.Abstand_Sonden) + 1) ** 2
            self.Entzugsleistung_VBH = self.Bohrtiefe * self.spez_Entzugsleistung * self.Anzahl_Sonden / 1000
            self.Entzugswärmemenge = self.Entzugsleistung_VBH * self.Vollbenutzungsstunden / 1000
            self.Investitionskosten_Sonden = self.Bohrtiefe * self.spez_Bohrkosten * self.Anzahl_Sonden
            
        except ValueError as e:
            print(f"Error setting parameters for {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for borehole field sizing.

        :param idx: Technology index
        :type idx: int
        :return: (initial_values, variables_order, bounds)
        :rtype: tuple

        .. note::
           Optimizes area and drilling depth.
        """
        initial_values = [self.Fläche, self.Bohrtiefe]
        variables_order = [f"Fläche_{idx}", f"Bohrtiefe_{idx}"]
        bounds = [
            (self.min_area_geothermal, self.max_area_geothermal),
            (self.min_depth_geothermal, self.max_depth_geothermal)
        ]
        
        return initial_values, variables_order, bounds

    def get_display_text(self) -> str:
        """
        Generate display text for GUI.

        :return: Formatted configuration text
        :rtype: str
        """
        return (f"{self.name}: Fläche Sondenfeld: {self.Fläche} m², Bohrtiefe: {self.Bohrtiefe} m, "
                f"Quelltemperatur Erdreich: {self.Temperatur_Geothermie} °C, spez. Bohrkosten: "
                f"{self.spez_Bohrkosten} €/m, spez. Entzugsleistung: {self.spez_Entzugsleistung} W/m, "
                f"Vollbenutzungsstunden: {self.Vollbenutzungsstunden} h, Abstand Sonden: {self.Abstand_Sonden} m, "
                f"spez. Investitionskosten Wärmepumpe: {self.spezifische_Investitionskosten_WP} €/kW")
    
    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting.

        :return: (name, dimensions, costs, full_costs)
        :rtype: tuple
        """
        # Technical specifications
        dimensions = (f"Fläche: {self.Fläche:.1f} m², Bohrtiefe: {self.Bohrtiefe:.1f} m, "
                     f"Temperatur Geothermie: {self.Temperatur_Geothermie:.1f} °C, "
                     f"Entzugsleistung: {self.spez_Entzugsleistung:.1f} W/m, "
                     f"th. Leistung: {self.max_Wärmeleistung:.1f} kW")
        
        # Detailed cost breakdown
        borehole_cost = self.Investitionskosten_Sonden
        hp_cost = self.spezifische_Investitionskosten_WP * self.max_Wärmeleistung
        costs = (f"Investitionskosten Sondenfeld: {borehole_cost:.1f} €, "
                f"Investitionskosten Wärmepumpe: {hp_cost:.1f} €")
        
        # Total investment costs
        full_costs = f"{borehole_cost + hp_cost:.1f}"
        
        return self.name, dimensions, costs, full_costs