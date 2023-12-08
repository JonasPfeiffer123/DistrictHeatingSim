import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setzen Sie den Titel und die Anfangsgröße des Hauptfensters
        self.setWindowTitle("PyQt Erste Anwendung")
        self.setGeometry(100, 100, 280, 80)

        # Erstellen und Konfigurieren von Widgets
        self.label = QLabel("Hallo, PyQt!")
        self.button = QPushButton("Klicken Sie hier")
        self.button.clicked.connect(self.on_button_clicked)

        # Erstellen eines Layouts und Hinzufügen der Widgets
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        # Erstellen eines zentralen Widgets
        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Festlegen des zentralen Widgets des Hauptfensters
        self.setCentralWidget(central_widget)

    def on_button_clicked(self):
        # Ändern des Textes im Label, wenn der Button geklickt wird
        self.label.setText("Button wurde geklickt!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
