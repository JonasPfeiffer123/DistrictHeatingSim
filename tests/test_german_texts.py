"""
German texts and units (user test 2026-10-08, UT-M2, UT-N).

Qt's own buttons and the file tree were English ("OK/Cancel", "Name/Size/Type"), the thermal storage
dialog entirely; fields had no units; the producer was called "Erzeugerstandort 162"; the network
preset for 85/70 °C was named "Niedertemperaturnetz".
"""

import json

import pytest

from districtheatingsim.utilities.utilities import get_resource_path


def test_qt_speaks_german(qapp):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFileSystemModel
    from PyQt6.QtWidgets import QDialogButtonBox

    from districtheatingsim.gui.qt_translation import install_german_qt_translation

    assert install_german_qt_translation(qapp)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    assert [b.text() for b in box.buttons()] == ["OK", "Abbrechen"]
    model = QFileSystemModel()
    assert [model.headerData(i, Qt.Orientation.Horizontal) for i in range(3)] == ["Name", "Größe", "Typ"]


def test_storage_dialog_is_german_and_keeps_the_model_keys(qapp):
    from PyQt6.QtWidgets import QComboBox, QGroupBox, QLabel

    from districtheatingsim.gui.EnergySystemTab.technology_dialogs._storage import ThermalStorage1DDialog

    dialog = ThermalStorage1DDialog(
        {"geometry_type": "truncated_cone", "loss_model_type": "split", "fluid_type": "constant"}
    )
    texts = [box.title() for box in dialog.findChildren(QGroupBox)] + [
        label.text() for label in dialog.findChildren(QLabel)
    ]
    for english in ("Basic", "Temperature Limits", "Loss Model", "Volume (m³):", "Costs", "Type:"):
        assert english not in texts
    assert dialog.geometry_combo.currentText() == "Kegelstumpf"
    assert [dialog.loss_type_combo.itemText(i) for i in range(3)] == [
        "ein U-Wert",
        "Deckel, Wand und Boden getrennt",
        "im Erdreich",
    ]
    inputs = dialog.getInputs()
    assert (inputs["geometry_type"], inputs["loss_model_type"], inputs["fluid_type"]) == (
        "truncated_cone",
        "split",
        "constant",
    )
    assert (inputs["solver"], inputs["advection_scheme"]) == ("implicit", "tvd")
    assert dialog._loss_split_widget.isVisibleTo(dialog) and not dialog._loss_constant_widget.isVisibleTo(dialog)
    assert isinstance(dialog.solver_combo, QComboBox)


@pytest.mark.parametrize(
    ("schema", "key", "unit"),
    [
        ("CHP_MAIN", "th_Leistung_kW", "in kW"),
        ("CHP_MAIN", "spez_Investitionskosten_GBHKW", "in €/kW"),
        ("CHP_STORAGE", "Speicher_Volumen_BHKW", "in m³"),
        ("CHP_STORAGE", "T_vorlauf", "in °C"),
        ("RIVER", "spezifische_Investitionskosten_WP", "in €/kW"),
    ],
)
def test_fields_have_units(schema, key, unit):
    from districtheatingsim.gui.EnergySystemTab.technology_dialogs import _schemas

    (field,) = [f for f in getattr(_schemas, schema) if getattr(f, "key", None) == key]
    assert unit in field.label


def test_network_presets():
    config = json.load(open(get_resource_path("gui/NetSimulationTab/dialog_config.json"), encoding="utf-8"))
    assert config["netconfiguration"] == ["Warmes Netz", "kaltes Netz"]  # 85/70 °C is no low-temperature network
    assert set(config["standardwerte"]) == set(config["netconfiguration"])


def test_producers_are_numbered_from_one(tmp_path):
    from districtheatingsim.gui.NetSimulationTab.producer_order_tab import ProducerOrderTab

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, i], [1, i]]},
            "properties": {"feature_type": "network_line_flow"},
        }
        for i in range(161)
    ] + [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[5, 5], [5, 6]]},
            "properties": {"feature_type": "generator_connection"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[6, 6], [6, 7]]},
            "properties": {"feature_type": "generator_connection"},
        },
    ]
    path = tmp_path / "Wärmenetz.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    producers = ProducerOrderTab.read_producers_from_geojson(None, str(path))
    assert [p["name"] for p in producers] == ["Erzeugerstandort 1", "Erzeugerstandort 2"]


@pytest.mark.parametrize(
    ("name", "shown"),
    [("flow line 3", "Vorlauf 3"), ("return line 12", "Rücklauf 12"), ("Vorlauf 4", "Vorlauf 4"), (None, "Leitung 7")],
)
def test_pipe_names_are_shown_in_german(name, shown):
    from districtheatingsim.gui.NetSimulationTab.pipe_config_table import pipe_display_name

    assert pipe_display_name(name, 7) == shown
