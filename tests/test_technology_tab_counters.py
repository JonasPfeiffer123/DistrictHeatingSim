"""
Technology tab name counters (BACKLOG C40, C45).

``rebuildScene`` (after loading a configuration or reordering) reset every counter inside its loop,
so only the last technology type kept its count and the next added technology of an earlier type
got a duplicate name. The counters' keys are also the technologies the GUI offers — AqvaHeat is
left out until its model is finished (C40).
"""

import types

import pytest

from districtheatingsim.gui.EnergySystemTab._03_technology_tab import TechnologyTab
from districtheatingsim.heat_generators import TECH_CLASS_REGISTRY


def _fake_tab(names):
    return types.SimpleNamespace(
        schematic_scene=types.SimpleNamespace(delete_all=lambda: None),
        addTechToScene=lambda tech: None,
        updateTechList=lambda: None,
        global_counters=dict(TechnologyTab.global_counters),
        tech_objects=[types.SimpleNamespace(name=n) for n in names],
    )


def test_rebuild_scene_counts_every_technology_type():
    tab = _fake_tab(["Gaskessel_1", "BHKW_1", "Holzgas-BHKW_1", "BHKW_2"])
    TechnologyTab.rebuildScene(tab)

    assert {k: v for k, v in tab.global_counters.items() if v} == {"Gaskessel": 1, "BHKW": 2, "Holzgas-BHKW": 1}


def test_gui_offers_every_registered_technology_except_aqvaheat():
    assert set(TechnologyTab.global_counters) == set(TECH_CLASS_REGISTRY) - {"AqvaHeat"}


def test_create_technology_rejects_aqvaheat():
    tab = _fake_tab([])
    with pytest.raises(ValueError, match="nicht verfügbar"):
        TechnologyTab.createTechnology(tab, "AqvaHeat", {})
