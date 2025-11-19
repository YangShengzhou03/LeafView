from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QVBoxLayout, QPushButton, QTextEdit, QDialog
import os
import pathlib
from collections import Counter

from common import get_resource_path, detect_media_type
from config_manager import config_manager


class FolderPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_items = []
        self._batch_adding = False
        self.init_page()
        self._setup_drag_drop()
        self._setup_click_behavior()
        self._setup_context_menu()
        self._load_saved_folders()
    
    def _setup_drag_drop(self):
        self.parent.widget_add_folder.setAcceptDrops(True)
        self.parent.widget_add_folder.dragEnterEvent = self.dragEnterEvent
        self.parent.widget_add_folder.dropEvent = self.dropEvent
    
    def _setup_click_behavior(self):
        self.parent.widget_add_folder.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.parent.widget_add_folder.mousePressEvent = self._open_folder_dialog_on_click

    def _setup_context_menu(self):
        """设置右键菜单"""
        self.parent.scrollAreaWidgetContents_folds.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.parent.scrollAreaWidgetContents_folds.customContextMenuRequested.connect(self._show_context_menu)

    def init_page(self):
        self.parent.pushButton_add_folder.clicked.connect(self._open_folder_dialog)

    def _connect_buttons(self):
        self.parent.pushButton_add_folder.clicked.connect(self._open_folder_dialog)
    
    def _open_folder_dialog_on_click(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._open_folder_dialog()

    def _open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self._check_and_add_folder(folder_path)

    def _check_and_add_folder(self, folder_path):
        try:
            folder_path = os.path.normpath(folder_path)
            folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
            
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
                
            try:
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
                
            for item in self.folder_items:
                if self._paths_equal(item['path'], folder_path):
                    QMessageBox.information(
                        self, 
                        "路径已存在", 
                        f"文件夹 '{folder_name}' 已经添加:\n\n{folder_path}\n\n"
                        "无需重复添加相同的文件夹。"
                    )
                    return
                    
            conflict_info = None
            
            for item in self.folder_items:
                item_path = os.path.normpath(item['path'])
                
                if item['include_sub'] and self._is_subpath(folder_path, item_path):
                    conflict_info = {
                        'type': 1,
                        'parent_path': item_path,
                        'parent_name': os.path.basename(item_path)
                    }
                    break
                
                if self._is_subpath(item_path, folder_path) and item['include_sub']:
                    conflict_info = {
                        'type': 2,
                        'child_path': item_path,
                        'child_name': os.path.basename(item_path)
                    }
                    break
            
            if conflict_info:
                if conflict_info['type'] == 1:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("路径冲突")
                    msg_box.setText(f"该文件夹是 '{conflict_info['parent_name']}' 的子目录，且 '{conflict_info['parent_name']}'"
                                    f" 包含子文件夹")
                    msg_box.setInformativeText("您可以选择以下操作：")
                    
                    continue_btn = msg_box.addButton("继续添加", QMessageBox.ButtonRole.ActionRole)
                    disable_sub_btn = msg_box.addButton("取消父文件夹的子文件夹选项", QMessageBox.ButtonRole.ActionRole)
                    cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
                    
                    msg_box.setDefaultButton(cancel_btn)
                    msg_box.exec()
                    
                    if msg_box.clickedButton() == continue_btn:
                        pass
                    elif msg_box.clickedButton() == disable_sub_btn:
                        for item in self.folder_items:
                            if self._paths_equal(item['path'], conflict_info['parent_path']):
                                item['checkbox'].setChecked(False)
                                config_manager.update_folder_include_sub(item['path'], False)
                                break
                        self._check_and_add_folder(folder_path)
                        return
                    else:
                        return
                else:
                    QMessageBox.warning(
                        self, 
                        "路径冲突",
                        f"'{conflict_info['child_name']}' 是该文件夹的子目录，且 '{conflict_info['child_name']}' 已选择包含子文件夹\n\n"
                        f"请先取消勾选 '{conflict_info['child_name']}' 的'包含子文件夹'选项，再添加该文件夹。"
                    )
                    return
            
            self._create_folder_item(folder_path, folder_name)
            self._check_media_files(folder_path)
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "添加失败", 
                f"添加文件夹时发生错误：{str(e)}\n\n"
                f"请检查文件夹路径和权限后重试。"
            )

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
        include_checkbox.setChecked(True)

        remove_button = QtWidgets.QPushButton("移除", parent=folder_frame)
        remove_button.setFixedSize(60, 30)
        remove_button.setFont(QtGui.QFont("微软雅黑", 9))
        remove_button.setStyleSheet(
            "QPushButton {background-color: #FF5A5A; color: white; border: none; border-radius: 6px; font-weight: 500;} QPushButton:hover {background-color: #FF3B3B;} QPushButton:pressed {background-color: #E03535;}")
        remove_button.hide()

        folder_frame.enterEvent = lambda e: self._show_remove_button(folder_frame)
        folder_frame.leaveEvent = lambda e: self._hide_remove_button(folder_frame)

        remove_button.clicked.connect(lambda: self._remove_folder_item(folder_frame))

        layout.addWidget(icon_widget)
        layout.addLayout(text_layout)
        layout.addStretch(1)
        layout.addWidget(include_checkbox)
        layout.addWidget(remove_button)

        folder_frame.setStyleSheet(
            "QFrame {background-color: #F5F7FA; border: 1px solid #E0E3E9; border-radius: 8px; margin: 2px;} QFrame:hover {background-color: #EBEFF5; border-color: #C2C9D6;}")

        self.parent.gridLayout_6.addWidget(folder_frame)
        
        def enter_event(event):
            remove_button.show()
            QtWidgets.QFrame.enterEvent(folder_frame, event)

        def leave_event(event):
            remove_button.hide()
            QtWidgets.QFrame.leaveEvent(folder_frame, event)

        folder_frame.enterEvent = enter_event
        folder_frame.leaveEvent = leave_event

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

        if len(self.folder_items) == 1:
            self.parent.gridLayout_6.setRowStretch(0, 0)
            self.parent.gridLayout_6.setRowStretch(1, 1)
        elif len(self.folder_items) > 1:
            for i in range(len(self.folder_items)):
                self.parent.gridLayout_6.setRowStretch(i, 0)
            self.parent.gridLayout_6.setRowStretch(len(self.folder_items), 1)

        self.parent._update_empty_state(bool(self.folder_items))
        remove_button.clicked.connect(lambda: self.remove_folder_item(folder_frame))
        
        # 为文件夹项添加右键菜单
        folder_frame.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        folder_frame.customContextMenuRequested.connect(
            lambda pos, item_data=item_data: self._show_folder_item_menu(pos, item_data)
        )
        
        config_manager.add_folder(folder_path)

    def _update_include_sub(self, folder_frame, state):
        try:
            for item in self.folder_items:
                if item['frame'] == folder_frame:
                    current_path = os.path.normpath(item['path'])
                    include_sub = state == QtCore.Qt.CheckState.Checked
                    
                    if include_sub:
                        conflict_found = False
                        conflict_type = 0
                        conflict_path = ""
                        
                        for other in self.folder_items:
                            if other['frame'] == folder_frame:
                                continue
                                
                            other_path = os.path.normpath(other['path'])
                            
                            if self._is_subpath(current_path, other_path) and other['include_sub']:
                                conflict_found = True
                                conflict_type = 1
                                conflict_path = other_path
                                break
                                
                            if self._is_subpath(other_path, current_path):
                                conflict_found = True
                                conflict_type = 2
                                conflict_path = other_path
                                break
                        
                        if conflict_found:
                            if hasattr(self, '_batch_adding') and self._batch_adding:
                                item['checkbox'].setChecked(False)
                                return
                            
                            if conflict_type == 1:
                                msg_box = QMessageBox(self)
                                msg_box.setWindowTitle("操作不允许")
                                msg_box.setText(f"操作被阻止！\n\n"
                                "您要勾选的文件夹是其他已勾选包含子文件夹的路径的子目录。")
                                msg_box.setInformativeText(f"• 父路径: {os.path.basename(conflict_path)}\n"
                                f"• 当前路径: {os.path.basename(current_path)}")
                                
                                cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
                                disable_parent_btn = msg_box.addButton("取消父文件夹的子文件夹选项", QMessageBox.ButtonRole.ActionRole)
                                
                                msg_box.setDefaultButton(cancel_btn)
                                msg_box.exec()
                                
                                if msg_box.clickedButton() == disable_parent_btn:
                                    for other_item in self.folder_items:
                                        if self._paths_equal(other_item['path'], conflict_path):
                                            other_item['checkbox'].setChecked(False)
                                            config_manager.update_folder_include_sub(other_item['path'], False)
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
                            
                    item['include_sub'] = include_sub
                    config_manager.update_folder_include_sub(current_path, include_sub)
                    break
        except Exception as e:
            if not (hasattr(self, '_batch_adding') and self._batch_adding):
                QMessageBox.critical(
                    self, 
                    "操作失败", 
                    f"更新文件夹选项时发生错误：{str(e)}\n\n"
                    f"请稍后重试。"
                )

    def remove_folder_item(self, folder_frame):
        self._remove_folder_item(folder_frame)

    def _paths_equal(self, path1, path2):
        try:
            norm_path1 = os.path.normcase(os.path.normpath(path1))
            norm_path2 = os.path.normcase(os.path.normpath(path2))
            
            if os.name == 'nt':
                drive1 = os.path.splitdrive(norm_path1)[0].lower()
                drive2 = os.path.splitdrive(norm_path2)[0].lower()
                path_part1 = norm_path1[len(drive1):]
                path_part2 = norm_path2[len(drive2):]
                return drive1 == drive2 and path_part1 == path_part2
            
            return norm_path1 == norm_path2
        except (TypeError, AttributeError):
            return False

    def _is_subpath(self, path, parent_path):
        try:
            path = os.path.normcase(os.path.normpath(path))
            parent_path = os.path.normcase(os.path.normpath(parent_path))
            
            parent_path_with_sep = parent_path
            if not parent_path.endswith(os.sep):
                parent_path_with_sep = parent_path + os.sep
            
            return path == parent_path or path.startswith(parent_path_with_sep)
        except (TypeError, AttributeError, ValueError):
            return False

    def _show_remove_button(self, folder_frame):
        for item in self.parent.gridLayout_6.children():
            if item == folder_frame:
                for child in folder_frame.children():
                    if isinstance(child, QtWidgets.QPushButton) and child.text() == "移除":
                        child.show()
                break

    def _hide_remove_button(self, folder_frame):
        for item in self.parent.gridLayout_6.children():
            if item == folder_frame:
                for child in folder_frame.children():
                    if isinstance(child, QtWidgets.QPushButton) and child.text() == "移除":
                        child.hide()
                break

    def _remove_folder_item(self, folder_frame):
        try:
            for i, item in enumerate(self.folder_items):
                if item['frame'] == folder_frame:
                    try:
                        item['remove_button'].clicked.disconnect()
                        item['checkbox'].stateChanged.disconnect()
                    except TypeError:
                        pass
                    
                    self.parent.gridLayout_6.removeWidget(folder_frame)
                    folder_frame.deleteLater()
                    
                    folder_path = item['path']
                    
                    self.folder_items.pop(i)
                    
                    try:
                        config_manager.remove_folder(folder_path)
                    except Exception as e:
                        pass
                    break
            
            for i in reversed(range(self.parent.gridLayout_6.count())):
                layout_item = self.parent.gridLayout_6.itemAt(i)
                if layout_item and layout_item.widget():
                    self.parent.gridLayout_6.removeItem(layout_item)
            
            for row, item in enumerate(self.folder_items):
                self.parent.gridLayout_6.addWidget(item['frame'], row, 0)
            
            if len(self.folder_items) == 1:
                self.parent.gridLayout_6.setRowStretch(0, 0)
                self.parent.gridLayout_6.setRowStretch(1, 1)
            elif len(self.folder_items) > 1:
                for i in range(len(self.folder_items)):
                    self.parent.gridLayout_6.setRowStretch(i, 0)
                self.parent.gridLayout_6.setRowStretch(len(self.folder_items), 1)
            
            self.parent._update_empty_state(bool(self.folder_items))
        except Exception as e:
            QMessageBox.warning(
                self, 
                "操作失败", 
                f"移除文件夹时发生错误：{str(e)}"
            )

    def _check_media_files(self, folder_path):
        has_media = False
        try:
            file_count = 0
            max_check_files = 200
            
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    try:
                        ext = os.path.splitext(file)[1].lower()
                        common_media_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff', '.heic', '.heif',
                                            '.mp4', '.mov', '.avi', '.mkv', '.flv', '.3gp', '.wmv',
                                            '.mp3', '.flac', '.wav', '.aac', '.ogg']
                        
                        if ext in common_media_exts:
                            has_media = True
                            break
                        
                        media_info = detect_media_type(file_path)
                        if media_info['valid']:
                            has_media = True
                            break
                    except Exception as e:
                        continue
                    
                file_count += 1
                if file_count >= max_check_files:
                    break
        except Exception as e:
            pass
        
        if has_media:
            self.parent._update_empty_state(True)

    def get_all_folders(self):
        return self.folder_items

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        
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
        
        total = len(folder_paths)
        added_count = 0
        skipped_count = 0
        error_count = 0
        self._batch_adding = True
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowTitle("正在添加文件夹")
        progress_dialog.setLabelText(f"准备处理 {total} 个文件夹...")
        progress_dialog.setRange(0, total)
        progress_dialog.setCancelButtonText("取消")
        progress_dialog.setValue(0)
        progress_dialog.show()
        
        results = {
            'added': [],
            'skipped': [],
            'error': []
        }
        
        for i, folder_path in enumerate(folder_paths):
            if progress_dialog.wasCanceled():
                QMessageBox.information(self, "操作已取消", "文件夹添加操作已被取消。")
                break
            
            folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
            progress_dialog.setLabelText(f"正在处理第 {i+1}/{total} 个文件夹...\n\n当前: {folder_name}")
            progress_dialog.setValue(i)
            
            QtCore.QCoreApplication.processEvents()
            
            try:
                if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                    skipped_count += 1
                    results['skipped'].append((folder_path, "路径不存在或不是文件夹"))
                    continue
                
                try:
                    os.listdir(folder_path)
                except PermissionError:
                    skipped_count += 1
                    results['skipped'].append((folder_path, "无访问权限"))
                    continue
                
                folder_path = os.path.normpath(folder_path)
                
                has_conflict = False
                conflict_reason = ""
                
                for item in self.folder_items:
                    item_path = os.path.normpath(item['path'])
                    
                    if self._paths_equal(item_path, folder_path):
                        has_conflict = True
                        conflict_reason = "已存在相同路径"
                        break
                        
                    if item['include_sub'] and self._is_subpath(folder_path, item_path):
                        has_conflict = True
                        conflict_reason = f"是已添加文件夹 '{os.path.basename(item_path)}' 的子目录且父目录已勾选包含子文件夹"
                        break
                        
                    if self._is_subpath(item_path, folder_path) and item['include_sub']:
                        has_conflict = True
                        conflict_reason = f"包含已添加文件夹 '{os.path.basename(item_path)}' 且子目录已勾选包含子文件夹"
                        break
                
                if has_conflict:
                    skipped_count += 1
                    results['skipped'].append((folder_path, conflict_reason))
                    continue
                
                folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
                self._create_folder_item(folder_path, folder_name)
                added_count += 1
                results['added'].append(folder_path)
                
                self._check_media_files(folder_path)
                
            except Exception as e:
                error_count += 1
                results['error'].append((folder_path, str(e)))
        
        self._batch_adding = False
        
        progress_dialog.close()
        
        if added_count > 0 or skipped_count > 0 or error_count > 0:
            message = ""
            details = []
            
            if added_count > 0:
                message += f"成功添加 {added_count} 个文件夹\n"
                for path in results['added']:
                    details.append(f"  已添加: {os.path.basename(path)} ({path})")
                details.append("")
            
            if skipped_count > 0:
                message += f"跳过 {skipped_count} 个文件夹\n"
                for path, reason in results['skipped']:
                    details.append(f"  {os.path.basename(path)} - {reason}")
                details.append("")
            
            if error_count > 0:
                message += f"{error_count} 个文件夹添加失败\n"
                for path, reason in results['error']:
                    details.append(f"  已跳过: {os.path.basename(path)} - {reason}")
            
            if details:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("添加完成")
                msg_box.setText(message)
                
                details_btn = msg_box.addButton("查看详情", QMessageBox.ButtonRole.ActionRole)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
                
                msg_box.exec()
                
                if msg_box.clickedButton() == details_btn:
                    details_dialog = QDialog(self)
                    details_dialog.setWindowTitle("添加详情")
                    details_dialog.resize(600, 400)
                    
                    text_browser = QTextEdit()
                    text_browser.setReadOnly(True)
                    text_browser.setPlainText("\n".join(details))
                    
                    close_btn = QPushButton("关闭")
                    close_btn.clicked.connect(details_dialog.close)
                    
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

    def _show_context_menu(self, position):
        """显示右键菜单"""
        if not self.folder_items:
            return
            
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e0e0e0;
                margin: 4px 0;
            }
        """)
        
        # 添加菜单项
        select_all_action = menu.addAction("全选")
        select_none_action = menu.addAction("全不选")
        menu.addSeparator()
        
        enable_all_sub_action = menu.addAction("全部包含子文件夹")
        disable_all_sub_action = menu.addAction("全部不包含子文件夹")
        menu.addSeparator()
        
        remove_all_action = menu.addAction("移除所有文件夹")
        refresh_action = menu.addAction("刷新列表")
        
        # 显示菜单
        action = menu.exec(self.parent.scrollAreaWidgetContents_folds.mapToGlobal(position))
        
        if action == select_all_action:
            self._select_all_folders(True)
        elif action == select_none_action:
            self._select_all_folders(False)
        elif action == enable_all_sub_action:
            self._set_all_subfolders(True)
        elif action == disable_all_sub_action:
            self._set_all_subfolders(False)
        elif action == remove_all_action:
            self._remove_all_folders()
        elif action == refresh_action:
            self._refresh_folder_list()

    def _select_all_folders(self, select):
        """全选或全不选所有文件夹"""
        for item in self.folder_items:
            item['checkbox'].setChecked(select)

    def _set_all_subfolders(self, include_sub):
        """设置所有文件夹的子文件夹包含状态"""
        for item in self.folder_items:
            item['checkbox'].setChecked(include_sub)
            config_manager.update_folder_include_sub(item['path'], include_sub)

    def _remove_all_folders(self):
        """移除所有文件夹"""
        if not self.folder_items:
            return
            
        reply = QtWidgets.QMessageBox.question(
            self, 
            "确认移除", 
            f"确定要移除所有 {len(self.folder_items)} 个文件夹吗？",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # 复制列表避免修改时出错
            items_copy = self.folder_items.copy()
            for item in items_copy:
                self.remove_folder_item(item['frame'])

    def _refresh_folder_list(self):
        """刷新文件夹列表"""
        # 保存当前状态
        current_paths = [item['path'] for item in self.folder_items]
        current_sub_states = {item['path']: item['checkbox'].isChecked() for item in self.folder_items}
        
        # 清除现有项目
        for item in self.folder_items.copy():
            self.remove_folder_item(item['frame'])
        
        # 重新添加文件夹
        for folder_path in current_paths:
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                folder_name = os.path.basename(folder_path) if os.path.basename(folder_path) else folder_path
                self._create_folder_item(folder_path, folder_name)
                
                # 恢复子文件夹状态
                for item in self.folder_items:
                    if item['path'] == folder_path:
                        item['checkbox'].setChecked(current_sub_states.get(folder_path, True))
                        break
        
        QtWidgets.QMessageBox.information(self, "刷新完成", "文件夹列表已刷新")

    def _show_folder_item_menu(self, position, item_data):
        """显示单个文件夹项的右键菜单"""
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
        """)
        
        # 添加菜单项
        open_action = menu.addAction("打开文件夹")
        copy_path_action = menu.addAction("复制路径")
        menu.addSeparator()
        
        toggle_sub_action = menu.addAction("切换子文件夹状态")
        rename_action = menu.addAction("重命名显示")
        menu.addSeparator()
        
        remove_action = menu.addAction("移除文件夹")
        
        # 显示菜单
        action = menu.exec(item_data['frame'].mapToGlobal(position))
        
        if action == open_action:
            self._open_folder_in_explorer(item_data['path'])
        elif action == copy_path_action:
            self._copy_folder_path(item_data['path'])
        elif action == toggle_sub_action:
            self._toggle_folder_sub_status(item_data)
        elif action == rename_action:
            self._rename_folder_display(item_data)
        elif action == remove_action:
            self.remove_folder_item(item_data['frame'])

    def _open_folder_in_explorer(self, folder_path):
        """在资源管理器中打开文件夹"""
        try:
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                subprocess.Popen(['explorer', folder_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', folder_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "打开失败", f"无法打开文件夹: {str(e)}")

    def _copy_folder_path(self, folder_path):
        """复制文件夹路径到剪贴板"""
        try:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(folder_path)
            QtWidgets.QMessageBox.information(self, "复制成功", "文件夹路径已复制到剪贴板")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "复制失败", f"无法复制路径: {str(e)}")

    def _toggle_folder_sub_status(self, item_data):
        """切换文件夹的子文件夹包含状态"""
        current_state = item_data['checkbox'].isChecked()
        item_data['checkbox'].setChecked(not current_state)
        config_manager.update_folder_include_sub(item_data['path'], not current_state)

    def _rename_folder_display(self, item_data):
        """重命名文件夹显示名称"""
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, 
            "重命名显示", 
            "输入新的显示名称:",
            text=item_data['name']
        )
        
        if ok and new_name.strip():
            item_data['name_label'].setText(new_name.strip())

    def _load_saved_folders(self):
        saved_folders = config_manager.get_folders()
        loaded_paths = []
        invalid_paths = []
        
        for folder_info in saved_folders:
            folder_path = folder_info["path"]
            folder_path = os.path.normpath(folder_path)
            
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                has_conflict = False
                for loaded_path in loaded_paths:
                    if self._paths_equal(folder_path, loaded_path):
                        has_conflict = True
                        break
                    
                if not has_conflict:
                    self._create_folder_item(folder_path, os.path.basename(folder_path))
                    loaded_paths.append(folder_path)
            else:
                invalid_paths.append(folder_path)
        
        for invalid_path in invalid_paths:
            config_manager.remove_folder(invalid_path)
            
        if invalid_paths:
            QMessageBox.information(
                self, 
                "文件夹更新", 
                f"检测到 {len(invalid_paths)} 个文件夹路径无效（可能已被移动或删除），\n\n"
                "这些路径已从配置中自动移除。"
            )
        self.parent._update_empty_state(bool(self.folder_items))
