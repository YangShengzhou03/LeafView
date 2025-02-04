from datetime import datetime
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QTextCursor
from Thread import ConversionThread


class Convert(QtWidgets.QWidget):
    log_signal = QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.conversion_thread = None
        self.init_page()

    def init_page(self):
        self.connect_signals()
        self.on_log_message('欢迎使用 LeafView 格式转换功能！只需选择需要转换的文件和目标格式，LeafView 将自动完成转换。',
                            'INFO')
        self.on_log_message(
            '默认情况下，原格式文件会保存在当前目录的“转换前”文件夹中，转换后的文件会保存在当前目录的“转换后”文件夹中。',
            'WARNING')

    def connect_signals(self):
        self.parent.toolButton_Convert.clicked.connect(self.toggle_convert_process)
        self.log_signal.connect(self.on_log_message)

    def toggle_convert_process(self):
        button = self.parent.toolButton_Convert
        if button.text() == "开始转换":
            if not self.parent.imported_folders:
                self.on_log_message('您还未导入文件夹,请先导入', 'ERROR')
                return
            original_format = self.parent.comboBox_BeforeConversion.currentText().lower()
            target_format = self.parent.comboBox_AfterConversion.currentText().lower()
            if original_format == target_format:
                self.on_log_message('原格式与目标格式一致,无需转换', 'WARNING')
                return
            self.conversion_thread = ConversionThread(self.parent.imported_folders, original_format, target_format)
            self.conversion_thread.log_message.connect(self.on_log_message)
            self.conversion_thread.progress_updated.connect(self.update_progress_bar)
            self.conversion_thread.finished_conversion.connect(lambda: button.setText("开始转换"))
            self.conversion_thread.start()
            button.setText("停止转换")
        else:
            if self.conversion_thread and self.conversion_thread.isRunning():
                self.conversion_thread.requestInterruption()
                self.conversion_thread.quit()
                self.conversion_thread.wait()
            button.setText("开始转换")

    def update_progress_bar(self, value):
        self.parent.progressBar_Convert.setValue(value)

    def append_log(self, message):
        cursor = self.parent.textEdit_Convert_Log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.parent.textEdit_Convert_Log.setTextCursor(cursor)
        self.parent.textEdit_Convert_Log.insertHtml(message)
        self.parent.textEdit_Convert_Log.ensureCursorVisible()

    def on_log_message(self, message, level):
        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
        formatted_message = f'[{timestamp}] [{level.upper()}]: {message}<br>'
        colors = {"INFO": "#691bfd", "WARNING": "#FFA500", "ERROR": "#FF0000", "DEBUG": "#00CC33"}
        color = colors.get(level.upper(), "#00CC33")
        formatted_message = f'<span style="color:{color}"> {formatted_message}</span>'
        self.append_log(formatted_message)
