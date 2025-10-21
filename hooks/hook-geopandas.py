# PyInstaller hook for geopandas
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all geopandas modules and data
datas, binaries, hiddenimports = collect_all('geopandas')

# Explicitly add geopandas submodules
hiddenimports += collect_submodules('geopandas')

# Add critical dependencies
hiddenimports += [
    'fiona',
    'fiona.crs',
    'fiona.schema',
    'fiona.transform',
    'fiona._env',
    'fiona._shim',
    'fiona._geometry',
    'fiona.collection',
    'shapely',
    'shapely.geometry',
    'shapely.geometry.base',
    'shapely.geometry.point',
    'shapely.geometry.linestring',
    'shapely.geometry.polygon',
    'shapely.geometry.multipoint',
    'shapely.geometry.multilinestring',
    'shapely.geometry.multipolygon',
    'shapely.geometry.collection',
    'shapely.ops',
    'shapely.prepared',
    'shapely.wkt',
    'shapely.wkb',
    'shapely.geos',
    'shapely.algorithms',
    'pyproj',
    'pyproj.crs',
    'pyproj.database',
    'pyproj.transformer',
    'pyproj._datadir',
    'rtree',
    'rtree.index',
]
