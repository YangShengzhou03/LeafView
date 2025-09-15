import os
import shutil

import numpy as np
import pillow_heif
import send2trash
from PIL import Image
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import pyqtSignal, QRunnable, QObject, Qt, QThreadPool
from PyQt6.QtGui import QPixmap, QImage

from RemoveDuplicationThread import HashWorker, ContrastWorker
from common import get_resource_path


class ThumbnailLoaderSignals(QObject):
    thumbnail_ready = pyqtSignal(str, QImage)
    progress_updated = pyqtSignal(int)


def load_heic_as_qimage(path):
    heif_file = pillow_heif.read_heif(path)
    image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
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
        image = QImage()
        if self.path.lower().endswith(('.heic', '.heif')):
            try:
                image = load_heic_as_qimage(self.path)
            except Exception:
                pass
        else:
            image.load(self.path)

        if not image.isNull():
            scaled_image = image.scaled(self.size.width(), self.size.height(),
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            self.signals.thumbnail_ready.emit(self.path, scaled_image)
            progress = 80 + int((1 / self.total_images) * 20)
            self.signals.progress_updated.emit(progress)
        self.signals.progress_updated.emit(100)
        # 修复内存泄漏：显式释放图像资源
        if not image.isNull():
            image = QImage()


class Contrast(QtWidgets.QWidget):
    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.groups = {}
        self.image_hashes = {}
        self._running = False
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        self.selected_images = []
        self.init_page()
        self.connect_signals()
        self.thumbnail_loaders = []

    def init_page(self):
        self.parent.horizontalSlider_levelContrast.setRange(1, 4)
        self.parent.horizontalSlider_levelContrast.setValue(4)
        self.parent.verticalFrame_similar.hide()

    def connect_signals(self):
        self.parent.horizontalSlider_levelContrast.valueChanged.connect(self.on_slider_value_changed)
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)
        self.parent.toolButton_move.clicked.connect(self.move_selected_images)
        self.parent.toolButton_autoSelect.clicked.connect(self.auto_select_images)
        self.parent.toolButton_delete.clicked.connect(self.delete_selected_images)

    def move_selected_images(self):
        dest_folder = QtWidgets.QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if not dest_folder:
            return
        for img in self.selected_images:
            try:
                shutil.move(img, os.path.join(dest_folder, os.path.basename(img)))
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "无法移动图片", f"无法移动图片 {img}: {e}")
        self.display_all_images()

    def auto_select_images(self):
        self.selected_images.clear()
        for group_id, paths in self.groups.items():
            if len(paths) <= 1:
                continue
            best = max(paths, key=lambda x: os.path.getsize(x))
            self.selected_images.extend([p for p in paths if p != best])
        self.refresh_selection_visuals()

    def delete_selected_images(self):
        reply = QtWidgets.QMessageBox.question(self, '移动到回收站', "确定要将选中的图片移动至回收站吗？",
                                               QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                               QtWidgets.QMessageBox.StandardButton.No)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        for img in self.selected_images:
            try:
                send2trash.send2trash(img)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "无法删除图片", f"删除图片{img}出错: {e}")
        self.selected_images.clear()
        self.display_all_images()

    def refresh_selection_visuals(self):
        layout = self.parent.gridLayout_2
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, QtWidgets.QLabel):
                path = widget.property("image_path")
                widget.setProperty("selected", path in self.selected_images)
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    def startContrast(self):
        folders = self.folder_page.get_all_folders() if self.folder_page else []
        if not folders:
            QtWidgets.QMessageBox.warning(self, "警告", "请先设置有效的文件夹路径")
            return

        self._running = True
        self.parent.verticalFrame_similar.show()
        self.parent.progressBar_Contrast.setValue(0)
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tif', '.tiff',
                             '.heif', '.heic', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
                             '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc'}
        image_paths = []
        for folder_info in folders:
            folder_path = folder_info['path']
            if folder_info['include_sub'] == 1:
                for root, _, files in os.walk(folder_path):
                    image_paths.extend(os.path.join(root, f) for f in files
                                       if os.path.splitext(f)[1].lower() in supported_formats)
            else:
                image_paths.extend(os.path.join(folder_path, f) for f in os.listdir(folder_path)
                                   if os.path.splitext(f)[1].lower() in supported_formats)
        
        # 限制处理图片数量，避免内存溢出
        if len(image_paths) > 1000:
            reply = QtWidgets.QMessageBox.question(self, "图片数量过多", 
                                                  f"检测到 {len(image_paths)} 张图片，处理可能较慢。是否继续？",
                                                  QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
            if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                self._running = False
                self.parent.toolButton_startContrast.setEnabled(True)
                return
        
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
        duplicate_groups = {k: v for k, v in self.groups.items() if len(v) > 1}
        total_images = sum(len(v) for v in duplicate_groups.values())
        no_images = True
        row = col = 0
        
        # 清空之前的缩略图加载器
        self.thumbnail_loaders.clear()
        
        for idx, (gid, paths) in enumerate(duplicate_groups.items(), 1):
            if not paths or not self._running:
                continue
            no_images = False
            title = QtWidgets.QLabel(f"📁 第{idx}组 ({len(paths)}张)")
            title.setStyleSheet("QLabel{font:bold 14px;color:#1976D2;padding:2px 0;}")
            layout.addWidget(title, row, 0, 1, 4)
            row += 1
            for path in paths:
                if col >= 4:
                    col = 0
                    row += 1
                thumb = self.create_thumbnail(path, total_images)
                if thumb:
                    layout.addWidget(thumb, row, col)
                    col += 1
            if paths and self._running:
                self.add_separator(layout, row + 1)
                row += 2
                col = 0
        if no_images:
            self.update_progress(100)
            self.parent.verticalFrame_similar.hide()
            QtWidgets.QMessageBox.information(self, "提示", "没有找到符合相似度条件的图片")
        self.parent.toolButton_startContrast.setEnabled(True)

    def create_thumbnail(self, path, total_images):
        label = QtWidgets.QLabel()
        label.setFixedSize(80, 80)
        label.setProperty("image_path", path)
        label.setProperty("selected", False)
        label.setStyleSheet("QLabel{background:#F5F5F5;border:2px solid #E0E0E0;border-radius:4px;}"
                            "QLabel:hover{border:2px solid #2196F3;}QLabel[selected=true]{border:3px solid #FF5722;}")
        label.mousePressEvent = lambda e, p=path: self.thumbnail_clicked(p)
        label.mouseDoubleClickEvent = lambda e, l=label: self.toggle_thumbnail_selection(l)
        loader = ThumbnailLoader(path, QtCore.QSize(80, 80), total_images)
        loader.signals.thumbnail_ready.connect(lambda p, img: self.on_thumbnail_ready(p, img, label))
        loader.signals.progress_updated.connect(self.update_progress)
        self.thumbnail_loaders.append(loader)
        self.thread_pool.start(loader)
        return label

    def toggle_thumbnail_selection(self, label):
        path = label.property("image_path")
        selected = not label.property("selected")
        label.setProperty("selected", selected)
        label.style().unpolish(label)
        label.style().polish(label)
        if selected:
            if path not in self.selected_images:
                self.selected_images.append(path)
        elif path in self.selected_images:
            self.selected_images.remove(path)

    def thumbnail_clicked(self, path):
        for gid, paths in self.groups.items():
            if path in paths:
                self.set_empty(False)
                self.show_image(self.parent.label_image_A, path)
                others = [p for p in paths if p != path]
                if others:
                    self.show_image(self.parent.label_image_B, np.random.choice(others))
                break

    def on_thumbnail_ready(self, path, image, label):
        if image.isNull():
            return
        pixmap = QPixmap.fromImage(image)
        label.setPixmap(pixmap)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # 修复内存泄漏：释放图像资源
        image = QImage()

    def show_images_from_thread(self, src, match):
        self.set_empty(False)
        self.show_image(self.parent.label_image_A, src)
        self.show_image(self.parent.label_image_B, match)

    def update_progress(self, value):
        self.parent.progressBar_Contrast.setValue(value)

    def get_similarity_threshold(self, val):
        return {1: 32, 2: 24, 3: 12, 4: 0}.get(val, 0)

    def on_slider_value_changed(self, val):
        levels = [("明显差异", "#FF5252"), ("部分相似", "#FF9800"),
                  ("比较相似", "#2196F3"), ("完全一致", "#4CAF50")]
        if 1 <= val <= 4:
            text, color = levels[val - 1]
            self.parent.label_levelContrast.setText(text)
            self.parent.label_levelContrast.setStyleSheet(f"QLabel{{color:{color};}}")

    def add_separator(self, layout, row):
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("border:1px dashed #BDBDBD;")
        layout.addWidget(sep, row, 0, 1, layout.columnCount())

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

    def set_empty(self, status):
        style1 = f"image:url({get_resource_path('resources/img/page_3/对比.jpg')})" if status else ""
        style2 = f"image:url({get_resource_path('resources/img/page_3/对比.jpg')})" if status else ""
        self.parent.label_image_A.setStyleSheet(style1)
        self.parent.label_image_B.setStyleSheet(style2)

    def show_image(self, label, path):
        if path.lower().endswith(('.heic', '.heif')):
            try:
                heif = pillow_heif.read_heif(path)
                img = Image.frombytes(heif.mode, heif.size, heif.data, "raw")
                if img.mode != "RGB":
                    img = img.convert("RGB")
                qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888)
                if not qimg.isNull():
                    pix = QPixmap.fromImage(qimg)
                    pix = pix.scaled(label.width(), label.height(),
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(pix)
                return
            except:
                return
        pix = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(label.width(), label.height(),
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(pix)

    def stop_processing(self):
        self._running = False
        if hasattr(self, 'hash_worker'):
            self.hash_worker.stop()
        if hasattr(self, 'contrast_worker'):
            self.contrast_worker.stop()
        # 停止所有缩略图加载器
        self.thumbnail_loaders.clear()
