"""
Declarative field schemas for the schema-driven technology dialogs.

Each list mirrors, field-for-field and default-for-default, the original
hand-written dialog in ``_04_technology_dialogs.py`` (pre-refactor). Two legacy
quirks are reproduced on purpose and pinned by ``tests/test_technology_dialogs.py``
(see BACKLOG): the capacity read/write key asymmetry (``in_key``) and the CHP
storage-cost default of ``"0.8"`` (Biomass uses ``"750"``).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from typing import List

from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import Field, CheckField


# ── Simple dialogs ────────────────────────────────────────────────────────────

GAS_BOILER: List = [
    # Quirk: initial value read from 'th_Leistung_kW', emitted as 'thermal_capacity_kW'.
    Field("thermal_capacity_kW", "Thermische Leistung Gaskessel in kW", "1000", in_key="th_Leistung_kW"),
    Field("Nutzungsgrad", "Nutzungsgrad Gaskessel", "0.9"),
    Field("spez_Investitionskosten", "spez. Investitionskosten in €/kW", "30"),
]

POWER_TO_HEAT: List = [
    Field("thermal_capacity_kW", "Thermische Leistung Power-To-Heat in kW", "1000", in_key="th_Leistung_kW"),
    Field("Nutzungsgrad", "Nutzungsgrad Power-to-Heat", "0.9"),
    Field("spez_Investitionskosten", "spez. Investitionskosten in €/kW", "30"),
]

WASTE_HEAT_PUMP: List = [
    Field("Kühlleistung_Abwärme", "Kühlleistung Abwärme in kW", "30"),
    Field("Temperatur_Abwärme", "Temperatur Abwärme in °C", "30"),
    Field("spez_Investitionskosten_Abwärme", "spez. Investitionskosten Abwärmenutzung in €/kW", "500"),
    Field("spezifische_Investitionskosten_WP", "spez. Investitionskosten Wärmepumpe", "1000"),
]


# ── Shared storage block (Biomass / CHP / HolzgasCHP) ─────────────────────────

def storage_fields(volume_key: str, opt_min_key: str, opt_max_key: str,
                   spez_cost_default: str) -> List[Field]:
    """Return the 9-field generator buffer-storage block.

    Six fields are identical across the three combustion dialogs; the volume key,
    the two optimization-bound keys, and the specific-cost default differ and are
    passed in.
    """
    return [
        Field(volume_key, "Speicher Volumen", "20"),
        Field("T_vorlauf", "Vorlauftemperatur", "90"),
        Field("T_ruecklauf", "Rücklauftemperatur", "60"),
        Field("initial_fill", "initiale Füllung", "0.0"),
        Field("min_fill", "minimale Füllung", "0.2"),
        Field("max_fill", "maximale Füllung", "0.8"),
        Field("spez_Investitionskosten_Speicher", "spez. Investitionskosten Speicher in €/m³", spez_cost_default),
        Field(opt_min_key, "Untere Grenze Speichervolumen Optimierung", "0"),
        Field(opt_max_key, "Obere Grenze Speichervolumen Optimierung", "100"),
    ]


# ── Combustion dialogs (main field block) ─────────────────────────────────────

BIOMASS_MAIN: List = [
    # Quirk: initial value read from 'P_BMK', emitted as 'thermal_capacity_kW'.
    Field("thermal_capacity_kW", "th. Leistung in kW", "240", in_key="P_BMK"),
    Field("Größe_Holzlager", "Größe Holzlager in t", "40"),
    Field("spez_Investitionskosten", "spez. Investitionskosten Kessel in €/kW", "200"),
    Field("spez_Investitionskosten_Holzlager", "spez. Investitionskosten Holzlager in €/t", "400"),
    Field("Nutzungsgrad_BMK", "Nutzungsgrad Biomassekessel", "0.8"),
    Field("min_Teillast", "minimale Teillast", "0.3"),
    Field("opt_BMK_min", "Untere Grenze th. Leistung Optimierung", "0"),
    Field("opt_BMK_max", "Obere Grenze th. Leistung Optimierung", "5000"),
    CheckField("speicher_aktiv", "Speicher aktiv"),
]
BIOMASS_STORAGE = storage_fields("Speicher_Volumen", "opt_Speicher_min", "opt_Speicher_max", "750")

CHP_MAIN: List = [
    Field("th_Leistung_kW", "thermische Leistung", "100"),
    Field("el_Wirkungsgrad", "elektrischer Wirkungsgrad BHKW", "0.33"),
    Field("KWK_Wirkungsgrad", "KWK Wirkungsgrad", "0.9"),
    Field("min_Teillast", "minimale Teillast", "0.7"),
    Field("spez_Investitionskosten_GBHKW", "spez. Investitionskosten BHKW", "1500"),
    Field("opt_BHKW_min", "Untere Grenze th. Leistung Optimierung", "0"),
    Field("opt_BHKW_max", "Obere Grenze th. Leistung Optimierung", "1000"),
    CheckField("speicher_aktiv", "Speicher aktiv"),
]

HOLZGAS_CHP_MAIN: List = [
    Field("th_Leistung_kW", "thermische Leistung", "100"),
    Field("el_Wirkungsgrad", "elektrischer Wirkungsgrad BHKW", "0.33"),
    Field("KWK_Wirkungsgrad", "KWK Wirkungsgrad", "0.9"),
    Field("min_Teillast", "minimale Teillast", "0.7"),
    Field("spez_Investitionskosten_HBHKW", "spez. Investitionskosten BHKW", "1850"),
    Field("opt_BHKW_min", "Untere Grenze th. Leistung Optimierung", "0"),
    Field("opt_BHKW_max", "Obere Grenze th. Leistung Optimierung", "1000"),
    CheckField("speicher_aktiv", "Speicher aktiv"),
]
# CHP and HolzgasCHP share the same storage block (note the legacy 0.8 default).
CHP_STORAGE = storage_fields("Speicher_Volumen_BHKW", "opt_BHKW_Speicher_min", "opt_BHKW_Speicher_max", "0.8")
