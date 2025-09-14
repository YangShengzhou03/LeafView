"""图像去重控制器模块

这个模块定义了LeafView应用程序中用于图像去重的控制器。
"""

import os
from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ..models.media_item import MediaItem
from ..models.duplicate_result import DuplicateResult, DuplicateGroup, DuplicateAction
from ..threads.duplicate_finder_thread import DuplicateFinderThread
from ..utils.logger import LoggerMixin


class DuplicateFinderController(QObject, LoggerMixin):
    """图像去重控制器类
    
    负责协调图像去重功能，管理去重线程，处理去重结果。
    """
    
    # 信号定义
    # 进度更新信号
    progress_updated = pyqtSignal(int, int, str)  # 当前进度, 最大进度, 消息
    
    # 发现重复项信号
    duplicate_found = pyqtSignal(object, object, float)  # MediaItem对象1, MediaItem对象2, 相似度
    
    # 批量重复项信号
    duplicates_found = pyqtSignal(object)  # DuplicateResult对象
    
    # 任务完成信号
    finished = pyqtSignal(bool)  # 是否成功
    
    # 错误信号
    error_occurred = pyqtSignal(str)  # 错误消息
    
    # 结果应用信号
    result_applied = pyqtSignal(object)  # DuplicateResult对象
    
    def __init__(self, parent=None):
        """初始化图像去重控制器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 初始化变量
        self._thread = None
        self._media_items = []
        self._result = None
        self._similarity_threshold = 0.9  # 默认相似度阈值
        self._is_running = False
        
        # 配置选项
        self._config = {
            'auto_select_best': True,  # 是否自动选择最佳保留项
            'prefer_larger_resolution': True,  # 是否优先保留高分辨率图像
            'prefer_earlier_date': True,  # 是否优先保留较早日期的图像
            'skip_system_files': True,  # 是否跳过系统文件
            'skip_hidden_files': True,  # 是否跳过隐藏文件
            'max_file_size_mb': 100,  # 最大文件大小(MB)
            'min_file_size_kb': 10,  # 最小文件大小(KB)
            'supported_extensions': ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        }
    
    def set_similarity_threshold(self, threshold: float):
        """设置相似度阈值
        
        Args:
            threshold: 相似度阈值，0-1之间
        """
        if 0.0 <= threshold <= 1.0:
            self._similarity_threshold = threshold
            self.logger.info(f"相似度阈值已设置为: {threshold}")
        else:
            self.logger.warning(f"无效的相似度阈值: {threshold}，必须在0-1之间")
    
    def get_similarity_threshold(self) -> float:
        """获取当前相似度阈值
        
        Returns:
            相似度阈值
        """
        return self._similarity_threshold
    
    def set_media_items(self, media_items: List[MediaItem]):
        """设置要检查的媒体项列表
        
        Args:
            media_items: 媒体项列表
        """
        self._media_items = media_items
        self.logger.info(f"已设置 {len(media_items)} 个媒体项")
    
    def get_media_items(self) -> List[MediaItem]:
        """获取当前媒体项列表
        
        Returns:
            媒体项列表
        """
        return self._media_items
    
    def get_result(self) -> Optional[DuplicateResult]:
        """获取去重结果
        
        Returns:
            去重结果对象，如果没有结果则返回None
        """
        return self._result
    
    def set_config(self, key: str, value: Any):
        """设置配置选项
        
        Args:
            key: 配置键
            value: 配置值
        """
        if key in self._config:
            self._config[key] = value
            self.logger.info(f"配置选项 {key} 已设置为: {value}")
        else:
            self.logger.warning(f"未知的配置选项: {key}")
    
    def get_config(self, key: str) -> Any:
        """获取配置选项
        
        Args:
            key: 配置键
            
        Returns:
            配置值，如果键不存在则返回None
        """
        return self._config.get(key)
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置选项
        
        Returns:
            所有配置选项的字典
        """
        return self._config.copy()
    
    def start_finding_duplicates(self):
        """开始查找重复图像
        
        如果已有线程在运行，则先停止它。
        """
        if self._is_running:
            self.logger.warning("去重线程已在运行，先停止现有线程")
            self.stop_finding_duplicates()
        
        if not self._media_items:
            self.logger.warning("没有媒体项需要检查")
            self.error_occurred.emit("没有媒体项需要检查")
            return
        
        # 过滤媒体项
        filtered_items = self._filter_media_items(self._media_items)
        
        if not filtered_items:
            self.logger.warning("没有符合条件的媒体项需要检查")
            self.error_occurred.emit("没有符合条件的媒体项需要检查")
            return
        
        # 创建并启动线程
        self._thread = DuplicateFinderThread(filtered_items, self._similarity_threshold)
        
        # 连接信号
        self._thread.signals.progress_updated.connect(self._on_progress_updated)
        self._thread.signals.duplicate_found.connect(self._on_duplicate_found)
        self._thread.signals.duplicates_found.connect(self._on_duplicates_found)
        self._thread.signals.finished.connect(self._on_finished)
        self._thread.signals.error_occurred.connect(self._on_error_occurred)
        
        # 启动线程
        self._thread.start()
        self._is_running = True
        self.logger.info("图像去重线程已启动")
    
    def stop_finding_duplicates(self):
        """停止查找重复图像
        
        如果有线程在运行，则停止它。
        """
        if self._thread and self._thread.is_running():
            self._thread.stop()
            self._thread.wait()
            self._is_running = False
            self.logger.info("图像去重线程已停止")
    
    def is_running(self) -> bool:
        """检查去重线程是否正在运行
        
        Returns:
            如果去重线程正在运行则返回True，否则返回False
        """
        return self._is_running
    
    def apply_result(self, result: DuplicateResult = None):
        """应用去重结果
        
        执行用户选择的操作（删除、移动等）
        
        Args:
            result: 要应用的结果对象，如果为None则使用当前结果
        """
        if result is None:
            result = self._result
        
        if result is None:
            self.logger.warning("没有可应用的去重结果")
            self.error_occurred.emit("没有可应用的去重结果")
            return
        
        try:
            # 应用结果
            result.apply_actions()
            
            # 发送信号
            self.result_applied.emit(result)
            
            self.logger.info(f"已应用去重结果，处理了 {result.total_files} 个文件")
        except Exception as e:
            self.logger.error(f"应用去重结果时发生错误: {e}")
            self.error_occurred.emit(str(e))
    
    def auto_select_best_items(self, result: DuplicateResult = None):
        """自动选择每组中的最佳保留项
        
        Args:
            result: 要处理的结果对象，如果为None则使用当前结果
        """
        if result is None:
            result = self._result
        
        if result is None:
            self.logger.warning("没有可处理的结果")
            return
        
        # 配置选项
        prefer_larger_resolution = self._config.get('prefer_larger_resolution', True)
        prefer_earlier_date = self._config.get('prefer_earlier_date', True)
        
        # 为每组选择最佳项
        for group in result.groups:
            group.auto_select_best(
                prefer_larger_resolution=prefer_larger_resolution,
                prefer_earlier_date=prefer_earlier_date
            )
        
        self.logger.info("已自动选择每组中的最佳保留项")
    
    def clear_result(self):
        """清除当前结果"""
        self._result = None
        self.logger.info("已清除去重结果")
    
    def _filter_media_items(self, media_items: List[MediaItem]) -> List[MediaItem]:
        """过滤媒体项
        
        根据配置选项过滤媒体项
        
        Args:
            media_items: 原始媒体项列表
            
        Returns:
            过滤后的媒体项列表
        """
        filtered_items = []
        
        # 获取配置选项
        skip_system_files = self._config.get('skip_system_files', True)
        skip_hidden_files = self._config.get('skip_hidden_files', True)
        max_file_size_mb = self._config.get('max_file_size_mb', 100)
        min_file_size_kb = self._config.get('min_file_size_kb', 10)
        supported_extensions = self._config.get('supported_extensions', [])
        
        # 转换文件大小限制为字节
        max_file_size = max_file_size_mb * 1024 * 1024
        min_file_size = min_file_size_kb * 1024
        
        for item in media_items:
            # 检查文件扩展名
            if supported_extensions and item.file_path.suffix.lower() not in supported_extensions:
                continue
            
            # 检查文件大小
            if item.file_size < min_file_size or item.file_size > max_file_size:
                continue
            
            # 检查系统文件
            if skip_system_files and self._is_system_file(item.file_path):
                continue
            
            # 检查隐藏文件
            if skip_hidden_files and self._is_hidden_file(item.file_path):
                continue
            
            filtered_items.append(item)
        
        self.logger.info(f"从 {len(media_items)} 个媒体项中过滤出 {len(filtered_items)} 个符合条件的项")
        return filtered_items
    
    def _is_system_file(self, file_path) -> bool:
        """检查文件是否为系统文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            如果是系统文件则返回True，否则返回False
        """
        try:
            # 在Windows上检查系统属性
            if os.name == 'nt':
                import win32api, win32con
                attrs = win32api.GetFileAttributes(str(file_path))
                return attrs & (win32con.FILE_ATTRIBUTE_SYSTEM | win32con.FILE_ATTRIBUTE_HIDDEN)
            else:
                # 在其他系统上，检查是否在系统目录中
                system_dirs = ['/System', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin']
                return any(str(file_path).startswith(d) for d in system_dirs)
        except Exception:
            return False
    
    def _is_hidden_file(self, file_path) -> bool:
        """检查文件是否为隐藏文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            如果是隐藏文件则返回True，否则返回False
        """
        try:
            # 在Windows上检查隐藏属性
            if os.name == 'nt':
                import win32api, win32con
                attrs = win32api.GetFileAttributes(str(file_path))
                return attrs & win32con.FILE_ATTRIBUTE_HIDDEN
            else:
                # 在其他系统上，检查文件名是否以点开头
                return file_path.name.startswith('.')
        except Exception:
            return False
    
    @pyqtSlot(int, int, str)
    def _on_progress_updated(self, current: int, total: int, message: str):
        """处理进度更新信号
        
        Args:
            current: 当前进度
            total: 总进度
            message: 进度消息
        """
        self.progress_updated.emit(current, total, message)
    
    @pyqtSlot(object, object, float)
    def _on_duplicate_found(self, item1: MediaItem, item2: MediaItem, similarity: float):
        """处理发现重复项信号
        
        Args:
            item1: 第一个媒体项
            item2: 第二个媒体项
            similarity: 相似度
        """
        self.duplicate_found.emit(item1, item2, similarity)
    
    @pyqtSlot(object)
    def _on_duplicates_found(self, result: DuplicateResult):
        """处理批量重复项信号
        
        Args:
            result: 去重结果对象
        """
        self._result = result
        self.duplicates_found.emit(result)
        
        # 如果配置了自动选择最佳项，则执行自动选择
        if self._config.get('auto_select_best', True):
            self.auto_select_best_items(result)
    
    @pyqtSlot(bool)
    def _on_finished(self, success: bool):
        """处理任务完成信号
        
        Args:
            success: 是否成功
        """
        self._is_running = False
        self.finished.emit(success)
    
    @pyqtSlot(str)
    def _on_error_occurred(self, error_message: str):
        """处理错误信号
        
        Args:
            error_message: 错误消息
        """
        self.error_occurred.emit(error_message)