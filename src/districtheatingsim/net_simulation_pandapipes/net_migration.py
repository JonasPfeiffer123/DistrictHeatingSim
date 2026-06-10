"""
Migrate pandapipes nets loaded from older saves to the current schema.
=====================================================================

Projects saved on pandapipes 0.13 pickle a pipe table that uses the old ``KMR …``
std-types and the removed ``diameter_m`` column. Loaded into 0.14 those nets crash
in ``pipeflow`` (``'DataFrame' object has no attribute 'inner_diameter_mm'``) and the
GUI still shows the obsolete KMR names. ``migrate_loaded_net`` upgrades such a net in
place so old projects open and recalculate.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging

import pandapipes as pp

from districtheatingsim.net_simulation_pandapipes.pipe_std_types import (
    kmr_to_isoplus_std_type,
    resolve_pipe_u_w_per_m2k,
)

logger = logging.getLogger(__name__)


def migrate_loaded_net(net):
    """
    Migrate a freshly loaded pandapipes net to the current (0.14) schema, in place.

    - Re-anchor legacy ``KMR …`` pipe std-types to their ISOPLUS successors, taking
      the diameter and heat-loss from the current catalog (the user's KMR pipes are
      anchored as ISOPLUS in pandapipes 0.14).
    - Ensure the pipe table has the 0.14 ``inner_diameter_mm`` column, deriving it
      from the legacy ``diameter_m`` [m] for any pipe not covered by the remap.

    :param net: The loaded pandapipes network.
    :return: The same network, migrated.
    """
    if not hasattr(net, "pipe") or len(net.pipe) == 0:
        return net

    try:
        catalog = pp.std_types.available_std_types(net, "pipe")
    except Exception:  # pragma: no cover - defensive
        catalog = None

    # Derive the new per-pipe diameter column from the old one where it is missing.
    if "inner_diameter_mm" not in net.pipe.columns and "diameter_m" in net.pipe.columns:
        net.pipe["inner_diameter_mm"] = net.pipe["diameter_m"] * 1000.0

    remapped = 0
    if "std_type" in net.pipe.columns and catalog is not None:
        for idx in net.pipe.index:
            isoplus = kmr_to_isoplus_std_type(net.pipe.at[idx, "std_type"])
            if isoplus is None or isoplus not in catalog.index:
                continue
            props = catalog.loc[isoplus]
            net.pipe.at[idx, "std_type"] = isoplus
            net.pipe.at[idx, "inner_diameter_mm"] = props["inner_diameter_mm"]
            if "outer_diameter_mm" in net.pipe.columns:
                net.pipe.at[idx, "outer_diameter_mm"] = props["outer_diameter_mm"]
            net.pipe.at[idx, "u_w_per_m2k"] = resolve_pipe_u_w_per_m2k(props)
            remapped += 1

    if remapped:
        logger.info("Migrated %d KMR pipe(s) to ISOPLUS std-types", remapped)

    return net
