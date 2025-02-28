"""
Filename: lod2_3d_plot_matplotlib.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-28
Description: Contains the 3D visualization for LOD2 data.
"""

from shapely.geometry import Polygon, MultiPolygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

class LOD2Visualization3D:
    """
    A class for handling 3D visualization of LOD2 building data.
    """

    def __init__(self, canvas_3d):
        """
        Initialize with the 3D canvas.

        Args:
            canvas_3d (FigureCanvas): The canvas for rendering 3D plots.
        """
        self.figure_3d = canvas_3d.figure
        self.canvas_3d = canvas_3d
        self.building_data = {}  # To keep track of all buildings
        self.highlighted_building_id = None  # To keep track of the highlighted building

    def update_3d_view(self, building_info):
        """
        Update the 3D view with new building data.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.building_data = building_info  # Store the current building data
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')

        # Initialize bounds
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        # Plot each building part and update the bounds
        for parent_id, info in building_info.items():
            color = 'red' if parent_id == self.highlighted_building_id else 'blue'
            min_x, min_y, min_z, max_x, max_y, max_z = self.plot_building_parts(
                ax, info, min_x, min_y, min_z, max_x, max_y, max_z, color)

        # Set plot limits based on calculated bounds
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_zlim(min_z, max_z)

        # Set the aspect ratio for proper scaling
        ax.set_box_aspect([max_x - min_x, max_y - min_y, max_z - min_z])

        ax.set_xlabel('UTM_X')
        ax.set_ylabel('UTM_Y')
        ax.set_zlabel('Höhe')
        ax.set_title('3D-Visualisierung der LOD2-Daten')

        self.canvas_3d.draw()

    def plot_building_parts(self, ax, info, min_x, min_y, min_z, max_x, max_y, max_z, color):
        """
        Plots the building parts in the 3D plot and updates the bounds.

        Args:
            ax (Axes3D): The 3D axes object.
            info (dict): A dictionary containing building information.
            min_x (float): The minimum X value for bounding the plot.
            min_y (float): The minimum Y value for bounding the plot.
            min_z (float): The minimum Z value for bounding the plot.
            max_x (float): The maximum X value for bounding the plot.
            max_y (float): The maximum Y value for bounding the plot.
            max_z (float): The maximum Z value for bounding the plot.
            color (str): The color to use for the building parts.

        Returns:
            tuple: Updated bounding box values (min_x, min_y, min_z, max_x, max_y, max_z).
        """
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Ground', []), color, min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Wall', []), color, min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Roof', []), color, min_x, min_y, min_z, max_x, max_y, max_z)

        return min_x, min_y, min_z, max_x, max_y, max_z

    def plot_geometry(self, ax, geoms, color, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        Plots the geometry in the 3D plot and updates the bounds.

        Args:
            ax (Axes3D): The 3D axes object.
            geoms (list or shapely.geometry): A list of geometries or a single geometry.
            color (str): The color to use for the geometry.
            min_x (float): The minimum X value for bounding the plot.
            min_y (float): The minimum Y value for bounding the plot.
            min_z (float): The minimum Z value for bounding the plot.
            max_x (float): The maximum X value for bounding the plot.
            max_y (float): The maximum Y value for bounding the plot.
            max_z (float): The maximum Z value for bounding the plot.

        Returns:
            tuple: Updated bounding box values (min_x, min_y, min_z, max_x, max_y, max_z).
        """
        if isinstance(geoms, (Polygon, MultiPolygon)):
            geoms = [geoms]

        for geom in geoms:
            if geom:
                if geom.geom_type == 'Polygon':
                    x, y, z = zip(*geom.exterior.coords)
                    verts = [list(zip(x, y, z))]
                    poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                    ax.add_collection3d(poly_collection)
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y, z = zip(*poly.exterior.coords)
                        verts = [list(zip(x, y, z))]
                        poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                        ax.add_collection3d(poly_collection)

                # Update bounds
                min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))

        return min_x, min_y, min_z, max_x, max_y, max_z

    def highlight_building_3d(self, parent_id):
        """
        Highlights a specific building in the 3D plot.

        Args:
            parent_id (str): The ID of the building to highlight.
        """
        # Check if the building is already highlighted
        if self.highlighted_building_id == parent_id:
            # Deselect the building by setting the highlighted_building_id to None
            self.highlighted_building_id = None
        else:
            # Highlight the new building
            self.highlighted_building_id = parent_id

        # Re-render the 3D view with the updated highlight
        self.update_3d_view(self.building_data)