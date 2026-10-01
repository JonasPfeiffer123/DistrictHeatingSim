"""
Shared mapping between an energy-system config display name and its results file.

Used by both the EnergySystem tab (which reads *and writes* configs) and the Comparison tab
(which only reads them). Keeping the naming and the discovery here means they cannot drift
apart — both used to be duplicated in the two tabs.

Results are written as Parquet array stores (``Ergebnisse.parquet`` / ``Ergebnisse_<name>.parquet``,
BACKLOG G7); ``.json`` files of projects saved earlier are still recognised. If a config exists in
both formats, the newer file is used (an older app version may have re-saved the JSON).
"""

import os

CONFIG_PREFIX = "Ergebnisse_"
CONFIG_SUFFIX = ".parquet"
LEGACY_SUFFIX = ".json"
DEFAULT_STEM = "Ergebnisse"
DEFAULT_FILENAME = DEFAULT_STEM + CONFIG_SUFFIX
LEGACY_DEFAULT_FILENAME = DEFAULT_STEM + LEGACY_SUFFIX
DEFAULT_CONFIG_NAME = "Standard"

_SUFFIXES = (CONFIG_SUFFIX, LEGACY_SUFFIX)


def config_name_to_filename(config_name: str) -> str:
    """
    Map a display config name to the filename it is saved under (current format).

    Characters illegal in a filename (``/``, ``\\``, ``:``) are replaced with ``-``. This is
    **lossy** — a name containing ``/`` cannot be recovered exactly — but it is applied here so
    both tabs sanitise identically (a config "A/B" becomes "A-B" everywhere, not just on save).

    :param config_name: Display name (``"Standard"`` maps to the default filename).
    :return: The results filename.
    """
    if config_name == DEFAULT_CONFIG_NAME:
        return DEFAULT_FILENAME
    safe = config_name.replace("/", "-").replace("\\", "-").replace(":", "-")
    return f"{CONFIG_PREFIX}{safe}{CONFIG_SUFFIX}"


def filename_to_config_name(filename: str) -> str | None:
    """
    Map a results filename (current or legacy format) back to its display config name.

    :param filename: The results filename (``"Ergebnisse.parquet"`` / ``".json"`` → ``"Standard"``).
    :return: The display name, or ``None`` if the file is not an energy-system config.
    """
    for suffix in _SUFFIXES:
        if not filename.endswith(suffix):
            continue
        stem = filename[: -len(suffix)]
        if stem == DEFAULT_STEM:
            return DEFAULT_CONFIG_NAME
        if stem.startswith(CONFIG_PREFIX) and len(stem) > len(CONFIG_PREFIX):
            return stem[len(CONFIG_PREFIX) :]
    return None


def discover_configs(ergebnisse_dir: str) -> list[tuple[str, str]]:
    """
    All energy-system configs in a results folder as ``(config_name, filename)``.

    ``Standard`` comes first, the others in filename order. A config present in both formats is
    listed once, with the newer file.

    :param ergebnisse_dir: The variant's ``Ergebnisse`` folder.
    :return: ``(config_name, filename)`` pairs (empty if the folder does not exist).
    :rtype: list[tuple[str, str]]
    """
    if not os.path.isdir(ergebnisse_dir):
        return []
    chosen: dict[str, str] = {}
    for filename in sorted(os.listdir(ergebnisse_dir)):
        name = filename_to_config_name(filename)
        if name is None:
            continue
        previous = chosen.get(name)
        if previous is None or os.path.getmtime(os.path.join(ergebnisse_dir, filename)) > os.path.getmtime(
            os.path.join(ergebnisse_dir, previous)
        ):
            chosen[name] = filename
    ordered = sorted(chosen.items(), key=lambda item: (item[0] != DEFAULT_CONFIG_NAME, item[1]))
    return [(name, filename) for name, filename in ordered]


def config_file(ergebnisse_dir: str, config_name: str) -> str | None:
    """
    Path of the file to load for ``config_name`` (the newer format if both exist), or ``None``.

    :param ergebnisse_dir: The variant's ``Ergebnisse`` folder.
    :param config_name: Display name.
    """
    for name, filename in discover_configs(ergebnisse_dir):
        if name == config_name:
            return os.path.join(ergebnisse_dir, filename)
    return None


def config_files(ergebnisse_dir: str, config_name: str) -> list[str]:
    """
    Every existing file of ``config_name`` in any format (e.g. to delete a config completely).

    :param ergebnisse_dir: The variant's ``Ergebnisse`` folder.
    :param config_name: Display name.
    """
    stem = config_name_to_filename(config_name)[: -len(CONFIG_SUFFIX)]
    candidates = [os.path.join(ergebnisse_dir, stem + suffix) for suffix in _SUFFIXES]
    return [path for path in candidates if os.path.exists(path)]
