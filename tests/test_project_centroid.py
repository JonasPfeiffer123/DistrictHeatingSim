"""Unit tests for the GeoJSON centroid helper (BACKLOG B2).

`centroid_of` is the GUI-free recursion extracted from
ProjectModel.calculate_centroid (which recursed through `self`). Used to place a
marker at the centre of imported building/network geometries.
"""

import pytest

from districtheatingsim.gui.ProjectTab.project_tab import centroid_of


def test_single_point_returns_itself():
    assert centroid_of([2.0, 4.0]) == (2.0, 4.0)


def test_linestring_averages_vertices():
    # A LineString is a list of [x, y] points.
    line = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    assert centroid_of(line) == (5.0, 5.0)


def test_polygon_one_ring():
    # A Polygon is a list of rings; one ring of four corners centres at (5, 5).
    polygon = [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]]
    assert centroid_of(polygon) == (5.0, 5.0)


def test_nested_multipolygon_averages_part_centroids():
    # Two square parts centred at (0,0) and (10,10) → overall (5, 5).
    part_a = [[[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]]]
    part_b = [[[9.0, 9.0], [11.0, 9.0], [11.0, 11.0], [9.0, 11.0]]]
    multipolygon = [part_a, part_b]
    x, y = centroid_of(multipolygon)
    assert x == pytest.approx(5.0)
    assert y == pytest.approx(5.0)
