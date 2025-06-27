"""
LOD2 PV Tab Module
==================

Tab for visualizing PV data in tree view format.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-03
"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QFileDialog, QWidget, QHeaderView, QHBoxLayout, QScrollArea, QMessageBox, QTreeWidget, QTreeWidgetItem)

class PVDataVisualizationTab(QWidget):
    """
    Widget for PV data visualization in tree view format.
    """

    def __init__(self, parent=None):
        """
        Initialize PV data visualization tab.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
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
        self.treeWidget.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        scroll_layout.addWidget(self.treeWidget)

    def add_building(self, adresse, koordinate_x, koordinate_y):
        """
        Add building entry to tree view.

        Parameters
        ----------
        adresse : str
            Building address.
        koordinate_x : float
            X coordinate.
        koordinate_y : float
            Y coordinate.

        Returns
        -------
        QTreeWidgetItem
            Building tree item.
        """
        building_item = QTreeWidgetItem(self.treeWidget)
        building_item.setText(0, adresse)
        building_item.setText(1, f'UTM_X: {koordinate_x}, UTM_Y: {koordinate_y}')
        return building_item

    def add_roof(self, building_item, roof_area, roof_slope, roof_orientation, yield_MWh, max_power):
        """
        Add roof entry under building in tree view.

        Parameters
        ----------
        building_item : QTreeWidgetItem
            Parent building item.
        roof_area : float
            Roof area in m².
        roof_slope : float
            Roof slope in degrees.
        roof_orientation : float
            Roof orientation in degrees.
        yield_MWh : float
            PV yield in MWh.
        max_power : float
            Maximum power in kW.
        """
        roof_item = QTreeWidgetItem(building_item)
        roof_item.setText(0, 'Dach')
        roof_item.setText(1, f'{roof_area:.2f}')
        roof_item.setText(2, f'{roof_slope:.2f}')
        roof_item.setText(3, f'{roof_orientation:.2f}')
        roof_item.setText(4, f'{yield_MWh:.2f}')
        roof_item.setText(5, f'{max_power:.2f}')

    def display_data(self, building_info):
        """
        Display building data in tree view.
        
        Parameters
        ----------
        building_info : dict
            Building information dictionary.
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
                        self.add_roof(building_item, roof_areas[i], roof_slopes[i], roof_orientations[i], 0, 0)