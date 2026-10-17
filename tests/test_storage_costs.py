"""
Size-dependent storage costs (user test 2026-10-08, M15).

The network storage defaulted to a flat 50 €/m³ at 1000 m³ - a large pit storage's value - next
to 750 €/m³ for the buffer and solar storages. New storages now start at the typical cost for
their volume, c(V) = 750 €/m³ · (V / 20 m³)^-0.37.
"""

import pytest

from districtheatingsim.heat_generators.thermal_storage import ThermalStorageAdapter, typical_storage_cost_eur_per_m3


@pytest.mark.parametrize(
    ("volume", "low", "high"),
    [
        (20.0, 750.0, 750.0),  # the buffer and solar storage default
        (2000.0, 100.0, 150.0),  # tank storages (store4grid: 1,500-2,500 m³ at about 150-100 €/m³)
        (60_000.0, 30.0, 45.0),  # Dronninglund pit: 38 €/m³
        (210_000.0, 20.0, 30.0),  # Vojens pit: 24 €/m³
    ],
)
def test_curve_follows_the_reference_storages(volume, low, high):
    assert low <= typical_storage_cost_eur_per_m3(volume) <= high


def test_curve_falls_with_the_volume():
    costs = [typical_storage_cost_eur_per_m3(v) for v in (5, 20, 100, 1000, 10_000)]
    assert costs == sorted(costs, reverse=True)
    assert typical_storage_cost_eur_per_m3(0) == 750.0


def test_network_storage_takes_the_typical_cost_by_default():
    storage = ThermalStorageAdapter("Speicher", volume=1000.0)
    assert storage.spez_Investitionskosten == pytest.approx(typical_storage_cost_eur_per_m3(1000.0))
    assert 150 < storage.spez_Investitionskosten < 200  # was 50 €/m³
    assert ThermalStorageAdapter("Speicher", volume=1000.0, spez_Investitionskosten=50.0).spez_Investitionskosten == 50


def test_dialog_suggests_the_typical_cost(qapp):
    from districtheatingsim.gui.EnergySystemTab.technology_dialogs._storage import ThermalStorage1DDialog

    dialog = ThermalStorage1DDialog()
    assert dialog.spez_cost_input.text() == str(round(typical_storage_cost_eur_per_m3(1000.0)))
    assert "1.000 m³" in dialog.cost_hint.text()
    dialog.volume_input.setText("60000")
    assert "60.000 m³: etwa 39 €/m³" in dialog.cost_hint.text()  # Dronninglund: 38
    # A saved storage keeps its own value
    assert ThermalStorage1DDialog({"spez_Investitionskosten": 50.0}).spez_cost_input.text() == "50.0"
