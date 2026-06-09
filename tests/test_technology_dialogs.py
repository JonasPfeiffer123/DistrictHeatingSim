"""
Characterization tests for the technology-input dialogs (GUI layer).

These pin the *current* behaviour of ``TechInputDialog`` and its 11 sub-dialogs —
dispatch by tech-type prefix, the default ``getInputs()`` dict for each, the
storage-section toggle on the combustion dialogs, and two latent quirks — so that
the B1 refactor (extracting a schema-based dialog package) can be proven
behaviour-preserving: this exact file must keep passing before and after the move.

Headless Qt: the session-scoped ``qapp`` fixture (conftest.py) plus
``QT_QPA_PLATFORM=offscreen`` let the widgets build without a display.

NOTE: some pinned values reproduce *bugs* on purpose (see ``TestKeyAsymmetry`` and
the CHP storage-cost default of 0.8 vs Biomass's 750 — BACKLOG). When those are
fixed, update the corresponding assertions in the same commit.
"""

import pytest

from districtheatingsim.gui.EnergySystemTab._04_technology_dialogs import (
    TechInputDialog,
    GasBoilerDialog,
    BiomassBoilerDialog,
    SolarThermalDialog,
    GeothermalDialog,
)

# Use the qapp fixture for the whole module (every test needs a QApplication).
pytestmark = pytest.mark.usefixtures("qapp")


def _inputs(tech_type, tech_data=None):
    """Build the dialog and return getInputs(), keeping the wrapper alive.

    The dialog must stay referenced by a local while getInputs() runs: otherwise
    Python drops the temporary TechInputDialog, Qt deletes its child QLineEdits,
    and getInputs() hits "wrapped C/C++ object ... has been deleted".
    """
    dialog = TechInputDialog(tech_type, tech_data)
    return dialog.dialog.getInputs()


def _dialog_class(tech_type):
    """Return the sub-dialog class name for a tech-type, keeping it alive."""
    dialog = TechInputDialog(tech_type)
    return type(dialog.dialog).__name__


# ---------------------------------------------------------------------------
# Expected default getInputs() dicts, captured from the current implementation.
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "Gaskessel": (
        "GasBoilerDialog",
        {"thermal_capacity_kW": 1000.0, "spez_Investitionskosten": 30.0, "Nutzungsgrad": 0.9},
    ),
    "Power-to-Heat": (
        "PowerToHeatDialog",
        {"thermal_capacity_kW": 1000.0, "spez_Investitionskosten": 30.0, "Nutzungsgrad": 0.9},
    ),
    "Abwärmepumpe": (
        "WasteHeatPumpDialog",
        {
            "Kühlleistung_Abwärme": 30.0,
            "Temperatur_Abwärme": 30.0,
            "spez_Investitionskosten_Abwärme": 500.0,
            "spezifische_Investitionskosten_WP": 1000.0,
        },
    ),
    "Biomassekessel": (
        "BiomassBoilerDialog",
        {
            "thermal_capacity_kW": 240.0,
            "Größe_Holzlager": 40.0,
            "spez_Investitionskosten": 200.0,
            "spez_Investitionskosten_Holzlager": 400.0,
            "Nutzungsgrad_BMK": 0.8,
            "min_Teillast": 0.3,
            "speicher_aktiv": False,
            "opt_BMK_min": 0.0,
            "opt_BMK_max": 5000.0,
        },
    ),
    "BHKW": (
        "CHPDialog",
        {
            "th_Leistung_kW": 100.0,
            "el_Wirkungsgrad": 0.33,
            "spez_Investitionskosten_GBHKW": 1500.0,
            "KWK_Wirkungsgrad": 0.9,
            "min_Teillast": 0.7,
            "speicher_aktiv": False,
            "opt_BHKW_min": 0.0,
            "opt_BHKW_max": 1000.0,
        },
    ),
    "Holzgas-BHKW": (
        "HolzgasCHPDialog",
        {
            "th_Leistung_kW": 100.0,
            "el_Wirkungsgrad": 0.33,
            "spez_Investitionskosten_HBHKW": 1850.0,
            "KWK_Wirkungsgrad": 0.9,
            "min_Teillast": 0.7,
            "speicher_aktiv": False,
            "opt_BHKW_min": 0.0,
            "opt_BHKW_max": 1000.0,
        },
    ),
    "Solarthermie": (
        "SolarThermalDialog",
        {
            "bruttofläche_STA": 200.0,
            "vs": 20.0,
            "Typ": "Vakuumröhrenkollektor",
            "Tsmax": 90.0,
            "Longitude": -14.4222,
            "STD_Longitude": 15,
            "Latitude": 51.1676,
            "East_West_collector_azimuth_angle": 0.0,
            "Collector_tilt_angle": 36.0,
            "Tm_rl": 60.0,
            "Qsa": 0.0,
            "Vorwärmung_K": 8.0,
            "DT_WT_Solar_K": 5.0,
            "DT_WT_Netz_K": 5.0,
            "kosten_speicher_spez": 750.0,
            "kosten_fk_spez": 430.0,
            "kosten_vrk_spez": 590.0,
            "opt_volume_min": 1.0,
            "opt_volume_max": 200.0,
            "opt_area_min": 1.0,
            "opt_area_max": 2000.0,
        },
    ),
    "Geothermie": (
        "GeothermalDialog",
        {
            "Fläche": 100.0,
            "Bohrtiefe": 100.0,
            "Temperatur_Geothermie": 10.0,
            "Abstand_Sonden": 10.0,
            "spez_Bohrkosten": 120.0,
            "spez_Entzugsleistung": 50.0,
            "Vollbenutzungsstunden": 2400.0,
            "spezifische_Investitionskosten_WP": 1000.0,
        },
    ),
    "Flusswärmepumpe": (
        "RiverHeatPumpDialog",
        {
            "Wärmeleistung_FW_WP": 200.0,
            "dT": 0.0,
            "spez_Investitionskosten_Flusswasser": 1000.0,
            "spezifische_Investitionskosten_WP": 1000.0,
            "Temperatur_FW_WP": 10.0,
        },
    ),
    "AqvaHeat": ("AqvaHeatDialog", {}),
    "Thermischer Netzspeicher": (
        "ThermalStorage1DDialog",
        {
            "volume": 1000.0,
            "height": 10.0,
            "geometry_type": "cylinder",
            "n_nodes": 50,
            "T_min": 40.0,
            "T_max": 95.0,
            "initial_temp": 60.0,
            "loss_model_type": "constant",
            "U_loss": 0.3,
            "U_top": 0.3,
            "U_side": 0.06,
            "U_bottom": 0.4,
            "T_ambient": 10.0,
            "z_ground": 2.0,
            "fluid_type": "water",
            "rho": 977.8,
            "cp": 4187.0,
            "lambda_fluid": 0.663,
            "solver": "implicit",
            "advection_scheme": "tvd",
            "buoyancy": True,
            "lambda_eff_factor": 5.0,
            "spez_Investitionskosten": 50.0,
            "hours": 8760,
            "T_charge": 90.0,
            "T_discharge_return": 50.0,
        },
    ),
}


class TestDispatch:
    """TechInputDialog routes each tech-type prefix to the right sub-dialog."""

    @pytest.mark.parametrize("tech_type", list(_DEFAULTS))
    def test_dispatch_class(self, tech_type):
        assert _dialog_class(tech_type) == _DEFAULTS[tech_type][0]

    @pytest.mark.parametrize("tech_type", list(_DEFAULTS))
    def test_dispatch_with_suffix(self, tech_type):
        # Real tech names carry a numeric suffix, e.g. "Gaskessel_1"; dispatch is
        # by startswith() so the suffixed name must route identically.
        assert _dialog_class(f"{tech_type}_1") == _DEFAULTS[tech_type][0]

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            TechInputDialog("Kernfusion")


class TestGetInputsDefaults:
    """Default getInputs() dict is frozen for every dialog."""

    @pytest.mark.parametrize("tech_type", list(_DEFAULTS))
    def test_defaults(self, tech_type):
        assert _inputs(tech_type) == _DEFAULTS[tech_type][1]


# Storage section keys added when speicher_aktiv is checked (combustion dialogs).
_STORAGE_ACTIVE = {
    "Biomassekessel": {
        "Speicher_Volumen": 20.0,
        "T_vorlauf": 90.0,
        "T_ruecklauf": 60.0,
        "initial_fill": 0.0,
        "min_fill": 0.2,
        "max_fill": 0.8,
        "spez_Investitionskosten_Speicher": 750.0,
        "opt_Speicher_min": 0.0,
        "opt_Speicher_max": 100.0,
    },
    "BHKW": {
        "Speicher_Volumen_BHKW": 20.0,
        "T_vorlauf": 90.0,
        "T_ruecklauf": 60.0,
        "initial_fill": 0.0,
        "min_fill": 0.2,
        "max_fill": 0.8,
        # Quirk: CHP default is 0.8 (Biomass is 750) — preserved verbatim.
        "spez_Investitionskosten_Speicher": 0.8,
        "opt_BHKW_Speicher_min": 0.0,
        "opt_BHKW_Speicher_max": 100.0,
    },
    "Holzgas-BHKW": {
        "Speicher_Volumen_BHKW": 20.0,
        "T_vorlauf": 90.0,
        "T_ruecklauf": 60.0,
        "initial_fill": 0.0,
        "min_fill": 0.2,
        "max_fill": 0.8,
        "spez_Investitionskosten_Speicher": 0.8,
        "opt_BHKW_Speicher_min": 0.0,
        "opt_BHKW_Speicher_max": 100.0,
    },
}


class TestStorageToggle:
    """The combustion dialogs add a storage block only when speicher_aktiv=True."""

    @pytest.mark.parametrize("tech_type", list(_STORAGE_ACTIVE))
    def test_storage_keys_absent_by_default(self, tech_type):
        out = _inputs(tech_type)
        assert out["speicher_aktiv"] is False
        for key in _STORAGE_ACTIVE[tech_type]:
            assert key not in out

    @pytest.mark.parametrize("tech_type", list(_STORAGE_ACTIVE))
    def test_storage_keys_present_when_active(self, tech_type):
        out = _inputs(tech_type, {"speicher_aktiv": True})
        assert out["speicher_aktiv"] is True
        for key, val in _STORAGE_ACTIVE[tech_type].items():
            assert out[key] == val


class TestKeyAsymmetry:
    """BACKLOG: capacity field reads one key but writes another.

    GasBoiler / BiomassBoiler read the QLineEdit default from ``th_Leistung_kW`` /
    ``P_BMK`` but emit it under ``thermal_capacity_kW``. Editing an existing tech
    (whose data carries ``thermal_capacity_kW``) therefore silently resets the
    displayed capacity to the field default. Pinned here; fix should flip these.
    """

    def test_gas_boiler_reads_th_leistung(self):
        dialog = GasBoilerDialog({"th_Leistung_kW": 555})
        assert dialog.getInputs()["thermal_capacity_kW"] == 555.0

    def test_gas_boiler_ignores_thermal_capacity_key(self):
        dialog = GasBoilerDialog({"thermal_capacity_kW": 555})
        assert dialog.getInputs()["thermal_capacity_kW"] == 1000.0  # field default

    def test_biomass_reads_p_bmk(self):
        dialog = BiomassBoilerDialog({"P_BMK": 555})
        assert dialog.getInputs()["thermal_capacity_kW"] == 555.0

    def test_biomass_ignores_thermal_capacity_key(self):
        dialog = BiomassBoilerDialog({"thermal_capacity_kW": 555})
        assert dialog.getInputs()["thermal_capacity_kW"] == 240.0  # field default


class TestVisualizationSmoke:
    """The Solar/Geothermal dialogs were schema-migrated; their 3D viz now reads
    field widgets via ``self._widgets``. getInputs() is pinned above, but the viz
    wiring is otherwise untested — these smoke tests ensure it builds and redraws
    without a KeyError / crash when the driving inputs change.
    """

    def test_geothermal_viz_redraws_on_change(self):
        dialog = GeothermalDialog()
        dialog._widgets["Fläche"].setText("250")    # triggers updateVisualization
        dialog._widgets["Bohrtiefe"].setText("150")
        dialog.updateVisualization()                 # explicit call must not raise

    def test_geothermal_viz_tolerates_invalid_input(self):
        dialog = GeothermalDialog()
        dialog._widgets["Fläche"].setText("")        # non-numeric → fallback path
        dialog.updateVisualization()

    def test_solar_viz_redraws_on_change(self):
        dialog = SolarThermalDialog()
        dialog._widgets["East_West_collector_azimuth_angle"].setText("45")
        dialog._widgets["Collector_tilt_angle"].setText("30")
        dialog.updateVisualization()

    def test_solar_viz_tolerates_invalid_input(self):
        dialog = SolarThermalDialog()
        dialog._widgets["Collector_tilt_angle"].setText("abc")  # non-numeric → fallback
        dialog.updateVisualization()
