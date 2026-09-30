"""
Save and load a project's pandapipes network.
=============================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

The network used to be stored with ``pp.to_pickle``. Pickles are tied to the library versions
that wrote them (cf. the 0.13 → 0.14 migration, BACKLOG C11) and unpickling a file from someone
else's project can execute arbitrary code. It is now stored as pandapipes JSON (``pp.to_json``),
which is also about half the size. Old projects still load from their pickle (BACKLOG G7).

pandas' JSON writer rounds floats to ~15 significant digits, so a reloaded net differs from the
in-memory one by rounding noise (measured on Görlitz: pipe lengths ≤ 5e-16 km, simulation results
≤ 3e-13 K / 5e-15 bar); controllers — including the project's own classes — round-trip.
"""

import logging
import os

import pandapipes as pp

logger = logging.getLogger(__name__)


def save_net(net, json_path: str) -> None:
    """
    Write the network as pandapipes JSON.

    :param net: Network to save
    :type net: pandapipes.pandapipesNet
    :param json_path: Target file
    :type json_path: str
    """
    pp.to_json(net, json_path)


def load_net(json_path: str, legacy_pickle_path: str | None = None):
    """
    Load the network from its JSON file, falling back to the legacy pickle of older projects.

    If both exist, the newer one wins — an older app version may have saved the project again
    (pickle only) after this one wrote the JSON.

    :param json_path: Current-format file
    :type json_path: str
    :param legacy_pickle_path: Pickle written by earlier versions
    :type legacy_pickle_path: str or None
    :return: The loaded network and the file it was read from
    :rtype: tuple[pandapipes.pandapipesNet, str]
    :raises FileNotFoundError: If neither file exists
    """
    has_json = os.path.exists(json_path)
    has_pickle = bool(legacy_pickle_path) and os.path.exists(legacy_pickle_path)
    if has_pickle and (not has_json or os.path.getmtime(legacy_pickle_path) > os.path.getmtime(json_path)):
        logger.info("Loading network from legacy pickle %s (saved as JSON on the next save)", legacy_pickle_path)
        return pp.from_pickle(legacy_pickle_path), legacy_pickle_path
    if has_json:
        return pp.from_json(json_path), json_path
    raise FileNotFoundError(f"Kein gespeichertes Netz gefunden: {json_path}")
