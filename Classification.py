from datetime import datetime

from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QFileDialog

from ClassificationThread import ClassificationThread


class Classification(QtWidgets.QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.last_selected_button_index = -1
        self.destination_root = None
        self.tag_buttons = {
            '年份': self.parent.pushButton_year,
            '月份': self.parent.pushButton_month,
            '日': self.parent.pushButton_date,
            '星期': self.parent.pushButton_day,
            '时间': self.parent.pushButton_time,
            '位置': self.parent.pushButton_address,
            '品牌': self.parent.pushButton_make
        }
        self.available_layout = self.parent.horizontalLayout_57
        self.selected_layout = self.parent.horizontalLayout_53
        self.classification_thread = None
        self.init_page()
        self.log_signal.connect(self.log)

    def init_page(self):
        self.connect_signals()
        for i in range(1, 6):
            getattr(self.parent, f'comboBox_level_{i}').currentIndexChanged.connect(
                lambda index, level=i: self.handle_combobox_selection(level, index))
        for button in self.tag_buttons.values():
            button.clicked.connect(lambda checked, b=button: self.move_tag(b))
        self.parent.comboBox_operation.currentIndexChanged.connect(self.handle_operation_change)
        self.log("DEBUG", "欢迎使用图像分类整理功能，您可以在上方构建文件夹整理路径和文件名格式~")

    def connect_signals(self):
        self.parent.toolButton_startClassification.clicked.connect(self.toggle_classification)

    def update_progress_bar(self, value):
        self.parent.progressBar_classification.setValue(value)

    def handle_operation_change(self, index):
        if index == 1:
            folder = QFileDialog.getExistingDirectory(self, "选择复制目标文件夹",
                                                      options=QFileDialog.Option.ShowDirsOnly)
            if folder:
                self.destination_root = folder
                display_path = folder + '/'
                if len(display_path) > 12:
                    display_path = f"{display_path[:8]}...{display_path[-6:]}"
                self.parent.label_CopyRoute.setText(display_path)
            else:
                self.parent.comboBox_operation.setCurrentIndex(0)
                self.destination_root = None
                self.parent.label_CopyRoute.setText("")
        else:
            self.parent.label_CopyRoute.setText("")

    def toggle_classification(self):
        if self.classification_thread and self.classification_thread.isRunning():
            self.classification_thread.stop()
            self.parent.toolButton_startClassification.setText("开始整理")
        else:
            folders = self.folder_page.get_all_folders() if self.folder_page else []
            if not folders:
                self.log("WARNING", "请先导入一个有效的文件夹。")
                return

            classification_structure = [
                getattr(self.parent, f'comboBox_level_{i}').currentText()
                for i in range(1, 6)
                if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
                   getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
            ]

            file_name_structure = [self.selected_layout.itemAt(i).widget().text()
                                   for i in range(self.selected_layout.count())
                                   if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]

            if not classification_structure and not file_name_structure and not self.destination_root:
                self.log("WARNING", "请选择至少一种操作（分类或重命名）")
                return

            self.classification_thread = ClassificationThread(
                parent=self,
                folders=folders,
                classification_structure=classification_structure or None,
                file_name_structure=file_name_structure or None,
                destination_root=self.destination_root,
                time_derive=self.parent.comboBox_timeSource.currentText()
            )
            self.classification_thread.finished.connect(self.on_thread_finished)
            self.classification_thread.start()
            self.parent.toolButton_startClassification.setText("停止整理")

    def on_thread_finished(self):
        self.parent.toolButton_startClassification.setText("开始整理")
        self.classification_thread = None

    def handle_combobox_selection(self, level, index):
        comboBox = getattr(self.parent, f'comboBox_level_{level}')
        if comboBox.currentText() == "识别文字":
            text, ok = QInputDialog.getText(self, "输入识别文字", "请输入识别文字(最多2个汉字):",
                                            QtWidgets.QLineEdit.EchoMode.Normal, "")
            if ok:
                if len(text.encode('utf-8')) > 8 or (len(text) > 4 and not text.isalpha()):
                    QMessageBox.warning(self, "输入错误", "输入超过长度限制(最多2个汉字)")
                    comboBox.setCurrentIndex(0)
                else:
                    comboBox.setItemText(index, text)
                    comboBox.setCurrentIndex(index)
            else:
                comboBox.setCurrentIndex(0)
        self.update_combobox_state(level)

    def update_combobox_state(self, level):
        current_box = getattr(self.parent, f'comboBox_level_{level}')
        next_box = getattr(self.parent, f'comboBox_level_{level + 1}', None) if level < 5 else None
        if next_box:
            next_box.setEnabled(current_box.currentIndex() != 0)
            if current_box.currentIndex() == 0:
                next_box.setCurrentIndex(0)
                for i in range(level + 1, 6):
                    future_box = getattr(self.parent, f'comboBox_level_{i}', None)
                    if future_box:
                        future_box.setEnabled(False)
                        future_box.setCurrentIndex(0)
            else:
                self.update_combobox_state(level + 1)
        self.parent.label_PreviewRoute.setText("/".join([
            self.get_specific_value(getattr(self.parent, f'comboBox_level_{i}').currentText())
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]) or "不分类")

    def get_specific_value(self, text):
        now = datetime.now()
        return {
            "年份": str(now.year),
            "月份": str(now.month),
            "拍摄设备": "小米",
            "拍摄省份": "江西",
            "拍摄城市": "南昌"
        }.get(text, text)

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
        selected = [self.selected_layout.itemAt(i).widget().text() for i in range(self.selected_layout.count())
                    if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]
        self.parent.label_PreviewName.setText(
            "请点击标签以组成文件名" if not selected else "-".join({
                                                                       "年份": f"{now.year}",
                                                                       "月份": f"{now.month:02d}",
                                                                       "日": f"{now.day:02d}",
                                                                       "星期": f"{self._get_weekday(now)}",
                                                                       "时间": f"{now.strftime('%H%M')}",
                                                                       "位置": "浙大",
                                                                       "品牌": "佳能"
                                                                   }.get(b, "") for b in selected))

    @staticmethod
    def _get_weekday(date):
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]

    def log(self, level, message):
        c = {'ERROR': '#FF0000', 'WARNING': '#FFA500', 'DEBUG': '#008000', 'INFO': '#8677FD'}
        self.parent.textEdit_Classification_Log.append(
            f'<span style="color:{c.get(level, "#000000")}">[{datetime.now().strftime("%H:%M:%S")}]'
            f' [{level}] {message}</span>')
