from PyQt6 import QtWidgets, QtCore, QtGui

from ReadThread import ReadThread


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


class Read(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.items = []
        self.image_grid = parent.gridLayout_5
        self.video_grid = parent.gridLayout_4
        self.read_thread = None

        parent.toolButton_startRecognition.clicked.connect(self.start_loading_images)
        self.parent.update_empty_status("gridLayout_5", False)
        self.parent.update_empty_status("gridLayout_4", False)

    def start_loading_images(self):
        self.clear_items()
        self.read_thread = ReadThread("resources/example")
        self.read_thread.image_loaded.connect(self.add_image_item)
        self.read_thread.finished_loading.connect(self.on_loading_finished)
        self.read_thread.start()

    def add_image_item(self, image_path, text):
        item = ExplorerItem(image_path, text, self)
        row = len(self.items) // 4
        col = len(self.items) % 4
        self.image_grid.addWidget(item, row, col)
        self.items.append(item)
        item.remove_requested.connect(self.remove_item)
        self.parent.update_empty_status("gridLayout_5", True)

    def on_loading_finished(self):
        if self.read_thread:
            self.read_thread.stop()
            self.read_thread = None

    def remove_item(self, item):
        if item in self.items:
            if self.image_grid.indexOf(item) != -1:
                self.image_grid.removeWidget(item)
                self.parent.update_empty_status("gridLayout_5", len(self.items) > 1)
            elif self.video_grid.indexOf(item) != -1:
                self.video_grid.removeWidget(item)
                self.parent.update_empty_status("gridLayout_4", len(self.items) > 1)

            self.items.remove(item)
            item.deleteLater()
            self._rearrange_items()

    def clear_items(self):
        def clear_grid(grid):
            while grid.count():
                item = grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        clear_grid(self.image_grid)
        clear_grid(self.video_grid)
        self.items.clear()
        self.parent.update_empty_status("gridLayout_5", False)
        self.parent.update_empty_status("gridLayout_4", False)

    def _rearrange_items(self):
        items_in_image_grid = []
        items_in_video_grid = []

        for item in self.items:
            if self.image_grid.indexOf(item) != -1:
                items_in_image_grid.append(item)
            elif self.video_grid.indexOf(item) != -1:
                items_in_video_grid.append(item)

        self._clear_and_populate_grid(self.image_grid, items_in_image_grid)
        self._clear_and_populate_grid(self.video_grid, items_in_video_grid)

        self.parent.update_empty_status("gridLayout_5", len(items_in_image_grid) > 0)
        self.parent.update_empty_status("gridLayout_4", len(items_in_video_grid) > 0)

    def _clear_and_populate_grid(self, grid, items):
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for i, item in enumerate(items):
            row = i // 4
            col = i % 4
            grid.addWidget(item, row, col)