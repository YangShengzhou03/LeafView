"""分类控制器模块

这个模块定义了LeafView应用程序中用于媒体文件分类的控制器。
"""

import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from enum import Enum
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import pyqtSignal, QObject

from ..models.media_item import MediaItem
from ..utils.logger import LoggerMixin
from ..utils.config import Config


class ClassificationMethod(Enum):
    """分类方法枚举"""
    DATE = "date"  # 按日期分类
    TYPE = "type"  # 按类型分类
    SIZE = "size"  # 按大小分类
    TAG = "tag"  # 按标签分类
    CUSTOM = "custom"  # 自定义分类


class ClassificationOperation(Enum):
    """分类操作类型枚举"""
    MOVE = "move"  # 移动文件
    COPY = "copy"  # 复制文件
    LINK = "link"  # 创建链接


class ClassificationRule:
    """分类规则类
    
    定义了分类的规则和条件。
    """
    
    def __init__(self, name: str, method: ClassificationMethod, 
                 structure: List[str], operation: ClassificationOperation = ClassificationOperation.MOVE,
                 conditions: Optional[Dict[str, Any]] = None,
                 enabled: bool = True):
        """初始化分类规则
        
        Args:
            name: 规则名称
            method: 分类方法
            structure: 目录结构
            operation: 操作类型
            conditions: 条件字典
            enabled: 是否启用
        """
        self.name = name
        self.method = method
        self.structure = structure
        self.operation = operation
        self.conditions = conditions or {}
        self.enabled = enabled
        
        # 统计信息
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """将规则转换为字典
        
        Returns:
            规则字典
        """
        return {
            "name": self.name,
            "method": self.method.value,
            "structure": self.structure,
            "operation": self.operation.value,
            "conditions": self.conditions,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassificationRule':
        """从字典创建规则
        
        Args:
            data: 规则字典
            
        Returns:
            分类规则对象
        """
        method = ClassificationMethod(data.get("method", ClassificationMethod.DATE.value))
        operation = ClassificationOperation(data.get("operation", ClassificationOperation.MOVE.value))
        
        return cls(
            name=data.get("name", "未命名规则"),
            method=method,
            structure=data.get("structure", ["year", "month"]),
            operation=operation,
            conditions=data.get("conditions", {}),
            enabled=data.get("enabled", True)
        )
    
    def matches(self, media_item: MediaItem) -> bool:
        """检查媒体项是否匹配规则
        
        Args:
            media_item: 媒体项对象
            
        Returns:
            是否匹配
        """
        if not self.enabled:
            return False
            
        # 检查条件
        for key, value in self.conditions.items():
            if key == "file_types":
                # 检查文件类型
                if media_item.extension.lower() not in [ft.lower() for ft in value]:
                    return False
            elif key == "min_size":
                # 检查最小文件大小
                if media_item.size < value:
                    return False
            elif key == "max_size":
                # 检查最大文件大小
                if media_item.size > value:
                    return False
            elif key == "tags":
                # 检查标签
                if not any(tag in media_item.tags for tag in value):
                    return False
            elif key == "date_range":
                # 检查日期范围
                if "start" in value and media_item.date_time and media_item.date_time < value["start"]:
                    return False
                if "end" in value and media_item.date_time and media_item.date_time > value["end"]:
                    return False
        
        return True


class ClassificationThreadSignals(QObject):
    """分类线程信号类
    
    定义了分类线程使用的信号。
    """
    
    # 进度更新信号
    progress_updated = pyqtSignal(int, int, str)  # 当前进度, 最大进度, 消息
    
    # 文件处理信号
    file_processed = pyqtSignal(str, bool, str)  # 文件路径, 是否成功, 消息
    
    # 任务完成信号
    finished = pyqtSignal(bool)  # 是否成功
    
    # 错误信号
    error_occurred = pyqtSignal(str)  # 错误消息
    
    # 规则应用信号
    rule_applied = pyqtSignal(str, str, int)  # 规则名称, 文件路径, 处理数量


class ClassificationThread(QtCore.QThread, LoggerMixin):
    """分类线程类
    
    用于在后台执行媒体文件分类操作。
    """
    
    def __init__(self, media_items: List[MediaItem], target_directory: Path, 
                 rules: List[ClassificationRule], separator: str = "_", 
                 parent=None):
        """初始化分类线程
        
        Args:
            media_items: 要分类的媒体项列表
            target_directory: 目标目录
            rules: 分类规则列表
            separator: 文件名分隔符
            parent: 父对象
        """
        super().__init__(parent)
        
        # 创建信号对象
        self.signals = ClassificationThreadSignals()
        
        # 初始化变量
        self.media_items = media_items
        self.target_directory = target_directory
        self.rules = rules
        self.separator = separator
        
        self._is_running = False
        self._should_stop = False
        
        # 统计信息
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # 规则统计
        self.rule_stats = {rule.name: {"processed": 0, "success": 0, "error": 0} for rule in rules}
    
    def stop(self):
        """停止分类线程"""
        self._should_stop = True
        # 确保线程能够及时响应停止请求
        self.wait(1000)  # 等待最多1秒让线程自然结束
        self.logger.info("分类线程已请求停止")
    
    def run(self):
        """线程主运行方法"""
        self._is_running = True
        self._should_stop = False
        
        try:
            success = self._classify_media()
            self.signals.finished.emit(success)
        except Exception as e:
            self.logger.error(f"分类线程发生错误: {e}")
            self.signals.error_occurred.emit(str(e))
            self.signals.finished.emit(False)
        finally:
            self._is_running = False
            self.logger.info("分类线程已结束")
    
    def _classify_media(self) -> bool:
        """分类媒体文件
        
        Returns:
            分类是否成功
        """
        total_items = len(self.media_items)
        
        if total_items == 0:
            self.signals.progress_updated.emit(100, 100, "没有文件需要分类")
            return True
        
        # 确保目标目录存在
        self.target_directory.mkdir(parents=True, exist_ok=True)
        
        # 处理每个媒体项
        for i, media_item in enumerate(self.media_items):
            # 更频繁地检查停止标志
            if self._should_stop:
                self.signals.progress_updated.emit(100, 100, "分类已停止")
                return False
            
            # 更新进度
            progress = int((i / total_items) * 100)
            self.signals.progress_updated.emit(progress, 100, f"正在处理 {i+1}/{total_items}...")
            
            # 查找匹配的规则
            matched_rule = None
            for rule in self.rules:
                if rule.matches(media_item):
                    matched_rule = rule
                    break
            
            # 如果没有匹配的规则，跳过该文件
            if not matched_rule:
                self.signals.file_processed.emit(str(media_item.file_path), False, "没有匹配的分类规则")
                continue
            
            # 处理媒体项
            success, message = self._process_media_item(media_item, matched_rule)
            
            # 更新规则统计
            self.rule_stats[matched_rule.name]["processed"] += 1
            if success:
                self.rule_stats[matched_rule.name]["success"] += 1
            else:
                self.rule_stats[matched_rule.name]["error"] += 1
            
            # 处理完成后再次检查停止标志
            if self._should_stop:
                self.signals.progress_updated.emit(progress, 100, "分类已停止")
                return False
                
            self.processed_count += 1
            
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
            
            # 发送文件处理信号
            self.signals.file_processed.emit(str(media_item.file_path), success, message)
            
            # 发送规则应用信号
            self.signals.rule_applied.emit(matched_rule.name, str(media_item.file_path), 
                                         self.rule_stats[matched_rule.name]["processed"])
        
        # 更新最终进度
        if self._should_stop:
            self.signals.progress_updated.emit(100, 100, f"分类已停止: 成功 {self.success_count}, 失败 {self.error_count}")
        else:
            self.signals.progress_updated.emit(100, 100, 
                f"分类完成: 成功 {self.success_count}, 失败 {self.error_count}")
        
        return self.error_count == 0
    
    def _process_media_item(self, media_item: MediaItem, rule: ClassificationRule) -> Tuple[bool, str]:
        """处理单个媒体项
        
        Args:
            media_item: 媒体项对象
            rule: 适用的分类规则
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 构建目标路径
            target_path = self._build_target_path(media_item, rule)
            
            # 确保目标目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查目标文件是否已存在
            if target_path.exists():
                # 如果文件已存在，添加序号
                counter = 1
                while True:
                    stem = target_path.stem
                    suffix = target_path.suffix
                    new_name = f"{stem}{self.separator}{counter}{suffix}"
                    new_path = target_path.with_name(new_name)
                    
                    if not new_path.exists():
                        target_path = new_path
                        break
                    
                    counter += 1
            
            # 执行操作
            if rule.operation == ClassificationOperation.MOVE:
                shutil.move(str(media_item.file_path), str(target_path))
                message = f"已移动到: {target_path}"
            elif rule.operation == ClassificationOperation.COPY:
                shutil.copy2(str(media_item.file_path), str(target_path))
                message = f"已复制到: {target_path}"
            elif rule.operation == ClassificationOperation.LINK:
                # 创建符号链接
                target_path.symlink_to(media_item.file_path)
                message = f"已创建链接到: {target_path}"
            else:
                return False, f"不支持的操作: {rule.operation.value}"
            
            return True, message
        except Exception as e:
            error_msg = f"处理文件失败: {media_item.file_path}, 错误: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _build_target_path(self, media_item: MediaItem, rule: ClassificationRule) -> Path:
        """构建目标路径
        
        Args:
            media_item: 媒体项对象
            rule: 适用的分类规则
            
        Returns:
            目标路径
        """
        # 构建目录结构
        dir_parts = []
        
        for part in rule.structure:
            if rule.method == ClassificationMethod.DATE:
                # 按日期分类
                year = media_item.get_year()
                month = media_item.get_month()
                day = media_item.get_day()
                
                if part == "year" and year is not None:
                    dir_parts.append(f"{year:04d}")
                elif part == "month" and month is not None:
                    dir_parts.append(f"{month:02d}")
                elif part == "day" and day is not None:
                    dir_parts.append(f"{day:02d}")
                else:
                    # 如果无法获取日期信息，使用"unknown"
                    dir_parts.append("unknown")
            
            elif rule.method == ClassificationMethod.TYPE:
                # 按类型分类
                if part == "type":
                    dir_parts.append(media_item.extension.lower())
                elif part == "category":
                    # 根据扩展名分类
                    ext = media_item.extension.lower()
                    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]:
                        dir_parts.append("images")
                    elif ext in [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"]:
                        dir_parts.append("videos")
                    elif ext in [".mp3", ".wav", ".flac", ".aac", ".ogg"]:
                        dir_parts.append("audio")
                    else:
                        dir_parts.append("other")
                else:
                    dir_parts.append(part)
            
            elif rule.method == ClassificationMethod.SIZE:
                # 按大小分类
                size_mb = media_item.size / (1024 * 1024)
                if part == "size":
                    if size_mb < 1:
                        dir_parts.append("small")
                    elif size_mb < 10:
                        dir_parts.append("medium")
                    else:
                        dir_parts.append("large")
                else:
                    dir_parts.append(part)
            
            elif rule.method == ClassificationMethod.TAG:
                # 按标签分类
                if part == "tag" and media_item.tags:
                    # 使用第一个标签
                    dir_parts.append(media_item.tags[0])
                else:
                    dir_parts.append("untagged")
            
            elif rule.method == ClassificationMethod.CUSTOM:
                # 自定义分类
                if part in rule.conditions:
                    dir_parts.append(str(rule.conditions[part]))
                else:
                    dir_parts.append(part)
            
            else:
                dir_parts.append(part)
        
        # 构建目标目录
        target_dir = self.target_directory
        for part in dir_parts:
            target_dir = target_dir / part
        
        # 构建目标文件路径
        target_path = target_dir / media_item.filename
        
        return target_path
    
    def is_running(self) -> bool:
        """检查线程是否正在运行
        
        Returns:
            如果线程正在运行则返回True，否则返回False
        """
        return self._is_running


class ClassificationController(QObject, LoggerMixin):
    """分类控制器类
    
    负责协调媒体文件的分类操作。
    """
    
    # 信号定义
    classification_started = pyqtSignal()  # 分类开始信号
    classification_completed = pyqtSignal(bool)  # 分类完成信号
    progress_updated = pyqtSignal(int, int, str)  # 进度更新信号
    file_processed = pyqtSignal(str, bool, str)  # 文件处理信号
    error_occurred = pyqtSignal(str)  # 错误信号
    rule_applied = pyqtSignal(str, str, int)  # 规则应用信号
    rules_loaded = pyqtSignal()  # 规则加载完成信号
    
    def __init__(self, parent=None):
        """初始化分类控制器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 初始化配置
        self.config = Config()
        
        # 初始化变量
        self.current_thread = None
        self.rules: List[ClassificationRule] = []
        
        # 加载规则
        self.load_rules()
        
        # 记录日志
        self.logger.info("分类控制器初始化完成")
    
    def load_rules(self) -> bool:
        """加载分类规则
        
        Returns:
            是否成功加载
        """
        try:
            # 从配置中加载规则
            rules_data = self.config.get("classification", "rules", [])
            
            # 如果配置中没有规则，使用默认规则
            if not rules_data:
                self._create_default_rules()
            else:
                # 从数据创建规则
                self.rules = [ClassificationRule.from_dict(rule_data) for rule_data in rules_data]
            
            # 发送规则加载完成信号
            self.rules_loaded.emit()
            
            self.logger.info(f"已加载 {len(self.rules)} 个分类规则")
            return True
        except Exception as e:
            self.logger.error(f"加载分类规则失败: {e}")
            self._create_default_rules()
            return False
    
    def save_rules(self) -> bool:
        """保存分类规则
        
        Returns:
            是否成功保存
        """
        try:
            # 将规则转换为字典
            rules_data = [rule.to_dict() for rule in self.rules]
            
            # 保存到配置
            self.config.set("classification", "rules", rules_data)
            self.config.save()
            
            self.logger.info(f"已保存 {len(self.rules)} 个分类规则")
            return True
        except Exception as e:
            self.logger.error(f"保存分类规则失败: {e}")
            return False
    
    def _create_default_rules(self):
        """创建默认分类规则"""
        self.rules = [
            ClassificationRule(
                name="按年月分类",
                method=ClassificationMethod.DATE,
                structure=["year", "month"],
                operation=ClassificationOperation.MOVE
            ),
            ClassificationRule(
                name="按类型分类",
                method=ClassificationMethod.TYPE,
                structure=["category"],
                operation=ClassificationOperation.COPY,
                conditions={"file_types": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
                                      ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
                                      ".mp3", ".wav", ".flac", ".aac", ".ogg"]}
            ),
            ClassificationRule(
                name="按大小分类",
                method=ClassificationMethod.SIZE,
                structure=["size"],
                operation=ClassificationOperation.COPY
            )
        ]
        
        # 保存默认规则
        self.save_rules()
    
    def add_rule(self, rule: ClassificationRule) -> bool:
        """添加分类规则
        
        Args:
            rule: 要添加的规则
            
        Returns:
            是否成功添加
        """
        try:
            # 检查规则名称是否已存在
            if any(r.name == rule.name for r in self.rules):
                self.logger.error(f"规则名称已存在: {rule.name}")
                return False
            
            # 添加规则
            self.rules.append(rule)
            
            # 保存规则
            self.save_rules()
            
            self.logger.info(f"已添加分类规则: {rule.name}")
            return True
        except Exception as e:
            self.logger.error(f"添加分类规则失败: {e}")
            return False
    
    def update_rule(self, index: int, rule: ClassificationRule) -> bool:
        """更新分类规则
        
        Args:
            index: 规则索引
            rule: 更新后的规则
            
        Returns:
            是否成功更新
        """
        try:
            if index < 0 or index >= len(self.rules):
                self.logger.error(f"规则索引无效: {index}")
                return False
            
            # 检查规则名称是否与其他规则冲突
            if any(r.name == rule.name and i != index for i, r in enumerate(self.rules)):
                self.logger.error(f"规则名称已存在: {rule.name}")
                return False
            
            # 更新规则
            self.rules[index] = rule
            
            # 保存规则
            self.save_rules()
            
            self.logger.info(f"已更新分类规则: {rule.name}")
            return True
        except Exception as e:
            self.logger.error(f"更新分类规则失败: {e}")
            return False
    
    def remove_rule(self, index: int) -> bool:
        """移除分类规则
        
        Args:
            index: 规则索引
            
        Returns:
            是否成功移除
        """
        try:
            if index < 0 or index >= len(self.rules):
                self.logger.error(f"规则索引无效: {index}")
                return False
            
            # 移除规则
            rule = self.rules.pop(index)
            
            # 保存规则
            self.save_rules()
            
            self.logger.info(f"已移除分类规则: {rule.name}")
            return True
        except Exception as e:
            self.logger.error(f"移除分类规则失败: {e}")
            return False
    
    def get_rule(self, index: int) -> Optional[ClassificationRule]:
        """获取分类规则
        
        Args:
            index: 规则索引
            
        Returns:
            分类规则对象，如果索引无效则返回None
        """
        if index < 0 or index >= len(self.rules):
            return None
        return self.rules[index]
    
    def get_rules(self) -> List[ClassificationRule]:
        """获取所有分类规则
        
        Returns:
            分类规则列表
        """
        return self.rules.copy()
    
    def enable_rule(self, index: int, enabled: bool) -> bool:
        """启用或禁用分类规则
        
        Args:
            index: 规则索引
            enabled: 是否启用
            
        Returns:
            是否成功
        """
        try:
            if index < 0 or index >= len(self.rules):
                self.logger.error(f"规则索引无效: {index}")
                return False
            
            # 更新规则状态
            self.rules[index].enabled = enabled
            
            # 保存规则
            self.save_rules()
            
            self.logger.info(f"已{'启用' if enabled else '禁用'}分类规则: {self.rules[index].name}")
            return True
        except Exception as e:
            self.logger.error(f"{'启用' if enabled else '禁用'}分类规则失败: {e}")
            return False
    
    def classify_media(self, media_items: List[MediaItem], target_directory: Path, 
                      separator: str = None) -> bool:
        """分类媒体文件
        
        Args:
            media_items: 要分类的媒体项列表
            target_directory: 目标目录
            separator: 文件名分隔符，如果为None则使用默认值
            
        Returns:
            是否成功启动分类
        """
        # 如果已有线程在运行，先停止它
        if self.current_thread and self.current_thread.is_running():
            self.current_thread.stop()
            self.current_thread.wait()
        
        # 获取默认值
        if separator is None:
            separator = self.config.get("classification", "separator", "_")
        
        # 过滤启用的规则
        enabled_rules = [rule for rule in self.rules if rule.enabled]
        
        if not enabled_rules:
            self.logger.error("没有启用的分类规则")
            return False
        
        # 创建并启动分类线程
        self.current_thread = ClassificationThread(
            media_items, target_directory, enabled_rules, separator
        )
        
        # 连接信号
        self.current_thread.signals.progress_updated.connect(self._on_progress_updated)
        self.current_thread.signals.file_processed.connect(self._on_file_processed)
        self.current_thread.signals.finished.connect(self._on_classification_finished)
        self.current_thread.signals.error_occurred.connect(self._on_error_occurred)
        self.current_thread.signals.rule_applied.connect(self._on_rule_applied)
        
        # 发射分类开始信号
        self.classification_started.emit()
        
        # 启动线程
        self.current_thread.start()
        
        # 记录日志
        self.logger.info(f"开始分类 {len(media_items)} 个媒体文件到目录: {target_directory}")
        
        return True
    
    def _on_progress_updated(self, value: int, maximum: int, message: str):
        """进度更新处理
        
        Args:
            value: 当前进度值
            maximum: 最大进度值
            message: 进度消息
        """
        # 转发进度更新信号
        self.progress_updated.emit(value, maximum, message)
    
    def _on_file_processed(self, file_path: str, success: bool, message: str):
        """文件处理完成处理
        
        Args:
            file_path: 文件路径
            success: 是否成功
            message: 消息
        """
        # 转发文件处理信号
        self.file_processed.emit(file_path, success, message)
    
    def _on_classification_finished(self, success: bool):
        """分类完成处理
        
        Args:
            success: 分类是否成功
        """
        # 清理线程引用
        self.current_thread = None
        
        # 转发分类完成信号
        self.classification_completed.emit(success)
        
        # 记录日志
        self.logger.info(f"媒体文件分类完成，成功: {success}")
    
    def _on_error_occurred(self, error_message: str):
        """错误处理
        
        Args:
            error_message: 错误消息
        """
        # 记录错误日志
        self.logger.error(f"分类错误: {error_message}")
        
        # 转发错误信号
        self.error_occurred.emit(error_message)
    
    def stop_classification(self):
        """停止分类操作"""
        if self.current_thread and self.current_thread.is_running():
            self.current_thread.stop()
            self.logger.info("已请求停止分类操作")
    
    def is_classifying(self) -> bool:
        """检查是否正在分类
        
        Returns:
            如果正在分类则返回True，否则返回False
        """
        return self.current_thread is not None and self.current_thread.is_running()
    
    def _on_rule_applied(self, rule_name: str, file_path: str, count: int):
        """规则应用处理
        
        Args:
            rule_name: 规则名称
            file_path: 文件路径
            count: 处理数量
        """
        # 转发规则应用信号
        self.rule_applied.emit(rule_name, file_path, count)
    
    def get_rule_statistics(self) -> Dict[str, Dict[str, int]]:
        """获取规则统计信息
        
        Returns:
            规则统计信息字典
        """
        if self.current_thread and hasattr(self.current_thread, 'rule_stats'):
            return self.current_thread.rule_stats
        
        # 返回空统计
        return {rule.name: {"processed": 0, "success": 0, "error": 0} for rule in self.rules}
    
    def preview_classification(self, media_items: List[MediaItem]) -> Dict[str, List[str]]:
        """预览分类结果
        
        Args:
            media_items: 要预览的媒体项列表
            
        Returns:
            预览结果字典，键为规则名称，值为文件路径列表
        """
        preview = {rule.name: [] for rule in self.rules if rule.enabled}
        
        for media_item in media_items:
            # 查找匹配的规则
            for rule in self.rules:
                if rule.enabled and rule.matches(media_item):
                    preview[rule.name].append(str(media_item.file_path))
                    break  # 只使用第一个匹配的规则
        
        return preview
    
    def export_rules(self, file_path: Path) -> bool:
        """导出规则到文件
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            是否成功导出
        """
        try:
            # 将规则转换为字典
            rules_data = [rule.to_dict() for rule in self.rules]
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"已导出 {len(self.rules)} 个分类规则到: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"导出分类规则失败: {e}")
            return False
    
    def import_rules(self, file_path: Path, replace: bool = False) -> bool:
        """从文件导入规则
        
        Args:
            file_path: 导入文件路径
            replace: 是否替换现有规则
            
        Returns:
            是否成功导入
        """
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            # 转换为规则对象
            imported_rules = [ClassificationRule.from_dict(rule_data) for rule_data in rules_data]
            
            if replace:
                # 替换现有规则
                self.rules = imported_rules
            else:
                # 添加到现有规则
                for rule in imported_rules:
                    # 检查规则名称是否已存在
                    if any(r.name == rule.name for r in self.rules):
                        # 添加序号
                        counter = 1
                        while any(r.name == f"{rule.name}_{counter}" for r in self.rules):
                            counter += 1
                        rule.name = f"{rule.name}_{counter}"
                    
                    self.rules.append(rule)
            
            # 保存规则
            self.save_rules()
            
            # 发送规则加载完成信号
            self.rules_loaded.emit()
            
            self.logger.info(f"已导入 {len(imported_rules)} 个分类规则从: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"导入分类规则失败: {e}")
            return False