"""
Unit + regression tests for the VDI 2067 annuity calculation.

``annuity()`` is the economic backbone of every heat generator's WGK/LCOH.
It is pure and deterministic, which makes it the cheapest high-value test
target in the codebase. These tests also pin the C5 "footgun" documented in
BACKLOG.md: the function expects interest/inflation as *factors* (1.05), not
*rates* (0.05), and silently produces ~0 cost when given a rate.

Reference values were captured from the current implementation (golden master).
If the economic model changes intentionally, update the expected numbers in the
same commit so the diff makes the change explicit.
"""

import pytest

from districtheatingsim.heat_generators.annuity import annuity


class TestAnnuityFactorConvention:
    """Core math in the correct (factor) convention."""

    def test_reference_value_example15(self):
        # Parameters from examples/15_example_annuity.py.
        result = annuity(
            initial_investment_cost=10000,
            asset_lifespan_years=20,
            installation_factor=0.03,
            maintenance_inspection_factor=0.02,
            operational_effort_h=10,
            interest_rate_factor=1.05,
            inflation_rate_factor=1.03,
            consideration_time_period_years=20,
            annual_energy_demand=15000,
            energy_cost_per_unit=0.15,
            annual_revenue=0,
        )
        assert result == pytest.approx(4267.681094, rel=1e-6)

    def test_capital_only_is_positive(self):
        # No energy, no maintenance, no labour — pure capital recovery.
        result = annuity(
            initial_investment_cost=10000,
            asset_lifespan_years=20,
            installation_factor=0,
            maintenance_inspection_factor=0,
            interest_rate_factor=1.05,
            inflation_rate_factor=1.03,
            consideration_time_period_years=20,
        )
        assert result == pytest.approx(802.425872, rel=1e-6)
        assert result > 0

    def test_revenue_reduces_net_annuity(self):
        common = dict(
            initial_investment_cost=10000,
            asset_lifespan_years=20,
            installation_factor=0.03,
            maintenance_inspection_factor=0.02,
            interest_rate_factor=1.05,
            inflation_rate_factor=1.03,
            consideration_time_period_years=20,
        )
        with_revenue = annuity(**common, annual_revenue=5000)
        without_revenue = annuity(**common, annual_revenue=0)
        assert with_revenue < without_revenue

    def test_higher_maintenance_increases_cost(self):
        common = dict(
            initial_investment_cost=10000,
            asset_lifespan_years=20,
            installation_factor=0,
            interest_rate_factor=1.05,
            inflation_rate_factor=1.03,
            consideration_time_period_years=20,
        )
        low = annuity(**common, maintenance_inspection_factor=0)
        high = annuity(**common, maintenance_inspection_factor=5.0)
        assert high > low


class TestAnnuityC5Footgun:
    """Characterization tests for the rate-vs-factor footgun (BACKLOG C5)."""

    def test_rate_instead_of_factor_silently_collapses_to_zero(self):
        # Passing 0.05/0.03 (rates) instead of 1.05/1.03 (factors) yields ~0,
        # with no error. If the API is later hardened (validate q > 1 or accept
        # rates), this assertion will fail and must be updated to the new
        # behaviour — that failure is the desired alarm.
        buggy = annuity(
            initial_investment_cost=10000,
            asset_lifespan_years=20,
            installation_factor=0.03,
            maintenance_inspection_factor=0.02,
            operational_effort_h=10,
            interest_rate_factor=0.05,
            inflation_rate_factor=0.03,
            consideration_time_period_years=20,
            annual_energy_demand=15000,
            energy_cost_per_unit=0.15,
        )
        assert buggy == pytest.approx(0.0, abs=1e-9)


class TestAnnuityValidation:
    """Guard rails that are already enforced."""

    def test_zero_lifespan_raises(self):
        with pytest.raises(ValueError):
            annuity(10000, 0, 0.03, 0.02)

    def test_negative_lifespan_raises(self):
        with pytest.raises(ValueError):
            annuity(10000, -5, 0.03, 0.02)

    def test_equal_interest_and_inflation_raises(self):
        with pytest.raises(ZeroDivisionError):
            annuity(
                10000, 20, 0.03, 0.02,
                interest_rate_factor=1.05,
                inflation_rate_factor=1.05,
            )
