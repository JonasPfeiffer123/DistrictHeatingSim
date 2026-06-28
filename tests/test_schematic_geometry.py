"""
Unit tests for the GUI-free generator-schematic geometry (BACKLOG B1).

``schematic_geometry.py`` holds the coordinate math extracted from the
QGraphicsScene in ``_11_generator_schematic.py`` — grid snapping and the
collision-avoiding label placement — so it is testable without a QApplication.
The label placement is exercised with a fake ``collides`` predicate instead of a
real scene.
"""

from districtheatingsim.gui.EnergySystemTab.schematic_geometry import optimal_label_position, snap_to_grid

# ----------------------------------------------------------------------------
# snap_to_grid
# ----------------------------------------------------------------------------


class TestSnapToGrid:
    def test_grid_size_one_rounds_to_integers(self):
        assert snap_to_grid(12.4, 7.6, 1) == (12, 8)

    def test_snaps_to_multiples(self):
        assert snap_to_grid(23, 47, 10) == (20, 50)

    def test_exact_grid_point_unchanged(self):
        assert snap_to_grid(40, 60, 20) == (40, 60)


# ----------------------------------------------------------------------------
# optimal_label_position
# ----------------------------------------------------------------------------

# Shared geometry for the placement cases:
#   test_x       = 100 - 30/2          = 85
#   base_y_below = 50 + 40 + 12        = 102
#   base_y_above = 50 - 40 - 12 - 10   = -12
_ITEM = dict(item_x=100, item_y=50, item_height=40, label_width=30, label_height=10)

_NEVER = lambda x, y, w, h: False  # noqa: E731 - terse predicate for tests
_ALWAYS = lambda x, y, w, h: True  # noqa: E731


class TestOptimalLabelPosition:
    def test_label_is_horizontally_centred(self):
        x, _ = optimal_label_position(**_ITEM, is_storage=False, collides=_NEVER)
        assert x == 85  # item_x - label_width / 2

    def test_non_storage_prefers_below(self):
        pos = optimal_label_position(**_ITEM, is_storage=False, collides=_NEVER)
        assert pos == (85, 102)  # base_y_below at offset 0

    def test_storage_prefers_above(self):
        pos = optimal_label_position(**_ITEM, is_storage=True, collides=_NEVER)
        assert pos == (85, -12)  # base_y_above at offset 0

    def test_non_storage_falls_back_to_above_at_same_offset(self):
        # Below position (y=102) blocked, above (y=-12) free -> takes above before stepping.
        collides = lambda x, y, w, h: y == 102  # noqa: E731
        pos = optimal_label_position(**_ITEM, is_storage=False, collides=collides)
        assert pos == (85, -12)

    def test_steps_to_next_offset_when_both_sides_blocked(self):
        # Offset 0 (102 and -12) blocked -> next below candidate is 102+15 = 117.
        collides = lambda x, y, w, h: y in (102, -12)  # noqa: E731
        pos = optimal_label_position(**_ITEM, is_storage=False, collides=collides)
        assert pos == (85, 117)

    def test_storage_steps_above_first(self):
        # Storage tries above (-12) first; block it -> below (102) at same offset.
        collides = lambda x, y, w, h: y == -12  # noqa: E731
        pos = optimal_label_position(**_ITEM, is_storage=True, collides=collides)
        assert pos == (85, 102)

    def test_fallback_to_base_below_when_everything_collides(self):
        pos = optimal_label_position(**_ITEM, is_storage=False, collides=_ALWAYS)
        assert pos == (85, 102)  # preferred base for non-storage

    def test_fallback_to_base_above_for_storage_when_everything_collides(self):
        pos = optimal_label_position(**_ITEM, is_storage=True, collides=_ALWAYS)
        assert pos == (85, -12)  # preferred base for storage

    def test_collides_receives_full_label_rect(self):
        seen = []

        def collides(x, y, w, h):
            seen.append((x, y, w, h))
            return False

        optimal_label_position(**_ITEM, is_storage=False, collides=collides)
        # First probe is the centred below position with the label's own size.
        assert seen[0] == (85, 102, 30, 10)
