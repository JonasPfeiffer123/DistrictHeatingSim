"""
Shared mapping between an energy-system config display name and its results JSON filename.

Used by both the EnergySystem tab (which reads *and writes* configs) and the Comparison tab
(which only reads them). Keeping the two directions here means they cannot drift apart — the
``filename_to_config_name`` half used to be duplicated verbatim, and only the EnergySystem tab
applied the filename sanitiser, so the two tabs could disagree on a config's display name.
"""

CONFIG_PREFIX = "Ergebnisse_"
CONFIG_SUFFIX = ".json"
DEFAULT_FILENAME = "Ergebnisse.json"
DEFAULT_CONFIG_NAME = "Standard"


def config_name_to_filename(config_name: str) -> str:
    """
    Map a display config name to its results JSON filename.

    Characters illegal in a filename (``/``, ``\\``, ``:``) are replaced with ``-``. This is
    **lossy** — a name containing ``/`` cannot be recovered exactly — but it is applied here so
    both tabs sanitise identically (a config "A/B" becomes "A-B" everywhere, not just on save).

    :param config_name: Display name (``"Standard"`` maps to the default filename).
    :return: The JSON filename.
    """
    if config_name == DEFAULT_CONFIG_NAME:
        return DEFAULT_FILENAME
    safe = config_name.replace("/", "-").replace("\\", "-").replace(":", "-")
    return f"{CONFIG_PREFIX}{safe}{CONFIG_SUFFIX}"


def filename_to_config_name(filename: str) -> str:
    """
    Map a results JSON filename back to its display config name.

    :param filename: The JSON filename (``"Ergebnisse.json"`` maps to ``"Standard"``).
    :return: The display name.
    """
    if filename == DEFAULT_FILENAME:
        return DEFAULT_CONFIG_NAME
    return filename[len(CONFIG_PREFIX) : -len(CONFIG_SUFFIX)]
