# PyInstaller hook for shapely
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_dynamic_libs

# Collect all shapely modules, data files and binaries
datas, binaries, hiddenimports = collect_all('shapely')

# Explicitly add shapely submodules
hiddenimports += collect_submodules('shapely')

# Collect dynamic libraries (GEOS)
binaries += collect_dynamic_libs('shapely')

# Add specific hidden imports
hiddenimports += [
    'shapely.geometry',
    'shapely.geometry.base',
    'shapely.geometry.point',
    'shapely.geometry.linestring',
    'shapely.geometry.polygon',
    'shapely.geometry.multipoint',
    'shapely.geometry.multilinestring',
    'shapely.geometry.multipolygon',
    'shapely.geometry.collection',
    'shapely.geometry.geo',
    'shapely.ops',
    'shapely.prepared',
    'shapely.wkt',
    'shapely.wkb',
    'shapely.geos',
    'shapely.algorithms',
    'shapely.algorithms.cga',
    'shapely.algorithms.polylabel',
    'shapely.affinity',
    'shapely.coords',
    'shapely.errors',
    'shapely.predicates',
    'shapely.set_operations',
    'shapely.constructive',
    'shapely.measurement',
    'shapely.strtree',
    'shapely._geometry',
    'shapely._geos',
    'shapely.lib',
]
