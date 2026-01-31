"""
Annuity Calculation Module
==========================

Economic evaluation module for technical installations according to VDI 2067.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

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

Features:

- VDI 2067 compliant annuity calculations
- Lifecycle cost analysis with inflation and interest rate considerations
- Capital-bound, demand-bound, and operation-bound cost components
- Residual value calculations for asset replacement cycles
- Revenue integration for economic optimization
- Support for multiple replacement cycles over analysis period

Mathematical Foundation:

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

Cost Categories:

**Capital-Bound Costs (A_N_K)**:
    Investment costs, replacement costs, and residual value considerations
    
**Demand-Bound Costs (A_N_V)**:
    Energy costs (electricity, gas, fuel) varying with system operation
    
**Operation-Bound Costs (A_N_B)**:
    Maintenance, inspection, insurance, and labor costs
    
**Other Costs (A_N_S)**:
    Additional system-specific costs not covered by other categories
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
    Calculate annuity for technical installations according to VDI 2067.

    :param initial_investment_cost: Initial capital investment cost [€]
    :type initial_investment_cost: float
    :param asset_lifespan_years: Technical lifetime [years]
    :type asset_lifespan_years: int
    :param installation_factor: Installation cost factor [%]
    :type installation_factor: float
    :param maintenance_inspection_factor: Annual maintenance cost factor [%]
    :type maintenance_inspection_factor: float
    :param operational_effort_h: Annual operational effort [hours/year], defaults to 0
    :type operational_effort_h: float
    :param interest_rate_factor: Interest rate factor (1 + rate), defaults to 1.05
    :type interest_rate_factor: float
    :param inflation_rate_factor: Inflation rate factor (1 + rate), defaults to 1.03
    :type inflation_rate_factor: float
    :param consideration_time_period_years: Economic analysis period [years], defaults to 20
    :type consideration_time_period_years: int
    :param annual_energy_demand: Annual energy consumption [MWh/year], defaults to 0
    :type annual_energy_demand: float
    :param energy_cost_per_unit: Energy cost [€/MWh], defaults to 0
    :type energy_cost_per_unit: float
    :param annual_revenue: Annual revenue [€/year], defaults to 0
    :type annual_revenue: float
    :param hourly_rate: Labor cost rate [€/hour], defaults to 45
    :type hourly_rate: float
    :return: Total annual equivalent cost [€/year]
    :rtype: float
    
    .. note::
       Implements VDI 2067 methodology for lifecycle cost analysis including capital-bound,
       demand-bound, and operation-bound costs with revenue integration.
    
    :raises ValueError: If
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