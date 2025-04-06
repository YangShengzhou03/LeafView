from datetime import datetime
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from ClassificationThread import ClassificationThread


class Classification(QtWidgets.QWidget):
    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.last_selected_button_index = -1
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
        self.init_page()

    def init_page(self):
        self.connect_signals()
        for i in range(1, 6):
            comboBox_name = f'comboBox_level_{i}'
            if hasattr(self.parent, comboBox_name):
                getattr(self.parent, comboBox_name).currentIndexChanged.connect(
                    lambda index, level=i: self.handle_combobox_selection(level, index))
        for button in self.tag_buttons.values():
            button.clicked.connect(lambda checked, b=button: self.move_tag(b))

    def connect_signals(self):
        self.parent.toolButton_startClassification.clicked.connect(self.start_organizing)

    def initialize_combobox(self):
        for i in range(1, 6):
            comboBox = getattr(self.parent, f'comboBox_level_{i}', None)
            if comboBox:
                comboBox.setEnabled(i == 1)
                comboBox.setCurrentIndex(0 if i != 1 else comboBox.currentIndex())

    def start_organizing(self):
        folders = self.folder_page.get_all_folders() if self.folder_page else []
        if not folders:
            QMessageBox.warning(self, "警告", "没有选择文件夹进行操作")
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

        if not classification_structure and not file_name_structure:
            QMessageBox.warning(self, "警告", "请选择至少一种操作（分类或重命名）")
            return
        time_derive_option = self.parent.comboBox_timeSource.currentText()
        self.classification_thread = ClassificationThread(
            parent=self,
            folders=folders,
            classification_structure=classification_structure or None,
            file_name_structure=file_name_structure or None,
            time_derive=time_derive_option
        )
        self.classification_thread.start()

    def update_progress_bar(self, value):
        self.parent.progressBar_Classification.setValue(value)

    def handle_combobox_selection(self, level, index):
        comboBox = getattr(self.parent, f'comboBox_level_{level}')
        current_text = comboBox.currentText()
        if current_text == "识别文字":
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
        folder_path = "/".join([
            self.get_specific_value(getattr(self.parent, f'comboBox_level_{i}').currentText())
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ])
        self.parent.label_PreviewRoute.setText(folder_path if folder_path else "未选择分类方式")

    def get_specific_value(self, text):
        now = datetime.now()
        specific_values = {"年份": str(now.year), "月份": str(now.month), "拍摄设备": "小米", "拍摄省份": "江西",
                           "拍摄城市": "南昌"}
        return specific_values.get(text, text)

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
        selected_buttons = [self.selected_layout.itemAt(i).widget().text() for i in range(self.selected_layout.count())
                            if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]
        example_text = "请点击标签以组成文件名" if not selected_buttons else "-".join(
            {"年份": f"{now.year}", "月份": f"{now.month:02d}", "日": f"{now.day:02d}",
             "星期": f"{self._get_weekday(now)}", "时间": f"{now.strftime('%H%M')}", "位置": "科师大",
             "品牌": "佳能"}.get(button_text, "") for button_text in selected_buttons)
        self.parent.label_PreviewName.setText(example_text)

    @staticmethod
    def _get_weekday(date):
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays[date.weekday()]
