from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import os

from common import get_resource_path, detect_media_type


class FolderPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_page()
        self.folder_items = []
        self.parent.widget_add_folder.setAcceptDrops(True)
        self.parent.widget_add_folder.dragEnterEvent = self.dragEnterEvent
        self.parent.widget_add_folder.dropEvent = self.dropEvent
        # 设置 widget_add_folder 为可点击区域并更改鼠标指针
        self.parent.widget_add_folder.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        # 连接整个 widget 的点击事件
        self.parent.widget_add_folder.mousePressEvent = self._open_folder_dialog_on_click

    def init_page(self):
        self._connect_buttons()

    def _connect_buttons(self):
        # 保持原有按钮的连接
        self.parent.pushButton_add_folder.clicked.connect(self._open_folder_dialog)
    
    def _open_folder_dialog_on_click(self, event):
        # 捕获 widget_add_folder 的点击事件并打开文件夹对话框
        self._open_folder_dialog()

    def _open_folder_dialog(self):
        folder_paths = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_paths:
            self._check_and_add_folder(folder_paths)

    def _check_and_add_folder(self, folder_path):
        folder_path = os.path.normpath(folder_path)
        folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
        
        # 检查是否已经添加了相同的路径或存在路径冲突
        for item in self.folder_items:
            item_path = os.path.normpath(item['path'])
            if self._paths_equal(item_path, folder_path):
                QMessageBox.warning(self, "路径已存在", f"文件夹路径已经添加:\n{folder_path}")
                return
            if item['include_sub'] and self._is_subpath(folder_path, item_path):
                QMessageBox.warning(self, "路径冲突",
                                    f"您选择的路径是已添加路径（且勾选了包含子文件夹）的子目录:\n\n已添加路径: {item_path}\n当前路径: {folder_path}")
                return
            if self._is_subpath(item_path, folder_path) and item['include_sub']:
                QMessageBox.warning(self, "路径冲突",
                                    f"您选择的路径包含已添加的路径（且已勾选包含子文件夹）:\n\n已添加路径: {item_path}\n当前路径: {folder_path}")
                return
        
        # 创建文件夹项并添加到列表
        self._create_folder_item(folder_path, folder_name)
        
        # 检查文件夹中是否有媒体文件
        self._check_media_files(folder_path)

    def _create_folder_item(self, folder_path, folder_name):
        folder_frame = QtWidgets.QFrame(parent=self.parent.scrollAreaWidgetContents_folds)
        folder_frame.setFixedHeight(48)
        folder_frame.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        layout = QtWidgets.QHBoxLayout(folder_frame)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(10)

        icon_widget = QtWidgets.QWidget(parent=folder_frame)
        icon_widget.setFixedSize(42, 42)
        icon_widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        icon_widget.setStyleSheet(f"image: url({get_resource_path('resources/img/page_0/导入文件夹.svg')}); background-color: transparent;")

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        name_label = QtWidgets.QLabel(folder_name, parent=folder_frame)
        name_label.setMaximumWidth(180)
        name_label.setFont(QtGui.QFont("微软雅黑", 12))
        name_label.setStyleSheet(
            "QLabel {background: transparent; border: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #333; font-weight: 500;}")

        path_label = QtWidgets.QLabel(folder_path, parent=folder_frame)
        path_label.setMaximumWidth(180)
        path_label.setFont(QtGui.QFont("微软雅黑", 9))
        path_label.setStyleSheet(
            "QLabel {background: transparent; border: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #666;}")

        text_layout.addWidget(name_label)
        text_layout.addWidget(path_label)

        include_checkbox = QtWidgets.QCheckBox("包含子文件夹", parent=folder_frame)
        include_checkbox.setFont(QtGui.QFont("微软雅黑", 9))
        include_checkbox.setStyleSheet("QCheckBox {spacing: 4px; background: transparent; color: #666;}")
        include_checkbox.stateChanged.connect(lambda state, f=folder_frame: self._update_include_sub(f, state))
        # 默认自动勾选包含子文件夹
        include_checkbox.setChecked(True)

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

        layout.addWidget(icon_widget)
        layout.addLayout(text_layout)
        layout.addStretch(1)
        layout.addWidget(include_checkbox)
        layout.addWidget(remove_button)

        folder_frame.setStyleSheet(
            "QFrame {background-color: #F5F7FA; border: 1px solid #E0E3E9; border-radius: 8px; margin: 2px;} QFrame:hover {background-color: #EBEFF5; border-color: #C2C9D6;}")

        # 添加到滚动区域
        self.parent.gridLayout_6.addWidget(folder_frame)
        
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

        for i, item in enumerate(self.folder_items[1:], 1):
            self.parent.gridLayout_6.addWidget(item['frame'], i, 0)

        self.parent._update_empty_state(bool(self.folder_items))
        remove_button.clicked.connect(lambda: self.remove_folder_item(folder_frame))

    def _update_include_sub(self, folder_frame, state):
        # 更新文件夹项的包含子文件夹状态
        for item in self.folder_items:
            if item['frame'] == folder_frame:
                current_path = os.path.normpath(item['path'])
                if state:
                    for other in self.folder_items:
                        other_path = os.path.normpath(other['path'])
                        if other['frame'] != folder_frame:
                            if self._is_subpath(current_path, other_path) and other['include_sub']:
                                QMessageBox.warning(self, "操作不允许",
                                                    f"您不能勾选此选项，因为该路径是其他已勾选包含子文件夹的路径的子目录:\n\n父路径: {other_path}\n当前路径: {current_path}")
                                item['checkbox'].setChecked(False)
                                return
                            if self._is_subpath(other_path, current_path):
                                QMessageBox.warning(self, "操作不允许",
                                                    f"您不能勾选此选项，因为该路径包含其他已添加的路径:\n\n子路径: {other_path}\n当前路径: {current_path}")
                                item['checkbox'].setChecked(False)
                                return
                item['include_sub'] = state == QtCore.Qt.CheckState.Checked
                break

    def remove_folder_item(self, folder_frame):
        for item in self.folder_items[:]:
            if item['frame'] == folder_frame:
                item['remove_button'].clicked.disconnect()
                item['checkbox'].stateChanged.disconnect()
                self.parent.gridLayout_6.removeWidget(folder_frame)
                folder_frame.deleteLater()
                self.folder_items.remove(item)
                for row, item in enumerate(self.folder_items):
                    self.parent.gridLayout_6.addWidget(item['frame'], row, 0)
                self.parent._update_empty_state(bool(self.folder_items))
                break



    def _paths_equal(self, path1, path2):
        if os.name == 'nt':
            return os.path.normcase(os.path.normpath(path1)) == os.path.normcase(os.path.normpath(path2))
        return os.path.normpath(path1) == os.path.normpath(path2)

    def _is_subpath(self, path, parent_path):
        try:
            path = os.path.normcase(os.path.normpath(path))
            parent_path = os.path.normcase(os.path.normpath(parent_path))
            return path.startswith(parent_path + os.sep) or path == parent_path
        except (TypeError, AttributeError):
            return False

    def _update_include_sub(self, folder_frame, state):
        # 更新文件夹项的包含子文件夹状态
        for item in self.folder_items:
            if item['frame'] == folder_frame:
                item['include_sub'] = state == QtCore.Qt.CheckState.Checked
                break

    def _show_remove_button(self, folder_frame):
        # 显示移除按钮
        for item in self.parent.gridLayout_6.children():
            if item == folder_frame:
                for child in folder_frame.children():
                    if isinstance(child, QtWidgets.QPushButton) and child.text() == "移除":
                        child.show()
                break

    def _hide_remove_button(self, folder_frame):
        # 隐藏移除按钮
        for item in self.parent.gridLayout_6.children():
            if item == folder_frame:
                for child in folder_frame.children():
                    if isinstance(child, QtWidgets.QPushButton) and child.text() == "移除":
                        child.hide()
                break

    def _remove_folder_item(self, folder_frame):
        # 移除文件夹项
        for i, item in enumerate(self.folder_items):
            if item['frame'] == folder_frame:
                # 从布局中移除
                self.parent.gridLayout_6.removeWidget(folder_frame)
                folder_frame.deleteLater()
                # 从列表中移除
                self.folder_items.pop(i)
                break
        
        # 检查是否还有文件夹，如果没有则显示空状态
        if not self.folder_items:
            self.parent._update_empty_state(False)

    def _check_media_files(self, folder_path):
        # 检查文件夹中是否有媒体文件
        has_media = False
        try:
            # 只检查顶层文件夹
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    try:
                        media_info = detect_media_type(file_path)
                        if media_info['valid']:
                            has_media = True
                            break
                    except:
                        continue
        except Exception as e:
            print(f"检查媒体文件失败: {e}")
        
        # 更新空状态
        if has_media:
            self.parent._update_empty_state(True)

    def get_all_folders(self):
        """获取所有添加的文件夹信息"""
        return self.folder_items

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                folder_path = url.toLocalFile()
                if os.path.isdir(folder_path):
                    self._check_and_add_folder(folder_path)
