import os
import sys
import geopandas as gpd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from shapely.geometry import Point, Polygon, MultiPolygon
import numpy as np

def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

def calculate_normal_and_angles(polygon):
    coords = list(polygon.exterior.coords)
    if len(coords) < 3:
        return None, None, None

    # Berechnung des Normalenvektors für die ersten drei Punkte
    p1 = np.array(coords[0])
    p2 = np.array(coords[1])
    p3 = np.array(coords[2])
    v1 = p2 - p1
    v2 = p3 - p1
    normal = np.cross(v1, v2)
    normal = normal / np.linalg.norm(normal)
    
    # Neigungswinkel
    inclination = np.arccos(normal[2]) * 180 / np.pi
    
    # Azimutwinkel
    azimuth = np.arctan2(normal[1], normal[0]) * 180 / np.pi
    if azimuth < 0:
        azimuth += 360

    area = polygon.area

    return normal, inclination, azimuth, area

class RoofAreaPlot(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.text_annotation = None  # Zum Speichern der Textreferenz
        self.selected_patches = []  # Zum Speichern der ausgewählten Dachpolygone
    
    def initUI(self):
        self.setWindowTitle('Dachflächen Visualisierung')
        self.setGeometry(100, 100, 800, 600)
        
        # Layout und Canvas einrichten
        layout = QVBoxLayout()
        self.canvas = FigureCanvas(plt.figure())
        layout.addWidget(self.canvas)
        
        # Hauptwidget und Layout
        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)
        
        self.plot_roof_areas()

    def plot_roof_areas(self):
        # GeoDataFrame einlesen
        self.gdf = gpd.read_file(get_resource_path('filtered_LOD_quartier_1.geojson'))
        
        # Überprüfen der Spaltennamen
        print(self.gdf.columns)
        
        self.dachflächen = self.gdf[self.gdf['Geometr_3D'] == 'Roof'][['geometry', 'Dachflaech', 'Dachorient', 'Dachneig', 'Obj_Parent', 'ID']]
        
        # Plotten
        self.ax = self.canvas.figure.subplots()
        self.dachflächen.plot(ax=self.ax, color='blue', edgecolor='black')
        
        self.canvas.draw()
        
        # Klick-Event hinzufügen
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def on_click(self, event):
        # Überprüfen, ob innerhalb der Achsen geklickt wurde
        if event.inaxes is not None:
            x, y = event.xdata, event.ydata
            
            # Überprüfen, ob ein Polygon geklickt wurde
            for idx, row in self.dachflächen.iterrows():
                if row['geometry'].contains(Point(x, y)):
                    # Vorherigen Text entfernen, falls vorhanden
                    if self.text_annotation:
                        self.text_annotation.remove()

                    # Daten für Parent-Objekt und Teilobjekte sammeln
                    object_id = row['ID']
                    parent_id = row['Obj_Parent']
                    
                    # Alle relevanten Dachflächen sammeln
                    if parent_id:
                        sub_roofs = self.dachflächen[(self.dachflächen['Obj_Parent'] == parent_id) | (self.dachflächen['ID'] == parent_id)]
                    else:
                        sub_roofs = self.dachflächen[(self.dachflächen['ID'] == object_id) | (self.dachflächen['Obj_Parent'] == object_id)]
                    
                    total_area = sub_roofs['Dachflaech'].sum()
                    print(f"Ausgewähltes Objekt: {object_id}")
                    print("Dazu gehörige Dachflächen:")
                    print(sub_roofs)

                    # Text für das Objekt und Teilflächen erstellen
                    text = f"Gesamtfläche: {total_area:.2f} m²\n"
                    for sub_idx, sub_row in sub_roofs.iterrows():
                        geom = sub_row['geometry']
                        if isinstance(geom, MultiPolygon):
                            for poly in geom.geoms:
                                normal, inclination, azimuth, area = calculate_normal_and_angles(poly)
                                text += (f"Teilfläche: {area:.2f} m², "
                                         f"Ausrichtung: {azimuth:.2f}°, "
                                         f"Neigung: {inclination:.2f}°\n")
                        else:
                            normal, inclination, azimuth, area = calculate_normal_and_angles(geom)
                            text += (f"Teilfläche: {area:.2f} m², "
                                     f"Ausrichtung: {azimuth:.2f}°, "
                                     f"Neigung: {inclination:.2f}°\n")
                    
                    # Neuen Text hinzufügen
                    self.text_annotation = plt.gcf().text(
                        0.5, 0.01, 
                        text, 
                        ha='center',
                        transform=plt.gcf().transFigure,
                        fontsize=8,
                        bbox=dict(facecolor='white', alpha=0.8)
                    )
                    
                    # Vorheriges ausgewähltes Polygon zurücksetzen
                    for patch in self.selected_patches:
                        patch.remove()
                    self.selected_patches = []

                    # Neues ausgewähltes Polygon hervorheben
                    for sub_idx, sub_row in sub_roofs.iterrows():
                        selected_patch = sub_row['geometry']
                        if isinstance(selected_patch, Polygon):
                            coords = [(x, y) for x, y, z in selected_patch.exterior.coords]
                            patch = plt.Polygon(coords, closed=True, fill=False, edgecolor='red', linewidth=3)
                            self.selected_patches.append(patch)
                            self.ax.add_patch(patch)
                        elif isinstance(selected_patch, MultiPolygon):
                            for poly in selected_patch.geoms:
                                coords = [(x, y) for x, y, z in poly.exterior.coords]
                                patch = plt.Polygon(coords, closed=True, fill=False, edgecolor='red', linewidth=3)
                                self.selected_patches.append(patch)
                                self.ax.add_patch(patch)
                    
                    self.canvas.draw()
                    break

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RoofAreaPlot()
    ex.show()
    sys.exit(app.exec_())
