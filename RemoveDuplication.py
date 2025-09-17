"""
图片去重模块 - 基于图像哈希算法检测和删除重复或相似的图片

该模块提供以下功能：
1. 支持多种图像格式（包括HEIC/HEIF等特殊格式）
2. 基于感知哈希算法计算图像相似度
3. 可视化相似图片分组展示
4. 批量选择和操作（移动、删除）重复图片
5. 多线程处理提高性能
"""

import os
import shutil

import numpy as np
import pillow_heif
import send2trash
from PIL import Image
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, QRunnable, QObject, Qt, QThreadPool
from PyQt6.QtGui import QPixmap, QImage

from RemoveDuplicationThread import HashWorker, ContrastWorker
from common import get_resource_path


class ThumbnailLoaderSignals(QObject):
    """缩略图加载器信号类 - 用于线程间通信"""
    thumbnail_ready = pyqtSignal(str, QImage)  # 缩略图加载完成信号
    progress_updated = pyqtSignal(int)         # 进度更新信号


def load_heic_as_qimage(path):
    """
    加载HEIC/HEIF格式图片并转换为QImage对象
    
    Args:
        path (str): HEIC/HEIF图片文件路径
        
    Returns:
        QImage: 转换后的QImage对象
    """
    heif_file = pillow_heif.read_heif(path)
    image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = image.tobytes()
    qimage = QImage(buffer, image.width, image.height, QImage.Format.Format_RGB888)
    return qimage.copy()


class ThumbnailLoader(QRunnable):
    """缩略图加载器 - 在后台线程中异步加载图片缩略图"""
    
    def __init__(self, path, size, total_images):
        """
        初始化缩略图加载器
        
        Args:
            path (str): 图片文件路径
            size (QSize): 缩略图目标尺寸
            total_images (int): 总图片数量（用于进度计算）
        """
        super().__init__()
        self.path = path
        self.size = size
        self.total_images = total_images
        self.signals = ThumbnailLoaderSignals()
        self._is_running = True

    def run(self):
        """在后台线程中执行缩略图加载任务"""
        if not self._is_running:
            return
            
        image = QImage()
        # 特殊处理HEIC/HEIF格式
        if self.path.lower().endswith(('.heic', '.heif')):
            try:
                image = load_heic_as_qimage(self.path)
            except Exception:
                pass
        else:
            image.load(self.path)

        if not image.isNull() and self._is_running:
            # 缩放图片到指定尺寸，保持宽高比
            scaled_image = image.scaled(self.size.width(), self.size.height(),
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            self.signals.thumbnail_ready.emit(self.path, scaled_image)
            # 计算并发送进度更新（80-100%范围）
            progress = 80 + int((1 / self.total_images) * 20)
            self.signals.progress_updated.emit(progress)
        
        if self._is_running:
            self.signals.progress_updated.emit(100)
        
        # 修复内存泄漏：显式释放图像资源
        if not image.isNull():
            image = QImage()
    
    def stop(self):
        """停止缩略图加载"""
        self._is_running = False


class Contrast(QtWidgets.QWidget):
    """图片去重对比主类 - 实现相似图片检测和管理的核心功能"""
    
    def __init__(self, parent=None, folder_page=None):
        """
        初始化图片去重对比组件
        
        Args:
            parent: 父组件
            folder_page: 文件夹页面组件，用于获取文件夹信息
        """
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.groups = {}           # 相似图片分组字典
        self.image_hashes = {}     # 图片哈希值字典
        self._running = False      # 处理状态标志
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)  # 限制最大线程数
        self.selected_images = []   # 用户选中的图片列表
        self.thumbnail_cache = {}  # 缩略图缓存字典
        self.init_page()
        self.connect_signals()
        self.thumbnail_loaders = []  # 缩略图加载器列表

    def init_page(self):
        """初始化界面组件状态"""
        self.parent.horizontalSlider_levelContrast.setRange(0, 100)
        self.parent.horizontalSlider_levelContrast.setValue(100)
        self.parent.verticalFrame_similar.hide()

    def get_similarity_threshold(self, val):
        """
        将相似度百分比值转换为汉明距离阈值
        
        Args:
            val (int): 相似度百分比值 (0-100)
            
        Returns:
            int: 汉明距离阈值 (64-0)
        """
        # 将百分比值转换为汉明距离阈值 (0-100% -> 64-0)
        # 0% = 巨大差异 (阈值64), 100% = 完全一致 (阈值0)
        return int(64 * (100 - val) / 100)

    def on_slider_value_changed(self, val):
        """
        相似度滑块值变化处理 - 更新显示文本和颜色
        
        Args:
            val (int): 滑块当前值
        """
        # 根据百分比值显示不同的文本和颜色
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
        """连接信号和槽函数"""
        self.parent.horizontalSlider_levelContrast.valueChanged.connect(self.on_slider_value_changed)
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)
        self.parent.toolButton_move.clicked.connect(self.move_selected_images)
        self.parent.toolButton_autoSelect.clicked.connect(self.auto_select_images)
        self.parent.toolButton_delete.clicked.connect(self.delete_selected_images)

    def move_selected_images(self):
        """移动选中的图片到指定文件夹"""
        dest_folder = QtWidgets.QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if not dest_folder:
            return
        for img in self.selected_images:
            try:
                shutil.move(img, os.path.join(dest_folder, os.path.basename(img)))
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "❌ 无法移动图片", 
                                           f"无法移动图片 {os.path.basename(img)}: {e}\n\n"
                                           "可能的原因：\n"
                                           "• 目标文件夹权限不足\n"
                                           "• 文件正在被其他程序使用\n"
                                           "• 磁盘空间不足")
        self.display_all_images()

    def auto_select_images(self):
        """自动选择重复图片 - 保留每组中最大的文件"""
        self.selected_images.clear()
        for group_id, paths in self.groups.items():
            if len(paths) <= 1:
                continue
            # 选择每组中文件大小最大的图片作为保留项
            best = max(paths, key=lambda x: os.path.getsize(x))
            self.selected_images.extend([p for p in paths if p != best])
        self.refresh_selection_visuals()

    def delete_selected_images(self):
        """删除选中的图片（移动到回收站）"""
        if not self.selected_images:
            QtWidgets.QMessageBox.information(self, "ℹ️ 提示", "当前没有选中任何图片\n\n"
                                           "请先选择要删除的重复图片")
            return
            
        reply = QtWidgets.QMessageBox.question(self, '⚠️ 确认删除', 
                                             f"确定要将选中的 {len(self.selected_images)} 张图片移动到回收站吗？\n\n"
                                             "⚠️ 此操作不可撤销，建议先备份重要文件。\n\n"
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
                QtWidgets.QMessageBox.warning(self, "❌ 删除失败", 
                                           f"无法删除图片 {os.path.basename(img)}: {str(e)}\n\n"
                                           "可能的原因：\n"
                                           "• 文件正在被其他程序使用\n"
                                           "• 回收站功能异常\n"
                                           "• 权限不足")
        
        # 显示操作结果
        if success_count > 0:
            QtWidgets.QMessageBox.information(self, "✅ 操作完成", 
                                             f"成功删除 {success_count} 张图片到回收站{f'，{failed_count} 张删除失败' if failed_count > 0 else ''}\n\n"
                                             "您可以在回收站中查看或恢复已删除的文件。")
        
        self.selected_images.clear()
        self.display_all_images()

    def refresh_selection_visuals(self):
        """刷新选中状态的视觉显示"""
        layout = self.parent.gridLayout_2
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, QtWidgets.QLabel):
                path = widget.property("image_path")
                widget.setProperty("selected", path in self.selected_images)
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    def startContrast(self):
        """开始相似图片检测流程"""
        folders = self.folder_page.get_all_folders() if self.folder_page else []
        if not folders:
            QtWidgets.QMessageBox.warning(self, "⚠️ 操作提示", 
                                       "请先导入包含图片的文件夹\n\n"
                                       "点击导入文件夹按钮添加要检测的文件夹")
            return

        self._running = True
        self.parent.verticalFrame_similar.show()
        self.parent.progressBar_Contrast.setValue(0)
        # 支持的图片格式集合
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tif', '.tiff',
                             '.heif', '.heic', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
                             '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc'}
        image_paths = []
        for folder_info in folders:
            folder_path = folder_info['path']
            if folder_info['include_sub'] == 1:
                # 包含子文件夹：递归遍历所有子目录
                for root, _, files in os.walk(folder_path):
                    image_paths.extend(os.path.join(root, f) for f in files
                                       if os.path.splitext(f)[1].lower() in supported_formats)
            else:
                # 不包含子文件夹：只处理当前目录
                image_paths.extend(os.path.join(folder_path, f) for f in os.listdir(folder_path)
                                   if os.path.splitext(f)[1].lower() in supported_formats)
        
        # 检查是否找到图片
        if not image_paths:
            QtWidgets.QMessageBox.information(self, "ℹ️ 提示", 
                                           "在所选文件夹中未找到支持的图片文件\n\n"
                                           "支持的格式：.jpg/.jpeg/.png/.bmp/.gif/.webp/.tif/.tiff/.heif/.heic\n"
                                           "请检查文件夹路径和文件格式")
            self._running = False
            self.parent.toolButton_startContrast.setEnabled(True)
            return
        
        # 限制处理图片数量，避免内存溢出
        if len(image_paths) > 1000:
            reply = QtWidgets.QMessageBox.question(self, "⚠️ 图片数量较多", 
                                                  f"检测到 {len(image_paths)} 张图片，处理可能需要一些时间。是否继续？\n\n"
                                                  "处理大量图片时：\n"
                                                  "• 可能需要几分钟到几十分钟\n"
                                                  "• 会占用较多内存资源",
                                                  QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                  QtWidgets.QMessageBox.StandardButton.Yes)
            if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                self._running = False
                self.parent.toolButton_startContrast.setEnabled(True)
                return
        
        self.parent.toolButton_startContrast.setEnabled(False)
        # 修改开始按钮为停止功能
        self.parent.toolButton_startContrast.setText("停止对比")
        self.parent.toolButton_startContrast.clicked.disconnect()
        self.parent.toolButton_startContrast.clicked.connect(self.stop_processing)
        
        # 保存处理状态信息
        self.processing_state = {
            'total_images': len(image_paths),
            'processed_images': 0,
            'current_stage': 'hashing'
        }
        
        # 创建并启动哈希计算工作线程
        self.hash_worker = HashWorker(image_paths)
        self.hash_worker.hash_completed.connect(self.on_hashes_computed)
        self.hash_worker.progress_updated.connect(self.update_progress)
        self.hash_worker.error_occurred.connect(self.on_hash_error)
        self.hash_worker.start()

    def on_hashes_computed(self, hashes):
        """哈希计算完成处理"""
        if not hashes:
            QtWidgets.QMessageBox.information(self, "ℹ️ 提示", 
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
        
        # 保存哈希结果
        self.image_hashes = hashes
        
        # 更新处理状态
        self.processing_state.update({
            'current_stage': 'contrasting',
            'hashed_images': len(hashes)
        })
        
        # 获取相似度阈值
        similarity_percent = self.parent.horizontalSlider_levelContrast.value()
        threshold = self.get_similarity_threshold(similarity_percent)
        
        # 创建并启动相似度对比工作线程
        self.contrast_worker = ContrastWorker(self.image_hashes, threshold)
        self.contrast_worker.result_signal.connect(self.on_groups_computed)
        self.contrast_worker.progress_signal.connect(self.update_progress)
        self.contrast_worker.start()

    def on_groups_computed(self, groups):
        """相似度对比完成处理"""
        # 将列表格式的相似组转换为字典格式，键为组ID，值为图片路径列表
        self.groups = {f"group_{i}": group for i, group in enumerate(groups)}
        self.display_all_images()

    def on_hash_error(self, error_msg):
        """哈希计算错误处理"""
        QtWidgets.QMessageBox.warning(self, "❌ 计算错误", 
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
        """停止正在进行的处理任务"""
        if hasattr(self, 'hash_worker') and self.hash_worker.isRunning():
            self.hash_worker.stop()
            self.hash_worker.wait()
        
        if hasattr(self, 'contrast_worker') and self.contrast_worker.isRunning():
            self.contrast_worker.stop()
            self.contrast_worker.wait()
        
        # 停止所有缩略图加载器
        for loader in self.thumbnail_loaders:
            if hasattr(loader, 'stop'):
                loader.stop()
        
        self._running = False
        self.parent.toolButton_startContrast.setEnabled(True)
        self.parent.toolButton_startContrast.setText("开始对比")
        self.parent.toolButton_startContrast.clicked.disconnect()
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)
        
        QtWidgets.QMessageBox.information(self, "⏹️ 处理已停止", 
                                       "图片处理任务已被用户中断\n\n"
                                       "已保存当前处理进度，您可以稍后继续处理。")

    def display_all_images(self):
        """显示所有相似图片分组"""
        layout = self.parent.gridLayout_2
        self.clear_layout(layout)
        # 设置布局对齐方式为顶部对齐，避免单个项目垂直居中
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        # 只显示有重复的组（图片数量>1）
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
            # 添加分组标题
            title = QtWidgets.QLabel(f"📁 第{idx}组 ({len(paths)}张)")
            title.setStyleSheet("QLabel{font:bold 14px;color:#1976D2;padding:2px 0;}")
            layout.addWidget(title, row, 0, 1, 4)
            row += 1
            # 添加该组的所有图片缩略图
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
        # 恢复开始按钮状态
        self.parent.toolButton_startContrast.setEnabled(True)
        self.parent.toolButton_startContrast.setText("开始对比")
        self.parent.toolButton_startContrast.clicked.disconnect()
        self.parent.toolButton_startContrast.clicked.connect(self.startContrast)

    def create_thumbnail(self, path, total_images):
        """创建单个图片缩略图组件"""
        label = QtWidgets.QLabel()
        label.setFixedSize(95, 95)
        label.setProperty("image_path", path)
        label.setProperty("selected", False)
        label.setStyleSheet("QLabel{background:#F5F5F5;border:2px solid #E0E0E0;border-radius:4px;}"
                            "QLabel:hover{border:2px solid #2196F3;}QLabel[selected=true]{border:3px solid #FF5722;}")
        label.mousePressEvent = lambda e, p=path: self.preview_image(p)
        label.mouseDoubleClickEvent = lambda e, l=label: self.toggle_thumbnail_selection(l)
        
        # 检查缓存中是否已有缩略图
        if path in self.thumbnail_cache:
            label.setPixmap(QtGui.QPixmap.fromImage(self.thumbnail_cache[path]))
        else:
            # 创建并启动缩略图加载器
            loader = ThumbnailLoader(path, QtCore.QSize(95, 95), total_images)
            loader.signals.thumbnail_ready.connect(lambda p, img: self.on_thumbnail_ready(p, img, label))
            loader.signals.progress_updated.connect(self.update_progress)
            self.thumbnail_loaders.append(loader)
            self.thread_pool.start(loader)
        
        return label

    def preview_image(self, path):
        """在对比窗口中预览图片"""
        if not hasattr(self.parent, 'label_image_A') or not hasattr(self.parent, 'label_image_B'):
            return
            
        # 获取当前选中的缩略图组
        current_group = None
        for group_id, paths in self.groups.items():
            if path in paths and len(paths) >= 2:
                current_group = paths
                break
        
        if not current_group or len(current_group) < 2:
            return
        
        # 找到当前图片在组中的索引
        current_index = current_group.index(path)
        
        # 确定要对比的另一张图片
        if current_index == 0:
            compare_path = current_group[1]
        else:
            compare_path = current_group[0]
        
        # 加载并显示第一张图片到label_image_A
        pixmap_a = self.load_image_to_pixmap(path)
        if pixmap_a:
            self.parent.label_image_A.setPixmap(pixmap_a.scaled(
                self.parent.label_image_A.width(), 
                self.parent.label_image_A.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        
        # 加载并显示第二张图片到label_image_B
        pixmap_b = self.load_image_to_pixmap(compare_path)
        if pixmap_b:
            self.parent.label_image_B.setPixmap(pixmap_b.scaled(
                self.parent.label_image_B.width(), 
                self.parent.label_image_B.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        
        # 显示对比窗口
        self.parent.verticalFrame_13.show()

    def load_image_to_pixmap(self, path):
        """加载图片并转换为QPixmap"""
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
        """切换缩略图选中状态"""
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
        """缩略图加载完成回调 - 设置缩略图显示"""
        if image.isNull():
            return
        # 缓存缩略图
        self.thumbnail_cache[path] = image.copy()
        pixmap = QPixmap.fromImage(image)
        label.setPixmap(pixmap)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setScaledContents(True)
        # 修复内存泄漏：释放图像资源
        image = QImage()

    def update_progress(self, value):
        """更新进度条显示"""
        self.parent.progressBar_Contrast.setValue(value)

    def add_separator(self, layout, row):
        """添加分隔线"""
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("border:1px dashed #BDBDBD;")
        layout.addWidget(sep, row, 0, 1, layout.columnCount())

    def clear_layout(self, layout):
        """清空布局中的所有组件"""
        while layout.count():
            item = layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

    def show_image(self, label, path):
        """在指定标签中显示图片"""
        # 特殊处理HEIC/HEIF格式
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
        # 处理普通图片格式
        pix = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(label.width(), label.height(),
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(pix)

    def stop_processing(self):
        """停止所有处理任务"""
        self._running = False
        if hasattr(self, 'hash_worker'):
            self.hash_worker.stop()
        if hasattr(self, 'contrast_worker'):
            self.contrast_worker.stop()
        # 停止所有缩略图加载器
        self.thumbnail_loaders.clear()
