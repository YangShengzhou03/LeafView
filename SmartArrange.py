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
            '原名': self.parent.pushButton_original_tag,
            '年份': self.parent.pushButton_year_tag,
            '月份': self.parent.pushButton_month_tag,
            '日': self.parent.pushButton_date_tag,
            '星期': self.parent.pushButton_day_tag,
            '时间': self.parent.pushButton_time_tag,
            '品牌': self.parent.pushButton_make_tag,
            '型号': self.parent.pushButton_model_tag,
            '位置': self.parent.pushButton_address_tag,
            '自定义': self.parent.pushButton_customize_tag
        }
        
        self.separator_mapping = {
            "-": "-",
            "无": "",
            "空格": " ",
            "_": "_",
            ".": ".",
            ",": ",",
            "|": "|",
            "~": "~"
        }
        
        self.available_layout = self.parent.layout_rename_tags
        self.selected_layout = self.parent.layout_rename_selected
        
        self.SmartArrange_thread = None
        self.SmartArrange_settings = []
        
        self.init_page()
        self.set_combo_box_states()
        self.log_signal.connect(self.handle_log_signal)
        self.log("INFO", "欢迎使用智能整理，可以为您整理目录、重命名媒体。请注意，操作一旦执行将无法恢复。")

    def init_page(self):
        self.connect_signals()
        
        for i in range(1, 6):
            getattr(self.parent, f'comboBox_level_{i}').currentIndexChanged.connect(
                lambda index, level=i: self.handle_combobox_selection(level, index))
        
        for button in self.tag_buttons.values():
            button.clicked.connect(lambda checked, b=button: self.move_tag(b))
        
        self.parent.comboBox_operation.currentIndexChanged.connect(self.handle_operation_change)
        
        self.parent.comboBox_separator.currentIndexChanged.connect(self.update_example_label)
        
        self.log("DEBUG", "欢迎使用图像分类整理，您可在上方构建文件路径与文件名结构。")

    def connect_signals(self):
        self.parent.toolButton_startSmartArrange.clicked.connect(self.toggle_SmartArrange)

    def update_progress_bar(self, value):
        self.parent.progressBar_classification.setValue(value)

    def handle_operation_change(self, index):
        if index == 1:
            folder = QFileDialog.getExistingDirectory(self, "选择复制目标文件夹",
                                                      options=QFileDialog.Option.ShowDirsOnly)
            if folder:
                self.destination_root = folder
                display_path = folder + '/'
                if len(display_path) > 20:
                    display_path = f"{display_path[:8]}...{display_path[-6:]}"
                operation_text = "复制到: "
                self.parent.label_CopyRoute.setText(f"{operation_text}{display_path}")
            else:
                self.parent.comboBox_operation.setCurrentIndex(0)
                self.destination_root = None
                self.parent.label_CopyRoute.setText("移动文件（默认操作）")
        else:
            self.destination_root = None
            operation_text = "移动文件"
            self.parent.label_CopyRoute.setText(f"{operation_text}")
        
        self.update_operation_display()

    def toggle_SmartArrange(self):
        """智能整理开关，简化用户交互流程"""
        if self.SmartArrange_thread and self.SmartArrange_thread.isRunning():
            self.SmartArrange_thread.stop()
            self.parent.toolButton_startSmartArrange.setText("开始整理")
            self.parent.progressBar_classification.setValue(0)
            self._show_operation_status("整理已停止", 2000)
        else:
            folders = self.folder_page.get_all_folders() if self.folder_page else []
            if not folders:
                self.log("WARNING", "请先导入一个包含文件的文件夹。")
                self._show_operation_status("请先添加文件夹", 2500)
                return

            # 快速确认流程
            if not self._quick_confirm_operation():
                return
                
            # 智能预检查
            if not self._smart_pre_check(folders):
                return
                
            # 启动整理线程
            self._start_smart_arrange_thread(folders)

    def _quick_confirm_operation(self):
        """快速确认操作，减少用户交互"""
        operation_type = self.parent.comboBox_operation.currentIndex()
        operation_text = "移动" if operation_type == 0 else "复制"
        
        # 智能生成简洁确认信息
        confirm_message = self._generate_smart_confirmation(operation_type, [])
        
        # 使用更简洁的确认对话框
        reply = QMessageBox.question(
            self,
            f"开始{operation_text}整理",
            confirm_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes  # 默认选择Yes，减少操作步骤
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            self.log("INFO", "用户取消整理操作")
            return False
        return True
        
    def _smart_pre_check(self, folders):
        """智能预检查"""
        try:
            # 检查文件数量
            total_files = 0
            for folder_info in folders:
                folder_path = Path(folder_info['path'])
                if folder_path.exists():
                    if folder_info.get('include_sub', 0):
                        for root, _, files in os.walk(folder_path):
                            total_files += len(files)
                    else:
                        files = os.listdir(folder_path)
                        total_files += len([f for f in files if (folder_path / f).is_file()])
            
            if total_files == 0:
                self.log("WARNING", "未检测到文件")
                self._show_operation_status("文件夹中没有文件", 2000)
                return False
                
            # 检查目标路径
            if self.parent.lineEdit_destination.text():
                dest_path = Path(self.parent.lineEdit_destination.text())
                try:
                    dest_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.log("ERROR", f"无法创建目标文件夹: {str(e)}")
                    self._show_operation_status("目标文件夹创建失败", 2500)
                    return False
                    
            return True
            
        except Exception as e:
            self.log("ERROR", f"预检查失败: {str(e)}")
            return False
            
    def _start_smart_arrange_thread(self, folders):
        """启动智能整理线程"""
        SmartArrange_structure = [
            getattr(self.parent, f'comboBox_level_{i}').currentText()
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]

        file_name_parts = []
        for i in range(self.selected_layout.count()):
            button = self.selected_layout.itemAt(i).widget()
            if isinstance(button, QtWidgets.QPushButton):
                tag_name = button.text()
                if button.property('original_text') == '自定义' and button.property('custom_content') is not None:
                    file_name_parts.append({
                        'tag': tag_name,
                        'content': button.property('custom_content')
                    })
                else:
                    file_name_parts.append({
                        'tag': tag_name,
                        'content': None
                    })

        separator_text = self.parent.comboBox_separator.currentText()
        separator = self.separator_mapping.get(separator_text, "-")
        
        operation_type = self.parent.comboBox_operation.currentIndex()
        operation_text = "移动" if operation_type == 0 else "复制"
        
        if not SmartArrange_structure and not file_name_parts:
            self.log("WARNING", f"执行{operation_text}操作：将文件夹中的所有文件提取到顶层目录")
        elif not SmartArrange_structure:
            self.log("WARNING", f"执行{operation_text}操作：仅重命名文件，不进行分类")
        elif not file_name_parts:
            self.log("WARNING", f"执行{operation_text}操作：仅进行分类，不重命名文件")
        else:
            self.log("WARNING", f"执行{operation_text}操作：进行分类和重命名")
        
        operation_summary = f"操作类型: {operation_text}"
        if SmartArrange_structure:
            operation_summary += f", 分类结构: {' → '.join(SmartArrange_structure)}"
        if file_name_parts:
            filename_tags = []
            for tag_info in file_name_parts:
                if tag_info['content'] is not None:
                    filename_tags.append(tag_info['content'])
                else:
                    filename_tags.append(tag_info['tag'])
            operation_summary += f", 文件名标签: {'+'.join(filename_tags)}"
        if self.destination_root:
            operation_summary += f", 目标路径: {self.destination_root}"
        
        self.log("INFO", f"摘要: {operation_summary}")
        
        self.SmartArrange_thread = SmartArrangeThread(
            parent=self,
            folders=folders,
            classification_structure=SmartArrange_structure or None,
            file_name_structure=file_name_parts or None,
            destination_root=self.destination_root,
            separator=separator,
            time_derive=self.parent.comboBox_timeSource.currentText()
        )
        self.SmartArrange_thread.finished.connect(self.on_thread_finished)
        self.SmartArrange_thread.progress_signal.connect(self.update_progress_bar)
        self.SmartArrange_thread.start()
        self.parent.toolButton_startSmartArrange.setText("停止整理")
        self._show_operation_status("开始整理文件...", 1500)

    def on_thread_finished(self):
        """线程结束处理"""
        self.parent.toolButton_startSmartArrange.setText("开始整理")
        self.SmartArrange_thread = None
        self.update_progress_bar(100)
        
        if hasattr(self, 'SmartArrange_thread') and hasattr(self.SmartArrange_thread, 'error'):
            error_msg = str(self.SmartArrange_thread.error)
            self.log("ERROR", f"整理过程中发生错误: {error_msg}")
            QMessageBox.critical(self, "整理失败", f"操作失败: {error_msg}")
            self._show_operation_status("整理失败", 3000)
        else:
            self.log("INFO", "整理完成")
            QMessageBox.information(self, "整理完成", "文件整理成功！")
            self._show_operation_status("整理完成", 2000)

    def handle_combobox_selection(self, level, index):
        """处理下拉框选择事件"""
        self.update_combobox_state(level)

    def _generate_smart_confirmation(self, operation_type, folders):
        """智能生成确认信息"""
        # 统计文件信息
        total_files = 0
        for folder in folders:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    total_files += len(files)
        
        operation_text = "移动" if operation_type == 0 else "复制"
        
        if total_files == 0:
            return f"{operation_text}模式：未检测到文件，请确保文件夹中包含文件。"
        elif total_files == 1:
            return f"{operation_text}模式：检测到1个文件，将根据标签进行分类整理。"
        else:
            return f"{operation_text}模式：检测到{total_files}个文件，将根据标签进行分类整理。\n\n操作完成后可在目标位置查看结果。"

    def update_combobox_state(self, level):
        current_text = getattr(self.parent, f'comboBox_level_{level}').currentText()
        
        if current_text == "不分类":
            for i in range(level + 1, 6):
                getattr(self.parent, f'comboBox_level_{i}').setEnabled(False)
                getattr(self.parent, f'comboBox_level_{i}').setCurrentIndex(0)
        else:
            if level < 5:
                getattr(self.parent, f'comboBox_level_{level + 1}').setEnabled(True)
                self.update_combobox_state(level + 1)
        
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
        
        self.SmartArrange_settings = [
            getattr(self.parent, f'comboBox_level_{i}').currentText()
            for i in range(1, 6)
            if getattr(self.parent, f'comboBox_level_{i}').isEnabled() and
               getattr(self.parent, f'comboBox_level_{i}').currentText() != "不分类"
        ]
        
        self.update_operation_display()
    
    def update_operation_display(self):
        has_SmartArrange = len(self.SmartArrange_settings) > 0
        
        has_filename = self.selected_layout.count() > 0
        
        if has_SmartArrange and has_filename:
            operation_type = "分类并重命名"
        elif has_SmartArrange and not has_filename:
            operation_type = "仅分类"
        elif not has_SmartArrange and has_filename:
            operation_type = "仅重命名"
        else:
            operation_type = "提取到顶层目录"
        
        operation_mode = "移动" if self.parent.comboBox_operation.currentIndex() == 0 else "复制"
        
        move_color = "#FF6B6B"
        copy_color = "#4ECDC4"
        
        if self.destination_root:
            display_path = str(self.destination_root)
            if len(display_path) > 20:
                display_path = f"{display_path[:8]}...{display_path[-6:]}"
            if operation_mode == "移动":
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{move_color}">{operation_mode}到: {display_path} ({operation_type})</span>'
                )
            else:
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{copy_color}">{operation_mode}到: {display_path} ({operation_type})</span>'
                )
        else:
            if operation_mode == "移动":
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{move_color}">{operation_mode}文件 ({operation_type})</span>'
                )
            else:
                self.parent.label_CopyRoute.setText(
                    f'<span style="color:{copy_color}">{operation_mode}文件 ({operation_type})</span>'
                )
    
    def set_combo_box_states(self):
        self.parent.comboBox_level_1.setEnabled(True)
        for i in range(2, 6):
            combo_box = getattr(self.parent, f'comboBox_level_{i}')
            combo_box.setEnabled(False)
            combo_box.setCurrentIndex(0)
        
        self.update_combobox_state(1)

    def get_specific_value(self, text):
        now = datetime.now()
        return {
            "年份": str(now.year),
            "月份": str(now.month),
            "拍摄设备": "小米",
            "相机型号": "EOS 5D Mark IV",
            "拍摄省份": "江西",
            "拍摄城市": "南昌"
        }.get(text, text)

    def is_valid_windows_filename(self, filename):
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
        if self.selected_layout.count() >= 5:
            return
        
        original_style = button.styleSheet()
        button.setProperty('original_style', original_style)
        
        original_text = button.text()
        button.setProperty('original_text', original_text)
        
        if original_text == '自定义':
            input_dialog = QInputDialog(self)
            input_dialog.setWindowTitle("自定义标签")
            input_dialog.setLabelText("请输入自定义部分的文件名内容:")
            input_dialog.setTextEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            input_dialog.setTextValue("")
            input_dialog.findChild(QtWidgets.QLineEdit).setMaxLength(255)
            
            ok = input_dialog.exec()
            custom_text = input_dialog.textValue()
            
            if ok and custom_text:
                if not self.is_valid_windows_filename(custom_text):
                    QMessageBox.warning(
                        self, 
                        "文件名无效", 
                        f"输入的文件名 '{custom_text}' 不符合Windows命名规范！\n\n"
                        "不允许的字符"
                        "不能使用保留文件名: CON, PRN, AUX, NUL, COM1-9, LPT1-9\n"
                        "不能以点(.)或空格结尾\n"
                        "长度不能超过255个字符\n\n"
                        "请修改后重试。"
                    )
                    return
                
                display_text = custom_text[:3] if len(custom_text) > 3 else custom_text
                button.setText(display_text)
                button.setProperty('custom_content', custom_text)
            else:
                return
        
        self.available_layout.removeWidget(button)
        
        self.selected_layout.addWidget(button)
        
        button.clicked.disconnect()
        button.clicked.connect(lambda checked, b=button: self.move_tag_back(b))
        
        self.update_example_label()
        
        self.update_operation_display()
        
        if self.selected_layout.count() >= 5:
            for btn in self.tag_buttons.values():
                if btn.parent() == self.available_layout:
                    btn.setEnabled(False)
    
    def update_example_label(self):
        now = datetime.now()
        selected_buttons = [self.selected_layout.itemAt(i).widget() for i in range(self.selected_layout.count())
                    if isinstance(self.selected_layout.itemAt(i).widget(), QtWidgets.QPushButton)]
        current_separator = self.separator_mapping.get(self.parent.comboBox_separator.currentText(), "")
        
        example_parts = []
        for button in selected_buttons:
            button_text = button.text()
            if button.property('original_text') == '自定义' and button.property('custom_content') is not None:
                custom_content = button.property('custom_content')
                display_content = custom_content[:3] if len(custom_content) > 3 else custom_content
                example_parts.append(display_content)
            else:
                parts = {
                    "原名": "IMG_1234",
                    "年份": f"{now.year}",
                    "月份": f"{now.month:02d}",
                    "日": f"{now.day:02d}",
                    "星期": f"{self._get_weekday(now)}",
                    "时间": f"{now.strftime('%H%M%S')}",
                    "品牌": "佳能",
                    "型号": "EOS 5D Mark IV",
                    "位置": "浙大",
                    "自定义": "自定义内容"
                }
                full_text = parts.get(button_text, button_text)
                example_parts.append(full_text)
        
        example_text = current_separator.join(example_parts) if example_parts else "请点击标签以组成文件名"
        self.parent.label_PreviewName.setText(example_text)

    @staticmethod
    def _get_weekday(date):
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]

    def handle_log_signal(self, level, message):
        if hasattr(self.parent, 'textEdit_SmartArrange_Log'):
            color_map = {
                'ERROR': '#FF0000',
                'WARNING': '#FFA500',
                'DEBUG': '#008000',
                'INFO': '#8677FD'
            }
            color = color_map.get(level, '#000000')
            self.parent.textEdit_SmartArrange_Log.append(
                f'<span style="color:{color}">{message}</span>')
    
    def log(self, level, message):
        current_time = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        self.log_signal.emit(level, log_message)

    def move_tag_back(self, button):
        self.selected_layout.removeWidget(button)
        
        self.available_layout.addWidget(button)
        
        if button.property('original_style') is not None:
            button.setStyleSheet(button.property('original_style'))
        
        if button.property('original_text') is not None:
            button.setText(button.property('original_text'))
        
        button.clicked.disconnect()
        button.clicked.connect(lambda checked, b=button: self.move_tag(b))
        
        self.update_example_label()
        
        self.update_operation_display()
        
        for btn in self.tag_buttons.values():
            btn.setEnabled(True)
