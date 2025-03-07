import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as cx

# Laden Sie Ihre GeoJSON-Daten
gdf = gpd.read_file('C:\\Users\\jp66tyda\DistrictHeatSim\\districtheatsim\\project_data\\Bad Muskau\\Wärmenetz\\Vorlauf.geojson')

# Koordinatensystem überprüfen und in EPSG:3857 umprojizieren
if gdf.crs != "EPSG:3857":
    gdf = gdf.to_crs(epsg=3857)

# Plot erstellen
fig, ax = plt.subplots(figsize=(10, 10))

# Achsen auf die Grenzen des GeoDataFrame setzen
xmin, ymin, xmax, ymax = gdf.total_bounds
ax.set_xlim(xmin-10, xmax+10)
ax.set_ylim(ymin-10, ymax+10)

# Kontextkarte hinzufügen
#cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, crs=gdf.crs)

# Satellitenbild hinzufügen
#cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=gdf.crs)

# Topologiekarte hinzufügen
#cx.add_basemap(ax, source=cx.providers.OpenTopoMap, crs=gdf.crs)

# GeoDataFrame darüber plotten
gdf.plot(ax=ax, color='red', edgecolor='red', linewidth=2)

plt.show()
