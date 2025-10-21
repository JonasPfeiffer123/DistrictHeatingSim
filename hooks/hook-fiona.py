# PyInstaller hook for fiona
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_dynamic_libs

# Collect all fiona modules, data files and binaries
datas, binaries, hiddenimports = collect_all('fiona')

# Explicitly add fiona submodules
hiddenimports += collect_submodules('fiona')

# Collect dynamic libraries (GDAL, GEOS, etc.)
binaries += collect_dynamic_libs('fiona')

# Add specific hidden imports
hiddenimports += [
    'fiona._shim',
    'fiona._geometry',
    'fiona._env',
    'fiona._err',
    'fiona._transform',
    'fiona.crs',
    'fiona.schema',
    'fiona.transform',
    'fiona.collection',
    'fiona.ogrext',
    'fiona.model',
]
