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

#: Project-level folders created next to the variant folders.
PROJECT_INPUT_FOLDERS = ("Eingangsdaten allgemein", "Definition Quartier IST")

#: Standard sub-folders inside every variant folder.
VARIANT_SUBDIRS = ("Ergebnisse", "Gebäudedaten", "Lastgang", "Wärmenetz")


def create_variant_structure(variant_path: str) -> None:
    """
    Create a variant folder and its standard sub-folders (:data:`VARIANT_SUBDIRS`).

    :param variant_path: Absolute path of the variant folder to create.
    """
    os.makedirs(variant_path, exist_ok=True)
    for sub in VARIANT_SUBDIRS:
        os.makedirs(os.path.join(variant_path, sub), exist_ok=True)


def create_project_structure(project_path: str) -> None:
    """
    Create a new project folder with the standard district-heating structure.

    Lays out :data:`PROJECT_INPUT_FOLDERS` plus the default variant
    (:data:`DEFAULT_VARIANT_NAME`) with its sub-folders.

    :param project_path: Absolute path of the project folder to create.
    :raises FileExistsError: If ``project_path`` already exists — callers rely on
        this to refuse overwriting an existing project.
    """
    os.makedirs(project_path)  # no exist_ok: fail loudly on an existing project
    for folder in PROJECT_INPUT_FOLDERS:
        os.makedirs(os.path.join(project_path, folder))
    create_variant_structure(os.path.join(project_path, DEFAULT_VARIANT_NAME))


def resolve_new_project_start_dir(recent_projects: list[str]) -> str:
    """
    Pick a sensible starting directory for the "new project parent folder" dialog.

    Prefers the parent directory of the most recently opened project, falling back
    to ``~/Documents`` (if it exists) and finally the user's home directory. Pure
    path logic so the fallback chain can be unit-tested without a file dialog.

    :param recent_projects: Recently opened project paths, most recent first
        (as returned by ``config_manager.get_recent_projects()``); may be empty.
    :return: An existing-or-home directory to open the folder picker at.
    :rtype: str
    """
    if recent_projects:
        parent = os.path.dirname(recent_projects[0])
        if parent:
            return parent
    documents = os.path.expanduser("~/Documents")
    if os.path.exists(documents):
        return documents
    return os.path.expanduser("~")


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
        name for name in entries if name.startswith(VARIANT_PREFIX) and os.path.isdir(os.path.join(project_path, name))
    )
