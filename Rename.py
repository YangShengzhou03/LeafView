from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QTextCursor
from datetime import datetime
from Thread import RenameThread


class Rename(QtWidgets.QWidget):
    log_signal = QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_page()
        self.rename_thread = None
        self.is_running = False

    def init_page(self):
        self.connect_signals()
        self.on_log_message(
            '欢迎使用 LeafView 的智能重命名功能！您可以自定义文件名格式，LeafView 将根据图片的 EXIF 数据自动进行重命名。',
            'INFO'
        )
        self.on_log_message(
            '请注意：一旦开始重命名操作将无法撤销，请务必仔细检查设置以确保一切正确无误。',
            'WARNING'
        )

    def connect_signals(self):
        self.tag_buttons = {
            '年份': self.parent.pushButton_year,
            '月份': self.parent.pushButton_month,
            '日': self.parent.pushButton_date,
            '星期': self.parent.pushButton_day,
            '时间': self.parent.pushButton_time,
            '位置': self.parent.pushButton_address,
            '相机品牌': self.parent.pushButton_make,
            '相机型号': self.parent.pushButton_model
        }

        self.available_layout = self.parent.horizontalLayout_57
        self.selected_layout = self.parent.horizontalLayout_53

        for button in self.tag_buttons.values():
            button.clicked.connect(lambda checked, b=button: self.move_tag(b))
        self.parent.comboBox_Separator.currentIndexChanged.connect(self.update_example_label)
        self.last_selected_button_index = -1
        self.parent.toolButton_Startnaming.clicked.connect(self.toggle_rename_thread)

    def move_tag(self, button):
        current_layout = self.available_layout if self.available_layout.indexOf(button) != -1 else self.selected_layout

        if current_layout:
            current_layout.removeWidget(button)
            button.setParent(None)

        if current_layout == self.available_layout:
            self.selected_layout.addWidget(button)
            self.last_selected_button_index += 1
        else:
            self.available_layout.addWidget(button)
            self.last_selected_button_index -= 1

        self.update_example_label()

    def update_example_label(self):
        now = datetime.now()
        selected_buttons = [self.selected_layout.itemAt(i).widget().text()
                            for i in range(self.selected_layout.count())
                            if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]

        separator = self.get_separator()
        example_text = ""

        if not selected_buttons:
            example_text = "请点击标签以组成文件名"
        else:
            for button_text in selected_buttons:
                example_text += {
                    '年份': f"{now.year}{separator}",
                    '月份': f"{now.month:02d}{separator}",
                    '日': f"{now.day:02d}{separator}",
                    '星期': f"{self._get_weekday(now)}{separator}",
                    '时间': f"{now.strftime('%H%M')}{separator}",
                    '位置': f"江西科技师大{separator}",
                    '相机品牌': f"佳能{separator}",
                    '相机型号': f"M50{separator}"
                }.get(button_text, "")

            if example_text and (separator or example_text[-1] in " -_.=#~@"):
                example_text = example_text.rstrip(separator)

        self.parent.label_Rename_EX.setText(example_text)

    def get_separator(self):
        index = self.parent.comboBox_Separator.currentIndex()
        separators = ["-", "", " ", "_", ".", "=", "#", "~", "@"]
        return separators[index]

    @staticmethod
    def _get_weekday(date):
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays[date.weekday()]

    def append_log(self, message):
        cursor = self.parent.textEdit_Renaming_Log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.parent.textEdit_Renaming_Log.setTextCursor(cursor)
        self.parent.textEdit_Renaming_Log.insertHtml(message)
        self.parent.textEdit_Renaming_Log.ensureCursorVisible()

    def on_log_message(self, message, level):
        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
        formatted_message = f'[{timestamp}] [{level.upper()}]: {message}<br>'
        colors = {"INFO": "#691bfd", "WARNING": "#FFA500", "ERROR": "#FF0000", "DEBUG": "#00CC33"}
        color = colors.get(level.upper(), "#00CC33")
        formatted_message = f'<span style="color:{color}"> {formatted_message}</span>'
        self.append_log(formatted_message)

    def toggle_rename_thread(self):
        if self.is_running:
            self.stop_rename_thread()
        else:
            self.start_rename_thread()

    def start_rename_thread(self):
        if not self.parent.imported_folders:
            self.on_log_message('您还未导入文件夹，请先导入', 'ERROR')
            return
        time_derive_value = self.parent.comboBox_timing_source.currentText()
        selected_buttons = [
            self.selected_layout.itemAt(i).widget().text()
            for i in range(self.selected_layout.count())
            if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)
        ]
        if not selected_buttons:
            self.on_log_message('您还未构建文件名，请点击标签构建', 'ERROR')
            return
        separator = self.get_separator()
        folders_to_process = self.parent.imported_folders.copy()
        self.rename_thread = RenameThread(
            parent=self,
            selected_buttons=selected_buttons,
            separator=separator,
            folders=folders_to_process,
            time_derive=time_derive_value
        )
        self.rename_thread.log_signal.connect(self.on_log_message)
        self.rename_thread.finished.connect(self.on_rename_finished)
        self.rename_thread.update_progress_bar.connect(self.update_progress_bar)
        self.rename_thread.start()
        self.is_running = True
        self.parent.toolButton_Startnaming.setText("停止命名")

    def stop_rename_thread(self):
        if self.rename_thread is not None:
            self.rename_thread.stop()
            self.on_log_message('正在停止重命名操作...', 'INFO')
        self.is_running = False
        self.parent.toolButton_Startnaming.setText("开始命名")

    def update_progress_bar(self, value):
        self.parent.progressBar_naming.setValue(value)

    def on_rename_finished(self):
        self.on_log_message('重命名操作已完成', 'INFO')
        self.is_running = False
        self.parent.toolButton_Startnaming.setText("开始命名")
