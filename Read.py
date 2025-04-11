import os
from PyQt6 import QtWidgets, QtCore, QtGui
from ReadThread import ReadThread
from common import get_resource_path

class Read(QtWidgets.QWidget):
    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.thread = None
        self.layout_config = {
            "gridLayout_5": {"counter": 0, "items": [], "layout": parent.gridLayout_5},
            "gridLayout_4": {"counter": 0, "items": [], "layout": parent.gridLayout_4},
            "gridLayout_3": {"counter": 0, "items": [], "layout": parent.gridLayout_3}
        }
        self.init_ui()

    def init_ui(self):
        self.parent.toolButton_startRecognition.clicked.connect(self.toggle_processing)
        self.parent.progressBar_Recognition.setRange(0, 100)
        self.parent.progressBar_Recognition.setValue(0)

    def toggle_processing(self):
        if self.thread and self.thread.isRunning():
            self._stop_processing()
        else:
            self._start_processing()

    def _start_processing(self):
        if not self.folder_page or not (folders := self.folder_page.get_all_folders()):
            QtWidgets.QMessageBox.warning(self, "警告", "请先选择文件夹")
            return

        self.parent.progressBar_Recognition.setValue(0)
        self.parent.toolButton_startRecognition.setText("停止")

        self.thread = ReadThread(folders)
        self.thread.image_loaded.connect(self.handle_image_loaded)
        self.thread.finished.connect(self._on_finished)
        self.thread.progress_updated.connect(self._update_progress)
        self.thread.start()

    def _stop_processing(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait()
            self._reset_ui()

    def _on_finished(self):
        self._reset_ui()
        self.parent.progressBar_Recognition.setValue(100)

    def _reset_ui(self):
        self.parent.toolButton_startRecognition.setText("开始")
        self.parent.progressBar_Recognition.setValue(0)

    def _update_progress(self, value):
        self.parent.progressBar_Recognition.setValue(value)

    def handle_image_loaded(self, path, layout):
        self.add_item(path, layout)

    def create_item_widget(self, path, layout_name):
        item_frame = QtWidgets.QFrame(parent=self.parent.scrollAreaWidgetContents_image)
        item_frame.setFixedSize(QtCore.QSize(120, 145))
        item_frame.setStyleSheet(self.get_frame_style())

        vertical_layout = QtWidgets.QVBoxLayout(item_frame)
        vertical_layout.setContentsMargins(0, 0, 0, 0)
        vertical_layout.setSpacing(0)

        image_widget = self.create_image_widget(path)
        text_label = self.create_text_label(path)

        vertical_layout.addWidget(image_widget, stretch=7)
        vertical_layout.addWidget(text_label, stretch=1)

        return item_frame

    @staticmethod
    def get_frame_style():
        return """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F8F8F8);
                border: 1px solid #E5E5E5;
                border-radius: 12px;
                padding: 4px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
            }
            QFrame:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F8F8F8, stop:1 #F0F0F0);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12); }
            QFrame:pressed { background: #F0F0F0; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }
        """

    def create_image_widget(self, path):
        image_widget = QtWidgets.QWidget()
        image_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred
        )
        image_widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        image_widget.setStyleSheet(f"""
            background-color: transparent;
            image: url({get_resource_path(path)});
            border-radius: 0px;
        """)
        return image_widget

    def create_text_label(self, path):
        filename = os.path.splitext(os.path.basename(path))[0] if path else "Item Name"
        text_label = QtWidgets.QLabel(self._truncate_filename(filename))
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
        return text_label

    @staticmethod
    def _truncate_filename(filename, max_length=9):
        if len(filename) > max_length:
            return f"{filename[:3]}...{filename[-6:]}" if len(filename) > 9 else filename
        return filename

    def add_item(self, path=None, layout="gridLayout_5"):
        config = self.layout_config.get(layout)
        if not config:
            return

        item_frame = self.create_item_widget(path or 'resources/img/page_1/示例.svg', layout)
        row, column = divmod(config["counter"], 4)
        config["layout"].addWidget(item_frame, row, column)
        config["counter"] += 1
        config["items"].append(item_frame)
        self.parent.update_empty_status(layout, has_content=True)
