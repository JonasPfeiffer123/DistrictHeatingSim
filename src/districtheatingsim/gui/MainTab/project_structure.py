"""
GUI-free helpers for the on-disk district-heating project structure.
=====================================================================

Deliberately PyQt-free so the variant-folder naming + discovery logic can be
unit-tested without a Qt display, and reused by both the Model
(``ProjectFolderManager``) and the GUI tabs without import cycles.

A project directory contains one or more *variant* sub-folders ("Variante 1",
"Variante 2", …) alongside shared input folders; the variant is the unit the
user switches between.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os

#: Prefix shared by every variant folder. Used both to construct new variant
#: names and to detect existing variant folders, so the creation and detection
#: logic can never drift apart.
VARIANT_PREFIX = "Variante"

#: Name of the first analysis variant folder created in every new project.
DEFAULT_VARIANT_NAME = f"{VARIANT_PREFIX} 1"


def discover_variants(project_path: str) -> list[str]:
    """
    Return the sorted names of the variant sub-folders in ``project_path``.

    A variant folder is a directory whose name starts with :data:`VARIANT_PREFIX`.
    The result is sorted for deterministic ordering (so "activate the first
    variant" picks ``Variante 1`` rather than an arbitrary filesystem order).

    :param project_path: Path to the main project directory.
    :type project_path: str
    :return: Sorted variant folder names; empty list if the path does not exist.
    :rtype: list[str]
    """
    try:
        entries = os.listdir(project_path)
    except (FileNotFoundError, NotADirectoryError):
        return []
    return sorted(
        name for name in entries
        if name.startswith(VARIANT_PREFIX)
        and os.path.isdir(os.path.join(project_path, name))
    )
