"""
Filename: annuity.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-24
Description: Contains the annuity calculation function for technical installations according to VDI 2067.
"""

def annuity(
    initial_investment_cost,
    asset_lifespan_years,
    installation_factor,
    maintenance_inspection_factor,
    operational_effort_h=0,
    interest_rate_factor=1.05,
    inflation_rate_factor=1.03,
    consideration_time_period_years=20,
    annual_energy_demand=0,
    energy_cost_per_unit=0,
    annual_revenue=0,
    hourly_rate=45
):
    """
    Calculates the annuity for technical installations according to VDI 2067.

    Parameters
    ----------
    initial_investment_cost : float
        Initial investment cost.
    asset_lifespan_years : int
        Useful life of the investment (years).
    installation_factor : float
        Installation factor (percentage).
    maintenance_inspection_factor : float
        Maintenance and inspection factor (percentage).
    operational_effort_h : float, optional
        Operating effort in hours per year. Default is 0.
    interest_rate_factor : float, optional
        Interest rate factor (e.g., 1.05 for 5%). Default is 1.05.
    inflation_rate_factor : float, optional
        Inflation rate factor (e.g., 1.03 for 3%). Default is 1.03.
    consideration_time_period_years : int, optional
        Consideration period in years. Default is 20.
    annual_energy_demand : float, optional
        Annual energy demand in unit. Default is 0. Use MWh or kWh as appropriate.
    energy_cost_per_unit : float, optional
        Energy costs in €/unit. Default is 0. Use €/MWh or €/kWh as appropriate.
    annual_revenue : float, optional
        Annual revenue (Erlöse). Default is 0.
    hourly_rate : float, optional
        Hourly rate for labor in €/h. Default is 45.

    Returns
    -------
    float
        Calculated annuity value.

    Notes
    -----
    The calculation follows the methodology of VDI 2067 for the economic
    evaluation of technical installations. All monetary values are in Euros.
    """
    # make sure T and TN are integers
    consideration_time_period_years = int(consideration_time_period_years)
    asset_lifespan_years = int(asset_lifespan_years)
    
    n = max(consideration_time_period_years // asset_lifespan_years, 0)

    a = (interest_rate_factor - 1) / (1 - (interest_rate_factor ** (-consideration_time_period_years)))  # Annuity factor
    b = (1 - (inflation_rate_factor / interest_rate_factor) ** consideration_time_period_years) / (interest_rate_factor - inflation_rate_factor)  # Price-dynamic present value factor
    b_v = b_B = b_IN = b_s = b_E = b  # Present value factors for different cost types

    # Capital-bound costs
    AN = initial_investment_cost + sum(initial_investment_cost * (inflation_rate_factor ** (i * asset_lifespan_years)) / (interest_rate_factor ** (i * asset_lifespan_years)) for i in range(1, n + 1)) # Present value of investment costs

    R_W = initial_investment_cost * (inflation_rate_factor**(n*asset_lifespan_years)) * (((n+1)*asset_lifespan_years-consideration_time_period_years)/asset_lifespan_years) * 1/(interest_rate_factor**consideration_time_period_years) # Residual value
    A_N_K = (AN - R_W) * a # Annuity of capital-bound costs

    # Demand-bound costs
    A_V1 = annual_energy_demand * energy_cost_per_unit # Energy costs in the first period
    A_N_V = A_V1 * a * b_v # Annuity of demand-bound costs

    # Operation-bound costs
    A_B1 = operational_effort_h * hourly_rate # Operating costs in the first period
    A_IN = initial_investment_cost * (installation_factor + maintenance_inspection_factor)/100 # Maintenance costs
    A_N_B = A_B1 * a * b_B + A_IN * a * b_IN # Annuity of operation-bound costs

    # Other costs
    A_S1 = 0 # Other costs in the first period
    A_N_S = A_S1 * a * b_s # Annuity of other costs

    A_N = - (A_N_K + A_N_V + A_N_B + A_N_S)  # Annuity of costs

    # Revenues
    A_NE = annual_revenue * a * b_E # Annuity of revenues

    A_N += A_NE # Annuity including revenues

    return -A_N  # Return the positive annuity value