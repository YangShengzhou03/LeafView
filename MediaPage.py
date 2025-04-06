# MediaPage
import os
import shutil
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QFileDialog


class MediaPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_page()

    def init_page(self):
        self.connect_signal()

    def connect_signal(self):
        pass
        # self.parent.toolButton_saveAs.clicked.connect(self.on_toolButton_saveAs_clicked)

    def on_item_selection_changed(self):
        selected_items_exist = any(
            state['selected']
            for state in self.parent.item_selection_state.values()
            if 'folder_path' not in state
        )
        self.parent.toolButton_saveAs.setVisible(selected_items_exist)

    def on_toolButton_saveAs_clicked(self):
        selected_file_paths = [
            self.get_file_path_for_widget(widget_id)
            for widget_id, state in self.parent.item_selection_state.items()
            if state['selected']
        ]
        if not selected_file_paths:
            return
        target_folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if not target_folder:
            return
        for file_path in selected_file_paths:
            try:
                file_name = os.path.basename(file_path)
                name, ext = os.path.splitext(file_name)
                destination_path = os.path.join(target_folder, file_name)
                counter = 1
                while os.path.exists(destination_path):
                    new_name = f"{name}_{counter}{ext}"
                    destination_path = os.path.join(target_folder, new_name)
                    counter += 1
                shutil.copy2(file_path, destination_path)
            except Exception as e:
                print(f"复制文件时出错: {file_path}, 错误信息: {e}")

    def get_file_path_for_widget(self, widget_id):
        if widget_id in self.parent.item_selection_state:
            return self.parent.item_selection_state[widget_id]['file_path']
        return None
