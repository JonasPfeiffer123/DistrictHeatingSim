import sys

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel, QApplication
from schematic_scene import SchematicScene, CustomGraphicsView

class SchematicWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up main window
        self.setWindowTitle('Complex Heat Generator Schematic')
        self.setGeometry(100, 100, 1000, 1000)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        main_layout = QVBoxLayout(self.centralWidget)

        layout = QHBoxLayout()

        # Instantiate SchematicScene (now decoupled from the window)
        self.scene = SchematicScene(1000, 1000)
        self.view = CustomGraphicsView(self.scene)  # Use custom view with zoom and pan functionality
        layout.addWidget(self.view)

        # Button panel for UI
        button_layout = QVBoxLayout()
        self.add_solar_button = QPushButton("Add Solar")
        self.add_chp_button = QPushButton("Add CHP")
        self.add_solar_storage_button = QPushButton("Add Solar + Storage")
        self.add_chp_storage_button = QPushButton("Add CHP + Storage")
        self.add_consumer_button = QPushButton("Add Consumer")
        button_layout.addWidget(self.add_solar_button)
        button_layout.addWidget(self.add_chp_button)
        button_layout.addWidget(self.add_solar_storage_button)
        button_layout.addWidget(self.add_chp_storage_button)
        button_layout.addWidget(self.add_consumer_button)

        layout.addLayout(button_layout)
        main_layout.addLayout(layout)

        self.mouse_label = QLabel("Mouse Coordinates: x = 0, y = 0")
        main_layout.addWidget(self.mouse_label)

        # Button signals
        self.add_solar_button.clicked.connect(self.scene.add_solar)
        self.add_chp_button.clicked.connect(self.scene.add_chp)
        self.add_solar_storage_button.clicked.connect(self.scene.add_solar_storage)
        self.add_chp_storage_button.clicked.connect(self.scene.add_chp_storage)
        self.add_consumer_button.clicked.connect(self.scene.add_consumer)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SchematicWindow()
    window.show()
    sys.exit(app.exec_())
