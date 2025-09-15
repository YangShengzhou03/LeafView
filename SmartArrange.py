from datetime import datetime
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QFileDialog

from SmartArrangeThread import SmartArrangeThread


class SmartArrange(QtWidgets.QWidget):
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
        self.SmartArrange_thread = None
        self.SmartArrange_settings = []  # 初始化分类设置
        self.init_page()
        # 设置分类级别的启用/禁用状态
        self.set_combo_box_states()
        # 连接日志信号到日志处理方法
        self.log_signal.connect(self.handle_log_signal)

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
        self.parent.toolButton_startSmartArrange.clicked.connect(self.toggle_SmartArrange)

    def update_progress_bar(self, value):
        self.parent.progressBar_SmartArrange.setValue(value)

    def handle_operation_change(self, index):
        if index == 1:
            # 复制操作需要选择目标文件夹
            folder = QFileDialog.getExistingDirectory(self, "选择复制目标文件夹",
                                                      options=QFileDialog.Option.ShowDirsOnly)
            if folder:
                self.destination_root = folder
                display_path = folder + '/'
                if len(display_path) > 20:
                    display_path = f"{display_path[:8]}...{display_path[-6:]}"
                # 更清晰的显示操作类型
                operation_text = "复制到: "
                self.parent.label_CopyRoute.setText(f"{operation_text}{display_path}")
            else:
                # 用户取消选择，恢复为移动操作
                self.parent.comboBox_operation.setCurrentIndex(0)
                self.destination_root = None
                self.parent.label_CopyRoute.setText("移动文件（默认操作）")
        else:
            # 移动操作
            self.destination_root = None
            # 显示当前操作类型
            operation_text = "移动文件"
            self.parent.label_CopyRoute.setText(f"{operation_text}")
        
        # 更新操作类型显示
        self.update_operation_display()

    def toggle_SmartArrange(self):
        if self.SmartArrange_thread and self.SmartArrange_thread.isRunning():
            self.SmartArrange_thread.stop()
            self.parent.toolButton_startSmartArrange.setText("开始整理")
            self.parent.progressBar_SmartArrange.setValue(0)
        else:
            folders = self.folder_page.get_all_folders() if self.folder_page else []
            if not folders:
                self.log("WARNING", "请先导入一个有效的文件夹。")
                return

            SmartArrange_structure = [
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
            operation_text = "移动" if operation_type == 0 else "复制"

            # 检查是否什么都不做（不分类且不重命名）
            if not SmartArrange_structure and not file_name_structure:
                self.log("INFO", f"将执行{operation_text}操作：将文件夹中的所有文件提取到顶层目录")
            elif not SmartArrange_structure:
                self.log("INFO", f"将执行{operation_text}操作：仅重命名文件，不进行分类")
            elif not file_name_structure:
                self.log("INFO", f"将执行{operation_text}操作：仅进行分类，不重命名文件")
            else:
                self.log("INFO", f"将执行{operation_text}操作：进行分类和重命名")

            self.SmartArrange_thread = SmartArrangeThread(
                parent=self,
                folders=folders,
                SmartArrange_structure=SmartArrange_structure or None,
                file_name_structure=file_name_structure or None,
                destination_root=self.destination_root,
                separator=separator,
                time_derive=self.parent.comboBox_timeSource.currentText()
            )
            self.SmartArrange_thread.finished.connect(self.on_thread_finished)
            self.SmartArrange_thread.start()
            self.parent.toolButton_startSmartArrange.setText("停止整理")

    def on_thread_finished(self):
        self.parent.toolButton_startSmartArrange.setText("开始整理")
        self.SmartArrange_thread = None
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
        
        # 更新预览路径 - 更友好的显示
        SmartArrange_paths = [
            self.get_specific_value(getattr(self.parent, f'comboBox_level_{i}').currentText())
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]
        
        if SmartArrange_paths:
            preview_text = "/".join(SmartArrange_paths)
        else:
            preview_text = "顶层目录（不分类）"
        
        self.parent.label_PreviewRoute.setText(preview_text)
        
        # 记录分类设置以便后续使用 - 必须在这里更新，而不是在最后
        self.SmartArrange_settings = [
            getattr(self.parent, f'comboBox_level_{i}').currentText()
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]
        
        # 更新操作类型显示
        self.update_operation_display()
    
    def update_operation_display(self):
        """更新操作类型显示"""
        # 检查分类设置
        has_SmartArrange = len(self.SmartArrange_settings) > 0
        
        # 检查文件名设置（标签选择）
        has_filename = self.selected_layout.count() > 0
        
        # 确定操作类型
        if has_SmartArrange and has_filename:
            operation_type = "分类并重命名"
        elif has_SmartArrange and not has_filename:
            operation_type = "仅分类"
        elif not has_SmartArrange and has_filename:
            operation_type = "仅重命名"
        else:
            operation_type = "提取到顶层目录"
        
        # 获取当前操作模式（移动/复制）
        operation_mode = "移动" if self.parent.comboBox_operation.currentIndex() == 0 else "复制"
        
        # 设置不同操作的颜色
        move_color = "#FF6B6B"  # 红色系，表示移动操作
        copy_color = "#4ECDC4"  # 青色系，表示复制操作
        
        # 更新显示
        if self.destination_root:
            display_path = str(self.destination_root)
            if len(display_path) > 20:
                display_path = f"{display_path[:8]}...{display_path[-6:]}"
            # 使用HTML格式设置颜色
            if operation_mode == "移动":
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{move_color}">{operation_mode}到: {display_path} ({operation_type})</span>'
                )
            else:
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{copy_color}">{operation_mode}到: {display_path} ({operation_type})</span>'
                )
        else:
            # 使用HTML格式设置颜色
            if operation_mode == "移动":
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{move_color}">{operation_mode}文件 ({operation_type})</span>'
                )
            else:
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{copy_color}">{operation_mode}文件 ({operation_type})</span>'
                )
    
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

    def is_valid_windows_filename(self, filename):
        # 检查文件名是否符合Windows命名规范
        invalid_chars = '<>:"/\\|?*'
        if any(char in filename for char in invalid_chars):
            return False
        if filename in ('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'):
            return False
        if filename.endswith('.') or filename.endswith(' '):
            return False
        if len(filename) > 255:
            return False
        return True
    
    def move_tag(self, button):
        # 移动标签到已选区域
        # 检查标签数量限制
        if self.selected_layout.count() >= 5:
            return
        
        # 保存按钮的原始样式
        original_style = button.styleSheet()
        button.setProperty('original_style', original_style)
        
        # 保存按钮的原始文本，用于恢复
        original_text = button.text()
        button.setProperty('original_text', original_text)
        
        # 特殊处理自定义标签
        if original_text == '自定义':
            # 弹出单行文本框让用户输入
            input_dialog = QInputDialog(self)
            input_dialog.setWindowTitle("自定义标签")
            input_dialog.setLabelText("请输入自定义部分的文件名内容:")
            input_dialog.setTextEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            input_dialog.setTextValue("")
            # 设置最大长度为255个字符（Windows文件名限制）
            input_dialog.findChild(QtWidgets.QLineEdit).setMaxLength(255)
            
            ok = input_dialog.exec()
            custom_text = input_dialog.textValue()
            
            if ok and custom_text:
                # 检查是否符合Windows命名规范
                if not self.is_valid_windows_filename(custom_text):
                    QMessageBox.warning(self, "文件名无效", "输入的文件名包含Windows不允许的字符或格式！")
                    return
                
                # 在已选区域显示前三个字
                display_text = custom_text[:3] if len(custom_text) > 3 else custom_text
                button.setText(display_text)
                # 存储用户实际输入的内容到新属性中
                button.setProperty('custom_content', custom_text)
            else:
                # 用户取消或未输入，不移动标签
                return
        
        # 从原布局中移除按钮
        self.available_layout.removeWidget(button)
        
        # 保持完全相同的样式
        # 添加到已选区域
        self.selected_layout.addWidget(button)
        
        # 更新点击事件
        button.clicked.disconnect()
        button.clicked.connect(lambda checked, b=button: self.move_tag_back(b))
        
        # 更新示例文件名
        self.update_example_label()
        
        # 更新操作类型显示
        self.update_operation_display()
        
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
        
        # 恢复原始文本（特别是自定义标签）
        if button.property('original_text') is not None:
            button.setText(button.property('original_text'))
        
        # 清理自定义内容属性
        if button.property('custom_content') is not None:
            button.setProperty('custom_content', None)
        
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
        selected_buttons = [self.selected_layout.itemAt(i).widget() for i in range(self.selected_layout.count())
                    if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]
        current_separator = self.separator_mapping.get(self.parent.comboBox_separator.currentText(), "")
        
        # 构建示例部分
        example_parts = []
        for button in selected_buttons:
            button_text = button.text()
            # 如果是自定义标签，使用用户输入的实际内容
            if button.property('original_text') == '自定义' and button.property('custom_content') is not None:
                # 获取用户实际输入的自定义内容，但只显示前3个字
                custom_content = button.property('custom_content')
                display_content = custom_content[:3] if len(custom_content) > 3 else custom_content
                example_parts.append(display_content)
            else:
                # 其他标签使用预设的示例值，也只显示前3个字
                parts = {
                    "原文件名": "DSC_1234",
                    "年份": f"{now.year}",
                    "月份": f"{now.month:02d}",
                    "日": f"{now.day:02d}",
                    "星期": f"{self._get_weekday(now)}",
                    "时间": f"{now.strftime('%H%M%S')}",
                    "品牌": "佳能",
                    "位置": "浙大",
                    "自定义": "自定义内容"
                }
                full_text = parts.get(button_text, button_text)
                display_text = full_text[:3] if len(full_text) > 3 else full_text
                example_parts.append(display_text)
        
        example_text = current_separator.join(example_parts) if example_parts else "请点击标签以组成文件名"
        self.parent.label_PreviewName.setText(example_text)

    @staticmethod
    def _get_weekday(date):
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]

    def handle_log_signal(self, level, message):
        # 处理日志信号，避免递归调用
        current_time = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        
        # 输出到控制台用于调试
        print(log_message)
        
        # 更新到日志显示区域，使用HTML颜色格式
        if hasattr(self.parent, 'textEdit_SmartArrange_Log'):
            # 定义颜色映射
            color_map = {
                'ERROR': '#FF0000',    # 红色
                'WARNING': '#FFA500',  # 橙色
                'DEBUG': '#008000',    # 绿色
                'INFO': '#8677FD'      # 紫色
            }
            color = color_map.get(level, '#000000')  # 默认黑色
            self.parent.textEdit_SmartArrange_Log.append(
                f'<span style="color:{color}">{log_message}</span>')
    
    def log(self, level, message):
        # 记录日志
        current_time = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        self.log_signal.emit(level, log_message)
        
        # 输出到控制台用于调试
        print(log_message)
        
        # 更新到日志显示区域，使用HTML颜色格式
        if hasattr(self.parent, 'textEdit_SmartArrange_Log'):
            # 定义颜色映射
            color_map = {
                'ERROR': '#FF0000',    # 红色
                'WARNING': '#FFA500',  # 橙色
                'DEBUG': '#008000',    # 绿色
                'INFO': '#8677FD'      # 紫色
            }
            color = color_map.get(level, '#000000')  # 默认黑色
            self.parent.textEdit_SmartArrange_Log.append(
                f'<span style="color:{color}">{log_message}</span>')
