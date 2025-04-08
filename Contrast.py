import os
import numpy as np
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, QRunnable, QObject, Qt, QThreadPool
from PyQt6.QtGui import QPixmap, QImage
from ContrastThread import HashWorker, ContrastWorker


class ThumbnailLoaderSignals(QObject):
    thumbnail_ready = pyqtSignal(str, QPixmap)
    progress_updated = pyqtSignal(int)


class ThumbnailLoader(QRunnable):
    def __init__(self, path, size, total_images):
        super().__init__()
        self.path = path
        self.size = size
        self.total_images = total_images
        self.signals = ThumbnailLoaderSignals()

    def run(self):
        image = QImage(self.path)
        if not image.isNull():
            scaled_image = image.scaled(self.size.width(), self.size.height(), Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            pixmap = QPixmap.fromImage(scaled_image)
            self.signals.thumbnail_ready.emit(self.path, pixmap)
            progress = 80 + int((1 / self.total_images) * 20)
            self.signals.progress_updated.emit(progress)
        self.signals.progress_updated.emit(100)


class Contrast(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.groups = {}
        self.image_hashes = {}
        self.folder_path = 'D:/test/666'
        self._running = False
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(min(8, os.cpu_count() or 4))
        self.init_page()
        self.connect_signals()

    def init_page(self):
        slider = self.parent.horizontalSlider_levelContrast
        slider.setRange(1, 4)
        slider.setValue(4)
        label = self.parent.label_levelContrast
        label.setText("完全一致")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("QLabel { font-size: 18px; color: #4CAF50; }")
        self.parent.verticalFrame_similar.hide()

    def connect_signals(self):
        self.parent.horizontalSlider_levelContrast.valueChanged.connect(self.on_slider_value_changed)
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)

    def set_folder_path(self, folder_path):
        self.folder_path = folder_path

    def startContrast(self):
        if not self.folder_path or not os.path.isdir(self.folder_path):
            QtWidgets.QMessageBox.warning(self, "警告", "请先设置有效的文件夹路径")
            return

        self._running = True
        self.parent.verticalFrame_similar.show()
        self.parent.progressBar_Contrast.setValue(0)

        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        image_paths = [os.path.join(self.folder_path, f) for f in os.listdir(self.folder_path) if
                       os.path.splitext(f)[1].lower() in supported_formats]
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
        print(error_msg)
        QtWidgets.QMessageBox.warning(self, "哈希计算错误", error_msg)
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
            QtWidgets.QMessageBox.information(self, "提示", "没有找到符合条件的图片")
        self.parent.toolButton_startContrast.setEnabled(True)

    def create_thumbnail(self, path, total_images):
        container_size = QtCore.QSize(100, 100)
        label = QtWidgets.QLabel()
        label.setFixedSize(container_size)
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
        """)
        loader = ThumbnailLoader(path, container_size, total_images)
        loader.signals.thumbnail_ready.connect(lambda p, pix: self.on_thumbnail_loaded(p, pix, label))
        loader.signals.progress_updated.connect(self.update_progress)
        self.thread_pool.start(loader)

        return label

    def on_thumbnail_loaded(self, path, pixmap, label):
        if not pixmap.isNull():
            label.setPixmap(pixmap)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.mousePressEvent = lambda e, p=path: self.thumbnail_clicked(p)

    def thumbnail_clicked(self, path):
        for group_id, paths in self.groups.items():
            if path in paths:
                self.set_empty(False)
                self.show_image(self.parent.label_image_A, path)
                candidates = [p for p in paths if p != path]
                if candidates:
                    random_image_path = np.random.choice(candidates)
                    self.show_image(self.parent.label_image_B, random_image_path)
                break

    def show_images_from_thread(self, source_path, match_path):
        self.set_empty(False)
        self.show_image(self.parent.label_image_A, source_path)
        self.show_image(self.parent.label_image_B, match_path)

    def update_progress(self, value):
        self.parent.progressBar_Contrast.setValue(value)

    def get_similarity_threshold(self, slider_value):
        threshold_map = {1: 32, 2: 16, 3: 8, 4: 0}
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
        self.parent.label_image_A.setStyleSheet(
            "QLabel {image: url('resources/img/page_3/对比1.svg');}" if status else "QLabel {image: url('');}")
        self.parent.label_image_B.setStyleSheet(
            "QLabel {image: url('resources/img/page_3/对比2.svg');}" if status else "QLabel {image: url('');}")

    def show_image(self, label, path):
        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(label.width(), label.height(), QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                   QtCore.Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)

    def stop_processing(self):
        self._running = False
        if hasattr(self, 'hash_worker'):
            self.hash_worker.stop()
        if hasattr(self, 'contrast_worker'):
            self.contrast_worker.stop()
