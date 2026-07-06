"""
Tests for the GUI-free Leaflet helpers.

``_nearest_address`` labels HAST circles from the project's building CSV by nearest
coordinate, because the network export drops the address from the HAST feature (C33 AP1
follow-up).
"""

from districtheatingsim.gui.LeafletTab.leaflet_tab import _nearest_address

_BUILDINGS = [(0.0, 0.0, "Brückenstraße 10"), (100.0, 100.0, "Furtstraße 1")]


def test_returns_nearest_within_tolerance():
    assert _nearest_address((0.03, 0.02), _BUILDINGS) == "Brückenstraße 10"
    assert _nearest_address((100.5, 99.8), _BUILDINGS) == "Furtstraße 1"


def test_returns_none_when_too_far():
    assert _nearest_address((50.0, 50.0), _BUILDINGS) is None


def test_empty_or_missing_inputs():
    assert _nearest_address((0.0, 0.0), []) is None
    assert _nearest_address(None, _BUILDINGS) is None


def test_respects_custom_tolerance():
    # 3 m away: outside the 2 m default, inside a 5 m tolerance.
    assert _nearest_address((3.0, 0.0), _BUILDINGS) is None
    assert _nearest_address((3.0, 0.0), _BUILDINGS, tolerance=5.0) == "Brückenstraße 10"
