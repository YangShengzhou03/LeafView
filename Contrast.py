from PyQt6 import QtWidgets, QtCore


class Contrast(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_page()

    def init_page(self):
        self.parent.horizontalSlider_levelContrast.setRange(1, 4)
        self.parent.horizontalSlider_levelContrast.setSingleStep(1)
        self.parent.horizontalSlider_levelContrast.setTickInterval(1)
        self.parent.horizontalSlider_levelContrast.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.parent.horizontalSlider_levelContrast.setValue(4)
        self.parent.label_levelContrast.setText("完全一致")
        self.parent.label_levelContrast.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.parent.label_levelContrast.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #4CAF50;
            }
        """)
        self.parent.verticalFrame_similar.hide()
        self.connect_signals()

    def connect_signals(self):
        self.parent.horizontalSlider_levelContrast.valueChanged.connect(self.on_slider_value_changed)
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)

    def startContrast(self):
        self.parent.verticalFrame_similar.show()

    @QtCore.pyqtSlot(int)
    def on_slider_value_changed(self, value):
        texts = ["明显差异", "部分相似", "比较相似", "完全一致"]
        if 1 <= value <= 4:
            self.parent.label_levelContrast.setText(texts[value - 1])
            colors = ["#FF5252", "#FF9800", "#2196F3", "#4CAF50"]
            self.parent.label_levelContrast.setStyleSheet(f"""
                QLabel {{
                    font-size: 18px;
                    color: {colors[value - 1]};
                }}
            """)
