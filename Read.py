import os
from PyQt6 import QtWidgets, QtCore, QtGui
from ReadThread import ReadThread
from common import get_resource_path

class Read(QtWidgets.QWidget):
    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.current_items = {}
        self.item_counter = 0
        self.thread = None
        self.init_page()

    def init_page(self):
        self.parent.toolButton_startRecognition.clicked.connect(self.toggle_processing)
        self.parent.progressBar_Recognition.setRange(0, 100)
        self.parent.progressBar_Recognition.setValue(0)

    def toggle_processing(self):
        if self.thread and self.thread.isRunning():
            self._stop_processing()
        else:
            self._start_processing()

    def _start_processing(self):
        folders = self.folder_page.get_all_folders() if self.folder_page else []
        if not folders:
            return

        self.parent.progressBar_Recognition.setValue(0)
        self.parent.toolButton_startRecognition.setText("停止")

        self.thread = ReadThread(folders)
        self.thread.image_loaded.connect(self.receive)
        self.thread.finished.connect(self._on_finished)
        self.thread.progress_updated.connect(self._update_progress)
        self.thread.start()

    def _stop_processing(self):
        if self.thread:
            self.thread.stop()
            self.parent.toolButton_startRecognition.setText("开始")
            self.parent.progressBar_Recognition.setValue(0)

    def _on_finished(self):
        self.parent.toolButton_startRecognition.setText("开始")
        self.parent.progressBar_Recognition.setValue(100)

    def _update_progress(self, value):
        self.parent.progressBar_Recognition.setValue(value)

    def receive(self, path, layout):
        self.add_item(path, layout=layout)

    def add_item(self, path=None, layout="gridLayout_5"):
        if path:
            path = get_resource_path(path)
        else:
            path = get_resource_path('resources/img/page_1/示例.svg')
        layout_name = layout
        if layout_name == "gridLayout_5":
            target_layout = self.parent.gridLayout_5
        elif layout_name == "gridLayout_4":
            target_layout = self.parent.gridLayout_4
        elif layout_name == "gridLayout_3":
            target_layout = self.parent.gridLayout_3
        else:
            return
        item_frame = QtWidgets.QFrame(parent=self.parent.scrollAreaWidgetContents_image)
        item_frame.setMinimumSize(QtCore.QSize(120, 145))
        item_frame.setMaximumSize(QtCore.QSize(120, 145))
        item_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F8F8F8);
                border: 1px solid #E5E5E5;
                border-radius: 12px;
                padding: 4px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
            }
            QFrame:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F8F8F8, stop:1 #F0F0F0);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
            }
            QFrame:pressed {
                background: #F0F0F0;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
        """)
        vertical_layout = QtWidgets.QVBoxLayout(item_frame)
        vertical_layout.setContentsMargins(0, 0, 0, 0)
        vertical_layout.setSpacing(0)
        image_widget = QtWidgets.QWidget(parent=item_frame)
        image_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred
        )
        image_widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        image_widget.setStyleSheet(f"""
            background-color: transparent;
            image: url({path});
            border-radius: 0px;
        """)
        text_label = QtWidgets.QLabel(parent=item_frame)
        text_label.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        text_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                font-size: 14px;
                color: #333333;
                padding: 0px;
                border: none;
                qproperty-alignment: AlignCenter;
            }
        """)
        filename = os.path.splitext(path.split("/")[-1])[0] if path else "Item Name"
        if len(filename) > 9:
            filename = filename[:3] + '...' + filename[-6:]
        text_label.setText(filename)
        vertical_layout.addWidget(image_widget)
        vertical_layout.addWidget(text_label)
        vertical_layout.setStretch(0, 7)
        vertical_layout.setStretch(1, 1)
        row = self.item_counter // 4
        column = self.item_counter % 4
        target_layout.addWidget(item_frame, row, column)
        self.item_counter += 1
        if layout_name not in self.current_items:
            self.current_items[layout_name] = []
        self.current_items[layout_name].append(item_frame)
        self.parent.update_empty_status(layout_name, has_content=True)