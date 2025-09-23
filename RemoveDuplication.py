import os
import shutil

import pillow_heif
import send2trash
from PIL import Image
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, QRunnable, QObject, Qt, QThreadPool
from PyQt6.QtGui import QPixmap, QImage

from RemoveDuplicationThread import HashWorker, ContrastWorker


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
        self._is_running = True

    def run(self):
        if not self._is_running:
            return

        image = QImage()
        if self.path.lower().endswith(('.heic', '.heif')):
            try:
                image = load_heic_as_qimage(self.path)
            except Exception:
                pass
        else:
            image.load(self.path)

        if not image.isNull() and self._is_running:
            scaled_image = image.scaled(self.size.width(), self.size.height(),
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            self.signals.thumbnail_ready.emit(self.path, scaled_image)
            progress = 80 + int((1 / self.total_images) * 20)
            self.signals.progress_updated.emit(progress)

        if self._is_running:
            self.signals.progress_updated.emit(100)

        if not image.isNull():
            image = QImage()

    def stop(self):
        self._is_running = False


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
        self.thumbnail_cache = {}
        self.init_page()
        self.connect_signals()
        self.thumbnail_loaders = []
        self.max_cache_size = 200
        self.current_progress = 0

    def init_page(self):
        self.parent.horizontalSlider_levelContrast.setRange(0, 100)
        self.parent.horizontalSlider_levelContrast.setValue(100)
        self.parent.verticalFrame_similar.hide()

    def get_similarity_threshold(self, val):
        return int(64 * (100 - val) / 100)

    def on_slider_value_changed(self, val):
        if val == 100:
            text, color = "完全一致", "#4CAF50"
        elif val >= 75:
            text, color = "高度相似", "#2196F3"
        elif val >= 50:
            text, color = "部分相似", "#FF9800"
        elif val >= 25:
            text, color = "略有相似", "#FF5252"
        else:
            text, color = "巨大差异", "#F44336"

        self.parent.label_levelContrast.setText(f"{text} ({val}%)")
        self.parent.label_levelContrast.setStyleSheet(f"QLabel{{color:{color};}}")

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
                QtWidgets.QMessageBox.warning(self, "无法移动图片",
                                              f"无法移动图片 {os.path.basename(img)}: {e}\n\n"
                                              "可能的原因：\n"
                                              "• 目标文件夹权限不足\n"
                                              "• 文件正在被其他程序使用\n"
                                              "• 磁盘空间不足")
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
        if not self.selected_images:
            QtWidgets.QMessageBox.information(self, "提示", "当前没有选中任何图片\n\n"
                                                            "请先选择要删除的重复图片")
            return

        reply = QtWidgets.QMessageBox.question(self, '确认删除',
                                               f"确定要将选中的 {len(self.selected_images)} 张图片移动到回收站吗？\n\n"
                                               "此操作不可撤销，建议先备份重要文件。\n\n"
                                               "删除后可在回收站中恢复。",
                                               QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                               QtWidgets.QMessageBox.StandardButton.No)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        success_count = 0
        failed_count = 0

        for img in self.selected_images:
            try:
                send2trash.send2trash(img)
                success_count += 1
            except Exception as e:
                failed_count += 1
                QtWidgets.QMessageBox.warning(self, "删除失败",
                                              f"无法删除图片 {os.path.basename(img)}: {str(e)}\n\n"
                                              "可能的原因：\n"
                                              "• 文件正在被其他程序使用\n"
                                              "• 回收站功能异常\n"
                                              "• 权限不足")

        if success_count > 0:
            QtWidgets.QMessageBox.information(self, "操作完成",
                                              f"成功删除 {success_count} 张图片到回收站{f'，{failed_count} 张删除失败' if failed_count > 0 else ''}\n\n"
                                              "您可以在回收站中查看或恢复已删除的文件。")

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
            QtWidgets.QMessageBox.warning(self, "操作提示",
                                          "请先导入包含图片的文件夹\n\n"
                                          "点击导入文件夹按钮添加要检测的文件夹")
            return

        self._running = True
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

        if not image_paths:
            QtWidgets.QMessageBox.information(self, "提示",
                                              "在所选文件夹中未找到支持的图片文件\n\n"
                                              "支持的格式：.jpg/.jpeg/.png/.bmp/.gif/.webp/.tif/.tiff/.heif/.heic\n"
                                              "请检查文件夹路径和文件格式")
            self._running = False
            self.parent.toolButton_startContrast.setEnabled(True)
            return

        if len(image_paths) > 200:
            reply = QtWidgets.QMessageBox.question(self, "图片数量较多",
                                                   f"检测到 {len(image_paths)} 张图片，您电脑配置较低，可能需要一些时间。还继续吗？\n\n"
                                                   "处理大量图片时：\n"
                                                   "• 可能需要几分钟甚至几十分钟\n"
                                                   "• 会占用较多内存和CPU资源",
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.Yes)
            if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                self._running = False
                self.parent.toolButton_startContrast.setEnabled(True)
                return

        self.parent.verticalFrame_similar.show()
        self.parent.toolButton_startContrast.setEnabled(False)
        self.parent.toolButton_startContrast.setText("停止对比")
        self.parent.toolButton_startContrast.clicked.disconnect()
        self.parent.toolButton_startContrast.clicked.connect(self.stop_processing)

        self.processing_state = {
            'total_images': len(image_paths),
            'processed_images': 0,
            'current_stage': 'hashing'
        }

        self.hash_worker = HashWorker(image_paths)
        self.hash_worker.hash_completed.connect(self.on_hashes_computed)
        self.hash_worker.progress_updated.connect(self.update_progress)
        self.hash_worker.error_occurred.connect(self.on_hash_error)
        self.hash_worker.start()

    def on_hashes_computed(self, hashes):
        if not hashes:
            QtWidgets.QMessageBox.information(self, "提示",
                                              "未成功计算任何图片的哈希值\n\n"
                                              "可能的原因：\n"
                                              "• 图片格式不受支持\n"
                                              "• 图片文件损坏\n"
                                              "• 图片尺寸过小或宽高比异常")
            self._running = False
            self.parent.toolButton_startContrast.setEnabled(True)
            self.parent.toolButton_startContrast.setText("开始对比")
            self.parent.toolButton_startContrast.clicked.disconnect()
            self.parent.toolButton_startContrast.clicked.connect(self.startContrast)
            return

        self.image_hashes = hashes

        self.processing_state.update({
            'current_stage': 'contrasting',
            'hashed_images': len(hashes)
        })

        similarity_percent = self.parent.horizontalSlider_levelContrast.value()
        threshold = self.get_similarity_threshold(similarity_percent)

        self.contrast_worker = ContrastWorker(self.image_hashes, threshold)
        self.contrast_worker.result_signal.connect(self.on_groups_computed)
        self.contrast_worker.progress_signal.connect(self.update_progress)
        self.contrast_worker.start()

    def on_groups_computed(self, groups):
        self.groups = {f"group_{i}": group for i, group in enumerate(groups)}
        self.display_all_images()

    def on_hash_error(self, error_msg):
        QtWidgets.QMessageBox.warning(self, "计算错误",
                                      f"图片哈希计算过程中发生错误：{error_msg}\n\n"
                                      "可能的原因：\n"
                                      "• 图片文件损坏\n"
                                      "• 内存不足\n"
                                      "• 系统资源限制")
        self._running = False
        self.parent.toolButton_startContrast.setEnabled(True)
        self.parent.toolButton_startContrast.setText("开始对比")
        self.parent.toolButton_startContrast.clicked.disconnect()
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)

    def stop_processing(self):
        if hasattr(self, 'hash_worker') and self.hash_worker.isRunning():
            self.hash_worker.stop()
            self.hash_worker.wait()

        if hasattr(self, 'contrast_worker') and self.contrast_worker.isRunning():
            self.contrast_worker.stop()
            self.contrast_worker.wait()

        for loader in self.thumbnail_loaders:
            if hasattr(loader, 'stop'):
                loader.stop()

        self._running = False
        self.parent.toolButton_startContrast.setEnabled(True)
        self.parent.toolButton_startContrast.setText("开始对比")
        self.parent.toolButton_startContrast.clicked.disconnect()
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)

        QtWidgets.QMessageBox.information(self, "处理已停止",
                                          "图片处理任务已被用户中断\n\n"
                                          "已保存当前处理进度，您可以稍后继续处理。")

    def display_all_images(self):
        layout = self.parent.gridLayout_2
        self.clear_layout(layout)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        duplicate_groups = {k: v for k, v in self.groups.items() if len(v) > 1}
        total_images = sum(len(v) for v in duplicate_groups.values())
        no_images = True
        row = col = 0

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
                if col >= 2:
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
            QtWidgets.QMessageBox.information(self, "检测完成",
                                              "未发现重复或相似的图片\n\n"
                                              "所有图片都是唯一的，无需进行去重操作")
        self.parent.toolButton_startContrast.setEnabled(True)
        self.parent.toolButton_startContrast.setText("开始对比")
        self.parent.toolButton_startContrast.clicked.disconnect()
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)

    def create_thumbnail(self, path, total_images):
        label = QtWidgets.QLabel()
        label.setFixedSize(95, 95)
        label.setProperty("image_path", path)
        label.setProperty("selected", False)
        label.setStyleSheet("QLabel{background:#F5F5F5;border:2px solid #E0E0E0;border-radius:4px;}"
                            "QLabel:hover{border:2px solid #2196F3;}QLabel[selected=true]{border:3px solid #FF5722;}")
        label.mousePressEvent = lambda e, p=path: self.preview_image(p)
        label.mouseDoubleClickEvent = lambda e, l=label: self.toggle_thumbnail_selection(l)

        if path in self.thumbnail_cache:
            label.setPixmap(QtGui.QPixmap.fromImage(self.thumbnail_cache[path]))
        else:
            if len(self.thumbnail_cache) >= self.max_cache_size:
                to_remove = int(len(self.thumbnail_cache) * 0.1)
                for key in list(self.thumbnail_cache.keys())[:to_remove]:
                    del self.thumbnail_cache[key]

            loader = ThumbnailLoader(path, QtCore.QSize(95, 95), total_images)
            loader.signals.thumbnail_ready.connect(lambda p, img: self.on_thumbnail_ready(p, img, label))
            loader.signals.progress_updated.connect(self.update_progress)
            self.thumbnail_loaders.append(loader)
            self.thread_pool.start(loader)

        return label

    def preview_image(self, path):
        if not hasattr(self.parent, 'label_image_A') or not hasattr(self.parent, 'label_image_B'):
            return

        current_group = None
        for group_id, paths in self.groups.items():
            if path in paths and len(paths) >= 2:
                current_group = paths
                break

        if not current_group or len(current_group) < 2:
            return

        current_index = current_group.index(path)

        if current_index == 0:
            compare_path = current_group[1]
        else:
            compare_path = current_group[0]

        pixmap_a = self.load_image_to_pixmap(path)
        if pixmap_a:
            self.parent.label_image_A.setPixmap(pixmap_a.scaled(
                self.parent.label_image_A.width(),
                self.parent.label_image_A.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        pixmap_b = self.load_image_to_pixmap(compare_path)
        if pixmap_b:
            self.parent.label_image_B.setPixmap(pixmap_b.scaled(
                self.parent.label_image_B.width(),
                self.parent.label_image_B.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        self.parent.verticalFrame_13.show()

    def load_image_to_pixmap(self, path):
        if path.lower().endswith(('.heic', '.heif')):
            try:
                qimage = load_heic_as_qimage(path)
                return QPixmap.fromImage(qimage)
            except Exception:
                return None
        else:
            pixmap = QPixmap(path)
            return pixmap if not pixmap.isNull() else None

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

    def on_thumbnail_ready(self, path, image, label):
        if image.isNull():
            return
        self.thumbnail_cache[path] = image.copy()
        pixmap = QPixmap.fromImage(image)
        label.setPixmap(pixmap)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setScaledContents(True)
        image = QImage()

    def update_progress(self, value):
        if value > self.current_progress:
            self.current_progress = value
            self.parent.progressBar_Contrast.setValue(value)

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
