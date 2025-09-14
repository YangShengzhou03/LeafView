from datetime import datetime
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QFileDialog

from SmartArrangeThread import SmartArrangeThread


class Classification(QtWidgets.QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.last_selected_button_index = -1
        self.destination_root = None
        self.tag_buttons = {
            '原文件名': self.parent.pushButton_original_tag,
            '年份': self.parent.pushButton_year_tag,
            '月份': self.parent.pushButton_month_tag,
            '日': self.parent.pushButton_date_tag,
            '星期': self.parent.pushButton_day_tag,
            '时间': self.parent.pushButton_time_tag,
            '品牌': self.parent.pushButton_make_tag,
            '位置': self.parent.pushButton_address_tag,
            '自定义': self.parent.pushButton_customize_tag
        }
        self.separator_mapping = {
            "-": "-",
            "无": "",
            "空格": " ",
            "_": "_"
        }
        self.available_layout = self.parent.horizontalLayout_57
        self.selected_layout = self.parent.horizontalLayout_53
        self.classification_thread = None
        self.init_page()
        # 设置分类级别的启用/禁用状态
        self.set_combo_box_states()
        # 连接日志信号
        self.log_signal.connect(self.log)

    def init_page(self):
        self.connect_signals()
        for i in range(1, 6):
            getattr(self.parent, f'comboBox_level_{i}').currentIndexChanged.connect(
                lambda index, level=i: self.handle_combobox_selection(level, index))
        for button in self.tag_buttons.values():
            button.clicked.connect(lambda checked, b=button: self.move_tag(b))
        self.parent.comboBox_operation.currentIndexChanged.connect(self.handle_operation_change)
        # 连接分隔符下拉框的信号
        self.parent.comboBox_separator.currentIndexChanged.connect(self.update_example_label)
        self.log("DEBUG", "欢迎使用图像分类整理，您可在上方构建文件路径与文件名结构。")

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
            self.parent.progressBar_classification.setValue(0)
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

            # 获取分隔符
            separator_text = self.parent.comboBox_separator.currentText()
            separator = self.separator_mapping.get(separator_text, "-")

            # 获取操作类型
            operation_type = self.parent.comboBox_operation.currentIndex()

            self.classification_thread = SmartArrangeThread(
                parent=self,
                folders=folders,
                classification_structure=classification_structure or None,
                file_name_structure=file_name_structure or None,
                destination_root=self.destination_root,
                separator=separator,
                time_derive=self.parent.comboBox_timeSource.currentText()
            )
            self.classification_thread.finished.connect(self.on_thread_finished)
            self.classification_thread.start()
            self.parent.toolButton_startClassification.setText("停止整理")

    def on_thread_finished(self):
        self.parent.toolButton_startClassification.setText("开始整理")
        self.classification_thread = None
        self.log("DEBUG", "整理任务已结束。")
        self.update_progress_bar(100)

    def handle_combobox_selection(self, level, index):
        # 直接调用update_combobox_state方法来处理所有级别的状态更新
        self.update_combobox_state(level)

    def update_combobox_state(self, level):
        # 检查当前级别的选择
        current_text = getattr(self.parent, f'comboBox_level_{level}').currentText()
        
        if current_text == "不分类":
            # 如果选择了"不分类"，则禁用后面的所有组合框
            for i in range(level + 1, 6):
                getattr(self.parent, f'comboBox_level_{i}').setEnabled(False)
                getattr(self.parent, f'comboBox_level_{i}').setCurrentIndex(0)  # 重置为第一个选项
        else:
            # 如果没有选择"不分类"，则启用下一级组合框
            if level < 5:
                getattr(self.parent, f'comboBox_level_{level + 1}').setEnabled(True)
                # 递归更新下一级状态
                self.update_combobox_state(level + 1)
        
        # 更新预览路径
        self.parent.label_PreviewRoute.setText("/".join([
            self.get_specific_value(getattr(self.parent, f'comboBox_level_{i}').currentText())
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]) or "不分类")
        
        # 记录分类设置以便后续使用
        self.classification_settings = [
            getattr(self.parent, f'comboBox_level_{i}').currentText()
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]
    
    def set_combo_box_states(self):
        """设置分类级别的初始启用/禁用状态"""
        # 启用第一级分类下拉框
        self.parent.comboBox_level_1.setEnabled(True)
        # 禁用其他级别分类下拉框
        for i in range(2, 6):
            combo_box = getattr(self.parent, f'comboBox_level_{i}')
            combo_box.setEnabled(False)
            combo_box.setCurrentIndex(0)
        
        # 初始化预览路径显示
        self.update_combobox_state(1)

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
        # 移动标签到已选区域
        # 检查标签数量限制
        if self.selected_layout.count() >= 5:
            return
        
        # 保存按钮的原始样式
        original_style = button.styleSheet()
        button.setProperty('original_style', original_style)
        
        # 从原布局中移除按钮
        self.available_layout.removeWidget(button)
        
        # 应用新样式
        button.setStyleSheet(
            "QPushButton {background-color: #8677FD; color: white; border: none; border-radius: 4px; padding: 4px 8px;}")
        
        # 添加到已选区域
        self.selected_layout.addWidget(button)
        
        # 更新点击事件
        button.clicked.disconnect()
        button.clicked.connect(lambda checked, b=button: self.move_tag_back(b))
        
        # 更新示例文件名
        self.update_example_label()
        
        # 限制标签数量
        if self.selected_layout.count() >= 5:
            # 禁用所有原始标签按钮
            for btn in self.tag_buttons.values():
                if btn.parent() == self.available_layout:
                    btn.setEnabled(False)
    
    def move_tag_back(self, button):
        # 将标签移回可用区域
        self.selected_layout.removeWidget(button)
        
        # 恢复原始样式
        if button.property('original_style') is not None:
            button.setStyleSheet(button.property('original_style'))
        
        # 添加回原布局
        self.available_layout.addWidget(button)
        
        # 更新点击事件
        button.clicked.disconnect()
        button.clicked.connect(lambda checked, b=button: self.move_tag(b))
        
        # 重新启用所有可用标签
        for btn in self.tag_buttons.values():
            if btn.parent() == self.available_layout:
                btn.setEnabled(True)
        
        # 更新示例文件名
        self.update_example_label()

    def update_example_label(self):
        now = datetime.now()
        selected = [self.selected_layout.itemAt(i).widget().text() for i in range(self.selected_layout.count())
                    if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]
        current_separator = self.separator_mapping.get(self.parent.comboBox_separator.currentText(), "")
        parts = {
            "原文件名": "DSC_1234",
            "年份": f"{now.year}",
            "月份": f"{now.month:02d}",
            "日": f"{now.day:02d}",
            "星期": f"{self._get_weekday(now)}",
            "时间": f"{now.strftime('%H%M%S')}",
            "品牌": "佳能",
            "位置": "浙大",
            "自定义": "家庭聚会"
        }
        example_text = current_separator.join(parts.get(b, "") for b in selected) if selected else "请点击标签以组成文件名"
        self.parent.label_PreviewName.setText(example_text)

    @staticmethod
    def _get_weekday(date):
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]

    def log(self, level, message):
        # 记录日志
        current_time = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        self.log_signal.emit(level, log_message)
        
        # 输出到控制台用于调试
        print(log_message)
        
        # 如果有日志显示区域，可以在这里更新
        # 例如: self.parent.textEdit_log.append(log_message)
