from datetime import datetime

from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QFileDialog

from Thread import ImageOrganizerThread


class Arrange(QtWidgets.QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.custom_folder_path = None
        self.organizer_thread = None
        self.init_page()

    def init_page(self):
        self.connect_signals()
        self.initialize_comboboxes()
        self.setup_tool_button()
        self.on_log_message(
            ' 欢迎使用 LeafView 分类整理功能！导入文件夹并在上方定义目录结构后，LeafView 将依据 EXIF 数据自动整理媒体文件。',
            'INFO'
        )
        self.on_log_message(
            '默认情况下，文件将在原目录中被移动；如需复制到新路径，请选择“在新路径下分类”。',
            'WARNING'
        )

    def connect_signals(self):
        for i in range(1, 6):
            comboBox_name = f'comboBox_level_{i}'
            if hasattr(self.parent, comboBox_name):
                getattr(self.parent, comboBox_name).currentIndexChanged.connect(
                    lambda index, level=i: self.update_combobox_state(level))

        self.parent.toolButton_StartOrganize.clicked.connect(self.toggle_organizing)
        self.parent.checkBox_newDirectory.clicked.connect(self.on_checkbox_state_changed)

    def initialize_comboboxes(self):
        for i in range(1, 6):
            comboBox = getattr(self.parent, f'comboBox_level_{i}', None)
            if comboBox:
                comboBox.setEnabled(i == 1)
                comboBox.setCurrentIndex(0 if i != 1 else comboBox.currentIndex())
        self.update_classification_label()

    def setup_tool_button(self):
        self.parent.toolButton_StartOrganize.setText("开始整理")

    def on_checkbox_state_changed(self, state):
        if state:
            folder_path = self.open_folder_dialog()
            if folder_path:
                self.custom_folder_path = folder_path
                self.parent.label_level_A.setText(folder_path)
                self.parent.label_level_1.setText('自定义目录')
            else:
                self.parent.checkBox_newDirectory.blockSignals(True)
                self.parent.checkBox_newDirectory.setChecked(False)
                self.parent.checkBox_newDirectory.blockSignals(False)
        else:
            self.custom_folder_path = None
            self.parent.label_level_A.setText('原文件夹路径')
            self.parent.label_level_1.setText('原文件目录')

    def open_folder_dialog(self):
        return QFileDialog.getExistingDirectory(self, "选择文件夹") or None

    def start_organizing(self):
        if not self.parent.imported_folders:
            self.on_log_message('您还未导入文件夹,请先导入', 'ERROR')
            return

        classification_structure = [
            getattr(self.parent, f'comboBox_level_{i}').currentText()
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]

        time_derive_option = self.parent.comboBox_timeDerive.currentText()

        destination_root = self.custom_folder_path if self.custom_folder_path else None

        self.organizer_thread = ImageOrganizerThread(
            parent=self,
            folders=self.parent.imported_folders,
            classification_structure=classification_structure,
            destination_root=destination_root,
            time_derive=time_derive_option
        )
        self.organizer_thread.progress_value.connect(self.update_progress_bar)
        self.organizer_thread.log_signal.connect(self.on_log_message)
        self.organizer_thread.finished.connect(self.on_finished)
        self.organizer_thread.start()
        self.parent.toolButton_StartOrganize.setText("停止整理")
        self.parent.toolButton_StartOrganize.setEnabled(True)

    def stop_organizing(self):
        if self.organizer_thread and self.organizer_thread.isRunning():
            self.organizer_thread.stop()
            self.organizer_thread.wait()
            self.parent.toolButton_StartOrganize.setText("开始整理")
            self.parent.toolButton_StartOrganize.setEnabled(True)
            self.on_log_message("整理任务已停止", "INFO")

    def toggle_organizing(self):
        if not self.organizer_thread or not self.organizer_thread.isRunning():
            self.start_organizing()
        else:
            self.stop_organizing()

    def update_progress_bar(self, value):
        self.parent.progressBar_Classification.setValue(value)

    def update_combobox_state(self, level):
        current_box = getattr(self.parent, f'comboBox_level_{level}')
        next_box = getattr(self.parent, f'comboBox_level_{level + 1}', None) if level < 5 else None

        is_not_classified = current_box.currentIndex() == 0

        if next_box:
            next_box.setEnabled(not is_not_classified)
            if is_not_classified:
                next_box.setCurrentIndex(0)
                for i in range(level + 1, 6):
                    future_box = getattr(self.parent, f'comboBox_level_{i}', None)
                    if future_box:
                        future_box.setEnabled(False)
                        future_box.setCurrentIndex(0)
            else:
                self.update_combobox_state(level + 1)

        self.update_classification_label()

    def update_classification_label(self):
        path_parts = [
            self.get_specific_value(getattr(self.parent, f'comboBox_level_{i}').currentText())
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]
        self.parent.label_classification_EX.setText('/'.join(path_parts))

    def get_specific_value(self, text):
        now = datetime.now()
        specific_values = {
            "年份": str(now.year),
            "月份": str(now.month),
            "拍摄设备": " Xiaomi ",
            "拍摄省份": " 江西省 ",
            "拍摄城市": " 南昌市 "
        }
        return specific_values.get(text, text)

    def append_log(self, message):
        cursor = self.parent.textEdit_Classification_Log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.parent.textEdit_Classification_Log.setTextCursor(cursor)
        self.parent.textEdit_Classification_Log.insertHtml(message)
        self.parent.textEdit_Classification_Log.ensureCursorVisible()

    def on_log_message(self, message, level):
        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
        formatted_message = f'[{timestamp}] [{level.upper()}]: {message}<br>'
        colors = {"INFO": "#691bfd", "WARNING": "#FFA500", "ERROR": "#FF0000", "DEBUG": "#00CC33"}
        color = colors.get(level.upper(), "#00CC33")
        formatted_message = f'<span style="color:{color}"> {formatted_message}</span>'
        self.append_log(formatted_message)

    def on_finished(self):
        self.parent.toolButton_StartOrganize.setText("开始整理")
        self.parent.toolButton_StartOrganize.setEnabled(True)
        self.on_log_message("整理任务执行完毕", "DEBUG")
