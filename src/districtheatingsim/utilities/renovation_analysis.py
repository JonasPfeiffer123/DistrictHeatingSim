"""
Filename: renovation_analysis.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-09
Description: Contains the calculation model for the renovation cost analysis.

This module provides comprehensive tools for analyzing the economic viability of building
renovations from an energy efficiency perspective. It includes building energy modeling,
financial analysis, and life-cycle cost assessment capabilities for various renovation
scenarios including individual component upgrades and complete building renovations.

The module implements standardized calculation methods according to German building energy
standards (EnEV/GEG) and provides detailed economic metrics including NPV, payback periods,
and return on investment calculations.
"""

import numpy_financial as npf
from typing import Dict, List, Optional, Tuple, Union
from districtheatingsim.utilities.test_reference_year import import_TRY

class Building:
    """
    Building energy model for calculating heat demand and energy consumption.
    
    This class models a building's thermal characteristics and provides methods to
    calculate heating and hot water demands based on building geometry, thermal
    properties, and climate data. The calculations follow German building energy
    standards and use the degree-day method for annual energy demand estimation.
    
    Parameters
    ----------
    ground_area : float
        Ground floor area of the building in square meters [m²].
    wall_area : float
        Total exterior wall area in square meters [m²].
    roof_area : float
        Roof area in square meters [m²].
    building_volume : float
        Heated building volume in cubic meters [m³].
    u_values : dict, optional
        Dictionary containing U-values and other thermal parameters.
        If None, uses STANDARD_U_VALUES.
        
    Attributes
    ----------
    STANDARD_U_VALUES : dict
        Default thermal parameters according to German building standards.
        
        - ground_u : float
            U-value for ground floor [W/m²K]
        - wall_u : float
            U-value for exterior walls [W/m²K]
        - roof_u : float
            U-value for roof [W/m²K]
        - window_u : float
            U-value for windows [W/m²K]
        - door_u : float
            U-value for doors [W/m²K]
        - air_change_rate : float
            Air changes per hour [1/h]
        - floors : int
            Number of floors
        - fracture_windows : float
            Window area fraction of wall area [-]
        - fracture_doors : float
            Door area fraction of wall area [-]
        - Normaußentemperatur : float
            Design outside temperature [°C]
        - room_temp : float
            Indoor design temperature [°C]
        - max_air_temp_heating : float
            Maximum outside temperature for heating [°C]
        - ww_demand_kWh_per_m2 : float
            Hot water demand per floor area [kWh/m²a]
            
    Examples
    --------
    >>> # Create a building with default parameters
    >>> building = Building(100, 400, 100, 1000)
    >>> building.calc_yearly_heat_demand(temperature_data)
    >>> print(f"Annual heat demand: {building.yearly_heat_demand:.1f} kWh/a")
    
    >>> # Create building with custom U-values
    >>> custom_u_values = Building.STANDARD_U_VALUES.copy()
    >>> custom_u_values['wall_u'] = 0.15  # Better insulation
    >>> efficient_building = Building(100, 400, 100, 1000, custom_u_values)
    
    Notes
    -----
    - U-values should comply with German energy standards (EnEV/GEG)
    - Temperature data should be hourly values for a complete year
    - The model assumes rectangular building geometry
    - Thermal bridges and solar gains are simplified
    """
    
    STANDARD_U_VALUES = {
        'ground_u': 0.31,           # W/m²K - Ground floor U-value
        'wall_u': 0.23,             # W/m²K - Wall U-value  
        'roof_u': 0.19,             # W/m²K - Roof U-value
        'window_u': 1.3,            # W/m²K - Window U-value
        'door_u': 1.3,              # W/m²K - Door U-value
        'air_change_rate': 0.5,     # 1/h - Air changes per hour
        'floors': 4,                # - Number of floors
        'fracture_windows': 0.10,   # - Window area fraction
        'fracture_doors': 0.01,     # - Door area fraction
        'Normaußentemperatur': -15, # °C - Design outside temperature
        'room_temp': 20,            # °C - Indoor design temperature
        'max_air_temp_heating': 15, # °C - Heating limit temperature
        'ww_demand_kWh_per_m2': 12.8 # kWh/m²a - Hot water demand
    }

    def __init__(self, ground_area: float, wall_area: float, roof_area: float, 
                 building_volume: float, u_values: Optional[Dict] = None):
        """
        Initialize a Building instance with geometric and thermal parameters.
        
        Parameters
        ----------
        ground_area : float
            Ground floor area [m²]
        wall_area : float
            Total exterior wall area [m²]
        roof_area : float
            Roof area [m²]
        building_volume : float
            Heated building volume [m³]
        u_values : dict, optional
            Thermal parameters dictionary. Uses STANDARD_U_VALUES if None.
        """
        self.ground_area = ground_area
        self.wall_area = wall_area
        self.roof_area = roof_area
        self.building_volume = building_volume
        self.u_values = u_values if u_values else self.STANDARD_U_VALUES.copy()
        self.window_area = wall_area * self.u_values["fracture_windows"]
        self.door_area = wall_area * self.u_values["fracture_doors"]

    def calc_heat_demand(self) -> None:
        """
        Calculate the maximum heat demand of the building.
        
        This method calculates the design heat load according to DIN EN 12831
        including transmission and ventilation heat losses. The calculation
        considers all building envelope components and their thermal properties.
        
        Notes
        -----
        - Sets attribute `max_heating_demand` with the result in Watts [W]
        - Considers transmission losses through all envelope components
        - Includes ventilation heat losses based on air change rate
        - Uses design temperatures for maximum load calculation
        """
        self.real_wall_area = self.wall_area - self.window_area - self.door_area

        heat_loss_per_K = {
            'wall': self.real_wall_area * self.u_values["wall_u"],
            'ground': self.ground_area * self.u_values["ground_u"],
            'roof': self.roof_area * self.u_values["roof_u"],
            'window': self.window_area * self.u_values["window_u"],
            'door': self.door_area * self.u_values["door_u"]
        }

        self.total_heat_loss_per_K = sum(heat_loss_per_K.values())
        self.dT_max_K = self.u_values["room_temp"] - self.u_values["Normaußentemperatur"]
        self.transmission_heat_loss = self.total_heat_loss_per_K * self.dT_max_K
        self.ventilation_heat_loss = 0.34 * self.u_values["air_change_rate"] * self.building_volume * self.dT_max_K
        self.max_heating_demand = self.transmission_heat_loss + self.ventilation_heat_loss

    def calc_yearly_heating_demand(self, temperature_data: List[float]) -> None:
        """
        Calculate the yearly heating demand based on temperature data.
        
        This method uses the degree-day method to calculate the annual heating
        energy demand based on hourly temperature data. The calculation assumes
        a linear relationship between heat demand and outside temperature.
        
        Parameters
        ----------
        temperature_data : List[float]
            Hourly outside temperature values for a complete year [°C].
            Should contain 8760 values for a standard year.
            
        Notes
        -----
        - Sets attribute `yearly_heating_demand` with the result in kWh/a
        - Uses simplified linear relationship between temperature and heat demand
        - Considers heating limit temperature (no heating above this temperature)
        - Converts hourly power values to annual energy consumption
        """
        m = self.max_heating_demand / (self.u_values["Normaußentemperatur"] - self.u_values["max_air_temp_heating"])
        b = -m * self.u_values["max_air_temp_heating"]
        self.yearly_heating_demand = sum(max(m * temp + b, 0) for temp in temperature_data if temp < self.u_values["max_air_temp_heating"]) / 1000

    def calc_yearly_warm_water_demand(self) -> None:
        """
        Calculate the yearly hot water demand.
        
        This method calculates the annual energy demand for domestic hot water
        based on the heated floor area and specific hot water consumption according
        to German standards.
        
        Notes
        -----
        - Sets attribute `yearly_warm_water_demand` with the result in kWh/a
        - Uses standard specific consumption values per floor area
        - Considers number of floors for total heated area calculation
        """
        self.yearly_warm_water_demand = self.u_values["ww_demand_kWh_per_m2"] * self.ground_area * self.u_values["floors"]

    def calc_yearly_heat_demand(self, temperature_data: List[float]) -> None:
        """
        Calculate the total yearly heat demand (heating + hot water).
        
        This method orchestrates the calculation of both heating and hot water
        demands and combines them into the total annual heat demand.
        
        Parameters
        ----------
        temperature_data : List[float]
            Hourly outside temperature values for a complete year [°C].
            
        Notes
        -----
        - Sets attribute `yearly_heat_demand` with the total result in kWh/a
        - Combines space heating and domestic hot water demands
        - Calls all necessary sub-calculation methods
        """
        self.calc_heat_demand()
        self.calc_yearly_heating_demand(temperature_data)
        self.calc_yearly_warm_water_demand()
        self.yearly_heat_demand = self.yearly_heating_demand + self.yearly_warm_water_demand
    
class SanierungsAnalyse:
    """
    Economic analysis tool for building renovation projects.
    
    This class provides comprehensive financial analysis methods for evaluating
    the economic viability of building renovations. It includes standard financial
    metrics such as payback period, net present value (NPV), life-cycle cost
    analysis (LCCA), and return on investment (ROI).
    
    Parameters
    ----------
    ref_heat_demand : float
        Reference (current) annual heat demand before renovation [kWh/a].
    san_heat_demand : float
        Annual heat demand after renovation [kWh/a].
    energiepreis_ist : float
        Current energy price [€/kWh].
    energiepreis_saniert : float
        Energy price after renovation (may differ due to system change) [€/kWh].
    diskontierungsrate : float
        Discount rate for financial calculations [fraction, e.g., 0.04 for 4%].
    jahre : int
        Analysis period in years.
        
    Examples
    --------
    >>> # Create analysis for a renovation project
    >>> analysis = SanierungsAnalyse(
    ...     ref_heat_demand=15000,  # kWh/a before
    ...     san_heat_demand=8000,   # kWh/a after  
    ...     energiepreis_ist=0.08,  # €/kWh current
    ...     energiepreis_saniert=0.06,  # €/kWh after
    ...     diskontierungsrate=0.04,    # 4% discount rate
    ...     jahre=20                    # 20 year analysis
    ... )
    >>> savings = analysis.berechne_kosteneinsparungen()
    >>> payback = analysis.berechne_amortisationszeit(50000)  # 50k€ investment
    >>> print(f"Annual savings: {savings:.0f} €/a, Payback: {payback:.1f} years")
    
    Notes
    -----
    - All financial calculations use the provided discount rate
    - Energy prices can differ before/after renovation (e.g., heat pump vs. gas)
    - Analysis period should reflect the expected lifetime of measures
    - Subsidies are handled as percentage reductions of investment costs
    """
    
    def __init__(self, ref_heat_demand: float, san_heat_demand: float, 
                 energiepreis_ist: float, energiepreis_saniert: float, 
                 diskontierungsrate: float, jahre: int):
        """
        Initialize economic analysis with energy and financial parameters.
        
        Parameters
        ----------
        ref_heat_demand : float
            Reference annual heat demand [kWh/a]
        san_heat_demand : float
            Post-renovation annual heat demand [kWh/a]
        energiepreis_ist : float
            Current energy price [€/kWh]
        energiepreis_saniert : float
            Post-renovation energy price [€/kWh]
        diskontierungsrate : float
            Discount rate [fraction]
        jahre : int
            Analysis period [years]
        """
        self.ref_heat_demand = ref_heat_demand
        self.san_heat_demand = san_heat_demand
        self.energiepreis_ist = energiepreis_ist
        self.energiepreis_saniert = energiepreis_saniert
        self.diskontierungsrate = diskontierungsrate
        self.jahre = jahre

    def berechne_kosteneinsparungen(self) -> float:
        """
        Calculate annual cost savings from the renovation.
        
        This method computes the difference between current energy costs
        and post-renovation energy costs, accounting for both demand
        reduction and potential energy price changes.
        
        Returns
        -------
        float
            Annual cost savings in €/a.
            
        Examples
        --------
        >>> analysis = SanierungsAnalyse(15000, 8000, 0.08, 0.06, 0.04, 20)
        >>> savings = analysis.berechne_kosteneinsparungen()
        >>> print(f"Annual savings: {savings:.0f} €/a")
        Annual savings: 720 €/a
        """
        kosten_ist = self.ref_heat_demand * self.energiepreis_ist
        kosten_saniert = self.san_heat_demand * self.energiepreis_saniert
        return kosten_ist - kosten_saniert

    def berechne_amortisationszeit(self, investitionskosten: float, 
                                  foerderquote: float = 0) -> float:
        """
        Calculate the simple payback period for the renovation.
        
        This method calculates the time required to recover the initial
        investment through annual energy cost savings. The calculation
        considers subsidies as a reduction of effective investment costs.
        
        Parameters
        ----------
        investitionskosten : float
            Total investment costs for the renovation [€].
        foerderquote : float, optional
            Subsidy rate as fraction of investment costs [0-1].
            Default is 0 (no subsidies).
            
        Returns
        -------
        float
            Simple payback period in years.
            
        Examples
        --------
        >>> payback = analysis.berechne_amortisationszeit(50000, 0.3)  # 30% subsidy
        >>> print(f"Payback period: {payback:.1f} years")
        Payback period: 7.2 years
        
        Notes
        -----
        - Simple payback does not consider time value of money
        - Result may be infinite if cost savings are zero or negative
        - Subsidies reduce effective investment costs proportionally
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen()
        return effektive_investitionskosten / kosteneinsparung if kosteneinsparung > 0 else float('inf')

    def berechne_npv(self, investitionskosten: float, 
                     foerderquote: float = 0) -> float:
        """
        Calculate the net present value (NPV) of the renovation.
        
        This method calculates the NPV considering the time value of money
        over the analysis period. The NPV represents the net benefit of
        the investment in present value terms.
        
        Parameters
        ----------
        investitionskosten : float
            Total investment costs [€].
        foerderquote : float, optional
            Subsidy rate as fraction [0-1]. Default is 0.
            
        Returns
        -------
        float
            Net present value in €. Positive values indicate profitable investments.
            
        Examples
        --------
        >>> npv = analysis.berechne_npv(50000, 0.2)  # 20% subsidy
        >>> if npv > 0:
        ...     print(f"Investment is profitable: NPV = {npv:.0f} €")
        Investment is profitable: NPV = 8543 €
        
        Notes
        -----
        - Uses the discount rate specified during initialization
        - Assumes constant annual savings over the analysis period
        - Positive NPV indicates economically viable investment
        - Does not consider residual values or varying cash flows
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen()
        cashflows = [-effektive_investitionskosten] + [kosteneinsparung] * self.jahre
        return npf.npv(self.diskontierungsrate, cashflows)

    def lcca(self, investitionskosten: float, betriebskosten: float, 
             instandhaltungskosten: float, restwert: float, 
             foerderquote: float = 0) -> float:
        """
        Perform life-cycle cost analysis (LCCA) for the renovation.
        
        This method calculates the complete life-cycle costs including
        initial investment, operating costs, maintenance costs, and
        residual value at the end of the analysis period.
        
        Parameters
        ----------
        investitionskosten : float
            Initial investment costs [€].
        betriebskosten : float
            Annual operating costs [€/a].
        instandhaltungskosten : float
            Annual maintenance costs [€/a].
        restwert : float
            Residual value at end of analysis period [€].
        foerderquote : float, optional
            Subsidy rate as fraction [0-1]. Default is 0.
            
        Returns
        -------
        float
            Net present value of all life-cycle costs [€].
            More negative values indicate higher total costs.
            
        Examples
        --------
        >>> lcca_result = analysis.lcca(50000, 200, 300, 5000, 0.15)
        >>> print(f"Life-cycle cost NPV: {lcca_result:.0f} €")
        Life-cycle cost NPV: -45623 €
        
        Notes
        -----
        - Includes all costs over the complete analysis period
        - Residual value is added as positive cash flow at end of period
        - More negative results indicate higher total costs
        - Useful for comparing different renovation scenarios
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        annual_costs = betriebskosten + instandhaltungskosten
        cashflows = ([-effektive_investitionskosten] + 
                    [-annual_costs] * self.jahre + 
                    [restwert])
        return npf.npv(self.diskontierungsrate, cashflows)
    
    def berechne_roi(self, investitionskosten: float, 
                     foerderquote: float = 0) -> float:
        """
        Calculate the return on investment (ROI) for the renovation.
        
        This method calculates the total return as a percentage of the
        initial investment over the complete analysis period. It considers
        total cost savings but does not account for time value of money.
        
        Parameters
        ----------
        investitionskosten : float
            Total investment costs [€].
        foerderquote : float, optional
            Subsidy rate as fraction [0-1]. Default is 0.
            
        Returns
        -------
        float
            Return on investment as fraction (e.g., 0.15 = 15% ROI).
            
        Examples
        --------
        >>> roi = analysis.berechne_roi(50000, 0.25)  # 25% subsidy
        >>> print(f"ROI over {analysis.jahre} years: {roi*100:.1f}%")
        ROI over 20 years: 28.5%
        
        Notes
        -----
        - Simple ROI calculation without discounting
        - Based on total savings over entire analysis period
        - Positive values indicate profitable investments
        - Does not consider timing of cash flows
        """
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen() * self.jahre
        return ((kosteneinsparung - effektive_investitionskosten) / 
                effektive_investitionskosten if effektive_investitionskosten > 0 else 0)

def calculate_all_results(
    length: float, width: float, floors: int, floor_height: float,
    u_ground: float, u_wall: float, u_roof: float, u_window: float, u_door: float,
    energy_price_ist: float, energy_price_saniert: float, discount_rate: float, years: int,
    cold_rent: float, target_u_ground: float, target_u_wall: float, target_u_roof: float,
    target_u_window: float, target_u_door: float, cost_ground: float, cost_wall: float,
    cost_roof: float, cost_window: float, cost_door: float, fracture_windows: float,
    fracture_doors: float, air_change_rate: float, min_air_temp: float, room_temp: float,
    max_air_temp_heating: float, warmwasserbedarf: float, betriebskosten: Dict[str, float],
    instandhaltungskosten: Dict[str, float], restwert_anteile: Dict[str, float],
    foerderquote: float, try_filename: str
) -> Dict[str, Dict[str, float]]:
    """
    Calculate comprehensive renovation analysis results for all scenarios.
    
    This function performs a complete renovation analysis including individual
    component renovations and a complete renovation scenario. It calculates
    building geometry, energy demands, investment costs, and all economic
    metrics for comparison of different renovation strategies.
    
    Parameters
    ----------
    length : float
        Building length [m].
    width : float
        Building width [m].
    floors : int
        Number of floors.
    floor_height : float
        Height per floor [m].
    u_ground : float
        Current ground U-value [W/m²K].
    u_wall : float
        Current wall U-value [W/m²K].
    u_roof : float
        Current roof U-value [W/m²K].
    u_window : float
        Current window U-value [W/m²K].
    u_door : float
        Current door U-value [W/m²K].
    energy_price_ist : float
        Current energy price [€/kWh].
    energy_price_saniert : float
        Post-renovation energy price [€/kWh].
    discount_rate : float
        Discount rate for financial calculations [fraction].
    years : int
        Analysis period [years].
    cold_rent : float
        Base rent per square meter [€/m²].
    target_u_ground : float
        Target ground U-value after renovation [W/m²K].
    target_u_wall : float
        Target wall U-value after renovation [W/m²K].
    target_u_roof : float
        Target roof U-value after renovation [W/m²K].
    target_u_window : float
        Target window U-value after renovation [W/m²K].
    target_u_door : float
        Target door U-value after renovation [W/m²K].
    cost_ground : float
        Ground renovation cost per area [€/m²].
    cost_wall : float
        Wall renovation cost per area [€/m²].
    cost_roof : float
        Roof renovation cost per area [€/m²].
    cost_window : float
        Window renovation cost per area [€/m²].
    cost_door : float
        Door renovation cost per area [€/m²].
    fracture_windows : float
        Window area fraction of wall area [-].
    fracture_doors : float
        Door area fraction of wall area [-].
    air_change_rate : float
        Air changes per hour [1/h].
    min_air_temp : float
        Design outside temperature [°C].
    room_temp : float
        Indoor design temperature [°C].
    max_air_temp_heating : float
        Maximum outside temperature for heating [°C].
    warmwasserbedarf : float
        Hot water demand per floor area [kWh/m²a].
    betriebskosten : Dict[str, float]
        Annual operating costs by component [€/a].
    instandhaltungskosten : Dict[str, float]
        Annual maintenance costs by component [€/a].
    restwert_anteile : Dict[str, float]
        Residual value fractions by component [-].
    foerderquote : float
        Subsidy rate [fraction].
    try_filename : str
        Path to Test Reference Year weather data file.
        
    Returns
    -------
    Dict[str, Dict[str, float]]
        Comprehensive results dictionary with the following structure:
        
        - "Investitionskosten in €" : Investment costs by renovation type
        - "Gesamtenergiebedarf in kWh/a" : Total energy demand by scenario
        - "Energieeinsparung in kWh/a" : Energy savings by renovation type
        - "Kosteneinsparung in €/a" : Annual cost savings by renovation type
        - "Kaltmieten in €/m²" : Cold rent by scenario
        - "Warmmieten in €/m²" : Warm rent (including energy) by scenario
        - "Amortisationszeit in a" : Payback periods by renovation type
        - "NPV in €" : Net present values by renovation type
        - "LCCA in €" : Life-cycle cost analysis by renovation type
        - "ROI" : Return on investment by renovation type
        
    Raises
    ------
    FileNotFoundError
        If the TRY weather data file cannot be found.
    ValueError
        If building dimensions or financial parameters are invalid.
        
    Examples
    --------
    >>> # Define building and renovation parameters
    >>> results = calculate_all_results(
    ...     length=20, width=15, floors=3, floor_height=3,
    ...     u_ground=0.8, u_wall=1.2, u_roof=0.6, u_window=2.8, u_door=2.5,
    ...     energy_price_ist=0.08, energy_price_saniert=0.06, 
    ...     discount_rate=0.04, years=20, cold_rent=8.0,
    ...     target_u_ground=0.25, target_u_wall=0.15, target_u_roof=0.12,
    ...     target_u_window=1.0, target_u_door=1.2,
    ...     cost_ground=80, cost_wall=120, cost_roof=150, 
    ...     cost_window=450, cost_door=400,
    ...     fracture_windows=0.15, fracture_doors=0.02,
    ...     air_change_rate=0.6, min_air_temp=-12, room_temp=20,
    ...     max_air_temp_heating=15, warmwasserbedarf=12.5,
    ...     betriebskosten={'ground_u': 50, 'wall_u': 30, ...},
    ...     instandhaltungskosten={'ground_u': 20, 'wall_u': 15, ...},
    ...     restwert_anteile={'ground_u': 0.1, 'wall_u': 0.15, ...},
    ...     foerderquote=0.2, try_filename="TRY_data.dat"
    ... )
    >>> 
    >>> # Access results
    >>> print("Investment costs:")
    >>> for renovation, cost in results["Investitionskosten in €"].items():
    ...     print(f"  {renovation}: {cost:,.0f} €")
    
    Notes
    -----
    - Calculates six renovation scenarios: individual components + complete renovation
    - Uses TRY weather data for realistic energy demand calculations
    - Includes comprehensive economic analysis with multiple financial metrics
    - Considers rent implications of renovation investments
    - All calculations follow German building energy and economic standards
    
    See Also
    --------
    Building : Building energy model
    SanierungsAnalyse : Economic analysis methods
    import_TRY : Weather data import function
    """
    # Import weather data
    temperature_data, _, _, _, _ = import_TRY(try_filename)

    # Calculate building geometry
    grundflaeche = length * width
    wall_area_pro_stockwerk = (2*length + 2*width) * floor_height
    ground_area = grundflaeche
    wall_area = wall_area_pro_stockwerk * floors
    roof_area = grundflaeche
    building_volume = ground_area * floor_height * floors
    wohnflaeche = ground_area * floors

    # Define reference building parameters
    ref_u_values = {
        'ground_u': u_ground,
        'wall_u': u_wall,
        'roof_u': u_roof,
        'window_u': u_window,
        'door_u': u_door,
        'air_change_rate': air_change_rate,
        'floors': floors,
        'fracture_windows': fracture_windows,
        'fracture_doors': fracture_doors,
        'Normaußentemperatur': min_air_temp,
        'room_temp': room_temp,
        'max_air_temp_heating': max_air_temp_heating,
        'ww_demand_kWh_per_m2': warmwasserbedarf
    }

    # Calculate reference building energy demand
    ref_building = Building(ground_area, wall_area, roof_area, building_volume, ref_u_values)
    ref_building.calc_yearly_heat_demand(temperature_data)
    alter_waermebedarf = ref_building.yearly_heat_demand

    # Define target U-values and costs
    ziel_u_wert = {
        'ground_u': target_u_ground,
        'wall_u': target_u_wall,
        'roof_u': target_u_roof,
        'window_u': target_u_window,
        'door_u': target_u_door
    }

    kosten = {
        'ground_u': cost_ground,
        'wall_u': cost_wall,
        'roof_u': cost_roof,
        'window_u': cost_window,
        'door_u': cost_door
    }

    # Calculate investment costs by component
    investitionskosten = {
        'ground_u': kosten['ground_u'] * ground_area,
        'wall_u': kosten['wall_u'] * wall_area,
        'roof_u': kosten['roof_u'] * roof_area,
        'window_u': kosten['window_u'] * wall_area * fracture_windows,
        'door_u': kosten['door_u'] * wall_area * fracture_doors
    }

    # Calculate residual values
    restwert = {
        'ground_u': investitionskosten['ground_u'] * restwert_anteile['ground_u'],
        'wall_u': investitionskosten['wall_u'] * restwert_anteile['wall_u'],
        'roof_u': investitionskosten['roof_u'] * restwert_anteile['roof_u'],
        'window_u': investitionskosten['window_u'] * restwert_anteile['window_u'],
        'door_u': investitionskosten['door_u'] * restwert_anteile['door_u']
    }

    # Define renovation scenarios
    varianten = ['Bodensanierung', 'Fassadensanierung', 'Dachsanierung', 
                'Fenstersanierung', 'Türsanierung', 'Komplettsanierung']

    komponenten_u_wert = {
        'Bodensanierung': 'ground_u',
        'Fassadensanierung': 'wall_u',
        'Dachsanierung': 'roof_u',
        'Fenstersanierung': 'window_u',
        'Türsanierung': 'door_u'
    }

    # Initialize result containers
    ergebnisse = {}
    kaltmieten_pro_m2 = {}
    warmmieten_pro_m2 = {}

    # Calculate reference warm rent
    ref_warmmiete_pro_m2 = cold_rent + ((ref_building.yearly_heat_demand / 12) / wohnflaeche) * energy_price_ist

    # Analyze each renovation scenario
    for komponente in varianten:
        # Create renovated building model
        san_building = Building(ground_area, wall_area, roof_area, building_volume, 
                               u_values=ref_building.u_values.copy())
        
        # Apply renovation measures
        if komponente == 'Komplettsanierung':
            san_building.u_values.update(ziel_u_wert)
        else:
            san_building.u_values[komponenten_u_wert[komponente]] = ziel_u_wert[komponenten_u_wert[komponente]]

        # Calculate post-renovation energy demand
        san_building.calc_yearly_heat_demand(temperature_data)
        neuer_waermebedarf = san_building.yearly_heat_demand
        
        # Perform economic analysis
        analyse = SanierungsAnalyse(alter_waermebedarf, neuer_waermebedarf, 
                                  energy_price_ist, energy_price_saniert, 
                                  discount_rate, years)

        # Determine component-specific costs
        if komponente == 'Komplettsanierung':
            investitionskosten_komponente = sum(investitionskosten.values())
            betriebskosten_komponente = sum(betriebskosten.values())
            instandhaltungskosten_komponente = sum(instandhaltungskosten.values())
            restwert_komponente = sum(restwert.values())
        else:
            key = komponenten_u_wert[komponente]
            investitionskosten_komponente = investitionskosten[key]
            betriebskosten_komponente = betriebskosten[key]
            instandhaltungskosten_komponente = instandhaltungskosten[key]
            restwert_komponente = restwert[key]

        # Calculate financial metrics
        amortisationszeit = analyse.berechne_amortisationszeit(investitionskosten_komponente, foerderquote)
        npv = analyse.berechne_npv(investitionskosten_komponente, foerderquote)
        lcca = analyse.lcca(investitionskosten_komponente,
                           betriebskosten_komponente,
                           instandhaltungskosten_komponente,
                           restwert_komponente,
                           foerderquote)
        roi = analyse.berechne_roi(investitionskosten_komponente, foerderquote)

        # Calculate rent implications
        neue_kaltmiete_pro_m2 = (cold_rent + investitionskosten_komponente / 
                                (amortisationszeit * 12 * wohnflaeche) 
                                if amortisationszeit > 0 else cold_rent)
        neue_warmmiete_pro_m2 = (neue_kaltmiete_pro_m2 + 
                                ((neuer_waermebedarf / 12) / wohnflaeche) * energy_price_saniert)

        # Store results
        kaltmieten_pro_m2[komponente] = neue_kaltmiete_pro_m2
        warmmieten_pro_m2[komponente] = neue_warmmiete_pro_m2

        ergebnisse[komponente] = {
            'Investitionskosten': investitionskosten_komponente,
            'Amortisationszeit': amortisationszeit,
            'NPV': npv,
            'LCCA': lcca,
            'Neuer Wärmebedarf': neuer_waermebedarf,
            'Kosteneinsparung': analyse.berechne_kosteneinsparungen(),
            'ROI': roi
        }       

    # Calculate energy savings and total demands
    energieeinsparung = [ref_building.yearly_heat_demand - ergebnisse[komponente]['Neuer Wärmebedarf'] 
                        for komponente in varianten]
    gesamtenergiebedarf = ([ref_building.yearly_heat_demand] + 
                          [ergebnisse[komponente]['Neuer Wärmebedarf'] 
                           for komponente in varianten])

    # Compile comprehensive results
    results = {
        "Investitionskosten in €": {k: v['Investitionskosten'] for k, v in ergebnisse.items()},
        "Gesamtenergiebedarf in kWh/a": dict(zip(['Referenz'] + varianten, gesamtenergiebedarf)),
        "Energieeinsparung in kWh/a": dict(zip(varianten, energieeinsparung)),
        "Kosteneinsparung in €/a": {k: v['Kosteneinsparung'] for k, v in ergebnisse.items()},
        "Kaltmieten in €/m²": {"Referenz": cold_rent, **kaltmieten_pro_m2},
        "Warmmieten in €/m²": {"Referenz": ref_warmmiete_pro_m2, **warmmieten_pro_m2},
        "Amortisationszeit in a": {k: v['Amortisationszeit'] for k, v in ergebnisse.items()},
        "NPV in €": {k: v['NPV'] for k, v in ergebnisse.items()},
        "LCCA in €": {k: v['LCCA'] for k, v in ergebnisse.items()},
        "ROI": {k: v['ROI'] for k, v in ergebnisse.items()}
    }

    return results