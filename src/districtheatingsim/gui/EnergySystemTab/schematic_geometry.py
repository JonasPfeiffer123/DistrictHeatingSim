"""
GUI-free geometry helpers for the generator schematic (BACKLOG B1).

The schematic in ``_11_generator_schematic.py`` is mostly genuine QGraphicsScene
glue, but a couple of coordinate computations are pure math that was trapped
inside scene methods (and therefore untestable). They are extracted here as plain
functions over floats so they can be unit-tested without a QApplication; the scene
methods are thin adapters that convert to/from ``QPointF`` and supply a collision
predicate.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from collections.abc import Callable


def snap_to_grid(x: float, y: float, grid_size: float) -> tuple[float, float]:
    """
    Snap a point to the nearest grid intersection.

    :param x: X coordinate.
    :param y: Y coordinate.
    :param grid_size: Grid spacing (the point is rounded to a multiple of this).
    :return: The snapped ``(x, y)``.
    :rtype: tuple[float, float]
    """
    return (
        round(x / grid_size) * grid_size,
        round(y / grid_size) * grid_size,
    )


def optimal_label_position(
    item_x: float,
    item_y: float,
    item_height: float,
    label_width: float,
    label_height: float,
    is_storage: bool,
    collides: Callable[[float, float, float, float], bool],
    *,
    padding: float = 12,
    max_offset: int = 60,
    step: int = 15,
) -> tuple[float, float]:
    """
    Choose a non-colliding label position for a schematic component.

    The label is horizontally centred on the component. Vertically it is tried at
    increasing offsets, preferring *below* the component for generators/consumers
    and *above* for storages (with the opposite side as fallback at each offset).
    If no collision-free slot is found within ``max_offset``, the preferred base
    position is returned regardless.

    :param item_x: Component X (its origin / left edge in scene coords).
    :param item_y: Component Y (its top edge in scene coords).
    :param item_height: Component bounding-box height.
    :param label_width: Label width.
    :param label_height: Label height.
    :param is_storage: Whether the component is a storage (flips the side preference).
    :param collides: Predicate ``(x, y, w, h) -> bool``; ``True`` if a label rect at
        that position would overlap an existing label.
    :param padding: Gap between component and label.
    :param max_offset: Largest vertical offset to probe (exclusive).
    :param step: Offset increment.
    :return: The chosen ``(x, y)`` for the label's top-left corner.
    :rtype: tuple[float, float]
    """
    test_x = item_x - label_width / 2
    base_y_below = item_y + item_height + padding
    base_y_above = item_y - item_height - padding - label_height

    for y_offset in range(0, max_offset, step):
        if not is_storage:
            sides = (base_y_below + y_offset, base_y_above - y_offset)  # below first
        else:
            sides = (base_y_above - y_offset, base_y_below + y_offset)  # above first
        for test_y in sides:
            if not collides(test_x, test_y, label_width, label_height):
                return (test_x, test_y)

    # No collision-free slot found — fall back to the preferred base position.
    return (test_x, base_y_above if is_storage else base_y_below)
