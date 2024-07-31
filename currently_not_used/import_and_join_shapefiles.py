import os
from qgis.core import QgsVectorLayer, QgsProject

def add_shapefiles_from_directory(directory):
    """Durchsucht ein Verzeichnis rekursiv nach Shapefiles und fügt sie einem QGIS-Projekt hinzu."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".shp"):
                file_path = os.path.join(root, file)
                # Erstelle einen Layer aus dem Shapefile
                layer = QgsVectorLayer(file_path, file, "ogr")
                if not layer.isValid():
                    print(f"Fehler beim Laden des Layers: {file_path}")
                    continue
                # Füge den Layer dem Projekt hinzu
                QgsProject.instance().addMapLayer(layer)
                print(f"Layer hinzugefügt: {file_path}")

# Pfad zum übergeordneten Ordner, der die Unterordner mit Shapefiles enthält
directory = 'C:/Users/username/heating_network_generation/project_data/Görlitz_SH_Campus/Gebäudedaten/lod2_data'

# Funktion aufrufen
add_shapefiles_from_directory(directory)