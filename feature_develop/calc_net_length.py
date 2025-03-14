import geopandas as gpd

# Read the GeoJSON file
#geojson_gdf = gpd.read_file("net_generation/Vorlauf.geojson", driver="GeoJSON")

# Calculate the total length of all LineString geometries in the GeoDataFrame
#total_length = geojson_gdf.length.sum()
#print(total_length)

# Dateipfad zur GeoJSON-Datei
#file_path = 'H:\\Arbeit\\01_SMWK-NEUES Bearbeitung\\04_Projekt Bad Muskau\\03_Bearbeitung\\Projektordner\\Bad Muskau Quartier 1\\Wärmenetz\\Vorlauf.geojson'
#file_path = 'H:\\Arbeit\\01_SMWK-NEUES Bearbeitung\\04_Projekt Bad Muskau\\03_Bearbeitung\\Projektordner\\Bad Muskau Quartier 2\\Wärmenetz\\Vorlauf.geojson'
file_path = 'H:\\Arbeit\\01_SMWK-NEUES Bearbeitung\\04_Projekt Bad Muskau\\03_Bearbeitung\\Projektordner\\Bad Muskau Quartier 3\\Wärmenetz\\Vorlauf.geojson'

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