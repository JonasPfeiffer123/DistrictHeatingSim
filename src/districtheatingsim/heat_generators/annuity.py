"""
Filename: annuity.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-24
Description: Economic evaluation module for technical installations according to VDI 2067.

This module provides comprehensive economic analysis capabilities for district heating
systems following the German VDI 2067 standard for economic evaluation of technical
installations. It implements standardized methodology for calculating annuities
considering capital costs, operational expenses, and revenue streams over the entire
system lifecycle.

The implementation supports lifecycle cost analysis for various district heating
technologies including heat pumps, thermal storage systems, solar thermal installations,
and conventional heating equipment. It provides standardized economic evaluation
suitable for investment decisions, subsidy calculations, and economic optimization
of district heating systems.

Features
--------
- VDI 2067 compliant annuity calculations
- Lifecycle cost analysis with inflation and interest rate considerations
- Capital-bound, demand-bound, and operation-bound cost components
- Residual value calculations for asset replacement cycles
- Revenue integration for economic optimization
- Support for multiple replacement cycles over analysis period

Mathematical Foundation
-----------------------
The module implements the VDI 2067 methodology for economic evaluation:

**Annuity Factor**:
    a = (q - 1) / [1 - q^(-T)]
    
    Where:
    - q = interest rate factor (1 + interest rate)
    - T = consideration time period [years]

**Price-Dynamic Present Value Factor**:
    b = [1 - (r/q)^T] / (q - r)
    
    Where:
    - r = inflation rate factor (1 + inflation rate)
    - q = interest rate factor
    - T = consideration time period [years]

**Total Annuity**:
    A_N = A_N_K + A_N_V + A_N_B + A_N_S - A_N_E
    
    Where:
    - A_N_K = Capital-bound costs annuity
    - A_N_V = Demand-bound costs annuity
    - A_N_B = Operation-bound costs annuity
    - A_N_S = Other costs annuity
    - A_N_E = Revenue annuity

Cost Categories
---------------
**Capital-Bound Costs (A_N_K)**:
    Investment costs, replacement costs, and residual value considerations
    
**Demand-Bound Costs (A_N_V)**:
    Energy costs (electricity, gas, fuel) varying with system operation
    
**Operation-Bound Costs (A_N_B)**:
    Maintenance, inspection, insurance, and labor costs
    
**Other Costs (A_N_S)**:
    Additional system-specific costs not covered by other categories

References
----------
Economic methodology based on:
- VDI 2067 - Economic efficiency of building installations
- DIN EN 15459 - Economic evaluation of heating and cooling systems
- German energy efficiency standards and subsidy programs
- District heating economic evaluation guidelines

Requirements
------------
- Python >= 3.8
- Standard mathematical operations (no external dependencies)

Applications
------------
The module supports economic evaluation for:
- Heat pump systems with various heat sources
- Thermal energy storage systems (sensible and latent)
- Solar thermal installations for district heating
- Combined heat and power (CHP) systems
- Conventional heating technologies (gas, oil, biomass)
- Grid infrastructure and distribution systems
"""

from typing import Union

def annuity(
    initial_investment_cost: float,
    asset_lifespan_years: int,
    installation_factor: float,
    maintenance_inspection_factor: float,
    operational_effort_h: float = 0,
    interest_rate_factor: float = 1.05,
    inflation_rate_factor: float = 1.03,
    consideration_time_period_years: int = 20,
    annual_energy_demand: float = 0,
    energy_cost_per_unit: float = 0,
    annual_revenue: float = 0,
    hourly_rate: float = 45
) -> float:
    """
    Calculate annuity for technical installations according to VDI 2067 standard.

    This function performs comprehensive economic evaluation of technical installations
    following the German VDI 2067 methodology. It calculates the equivalent annual
    cost considering all relevant cost components over the system lifecycle, including
    capital costs, operational expenses, energy costs, and revenue streams.

    The implementation provides standardized economic analysis suitable for comparing
    different technology options, optimizing system configurations, and supporting
    investment decisions in district heating applications. It handles multiple
    replacement cycles, inflation effects, and residual value calculations.

    Parameters
    ----------
    initial_investment_cost : float
        Initial capital investment cost [€].
        Total upfront cost including equipment, installation, and commissioning.
        Represents the primary investment for system acquisition.
    asset_lifespan_years : int
        Technical lifetime of the installation [years].
        Expected service life before replacement is required.
        Typical values: Heat pumps (20 years), Storage (30 years), Solar (25 years).
    installation_factor : float
        Installation cost factor [%].
        Additional costs for installation as percentage of investment cost.
        Includes labor, materials, and commissioning expenses.
    maintenance_inspection_factor : float
        Maintenance and inspection cost factor [%].
        Annual maintenance costs as percentage of investment cost.
        Covers preventive maintenance, inspections, and routine service.
    operational_effort_h : float, optional
        Annual operational effort [hours/year].
        Labor hours required for system operation and monitoring.
        Default is 0 for automated systems.
    interest_rate_factor : float, optional
        Interest rate factor [-].
        Calculated as (1 + interest_rate). Default is 1.05 (5% interest).
        Represents cost of capital and investment opportunity cost.
    inflation_rate_factor : float, optional
        Inflation rate factor [-].
        Calculated as (1 + inflation_rate). Default is 1.03 (3% inflation).
        Accounts for price escalation over analysis period.
    consideration_time_period_years : int, optional
        Economic analysis period [years].
        Total time horizon for economic evaluation. Default is 20 years.
        Should align with investment planning horizon.
    annual_energy_demand : float, optional
        Annual energy consumption [MWh/year or kWh/year].
        Energy input required for system operation.
        Default is 0 for systems without energy consumption.
    energy_cost_per_unit : float, optional
        Energy cost per unit [€/MWh or €/kWh].
        Unit cost of energy (electricity, gas, fuel).
        Must match units with annual_energy_demand.
    annual_revenue : float, optional
        Annual revenue from system operation [€/year].
        Income generated by the system (heat sales, grid services).
        Default is 0 for cost-only analysis.
    hourly_rate : float, optional
        Labor cost rate [€/hour].
        Hourly wage for operational and maintenance labor.
        Default is 45 €/hour for skilled technical personnel.

    Returns
    -------
    float
        Total annual equivalent cost [€/year].
        Levelized annual cost considering all economic factors.
        Positive values represent net costs, negative values represent net benefits.

    Notes
    -----
    Economic Analysis Methodology:
        
        **VDI 2067 Compliance**:
        The calculation follows the standardized German methodology for economic
        evaluation of building installations, ensuring consistency with national
        standards and enabling comparison between different technology options.
        
        **Cost Component Structure**:
        
        **Capital-Bound Costs (A_N_K)**:
        - Initial investment and replacement investments
        - Present value calculation for multiple replacement cycles
        - Residual value consideration for partial asset lifetime
        - Annualization using capital recovery factor
        
        **Demand-Bound Costs (A_N_V)**:
        - Energy costs varying with system operation
        - Price escalation over analysis period
        - Present value calculation with price-dynamic factors
        
        **Operation-Bound Costs (A_N_B)**:
        - Fixed maintenance and inspection costs
        - Variable operational labor costs
        - Insurance and administrative expenses
        
        **Revenue Integration**:
        - Heat sales revenue from district heating
        - Grid services and demand response compensation
        - Subsidy payments and incentive programs

    Calculation Sequence:
        
        **1. Parameter Validation and Preprocessing**:
        - Convert time periods to integers for discrete analysis
        - Calculate number of replacement cycles
        - Validate economic parameter consistency
        
        **2. Economic Factors Calculation**:
        - Annuity factor for capital recovery
        - Price-dynamic present value factors
        - Inflation adjustment over analysis period
        
        **3. Cost Component Calculation**:
        - Capital-bound costs with replacement cycles
        - Demand-bound costs with energy price escalation
        - Operation-bound costs with labor cost inflation
        
        **4. Revenue Integration**:
        - Revenue stream present value calculation
        - Net annuity determination
        - Final economic indicator computation

    Technical Considerations:
        
        **Multiple Replacement Cycles**:
        The function handles cases where asset lifetime is shorter than
        analysis period, calculating appropriate replacement investments
        and residual value for the final replacement cycle.
        
        **Inflation Effects**:
        Different cost components may have different inflation rates,
        though this implementation uses unified inflation for simplicity.
        Advanced applications can modify factors for specific cost categories.
        
        **Interest Rate Selection**:
        Interest rate should reflect cost of capital, risk assessment,
        and opportunity cost. Typical values range from 3-8% for
        district heating investments.

    Applications in District Heating:
        
        **Technology Comparison**:
        - Heat pump vs. conventional heating economic comparison
        - Storage technology selection and sizing optimization
        - Solar thermal integration economic assessment
        
        **System Optimization**:
        - Capacity sizing for minimum lifecycle cost
        - Operational strategy economic optimization
        - Grid expansion investment analysis
        
        **Subsidy Analysis**:
        - Economic impact of investment subsidies
        - Operational support program evaluation
        - Return on investment with various incentive levels

    Examples
    --------
    >>> # Basic heat pump economic analysis
    >>> from districtheatingsim.heat_generators.annuity import annuity
    >>> 
    >>> # Heat pump system parameters
    >>> investment_cost = 800000        # € for 1 MW heat pump system
    >>> technical_lifetime = 20        # years
    >>> installation_factor = 15       # % additional installation costs
    >>> maintenance_factor = 2.5       # % annual maintenance costs
    >>> 
    >>> # Economic parameters
    >>> interest_rate = 1.04           # 4% interest rate
    >>> inflation_rate = 1.025         # 2.5% inflation rate
    >>> analysis_period = 25           # years economic analysis
    >>> 
    >>> # Operational parameters
    >>> annual_electricity = 1500      # MWh/year electricity consumption
    >>> electricity_price = 280        # €/MWh electricity cost
    >>> annual_heat_sales = 3600000    # € revenue from heat sales
    >>> 
    >>> # Calculate annuity
    >>> annual_cost = annuity(
    ...     initial_investment_cost=investment_cost,
    ...     asset_lifespan_years=technical_lifetime,
    ...     installation_factor=installation_factor,
    ...     maintenance_inspection_factor=maintenance_factor,
    ...     interest_rate_factor=interest_rate,
    ...     inflation_rate_factor=inflation_rate,
    ...     consideration_time_period_years=analysis_period,
    ...     annual_energy_demand=annual_electricity,
    ...     energy_cost_per_unit=electricity_price,
    ...     annual_revenue=annual_heat_sales
    ... )
    >>> 
    >>> print(f"Annual equivalent cost: {annual_cost:,.0f} €/year")
    >>> 
    >>> # Calculate heat generation costs
    >>> annual_heat_delivery = 6000    # MWh/year heat delivery
    >>> heat_cost = annual_cost / annual_heat_delivery
    >>> print(f"Heat generation cost: {heat_cost:.2f} €/MWh")

    >>> # Comparison of different heat pump technologies
    >>> technologies = {
    ...     'Geothermal': {'investment': 1200, 'maintenance': 2.0, 'lifetime': 25},
    ...     'Air_Source': {'investment': 800, 'maintenance': 3.0, 'lifetime': 18},
    ...     'Wastewater': {'investment': 1000, 'maintenance': 2.5, 'lifetime': 20},
    ...     'River_Water': {'investment': 950, 'maintenance': 2.8, 'lifetime': 22}
    ... }
    >>> 
    >>> print("Technology Economic Comparison:")
    >>> for tech, params in technologies.items():
    ...     cost = annuity(
    ...         initial_investment_cost=params['investment'] * 1000,  # €/kW * 1000 kW
    ...         asset_lifespan_years=params['lifetime'],
    ...         installation_factor=15,
    ...         maintenance_inspection_factor=params['maintenance'],
    ...         interest_rate_factor=1.04,
    ...         inflation_rate_factor=1.025,
    ...         consideration_time_period_years=25,
    ...         annual_energy_demand=1500,
    ...         energy_cost_per_unit=280
    ...     )
    ...     heat_cost = cost / 6000  # €/MWh
    ...     print(f"{tech}: {heat_cost:.2f} €/MWh")

    >>> # Sensitivity analysis for interest rate
    >>> interest_rates = [1.02, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08]
    >>> base_cost = investment_cost
    >>> 
    >>> print("Interest Rate Sensitivity Analysis:")
    >>> for rate in interest_rates:
    ...     cost = annuity(
    ...         initial_investment_cost=base_cost,
    ...         asset_lifespan_years=20,
    ...         installation_factor=15,
    ...         maintenance_inspection_factor=2.5,
    ...         interest_rate_factor=rate,
    ...         inflation_rate_factor=1.025,
    ...         consideration_time_period_years=25,
    ...         annual_energy_demand=1500,
    ...         energy_cost_per_unit=280
    ...     )
    ...     interest_percent = (rate - 1) * 100
    ...     print(f"{interest_percent:.1f}%: {cost:,.0f} €/year")

    >>> # Storage system economic analysis
    >>> # Large thermal storage tank
    >>> storage_investment = 400000     # € for 10,000 m³ storage
    >>> storage_lifetime = 30          # years
    >>> storage_maintenance = 1.5      # % annual maintenance
    >>> pumping_energy = 200           # MWh/year for circulation pumps
    >>> 
    >>> storage_cost = annuity(
    ...     initial_investment_cost=storage_investment,
    ...     asset_lifespan_years=storage_lifetime,
    ...     installation_factor=20,    # Higher for complex installation
    ...     maintenance_inspection_factor=storage_maintenance,
    ...     operational_effort_h=100,  # Hours for monitoring/maintenance
    ...     interest_rate_factor=1.04,
    ...     inflation_rate_factor=1.025,
    ...     consideration_time_period_years=30,
    ...     annual_energy_demand=pumping_energy,
    ...     energy_cost_per_unit=280,
    ...     hourly_rate=55             # €/hour for specialized personnel
    ... )
    >>> 
    >>> print(f"Storage annual cost: {storage_cost:,.0f} €/year")
    >>> storage_capacity_cost = storage_cost / 10000  # €/m³/year
    >>> print(f"Storage capacity cost: {storage_capacity_cost:.2f} €/m³/year")

    >>> # Solar thermal system with revenue
    >>> solar_investment = 600000       # € for 1000 m² solar field
    >>> solar_lifetime = 25            # years
    >>> solar_maintenance = 1.8        # % annual maintenance
    >>> pump_energy = 50               # MWh/year for circulation
    >>> heat_revenue = 180000          # € annual heat sales
    >>> 
    >>> solar_cost = annuity(
    ...     initial_investment_cost=solar_investment,
    ...     asset_lifespan_years=solar_lifetime,
    ...     installation_factor=12,
    ...     maintenance_inspection_factor=solar_maintenance,
    ...     interest_rate_factor=1.04,
    ...     inflation_rate_factor=1.025,
    ...     consideration_time_period_years=25,
    ...     annual_energy_demand=pump_energy,
    ...     energy_cost_per_unit=280,
    ...     annual_revenue=heat_revenue
    ... )
    >>> 
    >>> print(f"Solar thermal net cost: {solar_cost:,.0f} €/year")
    >>> if solar_cost < 0:
    ...     print("Solar system generates net positive cash flow!")

    See Also
    --------
    VDI 2067 : German standard for economic evaluation of building installations
    DIN EN 15459 : European standard for economic evaluation of heating systems
    numpy.npv : Net present value calculations for alternative approaches
    scipy.optimize : Optimization functions for economic parameter studies

    Raises
    ------
    ValueError
        If asset_lifespan_years is zero or negative.
    ZeroDivisionError
        If interest and inflation rates are equal (mathematical singularity).
    TypeError
        If input parameters are not numeric types.
    """
    # Input validation and preprocessing
    if asset_lifespan_years <= 0:
        raise ValueError("Asset lifespan must be positive")
    
    if interest_rate_factor == inflation_rate_factor:
        raise ZeroDivisionError("Interest rate and inflation rate cannot be equal")
    
    # Convert time periods to integers for discrete analysis
    consideration_time_period_years = int(consideration_time_period_years)
    asset_lifespan_years = int(asset_lifespan_years)
    
    # Calculate number of complete replacement cycles
    n = max(consideration_time_period_years // asset_lifespan_years, 0)

    # Calculate economic factors according to VDI 2067
    # Annuity factor (capital recovery factor)
    a = (interest_rate_factor - 1) / (1 - (interest_rate_factor ** (-consideration_time_period_years)))
    
    # Price-dynamic present value factor for cost escalation
    b = (1 - (inflation_rate_factor / interest_rate_factor) ** consideration_time_period_years) / (interest_rate_factor - inflation_rate_factor)
    
    # Present value factors for different cost categories (unified in this implementation)
    b_v = b_B = b_IN = b_s = b_E = b

    # CAPITAL-BOUND COSTS (A_N_K)
    # Present value of all investment costs including replacements
    AN = initial_investment_cost + sum(
        initial_investment_cost * (inflation_rate_factor ** (i * asset_lifespan_years)) / 
        (interest_rate_factor ** (i * asset_lifespan_years)) 
        for i in range(1, n + 1)
    )

    # Residual value calculation for partial asset lifetime in final period
    R_W = (initial_investment_cost * 
           (inflation_rate_factor ** (n * asset_lifespan_years)) * 
           (((n + 1) * asset_lifespan_years - consideration_time_period_years) / asset_lifespan_years) * 
           (1 / (interest_rate_factor ** consideration_time_period_years)))

    # Annuity of capital-bound costs
    A_N_K = (AN - R_W) * a

    # DEMAND-BOUND COSTS (A_N_V)
    # Energy costs in the first period
    A_V1 = annual_energy_demand * energy_cost_per_unit
    
    # Annuity of demand-bound costs with price escalation
    A_N_V = A_V1 * a * b_v

    # OPERATION-BOUND COSTS (A_N_B)
    # Operating costs in the first period (labor)
    A_B1 = operational_effort_h * hourly_rate
    
    # Maintenance and inspection costs (percentage of investment)
    A_IN = initial_investment_cost * (installation_factor + maintenance_inspection_factor) / 100
    
    # Annuity of operation-bound costs
    A_N_B = A_B1 * a * b_B + A_IN * a * b_IN

    # OTHER COSTS (A_N_S)
    # Additional costs (currently not implemented, reserved for future extensions)
    A_S1 = 0
    A_N_S = A_S1 * a * b_s

    # TOTAL COST ANNUITY
    # Sum of all cost components (negative convention for costs)
    A_N = -(A_N_K + A_N_V + A_N_B + A_N_S)

    # REVENUE INTEGRATION
    # Annuity of revenues (positive cash flows)
    A_NE = annual_revenue * a * b_E
    
    # Net annuity including revenues
    A_N += A_NE

    # Return positive annuity value (costs are positive, revenues reduce costs)
    return -A_N