import os
import shutil

import numpy as np
import pillow_heif
from PIL import Image
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, QRunnable, QObject, Qt, QThreadPool
from PyQt6.QtGui import QPixmap, QImage
from ContrastThread import HashWorker, ContrastWorker
from common import get_resource_path


class ThumbnailLoaderSignals(QObject):
    thumbnail_ready = pyqtSignal(str, QPixmap)
    progress_updated = pyqtSignal(int)


def load_heic_as_qimage(path):
    heif_file = pillow_heif.read_heif(path)
    image = Image.frombytes(
        heif_file.mode,
        heif_file.size,
        heif_file.data,
        "raw",
    )
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = image.tobytes()
    qimage = QImage(buffer, image.width, image.height, QImage.Format.Format_RGB888)
    return qimage.copy()


class ThumbnailLoader(QRunnable):
    def __init__(self, path, size, total_images):
        super().__init__()
        self.path = path
        self.size = size
        self.total_images = total_images
        self.signals = ThumbnailLoaderSignals()

    def run(self):
        if self.path.lower().endswith(('.heic', '.heif')):
            try:
                image = load_heic_as_qimage(self.path)
            except Exception:
                return
        else:
            image = QImage(self.path)

        if not image.isNull():
            scaled_image = image.scaled(self.size.width(), self.size.height(),
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            pixmap = QPixmap.fromImage(scaled_image)
            self.signals.thumbnail_ready.emit(self.path, pixmap)
            progress = 80 + int((1 / self.total_images) * 20)
            self.signals.progress_updated.emit(progress)
        self.signals.progress_updated.emit(100)


class Contrast(QtWidgets.QWidget):
    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.groups = {}
        self.image_hashes = {}
        self._running = False
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(min(8, os.cpu_count() or 4))
        self.init_page()
        self.connect_signals()
        self.selected_images = []

    def init_page(self):
        slider = self.parent.horizontalSlider_levelContrast
        slider.setRange(1, 4)
        slider.setValue(4)
        self.parent.verticalFrame_similar.hide()

    def connect_signals(self):
        self.parent.horizontalSlider_levelContrast.valueChanged.connect(self.on_slider_value_changed)
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)
        self.parent.toolButton_move.clicked.connect(self.move_selected_images)
        self.parent.toolButton_autoSelect.clicked.connect(self.auto_select_images)
        self.parent.toolButton_delete.clicked.connect(self.delete_selected_images)

    def move_selected_images(self):
        dest_folder = QtWidgets.QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if dest_folder:
            for img in self.selected_images:
                try:
                    shutil.move(img, os.path.join(dest_folder, os.path.basename(img)))
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "无法移动图片", f"无法移动图片 {img}: {e}")
            self.display_all_images()

    def auto_select_images(self):
        self.selected_images.clear()
        for group_id, paths in self.groups.items():
            if len(paths) > 1:
                best_quality_image = max(paths, key=lambda x: os.path.getsize(x))
                for img in paths:
                    if img != best_quality_image:
                        self.selected_images.append(img)
        self.refresh_selection_visuals()

    def delete_selected_images(self):
        reply = QtWidgets.QMessageBox.question(self, '确认删除', "确定要删除选中的图片吗？",
                                               QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                               QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            for img in self.selected_images:
                try:
                    os.remove(img)
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "无法删除图片", f"删除图片{img}出错: {e}")
            self.selected_images.clear()
            self.display_all_images()

    def refresh_selection_visuals(self):
        layout = self.parent.gridLayout_2
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if isinstance(item.widget(), QtWidgets.QLabel):
                path = item.widget().property("image_path")
                selected = path in self.selected_images
                item.widget().setProperty("selected", selected)
                item.widget().style().unpolish(item.widget())
                item.widget().style().polish(item.widget())

    def startContrast(self):
        folders = self.folder_page.get_all_folders() if self.folder_page else []
        if not folders:
            QtWidgets.QMessageBox.warning(self, "警告", "请先设置有效的文件夹路径")
            return

        self._running = True
        self.parent.verticalFrame_similar.show()
        self.parent.progressBar_Contrast.setValue(0)

        supported_formats = [
            '.jpg', '.jpeg', '.png', '.bmp', '.gif',
            '.webp', '.tif', '.tiff', '.heif', '.heic',
            '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
            '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc'
        ]
        image_paths = []

        for folder_info in folders:
            folder_path = folder_info['path']
            include_sub = folder_info['include_sub']

            if include_sub == 1:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if os.path.splitext(file)[1].lower() in supported_formats:
                            image_paths.append(os.path.join(root, file))
            else:
                for file in os.listdir(folder_path):
                    if os.path.splitext(file)[1].lower() in supported_formats:
                        image_paths.append(os.path.join(folder_path, file))
        self.parent.toolButton_startContrast.setEnabled(False)
        self.hash_worker = HashWorker(image_paths)
        self.hash_worker.hash_completed.connect(self.on_hashes_computed)
        self.hash_worker.progress_updated.connect(self.update_progress)
        self.hash_worker.error_occurred.connect(self.on_hash_error)
        self.hash_worker.start()

    def on_hashes_computed(self, hashes):
        if not self._running:
            return

        self.image_hashes = hashes
        threshold = self.get_similarity_threshold(self.parent.horizontalSlider_levelContrast.value())
        self.contrast_worker = ContrastWorker(hashes, threshold)
        self.contrast_worker.groups_completed.connect(self.on_groups_computed)
        self.contrast_worker.progress_updated.connect(self.update_progress)
        self.contrast_worker.image_matched.connect(self.show_images_from_thread)
        self.contrast_worker.start()

    def on_groups_computed(self, groups):
        if not self._running:
            return
        self.groups = groups
        self.display_all_images()

    def on_hash_error(self, error_msg):
        QtWidgets.QMessageBox.warning(self, "图像Hash计算错误", error_msg)
        self._running = False
        self.parent.toolButton_startContrast.setEnabled(True)

    def display_all_images(self):
        layout = self.parent.gridLayout_2
        self.clear_layout(layout)
        COLUMN_COUNT = 4
        row, col = 0, 0
        duplicate_groups = {group_id: paths for group_id, paths in self.groups.items() if len(paths) > 1}
        total_images = sum(len(paths) for paths in duplicate_groups.values())
        no_images_found = True
        for index, (group_id, paths) in enumerate(duplicate_groups.items(), start=1):
            if not paths or not self._running:
                continue
            no_images_found = False
            title = QtWidgets.QLabel(f"📁 第{index}组 ({len(paths)}张)")
            title.setStyleSheet("QLabel { font: bold 14px; color: #1976D2; padding: 2px 0; }")
            layout.addWidget(title, row, 0, 1, COLUMN_COUNT)
            row += 1
            for path in paths:
                if col >= COLUMN_COUNT:
                    col = 0
                    row += 1
                thumbnail = self.create_thumbnail(path, total_images)
                if thumbnail:
                    layout.addWidget(thumbnail, row, col)
                    col += 1
            if paths and self._running:
                self.add_separator(layout, row + 1)
                row += 2
                col = 0
        layout.update()
        self.parent.update()
        if no_images_found:
            self.update_progress(100)
            self.parent.verticalFrame_similar.hide()
            QtWidgets.QMessageBox.information(self, "提示", "没有找到符合相似度条件的图片")
        self.parent.toolButton_startContrast.setEnabled(True)

    def create_thumbnail(self, path, total_images):
        container_size = QtCore.QSize(100, 100)
        label = QtWidgets.QLabel()
        label.setFixedSize(container_size)
        label.setProperty("image_path", path)
        label.setProperty("selected", False)
        label.setStyleSheet("""
            QLabel {
                background: #F5F5F5;
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                padding: 0px;
            }
            QLabel:hover {
                border: 2px solid #2196F3;
            }
            QLabel[selected=true] {
                border: 3px solid #FF5722;
            }
        """)
        label.mousePressEvent = lambda e, p=path: self.thumbnail_clicked(p)
        label.mouseDoubleClickEvent = lambda e, lbl=label: self.toggle_thumbnail_selection(lbl)
        loader = ThumbnailLoader(path, container_size, total_images)
        loader.signals.thumbnail_ready.connect(lambda p, pix: self.on_thumbnail_loaded(pix, label))
        loader.signals.progress_updated.connect(self.update_progress)
        self.thread_pool.start(loader)
        return label

    def toggle_thumbnail_selection(self, label):
        path = label.property("image_path")
        is_selected = not label.property("selected")
        label.setProperty("selected", is_selected)
        label.style().unpolish(label)
        label.style().polish(label)
        if is_selected:
            if path not in self.selected_images:
                self.selected_images.append(path)
        else:
            if path in self.selected_images:
                self.selected_images.remove(path)

    def thumbnail_clicked(self, path):
        for group_id, paths in self.groups.items():
            if path in paths:
                self.set_empty(False)
                self.show_image(self.parent.label_image_A, path)
                candidates = [p for p in paths if p != path]
                if candidates:
                    random_image_path = np.random.choice(candidates)
                    self.show_image(self.parent.label_image_B, random_image_path)
                    self.set_empty(status=False)
                break

    def on_thumbnail_loaded(self, pixmap, label):
        if not pixmap.isNull():
            label.setPixmap(pixmap)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def show_images_from_thread(self, source_path, match_path):
        self.set_empty(False)
        self.show_image(self.parent.label_image_A, source_path)
        self.show_image(self.parent.label_image_B, match_path)

    def update_progress(self, value):
        self.parent.progressBar_Contrast.setValue(value)

    def get_similarity_threshold(self, slider_value):
        threshold_map = {1: 32, 2: 24, 3: 12, 4: 0}
        return threshold_map.get(slider_value, 0)

    def on_slider_value_changed(self, value):
        level_info = [("明显差异", "#FF5252"), ("部分相似", "#FF9800"), ("比较相似", "#2196F3"),
                      ("完全一致", "#4CAF50")]
        if 1 <= value <= 4:
            text, color = level_info[value - 1]
            self.parent.label_levelContrast.setText(text)
            self.parent.label_levelContrast.setStyleSheet(f"QLabel {{ color: {color}; }}")

    def add_separator(self, layout, row):
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setStyleSheet("border: 1px dashed #BDBDBD;")
        layout.addWidget(separator, row, 0, 1, layout.columnCount())

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

    def set_empty(self, status=False):
        self.parent.label_image_A.setStyleSheet(f"image: url({get_resource_path('resources/img/page_3/对比1.jpg')})" if
                                                status else "QLabel {image: url('');}")
        self.parent.label_image_B.setStyleSheet(f"image: url({get_resource_path('resources/img/page_3/对比2.jpg')})" if
                                                status else "QLabel {image: url('');}")

    def show_image(self, label, path):
        if path.lower().endswith(('.heic', '.heif')):
            try:
                heif_file = pillow_heif.read_heif(path)
                image = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                )
                if image.mode != "RGB":
                    image = image.convert("RGB")
                buffer = image.tobytes()
                qimage = QImage(buffer, image.width, image.height, QImage.Format.Format_RGB888)
                if not qimage.isNull():
                    pixmap = QPixmap.fromImage(qimage)
                    scaled = pixmap.scaled(label.width(), label.height(),
                                           QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                           QtCore.Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(scaled)
                return
            except Exception:
                return
        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(label.width(), label.height(),
                                   QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                   QtCore.Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)

    def stop_processing(self):
        self._running = False
        if hasattr(self, 'hash_worker'):
            self.hash_worker.stop()
        if hasattr(self, 'contrast_worker'):
            self.contrast_worker.stop()
