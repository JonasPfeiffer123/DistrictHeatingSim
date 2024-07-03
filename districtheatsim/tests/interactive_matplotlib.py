import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QColorDialog)
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.canvas = FigureCanvas(Figure(figsize=(8, 6)))
        self.layout.addWidget(self.canvas)

        self.ax = self.canvas.figure.add_subplot(111)

        self.checkboxes_layout = QHBoxLayout()
        self.layout.addLayout(self.checkboxes_layout)

        self.checkboxes = {}
        self.colors = {}
        self.data = {
            'Dataset 1': np.random.rand(10),
            'Dataset 2': np.random.rand(10),
            'Dataset 3': np.random.rand(10)
        }

        for label in self.data.keys():
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.update_plot)
            self.checkboxes_layout.addWidget(checkbox)
            self.checkboxes[label] = checkbox

            color_button = QPushButton('Color')
            color_button.clicked.connect(lambda _, l=label: self.change_color(l))
            self.checkboxes_layout.addWidget(color_button)
            self.colors[label] = 'blue'

        self.update_plot()

    def update_plot(self):
        self.ax.clear()

        for label, data in self.data.items():
            if self.checkboxes[label].isChecked():
                self.ax.plot(data, label=label, color=self.colors[label])

        self.ax.legend()
        self.canvas.draw()

    def change_color(self, label):
        color = QColorDialog.getColor()

        if color.isValid():
            self.colors[label] = color.name()
            self.update_plot()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())