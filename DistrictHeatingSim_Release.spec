# -*- mode: python ; coding: utf-8 -*-

import os
import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

# Collect package metadata for packages that check their own version
from PyInstaller.utils.hooks import copy_metadata

datas_metadata = copy_metadata('osmnx')

# Resolve pandapipes data paths dynamically (avoids hardcoded site-packages paths)
import pandapipes as _pp
_pp_base = os.path.dirname(_pp.__file__)
_pandapipes_lib = os.path.join(_pp_base, 'std_types', 'library')
_pandapipes_props = os.path.join(_pp_base, 'properties')


a = Analysis(
    ['src\\districtheatingsim\\DistrictHeatingSim.py'],
    pathex=[],
    binaries=[],
    datas=[('src/districtheatingsim/data', 'data'), ('src/districtheatingsim/images', 'images'), ('src/districtheatingsim/leaflet', 'leaflet'), ('src/districtheatingsim/geocoding', 'geocoding'), ('src/districtheatingsim/gui', 'gui'), ('src/districtheatingsim/gui/MainTab', 'gui/MainTab'), ('src/districtheatingsim/gui/NetSimulationTab', 'gui/NetSimulationTab'), ('src/districtheatingsim/gui/BuildingTab', 'gui/BuildingTab'), ('src/districtheatingsim/gui/ComparisonTab', 'gui/ComparisonTab'), ('src/districtheatingsim/gui/EnergySystemTab', 'gui/EnergySystemTab'), ('src/districtheatingsim/gui/LeafletTab', 'gui/LeafletTab'), ('src/districtheatingsim/gui/ProjectTab', 'gui/ProjectTab'), ('src/districtheatingsim/heat_generators', 'heat_generators'), ('src/districtheatingsim/heat_requirement', 'heat_requirement'), ('src/districtheatingsim/net_generation', 'net_generation'), ('src/districtheatingsim/net_simulation_pandapipes', 'net_simulation_pandapipes'), ('src/districtheatingsim/osm', 'osm'), ('src/districtheatingsim/project_data', 'project_data'), ('src/districtheatingsim/project_data', 'districtheatingsim/project_data'), ('src/districtheatingsim/utilities', 'utilities'), ('src/districtheatingsim/styles', 'styles'), ('src/districtheatingsim/gui/MainTab/file_paths.json', 'gui/MainTab'), ('src/districtheatingsim/gui/MainTab/file_paths.json', 'districtheatingsim/gui/MainTab'), ('src/districtheatingsim/gui/MainTab/file_paths.json', '.'), (_pandapipes_lib, 'pandapipes/std_types/library'), (_pandapipes_props, 'pandapipes/properties')] + datas_metadata,
    hiddenimports=['geopandas', 'overpy', 'geojson', 'networkx', 'numpy_financial', 'pandapipes', 'pandapipes.timeseries', 'contextily', 'rasterio.sample', 'rtree', 'rtree.index', 'CoolProp', 'matplotlib.backends.backend_qtagg', 'osmnx', 'osmnx.graph', 'osmnx.utils', 'osmnx.convert', 'osmnx.distance', 'osmnx.geocoder', 'osmnx.projection', 'osmnx.settings', 'osmnx.plot', 'osmnx.simplification', 'osmnx.stats', 'osmnx.bearing', 'osmnx.elevation', 'osmnx.routing', 'osmnx.features', 'osmnx._errors', 'osmnx._nominatim', 'osmnx._overpass', 'scipy._lib.array_api_compat.numpy', 'scipy._lib.array_api_compat.numpy.fft', 'scipy._lib.array_api_compat.numpy.linalg', 'scipy.interpolate', 'scipy.special', 'scipy._cyutility', 'scipy.linalg', 'scipy.integrate', 'scipy.optimize', 'scipy.sparse', 'scipy.spatial', 'scipy.stats', 'scipy.fft', 'scipy.ndimage', 'scipy.signal', 'scipy._lib._ccallback', 'scipy._lib._util', 'scipy.linalg.cython_blas', 'scipy.linalg.cython_lapack', 'scipy.sparse.linalg', 'scipy.sparse.csgraph'],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'PySide6', 'tkinter'],
    noarchive=True,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='DistrictHeatingSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Separate datas into those that should be outside _internal and those inside
# Folders outside _internal: data, project_data, images, leaflet (user-accessible)
# Everything else goes into _internal
datas_outside_internal = []
datas_inside_internal = []

for item in a.datas:
    # item is a tuple: (dest_name, source_path, 'DATA')
    dest_path = item[0]
    # Check if this should go outside _internal (non-Python user-accessible folders)
    if dest_path.startswith('data/') or dest_path.startswith('data\\') or dest_path == 'data' or \
       dest_path.startswith('project_data/') or dest_path.startswith('project_data\\') or dest_path == 'project_data' or \
       dest_path.startswith('images/') or dest_path.startswith('images\\') or dest_path == 'images' or \
       dest_path.startswith('leaflet/') or dest_path.startswith('leaflet\\') or dest_path == 'leaflet' or \
       dest_path.startswith('districtheatingsim/images/') or dest_path.startswith('districtheatingsim\\images\\') or \
       dest_path.startswith('districtheatingsim/leaflet/') or dest_path.startswith('districtheatingsim\\leaflet\\'):
        datas_outside_internal.append(item)
    else:
        datas_inside_internal.append(item)

# Combine all datas before creating COLLECT (PyInstaller 6.5.0+ requirement)
all_datas = datas_inside_internal + datas_outside_internal

coll = COLLECT(
    exe,
    a.binaries,
    all_datas,  # All datas combined
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DistrictHeatingSim',
)