"""
LOD2 3D Plot Module
==================

3D visualization widget for LOD2 building data using Matplotlib.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-02
"""

import numpy as np

from shapely.geometry import Polygon, MultiPolygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import matplotlib.cm as cm
from matplotlib.ticker import MaxNLocator

import contextily as cx
import numpy as np
import matplotlib.pyplot as plt

class LOD2Visualization3D:
    """
    Widget for 3D visualization of LOD2 building data.
    """

    def __init__(self, canvas_3d):
        """
        Initialize 3D visualization widget.

        Parameters
        ----------
        canvas_3d : FigureCanvas
            Canvas for rendering 3D plots.
        """
        self.figure_3d = canvas_3d.figure
        self.canvas_3d = canvas_3d
        self.building_data = {}
        self.roof_data = {}
        self.highlighted_building_id = None
        self.roof = False
        self.highlighted_roof_id = None
        self.utm_epsg = "EPSG:25833"

    def update_3d_view(self, building_info):
        """
        Update 3D view with building data.

        Parameters
        ----------
        building_info : dict
            Building information dictionary.
        """
        self.building_data = building_info
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')

        # Hintergrundfarbe & Gitter optimieren
        ax.set_facecolor((0.95, 0.95, 0.95))
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5)

        # Farbskala für unmarkierte Gebäude
        color_map = cm.get_cmap('viridis')
        face_colors = color_map(np.linspace(0, 1, len(building_info)))

        # **Bounds berechnen**
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        # **Gebäude zeichnen**
        for i, (parent_id, info) in enumerate(building_info.items()):
            # **Hervorhebung der Auswahl**: Falls `highlighted_building_id`, dann ROT
            building_color = face_colors[i]
            if self.roof == False:
                if parent_id == self.highlighted_building_id:
                    building_color = (1, 0, 0, 1)  # **Reines Rot in RGBA**
            
            min_x, min_y, min_z, max_x, max_y, max_z = self.plot_building_parts(
                ax, info, min_x, min_y, min_z, max_x, max_y, max_z, building_color
            )

        # Achsenverzerrung entfernen, Z-Achse begrenzen
        self.set_equal_axes(ax, min_x, max_x, min_y, max_y, min_z, max_z)

        # load OSM background
        #self.add_osm_background(ax, min_x, max_x, min_y, max_y, min_z, max_z)

        # Achsenbeschriftungen
        ax.set_xlabel('UTM_X', fontsize=10, color='black', labelpad=10)
        ax.set_ylabel('UTM_Y', fontsize=10, color='black', labelpad=10)
        ax.set_zlabel('Absolute Höhe (m NN)', fontsize=10, color='black', labelpad=10)

        self.canvas_3d.draw()

    def plot_building_parts(self, ax, info, min_x, min_y, min_z, max_x, max_y, max_z, building_color):
        """
        Plot building parts and update bounding box.

        Parameters
        ----------
        ax : Axes3D
            3D axes object.
        info : dict
            Building information dictionary.
        min_x, min_y, min_z : float
            Minimum bounding values.
        max_x, max_y, max_z : float
            Maximum bounding values.
        building_color : tuple
            RGBA color for building parts.

        Returns
        -------
        tuple
            Updated bounding box values.
        """
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Ground', []), building_color, min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Wall', []), building_color, min_x, min_y, min_z, max_x, max_y, max_z)
        if self.roof == False:
            min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
                ax, info.get('Roof', []), building_color, min_x, min_y, min_z, max_x, max_y, max_z)
        else:
            # Plotting Roof geometries
            for i, roof in enumerate(info.get('Roofs', [])):
                roof_color = building_color
                parent_id = roof.get('parent_id')
                if parent_id == self.highlighted_building_id and (self.highlighted_roof_id is None or self.highlighted_roof_id == i):
                    roof_color = (1, 0, 0, 1)  # Pure red in RGBA
                
                min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
                    ax, [roof['geometry']], roof_color, min_x, min_y, min_z, max_x, max_y, max_z)

        return min_x, min_y, min_z, max_x, max_y, max_z

    def plot_geometry(self, ax, geoms, color, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        Plot geometry and update bounding box.

        Parameters
        ----------
        ax : Axes3D
            3D axes object.
        geoms : list or shapely.geometry
            Geometries to plot.
        color : tuple
            RGBA color for geometry.
        min_x, min_y, min_z : float
            Minimum bounding values.
        max_x, max_y, max_z : float
            Maximum bounding values.

        Returns
        -------
        tuple
            Updated bounding box values.
        """
        if isinstance(geoms, (Polygon, MultiPolygon)):
            geoms = [geoms]

        for geom in geoms:
            if geom:
                if geom.geom_type == 'Polygon':
                    x, y, z = zip(*geom.exterior.coords)
                    verts = [list(zip(x, y, z))]
                    poly_collection = Poly3DCollection(
                        verts, facecolors=color, edgecolors='k', linewidths=0.3, alpha=0.85  # Schärfere Kanten
                    )
                    ax.add_collection3d(poly_collection)

                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y, z = zip(*poly.exterior.coords)
                        verts = [list(zip(x, y, z))]
                        poly_collection = Poly3DCollection(
                            verts, facecolors=color, edgecolors='k', linewidths=0.3, alpha=0.85
                        )
                        ax.add_collection3d(poly_collection)

                # Update bounds
                min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))

        return min_x, min_y, min_z, max_x, max_y, max_z

    def highlight_building_3d(self, parent_id, roof=False, roof_id=None, roof_info=None):
        """
        Highlight specific building in 3D plot.

        Parameters
        ----------
        parent_id : str
            Building ID to highlight.
        roof : bool, optional
            Whether to highlight roof.
        roof_id : int, optional
            Roof index to highlight.
        roof_info : dict, optional
            Roof information dictionary.
        """
        self.roof = roof
        self.highlighted_roof_id = roof_id
        self.highlighted_building_id = parent_id
        self.roof_info = roof_info

        if self.roof and roof_info:
            # Re-render the 3D view with the updated highlight
            self.update_3d_view(self.roof_info)
        else:
            # Re-render the 3D view with the updated highlight
            self.update_3d_view(self.building_data)

    def set_equal_axes(self, ax, min_x, max_x, min_y, max_y, min_z, max_z):
        """
        Set equal aspect ratio for all axes with proportional Z scaling.

        Parameters
        ----------
        ax : Axes3D
            3D axes object.
        min_x, max_x : float
            X axis bounds.
        min_y, max_y : float
            Y axis bounds.
        min_z, max_z : float
            Z axis bounds.
        """
        range_x = max_x - min_x
        range_y = max_y - min_y
        range_z = max_z - min_z

        # Größte Spanne in X oder Y bestimmen (Grundfläche bestimmen)
        max_range = max(range_x, range_y)

        # Automatische Skalierung: Z-Achse relativ zur größten X/Y-Ausdehnung
        z_scale_factor = range_z / max_range

        # Berechne Mittelpunkte
        mid_x = (max_x + min_x) / 2
        mid_y = (max_y + min_y) / 2
        mid_z = (max_z + min_z) / 2

        # Achsenlimits setzen
        ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
        ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
        ax.set_zlim(mid_z - range_z / 2, mid_z + range_z / 2)

        ax.zaxis.set_major_locator(MaxNLocator(nbins=2))  # Reduziert auf maximal 5 Ticks

        # Proportionale Darstellung mit automatisch berechneter Z-Skalierung
        ax.set_box_aspect([1, 1, z_scale_factor])

    def add_osm_background(self, ax, xmin, xmax, ymin, ymax, zmin, zmax, resolution=400):
        """
        Add OSM map as 3D plot background.

        Parameters
        ----------
        ax : Axes3D
            3D axes object.
        xmin, ymin : float
            Lower left corner of bounding box.
        xmax, ymax : float
            Upper right corner of bounding box.
        zmin, zmax : float
            Z bounds for background placement.
        resolution : int, optional
            Maximum points per axis for performance.
        """

        print(f"Bounding Box berechnen... xmin={xmin}, xmax={xmax}, ymin={ymin}, ymax={ymax}")

        if any(map(lambda v: np.isnan(v) or np.isinf(v), [xmin, ymin, xmax, ymax])):
            print("Fehler: Ungültige Bounding Box!")
            return

        fig, ax2d = plt.subplots(figsize=(8, 8))

        # Achsenbegrenzung setzen
        ax2d.set_xlim(xmin, xmax)
        ax2d.set_ylim(ymin, ymax)

        # OSM-Karte als Hintergrund setzen
        try:
            cx.add_basemap(ax2d, source=cx.providers.OpenStreetMap.Mapnik, crs="EPSG:25833")
            print("OSM Karte erfolgreich hinzugefügt!")
        except Exception as e:
            print(f"Fehler bei der OSM-Karte: {e}")
            return

        fig.canvas.draw()
        background_img = np.array(fig.canvas.renderer.buffer_rgba())
        plt.close(fig)  # 2D-Plot schließen

        print(f"OSM-Karte geladen mit Shape {background_img.shape}")

        # **Alpha-Kanal entfernen, falls vorhanden (von (800,800,4) → (800,800,3))**
        if background_img.shape[2] == 4:
            background_img = background_img[:, :, :3]  # Nur RGB übernehmen

        # **Normalisiere die Farben auf [0,1] für plot_surface()**
        background_img = background_img / 255.0  

        # **Anzahl der Punkte begrenzen (Performance-Fix)**
        step = max(1, background_img.shape[0] // resolution)  # Reduziere Auflösung
        background_img = background_img[::step, ::step]  # Reduziert die Datenmenge

        # **OSM-Karte als 3D-Bodenebene setzen**
        x_range = np.linspace(xmin, xmax, background_img.shape[1])
        y_range = np.linspace(ymin, ymax, background_img.shape[0])
        x_mesh, y_mesh = np.meshgrid(x_range, y_range)

        # **Höhe leicht unterhalb der Gebäude setzen (min_z - 5%)**
        z_plane = np.full_like(x_mesh, zmin - (zmax - zmin) * 0.05)  

        print(f"3D-Boden mit Shape {x_mesh.shape} hinzugefügt.")

        # **`plot_surface()` mit korrekter `facecolors`-Shape**
        ax.plot_surface(x_mesh, y_mesh, z_plane, rstride=1, cstride=1,
                        facecolors=background_img, shade=False, zorder=-10, alpha=0.2)

        print("OSM-Karte erfolgreich im 3D-Plot hinzugefügt!")


        # Alternative Karten:
        # cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=self.utm_epsg)  # Satellitenkarte
        # cx.add_basemap(ax, source=cx.providers.OpenTopoMap, crs=self.utm_epsg)  # Topographische Karte