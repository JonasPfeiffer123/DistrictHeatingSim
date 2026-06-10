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
# successors "ISOPLUS_DRE<DN>_<insulation>x" in pandapipes >= 0.14.
_KMR_PATTERN = re.compile(r"^KMR\s+(\d+)/\d+-(\d+)v$")


def kmr_to_isoplus_std_type(name) -> str | None:
    """
    Map a legacy ``KMR …`` pipe std-type name to its ISOPLUS equivalent.

    ``KMR 100/250-2v`` → ``ISOPLUS_DRE100_2x``. Returns ``None`` for names that are
    not legacy KMR types (e.g. already-ISOPLUS names), so callers can skip them.

    :param name: A pipe std-type name.
    :return: The ISOPLUS name, or ``None`` if ``name`` is not a KMR type.
    :rtype: str | None
    """
    match = _KMR_PATTERN.match(str(name))
    if not match:
        return None
    nominal_width, insulation = match.group(1), match.group(2)
    return f"ISOPLUS_DRE{nominal_width}_{insulation}x"


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
