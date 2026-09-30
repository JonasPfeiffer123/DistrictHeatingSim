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
