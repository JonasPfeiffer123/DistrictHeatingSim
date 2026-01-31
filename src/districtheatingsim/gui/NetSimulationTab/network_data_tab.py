"""Network Data Tab Module
=======================

Tab for network data file selection and preview visualization.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os

import geopandas as gpd
from shapely import Point

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QComboBox, QWidget, \
    QPushButton, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

class NetworkDataTab(QWidget):
    """
    Widget for selecting network data files and previewing GeoJSON data.
    """
    
    def __init__(self, base_path, dialog_config, parent=None):
        """
        Initialize network data tab.

        :param base_path: Base path for file operations.
        :type base_path: str
        :param dialog_config: Configuration data.
        :type dialog_config: dict
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.base_path = base_path
        self.dialog_config = dialog_config
        self.parent = parent
        self.initUI()

    def initUI(self):
        """
        Initialize user interface components.
        """
        layout = QVBoxLayout(self)

        importGroup = QGroupBox("Import Netzdaten und Wärmebedarfsrechnung")
        importGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        importLayout = QVBoxLayout()
        importLayout.addWidget(QLabel("Importtyp Netz:"))
        self.importTypeComboBox = QComboBox()
        self.importTypeComboBox.addItems(["GeoJSON"])
        importLayout.addWidget(self.importTypeComboBox)
        self.importTypeComboBox.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        self.geojsonInputs = self.createGeojsonInputs()
        for input_layout in self.geojsonInputs:
            importLayout.addLayout(input_layout)

        jsonImportLayout = QHBoxLayout()
        jsonLabel = QLabel("JSON mit Daten:")
        jsonImportLayout.addWidget(jsonLabel)
        self.jsonLineEdit = QLineEdit(os.path.join(self.base_path, self.parent.parent.config_manager.get_relative_path('building_load_profile_path')))
        jsonImportLayout.addWidget(self.jsonLineEdit)
        jsonBrowseButton = QPushButton("Datei auswählen")
        jsonBrowseButton.clicked.connect(self.browseJsonFile)
        jsonImportLayout.addWidget(jsonBrowseButton)
        importLayout.addLayout(jsonImportLayout)

        importGroup.setLayout(importLayout)
        layout.addWidget(importGroup)

        DiagramsGroup = QGroupBox("Vorschau Netzdaten")
        DiagramsGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        DiagramsLayout = QVBoxLayout()

        self.figure1 = Figure()
        self.canvas1 = FigureCanvas(self.figure1)
        self.canvas1.setMinimumSize(350, 350)
        self.toolbar1 = NavigationToolbar(self.canvas1, self)

        DiagramsLayout.addWidget(self.canvas1)
        DiagramsLayout.addWidget(self.toolbar1)

        DiagramsGroup.setLayout(DiagramsLayout)
        layout.addWidget(DiagramsGroup)

        # Update der Sichtbarkeit
        self.updateInputFieldsVisibility()
        self.update_plot()

    def createGeojsonInputs(self):
        """
        Create GeoJSON file input layouts.

        :return: List of input layouts.
        :rtype: list
        """
        # Default path for unified network GeoJSON
        default_network_path = os.path.join(
            self.base_path, 
            self.parent.parent.config_manager.get_relative_path("dimensioned_net_path")
        )

        file_inputs_layout = self.createFileInputsGeoJSON(default_network_path)

        inputs = [
            file_inputs_layout
        ]
        return inputs

    def createFileInputsGeoJSON(self, default_network_path):
        """
        Create file input widget for unified network GeoJSON file.

        :param default_network_path: Default path to Wärmenetz.geojson.
        :type default_network_path: str
        :return: Layout containing file input.
        :rtype: QVBoxLayout
        """
        layout = QVBoxLayout()
        self.networkInput = self.createFileInput("Wärmenetz GeoJSON:", default_network_path)
        layout.addLayout(self.networkInput)

        return layout

    def createFileInput(self, label_text, default_text):
        """
        Create file input row with label, text field, and browse button.

        :param label_text: Label text.
        :type label_text: str
        :param default_text: Default file path.
        :type default_text: str
        :return: Layout containing file input components.
        :rtype: QHBoxLayout
        """
        layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        button = QPushButton("Datei auswählen")
        button.clicked.connect(lambda: self.selectFilename(line_edit))
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def browseJsonFile(self):
        """
        Open file dialog for JSON file selection.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', os.path.join(self.base_path, self.parent.parent.config_manager.get_relative_path('building_load_profile_path')), 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.jsonLineEdit.setText(fname)

    def selectFilename(self, line_edit):
        """
        Open file dialog and update line edit with selected file.

        :param line_edit: Line edit widget to update.
        :type line_edit: QLineEdit
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'All Files (*);;CSV Files (*.csv);;GeoJSON Files (*.geojson)')
        if fname:
            line_edit.setText(fname)
            self.update_plot()

    def update_plot(self):
        """
        Update plot visualization based on selected unified GeoJSON file.
        """
        try:
            # Import schema for feature type identification
            from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
            
            # Pfad auslesen
            network_path = self.networkInput.itemAt(1).widget().text()

            # Datei prüfen, ob sie existiert
            if not os.path.exists(network_path):
                raise FileNotFoundError("Die Wärmenetz GeoJSON-Datei wurde nicht gefunden.")
            
            # Datei einlesen
            network_gdf = gpd.read_file(network_path)
            
            # Separate features by type
            vorlauf = network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_FLOW]
            ruecklauf = network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_RETURN]
            hast = network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING]
            erzeugeranlagen = network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR]

            # Plot vorbereiten
            self.figure1.clear()
            ax = self.figure1.add_subplot(111)

            # GeoJSON-Daten plotten
            vorlauf.plot(ax=ax, color='red')
            ruecklauf.plot(ax=ax, color='blue')
            hast.plot(ax=ax, color='green')
            erzeugeranlagen.plot(ax=ax, color='black')

            # Annotations vorbereiten
            annotations = []
            for idx, row in hast.iterrows():
                point = row['geometry'].representative_point()
                
                # Access building data from nested structure
                building_data = row.get('building_data', {})
                if isinstance(building_data, dict):
                    adresse = building_data.get('Adresse', 'N/A')
                    waermebedarf = building_data.get('Wärmebedarf', 'N/A')
                    gebaeudetyp = building_data.get('Gebäudetyp', 'N/A')
                    vlt_max = building_data.get('VLT_max', 'N/A')
                    rlt_max = building_data.get('RLT_max', 'N/A')
                else:
                    # Fallback if data structure is different
                    adresse = 'N/A'
                    waermebedarf = 'N/A'
                    gebaeudetyp = 'N/A'
                    vlt_max = 'N/A'
                    rlt_max = 'N/A'
                
                label = (f"{adresse}\nWärmebedarf: {waermebedarf}\n"
                        f"Gebäudetyp: {gebaeudetyp}\nVLT_max: {vlt_max}\nRLT_max: {rlt_max}")
                annotation = ax.annotate(label, xy=(point.x, point.y), xytext=(10, 10),
                                        textcoords="offset points", bbox=dict(boxstyle="round", fc="w"))
                annotation.set_visible(False)
                annotations.append((point, annotation))

            # Event-Handler für Mausbewegung
            def on_move(event):
                if event.xdata is None or event.ydata is None:
                    return

                visibility_changed = False
                for point, annotation in annotations:
                    should_be_visible = (point.distance(Point(event.xdata, event.ydata)) < 5)
                    if should_be_visible != annotation.get_visible():
                        visibility_changed = True
                        annotation.set_visible(should_be_visible)

                if visibility_changed:
                    self.canvas1.draw()

            # Maus-Bewegung-Event verbinden
            self.figure1.canvas.mpl_connect('motion_notify_event', on_move)

            ax.set_title('Visualisierung der GeoJSON-Netz-Daten')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')

        except FileNotFoundError as e:
            # Fehlermeldung anzeigen, wenn Dateien fehlen
            self.figure1.clear()
            ax = self.figure1.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available', fontsize=20, ha='center')
            self.canvas1.draw()

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Dateien nicht gefunden")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Fehler")
            msg.exec()

        except Exception as e:
            # Allgemeine Fehlermeldung bei anderen Fehlern
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Ein Fehler ist aufgetreten")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Fehler")
            msg.exec()

    def set_layout_visibility(self, layout, visible):
        """
        Set visibility of all widgets in a layout.

        :param layout: Layout to update.
        :type layout: QLayout
        :param visible: Visibility state.
        :type visible: bool
        """
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setVisible(visible)
            elif item.layout():
                self.set_layout_visibility(item.layout(), visible)

    def set_default_value(self, parameter_row, value):
        """
        Set default value for a parameter row.

        :param parameter_row: Parameter row layout.
        :type parameter_row: QHBoxLayout
        :param value: Default value to set.
        :type value: str
        """
        # Zugriff auf das QLineEdit Widget in der Parameterzeile und Aktualisieren des Textes
        for i in range(parameter_row.count()):
            widget = parameter_row.itemAt(i).widget()
            if isinstance(widget, QLineEdit):
                widget.setText(value)
                break  # Beendet die Schleife, sobald das QLineEdit gefunden und aktualisiert wurde

    def updateInputFieldsVisibility(self):
        """
        Update visibility of input fields based on selected options.
        """
        is_geojson = self.importTypeComboBox.currentText() == "GeoJSON"

        # GeoJSON-spezifische Eingabefelder
        for input_layout in self.geojsonInputs:
            self.set_layout_visibility(input_layout, is_geojson)