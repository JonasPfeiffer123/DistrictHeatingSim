import geopandas as gpd

# Read the GeoJSON file
#geojson_gdf = gpd.read_file("net_generation/Vorlauf.geojson", driver="GeoJSON")

# Calculate the total length of all LineString geometries in the GeoDataFrame
#total_length = geojson_gdf.length.sum()
#print(total_length)

# Dateipfad zur GeoJSON-Datei
file_path = 'net_generation/Vorlauf.geojson'

# Einlesen der GeoJSON-Datei mit GeoPandas
gdf = gpd.read_file(file_path, driver="GeoJSON").to_crs(epsg=25833)

# Berechnung der Länge jeder Linie im GeoDataFrame
gdf['length'] = gdf.geometry.length

# Ausgabe der Längen der einzelnen Linien
print("Längen der einzelnen Linien:")
print(gdf['length'])

# Berechnung der Gesamtlänge aller Linien
total_length = gdf['length'].sum()
print("Gesamtlänge:", total_length)