"""
Versioned-JSON helpers for app-owned project artifacts (BACKLOG D4).
====================================================================

A single home for the "version + migrate" bookkeeping that D2 duplicated across
``project_settings.json`` and the EnergySystem JSON. New writes carry a ``_meta``
block holding the **schema version** (drives migration) and the **app version**
(diagnostics only). Reads tolerate three on-disk forms so older files keep loading:

* new:    ``{"_meta": {"schema_version": N, "app_version": "x.y.z"}, …}``
* legacy: ``{"version": N, …}``  — the D2 top-level field
* pre-versioning: neither present → schema version ``0``

Deliberately GUI-free and dependency-light (stdlib only) so the domain core
(``heat_generators``) can use it without dragging in PyQt6 (BACKLOG B5).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

logger = logging.getLogger(__name__)

#: Key under which the metadata block is stored in a serialized artifact.
META_KEY = "_meta"

#: Registry of every versioned artifact kind → its current schema version. Bump a
#: value here (and add a migration step in the artifact's loader) when its on-disk
#: format changes. This is the single source of truth that replaces the scattered
#: ``*_VERSION`` constants.
SCHEMA_VERSIONS: dict[str, int] = {
    "project_settings": 1,
    "energy_system": 1,
    "building_data": 1,
    "dialog_config": 1,
}


def _app_version() -> str:
    """Return the installed ``districtheatingsim`` version, or ``"unknown"``."""
    try:
        return _pkg_version("districtheatingsim")
    except PackageNotFoundError:
        return "unknown"


def current_version(kind: str) -> int:
    """Return the current schema version registered for ``kind``."""
    return SCHEMA_VERSIONS[kind]


def schema_version_of(raw: dict) -> int:
    """
    Extract the schema version from a loaded dict, tolerating all on-disk forms.

    :param raw: The dict as loaded from JSON.
    :return: ``_meta.schema_version`` if present, else the legacy top-level
        ``version``, else ``0`` (pre-versioning).
    :rtype: int
    """
    meta = raw.get(META_KEY)
    if isinstance(meta, dict) and "schema_version" in meta:
        return int(meta["schema_version"])
    if "version" in raw:
        return int(raw["version"])
    return 0


def add_meta(data: dict, kind: str) -> dict:
    """
    Return a copy of ``data`` stamped with a ``_meta`` block for ``kind``.

    Drops any legacy top-level ``version`` field so a re-saved file uses the new
    form exclusively.

    :param data: The payload to serialize.
    :param kind: A key registered in :data:`SCHEMA_VERSIONS`.
    :return: ``data`` plus a ``_meta`` block (schema + app version).
    :rtype: dict
    """
    out = dict(data)
    out.pop("version", None)
    out[META_KEY] = {
        "schema_version": SCHEMA_VERSIONS[kind],
        "app_version": _app_version(),
    }
    return out


def check_version(raw: dict, kind: str) -> int:
    """
    Read the schema version of a loaded artifact and warn if it is too new.

    A file written by a *newer* app may use a format this version cannot fully
    understand; we log a warning and let the caller load best-effort. (Migration
    of *older* files stays per-artifact, since the steps differ.)

    :param raw: The dict as loaded from JSON.
    :param kind: A key registered in :data:`SCHEMA_VERSIONS`.
    :return: The schema version found on disk (0 = pre-versioning).
    :rtype: int
    """
    found = schema_version_of(raw)
    current = SCHEMA_VERSIONS[kind]
    if found > current:
        logger.warning(
            "%s is schema v%d, newer than this app (v%d); loading best-effort",
            kind, found, current,
        )
    elif found < current:
        logger.info("Loading %s written with older schema v%d (current v%d)",
                    kind, found, current)
    return found
