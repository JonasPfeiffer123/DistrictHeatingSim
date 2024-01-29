import geopandas as gpd

# Read the GeoJSON file
geojson_gdf = gpd.read_file("net_generation/Vorlauf.geojson", driver="GeoJSON")

# Calculate the total length of all LineString geometries in the GeoDataFrame
total_length = geojson_gdf.length.sum()
print(total_length)