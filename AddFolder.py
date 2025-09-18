"""
媒体导入功能模块 - FolderPage类

负责处理:
1. 文件夹的拖拽和选择导入
2. 路径冲突检测和验证
3. 文件夹项UI的创建和管理
4. 子文件夹包含选项处理
"""

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QVBoxLayout, QPushButton, QTextEdit, QDialog
import os

from common import get_resource_path, detect_media_type
from config_manager import config_manager  # 导入配置管理器


class FolderPage(QtWidgets.QWidget):
    """
    媒体导入页面控制器
    
    管理文件夹的添加、移除和冲突检测，提供拖拽和对话框两种导入方式
    """
    
    def __init__(self, parent=None):
        """初始化媒体导入页面"""
        super().__init__(parent)
        self.parent = parent  # 主窗口引用
        self.folder_items = []  # 存储所有文件夹项数据
        self._batch_adding = False  # 批量添加标志，用于控制消息框显示
        
        # 初始化页面设置
        self.init_page()
        
        # 配置拖拽功能
        self._setup_drag_drop()
        
        # 设置点击功能
        self._setup_click_behavior()
        
        # 加载已保存的文件夹路径
        self._load_saved_folders()
    
    def _setup_drag_drop(self):
        """设置拖拽相关配置"""
        self.parent.widget_add_folder.setAcceptDrops(True)
        self.parent.widget_add_folder.dragEnterEvent = self.dragEnterEvent
        self.parent.widget_add_folder.dropEvent = self.dropEvent
    
    def _setup_click_behavior(self):
        """设置点击行为配置"""
        # 设置鼠标指针为手型，提示可点击
        self.parent.widget_add_folder.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        # 连接整个widget的点击事件
        self.parent.widget_add_folder.mousePressEvent = self._open_folder_dialog_on_click

    def init_page(self):
        """初始化页面连接信号槽"""
        # 连接按钮信号
        self.parent.pushButton_add_folder.clicked.connect(self._open_folder_dialog)  # 添加文件夹按钮
        # 移除不存在的按钮连接
        # self.parent.btn_clear_folders.clicked.connect(self._clear_all_folders)  # 清空文件夹按钮（按钮不存在）
        # self.parent.btn_next.clicked.connect(self._on_next_clicked)  # 下一步按钮（按钮不存在）

    def _connect_buttons(self):
        # 保持原有按钮的连接
        self.parent.pushButton_add_folder.clicked.connect(self._open_folder_dialog)
    
    def _open_folder_dialog_on_click(self, event):
        """
        点击widget时打开文件夹选择对话框
        
        处理widget_add_folder区域的点击事件，提供额外的交互方式
        """
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._open_folder_dialog()

    def _open_folder_dialog(self):
        """
        打开文件夹选择对话框
        
        使用系统原生对话框选择文件夹，选择后自动添加到列表
        """
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self._check_and_add_folder(folder_path)

    def _check_and_add_folder(self, folder_path):
        """
        检查并添加文件夹
        
        执行路径验证、冲突检查，通过后创建文件夹项
        增强版：更健壮地处理各种路径关系和重复导入场景
        """
        try:
            # 规范化路径，处理不同表示形式的相同路径
            folder_path = os.path.normpath(folder_path)
            folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
            
            # 检查文件夹是否存在
            if not os.path.exists(folder_path):
                QMessageBox.warning(
                    self, 
                    "路径不存在", 
                    f"文件夹路径不存在:\n\n{folder_path}\n\n"
                    "请确认文件夹位置没有被移动或删除。"
                )
                return
                
            if not os.path.isdir(folder_path):
                QMessageBox.warning(
                    self, 
                    "不是文件夹", 
                    f"选择的路径不是一个文件夹:\n\n{folder_path}\n\n"
                    "请选择一个有效的文件夹。"
                )
                return
                
            # 检查是否有权限访问该文件夹
            try:
                # 尝试列出文件夹内容以检查权限
                os.listdir(folder_path)
            except PermissionError:
                QMessageBox.warning(
                    self, 
                    "无访问权限", 
                    f"没有足够的权限访问文件夹:\n\n{folder_path}\n\n"
                    "请确保您拥有访问该文件夹的权限。"
                )
                return
            except Exception as e:
                QMessageBox.warning(
                    self, 
                    "访问错误", 
                    f"访问文件夹时发生错误:\n\n{folder_path}\n\n"
                    f"错误信息: {str(e)}"
                )
                return
                
            # 检查是否已经添加了相同的路径
            for item in self.folder_items:
                if self._paths_equal(item['path'], folder_path):
                    QMessageBox.information(
                        self, 
                        "路径已存在", 
                        f"文件夹 '{folder_name}' 已经添加:\n\n{folder_path}\n\n"
                        "无需重复添加相同的文件夹。"
                    )
                    return
                    
            # 检查路径冲突（子目录关系和包含关系）
            conflict_info = None
            
            # 先检查是否存在父目录关系且父目录勾选了包含子文件夹
            for item in self.folder_items:
                item_path = os.path.normpath(item['path'])
                
                # 情况1: 待添加路径是已存在路径的子目录，且父路径勾选了包含子文件夹
                if item['include_sub'] and self._is_subpath(folder_path, item_path):
                    conflict_info = {
                        'type': 1,
                        'parent_path': item_path,
                        'parent_name': os.path.basename(item_path)
                    }
                    break
                
                # 情况2: 待添加路径包含已存在的路径，且子路径勾选了包含子文件夹
                if self._is_subpath(item_path, folder_path) and item['include_sub']:
                    conflict_info = {
                        'type': 2,
                        'child_path': item_path,
                        'child_name': os.path.basename(item_path)
                    }
                    break
            
            # 处理路径冲突
            if conflict_info:
                if conflict_info['type'] == 1:
                    # 创建自定义消息框，提供解决方案选项
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("路径冲突")
                    msg_box.setText(f"该文件夹是 '{conflict_info['parent_name']}' 的子目录，且 '{conflict_info['parent_name']}' 已选择包含子文件夹")
                    msg_box.setInformativeText("您可以选择以下操作：")
                    
                    # 添加按钮
                    continue_btn = msg_box.addButton("继续添加", QMessageBox.ButtonRole.ActionRole)
                    disable_sub_btn = msg_box.addButton("取消父文件夹的子文件夹选项", QMessageBox.ButtonRole.ActionRole)
                    cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
                    
                    # 设置默认按钮
                    msg_box.setDefaultButton(cancel_btn)
                    
                    # 显示消息框并获取用户选择
                    msg_box.exec()
                    
                    # 处理用户选择
                    if msg_box.clickedButton() == continue_btn:
                        # 用户选择继续添加，即使存在冲突
                        pass  # 继续执行下面的代码
                    elif msg_box.clickedButton() == disable_sub_btn:
                        # 用户选择取消父文件夹的子文件夹选项
                        for item in self.folder_items:
                            if self._paths_equal(item['path'], conflict_info['parent_path']):
                                item['checkbox'].setChecked(False)
                                # 立即更新配置
                                config_manager.update_folder_include_sub(item['path'], False)
                                break
                        # 取消后再次尝试添加
                        self._check_and_add_folder(folder_path)
                        return
                    else:
                        # 用户选择取消添加
                        return
                else:  # conflict_info['type'] == 2
                    QMessageBox.warning(
                        self, 
                        "路径冲突",
                        f"'{conflict_info['child_name']}' 是该文件夹的子目录，且 '{conflict_info['child_name']}' 已选择包含子文件夹\n\n"
                        f"请先取消勾选 '{conflict_info['child_name']}' 的'包含子文件夹'选项，再添加该文件夹。"
                    )
                    return
            
            # 创建文件夹项并添加到列表
            self._create_folder_item(folder_path, folder_name)
            
            # 检查文件夹中是否有媒体文件
            self._check_media_files(folder_path)
            
        except Exception as e:
            print(f"添加文件夹过程中发生错误: {e}")
            QMessageBox.critical(
                self, 
                "添加失败", 
                f"添加文件夹时发生错误：{str(e)}\n\n"
                f"请检查文件夹路径和权限后重试。"
            )

    def _create_folder_item(self, folder_path, folder_name):
        """
        创建文件夹项UI
        
        构建包含图标、名称、路径、包含子文件夹选项和移除按钮的文件夹项
        """
        # 创建文件夹项框架
        folder_frame = QtWidgets.QFrame(parent=self.parent.scrollAreaWidgetContents_folds)
        folder_frame.setFixedHeight(48)
        folder_frame.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        layout = QtWidgets.QHBoxLayout(folder_frame)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(10)

        # 文件夹图标
        icon_widget = QtWidgets.QWidget(parent=folder_frame)
        icon_widget.setFixedSize(42, 42)
        icon_widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        icon_widget.setStyleSheet(f"image: url({get_resource_path('resources/img/page_0/导入文件夹.svg')}); background-color: transparent;")

        # 文本布局（名称和路径）
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        # 文件夹名称标签
        name_label = QtWidgets.QLabel(folder_name, parent=folder_frame)
        name_label.setMaximumWidth(180)
        name_label.setFont(QtGui.QFont("微软雅黑", 12))
        name_label.setStyleSheet(
            "QLabel {background: transparent; border: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #333; font-weight: 500;}")

        # 文件夹路径标签
        path_label = QtWidgets.QLabel(folder_path, parent=folder_frame)
        path_label.setMaximumWidth(180)
        path_label.setFont(QtGui.QFont("微软雅黑", 9))
        path_label.setStyleSheet(
            "QLabel {background: transparent; border: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #666;}")

        text_layout.addWidget(name_label)
        text_layout.addWidget(path_label)

        # 包含子文件夹复选框
        include_checkbox = QtWidgets.QCheckBox("包含子文件夹", parent=folder_frame)
        include_checkbox.setFont(QtGui.QFont("微软雅黑", 9))
        include_checkbox.setStyleSheet("QCheckBox {spacing: 4px; background: transparent; color: #666;}")
        include_checkbox.stateChanged.connect(lambda state, f=folder_frame: self._update_include_sub(f, state))
        # 默认自动勾选包含子文件夹
        include_checkbox.setChecked(True)

        # 移除按钮（默认隐藏）
        remove_button = QtWidgets.QPushButton("移除", parent=folder_frame)
        remove_button.setFixedSize(60, 30)
        remove_button.setFont(QtGui.QFont("微软雅黑", 9))
        remove_button.setStyleSheet(
            "QPushButton {background-color: #FF5A5A; color: white; border: none; border-radius: 6px; font-weight: 500;} QPushButton:hover {background-color: #FF3B3B;} QPushButton:pressed {background-color: #E03535;}")
        remove_button.hide()

        # 鼠标悬停时显示移除按钮
        folder_frame.enterEvent = lambda e: self._show_remove_button(folder_frame)
        folder_frame.leaveEvent = lambda e: self._hide_remove_button(folder_frame)

        # 连接移除按钮信号
        remove_button.clicked.connect(lambda: self._remove_folder_item(folder_frame))

        # 添加到布局
        layout.addWidget(icon_widget)
        layout.addLayout(text_layout)
        layout.addStretch(1)
        layout.addWidget(include_checkbox)
        layout.addWidget(remove_button)

        # 设置文件夹项样式
        folder_frame.setStyleSheet(
            "QFrame {background-color: #F5F7FA; border: 1px solid #E0E3E9; border-radius: 8px; margin: 2px;} QFrame:hover {background-color: #EBEFF5; border-color: #C2C9D6;}")

        # 添加到滚动区域
        self.parent.gridLayout_6.addWidget(folder_frame)
        
        # 自定义鼠标悬停事件处理
        def enter_event(event):
            remove_button.show()
            QtWidgets.QFrame.enterEvent(folder_frame, event)

        def leave_event(event):
            remove_button.hide()
            QtWidgets.QFrame.leaveEvent(folder_frame, event)

        folder_frame.enterEvent = enter_event
        folder_frame.leaveEvent = leave_event

        # 创建完整的文件夹项数据
        item_data = {
            'frame': folder_frame,
            'name_label': name_label,
            'path_label': path_label,
            'remove_button': remove_button,
            'path': folder_path,
            'name': folder_name,
            'include_sub': include_checkbox.isChecked(),
            'checkbox': include_checkbox
        }

        self.folder_items.append(item_data)
        self.parent.gridLayout_6.addWidget(folder_frame, 0, 0)

        # 重新排列所有文件夹项
        for i, item in enumerate(self.folder_items[1:], 1):
            self.parent.gridLayout_6.addWidget(item['frame'], i, 0)

        # 设置布局对齐方式为顶部对齐，避免单个项目垂直居中
        # 只在有文件夹项时设置拉伸策略，空状态时保持默认居中
        if len(self.folder_items) == 1:
            self.parent.gridLayout_6.setRowStretch(0, 0)  # 第一行不拉伸
            self.parent.gridLayout_6.setRowStretch(1, 1)   # 第二行拉伸以填充剩余空间
        elif len(self.folder_items) > 1:
            # 多个项目时恢复默认拉伸
            for i in range(len(self.folder_items)):
                self.parent.gridLayout_6.setRowStretch(i, 0)
            self.parent.gridLayout_6.setRowStretch(len(self.folder_items), 1)

        # 更新空状态显示
        self.parent._update_empty_state(bool(self.folder_items))
        remove_button.clicked.connect(lambda: self.remove_folder_item(folder_frame))
        
        # 保存文件夹路径到配置
        config_manager.add_folder(folder_path)

    def _update_include_sub(self, folder_frame, state):
        """
        更新包含子文件夹状态
        
        增强版：处理复选框状态变化，更全面地检查路径冲突并更新状态
        """
        try:
            # 更新文件夹项的包含子文件夹状态
            for item in self.folder_items:
                if item['frame'] == folder_frame:
                    current_path = os.path.normpath(item['path'])
                    include_sub = state == QtCore.Qt.CheckState.Checked
                    
                    # 当用户尝试勾选包含子文件夹时，进行全面的冲突检查
                    if include_sub:
                        # 遍历所有其他已添加的文件夹
                        conflict_found = False
                        conflict_type = 0
                        conflict_path = ""
                        
                        for other in self.folder_items:
                            if other['frame'] == folder_frame:
                                continue  # 跳过当前文件夹
                                
                            other_path = os.path.normpath(other['path'])
                            
                            # 情况1: 当前路径是其他文件夹的子目录，且父文件夹已勾选包含子文件夹
                            if self._is_subpath(current_path, other_path) and other['include_sub']:
                                conflict_found = True
                                conflict_type = 1
                                conflict_path = other_path
                                break
                                
                            # 情况2: 当前路径包含其他文件夹，且该文件夹已存在
                            if self._is_subpath(other_path, current_path):
                                conflict_found = True
                                conflict_type = 2
                                conflict_path = other_path
                                break
                        
                        if conflict_found:
                            # 如果是批量添加模式，我们静默拒绝而不显示消息框
                            if hasattr(self, '_batch_adding') and self._batch_adding:
                                item['checkbox'].setChecked(False)
                                return
                            
                            if conflict_type == 1:
                                # 创建自定义消息框，提供解决方案选项
                                msg_box = QMessageBox(self)
                                msg_box.setWindowTitle("操作不允许")
                                msg_box.setText(f"操作被阻止！\n\n"
                                "您要勾选的文件夹是其他已勾选包含子文件夹的路径的子目录。")
                                msg_box.setInformativeText(f"• 父路径: {os.path.basename(conflict_path)}\n"
                                f"• 当前路径: {os.path.basename(current_path)}")
                                
                                # 添加按钮
                                cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
                                disable_parent_btn = msg_box.addButton("取消父文件夹的子文件夹选项", QMessageBox.ButtonRole.ActionRole)
                                
                                # 设置默认按钮
                                msg_box.setDefaultButton(cancel_btn)
                                
                                # 显示消息框并获取用户选择
                                msg_box.exec()
                                
                                # 处理用户选择
                                if msg_box.clickedButton() == disable_parent_btn:
                                    # 用户选择取消父文件夹的子文件夹选项
                                    for other_item in self.folder_items:
                                        if self._paths_equal(other_item['path'], conflict_path):
                                            other_item['checkbox'].setChecked(False)
                                            # 立即更新配置
                                            config_manager.update_folder_include_sub(other_item['path'], False)
                                            # 现在可以安全地启用当前文件夹的选项
                                            item['include_sub'] = True
                                            config_manager.update_folder_include_sub(current_path, True)
                                            break
                            else:
                                QMessageBox.warning(
                                    self, 
                                    "操作不允许",
                                    f"操作被阻止！\n\n"
                                    f"您不能勾选此选项，因为该路径包含其他已添加的路径:\n\n"
                                    f"• 子路径: {os.path.basename(conflict_path)}\n"
                                    f"• 当前路径: {os.path.basename(current_path)}\n\n"
                                    "为了避免文件处理冲突，请先移除子路径。"
                                )
                                
                                item['checkbox'].setChecked(False)
                                return
                            
                    # 没有冲突，可以安全地更新状态
                    item['include_sub'] = include_sub
                    # 更新配置文件中的包含子文件夹状态
                    config_manager.update_folder_include_sub(current_path, include_sub)
                    break
        except Exception as e:
            print(f"更新包含子文件夹选项时出错: {e}")
            # 在非批量模式下显示错误消息
            if not (hasattr(self, '_batch_adding') and self._batch_adding):
                QMessageBox.critical(
                    self, 
                    "操作失败", 
                    f"更新文件夹选项时发生错误：{str(e)}\n\n"
                    f"请稍后重试。"
                )

    def remove_folder_item(self, folder_frame):
        """
        移除文件夹项
        
        从UI和数据中完全移除指定的文件夹项
        """
        # 统一使用内部方法处理，避免代码冗余
        self._remove_folder_item(folder_frame)

    def _paths_equal(self, path1, path2):
        """
        检查两个路径是否相等
        
        增强版：更健壮地处理Windows大小写不敏感和不同表示形式的相同路径
        """
        try:
            # 规范化路径，处理尾部斜杠、相对路径等差异
            norm_path1 = os.path.normcase(os.path.normpath(path1))
            norm_path2 = os.path.normcase(os.path.normpath(path2))
            
            # 在Windows上，额外确保驱动器号大小写一致
            if os.name == 'nt':
                # 处理UNC路径和本地路径
                if norm_path1.startswith('//') and norm_path2.startswith('//'):
                    return norm_path1 == norm_path2
                # 处理本地路径
                drive1 = os.path.splitdrive(norm_path1)[0].lower()
                drive2 = os.path.splitdrive(norm_path2)[0].lower()
                path_part1 = norm_path1[len(drive1):]
                path_part2 = norm_path2[len(drive2):]
                return drive1 == drive2 and path_part1 == path_part2
            
            return norm_path1 == norm_path2
        except (TypeError, AttributeError):
            return False

    def _is_subpath(self, path, parent_path):
        """
        检查路径是否为子路径
        
        增强版：更精确地判断一个路径是否是另一个路径的子目录，处理各种边界情况
        """
        try:
            # 规范化路径
            path = os.path.normcase(os.path.normpath(path))
            parent_path = os.path.normcase(os.path.normpath(parent_path))
            
            # 确保父路径以路径分隔符结尾，避免部分匹配问题
            # 例如，避免将 'C:\folder123' 误认为是 'C:\folder' 的子目录
            parent_path_with_sep = parent_path
            if not parent_path.endswith(os.sep):
                parent_path_with_sep = parent_path + os.sep
            
            # 完全相等的路径或真正的子目录路径
            return path == parent_path or path.startswith(parent_path_with_sep)
        except (TypeError, AttributeError, ValueError):
            return False

    def _show_remove_button(self, folder_frame):
        """显示移除按钮（鼠标悬停时）"""
        # 显示移除按钮
        for item in self.parent.gridLayout_6.children():
            if item == folder_frame:
                for child in folder_frame.children():
                    if isinstance(child, QtWidgets.QPushButton) and child.text() == "移除":
                        child.show()
                break

    def _hide_remove_button(self, folder_frame):
        """隐藏移除按钮（鼠标离开时）"""
        # 隐藏移除按钮
        for item in self.parent.gridLayout_6.children():
            if item == folder_frame:
                for child in folder_frame.children():
                    if isinstance(child, QtWidgets.QPushButton) and child.text() == "移除":
                        child.hide()
                break

    def _remove_folder_item(self, folder_frame):
        """
        移除文件夹项（内部方法）
        """
        try:
            # 移除文件夹项
            for i, item in enumerate(self.folder_items):
                if item['frame'] == folder_frame:
                    # 断开信号连接，避免内存泄漏
                    try:
                        item['remove_button'].clicked.disconnect()
                        item['checkbox'].stateChanged.disconnect()
                    except TypeError:
                        # 信号可能已经被断开，忽略错误
                        pass
                    
                    # 从布局中移除
                    self.parent.gridLayout_6.removeWidget(folder_frame)
                    folder_frame.deleteLater()
                    
                    # 先保存要移除的文件夹路径
                    folder_path = item['path']
                    
                    # 从列表中移除
                    self.folder_items.pop(i)
                    
                    # 从配置中移除文件夹路径，添加错误处理
                    try:
                        config_manager.remove_folder(folder_path)
                    except Exception as e:
                        print(f"移除文件夹配置失败: {e}")
                    break
            
            # 重新排列剩余的文件夹项，修复只移除选中项的问题
            # 移除所有已有的布局项但不删除widget
            for i in reversed(range(self.parent.gridLayout_6.count())):
                layout_item = self.parent.gridLayout_6.itemAt(i)
                if layout_item and layout_item.widget():
                    self.parent.gridLayout_6.removeItem(layout_item)
            
            # 重新添加所有剩余的文件夹项
            for row, item in enumerate(self.folder_items):
                self.parent.gridLayout_6.addWidget(item['frame'], row, 0)
            
            # 设置布局对齐方式
            if len(self.folder_items) == 1:
                self.parent.gridLayout_6.setRowStretch(0, 0)  # 第一行不拉伸
                self.parent.gridLayout_6.setRowStretch(1, 1)   # 第二行拉伸以填充剩余空间
            elif len(self.folder_items) > 1:
                # 多个项目时恢复默认拉伸
                for i in range(len(self.folder_items)):
                    self.parent.gridLayout_6.setRowStretch(i, 0)
                self.parent.gridLayout_6.setRowStretch(len(self.folder_items), 1)
            
            # 更新空状态
            self.parent._update_empty_state(bool(self.folder_items))
        except Exception as e:
            print(f"移除文件夹项失败: {e}")
            QMessageBox.warning(
                self, 
                "操作失败", 
                f"移除文件夹时发生错误：{str(e)}"
            )

    def _check_media_files(self, folder_path):
        """
        检查文件夹中是否有媒体文件
        
        快速扫描顶层文件夹，检测支持的媒体文件格式
        """
        # 检查文件夹中是否有媒体文件
        has_media = False
        try:
            # 只检查顶层文件夹以保持性能
            file_count = 0
            max_check_files = 200  # 最多检查200个文件以避免性能问题
            
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    try:
                        # 先通过扩展名快速判断，减少不必要的文件读取
                        ext = os.path.splitext(file)[1].lower()
                        common_media_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff', '.heic', '.heif',
                                            '.mp4', '.mov', '.avi', '.mkv', '.flv', '.3gp', '.wmv',
                                            '.mp3', '.flac', '.wav', '.aac', '.ogg']
                        
                        if ext in common_media_exts:
                            has_media = True
                            break
                        
                        # 对于不常见的扩展名，使用detect_media_type函数进一步检查
                        media_info = detect_media_type(file_path)
                        if media_info['valid']:
                            has_media = True
                            break
                    except Exception as e:
                        # 忽略单个文件的检查错误
                        print(f"检查文件 {file} 失败: {e}")
                        continue
                    
                # 限制检查的文件数量
                file_count += 1
                if file_count >= max_check_files:
                    break
        except Exception as e:
            print(f"检查媒体文件失败: {e}")
        
        # 更新空状态
        if has_media:
            self.parent._update_empty_state(True)

    def get_all_folders(self):
        """获取所有添加的文件夹信息"""
        return self.folder_items

    def dragEnterEvent(self, event):
        """
        拖拽进入事件处理
        
        检查拖拽内容是否包含URL（文件/文件夹路径），如果是则接受拖拽操作
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """
        拖拽释放事件处理
        
        处理拖拽释放的文件/文件夹，只处理本地文件夹路径
        """
        urls = event.mimeData().urls()
        
        # 过滤出本地文件夹
        folder_paths = []
        for url in urls:
            if url.isLocalFile():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    folder_paths.append(path)
        
        if not folder_paths:
            QMessageBox.information(
                self, 
                "操作提示", 
                "未找到有效的文件夹路径。请确保您拖拽的是本地文件夹。"
            )
            return
        
        # 批量添加文件夹
        total = len(folder_paths)
        added_count = 0
        skipped_count = 0
        error_count = 0
        
        # 创建一个临时标志来控制_check_and_add_folder中的消息框显示
        self._batch_adding = True
        
        # 显示进度对话框
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowTitle("正在添加文件夹")
        progress_dialog.setLabelText(f"准备处理 {total} 个文件夹...")
        progress_dialog.setRange(0, total)
        progress_dialog.setCancelButtonText("取消")
        progress_dialog.setValue(0)
        progress_dialog.show()
        
        # 为每个文件夹创建结果记录
        results = {
            'added': [],
            'skipped': [],
            'error': []
        }
        
        for i, folder_path in enumerate(folder_paths):
            # 检查用户是否取消
            if progress_dialog.wasCanceled():
                QMessageBox.information(self, "操作已取消", "文件夹添加操作已被取消。")
                break
            
            # 更新进度
            folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
            progress_dialog.setLabelText(f"正在处理第 {i+1}/{total} 个文件夹...\n\n当前: {folder_name}")
            progress_dialog.setValue(i)
            
            # 强制更新UI
            QtCore.QCoreApplication.processEvents()
            
            try:
                # 检查路径基本有效性
                if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                    skipped_count += 1
                    results['skipped'].append((folder_path, "路径不存在或不是文件夹"))
                    continue
                
                # 检查是否有权限访问该文件夹
                try:
                    os.listdir(folder_path)
                except PermissionError:
                    skipped_count += 1
                    results['skipped'].append((folder_path, "无访问权限"))
                    continue
                
                # 规范化路径
                folder_path = os.path.normpath(folder_path)
                
                # 执行冲突检查（使用简化版逻辑，避免在批量处理中弹出过多对话框）
                has_conflict = False
                conflict_reason = ""
                
                for item in self.folder_items:
                    item_path = os.path.normpath(item['path'])
                    
                    # 情况1: 完全相同的路径
                    if self._paths_equal(item_path, folder_path):
                        has_conflict = True
                        conflict_reason = "已存在相同路径"
                        break
                        
                    # 情况2: 待添加路径是已存在路径的子目录，且父路径勾选了包含子文件夹
                    if item['include_sub'] and self._is_subpath(folder_path, item_path):
                        has_conflict = True
                        conflict_reason = f"是已添加文件夹 '{os.path.basename(item_path)}' 的子目录且父目录已勾选包含子文件夹"
                        break
                        
                    # 情况3: 待添加路径包含已存在的路径，且子路径勾选了包含子文件夹
                    if self._is_subpath(item_path, folder_path) and item['include_sub']:
                        has_conflict = True
                        conflict_reason = f"包含已添加文件夹 '{os.path.basename(item_path)}' 且子目录已勾选包含子文件夹"
                        break
                
                if has_conflict:
                    skipped_count += 1
                    results['skipped'].append((folder_path, conflict_reason))
                    continue
                
                # 无冲突，添加文件夹
                folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
                self._create_folder_item(folder_path, folder_name)
                added_count += 1
                results['added'].append(folder_path)
                
                # 检查文件夹中是否有媒体文件
                self._check_media_files(folder_path)
                
            except Exception as e:
                print(f"添加文件夹 {folder_path} 失败: {e}")
                error_count += 1
                results['error'].append((folder_path, str(e)))
        
        # 重置批量添加标志
        self._batch_adding = False
        
        # 关闭进度对话框
        progress_dialog.close()
        
        # 显示详细总结
        if added_count > 0 or skipped_count > 0 or error_count > 0:
            message = ""
            details = []
            
            if added_count > 0:
                message += f"成功添加 {added_count} 个文件夹\n"
                for path in results['added']:
                    details.append(f"  ✓ {os.path.basename(path)} ({path})")
                details.append("")
            
            if skipped_count > 0:
                message += f"跳过 {skipped_count} 个文件夹\n"
                for path, reason in results['skipped']:
                    details.append(f"  ⚠️ {os.path.basename(path)} - {reason}")
                details.append("")
            
            if error_count > 0:
                message += f"{error_count} 个文件夹添加失败\n"
                for path, reason in results['error']:
                    details.append(f"  ✗ {os.path.basename(path)} - {reason}")
            
            # 创建详细信息对话框
            if details:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("添加完成")
                msg_box.setText(message)
                
                # 添加详细信息按钮
                details_btn = msg_box.addButton("查看详情", QMessageBox.ButtonRole.ActionRole)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
                
                # 显示消息框并处理按钮点击
                msg_box.exec()
                
                # 如果用户点击了查看详情按钮
                if msg_box.clickedButton() == details_btn:
                    details_dialog = QDialog(self)
                    details_dialog.setWindowTitle("添加详情")
                    details_dialog.resize(600, 400)
                    
                    # 创建文本浏览器显示详细信息
                    text_browser = QTextEdit()
                    text_browser.setReadOnly(True)
                    text_browser.setPlainText("\n".join(details))
                    
                    # 创建关闭按钮
                    close_btn = QPushButton("关闭")
                    close_btn.clicked.connect(details_dialog.close)
                    
                    # 创建布局
                    layout = QVBoxLayout()
                    layout.addWidget(text_browser)
                    layout.addWidget(close_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
                    
                    details_dialog.setLayout(layout)
                    details_dialog.exec()
            else:
                QMessageBox.information(
                    self, 
                    "添加完成", 
                    message
                )

    def _load_saved_folders(self):
        """
        加载已保存的文件夹路径
        
        增强版：在加载过程中进行路径冲突检测，自动处理无效路径和重复路径
        """
        # 获取所有保存的文件夹
        saved_folders = config_manager.get_folders()
        loaded_paths = []  # 跟踪已加载的有效路径
        invalid_paths = []  # 跟踪无效路径
        
        for folder_info in saved_folders:
            folder_path = folder_info["path"]
            folder_path = os.path.normpath(folder_path)
            
            # 检查路径是否存在且有效
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                # 检查是否与已加载的路径存在冲突
                has_conflict = False
                for loaded_path in loaded_paths:
                    if self._paths_equal(folder_path, loaded_path):
                        # 重复路径，跳过
                        has_conflict = True
                        break
                    
                if not has_conflict:
                    # 无冲突，加载文件夹
                    self._create_folder_item(folder_path, os.path.basename(folder_path))
                    loaded_paths.append(folder_path)
            else:
                # 路径无效，记录以便后续移除
                invalid_paths.append(folder_path)
        
        # 从配置中移除所有无效路径
        for invalid_path in invalid_paths:
            config_manager.remove_folder(invalid_path)
            
        # 如果有无效路径，通知用户
        if invalid_paths:
            QMessageBox.information(
                self, 
                "文件夹更新", 
                f"检测到 {len(invalid_paths)} 个文件夹路径已无效（可能已被移动或删除），\n\n" \
                "这些路径已从配置中自动移除。"
            )
        
        # 确保在加载完成后更新空状态
        self.parent._update_empty_state(bool(self.folder_items))