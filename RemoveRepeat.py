import os
import random
import shutil

import cv2
import numpy as np
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from Thread import SimilarImageThread


class RemoveRepeat(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_page()
        self.current_image_path = None
        self.current_display_area = 'legend'
        self.selected_images = []
        self.thread = None

    def init_page(self):
        self.setup_image_display_widgets()
        self.connect_signals()

    def connect_signals(self):
        self.parent.toolButton_Remove.clicked.connect(self.move_images)
        self.parent.toolButton_delete.clicked.connect(self.delete_images)
        button = self.parent.toolButton_StartRemove
        button.clicked.connect(self.toggle_process)
        self.parent.toolButton_AutoSelect.clicked.connect(self.auto_select_images)
        slider = self.parent.horizontalSlider_Similarity
        spinbox = self.parent.spinBox_Similarity
        slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(10)
        slider.valueChanged.connect(spinbox.setValue)
        spinbox.valueChanged.connect(slider.setValue)
        min_value, max_value = 0, 100
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        spinbox.setMinimum(min_value)
        spinbox.setMaximum(max_value)

    def move_images(self):
        if not self.selected_images:
            QMessageBox.warning(self, '请先选择图片', '您还未选中任何图片')
            return
        folder_path = QFileDialog.getExistingDirectory(self, "移动到文件夹")
        if folder_path:
            for img_path in self.selected_images:
                try:
                    shutil.move(img_path, os.path.join(folder_path, os.path.basename(img_path)))
                except Exception:
                    pass
            self.selected_images.clear()
        self.clear_widget_SimilarImage()

    def delete_images(self):
        if not self.selected_images:
            QMessageBox.warning(self, '请先选择图片', '您还未选中任何图片')
            return
        if QMessageBox.question(self, '请考虑清楚再做决定哦', '您真的要删除这些选中的图片吗?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            for img_path in self.selected_images:
                try:
                    os.remove(img_path)
                except Exception:
                    pass
            self.selected_images.clear()
        self.clear_widget_SimilarImage()

    def toggle_process(self):
        button = self.parent.toolButton_StartRemove
        if button.text() == "开始查找":
            if not self.parent.imported_folders:
                return
            self.start_remove_process()
            button.setText("停止查找")
        else:
            self.stop_remove_process()
            button.setText("开始查找")

    def start_remove_process(self):
        self.clear_widget_SimilarImage()
        similarity_threshold = self.parent.spinBox_Similarity.value()
        file_size_threshold = self.parent.spinBox_MB.value()
        self.thread = SimilarImageThread(
            folders=self.parent.imported_folders,
            similarity_threshold=similarity_threshold,
            file_size_threshold=file_size_threshold,
            parent=self
        )
        self.thread.similar_images_found.connect(self.display_similar_images)
        self.thread.progress_updated.connect(self.update_progress_bar)
        self.thread.stopped.connect(self.on_thread_stopped)
        self.thread.start()

    def stop_remove_process(self):
        if self.thread and self.thread.isRunning():
            self.thread.stop()

    def on_thread_stopped(self):
        self.thread = None
        self.update_button_text()

    def clear_widget_SimilarImage(self):
        layout = getattr(self.parent, 'verticalLayout_39', None)
        if layout:
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                elif isinstance(item, QtWidgets.QLayoutItem) and item.layout():
                    sub_layout = item.layout()
                    while sub_layout.count():
                        sub_item = sub_layout.takeAt(0)
                        sub_widget = sub_item.widget()
                        if sub_widget:
                            sub_widget.setParent(None)
                    sub_layout.setParent(None)

    def auto_select_images(self):
        layout = getattr(self.parent, 'verticalLayout_39', None)
        if not layout:
            return
        for i in range(layout.count()):
            group_layout = layout.itemAt(i).layout()
            if not isinstance(group_layout, QtWidgets.QHBoxLayout):
                continue
            images = []
            for j in range(group_layout.count()):
                container = group_layout.itemAt(j).widget()
                if container:
                    label = next((child for child in container.children() if isinstance(child, ImageLabel)), None)
                    checkbox = next((child for child in container.children() if isinstance(child, QtWidgets.QCheckBox)),
                                    None)
                    if label and checkbox:
                        byte_content = np.fromfile(label.img_path, dtype=np.uint8)
                        img = cv2.imdecode(byte_content, cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            fm = cv2.Laplacian(img, cv2.CV_64F).var()
                            images.append((label.img_path, checkbox, fm))
            if images:
                best_quality_image = max(images, key=lambda x: x[2], default=None)
                others = [img for img in images if img != best_quality_image]
                if best_quality_image:
                    best_quality_image[1].setChecked(False)
                for _, checkbox, _ in others:
                    checkbox.setChecked(True)
                QtWidgets.QApplication.processEvents()

    def update_progress_bar(self, value):
        self.parent.progressBar_RemoveRepeat.setValue(value)

    def display_similar_images(self, groups):
        if not groups:
            return
        widget = self.ensure_widget_SimilarImage()
        layout = self.ensure_vertical_layout(widget)
        for group in groups:
            self.add_image_group_to_layout(layout, group)

        main_layout = self.parent.layout()
        if main_layout is None:
            main_layout = QtWidgets.QVBoxLayout(self.parent)
            self.parent.setLayout(main_layout)
        if widget not in [main_layout.itemAt(i).widget() for i in range(main_layout.count())]:
            main_layout.addWidget(widget)
        widget.update()
        widget.repaint()
        QtWidgets.QApplication.processEvents()
        self.update_button_text()

    def update_button_text(self):
        button = self.parent.toolButton_StartRemove
        if not self.thread or not self.thread.isRunning():
            button.setText("开始查找")

    def ensure_widget_SimilarImage(self):
        if not hasattr(self.parent, 'widget_SimilarImage') or not isinstance(
                getattr(self.parent, 'widget_SimilarImage', None), QtWidgets.QWidget):
            widget = QtWidgets.QWidget(self.parent)
            widget.setGeometry(QtCore.QRect(10, 10, 800, 600))
            widget.setObjectName("widget_SimilarImage")
            setattr(self.parent, 'widget_SimilarImage', widget)
        return self.parent.widget_SimilarImage

    def ensure_vertical_layout(self, widget):
        layout = getattr(self.parent, 'verticalLayout_39', None)
        if layout is None or not isinstance(layout, QtWidgets.QVBoxLayout):
            layout = QtWidgets.QVBoxLayout()
            layout.setSpacing(0)
            layout.setContentsMargins(10, 10, 10, 10)
            widget.setLayout(layout)
            setattr(self.parent, 'verticalLayout_39', layout)
        return layout

    def add_image_group_to_layout(self, layout, group):
        group_layout = QtWidgets.QHBoxLayout()
        group_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        group_layout.setSpacing(2)
        for img_path in group:
            container = QtWidgets.QWidget()
            container.setStyleSheet("QWidget { background-color: white; border-radius: 4px; border: 1px solid #ccc; }")
            container_layout = QtWidgets.QVBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            checkbox = QtWidgets.QCheckBox(container)
            checkbox.setStyleSheet("QCheckBox { border: none; }")
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(lambda state, path=img_path: self.on_checkbox_state_changed(state, path))
            label = ImageLabel(container)
            pixmap = QtGui.QPixmap(img_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(128, 128, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                              QtCore.Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(scaled_pixmap)
                label.img_path = img_path
                label.group = group
                label.image_clicked.connect(lambda path=img_path, grp=group: self.show_selected_image(path, grp))
            container_layout.addWidget(label)
            container_layout.addWidget(checkbox,
                                       alignment=QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
            group_layout.addWidget(container)
        layout.setSpacing(4)
        layout.addLayout(group_layout)

    def on_checkbox_state_changed(self, state, img_path):
        if state == QtCore.Qt.CheckState.Checked.value:
            if img_path not in self.selected_images:
                self.selected_images.append(img_path)
        else:
            if img_path in self.selected_images:
                self.selected_images.remove(img_path)

    def show_selected_image(self, img_path, group):
        if self.current_image_path != img_path or self.current_display_area != 'legend':
            previous_img_path = self.current_image_path
            self.current_image_path = img_path
            self.display_image_in_widget('legend2', img_path)
            if previous_img_path and previous_img_path in group:
                self.display_image_in_widget('legend', previous_img_path)
            else:
                other_images = [img for img in group if img != img_path]
                if other_images:
                    self.display_image_in_widget('legend', random.choice(other_images))

    def display_image_in_widget(self, widget_name, img_path):
        container = getattr(self.parent, f'verticalWidget_{widget_name}', None)
        if container:
            label = self.get_or_create_label(container)
            if label:
                pixmap = QtGui.QPixmap(img_path)
                if not pixmap.isNull():
                    available_size = container.size().boundedTo(pixmap.size())
                    scaled_pixmap = pixmap.scaled(available_size, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                                  QtCore.Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(scaled_pixmap)
                    label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    label.setStyleSheet("border: none;")
                    label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
                    label.setMaximumSize(available_size)
                    label.setMinimumSize(available_size)
                    label.update()
                    label.repaint()
                    QtWidgets.QApplication.processEvents()

    def get_or_create_label(self, container):
        layout = container.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            container.setLayout(layout)

        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QtWidgets.QLabel):
                return widget

        label = QtWidgets.QLabel(container)
        label.setStyleSheet("background-color: transparent; border: none;")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return label

    def setup_image_display_widgets(self):
        if not hasattr(self.parent, 'widget_SimilarImage'):
            widget = QtWidgets.QWidget(self.parent)
            widget.setGeometry(QtCore.QRect(10, 10, 800, 600))
            widget.setObjectName("widget_SimilarImage")
            layout = QtWidgets.QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)
            widget.setLayout(layout)
            setattr(self.parent, 'widget_SimilarImage', widget)

        for name in ['legend', 'legend2']:
            widget_name = f'verticalWidget_{name}'
            if not hasattr(self.parent, widget_name) or not isinstance(getattr(self.parent, widget_name, None),
                                                                       QtWidgets.QWidget):
                container = QtWidgets.QWidget(self.parent)
                container.setGeometry(QtCore.QRect(10, 10, 256, 256))
                container.setObjectName(widget_name)
                horizontal_layout = getattr(self.parent, 'horizontalLayout_65', None)
                if horizontal_layout:
                    horizontal_layout.addWidget(container)
                setattr(self.parent, widget_name, container)
                self.get_or_create_label(container)


class ImageLabel(QtWidgets.QLabel):
    image_clicked = QtCore.pyqtSignal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.img_path = None
        self.group = None
        self.setStyleSheet("border: none;")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.img_path and self.group:
            self.image_clicked.emit(self.img_path, self.group)
        super().mousePressEvent(event)
