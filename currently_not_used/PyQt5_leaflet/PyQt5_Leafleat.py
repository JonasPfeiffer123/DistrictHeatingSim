import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Leaflet.draw in PyQt5')
        self.setGeometry(100, 100, 1000, 800)

        # Create a QWebEngineView to display the HTML map
        self.web_view = QWebEngineView()

        # Path to the local HTML file (make sure it's the correct path)
        map_file_path = os.path.join(os.getcwd(), 'currently_not_used\\PyQt5_leaflet\\map.html')

        print(map_file_path)

        # Load the HTML file in the QWebEngineView
        self.web_view.setUrl(QUrl.fromLocalFile(map_file_path))

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)

        # Create a central widget and set the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Add buttons for importing and exporting GeoJSON
        export_button = QPushButton('Export GeoJSON')
        export_button.clicked.connect(self.export_geojson)
        layout.addWidget(export_button)

        import_button = QPushButton('Import GeoJSON')
        import_button.clicked.connect(self.import_geojson)
        layout.addWidget(import_button)

    def export_geojson(self):
        # Run JavaScript in the embedded page to export GeoJSON and capture the result
        self.web_view.page().runJavaScript("window.exportGeoJSON()", self.handle_geojson)

    def handle_geojson(self, geojson_data):
        # This will print the GeoJSON data that was returned from JavaScript
        print("Exported GeoJSON:", geojson_data)

    def import_geojson(self):
        # Open a file dialog to select a GeoJSON file
        options = QFileDialog.Options()
        geojson_file, _ = QFileDialog.getOpenFileName(self, 'Open GeoJSON File', '', 'GeoJSON Files (*.geojson)', options=options)
        
        if geojson_file:
            # Read the GeoJSON file content
            with open(geojson_file, 'r') as f:
                geojson_data = json.load(f)

            # Pass the GeoJSON data to the map in the JavaScript context
            geojson_str = json.dumps(geojson_data)  # Convert to string
            self.web_view.page().runJavaScript(f"window.importGeoJSON({geojson_str});")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec_())
