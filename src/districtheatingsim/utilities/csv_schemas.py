"""
Column contracts for app-owned CSV files (BACKLOG D4 step 4).
=============================================================

CSV files here are user- and Excel-editable, so — unlike the JSON artifacts in
:mod:`districtheatingsim.utilities.schema` — the **column header is the contract**;
a version field would break pandas/Excel interop. Instead we centralize the
required columns per file *kind* and validate on load, turning a ``KeyError`` raised
deep inside the maths (``data["VLT_max"]`` …) into one clear message naming every
missing column up front. Generalizes the ad-hoc ``UTM_X``/``UTM_Y`` checks.

GUI-free and pandas-free at import (the DataFrame is duck-typed via ``.columns``).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

#: Required (and known-optional) columns per CSV kind. ``optional`` is documentation
#: only — it lists columns the readers use when present but tolerate when absent.
CSV_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    # The building / "Quartier" CSV consumed by the heat-demand profile calculation.
    "building": {
        "required": (
            "Wärmebedarf",
            "Gebäudetyp",
            "Subtyp",
            "WW_Anteil",
            "Normaußentemperatur",
            "VLT_max",
            "RLT_max",
            "Steigung_Heizkurve",
        ),
        "optional": ("Heizgrenztemperatur", "Heizexponent", "P_max"),
    },
    # Any layer that needs projected coordinates (e.g. building CSV → network layers).
    "coordinates": {
        "required": ("UTM_X", "UTM_Y"),
        "optional": (),
    },
}


def required_columns(kind: str) -> tuple[str, ...]:
    """Return the required column names for a CSV ``kind``."""
    return CSV_SCHEMAS[kind]["required"]


def validate_csv_columns(df, kind: str) -> None:
    """
    Raise ``KeyError`` if ``df`` is missing any required column for ``kind``.

    :param df: A loaded table (duck-typed: needs a ``.columns`` collection).
    :param kind: A key registered in :data:`CSV_SCHEMAS`.
    :raises KeyError: Naming every missing required column (and listing the present
        ones), so a renamed/missing header is a clear up-front error rather than an
        opaque failure deep in the calculation.
    """
    required = CSV_SCHEMAS[kind]["required"]
    columns = list(df.columns)
    missing = [c for c in required if c not in columns]
    if missing:
        raise KeyError(f"CSV is missing required column(s) for kind '{kind}': {missing}. Present columns: {columns}")
