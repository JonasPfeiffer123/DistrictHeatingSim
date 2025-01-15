import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyqtgraph as pg
import pyqtgraph.opengl as gl

class SpiderPlot(QWidget):
    def __init__(self, labels, values):
        super().__init__()
        self.labels = labels
        self.values = values
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        plot = pg.PlotWidget()
        plot.setAspectLocked()
        
        # Berechnung der Winkel für die Achsen
        angles = np.linspace(0, 2 * np.pi, len(self.labels), endpoint=False).tolist()
        angles += angles[:1]  # Zurück zum Startpunkt

        # Werte normalisieren und schließen
        values = self.values + self.values[:1]

        # Punkte für das Spinnennetz zeichnen
        x = [np.cos(a) * v for a, v in zip(angles, values)]
        y = [np.sin(a) * v for a, v in zip(angles, values)]
        plot.plot(x, y, pen=pg.mkPen(color='r', width=2), symbol='o', symbolSize=8)

        # Hintergrundgitter zeichnen
        for i in range(1, 6):
            r = i / 5.0  # Radius von 0.2 bis 1.0
            x = [np.cos(a) * r for a in angles]
            y = [np.sin(a) * r for a in angles]
            plot.plot(x, y, pen=pg.mkPen(color='gray', width=0.5))

        # Achsentitel hinzufügen
        for angle, label in zip(angles[:-1], self.labels):
            x = np.cos(angle) * 1.1  # Außerhalb des Diagramms
            y = np.sin(angle) * 1.1
            text_item = pg.TextItem(label, anchor=(0.5, 0.5), color='k')
            text_item.setPos(x, y)
            plot.addItem(text_item)


        layout.addWidget(plot)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    labels = ["A", "B", "C", "D", "E"]
    values = [0.8, 0.6, 0.9, 0.4, 0.7]
    window = SpiderPlot(labels, values)
    window.show()
    sys.exit(app.exec_())
