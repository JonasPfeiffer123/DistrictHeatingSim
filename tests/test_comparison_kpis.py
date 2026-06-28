"""Unit tests for the variant-comparison KPI aggregation (BACKLOG B2).

`format_kpi_range` is the GUI-free domain/formatting logic extracted from
ComparisonTab.update_kpis (which previously inlined the same filter + single/range
+ unavailable logic six times next to Qt label-setting).
"""

from districtheatingsim.gui.ComparisonTab.comparison_data import format_kpi_range


def test_no_variants_returns_empty():
    assert format_kpi_range([], "WGK_Gesamt", ".1f") == "--"
    assert format_kpi_range([], "Trassenlänge", ".0f", empty="n.v.") == "n.v."


def test_single_value_is_formatted():
    data = [{"WGK_Gesamt": 123.456}]
    assert format_kpi_range(data, "WGK_Gesamt", ".1f") == "123.5"


def test_multiple_values_render_min_max_range():
    data = [{"WGK_Gesamt": 120.0}, {"WGK_Gesamt": 95.5}, {"WGK_Gesamt": 110.2}]
    assert format_kpi_range(data, "WGK_Gesamt", ".1f") == "95.5 - 120.0"


def test_missing_and_zero_values_are_filtered_out():
    # None and 0 are treated as "not provided".
    data = [{"WGK_Gesamt": 0}, {"WGK_Gesamt": None}, {}, {"WGK_Gesamt": 80.0}]
    assert format_kpi_range(data, "WGK_Gesamt", ".1f") == "80.0"


def test_all_missing_returns_empty():
    data = [{"WGK_Gesamt": 0}, {"other": 5}]
    assert format_kpi_range(data, "WGK_Gesamt", ".1f", empty="n.v.") == "n.v."


def test_format_spec_is_respected():
    data = [{"co2": 0.123456}]
    assert format_kpi_range(data, "co2", ".3f") == "0.123"


def test_equal_values_still_render_as_range():
    # Two variants with the same value → "min - max" (both equal); matches old behaviour.
    data = [{"x": 5.0}, {"x": 5.0}]
    assert format_kpi_range(data, "x", ".0f") == "5 - 5"
