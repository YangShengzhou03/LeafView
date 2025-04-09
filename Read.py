from PyQt6 import QtWidgets

from common import author


class Read(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.items = []
        self.grid_layout = parent.gridLayout_7
        parent.toolButton_startRecognition.clicked.connect(author)
