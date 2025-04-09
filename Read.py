from PyQt6 import QtWidgets, QtCore, QtGui


class Read(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.items = []
        self.grid_layout = parent.gridLayout_7
        parent.toolButton_startRecognition.clicked.connect(self.add_item)
        self.parent.update_empty_status("gridLayout_7", False)

    def add_item(self):
        text = f"项目 {len(self.items) + 1}"
        item = ExplorerItem("resources/example/XX", text, self)
        row = len(self.items) // 4
        col = len(self.items) % 4
        self.grid_layout.addWidget(item, row, col)
        self.items.append(item)
        item.remove_requested.connect(self.remove_item)
        self.parent.update_empty_status("gridLayout_7", True)

    def remove_item(self, item):
        if item in self.items:
            self.grid_layout.removeWidget(item)
            self.items.remove(item)
            item.deleteLater()
            self._rearrange_items()
            self.parent.update_empty_status("gridLayout_7", len(self.items) > 0)

    def _rearrange_items(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for i, item in enumerate(self.items):
            row = i // 4
            col = i % 4
            self.grid_layout.addWidget(item, row, col)


class ExplorerItem(QtWidgets.QFrame):
    remove_requested = QtCore.pyqtSignal(object)

    def __init__(self, image_path, text, parent=None):
        super().__init__(parent)
        self.setFixedSize(146, 160)
        self.setup_ui(image_path, text)

    def setup_ui(self, image_path, text):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(120, 120)
        self._set_rounded_image(image_path)

        self.text_label = QtWidgets.QLabel(text)
        self.text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("font: 12pt 'Segoe UI'; color: #333;")

        self.remove_btn = QtWidgets.QPushButton("×")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.hide()
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.remove_btn)

        layout.addLayout(btn_layout)
        layout.addWidget(self.image_label)
        layout.addWidget(self.text_label)

        self._setup_styles()
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))

    def _setup_styles(self):
        self.setStyleSheet("""
            ExplorerItem {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
                transition: all 0.3s ease;
            }
            ExplorerItem:hover {
                background: #f9f9f9;
                border-color: #d0d0d0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            QLabel#image_label {
                border-radius: 10px;
                background: #f0f0f0;
            }
            QPushButton#remove_btn {
                border: none;
                background: transparent;
                color: #a0a0a0;
                font: bold 16px 'Arial';
                border-radius: 12px;
            }
            QPushButton#remove_btn:hover {
                color: #ffffff;
                background: #ff4d4f;
            }
            QPushButton#remove_btn:pressed {
                background: #cf1322;
            }
        """)
        self.image_label.setObjectName("image_label")
        self.text_label.setObjectName("text_label")
        self.remove_btn.setObjectName("remove_btn")

    def _set_rounded_image(self, image_path):
        pixmap = QtGui.QPixmap(image_path)
        if pixmap.isNull():
            pixmap = self._create_default_icon()
        else:
            pixmap = self._process_image(pixmap)
        self.image_label.setPixmap(pixmap)

    def _create_default_icon(self):
        pixmap = QtGui.QPixmap(120, 120)
        pixmap.fill(QtGui.QColor(240, 240, 240))
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(220, 220, 220)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 120, 120, 10, 10)
        painter.setPen(QtGui.QPen(QtGui.QColor(160, 160, 160), 1))
        font = painter.font()
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "图片")
        painter.end()
        return pixmap

    def _process_image(self, pixmap):
        pixmap = pixmap.scaled(140, 140,
                               QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                               QtCore.Qt.TransformationMode.SmoothTransformation)
        rounded = QtGui.QPixmap(140, 140)
        rounded.fill(QtGui.QColor("transparent"))
        painter = QtGui.QPainter(rounded)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        x = (140 - pixmap.width()) // 2
        y = (140 - pixmap.height()) // 2
        path = QtGui.QPainterPath()
        path.addRoundedRect(0, 0, 140, 140, 10, 10)
        painter.setClipPath(path)
        painter.drawPixmap(x, y, pixmap)
        painter.end()
        return rounded

    def enterEvent(self, event):
        self.remove_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.remove_btn.hide()
        super().leaveEvent(event)

