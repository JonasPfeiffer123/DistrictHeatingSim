"""Network configuration tab of the net generation dialog: defaults per network type.

Every checkbox toggle reset the supply and return temperatures typed in to the defaults, and a
switch of the network type left the building minimum supply temperature and dT_RL of the previous
type.
"""

import pytest

from districtheatingsim.gui.NetSimulationTab.net_generation_dialog import load_dialog_config


@pytest.fixture
def tab(qapp):
    from districtheatingsim.gui.NetSimulationTab.network_config_tab import NetworkConfigTab

    return NetworkConfigTab(load_dialog_config())


def _text(row):
    return row.itemAt(1).widget().text()


def _rows(tab):
    return {
        "max_supply_temp": tab.max_supply_temp_row,
        "min_supply_temp": tab.min_supply_temp_row,
        "min_supply_temp_building": tab.min_supply_temperature_building_row,
        "return_temp": tab.return_temp_row,
        "dT_RL": tab.dT_RL_row,
    }


def test_typed_values_survive_checkbox_toggles(tab):
    typed = {"max_supply_temp": "90", "min_supply_temp": "72", "min_supply_temp_building": "55", "return_temp": "42"}
    for key, value in typed.items():
        _rows(tab)[key].itemAt(1).widget().setText(value)

    tab.minSupplyTempCheckbox.setChecked(True)
    tab.returnTempCheckbox.setChecked(True)
    tab.buildingTempCheckbox.setChecked(True)
    tab.supplyTemperatureControlInput.setCurrentText("Statisch")
    tab.supplyTemperatureControlInput.setCurrentText("Gleitend")

    assert {key: _text(_rows(tab)[key]) for key in typed} == typed


@pytest.mark.parametrize("network_type", ["kaltes Netz", "Warmes Netz"])
def test_switching_the_network_type_applies_all_its_defaults(tab, network_type):
    other = next(name for name in load_dialog_config()["netconfiguration"] if name != network_type)
    tab.netconfigurationControlInput.setCurrentText(other)
    tab.netconfigurationControlInput.setCurrentText(network_type)

    defaults = load_dialog_config()["standardwerte"][network_type]
    assert {key: _text(row) for key, row in _rows(tab).items()} == {key: str(defaults[key]) for key in _rows(tab)}
