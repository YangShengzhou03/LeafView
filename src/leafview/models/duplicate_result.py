"""图像去重结果模型模块

这个模块定义了LeafView应用程序中用于存储和管理图像去重结果的数据模型。
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..models.media_item import MediaItem


class DuplicateAction(Enum):
    """重复文件处理操作枚举"""
    NONE = "none"  # 无操作
    MOVE = "move"  # 移动
    DELETE = "delete"  # 删除
    KEEP = "keep"  # 保留


@dataclass
class DuplicateGroup:
    """重复文件组类
    
    表示一组相似的文件，包含多个媒体项和它们的相似度关系。
    """
    id: str  # 组ID
    items: List[MediaItem] = field(default_factory=list)  # 组中的媒体项
    similarity_matrix: Dict[Tuple[int, int], float] = field(default_factory=dict)  # 相似度矩阵
    actions: Dict[int, DuplicateAction] = field(default_factory=dict)  # 每个项的操作
    selected_item_index: Optional[int] = None  # 用户选择的保留项索引
    
    def add_item(self, item: MediaItem) -> None:
        """添加媒体项到组中
        
        Args:
            item: 媒体项
        """
        if item not in self.items:
            self.items.append(item)
            self.actions[len(self.items) - 1] = DuplicateAction.NONE
    
    def set_similarity(self, index1: int, index2: int, similarity: float) -> None:
        """设置两个媒体项之间的相似度
        
        Args:
            index1: 第一个媒体项的索引
            index2: 第二个媒体项的索引
            similarity: 相似度值
        """
        if 0 <= index1 < len(self.items) and 0 <= index2 < len(self.items):
            self.similarity_matrix[(index1, index2)] = similarity
            self.similarity_matrix[(index2, index1)] = similarity
    
    def get_similarity(self, index1: int, index2: int) -> float:
        """获取两个媒体项之间的相似度
        
        Args:
            index1: 第一个媒体项的索引
            index2: 第二个媒体项的索引
            
        Returns:
            相似度值，如果不存在则返回0
        """
        return self.similarity_matrix.get((index1, index2), 0.0)
    
    def set_action(self, index: int, action: DuplicateAction) -> None:
        """设置媒体项的操作
        
        Args:
            index: 媒体项的索引
            action: 操作类型
        """
        if 0 <= index < len(self.items):
            self.actions[index] = action
            
            # 如果设置为保留，则清除之前的保留项
            if action == DuplicateAction.KEEP:
                for i in range(len(self.items)):
                    if i != index and self.actions[i] == DuplicateAction.KEEP:
                        self.actions[i] = DuplicateAction.NONE
                self.selected_item_index = index
            # 如果清除保留操作，则清除选择
            elif index == self.selected_item_index and action != DuplicateAction.KEEP:
                self.selected_item_index = None
    
    def get_action(self, index: int) -> DuplicateAction:
        """获取媒体项的操作
        
        Args:
            index: 媒体项的索引
            
        Returns:
            操作类型
        """
        return self.actions.get(index, DuplicateAction.NONE)
    
    def auto_select(self) -> None:
        """自动选择最佳保留项
        
        基于文件大小、分辨率和修改日期等因素自动选择最佳保留项。
        """
        if not self.items:
            return
            
        best_index = 0
        best_score = -1
        
        for i, item in enumerate(self.items):
            score = 0
            
            # 文件大小评分（越大越好）
            score += item.file_size / (1024 * 1024)  # 转换为MB
            
            # 修改日期评分（越新越好）
            if item.get_modification_date():
                import time
                mod_time = item.get_modification_date().timestamp()
                score += mod_time / (365 * 24 * 60 * 60)  # 转换为年
            
            # 分辨率评分（越高越好，仅对图像有效）
            if item.media_type == "image":
                try:
                    from PIL import Image
                    with Image.open(item.file_path) as img:
                        width, height = img.size
                        score += (width * height) / (1000 * 1000)  # 转换为兆像素
                except Exception:
                    pass
            
            if score > best_score:
                best_score = score
                best_index = i
        
        # 设置最佳项为保留，其他为删除
        for i in range(len(self.items)):
            if i == best_index:
                self.set_action(i, DuplicateAction.KEEP)
            else:
                self.set_action(i, DuplicateAction.DELETE)
    
    def get_items_to_delete(self) -> List[MediaItem]:
        """获取标记为删除的媒体项
        
        Returns:
            标记为删除的媒体项列表
        """
        return [self.items[i] for i, action in self.actions.items() 
                if action == DuplicateAction.DELETE]
    
    def get_items_to_move(self) -> List[MediaItem]:
        """获取标记为移动的媒体项
        
        Returns:
            标记为移动的媒体项列表
        """
        return [self.items[i] for i, action in self.actions.items() 
                if action == DuplicateAction.MOVE]
    
    def get_kept_item(self) -> Optional[MediaItem]:
        """获取标记为保留的媒体项
        
        Returns:
            标记为保留的媒体项，如果没有则返回None
        """
        if self.selected_item_index is not None:
            return self.items[self.selected_item_index]
        return None


class DuplicateResult:
    """去重结果类
    
    存储和管理所有重复文件组。
    """
    
    def __init__(self):
        """初始化去重结果"""
        self.groups: List[DuplicateGroup] = []
        self.total_groups = 0
        self.total_files = 0
        self.similarity_threshold = 0.9
        
    def add_group(self, group: DuplicateGroup) -> None:
        """添加重复文件组
        
        Args:
            group: 重复文件组
        """
        self.groups.append(group)
        self.total_groups = len(self.groups)
        self.total_files = sum(len(g.items) for g in self.groups)
    
    def get_group(self, index: int) -> Optional[DuplicateGroup]:
        """获取指定索引的重复文件组
        
        Args:
            index: 组索引
            
        Returns:
            重复文件组，如果索引无效则返回None
        """
        if 0 <= index < len(self.groups):
            return self.groups[index]
        return None
    
    def remove_group(self, index: int) -> bool:
        """移除指定索引的重复文件组
        
        Args:
            index: 组索引
            
        Returns:
            移除是否成功
        """
        if 0 <= index < len(self.groups):
            self.groups.pop(index)
            self.total_groups = len(self.groups)
            self.total_files = sum(len(g.items) for g in self.groups)
            return True
        return False
    
    def clear(self) -> None:
        """清空所有重复文件组"""
        self.groups.clear()
        self.total_groups = 0
        self.total_files = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取去重结果统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "total_groups": self.total_groups,
            "total_files": self.total_files,
            "files_to_delete": 0,
            "files_to_move": 0,
            "files_to_keep": 0,
            "files_no_action": 0,
            "space_to_save": 0  # 可节省的磁盘空间（字节）
        }
        
        for group in self.groups:
            kept_item = group.get_kept_item()
            
            for i, item in enumerate(group.items):
                action = group.get_action(i)
                
                if action == DuplicateAction.DELETE:
                    stats["files_to_delete"] += 1
                    if kept_item:
                        stats["space_to_save"] += item.file_size
                elif action == DuplicateAction.MOVE:
                    stats["files_to_move"] += 1
                elif action == DuplicateAction.KEEP:
                    stats["files_to_keep"] += 1
                else:
                    stats["files_no_action"] += 1
        
        return stats
    
    def apply_actions(self, move_destination: Optional[str] = None) -> Dict[str, Any]:
        """应用所有操作
        
        Args:
            move_destination: 移动目标目录，如果为None则使用默认目录
            
        Returns:
            操作结果字典
        """
        result = {
            "success": True,
            "deleted_files": [],
            "moved_files": [],
            "failed_files": [],
            "errors": []
        }
        
        try:
            import os
            import shutil
            from pathlib import Path
            
            # 如果没有指定移动目录，则使用默认目录
            if move_destination is None:
                from ..utils.config import Config
                config = Config()
                move_destination = config.get("last_used", "export_directory", str(Path.home() / "Pictures/Duplicates"))
            
            # 确保移动目录存在
            move_path = Path(move_destination)
            move_path.mkdir(parents=True, exist_ok=True)
            
            # 处理每个组
            for group in self.groups:
                # 处理删除操作
                for item in group.get_items_to_delete():
                    try:
                        os.remove(item.file_path)
                        result["deleted_files"].append(str(item.file_path))
                    except Exception as e:
                        result["failed_files"].append(str(item.file_path))
                        result["errors"].append(f"删除文件 {item.file_path} 失败: {e}")
                        result["success"] = False
                
                # 处理移动操作
                for item in group.get_items_to_move():
                    try:
                        dest_path = move_path / item.filename
                        # 如果目标文件已存在，添加序号
                        counter = 1
                        while dest_path.exists():
                            stem = item.file_path.stem
                            suffix = item.file_path.suffix
                            dest_path = move_path / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                        shutil.move(str(item.file_path), str(dest_path))
                        result["moved_files"].append({"from": str(item.file_path), "to": str(dest_path)})
                    except Exception as e:
                        result["failed_files"].append(str(item.file_path))
                        result["errors"].append(f"移动文件 {item.file_path} 失败: {e}")
                        result["success"] = False
        
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"应用操作失败: {e}")
        
        return result