"""
LeafView 智能整理模块

负责媒体文件的智能分类和重命名功能，包括：
1. 多级分类结构设置（年份、月份、设备等）
2. 文件名标签组合和自定义
3. 文件操作（移动/复制）管理
4. 实时预览和示例显示
5. 后台整理线程管理
"""

from datetime import datetime
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QFileDialog

from SmartArrangeThread import SmartArrangeThread


class SmartArrange(QtWidgets.QWidget):
    """
    智能整理功能主类
    
    实现媒体文件的分类整理、重命名和文件操作功能
    """
    log_signal = pyqtSignal(str, str)  # 日志信号，用于线程间日志传递

    def __init__(self, parent=None, folder_page=None):
        """
        初始化智能整理模块
        
        Args:
            parent: 父窗口对象
            folder_page: 文件夹页面对象，用于获取媒体文件夹信息
        """
        super().__init__(parent)
        self.parent = parent  # 父窗口引用
        self.folder_page = folder_page  # 文件夹页面引用
        self.last_selected_button_index = -1  # 最后选中的按钮索引
        self.destination_root = None  # 复制操作的目标根目录
        
        # 标签按钮映射字典，将标签名称映射到对应的UI按钮
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
        
        # 分隔符映射字典，将显示文本映射到实际分隔符
        self.separator_mapping = {
            "-": "-",
            "无": "",
            "空格": " ",
            "_": "_"
        }
        
        # 布局引用
        self.available_layout = self.parent.horizontalLayout_57  # 可用标签布局
        self.selected_layout = self.parent.horizontalLayout_53  # 已选标签布局
        
        self.SmartArrange_thread = None  # 整理线程实例
        self.SmartArrange_settings = []  # 分类设置列表
        
        self.init_page()  # 初始化页面
        self.set_combo_box_states()  # 设置分类下拉框状态
        self.log_signal.connect(self.handle_log_signal)  # 连接日志信号

    def init_page(self):
        """初始化页面，连接信号槽和设置初始状态"""
        self.connect_signals()  # 连接按钮信号
        
        # 连接分类级别下拉框的信号
        for i in range(1, 6):
            getattr(self.parent, f'comboBox_level_{i}').currentIndexChanged.connect(
                lambda index, level=i: self.handle_combobox_selection(level, index))
        
        # 连接标签按钮的点击信号
        for button in self.tag_buttons.values():
            button.clicked.connect(lambda checked, b=button: self.move_tag(b))
        
        # 连接操作类型下拉框的信号
        self.parent.comboBox_operation.currentIndexChanged.connect(self.handle_operation_change)
        
        # 连接分隔符下拉框的信号
        self.parent.comboBox_separator.currentIndexChanged.connect(self.update_example_label)
        
        self.log("DEBUG", "欢迎使用图像分类整理，您可在上方构建文件路径与文件名结构。")

    def connect_signals(self):
        """连接开始整理按钮的信号"""
        self.parent.toolButton_startSmartArrange.clicked.connect(self.toggle_SmartArrange)

    def update_progress_bar(self, value):
        """更新进度条显示
        
        Args:
            value: 进度值 (0-100)
        """
        self.parent.progressBar_classification.setValue(value)

    def handle_operation_change(self, index):
        """处理操作类型变更
        
        Args:
            index: 操作类型索引 (0:移动, 1:复制)
        """
        if index == 1:
            # 复制操作需要选择目标文件夹
            folder = QFileDialog.getExistingDirectory(self, "选择复制目标文件夹",
                                                      options=QFileDialog.Option.ShowDirsOnly)
            if folder:
                self.destination_root = folder  # 设置目标根目录
                display_path = folder + '/'
                if len(display_path) > 20:
                    display_path = f"{display_path[:8]}...{display_path[-6:]}"  # 长路径截断显示
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
            operation_text = "移动文件"
            self.parent.label_CopyRoute.setText(f"{operation_text}")
        
        self.update_operation_display()  # 更新操作显示

    def toggle_SmartArrange(self):
        """切换整理任务的启动/停止状态"""
        if self.SmartArrange_thread and self.SmartArrange_thread.isRunning():
            # 停止正在运行的整理线程
            self.SmartArrange_thread.stop()
            self.parent.toolButton_startSmartArrange.setText("开始整理")
            self.parent.progressBar_classification.setValue(0)
        else:
            # 获取所有文件夹信息
            folders = self.folder_page.get_all_folders() if self.folder_page else []
            if not folders:
                self.log("WARNING", "请先导入一个有效的文件夹。")
                return

            # 弹出确认对话框
            reply = QMessageBox.question(
                self,
                "确认整理操作",
                "一旦开始整理，操作的文件将无法恢复，请务必备份好数据！\n\n是否确认开始整理？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                self.log("INFO", "用户取消了整理操作")
                return

            # 构建分类结构
            SmartArrange_structure = [
                getattr(self.parent, f'comboBox_level_{i}').currentText()
                for i in range(1, 6)
                if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
                   getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
            ]

            # 构建文件名结构
            file_name_structure = [self.selected_layout.itemAt(i).widget().text()
                                   for i in range(self.selected_layout.count())
                                   if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]

            # 获取分隔符
            separator_text = self.parent.comboBox_separator.currentText()
            separator = self.separator_mapping.get(separator_text, "-")

            # 获取操作类型
            operation_type = self.parent.comboBox_operation.currentIndex()
            operation_text = "移动" if operation_type == 0 else "复制"

            # 根据设置显示不同的操作信息
            if not SmartArrange_structure and not file_name_structure:
                self.log("INFO", f"将执行{operation_text}操作：将文件夹中的所有文件提取到顶层目录")
            elif not SmartArrange_structure:
                self.log("INFO", f"将执行{operation_text}操作：仅重命名文件，不进行分类")
            elif not file_name_structure:
                self.log("INFO", f"将执行{operation_text}操作：仅进行分类，不重命名文件")
            else:
                self.log("INFO", f"将执行{operation_text}操作：进行分类和重命名")

            # 创建并启动整理线程
            self.SmartArrange_thread = SmartArrangeThread(
                parent=self,
                folders=folders,
                classification_structure=SmartArrange_structure or None,
                file_name_structure=file_name_structure or None,
                destination_root=self.destination_root,
                separator=separator,
                time_derive=self.parent.comboBox_timeSource.currentText()
            )
            self.SmartArrange_thread.finished.connect(self.on_thread_finished)
            self.SmartArrange_thread.start()
            self.parent.toolButton_startSmartArrange.setText("停止整理")

    def on_thread_finished(self):
        """整理线程完成时的处理"""
        self.parent.toolButton_startSmartArrange.setText("开始整理")
        self.SmartArrange_thread = None
        self.log("DEBUG", "整理任务已结束。")
        self.update_progress_bar(100)

    def handle_combobox_selection(self, level, index):
        """处理分类下拉框选择变更
        
        Args:
            level: 分类级别 (1-5)
            index: 选择的索引
        """
        self.update_combobox_state(level)  # 更新下拉框状态

    def update_combobox_state(self, level):
        """更新分类下拉框的启用状态
        
        Args:
            level: 当前变更的分类级别
        """
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
                self.update_combobox_state(level + 1)  # 递归更新下一级状态
        
        # 更新预览路径显示
        SmartArrange_paths = [
            self.get_specific_value(getattr(self.parent, f'comboBox_level_{i}').currentText())
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]
        
        if SmartArrange_paths:
            preview_text = "/".join(SmartArrange_paths)  # 用斜杠连接路径部分
        else:
            preview_text = "顶层目录（不分类）"  # 无分类时的显示文本
        
        self.parent.label_PreviewRoute.setText(preview_text)
        
        # 更新分类设置
        self.SmartArrange_settings = [
            getattr(self.parent, f'comboBox_level_{i}').currentText()
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]
        
        self.update_operation_display()  # 更新操作显示
    
    def update_operation_display(self):
        """更新操作类型显示，包括分类和重命名状态"""
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
                display_path = f"{display_path[:8]}...{display_path[-6:]}"  # 长路径截断显示
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
        
        self.update_combobox_state(1)  # 初始化预览路径显示

    def get_specific_value(self, text):
        """获取分类选项对应的示例值
        
        Args:
            text: 分类选项文本
            
        Returns:
            str: 对应的示例值
        """
        now = datetime.now()
        return {
            "年份": str(now.year),
            "月份": str(now.month),
            "拍摄设备": "小米",
            "拍摄省份": "江西",
            "拍摄城市": "南昌"
        }.get(text, text)

    def is_valid_windows_filename(self, filename):
        """检查文件名是否符合Windows命名规范
        
        Args:
            filename: 要检查的文件名
            
        Returns:
            bool: 是否有效
        """
        invalid_chars = '<>:"/\\|?*'  # Windows不允许的字符
        if any(char in filename for char in invalid_chars):
            return False
        # 检查保留文件名
        if filename in ('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'):
            return False
        if filename.endswith('.') or filename.endswith(' '):  # 不能以点或空格结尾
            return False
        if len(filename) > 255:  # 长度限制
            return False
        return True
    
    def move_tag(self, button):
        """移动标签到已选区域
        
        Args:
            button: 要移动的按钮对象
        """
        # 检查标签数量限制（最多5个）
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
        
        # 添加到已选区域
        self.selected_layout.addWidget(button)
        
        # 更新点击事件
        button.clicked.disconnect()
        button.clicked.connect(lambda checked, b=button: self.move_tag_back(b))
        
        # 更新示例文件名
        self.update_example_label()
        
        # 更新操作类型显示
        self.update_operation_display()
        
        # 限制标签数量，达到上限时禁用所有可用标签
        if self.selected_layout.count() >= 5:
            for btn in self.tag_buttons.values():
                if btn.parent() == self.available_layout:
                    btn.setEnabled(False)
    
    def move_tag_back(self, button):
        """将标签移回可用区域
        
        Args:
            button: 要移回的按钮对象
        """
        # 从已选布局中移除按钮
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
        """更新示例文件名显示"""
        now = datetime.now()
        # 获取所有已选按钮
        selected_buttons = [self.selected_layout.itemAt(i).widget() for i in range(self.selected_layout.count())
                    if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]
        # 获取当前分隔符
        current_separator = self.separator_mapping.get(self.parent.comboBox_separator.currentText(), "")
        
        # 构建示例部分
        example_parts = []
        for button in selected_buttons:
            button_text = button.text()
            # 如果是自定义标签，使用用户输入的实际内容
            if button.property('original_text') == '自定义' and button.property('custom_content') is not None:
                custom_content = button.property('custom_content')
                display_content = custom_content[:3] if len(custom_content) > 3 else custom_content
                example_parts.append(display_content)
            else:
                # 其他标签使用预设的示例值
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
        
        # 构建示例文本
        example_text = current_separator.join(example_parts) if example_parts else "请点击标签以组成文件名"
        self.parent.label_PreviewName.setText(example_text)

    @staticmethod
    def _get_weekday(date):
        """获取星期几的中文表示
        
        Args:
            date: 日期对象
            
        Returns:
            str: 星期几的中文表示
        """
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]

    def handle_log_signal(self, level, message):
        """处理日志信号，避免递归调用
        
        Args:
            level: 日志级别
            message: 日志消息
        """
        current_time = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        
        print(log_message)  # 输出到控制台用于调试
        
        # 更新到日志显示区域，使用HTML颜色格式
        if hasattr(self.parent, 'textEdit_SmartArrange_Log'):
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
        """记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
        """
        current_time = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        self.log_signal.emit(level, log_message)  # 发射日志信号
        
        print(log_message)  # 输出到控制台用于调试
        
        # 更新到日志显示区域
        if hasattr(self.parent, 'textEdit_SmartArrange_Log'):
            color_map = {
                'ERROR': '#FF0000',    # 红色
                'WARNING': '#FFA500',  # 橙色
                'DEBUG': '#008000',    # 绿色
                'INFO': '#8677FD'      # 紫色
            }
            color = color_map.get(level, '#000000')  # 默认黑色
            self.parent.textEdit_SmartArrange_Log.append(
                f'<span style="color:{color}">{log_message}</span>')
