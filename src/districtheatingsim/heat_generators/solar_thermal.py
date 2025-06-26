"""
Filename: solar_thermal.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-11
Description: Solar thermal collector system modeling for district heating applications.

This module provides comprehensive solar thermal collector system modeling capabilities
for district heating applications. The implementation includes detailed thermal performance
modeling, economic analysis, and environmental impact assessment for solar thermal energy
generation with integrated thermal storage systems.

The module supports both flat-plate and vacuum tube collector technologies with advanced
solar radiation calculations, thermal efficiency modeling, and optimization capabilities
for optimal district heating system integration.

Features
--------
- Comprehensive solar thermal collector modeling with efficiency calculations
- Support for flat-plate and vacuum tube collector technologies
- Advanced solar radiation calculation including incidence angle modifiers
- Integrated thermal storage system modeling with temperature stratification
- Economic analysis with lifecycle cost assessment and subsidy integration
- Environmental impact evaluation with zero-emission heat generation
- Optimization capabilities for collector area and storage volume sizing

Technical Specifications
------------------------
**Solar Collector Technologies**:
- Flat-plate collectors with detailed thermal performance modeling
- Vacuum tube collectors with enhanced efficiency characteristics
- Incidence angle modifier calculations for accurate yield prediction
- Temperature-dependent efficiency modeling with thermal losses
- Stagnation protection and overheating prevention algorithms

**Thermal Storage Integration**:
- Temperature-stratified storage tank modeling
- Heat loss calculations with ambient temperature dependency
- Storage charging and discharging optimization
- Integration with district heating supply and return temperatures
- Storage volume optimization for seasonal energy storage

**Solar Radiation Modeling**:
- Detailed solar position calculations for any geographic location
- Beam and diffuse radiation separation with collector orientation
- Incidence angle modifier application for realistic performance
- Weather data integration with Test Reference Year (TRY) support
- Albedo consideration for ground-reflected radiation

**Economic Analysis**:
- Comprehensive cost modeling including collector and storage costs
- Technology-specific cost functions for flat-plate and vacuum collectors
- Subsidy integration with German renewable energy incentives (BEW)
- Levelized cost of heat calculations for economic comparison
- Investment optimization with capacity and storage sizing

**Environmental Assessment**:
- Zero CO2 emissions for renewable solar heat generation
- Primary energy factor analysis for sustainability assessment
- Environmental benefit quantification compared to fossil alternatives
- Life cycle assessment integration for comprehensive evaluation

Classes
-------
SolarThermal : Main solar thermal collector system class
SolarThermalStrategy : Control strategy for solar thermal operation

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- math : Mathematical functions for thermal calculations
- districtheatingsim.heat_generators.solar_radiation : Solar radiation calculation module
- districtheatingsim.heat_generators.base_heat_generator : Base classes for heat generators

Applications
------------
The module supports solar thermal applications including:
- Large-scale district heating solar thermal systems
- Seasonal energy storage with solar collector fields
- Solar thermal integration with conventional heating systems
- Renewable energy system optimization and economic analysis

References
----------
Solar thermal modeling based on:
- EN 12975 thermal performance of solar collectors
- ScenoCalc District Heating 2.0 calculation methodology
- VDI 6002 solar heating systems design guidelines
- German solar thermal standards and certification procedures
"""

import numpy as np
from math import pi, exp, log, sqrt
from typing import Dict, Tuple, List, Optional, Union

from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation
from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class SolarThermal(BaseHeatGenerator):
    """
    Comprehensive solar thermal collector system for district heating applications.

    This class models solar thermal collector systems including flat-plate and vacuum
    tube collectors with integrated thermal storage for district heating applications.
    The implementation provides detailed thermal performance modeling, economic analysis,
    and environmental impact assessment for renewable solar heat generation.

    The solar thermal model includes advanced solar radiation calculations, temperature-
    dependent efficiency modeling, thermal storage integration, and optimization
    capabilities for optimal district heating system configuration.

    Parameters
    ----------
    name : str
        Unique identifier for the solar thermal system.
        Used for system identification and result tracking.
    bruttofläche_STA : float
        Gross collector area of the solar thermal system [m²].
        Total area including frame and mounting structures.
    vs : float
        Volume of the thermal storage system [m³].
        Capacity for seasonal energy storage and load balancing.
    Typ : str
        Type of solar collector technology.
        Options: "Flachkollektor" (flat-plate) or "Vakuumröhrenkollektor" (vacuum tube).
    kosten_speicher_spez : float, optional
        Specific costs for thermal storage system [€/m³].
        Investment cost per unit storage volume (default: 750 €/m³).
    kosten_fk_spez : float, optional
        Specific costs for flat-plate collectors [€/m²].
        Investment cost per unit collector area (default: 430 €/m²).
    kosten_vrk_spez : float, optional
        Specific costs for vacuum tube collectors [€/m²].
        Investment cost per unit collector area (default: 590 €/m²).
    Tsmax : float, optional
        Maximum storage temperature [°C].
        Upper temperature limit for thermal storage (default: 90°C).
    Longitude : float, optional
        Longitude of installation site [degrees].
        Geographic coordinate for solar calculations (default: -14.4222°).
    STD_Longitude : float, optional
        Standard longitude for time zone [degrees].
        Reference longitude for local time calculation (default: -15°).
    Latitude : float, optional
        Latitude of installation site [degrees].
        Geographic coordinate for solar calculations (default: 51.1676°).
    East_West_collector_azimuth_angle : float, optional
        Collector azimuth angle [degrees].
        Orientation angle from south (default: 0° = south-facing).
    Collector_tilt_angle : float, optional
        Collector tilt angle [degrees].
        Inclination angle from horizontal (default: 36°).
    Tm_rl : float, optional
        Mean return temperature [°C].
        Average return temperature from district heating network (default: 60°C).
    Qsa : float, optional
        Initial heat content in storage [MWh].
        Starting energy content for simulation (default: 0).
    Vorwärmung_K : float, optional
        Preheating temperature difference [K].
        Additional heating above return temperature (default: 8K).
    DT_WT_Solar_K : float, optional
        Temperature difference for solar heat exchanger [K].
        Heat transfer temperature difference (default: 5K).
    DT_WT_Netz_K : float, optional
        Temperature difference for network heat exchanger [K].
        Heat transfer temperature difference (default: 5K).
    opt_volume_min : float, optional
        Minimum optimization volume [m³].
        Lower bound for storage volume optimization (default: 0).
    opt_volume_max : float, optional
        Maximum optimization volume [m³].
        Upper bound for storage volume optimization (default: 200).
    opt_area_min : float, optional
        Minimum optimization area [m²].
        Lower bound for collector area optimization (default: 0).
    opt_area_max : float, optional
        Maximum optimization area [m²].
        Upper bound for collector area optimization (default: 2000).
    active : bool, optional
        Initial operational state of the solar thermal system.
        Starting condition for simulation (default: True).

    Attributes
    ----------
    bruttofläche_STA : float
        Gross collector area [m²]
    vs : float
        Storage volume [m³]
    Typ : str
        Collector technology type
    Aperaturfläche : float
        Aperture area of collectors [m²]
    Bezugsfläche : float
        Reference area for performance calculations [m²]
    Eta0b_neu : float
        Zero-loss collector efficiency [-]
    Koll_c1 : float
        Linear heat loss coefficient [W/(m²·K)]
    Koll_c2 : float
        Quadratic heat loss coefficient [W/(m²·K²)]
    IAM_W : dict
        Incidence angle modifier for beam radiation
    IAM_N : dict
        Incidence angle modifier for diffuse radiation
    QSmax : float
        Maximum storage capacity [kWh]
    strategy : SolarThermalStrategy
        Control strategy for solar thermal operation

    Notes
    -----
    Solar Thermal Technology:
        
        **Flat-Plate Collectors**:
        The flat-plate collector model provides:
        - High durability and proven technology
        - Good performance for moderate temperatures
        - Cost-effective solution for district heating
        - Robust design with low maintenance requirements
        - Suitable for large-scale installations
        
        **Vacuum Tube Collectors**:
        The vacuum tube collector model provides:
        - Higher efficiency at elevated temperatures
        - Better performance in cold and windy conditions
        - Enhanced optical properties with selective coatings
        - Reduced heat losses through vacuum insulation
        - Optimal for high-temperature district heating
        
        **Thermal Performance**:
        - Temperature-dependent efficiency calculations
        - Incidence angle modifier consideration
        - Thermal loss modeling with ambient conditions
        - Stagnation protection and overheating prevention

    Thermal Storage Integration:
        
        **Storage Modeling**:
        - Temperature stratification with hot and cold zones
        - Heat loss calculations with ambient dependency
        - Storage charging optimization with solar gains
        - Discharging control based on demand requirements
        
        **Heat Transfer**:
        - Heat exchanger modeling for solar circuit
        - Network integration with supply/return temperatures
        - Temperature differences for realistic performance
        - Thermal efficiency optimization
        
        **Seasonal Storage**:
        - Long-term energy storage for seasonal balancing
        - Volume optimization for economic feasibility
        - Heat loss minimization through insulation
        - Integration with district heating operation

    Economic Modeling:
        
        **Investment Costs**:
        - Collector field: Technology-specific costs per area
        - Storage system: Volume-dependent cost structure
        - Installation: Simplified installation factor
        - System integration: Heat exchanger and controls
        
        **Operational Costs**:
        - Maintenance: Low maintenance due to passive operation
        - Pumping energy: Minimal electricity consumption
        - System monitoring: Automated operation
        - No fuel costs due to renewable energy source
        
        **Economic Incentives**:
        - German BEW subsidy integration (40% investment support)
        - Operational cost incentives (10 €/MWh for 10 years)
        - Economic competitiveness through zero fuel costs
        - Long-term price stability for renewable heat

    Environmental Impact:
        
        **CO2 Emissions**:
        - Zero direct emissions from solar heat generation
        - Minimal indirect emissions from system manufacturing
        - Significant CO2 savings compared to fossil alternatives
        - Contribution to climate protection goals
        
        **Primary Energy**:
        - Zero primary energy factor for renewable solar energy
        - Reduction of fossil fuel dependency
        - Enhanced energy security through domestic resources
        - Sustainable heat generation for district heating

    Examples
    --------
    >>> # Create flat-plate collector system
    >>> solar_thermal = SolarThermal(
    ...     name="Solar_Thermal_District",
    ...     bruttofläche_STA=1000.0,        # 1000 m² collector area
    ...     vs=50.0,                        # 50 m³ storage volume
    ...     Typ="Flachkollektor",           # Flat-plate technology
    ...     kosten_fk_spez=450,             # €/m² collector cost
    ...     kosten_speicher_spez=800,       # €/m³ storage cost
    ...     Latitude=51.5,                  # Berlin latitude
    ...     Longitude=13.4,                 # Berlin longitude
    ...     Collector_tilt_angle=45         # 45° tilt angle
    ... )
    >>> 
    >>> print(f"Collector area: {solar_thermal.bruttofläche_STA} m²")
    >>> print(f"Storage volume: {solar_thermal.vs} m³")
    >>> print(f"Technology: {solar_thermal.Typ}")
    >>> print(f"Max storage capacity: {solar_thermal.QSmax:.1f} kWh")

    >>> # Create vacuum tube collector system for high-temperature application
    >>> vacuum_solar = SolarThermal(
    ...     name="Solar_Vacuum_System",
    ...     bruttofläche_STA=500.0,         # 500 m² collector area
    ...     vs=25.0,                        # 25 m³ storage volume
    ...     Typ="Vakuumröhrenkollektor",    # Vacuum tube technology
    ...     kosten_vrk_spez=620,            # €/m² collector cost
    ...     Tsmax=95,                       # 95°C max temperature
    ...     Collector_tilt_angle=60         # Steeper angle for winter optimization
    ... )
    >>> 
    >>> print(f"Vacuum collector efficiency: {vacuum_solar.Eta0b_neu:.3f}")
    >>> print(f"Heat loss coefficient: {vacuum_solar.Koll_c1:.3f} W/(m²·K)")

    >>> # Simulate annual solar thermal operation
    >>> import numpy as np
    >>> annual_hours = 8760
    >>> 
    >>> # Create synthetic weather data (simplified example)
    >>> air_temp = 10 + 15 * np.sin(2 * np.pi * np.arange(annual_hours) / 8760)
    >>> wind_speed = 3 + 2 * np.random.random(annual_hours)
    >>> global_radiation = np.maximum(0, 400 * np.sin(2 * np.pi * np.arange(annual_hours) / 8760) 
    ...                              + 200 * np.random.random(annual_hours))
    >>> direct_radiation = global_radiation * 0.7
    >>> 
    >>> TRY_data = (air_temp, wind_speed, direct_radiation, global_radiation)
    >>> 
    >>> # District heating temperature profiles
    >>> VLT_profile = 80 + 10 * np.sin(2 * np.pi * np.arange(annual_hours) / 8760)  # Supply temp
    >>> RLT_profile = VLT_profile - 25  # Return temp (25K difference)
    >>> 
    >>> # Heat demand profile (higher in winter)
    >>> heat_demand = 200 + 300 * np.cos(2 * np.pi * np.arange(annual_hours) / 8760)
    >>> heat_demand = np.maximum(50, heat_demand)  # Minimum 50 kW baseload
    >>> 
    >>> # Time steps for simulation
    >>> time_steps = np.arange(annual_hours, dtype='datetime64[h]')
    >>> 
    >>> # Economic parameters for solar thermal analysis
    >>> economic_params = {
    ...     'electricity_price': 0.25,      # €/kWh
    ...     'gas_price': 0.08,              # €/kWh
    ...     'wood_price': 0.05,             # €/kWh (not used)
    ...     'capital_interest_rate': 0.04,   # 4% interest
    ...     'inflation_rate': 0.02,         # 2% inflation
    ...     'time_period': 20,              # 20-year analysis
    ...     'subsidy_eligibility': "Ja",    # BEW subsidy eligible
    ...     'hourly_rate': 40.0             # €/hour labor cost
    ... }
    >>> 
    >>> # Calculate solar thermal system performance
    >>> results = solar_thermal.calculate(
    ...     economic_parameters=economic_params,
    ...     duration=1.0,  # 1-hour time steps
    ...     load_profile=heat_demand,
    ...     VLT_L=VLT_profile,
    ...     RLT_L=RLT_profile,
    ...     TRY_data=TRY_data,
    ...     time_steps=time_steps
    ... )
    >>> 
    >>> print(f"Annual solar heat generation: {results['Wärmemenge']:.1f} MWh")
    >>> print(f"Solar fraction: {results['Wärmemenge']/np.sum(heat_demand)*1000:.1%}")
    >>> print(f"Heat generation cost: {results['WGK']:.2f} €/MWh")
    >>> print(f"Operating hours: {results['Betriebsstunden']:.0f} h/year")
    >>> print(f"CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")

    >>> # Analyze seasonal storage performance
    >>> storage_content = results['Speicherladung_L']
    >>> storage_level = results['Speicherfüllstand_L']
    >>> 
    >>> max_storage = np.max(storage_content)
    >>> min_storage = np.min(storage_content)
    >>> avg_storage_level = np.mean(storage_level)
    >>> 
    >>> print(f"Maximum storage content: {max_storage:.1f} kWh")
    >>> print(f"Minimum storage content: {min_storage:.1f} kWh")
    >>> print(f"Average storage level: {avg_storage_level:.1%}")
    >>> 
    >>> # Storage utilization analysis
    >>> summer_months = np.arange(4*30*24, 9*30*24)  # May to September
    >>> winter_months = np.concatenate([np.arange(0, 3*30*24), np.arange(10*30*24, 12*30*24)])
    >>> 
    >>> summer_generation = np.sum(results['Wärmeleistung_L'][summer_months]) / 1000
    >>> winter_generation = np.sum(results['Wärmeleistung_L'][winter_months]) / 1000
    >>> 
    >>> print(f"Summer heat generation: {summer_generation:.1f} MWh")
    >>> print(f"Winter heat generation: {winter_generation:.1f} MWh")
    >>> print(f"Summer/Winter ratio: {summer_generation/winter_generation:.2f}")

    >>> # Economic comparison with conventional heating
    >>> gas_price = economic_params['gas_price']
    >>> gas_efficiency = 0.9
    >>> gas_heat_cost = gas_price / gas_efficiency * 1000  # €/MWh
    >>> 
    >>> solar_heat_cost = results['WGK']
    >>> cost_savings = gas_heat_cost - solar_heat_cost
    >>> 
    >>> print(f"Gas heating cost: {gas_heat_cost:.2f} €/MWh")
    >>> print(f"Solar heating cost: {solar_heat_cost:.2f} €/MWh")
    >>> print(f"Cost savings: {cost_savings:.2f} €/MWh")
    >>> 
    >>> if cost_savings > 0:
    ...     annual_savings = cost_savings * results['Wärmemenge']
    ...     print(f"Annual cost savings: {annual_savings:.0f} €")

    >>> # Optimization example for collector area and storage volume
    >>> optimization_solar = SolarThermal(
    ...     name="Solar_Optimized",
    ...     bruttofläche_STA=800,           # Initial area
    ...     vs=40,                          # Initial volume
    ...     Typ="Flachkollektor",
    ...     opt_area_min=500,               # Min 500 m²
    ...     opt_area_max=1500,              # Max 1500 m²
    ...     opt_volume_min=20,              # Min 20 m³
    ...     opt_volume_max=100              # Max 100 m³
    ... )
    >>> 
    >>> # Get optimization parameters
    >>> initial_values, variables, bounds = optimization_solar.add_optimization_parameters("1")
    >>> print(f"Optimization variables: {variables}")
    >>> print(f"Initial values: {initial_values}")
    >>> print(f"Optimization bounds: {bounds}")

    >>> # Environmental impact analysis
    >>> fossil_co2_factor = 0.201  # tCO2/MWh for natural gas
    >>> solar_co2_factor = results['spec_co2_total']
    >>> 
    >>> co2_avoided = (fossil_co2_factor - solar_co2_factor) * results['Wärmemenge']
    >>> print(f"CO2 emissions avoided: {co2_avoided:.1f} tCO2/year")
    >>> 
    >>> # Economic value of CO2 savings
    >>> carbon_price = 50  # €/tCO2
    >>> carbon_value = co2_avoided * carbon_price
    >>> print(f"Carbon savings value: {carbon_value:.0f} €/year")

    See Also
    --------
    BaseHeatGenerator : Base class for heat generation systems
    SolarThermalStrategy : Control strategy for solar thermal operation
    calculate_solar_radiation : Solar radiation calculation module
    """

    def __init__(self, name: str, bruttofläche_STA: float, vs: float, Typ: str, 
                 kosten_speicher_spez: float = 750, kosten_fk_spez: float = 430, 
                 kosten_vrk_spez: float = 590, Tsmax: float = 90, Longitude: float = -14.4222, 
                 STD_Longitude: float = -15, Latitude: float = 51.1676, 
                 East_West_collector_azimuth_angle: float = 0, Collector_tilt_angle: float = 36, 
                 Tm_rl: float = 60, Qsa: float = 0, Vorwärmung_K: float = 8, 
                 DT_WT_Solar_K: float = 5, DT_WT_Netz_K: float = 5, 
                 opt_volume_min: float = 0, opt_volume_max: float = 200, 
                 opt_area_min: float = 0, opt_area_max: float = 2000, active: bool = True):
        """
        Initialize the solar thermal collector system with technical and economic parameters.

        Parameters
        ----------
        name : str
            Unique identifier for the solar thermal system.
        bruttofläche_STA : float
            Gross collector area [m²].
        vs : float
            Storage volume [m³].
        Typ : str
            Collector technology type ("Flachkollektor" or "Vakuumröhrenkollektor").
        kosten_speicher_spez : float, optional
            Specific storage costs [€/m³] (default: 750).
        kosten_fk_spez : float, optional
            Specific flat-plate collector costs [€/m²] (default: 430).
        kosten_vrk_spez : float, optional
            Specific vacuum tube collector costs [€/m²] (default: 590).
        Tsmax : float, optional
            Maximum storage temperature [°C] (default: 90).
        Longitude : float, optional
            Geographic longitude [degrees] (default: -14.4222).
        STD_Longitude : float, optional
            Standard time zone longitude [degrees] (default: -15).
        Latitude : float, optional
            Geographic latitude [degrees] (default: 51.1676).
        East_West_collector_azimuth_angle : float, optional
            Collector azimuth angle [degrees] (default: 0).
        Collector_tilt_angle : float, optional
            Collector tilt angle [degrees] (default: 36).
        Tm_rl : float, optional
            Mean return temperature [°C] (default: 60).
        Qsa : float, optional
            Initial storage heat content [MWh] (default: 0).
        Vorwärmung_K : float, optional
            Preheating temperature difference [K] (default: 8).
        DT_WT_Solar_K : float, optional
            Solar heat exchanger temperature difference [K] (default: 5).
        DT_WT_Netz_K : float, optional
            Network heat exchanger temperature difference [K] (default: 5).
        opt_volume_min : float, optional
            Minimum optimization storage volume [m³] (default: 0).
        opt_volume_max : float, optional
            Maximum optimization storage volume [m³] (default: 200).
        opt_area_min : float, optional
            Minimum optimization collector area [m²] (default: 0).
        opt_area_max : float, optional
            Maximum optimization collector area [m²] (default: 2000).
        active : bool, optional
            Initial operational state (default: True).
        """
        super().__init__(name)
        self.bruttofläche_STA = bruttofläche_STA
        self.vs = vs
        self.Typ = Typ
        self.kosten_speicher_spez = kosten_speicher_spez
        self.kosten_fk_spez = kosten_fk_spez
        self.kosten_vrk_spez = kosten_vrk_spez
        self.Tsmax = Tsmax
        self.Longitude = Longitude
        self.STD_Longitude = STD_Longitude
        self.Latitude = Latitude
        self.East_West_collector_azimuth_angle = East_West_collector_azimuth_angle
        self.Collector_tilt_angle = Collector_tilt_angle
        self.Tm_rl = Tm_rl
        self.Qsa = Qsa
        self.Vorwärmung_K = Vorwärmung_K
        self.DT_WT_Solar_K = DT_WT_Solar_K
        self.DT_WT_Netz_K = DT_WT_Netz_K
        self.opt_volume_min = opt_volume_min
        self.opt_volume_max = opt_volume_max
        self.opt_area_min = opt_area_min
        self.opt_area_max = opt_area_max
        self.active = active

        # Technology-specific cost structure
        self.kosten_pro_typ = {
            # Viessmann Flachkollektor Vitosol 200-FM, 2,56 m²: 697,9 € (brutto); 586,5 € (netto) -> 229 €/m²
            # + 200 €/m² Installation/Zubehör
            "Flachkollektor": self.kosten_fk_spez,
            # Ritter Vakuumröhrenkollektor CPC XL1921 (4,99m²): 2299 € (brutto); 1932 € (Netto) -> 387 €/m²
            # + 200 €/m² Installation/Zubehör
            "Vakuumröhrenkollektor": self.kosten_vrk_spez
        }

        self.Kosten_STA_spez = self.kosten_pro_typ[self.Typ]  # €/m²
        self.Nutzungsdauer = 20  # Jahre
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 0.5, 1, 0
        self.Anteil_Förderung_BEW = 0.4
        self.Betriebskostenförderung_BEW = 10  # €/MWh 10 Jahre
        self.co2_factor_solar = 0.0  # tCO2/MWh heat is 0
        self.primärenergiefaktor = 0.0

        self.strategy = SolarThermalStrategy(charge_on=0, charge_off=0)

        self.init_calculation_constants()
        self.init_operation(8760)

    def init_calculation_constants(self) -> None:
        """
        Initialize technology-specific calculation constants for solar thermal modeling.

        This method sets up the technical parameters for solar collector performance
        calculations based on the selected collector technology. The parameters
        include efficiency characteristics, heat loss coefficients, and incidence
        angle modifiers for accurate thermal performance modeling.

        Notes
        -----
        Flat-Plate Collector Constants:
            
            **Performance Parameters** (Vitosol 200-F XL13):
            - Zero-loss efficiency: 0.763 (gross area reference)
            - Linear heat loss coefficient: 1.969 W/(m²·K)
            - Quadratic heat loss coefficient: 0.015 W/(m²·K²)
            - Diffuse radiation modifier: 0.931
            
            **Geometric Parameters**:
            - Gross area reference for efficiency calculations
            - Aperture area ratio: 12.35/13.17 = 0.938
            - Heat capacity factor: 9.053 kJ/(m²·K)
            
            **Incidence Angle Modifiers**:
            - Symmetric behavior for beam and diffuse radiation
            - Optimized for standard flat-plate geometry
            - Good performance up to 50° incidence angle

        Vacuum Tube Collector Constants:
            
            **Performance Parameters** (Vacuum tube technology):
            - Hemispherical efficiency: 0.688 (aperture reference)
            - Effective zero-loss efficiency: 0.693 (gross area)
            - Linear heat loss coefficient: 0.583 W/(m²·K)
            - Quadratic heat loss coefficient: 0.003 W/(m²·K²)
            
            **Enhanced Performance**:
            - Lower heat losses due to vacuum insulation
            - Better high-temperature performance
            - Aperture area reference for calculations
            - Heat capacity factor: 8.78 kJ/(m²·K)
            
            **Incidence Angle Modifiers**:
            - Enhanced performance at moderate angles
            - Asymmetric behavior due to tube geometry
            - Optimal performance range: 0° to 60°

        The calculation constants are based on certified test results and
        established solar thermal modeling standards for accurate performance
        prediction in district heating applications.
        """
        # Environmental parameters
        self.Albedo = 0.2  # Ground reflection coefficient
        self.wcorr = 0.5   # Wind speed correction factor

        if self.Typ == "Flachkollektor":
            # Flat-plate collector parameters (Vitosol 200-F XL13)
            # Gross area is reference area
            self.Eta0b_neu = 0.763
            self.Kthetadiff = 0.931
            self.Koll_c1 = 1.969
            self.Koll_c2 = 0.015
            self.Koll_c3 = 0
            self.KollCeff_A = 9.053
            self.KollAG = 13.17
            self.KollAAp = 12.35

            self.Aperaturfläche = self.bruttofläche_STA * (self.KollAAp / self.KollAG)
            self.Bezugsfläche = self.bruttofläche_STA

            self.IAM_W = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}
            self.IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}

        elif self.Typ == "Vakuumröhrenkollektor":
            # Vacuum tube collector parameters
            # Aperture area is reference area
            self.Eta0hem = 0.688
            self.a1 = 0.583
            self.a2 = 0.003
            self.KollCeff_A = 8.78
            self.KollAG = 4.94
            self.KollAAp = 4.5

            self.Koll_c1 = self.a1
            self.Koll_c2 = self.a2
            self.Koll_c3 = 0
            self.Eta0b_neu = 0.693
            self.Kthetadiff = 0.951

            self.Aperaturfläche = self.bruttofläche_STA * (self.KollAAp / self.KollAG)
            self.Bezugsfläche = self.Aperaturfläche

            self.IAM_W = {0: 1, 10: 1.02, 20: 1.03, 30: 1.03, 40: 1.03, 50: 0.96, 60: 1.07, 70: 1.19, 80: 0.595, 90: 0.0}
            self.IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.96, 40: 0.93, 50: 0.9, 60: 0.87, 70: 0.86, 80: 0.43, 90: 0.0}

        # Storage system parameters
        self.QSmax = 1.16 * self.vs * (self.Tsmax - self.Tm_rl)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational arrays for annual solar thermal simulation.

        Parameters
        ----------
        hours : int
            Number of simulation hours (typically 8760 for annual analysis).
        """
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours, dtype=float)
        self.Speicherinhalt = np.zeros(hours, dtype=float)
        self.Speicherfüllstand = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if calculation is complete

        # Initialize detailed calculation arrays
        self.Tm_a_L = np.zeros(hours, dtype=float)
        self.Pkoll_a_L = np.zeros(hours, dtype=float)
        self.Pkoll_b_L = np.zeros(hours, dtype=float)
        self.T_koll_a_L = np.zeros(hours, dtype=float)
        self.T_koll_b_L = np.zeros(hours, dtype=float)
        self.Tgkoll_a_L = np.zeros(hours, dtype=float)
        self.Tgkoll_L = np.zeros(hours, dtype=float)
        self.Tm_koll_L = np.zeros(hours, dtype=float)
        self.Tm_L = np.zeros(hours, dtype=float)
        self.Kollektorfeldertrag_L = np.zeros(hours, dtype=float)
        self.Zieltemperatur_Solaranlage_L = np.zeros(hours, dtype=float)
        self.TRL_Solar_L = np.zeros(hours, dtype=float)
        self.TS_unten_L = np.zeros(hours, dtype=float)
        self.Verlustwärmestrom_Speicher_L = np.zeros(hours, dtype=float)
        self.Stagnation_L = np.zeros(hours, dtype=float)

    def calculate_heat_generation_costs(self, economic_parameters: Dict) -> float:
        """
        Calculate comprehensive heat generation costs for the solar thermal system.

        This method performs detailed economic analysis of the solar thermal system
        including collector and storage investment costs, operational expenses, and
        subsidy integration for lifecycle cost assessment.

        Parameters
        ----------
        economic_parameters : dict
            Dictionary containing economic parameters:
            
            - electricity_price : float
                Electricity price [€/kWh] (minimal for pumping)
            - gas_price : float
                Gas price [€/kWh] (not used for solar thermal)
            - wood_price : float
                Wood price [€/kWh] (not used for solar thermal)
            - capital_interest_rate : float
                Interest rate for capital costs [-]
            - inflation_rate : float
                Annual inflation rate [-]
            - time_period : int
                Analysis time period [years]
            - subsidy_eligibility : str
                BEW subsidy eligibility ("Ja" or "Nein")
            - hourly_rate : float
                Labor cost rate [€/hour]

        Returns
        -------
        float
            Heat generation cost [€/MWh] considering subsidies if applicable.

        Notes
        -----
        Economic Analysis Components:
            
            **Investment Costs**:
            - Collector field: Area-dependent costs based on technology
            - Storage system: Volume-dependent cost structure
            - Installation: Simplified installation factor (50%)
            - Low complexity due to proven technology
            
            **Operational Costs**:
            - Maintenance: Low due to passive solar operation
            - Pumping energy: Minimal electricity consumption
            - No fuel costs due to renewable energy source
            - Long-term operation with minimal intervention
            
            **Subsidy Integration**:
            - German BEW program: 40% investment cost reduction
            - Operational cost incentive: 10 €/MWh for 10 years
            - Conditional on renewable energy law eligibility
            - Significant impact on economic competitiveness
            
            **Cost Structure**:
            - Zero fuel costs provide long-term price stability
            - High investment costs offset by subsidies and longevity
            - Minimal operational costs due to automated operation
            - Economic competitiveness with fossil alternatives

        The calculation provides comprehensive lifecycle cost analysis
        for solar thermal economic evaluation in district heating systems.
        """
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

        # Calculate investment costs
        self.Investitionskosten_Speicher = self.vs * self.kosten_speicher_spez
        self.Investitionskosten_STA = self.bruttofläche_STA * self.Kosten_STA_spez
        self.Investitionskosten = self.Investitionskosten_Speicher + self.Investitionskosten_STA

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
            annual_energy_demand=0,
            energy_cost_per_unit=0,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        self.WGK = self.A_N / self.Wärmemenge_MWh

        # Calculate subsidized costs with BEW program
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
            annual_energy_demand=0,
            energy_cost_per_unit=0,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        self.WGK_BEW = self.Annuität_BEW / self.Wärmemenge_MWh
        self.WGK_BEW_BKF = self.WGK_BEW - self.Betriebskostenförderung_BEW

        if self.BEW == "Nein":
            return self.WGK
        elif self.BEW == "Ja":
            return self.WGK_BEW_BKF
        
    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact metrics for the solar thermal system.

        This method assesses the environmental performance of the renewable
        solar thermal system including zero direct CO2 emissions and
        minimal primary energy consumption for sustainability analysis.

        Notes
        -----
        Environmental Assessment:
            
            **CO2 Emissions**:
            - Zero direct emissions from solar heat generation
            - Minimal indirect emissions from system manufacturing
            - Significant CO2 savings compared to fossil alternatives
            - Contribution to climate protection and decarbonization
            
            **Primary Energy**:
            - Zero primary energy factor for renewable solar energy
            - No fossil fuel dependency for operation
            - Enhanced energy security through domestic resources
            - Sustainable heat generation for district heating
            
            **Environmental Benefits**:
            - Renewable energy source with unlimited availability
            - No air pollutants or local environmental impact
            - Long-term technology with 20+ year lifespan
            - Support for renewable energy transition goals

        The environmental analysis supports sustainability reporting
        and renewable energy transition planning for district heating.
        """
        # Calculate CO2 emissions (zero for renewable solar energy)
        self.co2_emissions = self.Wärmemenge_MWh * self.co2_factor_solar  # tCO2
        
        # Calculate specific CO2 emissions per unit heat generated
        self.spec_co2_total = (self.co2_emissions / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat
        
        # Calculate primary energy consumption (zero for solar energy)
        self.primärenergie_Solarthermie = self.Wärmemenge_MWh * self.primärenergiefaktor

    def calculate_solar_thermal_with_storage(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                                           RLT_L: np.ndarray, TRY_data: Tuple, 
                                           time_steps: np.ndarray, duration: float) -> None:
        """
        Comprehensive solar thermal system calculation with integrated storage modeling.

        This method performs detailed hourly simulation of the solar thermal collector
        system including solar radiation calculations, thermal efficiency modeling,
        storage operation, and heat generation for district heating applications.

        Parameters
        ----------
        Last_L : numpy.ndarray
            Hourly heat demand profile [kW].
        VLT_L : numpy.ndarray
            District heating supply temperature profile [°C].
        RLT_L : numpy.ndarray
            District heating return temperature profile [°C].
        TRY_data : tuple
            Test Reference Year weather data containing:
            (air_temperature, wind_speed, direct_radiation, global_radiation).
        time_steps : numpy.ndarray
            Time step array for temporal calculations.
        duration : float
            Time step duration [hours] for energy calculations.

        Notes
        -----
        Calculation Methodology:
            
            **Solar Radiation Processing**:
            - Global and direct radiation separation
            - Solar position calculations for site coordinates
            - Incidence angle calculations for collector orientation
            - Beam and diffuse radiation on tilted surface
            - Incidence angle modifier application
            
            **Thermal Performance Modeling**:
            - Temperature-dependent collector efficiency
            - Heat loss calculations with ambient conditions
            - Collector field thermal dynamics
            - Stagnation protection and overheating prevention
            
            **Storage System Integration**:
            - Temperature stratification with hot/cold zones
            - Heat loss calculations with ambient dependency
            - Storage charging from collector field
            - Storage discharging for heat demand
            - Temperature control and optimization
            
            **Heat Generation**:
            - Collector field output calculation
            - Storage contribution to heat supply
            - Load balancing and demand satisfaction
            - System efficiency and performance metrics

        The comprehensive simulation provides detailed system performance
        analysis for economic evaluation and optimization of solar thermal
        systems in district heating applications.
        """
        self.Lufttemperatur_L, self.Windgeschwindigkeit_L, self.Direktstrahlung_L, self.Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]
        
        # Calculate solar radiation on collector surface
        self.GT_H_Gk, self.K_beam_L, self.GbT_L, self.GdT_H_Dk_L = calculate_solar_radiation(
            time_steps, self.Globalstrahlung_L, self.Direktstrahlung_L, self.Longitude,
            self.STD_Longitude, self.Latitude, self.Albedo, 
            self.East_West_collector_azimuth_angle,
            self.Collector_tilt_angle, self.IAM_W, self.IAM_N
        )

        # Hourly simulation loop
        n_steps = len(time_steps)

        for i in range(n_steps):
            # Calculate effective solar radiation terms
            Eta0b_neu_K_beam_GbT = self.Eta0b_neu * self.K_beam_L[i] * self.GbT_L[i]
            Eta0b_neu_Kthetadiff_GdT_H_Dk = self.Eta0b_neu * self.Kthetadiff * self.GdT_H_Dk_L[i]

            if i == 0:
                # Initialize first time step
                self.TS_unten_L[i] = RLT_L[i]
                self.TRL_Solar_L[i] = RLT_L[i]
                self.Zieltemperatur_Solaranlage_L[i] = self.TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.Tm_a_L[i] = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2
                self.Pkoll_a_L[i] = 0
                self.Tgkoll_a_L[i] = 9.3
                self.T_koll_a_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Pkoll_b_L[i] = 0
                self.T_koll_b_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - 0) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[i] = 9.3
                self.Tm_koll_L[i] = (self.T_koll_a_L[i] + self.T_koll_b_L[i]) / 2

                self.Kollektorfeldertrag_L[i] = 0
                self.Wärmeleistung_kW[i] = min(self.Kollektorfeldertrag_L[i], Last_L[i])
                self.Verlustwärmestrom_Speicher_L[i] = 0
                self.Speicherinhalt[i] = self.Qsa * 1000
                self.Speicherfüllstand[i] = self.Speicherinhalt[i] / self.QSmax
                self.Stagnation_L[i] = 0

            else:
                # Calculate storage temperature stratification
                if self.Speicherfüllstand[i - 1] >= 0.8:
                    self.TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherfüllstand[i - 1]) + (1 / 3 * (VLT_L[i] - RLT_L[i])) - (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherfüllstand[i - 1])
                else:
                    self.TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (1 / 3 * (VLT_L[i] - RLT_L[i]) / 0.8) * self.Speicherfüllstand[i - 1]

                # Calculate solar circuit temperatures
                self.Zieltemperatur_Solaranlage_L[i] = self.TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.TRL_Solar_L[i] = self.TS_unten_L[i] + self.DT_WT_Solar_K
                self.Tm_a_L[i] = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2

                # Calculate collector performance with thermal losses
                c1a = self.Koll_c1 * (self.Tm_a_L[i] - self.Lufttemperatur_L[i])
                c2a = self.Koll_c2 * (self.Tm_a_L[i] - self.Lufttemperatur_L[i]) ** 2
                c3a = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.Tm_a_L[i] - self.Lufttemperatur_L[i])

                self.Pkoll_a_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1a - c2a - c3a) * self.Bezugsfläche / 1000)
                self.T_koll_a_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)

                # Calculate alternative collector state
                c1b = self.Koll_c1 * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i])
                c2b = self.Koll_c2 * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i]) ** 2
                c3b = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i])
                
                self.Pkoll_b_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1b - c2b - c3b) * self.Bezugsfläche / 1000)
                self.T_koll_b_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                
                # Temperature control and collector field output
                self.Tgkoll_a_L[i] = min(self.Zieltemperatur_Solaranlage_L[i], self.T_koll_a_L[i])
                self.Tm_koll_L[i] = (self.T_koll_a_L[i] + self.T_koll_b_L[i]) / 2
                Tm_sys = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2
                
                if self.Tm_koll_L[i] < Tm_sys and self.Tm_koll_L[i - 1] < Tm_sys:
                    self.Tm_L[i] = self.Tm_koll_L[i]
                else:
                    self.Tm_L[i] = Tm_sys

                # Final collector output calculation
                c1 = self.Koll_c1 * (self.Tm_L[i] - self.Lufttemperatur_L[i])
                c2 = self.Koll_c2 * (self.Tm_L[i] - self.Lufttemperatur_L[i]) ** 2
                c3 = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.Tm_L[i] - self.Lufttemperatur_L[i])
                Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * self.Bezugsfläche / 1000)

                # Temperature rise calculation
                T_koll = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[i] = min(self.Zieltemperatur_Solaranlage_L[i], T_koll)

                # Collector field yield calculation
                if T_koll > self.Tgkoll_L[i - 1]:
                    Pkoll_temp_corr = (T_koll-self.Tgkoll_L[i])/(T_koll-self.Tgkoll_L[i - 1]) * Pkoll if self.Tgkoll_L[i] >= self.Zieltemperatur_Solaranlage_L[i] else 0
                    self.Kollektorfeldertrag_L[i] = max(0, min(Pkoll, Pkoll_temp_corr)) if self.Stagnation_L[i - 1] <= 0 else 0
                else:
                    self.Kollektorfeldertrag_L[i] = 0

                # Heat output and storage balance
                self.Wärmeleistung_kW[i] = min(self.Kollektorfeldertrag_L[i] + self.Speicherinhalt[i - 1], Last_L[i]) if self.Kollektorfeldertrag_L[i] + self.Speicherinhalt[i - 1] > 0 else 0

                # Storage energy balance
                Stagnationsverluste = max(0, self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + self.Kollektorfeldertrag_L[i] - self.Wärmeleistung_kW[i] - self.QSmax)
                PSin = self.Kollektorfeldertrag_L[i] - Stagnationsverluste

                if self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + PSin - self.Wärmeleistung_kW[i] > self.QSmax:
                    self.Speicherinhalt[i] = self.QSmax
                else:
                    self.Speicherinhalt[i] = self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + PSin - self.Wärmeleistung_kW[i]

                # Storage temperature and heat loss calculation
                self.Speicherfüllstand[i] = self.Speicherinhalt[i] / self.QSmax

                TS_oben = self.Zieltemperatur_Solaranlage_L[i] - self.DT_WT_Solar_K
                if self.Speicherinhalt[i] <= 0:
                    berechnete_temperatur = TS_oben
                else:
                    temperaturverhältnis = (TS_oben - self.Tm_rl) / (self.Tsmax - self.Tm_rl)
                    if self.Speicherfüllstand[i] < temperaturverhältnis:
                        berechnete_temperatur = VLT_L[i] + self.DT_WT_Netz_K
                    else:
                        berechnete_temperatur = self.Tsmax

                gewichtete_untere_temperatur = (1 - self.Speicherfüllstand[i]) * self.TS_unten_L[i]
                Tms = self.Speicherfüllstand[i] * berechnete_temperatur + gewichtete_untere_temperatur

                self.Verlustwärmestrom_Speicher_L[i] = 0.75 * (self.vs * 1000) ** 0.5 * 0.16 * (Tms - self.Lufttemperatur_L[i]) / 1000

                # Stagnation detection
                self.Stagnation_L[i] = 1 if np.datetime_as_string(time_steps[i], unit='D') == np.datetime_as_string(time_steps[i - 1], unit='D') and self.Kollektorfeldertrag_L[i] > Last_L[i] and self.Speicherinhalt[i] >= self.QSmax else 0

        # Calculate total annual heat generation
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW) * duration / 1000  # kWh -> MWh

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate instantaneous heat output from the solar thermal system for real-time simulation.

        This method performs detailed solar thermal collector modeling including
        radiation calculations, collector efficiency analysis, storage integration,
        and stagnation control for accurate heat generation simulation at each
        time step in district heating applications.

        Parameters
        ----------
        t : int
            Current simulation time step index.
            Used for accessing time-dependent arrays and calculations.
        **kwargs
            Additional simulation parameters:
            
            remaining_load : float
                Remaining heat demand to be covered by solar thermal [kW].
            upper_storage_temperature : float
                Current upper storage layer temperature [°C].
            lower_storage_temperature : float
                Current lower storage layer temperature [°C].
            current_storage_state : float
                Current storage filling level [-] (0.0 to 1.0).
            available_energy : float
                Currently available energy in storage [kWh].
            max_energy : float
                Maximum storage energy capacity [kWh].
            Q_loss : float
                Current storage heat losses [kW].
            TRY_data : tuple
                Test Reference Year weather data:
                (air_temp, wind_speed, direct_radiation, global_radiation).
            time_steps : numpy.ndarray
                Array of simulation time stamps.
            duration : float
                Time step duration [hours].

        Returns
        -------
        tuple of (float, float)
            Heat generation outputs:
            
            heat_output : float
                Instantaneous thermal power output from collectors [kW].
            electricity_output : float
                Electrical power output [kW] (always 0 for solar thermal).

        Notes
        -----
        Solar Thermal Modeling:
            
            **Collector Performance**:
            The method implements detailed collector modeling:
            
            - **Optical Efficiency**: Accounts for solar radiation angle effects
            - **Thermal Losses**: Temperature-dependent heat loss calculations
            - **Wind Effects**: Wind speed correction for convective losses
            - **Dual Collector Approach**: Separate A/B collector modeling
            
            **Mathematical Model**:
            Collector power output calculated as:
            
            .. math::
                P_{coll} = \\eta_0 \\cdot G_{total} \\cdot A_{ref} - U_L \\cdot (T_m - T_{air}) \\cdot A_{ref}
            
            Where:
            - η₀: Optical efficiency [-]
            - G_total: Total solar irradiation [W/m²]
            - A_ref: Reference collector area [m²]
            - U_L: Heat loss coefficient [W/(m²·K)]
            - T_m: Mean collector temperature [°C]
            - T_air: Ambient air temperature [°C]
            
            **Temperature Calculation**:
            Collector temperature evolution:
            
            .. math::
                T_{coll}(t) = T_{air} - (T_{air} - T_{glycol,prev}) \\cdot e^{-U_L/(C_{eff} \\cdot A) \\cdot \\Delta t} + \\frac{P_{coll} \\cdot \\Delta t}{C_{eff} \\cdot A}

        Storage Integration:
            
            **Temperature Stratification**:
            The method models stratified storage behavior:
            
            - **Lower Zone Temperature**: Based on storage state and return temperature
            - **Target Temperature**: Solar circuit design temperature
            - **Heat Exchanger Losses**: Temperature differences in heat exchangers
            
            **Storage State Logic**:
            For storage filling level ≥ 80%:
            
            .. math::
                T_{lower} = T_{return} + \\Delta T_{HX} + f(fill_{level}, T_{upper}, T_{return})
            
            For storage filling level < 80%:
            
            .. math::
                T_{lower} = T_{return} + \\Delta T_{HX} + \\frac{1}{3} \\cdot \\frac{\\Delta T_{storage}}{0.8} \\cdot fill_{level}

        Operational Control:
            
            **Stagnation Prevention**:
            - Monitors collector temperature vs. target temperature
            - Prevents operation during overheating conditions
            - Accounts for storage capacity limitations
            
            **Temperature Correction**:
            - Corrects collector output for temperature limitations
            - Implements minimum temperature requirements
            - Prevents reverse heat flow conditions
            
            **System Protection**:
            - Automatic shutdown during stagnation conditions
            - Temperature-limited operation for system safety
            - Daily stagnation reset functionality

        Algorithm Workflow:
            
            **1. Initialization (t=0)**:
            - Extract weather data and calculate solar radiation
            - Initialize collector and storage temperatures
            - Set initial system state variables
            
            **2. Solar Radiation Processing**:
            - Calculate beam and diffuse radiation components
            - Apply incidence angle modifiers
            - Determine collector-specific irradiation
            
            **3. Thermal Calculations**:
            - Calculate collector A and B performance separately
            - Determine average collector temperature
            - Apply thermal loss corrections
            
            **4. Heat Output Determination**:
            - Calculate instantaneous collector power
            - Apply temperature and stagnation limitations
            - Determine final heat output to system
            
            **5. State Updates**:
            - Update cumulative energy generation
            - Record operational parameters
            - Prepare for next time step

        Performance Characteristics:
            
            **Flat Plate Collectors**:
            - Optical efficiency: ~76%
            - Linear heat loss coefficient: ~2.0 W/(m²·K)
            - Quadratic heat loss coefficient: ~0.015 W/(m²·K²)
            - Good performance at moderate temperatures
            
            **Vacuum Tube Collectors**:
            - Optical efficiency: ~69%
            - Linear heat loss coefficient: ~0.6 W/(m²·K)
            - Quadratic heat loss coefficient: ~0.003 W/(m²·K²)
            - Superior performance at high temperatures

        Examples
        --------
        >>> # Real-time solar thermal generation
        >>> solar = SolarThermal(
        ...     name="Solar_District",
        ...     bruttofläche_STA=500.0,  # 500 m² collector area
        ...     vs=50.0,                 # 50 m³ storage volume
        ...     Typ="Flachkollektor"     # Flat plate collectors
        ... )
        >>> 
        >>> # Simulation parameters for summer day
        >>> t = 2000  # Hour 2000 (summer afternoon)
        >>> simulation_params = {
        ...     'remaining_load': 150.0,           # 150 kW remaining demand
        ...     'upper_storage_temperature': 85.0,  # 85°C upper storage
        ...     'lower_storage_temperature': 45.0,  # 45°C lower storage
        ...     'current_storage_state': 0.7,      # 70% storage filling
        ...     'available_energy': 1000.0,        # 1000 kWh available
        ...     'max_energy': 1450.0,              # 1450 kWh max capacity
        ...     'Q_loss': 5.0,                     # 5 kW storage losses
        ...     'TRY_data': (25.0, 3.0, 400.0, 800.0),  # Weather data
        ...     'time_steps': time_array,
        ...     'duration': 1.0                    # 1-hour time steps
        ... }
        >>> 
        >>> # Generate heat output
        >>> heat_out, elec_out = solar.generate(t, **simulation_params)
        >>> print(f"Solar thermal output: {heat_out:.1f} kW")
        >>> print(f"Electrical output: {elec_out:.1f} kW")  # Always 0

        >>> # Compare collector types under identical conditions
        >>> collectors = {
        ...     'flat_plate': SolarThermal("FP", 100, 10, "Flachkollektor"),
        ...     'vacuum_tube': SolarThermal("VT", 100, 10, "Vakuumröhrenkollektor")
        ... }
        >>> 
        >>> # Test under high temperature conditions
        >>> high_temp_params = simulation_params.copy()
        >>> high_temp_params.update({
        ...     'upper_storage_temperature': 95.0,
        ...     'lower_storage_temperature': 70.0,
        ...     'TRY_data': (30.0, 2.0, 600.0, 900.0)  # High irradiation
        ... })
        >>> 
        >>> for name, collector in collectors.items():
        ...     heat_output, _ = collector.generate(t, **high_temp_params)
        ...     print(f"{name}: {heat_output:.1f} kW at high temperature")

        >>> # Stagnation condition simulation
        >>> stagnation_params = simulation_params.copy()
        >>> stagnation_params.update({
        ...     'remaining_load': 0.0,              # No heat demand
        ...     'current_storage_state': 1.0,       # Full storage
        ...     'available_energy': 1450.0,         # Max energy
        ...     'TRY_data': (35.0, 1.0, 800.0, 1000.0)  # High solar irradiation
        ... })
        >>> 
        >>> # Check stagnation prevention
        >>> heat_out, _ = solar.generate(t, **stagnation_params)
        >>> print(f"Output during stagnation risk: {heat_out:.1f} kW")
        >>> if solar.Stagnation_L[t] == 1:
        ...     print("Stagnation protection activated")

        See Also
        --------
        calculate_solar_thermal_with_storage : Complete system calculation method
        calculate_solar_radiation : Solar radiation calculation module
        SolarThermalStrategy : Control strategy for solar thermal operation
        """
        # Extract simulation parameters from kwargs
        remaining_load = kwargs.get('remaining_load', 0.0)
        upper_storage_temperature = kwargs.get('upper_storage_temperature', 70.0)
        lower_storage_temperature = kwargs.get('lower_storage_temperature', 40.0)
        current_storage_state = kwargs.get('current_storage_state', 0.0)
        available_energy = kwargs.get('available_energy', 0.0)
        max_energy = kwargs.get('max_energy', 1000.0)
        Q_loss = kwargs.get('Q_loss', 0.0)
        TRY_data = kwargs.get('TRY_data', (20.0, 2.0, 200.0, 400.0))
        time_steps = kwargs.get('time_steps', np.array([]))
        duration = kwargs.get('duration', 1.0)

        # Initialize weather data and solar radiation calculations at t=0
        if t == 0:
            # Extract weather data components
            self.Lufttemperatur_L, self.Windgeschwindigkeit_L, self.Direktstrahlung_L, self.Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]
        
            # Calculate solar radiation on collector surface
            self.GT_H_Gk, self.K_beam_L, self.GbT_L, self.GdT_H_Dk_L = calculate_solar_radiation(
                time_steps, self.Globalstrahlung_L, self.Direktstrahlung_L, self.Longitude,
                self.STD_Longitude, self.Latitude, self.Albedo, 
                self.East_West_collector_azimuth_angle,
                self.Collector_tilt_angle, self.IAM_W, self.IAM_N
            )
        
        # Perform heat generation calculation only if system is active
        if self.active:
            # Calculate optical efficiency components for current time step
            Eta0b_neu_K_beam_GbT = self.Eta0b_neu * self.K_beam_L[t] * self.GbT_L[t]
            Eta0b_neu_Kthetadiff_GdT_H_Dk = self.Eta0b_neu * self.Kthetadiff * self.GdT_H_Dk_L[t]

            # Update storage parameters from external storage system
            self.QSmax = max_energy  # Maximum storage energy capacity [kWh]
            self.Speicherinhalt[t] = available_energy  # Current storage energy content [kWh]
            self.Speicherfüllstand[t] = current_storage_state  # Storage filling level [-]

            # Update storage heat losses and initialize stagnation state
            self.Verlustwärmestrom_Speicher_L[t] = Q_loss  # Storage heat losses [kW]
            self.Stagnation_L[t] = 0  # Initialize stagnation indicator

            # Initial conditions for first time step
            if t == 0:
                # Initialize storage and solar circuit temperatures
                self.TS_unten_L[t] = lower_storage_temperature
                self.TRL_Solar_L[t] = lower_storage_temperature
                
                # Calculate target temperature for solar circuit
                self.Zieltemperatur_Solaranlage_L[t] = (self.TS_unten_L[t] + self.Vorwärmung_K + 
                                                    self.DT_WT_Solar_K + self.DT_WT_Netz_K)
                
                # Calculate mean collector A temperature
                self.Tm_a_L[t] = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2
                
                # Initialize collector power outputs and temperatures
                self.Pkoll_a_L[t] = 0
                self.Tgkoll_a_L[t] = 9.3  # Initial glycol temperature [°C]
                
                # Calculate initial collector A temperature using thermal time constant
                self.T_koll_a_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t]) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_a_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Initialize collector B with zero initial conditions
                self.Pkoll_b_L[t] = 0
                self.T_koll_b_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - 0) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_b_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Initialize system glycol temperature
                self.Tgkoll_L[t] = 9.3

                # No collector field output at initialization
                self.Kollektorfeldertrag_L[t] = 0
                self.Wärmeleistung_kW[t] = min(self.Kollektorfeldertrag_L[t], remaining_load)

            else:
                # Calculate lower storage tank temperature based on stratification model
                if self.Speicherfüllstand[t - 1] >= 0.8:
                    # High filling level: complex stratification calculation
                    self.TS_unten_L[t] = (lower_storage_temperature + self.DT_WT_Netz_K + 
                                        (2/3 * (upper_storage_temperature - lower_storage_temperature) / 0.2 * 
                                        self.Speicherfüllstand[t - 1]) + 
                                        (1/3 * (upper_storage_temperature - lower_storage_temperature)) - 
                                        (2/3 * (upper_storage_temperature - lower_storage_temperature) / 0.2 * 
                                        self.Speicherfüllstand[t - 1]))
                else:
                    # Low filling level: simplified linear stratification
                    self.TS_unten_L[t] = (lower_storage_temperature + self.DT_WT_Netz_K + 
                                        (1/3 * (upper_storage_temperature - lower_storage_temperature) / 0.8) * 
                                        self.Speicherfüllstand[t - 1])

                # Calculate solar circuit target and return temperatures
                self.Zieltemperatur_Solaranlage_L[t] = (self.TS_unten_L[t] + self.Vorwärmung_K + 
                                                    self.DT_WT_Solar_K + self.DT_WT_Netz_K)
                self.TRL_Solar_L[t] = self.TS_unten_L[t] + self.DT_WT_Solar_K

                # Calculate mean collector A temperature for performance calculation
                self.Tm_a_L[t] = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2

                # Calculate collector A thermal loss coefficients
                c1a = self.Koll_c1 * (self.Tm_a_L[t] - self.Lufttemperatur_L[t])
                c2a = self.Koll_c2 * (self.Tm_a_L[t] - self.Lufttemperatur_L[t]) ** 2
                c3a = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.Tm_a_L[t] - self.Lufttemperatur_L[t])

                # Calculate collector A power output with thermal losses
                self.Pkoll_a_L[t] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - 
                                        c1a - c2a - c3a) * self.Bezugsfläche / 1000)
                
                # Calculate collector A temperature evolution
                self.T_koll_a_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t - 1]) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_a_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))

                # Calculate collector B thermal loss coefficients using previous temperature
                c1b = self.Koll_c1 * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t])
                c2b = self.Koll_c2 * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t]) ** 2
                c3b = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t])
                
                # Calculate collector B power output
                self.Pkoll_b_L[t] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - 
                                        c1b - c2b - c3b) * self.Bezugsfläche / 1000)
                
                # Calculate collector B temperature evolution
                self.T_koll_b_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t - 1]) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_b_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Calculate glycol temperature with target temperature limitation
                self.Tgkoll_a_L[t] = min(self.Zieltemperatur_Solaranlage_L[t], self.T_koll_a_L[t])

                # Calculate average collector temperature and system mean temperature
                self.Tm_koll_L[t] = (self.T_koll_a_L[t] + self.T_koll_b_L[t]) / 2
                Tm_sys = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2
                
                # Select appropriate mean temperature for system calculation
                if self.Tm_koll_L[t] < Tm_sys and self.Tm_koll_L[t - 1] < Tm_sys:
                    self.Tm_L[t] = self.Tm_koll_L[t]
                else:
                    self.Tm_L[t] = Tm_sys

                # Calculate system collector power output using system mean temperature
                c1 = self.Koll_c1 * (self.Tm_L[t] - self.Lufttemperatur_L[t])
                c2 = self.Koll_c2 * (self.Tm_L[t] - self.Lufttemperatur_L[t]) ** 2
                c3 = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.Tm_L[t] - self.Lufttemperatur_L[t])
                Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - 
                            c1 - c2 - c3) * self.Bezugsfläche / 1000)

                # Calculate collector temperature with thermal inertia
                T_koll = (self.Lufttemperatur_L[t] - 
                        (self.Lufttemperatur_L[t] - self.Tgkoll_L[t - 1]) * 
                        exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                        (Pkoll * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Apply target temperature limitation to glycol temperature
                self.Tgkoll_L[t] = min(self.Zieltemperatur_Solaranlage_L[t], T_koll)

                # Calculate collector field output with temperature corrections
                if T_koll > self.Tgkoll_L[t - 1]:
                    # Apply temperature correction factor if target temperature is reached
                    Pkoll_temp_corr = ((T_koll - self.Tgkoll_L[t]) / (T_koll - self.Tgkoll_L[t - 1]) * Pkoll 
                                    if self.Tgkoll_L[t] >= self.Zieltemperatur_Solaranlage_L[t] else 0)

                    # Determine collector field output considering stagnation protection
                    self.Kollektorfeldertrag_L[t] = (max(0, min(Pkoll, Pkoll_temp_corr)) 
                                                    if self.Stagnation_L[t - 1] <= 0 else 0)
                else:
                    # No output if collector temperature is not increasing
                    self.Kollektorfeldertrag_L[t] = 0

                # Set system heat output to collector field output
                self.Wärmeleistung_kW[t] = self.Kollektorfeldertrag_L[t]

                # Check for stagnation conditions and activate protection
                same_day = (np.datetime_as_string(time_steps[t], unit='D') == 
                        np.datetime_as_string(time_steps[t - 1], unit='D'))
                excess_generation = self.Kollektorfeldertrag_L[t] > remaining_load
                storage_full = self.Speicherinhalt[t] >= self.QSmax
                
                self.Stagnation_L[t] = 1 if (same_day and excess_generation and storage_full) else 0

        else:
            # System inactive: no heat generation
            self.Wärmeleistung_kW[t] = 0

        # Update cumulative energy generation
        self.Wärmemenge_MWh += self.Wärmeleistung_kW[t] * duration / 1000  # Convert kW·h to MWh

        # Return heat output and zero electrical output (solar thermal only)
        return self.Wärmeleistung_kW[t], 0

    def calculate(self, economic_parameters: Dict[str, Union[float, str]], duration: float, 
                load_profile: np.ndarray, **kwargs) -> Dict[str, Union[str, float, np.ndarray]]:
        """
        Perform comprehensive solar thermal system analysis including performance and economic evaluation.

        This method executes complete system calculation including thermal performance
        simulation, operational analysis, economic cost assessment, and environmental
        impact evaluation for solar thermal systems in district heating applications.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters containing:
            
            - electricity_price : float
                Electricity price [€/kWh] (not used for solar thermal)
            - gas_price : float
                Natural gas price [€/kWh] (not used for solar thermal)
            - wood_price : float
                Wood pellet price [€/kWh] (not used for solar thermal)
            - capital_interest_rate : float
                Interest rate for capital costs [-]
            - inflation_rate : float
                Annual inflation rate [-]
            - time_period : int
                Economic analysis time period [years]
            - subsidy_eligibility : str
                Subsidy eligibility ("Ja" or "Nein")
            - hourly_rate : float
                Labor cost rate [€/hour]
        duration : float
            Simulation time step duration [hours].
            Typically 1.0 for hourly simulation.
        load_profile : numpy.ndarray
            Hourly thermal load demand profile [kW].
            Heat demand time series for the district heating system.
        **kwargs
            Additional calculation parameters:
            
            VLT_L : numpy.ndarray
                Supply temperature profile [°C]
            RLT_L : numpy.ndarray
                Return temperature profile [°C]
            TRY_data : tuple
                Test Reference Year weather data
            time_steps : numpy.ndarray
                Simulation time stamps

        Returns
        -------
        dict
            Comprehensive calculation results containing:
            
            - tech_name : str
                Technology identifier
            - Wärmemenge : float
                Total annual heat generation [MWh]
            - Wärmeleistung_L : numpy.ndarray
                Hourly heat output profile [kW]
            - WGK : float
                Heat generation cost [€/MWh]
            - Anzahl_Starts : int
                Number of operational start cycles
            - Betriebsstunden : float
                Total annual operating hours [h]
            - Betriebsstunden_pro_Start : float
                Average operating hours per start [h]
            - spec_co2_total : float
                Specific CO2 emissions [tCO2/MWh]
            - primärenergie : float
                Primary energy consumption [MWh]
            - Speicherladung_L : numpy.ndarray
                Storage energy content profile [kWh]
            - Speicherfüllstand_L : numpy.ndarray
                Storage filling level profile [-]
            - color : str
                Visualization color identifier

        Notes
        -----
        Calculation Workflow:
            
            **1. Thermal Simulation**:
            - Complete solar thermal system calculation
            - Weather data processing and solar radiation calculation
            - Collector performance modeling with thermal losses
            - Storage system integration and temperature stratification
            
            **2. Performance Analysis**:
            - Annual energy balance and efficiency calculation
            - Operational pattern analysis and start-stop cycle counting
            - Capacity factor and system utilization assessment
            - Storage performance and cycling analysis
            
            **3. Economic Evaluation**:
            - Investment cost calculation for collectors and storage
            - Operational cost analysis including maintenance
            - Subsidy consideration for renewable energy support
            - Levelized cost of heat generation calculation
            
            **4. Environmental Assessment**:
            - CO2 emission analysis (zero for solar thermal)
            - Primary energy factor evaluation
            - Environmental impact quantification

        Solar Thermal Performance:
            
            **Collector Efficiency**:
            The system efficiency depends on:
            - Solar irradiation availability and collector orientation
            - Temperature level requirements and thermal losses
            - Storage integration and operational strategy
            - Weather conditions and seasonal variations
            
            **Annual Performance**:
            Typical performance indicators:
            - Solar fraction: 20-60% of heat demand
            - Collector efficiency: 30-50% annual average
            - Storage utilization: 50-80% cycling efficiency
            - System availability: >95% operational readiness

        Economic Characteristics:
            
            **Investment Costs**:
            - Flat plate collectors: ~430 €/m²
            - Vacuum tube collectors: ~590 €/m²
            - Storage systems: ~750 €/m³
            - Installation and integration: ~50% of equipment costs
            
            **Operational Costs**:
            - Very low operational costs (no fuel required)
            - Minimal maintenance requirements
            - Long system lifetime (20+ years)
            - High reliability and low failure rates
            
            **Economic Benefits**:
            - Zero fuel costs for operation
            - Renewable energy subsidies available
            - Long-term cost stability
            - High environmental value

        Examples
        --------
        >>> # Comprehensive solar thermal system analysis
        >>> solar_system = SolarThermal(
        ...     name="District_Solar",
        ...     bruttofläche_STA=800.0,     # 800 m² collector area
        ...     vs=100.0,                   # 100 m³ storage volume
        ...     Typ="Flachkollektor"        # Flat plate collectors
        ... )
        >>> 
        >>> # Economic parameters for analysis
        >>> economics = {
        ...     'electricity_price': 0.25,      # €/kWh
        ...     'gas_price': 0.08,              # €/kWh
        ...     'wood_price': 0.05,             # €/kWh
        ...     'capital_interest_rate': 0.04,   # 4% interest
        ...     'inflation_rate': 0.02,         # 2% inflation
        ...     'time_period': 20,              # 20-year analysis
        ...     'subsidy_eligibility': "Ja",    # Eligible for subsidies
        ...     'hourly_rate': 45.0             # €/hour labor cost
        ... }
        >>> 
        >>> # Additional calculation parameters
        >>> calc_params = {
        ...     'VLT_L': supply_temperature_profile,   # °C
        ...     'RLT_L': return_temperature_profile,   # °C
        ...     'TRY_data': weather_data,              # TRY dataset
        ...     'time_steps': time_array               # Time stamps
        ... }
        >>> 
        >>> # Perform comprehensive calculation
        >>> results = solar_system.calculate(
        ...     economic_parameters=economics,
        ...     duration=1.0,  # 1-hour time steps
        ...     load_profile=heat_demand_profile,
        ...     **calc_params
        ... )
        >>> 
        >>> # Analyze results
        >>> print(f"Annual solar heat generation: {results['Wärmemenge']:.1f} MWh")
        >>> print(f"Heat generation cost: {results['WGK']:.2f} €/MWh")
        >>> print(f"Solar fraction: {results['Wärmemenge']/np.sum(heat_demand_profile)*1000:.1%}")
        >>> print(f"Operating hours: {results['Betriebsstunden']:.0f} h/year")
        >>> print(f"CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")

        >>> # Compare with and without subsidies
        >>> economics_no_subsidy = economics.copy()
        >>> economics_no_subsidy['subsidy_eligibility'] = "Nein"
        >>> 
        >>> results_no_subsidy = solar_system.calculate(
        ...     economics_no_subsidy, 1.0, heat_demand_profile, **calc_params
        ... )
        >>> 
        >>> cost_difference = results_no_subsidy['WGK'] - results['WGK']
        >>> print(f"Subsidy impact: {cost_difference:.2f} €/MWh cost reduction")

        >>> # Seasonal performance analysis
        >>> monthly_generation = np.zeros(12)
        >>> for month in range(12):
        ...     start_hour = month * 730  # Approximate month start
        ...     end_hour = (month + 1) * 730
        ...     monthly_generation[month] = np.sum(results['Wärmeleistung_L'][start_hour:end_hour]) / 1000
        >>> 
        >>> summer_generation = np.sum(monthly_generation[5:8])  # Jun-Aug
        >>> winter_generation = np.sum(monthly_generation[[11, 0, 1]])  # Dec-Feb
        >>> seasonal_ratio = summer_generation / winter_generation
        >>> print(f"Summer/Winter generation ratio: {seasonal_ratio:.1f}")

        >>> # Storage utilization analysis
        >>> max_storage_level = np.max(results['Speicherfüllstand_L'])
        >>> avg_storage_level = np.mean(results['Speicherfüllstand_L'])
        >>> storage_cycles = np.sum(np.diff(results['Speicherfüllstand_L']) > 0.1)
        >>> 
        >>> print(f"Maximum storage utilization: {max_storage_level:.1%}")
        >>> print(f"Average storage level: {avg_storage_level:.1%}")
        >>> print(f"Annual storage cycles: {storage_cycles}")

        See Also
        --------
        generate : Real-time heat generation method
        calculate_solar_thermal_with_storage : Detailed thermal simulation
        calculate_heat_generation_costs : Economic cost calculation
        """
        # Extract additional calculation parameters
        VLT_L = kwargs.get('VLT_L', np.full(len(load_profile), 70.0))
        RLT_L = kwargs.get('RLT_L', np.full(len(load_profile), 40.0))
        TRY_data = kwargs.get('TRY_data', (np.full(len(load_profile), 10.0),) * 4)
        time_steps = kwargs.get('time_steps', np.arange(len(load_profile)))

        # Perform thermal calculation if not already completed
        if not self.calculated:
            # Execute complete solar thermal system calculation
            self.calculate_solar_thermal_with_storage(
                load_profile,
                VLT_L,
                RLT_L,
                TRY_data,
                time_steps,
                duration
            )
            
            # Mark calculation as completed
            self.calculated = True

        # Display calculation completion summary
        print(f"Solar thermal system calculation completed: {self.name}")
        print(f"Total heat generation: {self.Wärmemenge_MWh:.2f} MWh")
        print(f"Collector output profile calculated: {len(self.Wärmeleistung_kW)} time steps")

        # Calculate operational statistics
        betrieb_mask = self.Wärmeleistung_kW > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                        if self.Anzahl_Starts > 0 else 0)

        # Display operational statistics
        print(f"Operational starts: {self.Anzahl_Starts}")
        print(f"Operating hours: {self.Betriebsstunden:.2f} h/year")
        print(f"Hours per start: {self.Betriebsstunden_pro_Start:.2f} h/start")

        # Calculate economic performance
        self.WGK = self.calculate_heat_generation_costs(economic_parameters)

        # Calculate environmental impact
        self.calculate_environmental_impact()

        # Compile comprehensive results dictionary
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'WGK': self.WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie_Solarthermie,
            'Speicherladung_L': self.Speicherinhalt,
            'Speicherfüllstand_L': self.Speicherfüllstand,
            'color': "red"  # Red color for solar thermal visualization
        }

        return results

    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters for the solar thermal system configuration.

        This method updates the solar thermal system parameters based on optimization
        variable values for system capacity optimization and economic analysis in
        district heating applications.

        Parameters
        ----------
        variables : list of float
            Optimization variable values in the order specified by variables_order.
            Contains optimized values for collector area and storage volume.
        variables_order : list of str
            Variable names corresponding to the values in variables list.
            Defines the mapping between variable names and values.
        idx : int
            Technology index for unique parameter identification in multi-technology systems.
            Used to identify technology-specific optimization variables.

        Notes
        -----
        Optimization Parameters:
            
            **Collector Area Optimization**:
            - Variable name: f"bruttofläche_STA_{idx}"
            - Parameter: self.bruttofläche_STA
            - Units: [m²]
            - Constraints: Defined by opt_area_min and opt_area_max
            
            **Storage Volume Optimization**:
            - Variable name: f"vs_{idx}"
            - Parameter: self.vs
            - Units: [m³]
            - Constraints: Defined by opt_volume_min and opt_volume_max

        Parameter Update Process:
            
            **1. Variable Extraction**:
            - Locate collector area parameter in variables list
            - Locate storage volume parameter in variables list
            - Apply bounds checking and validation
            
            **2. System Reconfiguration**:
            - Update collector area for performance calculations
            - Update storage volume for capacity calculations
            - Recalculate dependent system parameters
            
            **3. Cost Impact**:
            - Updated parameters affect investment costs
            - Performance characteristics change with sizing
            - Economic optimization depends on parameter selection

        The method provides error handling for missing optimization parameters
        and ensures system consistency after parameter updates.

        Examples
        --------
        >>> # Example optimization parameter setting
        >>> solar = SolarThermal("Solar_Opt", 500, 50, "Flachkollektor")
        >>> 
        >>> # Optimization variables from optimizer
        >>> opt_variables = [800.0, 75.0]  # 800 m² area, 75 m³ storage
        >>> var_order = ["bruttofläche_STA_1", "vs_1"]
        >>> tech_idx = 1
        >>> 
        >>> # Set optimized parameters
        >>> solar.set_parameters(opt_variables, var_order, tech_idx)
        >>> 
        >>> # Verify parameter update
        >>> print(f"Updated collector area: {solar.bruttofläche_STA} m²")
        >>> print(f"Updated storage volume: {solar.vs} m³")
        """
        try:
            # Extract collector area from optimization variables
            area_var_name = f"bruttofläche_STA_{idx}"
            if area_var_name in variables_order:
                area_index = variables_order.index(area_var_name)
                self.bruttofläche_STA = variables[area_index]
            
            # Extract storage volume from optimization variables
            volume_var_name = f"vs_{idx}"
            if volume_var_name in variables_order:
                volume_index = variables_order.index(volume_var_name)
                self.vs = variables[volume_index]
                
            # Recalculate dependent parameters after optimization update
            self.init_calculation_constants()
            
        except (ValueError, IndexError) as e:
            print(f"Error setting optimization parameters for {self.name}: {e}")
            print(f"Available variables: {variables_order}")
            print(f"Expected variables: bruttofläche_STA_{idx}, vs_{idx}")

    def add_optimization_parameters(self, idx: int) -> Tuple[List[float], List[str], List[Tuple[float, float]]]:
        """
        Define optimization parameters for solar thermal system sizing and configuration.

        This method provides the optimization framework with parameter definitions,
        initial values, and optimization bounds for solar thermal system capacity
        optimization in district heating applications.

        Parameters
        ----------
        idx : int
            Technology index for unique parameter identification in multi-technology systems.
            Used to create unique variable names for optimization.

        Returns
        -------
        tuple of (list, list, list)
            Optimization parameter specification:
            
            initial_values : list of float
                Initial parameter values for optimization start:
                [collector_area, storage_volume]
            variables_order : list of str
                Variable names for parameter identification:
                [f"bruttofläche_STA_{idx}", f"vs_{idx}"]
            bounds : list of tuple
                Parameter optimization bounds:
                [(area_min, area_max), (volume_min, volume_max)]

        Notes
        -----
        Optimization Variables:
            
            **Collector Area (bruttofläche_STA)**:
            - Physical meaning: Total collector gross area [m²]
            - Impact: Determines solar heat generation potential
            - Optimization range: Defined by opt_area_min to opt_area_max
            - Economic impact: Linear effect on investment costs
            
            **Storage Volume (vs)**:
            - Physical meaning: Thermal storage tank volume [m³]
            - Impact: Determines energy storage and system flexibility
            - Optimization range: Defined by opt_volume_min to opt_volume_max
            - Economic impact: Storage costs and system performance

        Optimization Considerations:
            
            **System Sizing**:
            - Collector area affects annual solar yield
            - Storage volume affects seasonal energy shifting
            - Optimal sizing depends on load profile characteristics
            - Economic optimum balances investment and performance
            
            **Technology Integration**:
            - Solar thermal complements other heating technologies
            - Storage enables load shifting and peak shaving
            - Sizing affects system interaction and control strategies
            
            **Economic Optimization**:
            - Investment costs scale with collector area and storage
            - Performance benefits increase with appropriate sizing
            - Subsidies may affect optimal configuration

        Examples
        --------
        >>> # Get optimization parameters for solar thermal system
        >>> solar = SolarThermal(
        ...     name="Solar_Opt",
        ...     bruttofläche_STA=400.0,     # Initial 400 m²
        ...     vs=40.0,                    # Initial 40 m³
        ...     Typ="Flachkollektor",
        ...     opt_area_min=100.0,         # Minimum 100 m²
        ...     opt_area_max=1000.0,        # Maximum 1000 m²
        ...     opt_volume_min=10.0,        # Minimum 10 m³
        ...     opt_volume_max=150.0        # Maximum 150 m³
        ... )
        >>> 
        >>> # Get optimization setup
        >>> initial_vals, var_names, bounds = solar.add_optimization_parameters(idx=1)
        >>> 
        >>> print("Optimization setup:")
        >>> print(f"Initial values: {initial_vals}")
        >>> print(f"Variable names: {var_names}")
        >>> print(f"Bounds: {bounds}")

        >>> # Integration with optimizer
        >>> from scipy.optimize import minimize
        >>> 
        >>> def objective_function(variables):
        ...     # Set parameters and calculate system performance
        ...     solar.set_parameters(variables, var_names, 1)
        ...     results = solar.calculate(economic_params, 1.0, load_profile, **kwargs)
        ...     return results['WGK']  # Minimize heat generation cost
        >>> 
        >>> # Perform optimization
        >>> result = minimize(
        ...     objective_function, 
        ...     initial_vals, 
        ...     bounds=bounds,
        ...     method='L-BFGS-B'
        ... )
        >>> 
        >>> # Apply optimal parameters
        >>> solar.set_parameters(result.x, var_names, 1)
        >>> print(f"Optimal collector area: {solar.bruttofläche_STA:.1f} m²")
        >>> print(f"Optimal storage volume: {solar.vs:.1f} m³")

        See Also
        --------
        set_parameters : Method to apply optimization parameter values
        EnergySystemOptimizer : Multi-objective optimization framework
        """
        # Define initial values from current system configuration
        initial_values = [self.bruttofläche_STA, self.vs]
        
        # Create unique variable names using technology index
        variables_order = [f"bruttofläche_STA_{idx}", f"vs_{idx}"]
        
        # Define optimization bounds from system constraints
        bounds = [
            (self.opt_area_min, self.opt_area_max),      # Collector area bounds [m²]
            (self.opt_volume_min, self.opt_volume_max)   # Storage volume bounds [m³]
        ]
        
        return initial_values, variables_order, bounds

    def get_display_text(self) -> str:
        """
        Generate formatted display text for GUI representation of the solar thermal system.

        Returns
        -------
        str
            Formatted text containing key system parameters and specifications.
        """
        return (f"{self.name}: Bruttokollektorfläche: {self.bruttofläche_STA:.1f} m², "
                f"Volumen Solarspeicher: {self.vs:.1f} m³, Kollektortyp: {self.Typ}, "
                f"spez. Kosten Speicher: {self.kosten_speicher_spez:.1f} €/m³, "
                f"spez. Kosten Flachkollektor: {self.kosten_fk_spez:.1f} €/m², "
                f"spez. Kosten Röhrenkollektor: {self.kosten_vrk_spez:.1f} €/m²")

    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract comprehensive technology data for reporting and documentation.

        Returns
        -------
        tuple of (str, str, str, str)
            Technology summary data:
            
            name : str
                System name identifier
            dimensions : str
                Technical specifications summary
            costs : str
                Investment cost breakdown
            full_costs : str
                Total investment costs
        """
        dimensions = (f"Bruttokollektorfläche: {self.bruttofläche_STA:.1f} m², "
                    f"Speichervolumen: {self.vs:.1f} m³, Kollektortyp: {self.Typ}")
        costs = (f"Investitionskosten Speicher: {self.Investitionskosten_Speicher:.1f} €, "
                f"Investitionskosten STA: {self.Investitionskosten_STA:.1f} €")
        full_costs = f"{self.Investitionskosten:.1f}"
        
        return self.name, dimensions, costs, full_costs

class SolarThermalStrategy(BaseStrategy):
    """
    Control strategy for solar thermal systems in district heating applications.

    This class implements the operational strategy for solar thermal systems,
    providing continuous renewable heat generation whenever solar irradiation
    is available, with minimal control constraints compared to other technologies.

    Parameters
    ----------
    charge_on : int
        Storage temperature threshold for system activation [°C].
        Not typically used for solar thermal as it operates continuously.
    charge_off : int, optional
        Storage temperature threshold for system deactivation [°C].
        Not typically used for solar thermal (default: None).

    Notes
    -----
    Solar Thermal Operation Strategy:
        
        **Continuous Operation**:
        - Solar thermal systems operate whenever solar irradiation is available
        - No minimum load constraints or complex control algorithms
        - Weather-dependent operation with maximum energy harvest focus
        - Priority renewable energy source in multi-technology systems
        
        **Control Philosophy**:
        - Maximize renewable energy utilization
        - Operate independently of storage temperature in most cases
        - Provide heat whenever possible to reduce fossil fuel consumption
        - Support system-wide renewable energy targets

    The strategy ensures optimal renewable energy harvesting while maintaining
    system reliability and integration with other heating technologies.

    Examples
    --------
    >>> # Create solar thermal control strategy
    >>> strategy = SolarThermalStrategy(
    ...     charge_on=0,    # Always operate when solar available
    ...     charge_off=0    # No deactivation temperature
    ... )
    >>> 
    >>> # Apply to solar thermal system
    >>> solar = SolarThermal("Solar_System", 500, 50, "Flachkollektor")
    >>> solar.strategy = strategy

    See Also
    --------
    BaseStrategy : Base class for heat generator control strategies
    SolarThermal : Solar thermal system implementation
    """
    
    def __init__(self, charge_on: int, charge_off: Optional[int] = None):
        """
        Initialize solar thermal control strategy with activation parameters.

        Parameters
        ----------
        charge_on : int
            Storage temperature for system activation [°C].
        charge_off : int, optional
            Storage temperature for system deactivation [°C].
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: float, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide solar thermal operation based on renewable energy priority strategy.

        This method implements the decision logic for solar thermal operation,
        prioritizing maximum renewable energy harvesting and continuous operation
        whenever solar irradiation is available.

        Parameters
        ----------
        current_state : float
            Current system state (not used in solar thermal operation).
        upper_storage_temp : float
            Current upper storage temperature [°C] (not used).
        lower_storage_temp : float
            Current lower storage temperature [°C] (not used).
        remaining_demand : float
            Remaining heat demand to be covered [kW] (not used).

        Returns
        -------
        bool
            Operation decision:
            
            True : Solar thermal should operate (always for renewable priority)
            False : Solar thermal should not operate (not applicable)

        Notes
        -----
        Decision Logic:
            
            **Renewable Energy Priority**:
            - Solar thermal always operates when solar irradiation is available
            - No constraints based on storage temperature or demand
            - Maximum renewable energy harvesting strategy
            - Weather-dependent operation with automatic control
            
            **System Integration**:
            - Provides renewable energy baseline for district heating
            - Operates independently of other technology states
            - Supports overall system decarbonization goals
            - Minimizes dependency on fossil fuel backup systems

        The decision logic ensures optimal renewable energy utilization
        and supports sustainable district heating operation.
        """
        # Solar thermal operates continuously when solar irradiation is available
        # Operation is weather-dependent and prioritizes renewable energy harvesting
        return True