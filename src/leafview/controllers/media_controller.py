"""媒体控制器模块

这个模块定义了LeafView应用程序中用于媒体处理的控制器。
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import pyqtSignal, QObject

from ..models.media_item import MediaItem
from ..threads.media_thread import MediaLoadThread
from ..utils.logger import LoggerMixin
from ..utils.config import Config


class MediaController(QObject, LoggerMixin):
    """媒体控制器类
    
    负责协调媒体文件的加载、显示和处理操作。
    """
    
    # 信号定义
    media_loaded = pyqtSignal(list)  # 媒体加载完成信号
    progress_updated = pyqtSignal(int, int, str)  # 进度更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, parent=None):
        """初始化媒体控制器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 初始化配置
        self.config = Config()
        
        # 初始化变量
        self.current_directory = None
        self.media_items = []
        self.current_thread = None
        self.thumbnail_dir = Path.home() / ".leafview" / "thumbnails"
        
        # 确保缩略图目录存在
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化UI组件
        self._init_ui()
        
        # 记录日志
        self.logger.info("媒体控制器初始化完成")
    
    def _init_ui(self):
        """初始化UI组件"""
        # 这里可以初始化UI相关的组件，但具体的UI元素应该在视图中定义
        pass
    
    def select_folder(self):
        """选择文件夹对话框"""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "选择文件夹",
            str(Path.home()),
            QtWidgets.QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.load_media_from_directory(Path(folder_path))
    
    def load_media_from_directory(self, directory: Path, recursive: bool = True, filters: Optional[Dict[str, Any]] = None):
        """从目录加载媒体文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归加载子目录
            filters: 过滤条件
        """
        # 如果已有线程在运行，先停止它
        if self.current_thread and self.current_thread.is_running():
            self.current_thread.stop()
            self.current_thread.wait()
        
        # 更新当前目录
        self.current_directory = directory
        
        # 清空现有媒体项
        self.media_items = []
        
        # 创建并启动加载线程
        self.current_thread = MediaLoadThread(directory, recursive, filters)
        
        # 连接信号
        self.current_thread.signals.media_item_loaded.connect(self._on_media_item_loaded)
        self.current_thread.signals.media_items_loaded.connect(self._on_media_items_loaded)
        self.current_thread.signals.progress_updated.connect(self._on_progress_updated)
        self.current_thread.signals.error_occurred.connect(self._on_error_occurred)
        self.current_thread.signals.finished.connect(self._on_thread_finished)
        
        # 启动线程
        self.current_thread.start()
        
        # 记录日志
        self.logger.info(f"开始从目录加载媒体文件: {directory}")
    
    def _on_media_item_loaded(self, media_item: MediaItem):
        """媒体项加载完成处理
        
        Args:
            media_item: 媒体项对象
        """
        self.media_items.append(media_item)
        
        # 可以在这里添加单个媒体项的处理逻辑
        # 例如，预加载缩略图等
    
    def _on_media_items_loaded(self, media_items: List[MediaItem]):
        """媒体项批量加载完成处理
        
        Args:
            media_items: 媒体项对象列表
        """
        # 更新媒体项列表
        self.media_items = media_items
        
        # 发射信号
        self.media_loaded.emit(media_items)
        
        # 更新最近使用的文件夹
        self._update_recent_folders(str(self.current_directory))
        
        # 记录日志
        self.logger.info(f"媒体文件加载完成，共 {len(media_items)} 个文件")
    
    def _on_progress_updated(self, value: int, maximum: int, message: str):
        """进度更新处理
        
        Args:
            value: 当前进度值
            maximum: 最大进度值
            message: 进度消息
        """
        # 转发进度更新信号
        self.progress_updated.emit(value, maximum, message)
    
    def _on_error_occurred(self, error_message: str):
        """错误处理
        
        Args:
            error_message: 错误消息
        """
        # 记录错误日志
        self.logger.error(f"媒体加载错误: {error_message}")
        
        # 转发错误信号
        self.error_occurred.emit(error_message)
    
    def _on_thread_finished(self):
        """线程完成处理"""
        # 清理线程引用
        self.current_thread = None
        
        # 记录日志
        self.logger.info("媒体加载线程已完成")
    
    def display_media(self, media_items: List[MediaItem]):
        """显示媒体项
        
        Args:
            media_items: 媒体项对象列表
        """
        # 这个方法应该与视图组件交互，显示媒体项
        # 具体的实现取决于UI设计
        
        # 记录日志
        self.logger.info(f"显示 {len(media_items)} 个媒体项")
    
    def get_media_item(self, index: int) -> Optional[MediaItem]:
        """获取指定索引的媒体项
        
        Args:
            index: 媒体项索引
            
        Returns:
            媒体项对象，如果索引无效则返回None
        """
        if 0 <= index < len(self.media_items):
            return self.media_items[index]
        return None
    
    def get_media_items(self) -> List[MediaItem]:
        """获取所有媒体项
        
        Returns:
            媒体项对象列表
        """
        return self.media_items
    
    def filter_media_items(self, filters: Dict[str, Any]) -> List[MediaItem]:
        """过滤媒体项
        
        Args:
            filters: 过滤条件字典
            
        Returns:
            过滤后的媒体项列表
        """
        filtered_items = self.media_items
        
        # 按媒体类型过滤
        if "media_type" in filters:
            media_type = filters["media_type"]
            filtered_items = [item for item in filtered_items if item.media_type == media_type]
        
        # 按年份过滤
        if "year" in filters:
            year = filters["year"]
            filtered_items = [item for item in filtered_items if item.get_year() == year]
        
        # 按月份过滤
        if "month" in filters:
            month = filters["month"]
            filtered_items = [item for item in filtered_items if item.get_month() == month]
        
        # 按标签过滤
        if "tags" in filters:
            tags = filters["tags"]
            if isinstance(tags, str):
                tags = [tags]
            filtered_items = [item for item in filtered_items if any(tag in item.tags for tag in tags)]
        
        return filtered_items
    
    def sort_media_items(self, key: str, reverse: bool = False) -> List[MediaItem]:
        """排序媒体项
        
        Args:
            key: 排序键
            reverse: 是否降序排序
            
        Returns:
            排序后的媒体项列表
        """
        sorted_items = self.media_items.copy()
        
        if key == "name":
            sorted_items.sort(key=lambda item: item.filename, reverse=reverse)
        elif key == "size":
            sorted_items.sort(key=lambda item: item.file_size, reverse=reverse)
        elif key == "date":
            sorted_items.sort(key=lambda item: item.get_creation_date() or item.get_modification_date(), reverse=reverse)
        elif key == "type":
            sorted_items.sort(key=lambda item: item.media_type, reverse=reverse)
        
        return sorted_items
    
    def delete_media(self, media_item: MediaItem, permanent=False):
        """删除媒体文件
        
        Args:
            media_item: 要删除的媒体项
            permanent: 是否永久删除（不放入回收站）
        """
        try:
            if permanent:
                # 永久删除
                if os.path.exists(media_item.file_path):
                    os.remove(media_item.file_path)
            else:
                # 移动到回收站
                import send2trash
                send2trash.send2trash(media_item.file_path)
            
            # 从列表中移除
            if media_item in self.media_items:
                self.media_items.remove(media_item)
                self.media_loaded.emit(self.get_filtered_media())
        except Exception as e:
            self.logger.error(f"删除媒体失败: {str(e)}")
            self.error_occurred.emit(f"删除媒体失败: {str(e)}")
    
    def move_media(self, media_item: MediaItem, destination_path: str):
        """移动媒体文件
        
        Args:
            media_item: 要移动的媒体项
            destination_path: 目标路径
        """
        try:
            if not os.path.exists(os.path.dirname(destination_path)):
                os.makedirs(os.path.dirname(destination_path))
            
            # 移动文件
            shutil.move(media_item.file_path, destination_path)
            
            # 更新媒体项路径
            media_item.file_path = destination_path
            media_item.file_name = os.path.basename(destination_path)
            
            # 更新列表
            self.media_loaded.emit(self.get_filtered_media())
        except Exception as e:
            self.logger.error(f"移动媒体失败: {str(e)}")
            self.error_occurred.emit(f"移动媒体失败: {str(e)}")
    
    def copy_media(self, media_item: MediaItem, destination_path: str):
        """复制媒体文件
        
        Args:
            media_item: 要复制的媒体项
            destination_path: 目标路径
        """
        try:
            if not os.path.exists(os.path.dirname(destination_path)):
                os.makedirs(os.path.dirname(destination_path))
            
            # 复制文件
            shutil.copy2(media_item.file_path, destination_path)
            
            # 创建新媒体项
            new_item = MediaItem(destination_path)
            self.media_items.append(new_item)
            self.media_loaded.emit(self.get_filtered_media())
        except Exception as e:
            self.logger.error(f"复制媒体失败: {str(e)}")
            self.error_occurred.emit(f"复制媒体失败: {str(e)}")
    
    def _update_recent_folders(self, folder_path: str):
        """更新最近使用的文件夹列表
        
        Args:
            folder_path: 文件夹路径
        """""
        # 获取当前最近使用的文件夹列表
        recent_folders = self.config.get_section("last_used").get("folders", [])
        
        # 如果文件夹已在列表中，先移除
        if folder_path in recent_folders:
            recent_folders.remove(folder_path)
        
        # 将文件夹添加到列表开头
        recent_folders.insert(0, folder_path)
        
        # 限制列表长度
        max_recent = 10
        if len(recent_folders) > max_recent:
            recent_folders = recent_folders[:max_recent]
        
        # 更新配置
        self.config.set("last_used", "folders", recent_folders)
        self.config.save()
    
    def get_recent_folders(self) -> List[str]:
        """获取最近使用的文件夹列表
        
        Returns:
            最近使用的文件夹路径列表
        """""
        return self.config.get_section("last_used").get("folders", [])
    
    def cleanup(self):
        """清理资源"""
        # 停止当前线程
        if self.current_thread and self.current_thread.is_running():
            self.current_thread.stop()
            self.current_thread.wait()
        
        # 记录日志
        self.logger.info("媒体控制器资源已清理")