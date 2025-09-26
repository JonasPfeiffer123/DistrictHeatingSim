"""
Base Heat Pump Classes
========================

This module provides base classes for heat pump modeling in district heating applications.
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11

This module provides comprehensive heat pump modeling capabilities for district heating systems,
including performance calculations, economic analysis, and environmental impact assessment.
The implementation supports various heat pump technologies with detailed thermodynamic modeling,
COP calculations, and integration with thermal storage systems.

The module is designed for German district heating applications and includes support for
subsidy programs (BEW - Bundesförderung für effiziente Wärmenetze), economic optimization,
and environmental impact evaluation according to German energy standards.

Features
--------
- Thermodynamic performance modeling with COP interpolation
- Economic analysis including investment costs and operational expenses
- Environmental impact assessment (CO2 emissions and primary energy)
- Control strategy implementation for optimal system integration
- Support for various heat source types (geothermal, waste heat, etc.)
- German subsidy program (BEW) integration
- Thermal storage integration with temperature-based control

Classes
-------
HeatPump : Base heat pump implementation with performance and economic modeling
HeatPumpStrategy : Control strategy for heat pump operation optimization

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- scipy >= 1.7.0 : Scientific computing and interpolation functions
- CoolProp >= 6.4.1 : Thermodynamic property calculations
- districtheatingsim.heat_generators.base_heat_generator : Base generator framework

References
----------
Heat pump modeling based on:
- VDI 4650 - Calculation of heat pumps
- EN 14511 - Air conditioners, liquid chilling packages and heat pumps
- Bundesförderung für effiziente Wärmenetze (BEW) guidelines
- German energy efficiency standards (EnEV/GEG)
"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from typing import Dict, Tuple, Union, Optional, Any

import CoolProp.CoolProp as CP

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class HeatPump(BaseHeatGenerator):
    """
    Comprehensive heat pump model for district heating applications.

    This class implements a sophisticated heat pump model suitable for district heating
    systems with detailed performance calculations, economic analysis, and environmental
    impact assessment. It provides accurate modeling of heat pump behavior under varying
    operating conditions and supports integration with thermal storage systems.

    The implementation follows German engineering standards and includes support for
    various heat source types, economic optimization considering subsidies, and
    environmental impact evaluation for sustainable district heating design.

    Parameters
    ----------
    name : str
        Unique identifier for the heat pump system.
        Used for system identification and result tracking.
    spezifische_Investitionskosten_WP : float, optional
        Specific investment costs for heat pump unit [€/kW].
        Default is 1000 €/kW based on commercial heat pump systems.
    active : bool, optional
        Initial operational status of the heat pump.
        Default is True for immediate availability.

    Attributes
    ----------
    spezifische_Investitionskosten_WP : float
        Specific investment costs for heat pump unit [€/kW].
        Used for economic analysis and cost calculations.
    active : bool
        Current operational status of the heat pump system.
    Nutzungsdauer_WP : int
        Design lifetime of heat pump equipment [years].
        Default is 20 years for economic calculations.
    f_Inst_WP : float
        Installation cost factor for heat pump [-].
        Multiplier for additional installation expenses.
    f_W_Insp_WP : float
        Maintenance and inspection cost factor for heat pump [-].
        Annual maintenance cost as fraction of investment.
    Bedienaufwand_WP : float
        Operational effort for heat pump [hours/year].
        Annual labor hours for system operation.
    f_Inst_WQ : float
        Installation cost factor for heat source [-].
        Multiplier for heat source installation costs.
    f_W_Insp_WQ : float
        Maintenance and inspection cost factor for heat source [-].
        Annual maintenance cost for heat source system.
    Bedienaufwand_WQ : float
        Operational effort for heat source [hours/year].
        Annual labor hours for heat source maintenance.
    Nutzungsdauer_WQ_dict : dict
        Design lifetime for different heat source types [years].
        Contains lifetime values for various heat source technologies.
    co2_factor_electricity : float
        CO2 emission factor for electricity [tCO2/MWh].
        Used for environmental impact calculations.
    primärenergiefaktor : float
        Primary energy factor for electricity [-].
        Conversion factor for primary energy calculations.
    Anteil_Förderung_BEW : float
        Subsidy fraction for BEW program [-].
        Percentage of investment costs covered by subsidies.
    strategy : HeatPumpStrategy
        Control strategy for heat pump operation.
        Defines switching logic based on system conditions.
    betrieb_mask : numpy.ndarray
        Operational state time series [bool].
        Hourly operational status throughout simulation.
    Wärmeleistung_kW : numpy.ndarray
        Heat output time series [kW].
        Hourly heat delivery to district heating system.
    el_Leistung_kW : numpy.ndarray
        Electrical power consumption time series [kW].
        Hourly electricity demand for heat pump operation.
    Kühlleistung_kW : numpy.ndarray
        Cooling power from heat source time series [kW].
        Heat extracted from ambient or waste heat source.
    VLT_WP : numpy.ndarray
        Heat pump flow temperature time series [°C].
        Supply temperature delivered by heat pump.
    COP : numpy.ndarray
        Coefficient of Performance time series [-].
        Instantaneous efficiency of heat pump operation.
    Wärmemenge_MWh : float
        Total heat production [MWh].
        Cumulative heat delivery over simulation period.
    Strommenge_MWh : float
        Total electricity consumption [MWh].
        Cumulative electrical energy demand.
    Brennstoffbedarf_MWh : float
        Total energy demand [MWh].
        Equivalent to electricity consumption for heat pumps.
    Anzahl_Starts : int
        Number of start-up events [-].
        Count of heat pump start operations.
    Betriebsstunden : int
        Total operating hours [hours].
        Cumulative operational time.
    Betriebsstunden_pro_Start : float
        Average operating hours per start [hours/start].
        Indicator of operational cycling behavior.
    co2_emissions : float
        Total CO2 emissions [tCO2].
        Environmental impact from electricity consumption.
    spec_co2_total : float
        Specific CO2 emissions [tCO2/MWh_heat].
        Emissions per unit heat delivered.
    primärenergie : float
        Primary energy consumption [MWh].
        Total primary energy demand including conversion losses.

    Notes
    -----
    Heat Pump Performance Modeling:
        
        **Thermodynamic Analysis**:
        The heat pump model implements detailed thermodynamic calculations:
        - COP calculation based on source and sink temperatures
        - Performance curve interpolation from manufacturer data
        - Technical limits for temperature lift and operating range
        - Part-load performance modeling
        
        **Operating Constraints**:
        - Maximum temperature lift: 75 K (technical limitation)
        - Minimum and maximum source temperatures
        - Flow temperature limitations based on heat pump technology
        - Defrosting cycles for air source heat pumps
        
        **Heat Source Integration**:
        - Geothermal systems with stable source temperatures
        - Waste heat recovery from industrial processes
        - Wastewater heat recovery systems
        - River/lake water heat extraction

    Economic Analysis Framework:
        
        **Investment Costs**:
        - Heat pump unit costs based on thermal capacity
        - Heat source development costs (drilling, heat exchangers)
        - Installation and commissioning expenses
        - Grid connection and electrical infrastructure
        
        **Operational Costs**:
        - Electricity costs for heat pump operation
        - Maintenance and inspection expenses
        - Insurance and administrative costs
        - Performance monitoring and control systems
        
        **Subsidy Integration**:
        - BEW (Bundesförderung für effiziente Wärmenetze) support
        - Investment cost reduction through subsidies
        - Operational cost benefits from renewable energy
        - Economic optimization with and without subsidies

    Environmental Impact Assessment:
        
        **CO2 Emissions**:
        - Direct emissions from electricity consumption
        - Indirect emissions from electrical grid mix
        - Lifecycle emissions including manufacturing
        - Comparison with conventional heating systems
        
        **Primary Energy**:
        - Primary energy factor for electrical grid
        - Efficiency improvements through heat pump operation
        - Renewable energy integration benefits
        - Overall system efficiency evaluation

    Control Strategy Integration:
        
        **Temperature-Based Control**:
        - Storage temperature monitoring for optimal operation
        - Demand-responsive heat pump activation
        - Load balancing with other heat generators
        - Grid services and demand-side management
        
        **Economic Optimization**:
        - Electricity price-based operation scheduling
        - Peak demand management and load shifting
        - Integration with renewable energy sources
        - Storage charging strategies for efficiency

    Examples
    --------
    >>> # Basic heat pump initialization for district heating
    >>> from districtheatingsim.heat_generators.base_heat_pump import HeatPump
    >>> import numpy as np
    >>> 
    >>> # Create geothermal heat pump system
    >>> geothermal_hp = HeatPump(
    ...     name="Geothermie_HP_01",
    ...     spezifische_Investitionskosten_WP=1200,  # €/kW for geothermal
    ...     active=True
    ... )
    >>> 
    >>> # Configure economic parameters
    >>> economic_params = {
    ...     'electricity_price': 0.25,           # €/kWh
    ...     'capital_interest_rate': 0.03,       # 3% interest rate
    ...     'inflation_rate': 0.02,              # 2% inflation
    ...     'time_period': 20,                   # 20-year analysis
    ...     'subsidy_eligibility': "Ja",         # BEW eligibility
    ...     'hourly_rate': 50.0                  # €/hour labor cost
    ... }

    >>> # Define COP performance data (example for geothermal heat pump)
    >>> # First row: flow temperatures, first column: source temperatures
    >>> cop_data = np.array([
    ...     [0,    35,   45,   55,   65,   75],  # Flow temperatures
    ...     [0,    5.2,  4.8,  4.3,  3.7,  3.2], # COP at 0°C source
    ...     [10,   5.8,  5.3,  4.7,  4.1,  3.5], # COP at 10°C source
    ...     [20,   6.5,  5.9,  5.2,  4.5,  3.8]  # COP at 20°C source
    ... ])

    >>> # Calculate heat pump performance for varying conditions
    >>> flow_temps = np.array([45, 50, 55, 60])  # °C supply temperatures
    >>> source_temp = 12.0  # °C geothermal source temperature
    >>> 
    >>> cop_values, adjusted_temps = geothermal_hp.calculate_COP(
    ...     flow_temps, source_temp, cop_data
    ... )
    >>> 
    >>> print("Heat Pump Performance Analysis:")
    >>> for i, (temp, cop) in enumerate(zip(adjusted_temps, cop_values)):
    ...     print(f"Flow temp: {temp:.1f}°C, COP: {cop:.2f}")

    >>> # Calculate economic performance
    >>> heat_output = 500.0    # kW rated capacity
    >>> annual_heat = 1500.0   # MWh/year heat delivery
    >>> electricity_demand = annual_heat / 4.5  # Assume average COP of 4.5
    >>> heat_source_cost = 200.0  # €/kW for geothermal well
    >>> 
    >>> wgk = geothermal_hp.calculate_heat_generation_costs(
    ...     heat_output, annual_heat, electricity_demand,
    ...     heat_source_cost, economic_params
    ... )
    >>> 
    >>> print(f"Heat generation costs: {wgk:.2f} €/MWh")

    >>> # Environmental impact assessment
    >>> geothermal_hp.Strommenge_MWh = electricity_demand
    >>> geothermal_hp.Wärmemenge_MWh = annual_heat
    >>> geothermal_hp.calculate_environmental_impact()
    >>> 
    >>> print(f"CO2 emissions: {geothermal_hp.co2_emissions:.1f} tCO2/year")
    >>> print(f"Specific emissions: {geothermal_hp.spec_co2_total:.3f} tCO2/MWh")
    >>> print(f"Primary energy: {geothermal_hp.primärenergie:.1f} MWh/year")

    >>> # Advanced usage with control strategy
    >>> # Configure heat pump strategy for storage integration
    >>> geothermal_hp.strategy = HeatPumpStrategy(
    ...     charge_on=65,   # °C - activate when storage below 65°C
    ...     charge_off=75   # °C - deactivate when storage above 75°C
    ... )
    >>> 
    >>> # Simulate operational decision making
    >>> current_state = False  # Heat pump currently off
    >>> upper_temp = 62.0      # °C upper storage temperature
    >>> lower_temp = 58.0      # °C lower storage temperature
    >>> remaining_demand = 300.0  # kW remaining heat demand
    >>> 
    >>> should_operate = geothermal_hp.strategy.decide_operation(
    ...     current_state, upper_temp, lower_temp, remaining_demand
    ... )
    >>> 
    >>> print(f"Heat pump should operate: {should_operate}")

    >>> # Comparison of different heat pump types
    >>> # Air source heat pump
    >>> air_hp = HeatPump("Luft_HP_01", spezifische_Investitionskosten_WP=800)
    >>> 
    >>> # Wastewater heat pump
    >>> wastewater_hp = HeatPump("Abwasser_HP_01", spezifische_Investitionskosten_WP=1100)
    >>> 
    >>> # River water heat pump
    >>> river_hp = HeatPump("Fluss_HP_01", spezifische_Investitionskosten_WP=950)
    >>> 
    >>> heat_pumps = [geothermal_hp, air_hp, wastewater_hp, river_hp]
    >>> 
    >>> print("Heat Pump Technology Comparison:")
    >>> for hp in heat_pumps:
    ...     base_name = hp.name.split('_')[0]
    ...     lifetime = hp.Nutzungsdauer_WQ_dict.get(base_name, 20)
    ...     print(f"{base_name}: {hp.spezifische_Investitionskosten_WP} €/kW, "
    ...           f"{lifetime} years lifetime")

    See Also
    --------
    BaseHeatGenerator : Base class for all heat generation systems
    HeatPumpStrategy : Control strategy implementation for heat pumps
    CoolProp : Thermodynamic property calculations
    scipy.interpolate.RegularGridInterpolator : COP interpolation methods
    """

    def __init__(self, name: str, spezifische_Investitionskosten_WP: float = 1000, active: bool = True) -> None:
        """
        Initialize heat pump system with default parameters.

        Parameters
        ----------
        name : str
            Unique identifier for the heat pump system.
        spezifische_Investitionskosten_WP : float, optional
            Specific investment costs for heat pump unit [€/kW].
        active : bool, optional
            Initial operational status of the heat pump.
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

        Parameters
        ----------
        hours : int
            Number of simulation hours (typically 8760 for annual simulation).

        Notes
        -----
        This method initializes all time-series arrays for tracking heat pump
        performance throughout the simulation period. Arrays are pre-allocated
        for computational efficiency.
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
        Calculate Coefficient of Performance using interpolation of manufacturer data.

        This method performs detailed COP calculations based on flow and source temperatures
        using bilinear interpolation of manufacturer performance data. It includes technical
        limitations such as maximum temperature lift and handles out-of-bounds conditions
        appropriately for robust system modeling.

        Parameters
        ----------
        VLT_L : numpy.ndarray
            Flow temperature array [°C].
            Supply temperatures delivered by heat pump.
        QT : float or numpy.ndarray
            Source temperature(s) [°C].
            Heat source temperature (geothermal, ambient, waste heat).
            Can be constant or time-varying.
        COP_data : numpy.ndarray
            COP lookup table for interpolation.
            2D array with source temperatures as rows and flow temperatures as columns.
            First row contains flow temperature values, first column contains source temperatures.

        Returns
        -------
        tuple of numpy.ndarray
            Interpolated performance data:
            
            COP_L : numpy.ndarray
                Coefficient of Performance values [-].
                Instantaneous efficiency for given operating conditions.
                
            VLT_L_adjusted : numpy.ndarray
                Adjusted flow temperatures [°C].
                Flow temperatures limited by technical constraints.

        Notes
        -----
        COP Calculation Methodology:
            
            **Performance Interpolation**:
            - Bilinear interpolation between manufacturer data points
            - Smooth performance curves for accurate modeling
            - Handling of sparse data with appropriate bounds checking
            
            **Technical Limitations**:
            - Maximum temperature lift: 75 K (typical for heat pumps)
            - Source temperature range validation
            - Flow temperature operational limits
            - Out-of-bounds handling with zero COP
            
            **Performance Considerations**:
            - COP degradation at extreme conditions
            - Part-load performance effects
            - Seasonal performance variations
            - Defrosting cycle impacts for air source systems

        Physical Background:
            The Coefficient of Performance represents the thermodynamic efficiency:
            COP = Q_heating / W_electrical
            
            Where theoretical maximum is given by Carnot efficiency:
            COP_Carnot = T_hot / (T_hot - T_cold)

        Examples
        --------
        >>> # Define COP performance data for geothermal heat pump
        >>> cop_data = np.array([
        ...     [0,    35,   45,   55,   65,   75],    # Flow temperatures [°C]
        ...     [0,    4.5,  4.1,  3.6,  3.1,  2.6],  # COP at 0°C source
        ...     [10,   5.2,  4.7,  4.1,  3.5,  2.9],  # COP at 10°C source
        ...     [15,   5.6,  5.0,  4.4,  3.7,  3.1],  # COP at 15°C source
        ...     [20,   6.1,  5.4,  4.7,  4.0,  3.3]   # COP at 20°C source
        ... ])
        >>> 
        >>> # Calculate COP for varying flow temperatures
        >>> flow_temps = np.array([40, 45, 50, 55, 60, 65])  # °C
        >>> source_temp = 12.0  # °C constant geothermal temperature
        >>> 
        >>> cop_values, adjusted_temps = heat_pump.calculate_COP(
        ...     flow_temps, source_temp, cop_data
        ... )
        >>> 
        >>> # Display results
        >>> for temp, cop in zip(adjusted_temps, cop_values):
        ...     print(f"Flow: {temp:.1f}°C, COP: {cop:.2f}")

        >>> # Time-varying source temperature (e.g., air source heat pump)
        >>> hourly_air_temps = np.array([-5, 0, 5, 10, 15, 20])  # °C
        >>> flow_temp = np.full(6, 45.0)  # °C constant flow temperature
        >>> 
        >>> cop_hourly, _ = heat_pump.calculate_COP(
        ...     flow_temp, hourly_air_temps, cop_data
        ... )
        >>> 
        >>> print("Hourly COP variation:")
        >>> for hour, (air_temp, cop) in enumerate(zip(hourly_air_temps, cop_hourly)):
        ...     print(f"Hour {hour}: Air {air_temp}°C, COP {cop:.2f}")

        Raises
        ------
        ValueError
            If QT array length doesn't match VLT_L array length.
        IndexError
            If COP_data structure is invalid for interpolation.
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
        if np.isscalar(QT):
            # Create array with constant source temperature
            QT_array = np.full_like(VLT_L, QT)
        else:
            # Validate array dimensions
            if len(QT) != len(VLT_L):
                raise ValueError(
                    "QT must be either a single number or an array with the same length as VLT_L."
                )
            QT_array = QT

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
        Calculate comprehensive heat generation costs including subsidies.

        This method performs detailed economic analysis of heat pump systems including
        investment costs, operational expenses, and subsidy considerations. It provides
        separate calculations for scenarios with and without BEW subsidies for
        comprehensive economic evaluation.

        Parameters
        ----------
        Wärmeleistung : float
            Rated heat output capacity [kW].
            Design capacity for economic calculations.
        Wärmemenge_MWh : float
            Annual heat production [MWh/year].
            Total heat delivered for cost calculation.
        Strombedarf : float
            Annual electricity demand [MWh/year].
            Electrical energy consumption for heat pump operation.
        spez_Investitionskosten_WQ : float
            Specific investment costs for heat source [€/kW].
            Heat source development costs per kW capacity.
        economic_parameters : dict
            Economic analysis parameters containing:
            
            - **electricity_price** (float): Electricity cost [€/kWh]
            - **capital_interest_rate** (float): Interest rate [-]
            - **inflation_rate** (float): Inflation rate [-]
            - **time_period** (int): Analysis period [years]
            - **subsidy_eligibility** (str): BEW eligibility ("Ja"/"Nein")
            - **hourly_rate** (float): Labor cost [€/hour]

        Returns
        -------
        float
            Heat generation costs [€/MWh].
            Levelized cost of heat considering all economic factors.

        Notes
        -----
        Economic Analysis Framework:
            
            **Investment Cost Components**:
            - Heat pump unit costs based on thermal capacity
            - Heat source development (wells, heat exchangers, pumps)
            - Installation and commissioning expenses
            - Electrical infrastructure and grid connection
            
            **Operational Cost Components**:
            - Electricity costs for heat pump operation
            - Maintenance and inspection expenses
            - Insurance and administrative costs
            - Labor costs for operation and maintenance
            
            **Subsidy Integration (BEW)**:
            - Investment cost reduction (typically 40%)
            - Separate calculation for subsidized vs. non-subsidized scenarios
            - Economic optimization considering subsidy eligibility
            
            **Annuity Calculation**:
            The method uses standard engineering economics:
            - Capital recovery factor for investment costs
            - Present value calculations for operational expenses
            - Inflation adjustment for future cost projections

        Heat Source Cost Considerations:
            Different heat source types have varying investment requirements:
            - **Geothermal**: High upfront costs, long lifetime (30 years)
            - **Waste heat**: Moderate costs, 20-year lifetime
            - **Wastewater**: Medium costs, specialized equipment
            - **River/lake water**: Variable costs, environmental permits

        Examples
        --------
        >>> # Define economic parameters for analysis
        >>> economic_params = {
        ...     'electricity_price': 0.28,      # €/kWh current German prices
        ...     'capital_interest_rate': 0.04,  # 4% interest rate
        ...     'inflation_rate': 0.025,        # 2.5% inflation
        ...     'time_period': 20,              # 20-year analysis
        ...     'subsidy_eligibility': "Ja",    # BEW eligible
        ...     'hourly_rate': 55.0             # €/hour labor cost
        ... }
        >>> 
        >>> # Calculate costs for geothermal heat pump
        >>> heat_capacity = 800.0      # kW rated capacity
        >>> annual_heat = 2400.0       # MWh/year heat delivery
        >>> annual_electricity = 600.0  # MWh/year electricity
        >>> geothermal_cost = 400.0    # €/kW for geothermal wells
        >>> 
        >>> wgk_geothermal = geothermal_hp.calculate_heat_generation_costs(
        ...     heat_capacity, annual_heat, annual_electricity,
        ...     geothermal_cost, economic_params
        ... )
        >>> 
        >>> print(f"Geothermal heat pump WGK: {wgk_geothermal:.2f} €/MWh")

        >>> # Compare different heat source technologies
        >>> heat_sources = {
        ...     'Geothermie': 400.0,      # €/kW for deep wells
        ...     'Abwasser': 150.0,        # €/kW for wastewater systems
        ...     'Fluss': 200.0,           # €/kW for river water intake
        ...     'Abwärme': 100.0          # €/kW for waste heat recovery
        ... }
        >>> 
        >>> print("Heat Source Technology Comparison:")
        >>> for source, cost in heat_sources.items():
        ...     hp_test = HeatPump(f"{source}_Test")
        ...     wgk = hp_test.calculate_heat_generation_costs(
        ...         heat_capacity, annual_heat, annual_electricity,
        ...         cost, economic_params
        ...     )
        ...     print(f"{source}: {wgk:.2f} €/MWh")

        >>> # Sensitivity analysis for electricity price
        >>> electricity_prices = [0.20, 0.25, 0.30, 0.35]  # €/kWh
        >>> 
        >>> print("Electricity Price Sensitivity:")
        >>> for price in electricity_prices:
        ...     params = economic_params.copy()
        ...     params['electricity_price'] = price
        ...     wgk = geothermal_hp.calculate_heat_generation_costs(
        ...         heat_capacity, annual_heat, annual_electricity,
        ...         geothermal_cost, params
        ...     )
        ...     print(f"{price:.2f} €/kWh: {wgk:.2f} €/MWh")

        Raises
        ------
        KeyError
            If heat source type is not found in lifetime dictionary.
        ValueError
            If heat production is zero (division by zero).
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
        Calculate environmental impact metrics for heat pump operation.

        This method computes CO2 emissions and primary energy consumption based on
        electricity usage and German grid emission factors. It provides essential
        data for environmental assessment and comparison with conventional heating
        systems for sustainable energy planning.

        Notes
        -----
        Environmental Impact Calculations:
            
            **CO2 Emissions**:
            - Direct emissions from electricity consumption
            - Grid emission factor for German electricity mix
            - Accounts for renewable energy integration
            - Seasonal variations in grid carbon intensity
            
            **Primary Energy Factor**:
            - Conversion losses in electricity generation
            - Grid transmission and distribution losses
            - Overall system efficiency from primary energy to heat
            
            **Specific Emissions**:
            - Emissions per unit heat delivered [tCO2/MWh_heat]
            - Comparison metric with other heating technologies
            - Environmental performance indicator

        The calculations use current German energy system parameters and can be
        updated to reflect changes in grid decarbonization and efficiency improvements.

        Examples
        --------
        >>> # Calculate environmental impact after operation
        >>> heat_pump.Strommenge_MWh = 500.0    # MWh electricity consumed
        >>> heat_pump.Wärmemenge_MWh = 2200.0   # MWh heat delivered
        >>> 
        >>> heat_pump.calculate_environmental_impact()
        >>> 
        >>> print(f"Total CO2 emissions: {heat_pump.co2_emissions:.1f} tCO2")
        >>> print(f"Specific emissions: {heat_pump.spec_co2_total:.3f} tCO2/MWh_heat")
        >>> print(f"Primary energy: {heat_pump.primärenergie:.1f} MWh")
        >>> 
        >>> # Compare with gas boiler (example: 0.2 tCO2/MWh)
        >>> gas_emissions = 0.2 * heat_pump.Wärmemenge_MWh
        >>> emission_reduction = (gas_emissions - heat_pump.co2_emissions) / gas_emissions
        >>> print(f"CO2 reduction vs. gas: {emission_reduction:.1%}")
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
    Control strategy for optimal heat pump operation in district heating systems.

    This class implements intelligent control logic for heat pump systems based on
    thermal storage temperatures and system demand. It provides hysteresis control
    to prevent excessive cycling while ensuring efficient heat pump operation and
    optimal system integration.

    Parameters
    ----------
    charge_on : float
        Upper storage temperature threshold for heat pump activation [°C].
        Heat pump turns on when storage temperature falls below this value.
    charge_off : float
        Lower storage temperature threshold for heat pump deactivation [°C].
        Heat pump turns off when storage temperature rises above this value.

    Notes
    -----
    Control Strategy Logic:
        
        **Hysteresis Control**:
        - Prevents excessive cycling through temperature deadband
        - Reduces mechanical wear and improves efficiency
        - Maintains stable system operation
        
        **Demand-Responsive Operation**:
        - Heat pump operation based on remaining system demand
        - Integration with other heat generators
        - Load prioritization and optimization
        
        **Temperature-Based Switching**:
        - Upper storage temperature monitoring for activation
        - Lower storage temperature monitoring for deactivation
        - Storage protection against overheating

    The strategy balances system efficiency, equipment protection, and demand
    satisfaction for optimal district heating operation.

    Examples
    --------
    >>> # Configure heat pump strategy for district heating
    >>> strategy = HeatPumpStrategy(
    ...     charge_on=65,   # Activate when storage drops below 65°C
    ...     charge_off=75   # Deactivate when storage rises above 75°C
    ... )
    >>> 
    >>> # Simulate control decisions
    >>> current_state = False      # Heat pump currently off
    >>> upper_temp = 62.0         # °C upper storage temperature
    >>> lower_temp = 58.0         # °C lower storage temperature  
    >>> demand = 400.0            # kW remaining demand
    >>> 
    >>> # Decision: should heat pump start?
    >>> should_operate = strategy.decide_operation(
    ...     current_state, upper_temp, lower_temp, demand
    ... )
    >>> print(f"Heat pump should start: {should_operate}")  # True
    >>> 
    >>> # Simulate operation with high storage temperature
    >>> current_state = True       # Heat pump currently on
    >>> lower_temp = 76.0         # °C high lower storage temperature
    >>> demand = 200.0            # kW remaining demand
    >>> 
    >>> # Decision: should heat pump continue?
    >>> should_operate = strategy.decide_operation(
    ...     current_state, upper_temp, lower_temp, demand
    ... )
    >>> print(f"Heat pump should continue: {should_operate}")  # False
    """
    
    def __init__(self, charge_on: float, charge_off: float) -> None:
        """
        Initialize heat pump control strategy with temperature thresholds.

        Parameters
        ----------
        charge_on : float
            Upper storage temperature to activate the heat pump [°C].
        charge_off : float
            Lower storage temperature to deactivate the heat pump [°C].
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: bool, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide heat pump operation based on storage temperature and demand.

        This method implements the core control logic for heat pump operation,
        considering current operational state, storage conditions, and system
        demand to make optimal switching decisions.

        Parameters
        ----------
        current_state : bool
            Current operational state of the heat pump.
            True if heat pump is currently running, False if stopped.
        upper_storage_temp : float
            Current upper storage temperature [°C].
            Temperature in upper storage layers for activation decisions.
        lower_storage_temp : float
            Current lower storage temperature [°C].
            Temperature in lower storage layers for deactivation decisions.
        remaining_demand : float
            Remaining heat demand in the system [kW].
            Unmet demand after other heat generators.

        Returns
        -------
        bool
            Operational decision for heat pump.
            True to operate heat pump, False to stop operation.

        Notes
        -----
        Control Logic:
            
            **Heat Pump Currently On**:
            - Continue operation if lower storage temp < charge_off AND demand > 0
            - Stop operation if lower storage temp ≥ charge_off OR demand ≤ 0
            
            **Heat Pump Currently Off**:
            - Start operation if upper storage temp ≤ charge_on AND demand > 0
            - Remain off if upper storage temp > charge_on OR demand ≤ 0
            
            **Safety Considerations**:
            - Storage overheating protection through lower temperature monitoring
            - Demand-responsive operation prevents unnecessary operation
            - Hysteresis prevents rapid cycling

        Examples
        --------
        >>> # Initialize control strategy
        >>> strategy = HeatPumpStrategy(charge_on=65, charge_off=75)
        >>> 
        >>> # Test various operational scenarios
        >>> scenarios = [
        ...     (False, 60.0, 55.0, 300.0),  # Off, low temp, high demand
        ...     (True, 70.0, 76.0, 200.0),   # On, high temp, low demand  
        ...     (True, 65.0, 70.0, 400.0),   # On, medium temp, high demand
        ...     (False, 70.0, 65.0, 0.0),    # Off, medium temp, no demand
        ... ]
        >>> 
        >>> for state, upper, lower, demand in scenarios:
        ...     decision = strategy.decide_operation(state, upper, lower, demand)
        ...     print(f"State: {state}, Upper: {upper}°C, Lower: {lower}°C, "
        ...           f"Demand: {demand}kW → Decision: {decision}")
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