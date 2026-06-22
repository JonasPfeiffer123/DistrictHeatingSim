"""
Shared PyInstaller build configuration for DistrictHeatingSim.

Both ``DistrictHeatingSim.spec`` (debug) and ``DistrictHeatingSim_Release.spec``
(release) import from here so the heavy ``datas`` / ``hiddenimports`` lists live in
exactly one place. The specs themselves only differ in the ``debug`` / ``console``
EXE flags.
"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# Entry script (OS-agnostic; the build is Windows-only but keep the separator portable).
ENTRY_SCRIPT = os.path.join("src", "districtheatingsim", "DistrictHeatingSim.py")

# Toolkits we never want pulled in.
EXCLUDES = ["PyQt5", "PySide2", "PySide6", "tkinter"]

# Imports PyInstaller's static analysis cannot discover on its own.
HIDDENIMPORTS = [
    "geopandas",
    "overpy",
    "geojson",
    "networkx",
    "pandapipes",
    "pandapipes.timeseries",
    "contextily",
    "rasterio.sample",
    "rtree",
    "rtree.index",
    "CoolProp",
    "matplotlib.backends.backend_qtagg",
    # osmnx 2.x splits its public API across many submodules PyInstaller misses.
    "osmnx",
    "osmnx.graph",
    "osmnx.utils",
    "osmnx.convert",
    "osmnx.distance",
    "osmnx.geocoder",
    "osmnx.projection",
    "osmnx.settings",
    "osmnx.plot",
    "osmnx.simplification",
    "osmnx.stats",
    "osmnx.bearing",
    "osmnx.elevation",
    "osmnx.routing",
    "osmnx.features",
    "osmnx._errors",
    "osmnx._nominatim",
    "osmnx._overpass",
    # scipy ships many lazily-imported C-extension submodules.
    "scipy._lib.array_api_compat.numpy",
    "scipy._lib.array_api_compat.numpy.fft",
    "scipy._lib.array_api_compat.numpy.linalg",
    "scipy.interpolate",
    "scipy.special",
    "scipy._cyutility",
    "scipy.linalg",
    "scipy.integrate",
    "scipy.optimize",
    "scipy.sparse",
    "scipy.spatial",
    "scipy.stats",
    "scipy.fft",
    "scipy.ndimage",
    "scipy.signal",
    "scipy._lib._ccallback",
    "scipy._lib._util",
    "scipy.linalg.cython_blas",
    "scipy.linalg.cython_lapack",
    "scipy.sparse.linalg",
    "scipy.sparse.csgraph",
]

# numpy 2.x renamed numpy.core -> numpy._core; the numpy hook bundled with PyInstaller
# 6.5.0 (released before numpy 2.0) misses some _core submodules, so the frozen exe
# crashed with "No module named 'numpy._core._exceptions'". Force the full numpy
# submodule tree in. (A newer PyInstaller + pyinstaller-hooks-contrib would also fix
# this via its updated numpy hook.)
HIDDENIMPORTS += collect_submodules("numpy")

# App resource folders bundled as plain data. Whole-directory copies, so new modules
# added inside them are picked up automatically. ``move_user_data_outside()`` in
# build_common.py later lifts data/project_data/images/leaflet out of _internal so
# users can edit them.
_APP_DATA_DIRS = [
    "data",
    "images",
    "leaflet",
    "geocoding",
    "gui",
    "gui/MainTab",
    "gui/NetSimulationTab",
    "gui/BuildingTab",
    "gui/ComparisonTab",
    "gui/EnergySystemTab",
    "gui/LeafletTab",
    "gui/ProjectTab",
    "heat_generators",
    "heat_requirement",
    "net_generation",
    "net_simulation_pandapipes",
    "osm",
    "project_data",
    "utilities",
    "styles",
]

_SRC = "src/districtheatingsim"


def get_datas():
    """Build the full ``datas`` list (resolved at build time, so paths stay current)."""
    datas = [(f"{_SRC}/{rel}", rel) for rel in _APP_DATA_DIRS]

    # file_paths.json is read from several locations depending on how the app is launched.
    datas += [
        (f"{_SRC}/gui/MainTab/file_paths.json", "gui/MainTab"),
        (f"{_SRC}/gui/MainTab/file_paths.json", "districtheatingsim/gui/MainTab"),
        (f"{_SRC}/gui/MainTab/file_paths.json", "."),
        (f"{_SRC}/project_data", "districtheatingsim/project_data"),
    ]

    # pandapipes std-type library + properties (the ISOPLUS catalog the 0.14 net model
    # relies on), resolved dynamically to avoid hardcoding a site-packages path.
    import pandapipes as _pp

    _pp_base = os.path.dirname(_pp.__file__)
    datas += [
        (os.path.join(_pp_base, "std_types", "library"), "pandapipes/std_types/library"),
        (os.path.join(_pp_base, "properties"), "pandapipes/properties"),
    ]

    # osmnx checks its own version → needs its dist metadata.
    datas += copy_metadata("osmnx")

    # pyslpheat (normal site-packages install) ships non-.py data that import-following
    # does NOT collect: BDEW/VDI profile CSVs (data/) + images/. Without these the frozen
    # exe's heat-demand calc fails at runtime. Its .py modules ARE collected normally.
    datas += collect_data_files("pyslpheat")

    # thermal-energy-storage-1d (import name thermal_energy_storage_model) is installed
    # *editable* (PEP 660, outside site-packages). PyInstaller's analysis can't resolve its
    # custom import finder, so it bundled only py.typed — the exe crashed on
    # "cannot import name 'ConstantAmbientLoss'". Copy the whole package directory in as
    # data so all its modules (incl. __init__/losses/model/solver) are importable from
    # _internal. (On a normal git install this dir lives in site-packages; the copy is
    # still correct and harmless.)
    import thermal_energy_storage_model as _tes

    datas += [(os.path.dirname(_tes.__file__), "thermal_energy_storage_model")]

    return datas
