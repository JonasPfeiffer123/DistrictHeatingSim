from PyQt5.QtWidgets import QComboBox, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, pyqtSignal

class CheckableComboBox(QComboBox):
    checkedStateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        self.setView(QListView(self))
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        
        self.checkedStateChanged.emit()

    def itemChecked(self, index):
        item = self.model().item(index)
        return item.checkState() == Qt.Checked

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)
