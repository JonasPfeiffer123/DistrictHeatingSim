"""
Startup-import guards (BACKLOG G8).

Importing the main window imports every tab. CoolProp (~0.9 s, only for the AqvaHeat heat
pump) and osmnx (~0.7 s incl. scikit-learn/rasterio, only for OSMnx net generation) used to
load on that path. These tests pin that they stay off it — run in a subprocess so modules
imported by other tests don't interfere. (seaborn is not guarded: pandapower imports it.)
"""

import os
import subprocess
import sys

import pytest

_HEAVY_OPTIONAL = ("CoolProp", "osmnx")


def test_main_window_import_skips_heavy_optional_packages():
    code = (
        "import sys\n"
        "import districtheatingsim.gui.MainTab.main_view\n"
        f"print('LOADED:' + ','.join(m for m in {_HEAVY_OPTIONAL!r} if m in sys.modules))\n"
    )
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=300)

    assert result.returncode == 0, result.stderr
    loaded = [line for line in result.stdout.splitlines() if line.startswith("LOADED:")]
    assert loaded == ["LOADED:"]


def test_net_generation_reexports_resolve_lazily():
    import districtheatingsim.net_generation as net_generation
    from districtheatingsim.net_generation import generate_osmnx_network
    from districtheatingsim.net_generation.osmnx_steiner_network import generate_osmnx_network as direct

    assert generate_osmnx_network is direct
    with pytest.raises(AttributeError):
        net_generation.does_not_exist  # noqa: B018


_WELCOME_WINDOW = """
import sys
from PyQt6 import QtWebEngineWidgets  # as in the entry point: before the QApplication
from PyQt6.QtWidgets import QApplication
from districtheatingsim.gui.MainTab.main_data_manager import DataManager, ProjectConfigManager, ProjectFolderManager
from districtheatingsim.gui.MainTab.main_presenter import HeatSystemPresenter
from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI

app = QApplication(sys.argv)
config_manager = ProjectConfigManager()
folder_manager = ProjectFolderManager(config_manager)
data_manager = DataManager()
view = HeatSystemDesignGUI(folder_manager, data_manager)
view.set_presenter(HeatSystemPresenter(view, folder_manager, data_manager, config_manager))
heavy = ("pandapipes", "pandapower", "geopandas", "matplotlib", "pyarrow", "scipy", "osmnx", "CoolProp")
print("BUILT:" + str(view.main_interface_widget is not None))
print("LOADED:" + ",".join(m for m in heavy if m in sys.modules))
view.close()  # closing from the welcome screen must work without any tab
print("CLOSED:" + str(not view.isVisible()))
"""


def test_welcome_screen_builds_no_tabs_and_loads_no_heavy_packages():
    # G8: the main interface (six tabs incl. two web views) and the tab modules are only built /
    # imported when it is first shown; the welcome screen came up after 3.7 s, now ~0.5 s.
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, "-c", _WELCOME_WINDOW], capture_output=True, text=True, env=env, timeout=300
    )
    assert result.returncode == 0, result.stderr
    lines = dict(line.split(":", 1) for line in result.stdout.splitlines() if line.split(":", 1)[0].isupper())
    assert lines["BUILT"] == "False"
    assert lines["LOADED"] == ""
    assert lines["CLOSED"] == "True"
