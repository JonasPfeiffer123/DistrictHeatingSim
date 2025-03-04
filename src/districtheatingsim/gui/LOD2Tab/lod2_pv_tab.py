"""
Filename: lod2_pv_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-03
Description: Contains the LOD2PVTab as MVP structure.
"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QFileDialog, QWidget, QHeaderView, QHBoxLayout, QScrollArea, QMessageBox, QTreeWidget, QTreeWidgetItem)
class PVDataVisualizationTab(QWidget):
    """
    The view class for PV data visualization.
    """

    def __init__(self, parent=None):
        """
        Initializes the PVDataVisualizationTab with UI components.

        Args:
            parent (QWidget, optional): The parent widget.
        """
        super().__init__(parent)
        self.initUI()#

    def initUI(self):
        """
        Initializes the UI components of the PVDataVisualizationTab.
        """
        main_layout = QVBoxLayout(self)
        data_vis_layout = QHBoxLayout()
        main_layout.addLayout(data_vis_layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        data_vis_layout.addWidget(scroll_area)

        scroll_content = QWidget(scroll_area)
        scroll_area.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(scroll_content)

        self.treeWidget = QTreeWidget(self)
        self.treeWidget.setHeaderLabels(['Gebäude/Dach', 'Dachfläche (m²)', 'Dachneigung (°)', 'Dachausrichtung (°)', 'Yield (MWh)', 'Max Power (kW)'])
        # Automatically resize columns to fit their content
        self.treeWidget.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        scroll_layout.addWidget(self.treeWidget)

    def add_building(self, adresse, koordinate_x, koordinate_y):
        """Add a building entry to the tree view."""
        building_item = QTreeWidgetItem(self.treeWidget)
        building_item.setText(0, adresse)
        building_item.setText(1, f'UTM_X: {koordinate_x}, UTM_Y: {koordinate_y}')
        return building_item

    def add_roof(self, building_item, roof_area, roof_slope, roof_orientation, yield_MWh, max_power):
        """Add a roof entry under a building in the tree view."""
        roof_item = QTreeWidgetItem(building_item)
        roof_item.setText(0, 'Dach')
        roof_item.setText(1, f'{roof_area:.2f}')
        roof_item.setText(2, f'{roof_slope:.2f}')
        roof_item.setText(3, f'{roof_orientation:.2f}')
        roof_item.setText(4, f'{yield_MWh:.2f}')
        roof_item.setText(5, f'{max_power:.2f}')

    def display_data(self, building_info):
        """
        Display the loaded building data in the Tree View.
        
        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.treeWidget.clear()

        for parent_id, info in building_info.items():
            building_item = self.add_building(info['Adresse'], info['Koordinate_X'], info['Koordinate_Y'])
            if 'Roofs' in info:
                for roof in info['Roofs']:
                    roof_areas = roof['Area'] if isinstance(roof['Area'], list) else [roof['Area']]
                    roof_slopes = roof['Roof_Slope'] if isinstance(roof['Roof_Slope'], list) else [roof['Roof_Slope']]
                    roof_orientations = roof['Roof_Orientation'] if isinstance(roof['Roof_Orientation'], list) else [roof['Roof_Orientation']]

                    for i in range(len(roof_areas)):
                        self.add_roof(building_item, roof_areas[i], roof_slopes[i], roof_orientations[i], 0, 0)  # Initial yield and max power set to 0