"""
Helpers for reading pandapipes pipe std-type properties (GUI-free, numpy-only).
===============================================================================

pandapipes >= 0.14 ships ISOPLUS bonded-steel pipes (the successor to the old
"KMR …" types). Those carry their heat loss as ``u_w_per_mk`` [W/(m·K)] (per pipe
length) and leave the legacy ``u_w_per_m2k`` [W/(m²·K)] column empty, whereas the
0.13 KMR types stored ``u_w_per_m2k`` directly. Code that reads ``u_w_per_m2k`` from
the std-type table therefore gets NaN for ISOPLUS pipes.

``resolve_pipe_u_w_per_m2k`` returns the per-area coefficient for either format,
converting the per-length value the same way pandapipes does internally
(``u_w_per_m2k = u_w_per_mk / (π · outer_diameter)``).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import math
import re

import numpy as np

# Legacy "KMR <DN>/<outer>-<insulation>v" pipe names map to the ISOPLUS bonded-steel
# successors "ISOPLUS_DRE<DN>_<insulation>x" in pandapipes >= 0.14. The outer-diameter
# part is sometimes blank in old data (e.g. "KMR 175/-2v"), so it is matched loosely.
_KMR_PATTERN = re.compile(r"^KMR\s+(\d+)/[^-]*-(\d+)v$")
_ISOPLUS_PATTERN = re.compile(r"^ISOPLUS_DRE(\d+)(_\w+)$")

# Material of the ISOPLUS bonded-steel pipes — the only pipe family relevant for district
# heating networks. Other pandapipes std-types (gas/water utility pipes) are filtered out
# of the UI pipe selectors.
ISOPLUS_MATERIAL = "P235GH/PUR/PEHD"

# ISOPLUS insulation grades (the "_<grade>" suffix), thinnest → thickest. The grade sets
# the insulation thickness / heat loss, not the bore — every grade offers the full DN
# range with identical inner diameters. The UI lets the user pick a grade first, then a
# diameter within it; the optimizer keeps the grade fixed (see utilities.optimize/init).
ISOPLUS_GRADE_ORDER = ["STD", "1x", "2x"]

#: Human-readable grade labels for the pipe selector (German UI). The raw suffix is kept
#: in parentheses so the mapping stays unambiguous.
ISOPLUS_GRADE_LABELS = {
    "STD": "Standard (STD)",
    "1x": "1-fach verstärkt (1x)",
    "2x": "2-fach verstärkt (2x)",
}


def parse_isoplus_std_type(name) -> tuple[int, str] | None:
    """
    Split an ISOPLUS std-type name into its nominal width and insulation grade.

    ``"ISOPLUS_DRE100_2x"`` → ``(100, "2x")``. Returns ``None`` for names that are not
    ISOPLUS ``DRE`` types.

    :param name: A pipe std-type name.
    :return: ``(nominal_width_dn, grade)`` or ``None``.
    :rtype: tuple[int, str] | None
    """
    match = _ISOPLUS_PATTERN.match(str(name))
    if not match:
        return None
    return int(match.group(1)), match.group(2).lstrip("_")


def group_isoplus_by_grade(names) -> dict[str, list[tuple[int, str]]]:
    """
    Group ISOPLUS std-type names by insulation grade for the cascading pipe selector.

    :param names: ISOPLUS std-type names (e.g. from :func:`isoplus_std_type_names`).
    :return: ``{grade: [(dn, name), …]}`` with each list sorted by ascending nominal
        width and the grades ordered :data:`ISOPLUS_GRADE_ORDER` first (any unknown
        grades appended in sorted order). Non-ISOPLUS names are ignored.
    :rtype: dict[str, list[tuple[int, str]]]
    """
    groups: dict[str, list[tuple[int, str]]] = {}
    for name in names:
        parsed = parse_isoplus_std_type(name)
        if parsed is None:
            continue
        dn, grade = parsed
        groups.setdefault(grade, []).append((dn, str(name)))

    ordered = [g for g in ISOPLUS_GRADE_ORDER if g in groups]
    ordered += sorted(g for g in groups if g not in ISOPLUS_GRADE_ORDER)
    return {grade: sorted(groups[grade]) for grade in ordered}


def isoplus_std_type_names(std_types) -> list[str]:
    """
    Filter a pandapipes pipe-std-type table to the ISOPLUS bonded-steel types.

    :param std_types: DataFrame from ``pp.std_types.available_std_types(net, "pipe")``
        (or ``None``).
    :return: The names of the ISOPLUS pipe std-types, preferring the ``material`` column
        and falling back to the ``ISOPLUS`` name prefix if that column is absent.
    :rtype: list[str]
    """
    if std_types is None or len(std_types.index) == 0:
        return []
    if "material" in std_types.columns:
        names = std_types.index[std_types["material"] == ISOPLUS_MATERIAL].tolist()
        if names:
            return names
    return [name for name in std_types.index if str(name).startswith("ISOPLUS")]


def kmr_to_isoplus_std_type(name) -> str | None:
    """
    Map a legacy ``KMR …`` pipe std-type name to its nominal ISOPLUS equivalent.

    ``KMR 100/250-2v`` → ``ISOPLUS_DRE100_2x``. The returned type may not exist in
    pandapipes for every nominal width (e.g. ``ISOPLUS_DRE175_2x``); use
    :func:`nearest_isoplus_for_kmr` to snap to an available size. Returns ``None`` for
    names that are not legacy KMR types (e.g. already-ISOPLUS names).

    :param name: A pipe std-type name.
    :return: The nominal ISOPLUS name, or ``None`` if ``name`` is not a KMR type.
    :rtype: str | None
    """
    match = _KMR_PATTERN.match(str(name))
    if not match:
        return None
    nominal_width, insulation = match.group(1), match.group(2)
    return f"ISOPLUS_DRE{nominal_width}_{insulation}x"


def nearest_isoplus_for_kmr(name, catalog) -> str | None:
    """
    Map a legacy KMR name to an ISOPLUS std-type that exists in ``catalog``.

    Prefers the exact ``ISOPLUS_DRE<DN>_<n>x`` successor; if that nominal width is not
    offered (e.g. DN175), snaps to the same insulation grade at the nearest available
    nominal width, rounding **up** on a tie (the hydraulically safer, larger pipe).

    :param name: A legacy KMR std-type name.
    :param catalog: Pipe std-type catalog (a ``DataFrame`` with the type names as index).
    :return: An ISOPLUS type present in ``catalog``, or ``None`` if ``name`` is not KMR
        or no same-grade ISOPLUS type exists.
    :rtype: str | None
    """
    candidate = kmr_to_isoplus_std_type(name)
    if candidate is None:
        return None
    if candidate in catalog.index:
        return candidate

    match = _ISOPLUS_PATTERN.match(candidate)
    if not match:
        return None
    target_dn, suffix = int(match.group(1)), match.group(2)

    available = []
    for type_name in catalog.index:
        iso = _ISOPLUS_PATTERN.match(str(type_name))
        if iso and iso.group(2) == suffix:
            available.append((int(iso.group(1)), str(type_name)))
    if not available:
        return None
    # Nearest nominal width; on a tie prefer the larger DN (negative dn breaks ties up).
    return min(available, key=lambda dn_name: (abs(dn_name[0] - target_dn), -dn_name[0]))[1]


def resolve_pipe_u_w_per_m2k(properties) -> float:
    """
    Per-area heat-transfer coefficient [W/(m²·K)] for a pipe std-type row.

    :param properties: A pipe std-type row (pandas Series or dict) with at least
        ``outer_diameter_mm`` and one of ``u_w_per_m2k`` / ``u_w_per_mk``.
    :return: ``u_w_per_m2k``: the stored per-area value if present, otherwise the
        per-length ``u_w_per_mk`` converted via the outer surface.
    :rtype: float
    :raises ValueError: If neither a valid per-area nor per-length value is available.
    """
    u_area = properties.get("u_w_per_m2k") if hasattr(properties, "get") else properties["u_w_per_m2k"]
    if u_area is not None and np.isfinite(u_area):
        return float(u_area)

    u_len = properties.get("u_w_per_mk") if hasattr(properties, "get") else properties["u_w_per_mk"]
    outer_d_m = float(properties["outer_diameter_mm"]) / 1000.0
    if u_len is None or not np.isfinite(u_len) or outer_d_m <= 0:
        raise ValueError(
            "pipe std-type has neither a valid 'u_w_per_m2k' nor 'u_w_per_mk' "
            "(cannot determine the heat-transfer coefficient)."
        )
    # Match pandapipes: spread the per-length loss over the outer pipe surface.
    return float(u_len) / (math.pi * outer_d_m)
