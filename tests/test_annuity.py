"""
Unit + regression tests for the VDI 2067 annuity calculation.

``annuity()`` is the economic backbone of every heat generator's WGK/LCOH.
It is pure and deterministic, which makes it the cheapest high-value test
target in the codebase. The function expects interest/inflation as *factors*
(1.05), not *rates* (0.05); the C5 footgun (a rate silently producing ~0 cost) is
now guarded and raises a clear ValueError (see ``TestAnnuityRateFactorGuard``).

Reference values were captured from the current implementation (golden master).
If the economic model changes intentionally, update the expected numbers in the
same commit so the diff makes the change explicit.
"""

import pytest

from districtheatingsim.heat_generators.annuity import annuity, infrastructure_annuity


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


class TestAnnuityRateFactorGuard:
    """C5 fixed: passing a rate (0.05) instead of a factor (1.05) now raises a
    clear ValueError instead of silently collapsing the cost to ~0.
    """

    def test_interest_rate_instead_of_factor_raises(self):
        with pytest.raises(ValueError, match="factor"):
            annuity(
                initial_investment_cost=10000,
                asset_lifespan_years=20,
                installation_factor=0.03,
                maintenance_inspection_factor=0.02,
                interest_rate_factor=0.05,  # rate, not factor
                inflation_rate_factor=1.03,
            )

    def test_inflation_rate_instead_of_factor_raises(self):
        with pytest.raises(ValueError, match="factor"):
            annuity(
                initial_investment_cost=10000,
                asset_lifespan_years=20,
                installation_factor=0.03,
                maintenance_inspection_factor=0.02,
                interest_rate_factor=1.05,
                inflation_rate_factor=0.03,  # rate, not factor
            )

    def test_interest_factor_of_one_raises(self):
        # q = 1 (0 % interest) makes the annuity factor 0/0 — must be rejected.
        with pytest.raises(ValueError):
            annuity(
                initial_investment_cost=10000,
                asset_lifespan_years=20,
                installation_factor=0.03,
                maintenance_inspection_factor=0.02,
                interest_rate_factor=1.0,
                inflation_rate_factor=1.03,
            )

    def test_zero_inflation_factor_is_valid(self):
        # r = 1.0 (0 % inflation) is a legitimate factor and must NOT raise.
        result = annuity(
            initial_investment_cost=10000,
            asset_lifespan_years=20,
            installation_factor=0,
            maintenance_inspection_factor=0,
            interest_rate_factor=1.05,
            inflation_rate_factor=1.0,
        )
        assert result > 0


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
                10000,
                20,
                0.03,
                0.02,
                interest_rate_factor=1.05,
                inflation_rate_factor=1.05,
            )


class TestInfrastructureAnnuity:
    """The GUI adapter (extracted from the cost tab, BACKLOG B2): maps an
    economic_parameters mapping to annuity() and guards a zero lifespan."""

    def test_zero_lifespan_returns_zero_not_raises(self, economic_parameters):
        # A not-yet-configured infrastructure row (TN=0) must yield 0, not the
        # ValueError that annuity() raises for a zero lifespan.
        assert infrastructure_annuity(1000, 0, 1.0, 2.0, 0, economic_parameters) == 0.0

    def test_matches_annuity_with_mapped_parameters(self, economic_parameters):
        A0, TN, f_inst, f_wi, effort = 50000, 20, 1.0, 2.0, 10
        expected = annuity(
            A0,
            TN,
            f_inst,
            f_wi,
            effort,
            interest_rate_factor=economic_parameters["capital_interest_rate"],
            inflation_rate_factor=economic_parameters["inflation_rate"],
            consideration_time_period_years=economic_parameters["time_period"],
            hourly_rate=economic_parameters["hourly_rate"],
        )
        assert infrastructure_annuity(A0, TN, f_inst, f_wi, effort, economic_parameters) == expected
        assert expected > 0  # sanity: a real cost row has a positive annuity
