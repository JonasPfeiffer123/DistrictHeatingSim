"""
Declarative field schemas for the schema-driven technology dialogs.

Each list mirrors, field-for-field and default-for-default, the original
hand-written dialog in ``_04_technology_dialogs.py`` (pre-refactor). Two legacy
quirks are reproduced on purpose and pinned by ``tests/test_technology_dialogs.py``
(see BACKLOG): the capacity read/write key asymmetry (``in_key``) and the CHP
storage-cost default of ``"0.8"`` (Biomass uses ``"750"``).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""


from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import (
    CheckField,
    ComboField,
    Field,
    Section,
)

# ── Simple dialogs ────────────────────────────────────────────────────────────

GAS_BOILER: list = [
    Field("thermal_capacity_kW", "Thermische Leistung Gaskessel in kW", "1000"),
    Field("Nutzungsgrad", "Nutzungsgrad Gaskessel", "0.9"),
    Field("spez_Investitionskosten", "spez. Investitionskosten in €/kW", "30"),
]

POWER_TO_HEAT: list = [
    Field("thermal_capacity_kW", "Thermische Leistung Power-To-Heat in kW", "1000"),
    Field("Nutzungsgrad", "Nutzungsgrad Power-to-Heat", "0.9"),
    Field("spez_Investitionskosten", "spez. Investitionskosten in €/kW", "30"),
]

WASTE_HEAT_PUMP: list = [
    Field("Kühlleistung_Abwärme", "Kühlleistung Abwärme in kW", "30"),
    Field("Temperatur_Abwärme", "Temperatur Abwärme in °C", "30"),
    Field("spez_Investitionskosten_Abwärme", "spez. Investitionskosten Abwärmenutzung in €/kW", "500"),
    Field("spezifische_Investitionskosten_WP", "spez. Investitionskosten Wärmepumpe", "1000"),
]


# ── Shared storage block (Biomass / CHP / HolzgasCHP) ─────────────────────────

def storage_fields(volume_key: str, opt_min_key: str, opt_max_key: str,
                   spez_cost_default: str) -> list[Field]:
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

BIOMASS_MAIN: list = [
    Field("thermal_capacity_kW", "th. Leistung in kW", "240"),
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

CHP_MAIN: list = [
    Field("th_Leistung_kW", "thermische Leistung", "100"),
    Field("el_Wirkungsgrad", "elektrischer Wirkungsgrad BHKW", "0.33"),
    Field("KWK_Wirkungsgrad", "KWK Wirkungsgrad", "0.9"),
    Field("min_Teillast", "minimale Teillast", "0.7"),
    Field("spez_Investitionskosten_GBHKW", "spez. Investitionskosten BHKW", "1500"),
    Field("opt_BHKW_min", "Untere Grenze th. Leistung Optimierung", "0"),
    Field("opt_BHKW_max", "Obere Grenze th. Leistung Optimierung", "1000"),
    CheckField("speicher_aktiv", "Speicher aktiv"),
]

HOLZGAS_CHP_MAIN: list = [
    Field("th_Leistung_kW", "thermische Leistung", "100"),
    Field("el_Wirkungsgrad", "elektrischer Wirkungsgrad BHKW", "0.33"),
    Field("KWK_Wirkungsgrad", "KWK Wirkungsgrad", "0.9"),
    Field("min_Teillast", "minimale Teillast", "0.7"),
    Field("spez_Investitionskosten_HBHKW", "spez. Investitionskosten BHKW", "1850"),
    Field("opt_BHKW_min", "Untere Grenze th. Leistung Optimierung", "0"),
    Field("opt_BHKW_max", "Obere Grenze th. Leistung Optimierung", "1000"),
    CheckField("speicher_aktiv", "Speicher aktiv"),
]
# CHP and HolzgasCHP share the same storage block.
CHP_STORAGE = storage_fields("Speicher_Volumen_BHKW", "opt_BHKW_Speicher_min", "opt_BHKW_Speicher_max", "750")


# ── Heat pumps ────────────────────────────────────────────────────────────────

# River heat pump: the four plain fields. The 'Temperatur_FW_WP' field (CSV import
# / scalar / ndarray) is handled by RiverHeatPumpDialog's getInputs override.
RIVER: list = [
    Field("Wärmeleistung_FW_WP", "th. Leistung Wärmepumpe in kW", "200"),
    Field("dT", "Zulässige Abweichung Vorlauftemperatur Wärmepumpe von Netzvorlauftemperatur", "0"),
    Field("spez_Investitionskosten_Flusswasser", "spez. Investitionskosten Flusswärmenutzung", "1000"),
    Field("spezifische_Investitionskosten_WP", "spez. Investitionskosten Wärmepumpe", "1000"),
]


# ── Geothermal ────────────────────────────────────────────────────────────────

GEOTHERMAL: list = [
    Field("Fläche", "Fläche Erdsondenfeld in m²", "100"),
    Field("Bohrtiefe", "Bohrtiefe Sonden in m", "100"),
    Field("Temperatur_Geothermie", "Quelltemperatur in °C", "10"),
    Field("Abstand_Sonden", "Abstand Erdsonden in m", "10"),
    Field("spez_Bohrkosten", "spez. Bohrkosten pro Bohrmeter in €/m", "120"),
    Field("spez_Entzugsleistung", "spez. Entzugsleistung Untergrund in W/m", "50"),
    Field("Vollbenutzungsstunden", "Vollbenutzungsstunden Sondenfeld in h", "2400"),
    Field("spezifische_Investitionskosten_WP", "spez. Investitionskosten Wärmepumpe in €/kW", "1000"),
]


# ── Solar thermal ─────────────────────────────────────────────────────────────
# Grouped into the same three group boxes as the original dialog.

SOLAR_SECTIONS: list[Section] = [
    Section("Technische Daten", [
        Field("bruttofläche_STA", "Kollektorbruttofläche in m²", "200"),
        Field("vs", "Solarspeichervolumen in m³", "20"),
        ComboField("Typ", "Kollektortyp", ["Vakuumröhrenkollektor", "Flachkollektor"], "Vakuumröhrenkollektor"),
        Field("Tsmax", "Maximale Speichertemperatur in °C", "90"),
        Field("Longitude", "Longitude des Erzeugerstandortes", "-14.4222"),
        Field("STD_Longitude", "STD_Longitude des Erzeugerstandortes", "15", cast=int),
        Field("Latitude", "Latitude des Erzeugerstandortes", "51.1676"),
        Field("East_West_collector_azimuth_angle", "Azimuth-Ausrichtung des Kollektors in °", "0"),
        Field("Collector_tilt_angle", "Neigungswinkel des Kollektors in ° (0-90)", "36"),
        Field("Tm_rl", "Startwert Rücklauftemperatur in Speicher in °C", "60"),
        Field("Qsa", "Startwert Speicherfüllstand", "0"),
        Field("Vorwärmung_K", "Mögliche Abweichung von Solltemperatur bei Vorwärmung", "8"),
        Field("DT_WT_Solar_K", "Grädigkeit Wärmeübertrager Kollektor/Speicher", "5"),
        Field("DT_WT_Netz_K", "Grädigkeit Wärmeübertrager Speicher/Netz", "5"),
    ]),
    Section("Kosten", [
        Field("kosten_speicher_spez", "spez. Kosten Solarspeicher in €/m³", "750"),
        Field("kosten_fk_spez", "spez. Kosten Flachkollektor in €/m²", "430"),
        Field("kosten_vrk_spez", "spez. Kosten Vakuumröhrenkollektor in €/m²", "590"),
    ]),
    Section("Optimierungsparameter", [
        Field("opt_volume_min", "Untere Grenze Speichervolumen Optimierung", "1"),
        Field("opt_volume_max", "Obere Grenze Speichervolumen Optimierung", "200"),
        Field("opt_area_min", "Untere Grenze Kollektorfläche Optimierung", "1"),
        Field("opt_area_max", "Obere Grenze Kollektorfläche Optimierung", "2000"),
    ]),
]
