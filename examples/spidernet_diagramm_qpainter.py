from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt
import sys
import math

class SpiderDiagram(QWidget):
    def __init__(self, labels, values):
        super().__init__()
        self.labels = labels  # Die Achsenbeschriftungen
        self.values = values  # Die Werte (normiert auf 0-1)
        self.setWindowTitle("Spinnennetz-Diagramm")
        self.setMinimumSize(400, 400)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Mittelpunkt des Diagramms
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(self.width(), self.height()) // 3

        # Achsen zeichnen
        num_axes = len(self.labels)
        angle_step = 2 * math.pi / num_axes

        for i in range(num_axes):
            angle = i * angle_step
            end_x = center_x + radius * math.cos(angle)
            end_y = center_y - radius * math.sin(angle)

            # Achse zeichnen
            painter.setPen(QPen(Qt.black, 1))
            painter.drawLine(int(center_x), int(center_y), int(end_x), int(end_y))

            # Label hinzufügen
            label_x = center_x + (radius + 20) * math.cos(angle)
            label_y = center_y - (radius + 20) * math.sin(angle)
            painter.drawText(int(label_x) - 10, int(label_y) + 5, self.labels[i])

        # Hintergrundgitter zeichnen
        for r in range(1, 6):  # 5 konzentrische Kreise
            step_radius = radius * r / 5
            painter.setPen(QPen(Qt.gray, 1, Qt.DotLine))
            painter.drawEllipse(int(center_x - step_radius), int(center_y - step_radius),
                                int(2 * step_radius), int(2 * step_radius))

        # Werte zeichnen
        points = []
        for i, value in enumerate(self.values):
            angle = i * angle_step
            value_x = center_x + radius * value * math.cos(angle)
            value_y = center_y - radius * value * math.sin(angle)
            points.append((int(value_x), int(value_y)))

        # Punkte verbinden
        painter.setPen(QPen(Qt.red, 2))
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            painter.drawLine(x1, y1, x2, y2)

        # Punkte markieren
        painter.setBrush(Qt.red)
        for x, y in points:
            painter.drawEllipse(x - 5, y - 5, 10, 10)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    labels = ["A", "B", "C", "D", "E"]  # Beschriftung der Achsen
    values = [0.8, 0.6, 0.9, 0.4, 0.7]  # Normierte Werte (zwischen 0 und 1)
    window = SpiderDiagram(labels, values)
    window.show()
    sys.exit(app.exec())
