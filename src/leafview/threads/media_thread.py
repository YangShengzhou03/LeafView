"""媒体处理线程模块

这个模块定义了LeafView应用程序中用于媒体处理的后台线程。
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from ..models.media_item import MediaItem
from ..utils.logger import LoggerMixin


class MediaThreadSignals(QObject):
    """媒体线程信号类
    
    定义了媒体处理线程使用的信号。
    """
    
    # 进度更新信号
    progress_updated = pyqtSignal(int, int, str)  # 当前进度, 最大进度, 消息
    
    # 媒体项加载完成信号
    media_item_loaded = pyqtSignal(object)  # MediaItem对象
    
    # 媒体项加载完成信号（批量）
    media_items_loaded = pyqtSignal(list)  # MediaItem对象列表
    
    # 任务完成信号
    finished = pyqtSignal()
    
    # 错误信号
    error_occurred = pyqtSignal(str)  # 错误消息


class MediaThread(QThread, LoggerMixin):
    """媒体处理线程类
    
    用于在后台处理媒体文件，如加载、分类等操作。
    """
    
    def __init__(self, parent=None):
        """初始化媒体处理线程
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 创建信号对象
        self.signals = MediaThreadSignals()
        
        # 初始化变量
        self._is_running = False
        self._should_stop = False
        
        # 支持的文件扩展名
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    
    def stop(self):
        """停止线程执行"""
        self._should_stop = True
        # 等待最多1秒让线程自然结束
        if self.isRunning():
            self.wait(1000)
        self.logger.info("媒体处理线程已请求停止")
    
    def run(self):
        """线程主运行方法"""
        self._is_running = True
        self._should_stop = False
        
        try:
            self._process_media()
        except Exception as e:
            self.logger.error(f"媒体处理线程发生错误: {e}")
            self.signals.error_occurred.emit(str(e))
        finally:
            self._is_running = False
            self.signals.finished.emit()
            self.logger.info("媒体处理线程已结束")
    
    def _process_media(self):
        """处理媒体文件
        
        子类应重写此方法以实现特定的媒体处理逻辑。
        """
        pass
    
    def _collect_files(self, directory: Path, recursive: bool = True) -> List[Path]:
        """收集目录中的媒体文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归搜索子目录
            
        Returns:
            媒体文件路径列表
        """
        if not directory.exists() or not directory.is_dir():
            self.logger.warning(f"目录不存在或不是目录: {directory}")
            return []
        
        files = []
        
        try:
            if recursive:
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        file_path = Path(root) / filename
                        if self._is_media_file(file_path):
                            files.append(file_path)
            else:
                for item in directory.iterdir():
                    if item.is_file() and self._is_media_file(item):
                        files.append(item)
        except Exception as e:
            self.logger.error(f"收集文件时发生错误: {e}")
            self.signals.error_occurred.emit(f"收集文件时发生错误: {e}")
            return []
        
        return files
    
    def _is_media_file(self, file_path: Path) -> bool:
        """检查文件是否为媒体文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            如果是媒体文件则返回True，否则返回False
        """
        # 检查文件扩展名
        ext = file_path.suffix.lower()
        return ext in self.image_extensions or ext in self.video_extensions
    
    def _filter_files(self, files: List[Path], filters: Optional[Dict[str, Any]] = None) -> List[Path]:
        """过滤文件列表
        
        Args:
            files: 文件路径列表
            filters: 过滤条件字典
            
        Returns:
            过滤后的文件路径列表
        """
        if not filters:
            return files
        
        filtered_files = files
        
        # 按文件名模式过滤
        if "name_pattern" in filters:
            pattern = filters["name_pattern"]
            try:
                regex = re.compile(pattern)
                filtered_files = [f for f in filtered_files if regex.search(f.name)]
            except re.error as e:
                self.logger.warning(f"无效的正则表达式: {pattern}, 错误: {e}")
        
        # 按文件大小过滤
        if "min_size" in filters:
            min_size = filters["min_size"]
            filtered_files = [f for f in filtered_files if f.stat().st_size >= min_size]
        
        if "max_size" in filters:
            max_size = filters["max_size"]
            filtered_files = [f for f in filtered_files if f.stat().st_size <= max_size]
        
        # 按修改日期过滤
        if "modified_after" in filters:
            modified_after = filters["modified_after"]
            filtered_files = [f for f in filtered_files if f.stat().st_mtime >= modified_after]
        
        if "modified_before" in filters:
            modified_before = filters["modified_before"]
            filtered_files = [f for f in filtered_files if f.stat().st_mtime <= modified_before]
        
        return filtered_files
    
    def _create_media_item(self, file_path: Path) -> Optional[MediaItem]:
        """创建媒体项
        
        Args:
            file_path: 文件路径
            
        Returns:
            媒体项对象，如果创建失败则返回None
        """
        try:
            return MediaItem(str(file_path))
        except Exception as e:
            self.logger.error(f"创建媒体项失败: {file_path}, 错误: {e}")
            return None
    
    def _check_should_stop(self) -> bool:
        """检查是否应该停止线程
        
        Returns:
            如果应该停止则返回True，否则返回False
        """
        return self._should_stop
    
    def is_running(self) -> bool:
        """检查线程是否正在运行
        
        Returns:
            如果线程正在运行则返回True，否则返回False
        """
        return self._is_running


class MediaLoadThread(MediaThread):
    """媒体加载线程类
    
    专门用于加载媒体文件的线程。
    """
    
    def __init__(self, directory: Path, recursive: bool = True, filters: Optional[Dict[str, Any]] = None, parent=None):
        """初始化媒体加载线程
        
        Args:
            directory: 要加载的目录
            recursive: 是否递归加载子目录
            filters: 过滤条件
            parent: 父对象
        """
        super().__init__(parent)
        
        self.directory = directory
        self.recursive = recursive
        self.filters = filters or {}
        
        self.media_items = []
    
    def _process_media(self):
        """处理媒体文件"""
        self.logger.info(f"开始加载媒体文件，目录: {self.directory}")
        
        # 收集文件
        self.signals.progress_updated.emit(0, 100, "正在收集文件...")
        files = self._collect_files(self.directory, self.recursive)
        
        if self._check_should_stop():
            return
        
        # 过滤文件
        if self.filters:
            self.signals.progress_updated.emit(10, 100, "正在过滤文件...")
            files = self._filter_files(files, self.filters)
        
        if self._check_should_stop():
            return
        
        # 创建媒体项
        total_files = len(files)
        self.signals.progress_updated.emit(20, 100, f"正在加载 {total_files} 个文件...")
        
        for i, file_path in enumerate(files):
            if self._check_should_stop():
                break
            
            # 更新进度
            progress = int(20 + (i / total_files) * 80)
            self.signals.progress_updated.emit(progress, 100, f"正在加载 {i+1}/{total_files}...")
            
            # 创建媒体项
            media_item = self._create_media_item(file_path)
            if media_item:
                self.media_items.append(media_item)
                self.signals.media_item_loaded.emit(media_item)
        
        # 发送完成信号
        self.signals.media_items_loaded.emit(self.media_items)
        self.signals.progress_updated.emit(100, 100, f"加载完成，共 {len(self.media_items)} 个文件")
        
        self.logger.info(f"媒体文件加载完成，共 {len(self.media_items)} 个文件")