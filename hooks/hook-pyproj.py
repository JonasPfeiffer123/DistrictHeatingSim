# PyInstaller hook for pyproj
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, collect_dynamic_libs

# Collect all pyproj modules, data files and binaries
datas, binaries, hiddenimports = collect_all('pyproj')

# Explicitly add pyproj submodules
hiddenimports += collect_submodules('pyproj')

# Collect dynamic libraries (PROJ)
binaries += collect_dynamic_libs('pyproj')

# Collect data files (PROJ database)
datas += collect_data_files('pyproj')

# Add specific hidden imports
hiddenimports += [
    'pyproj.crs',
    'pyproj.crs.crs',
    'pyproj.crs.coordinate_system',
    'pyproj.crs.coordinate_operation',
    'pyproj.crs.datum',
    'pyproj.crs.enums',
    'pyproj.database',
    'pyproj.transformer',
    'pyproj.geod',
    'pyproj._datadir',
    'pyproj._compat',
    'pyproj._transformer',
    'pyproj._geod',
    'pyproj._crs',
    'pyproj._datadir',
    'pyproj.exceptions',
]
