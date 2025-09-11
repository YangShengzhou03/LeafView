"""图像去重线程模块

这个模块定义了LeafView应用程序中用于图像去重的后台线程。
"""

import os
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from ..models.media_item import MediaItem
from ..models.duplicate_result import DuplicateResult, DuplicateGroup
from ..utils.logger import LoggerMixin

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageFilter
    import imagehash
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class DuplicateFinderSignals(QObject):
    """图像去重线程信号类
    
    定义了图像去重线程使用的信号。
    """
    
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


class DuplicateFinderThread(QThread, LoggerMixin):
    """图像去重线程类
    
    用于在后台处理图像文件，查找相似或重复的图像。
    """
    
    def __init__(self, media_items: List[MediaItem], similarity_threshold: float = 0.9, parent=None):
        """初始化图像去重线程
        
        Args:
            media_items: 要检查的媒体项列表
            similarity_threshold: 相似度阈值，0-1之间，1表示完全相同
            parent: 父对象
        """
        super().__init__(parent)
        
        # 创建信号对象
        self.signals = DuplicateFinderSignals()
        
        # 初始化变量
        self._is_running = False
        self._should_stop = False
        
        # 设置参数
        self.media_items = media_items
        self.similarity_threshold = similarity_threshold
        
        # 存储结果
        self.result = DuplicateResult()
        self.result.similarity_threshold = similarity_threshold
        
        # 支持的文件扩展名
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        
        # 缓存哈希值
        self._hash_cache = {}
        
        # 缓存图像特征
        self._feature_cache = {}
        
        # 可用的相似度计算方法
        self.available_methods = []
        if CV2_AVAILABLE:
            self.available_methods.append("cv2")
        if PIL_AVAILABLE:
            self.available_methods.append("pil")
        
        # 默认使用PIL方法，如果可用
        self.method = "pil" if "pil" in self.available_methods else "cv2" if "cv2" in self.available_methods else "basic"
    
    def stop(self):
        """停止线程执行"""
        self._should_stop = True
        # 等待最多1秒让线程自然结束
        if self.isRunning():
            self.wait(1000)
        self.logger.info("图像去重线程已请求停止")
    
    def run(self):
        """线程主运行方法"""
        self._is_running = True
        self._should_stop = False
        
        try:
            success = self._find_duplicates()
            self.signals.duplicates_found.emit(self.result)
            self.signals.finished.emit(success)
        except Exception as e:
            self.logger.error(f"图像去重线程发生错误: {e}")
            self.signals.error_occurred.emit(str(e))
            self.signals.finished.emit(False)
        finally:
            self._is_running = False
            self.logger.info("图像去重线程已结束")
    
    def _find_duplicates(self) -> bool:
        """查找重复图像
        
        Returns:
            查找是否成功
        """
        total_items = len(self.media_items)
        
        if total_items == 0:
            self.signals.progress_updated.emit(100, 100, "没有文件需要检查")
            return True
        
        # 过滤出图像文件
        image_items = [item for item in self.media_items if self._is_image_file(item.file_path)]
        
        if len(image_items) == 0:
            self.signals.progress_updated.emit(100, 100, "没有图像文件需要检查")
            return True
        
        # 首先检查完全相同的文件（通过文件大小和哈希值）
        self.signals.progress_updated.emit(0, 100, "正在检查完全相同的文件...")
        exact_duplicates = self._find_exact_duplicates(image_items)
        
        if self._should_stop:
            return False
        
        # 然后检查相似文件（通过图像内容）
        self.signals.progress_updated.emit(30, 100, "正在检查相似文件...")
        similar_duplicates = self._find_similar_duplicates(image_items)
        
        if self._should_stop:
            return False
        
        # 更新最终进度
        self.signals.progress_updated.emit(100, 100, 
            f"检查完成: 发现 {self.result.total_groups} 组重复文件")
        
        return True
    
    def _find_exact_duplicates(self, image_items: List[MediaItem]) -> bool:
        """查找完全相同的文件
        
        Args:
            image_items: 图像项列表
            
        Returns:
            查找是否成功
        """
        # 按文件大小分组
        size_groups = {}
        for item in image_items:
            if self._should_stop:
                return False
                
            size = item.file_size
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(item)
        
        # 只处理有多个文件的组
        processed = 0
        total_groups = len([g for g in size_groups.values() if len(g) > 1])
        
        for size, items in size_groups.items():
            if len(items) < 2:
                continue
            
            if self._should_stop:
                return False
            
            # 更新进度
            processed += 1
            progress = int(30 * processed / total_groups)
            self.signals.progress_updated.emit(progress, 100, 
                f"正在检查完全相同的文件 {processed}/{total_groups}...")
            
            # 计算每个文件的哈希值
            hash_items = []
            for item in items:
                if self._should_stop:
                    return False
                
                file_hash = item.get_hash()
                hash_items.append((file_hash, item))
                self._hash_cache[item.file_path] = file_hash
            
            # 按哈希值分组
            hash_groups = {}
            for file_hash, item in hash_items:
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(item)
            
            # 只处理有多个文件的组
            for file_hash, items in hash_groups.items():
                if len(items) < 2:
                    continue
                
                # 创建重复组
                group = DuplicateGroup(id=f"exact_{file_hash}")
                
                # 添加所有项到组中
                for item in items:
                    group.add_item(item)
                
                # 设置所有项之间的相似度为1.0（完全相同）
                for i in range(len(items)):
                    for j in range(i + 1, len(items)):
                        group.set_similarity(i, j, 1.0)
                        self.signals.duplicate_found.emit(items[i], items[j], 1.0)
                
                # 添加到结果中
                self.result.add_group(group)
        
        return True
    
    def _find_similar_duplicates(self, image_items: List[MediaItem]) -> bool:
        """查找相似的文件
        
        Args:
            image_items: 图像项列表
            
        Returns:
            查找是否成功
        """
        total_items = len(image_items)
        processed = 0
        
        # 简单实现：比较每个图像与其他所有图像
        for i in range(total_items):
            if self._should_stop:
                return False
            
            item1 = image_items[i]
            
            # 更新进度
            processed += 1
            progress = int(30 + 70 * processed / total_items)
            self.signals.progress_updated.emit(progress, 100, 
                f"正在检查相似文件 {processed}/{total_items}...")
            
            for j in range(i + 1, total_items):
                if self._should_stop:
                    return False
                
                item2 = image_items[j]
                
                # 跳过已经确定为完全相同的文件
                if (item1.file_path in self._hash_cache and 
                    item2.file_path in self._hash_cache and
                    self._hash_cache[item1.file_path] == self._hash_cache[item2.file_path]):
                    continue
                
                # 计算相似度
                similarity = self._calculate_similarity(item1, item2)
                
                # 如果相似度超过阈值，则认为是重复的
                if similarity >= self.similarity_threshold:
                    # 检查是否已经存在包含这两个项的组
                    found_group = None
                    for group in self.result.groups:
                        if item1 in group.items and item2 in group.items:
                            found_group = group
                            break
                    
                    if found_group:
                        # 更新现有组的相似度
                        idx1 = found_group.items.index(item1)
                        idx2 = found_group.items.index(item2)
                        found_group.set_similarity(idx1, idx2, similarity)
                    else:
                        # 创建新组
                        group_id = f"similar_{hash(item1.file_path)}_{hash(item2.file_path)}"
                        group = DuplicateGroup(id=group_id)
                        group.add_item(item1)
                        group.add_item(item2)
                        group.set_similarity(0, 1, similarity)
                        self.result.add_group(group)
                    
                    self.signals.duplicate_found.emit(item1, item2, similarity)
        
        return True
    
    def _calculate_similarity(self, item1: MediaItem, item2: MediaItem) -> float:
        """计算两个图像的相似度
        
        Args:
            item1: 第一个媒体项
            item2: 第二个媒体项
            
        Returns:
            相似度，0-1之间，1表示完全相同
        """
        # 如果文件大小相同且哈希值相同，则认为是完全相同的
        if (item1.file_path in self._hash_cache and 
            item2.file_path in self._hash_cache and
            self._hash_cache[item1.file_path] == self._hash_cache[item2.file_path]):
            return 1.0
        
        # 根据可用方法计算相似度
        if self.method == "cv2" and CV2_AVAILABLE:
            return self._calculate_similarity_cv2(item1, item2)
        elif self.method == "pil" and PIL_AVAILABLE:
            return self._calculate_similarity_pil(item1, item2)
        else:
            # 基本方法：基于文件大小和扩展名
            return self._calculate_similarity_basic(item1, item2)
    
    def _calculate_similarity_basic(self, item1: MediaItem, item2: MediaItem) -> float:
        """使用基本方法计算两个图像的相似度
        
        Args:
            item1: 第一个媒体项
            item2: 第二个媒体项
            
        Returns:
            相似度，0-1之间，1表示完全相同
        """
        # 计算文件大小的相似度
        if item1.file_size == 0 or item2.file_size == 0:
            size_similarity = 0.0
        else:
            size_similarity = min(item1.file_size, item2.file_size) / max(item1.file_size, item2.file_size)
        
        # 计算文件名的相似度（基于扩展名）
        ext_similarity = 1.0 if item1.file_path.suffix.lower() == item2.file_path.suffix.lower() else 0.0
        
        # 综合相似度（权重：文件大小70%，扩展名30%）
        similarity = 0.7 * size_similarity + 0.3 * ext_similarity
        
        return similarity
    
    def _calculate_similarity_pil(self, item1: MediaItem, item2: MediaItem) -> float:
        """使用PIL计算两个图像的相似度
        
        Args:
            item1: 第一个媒体项
            item2: 第二个媒体项
            
        Returns:
            相似度，0-1之间，1表示完全相同
        """
        try:
            # 检查缓存
            cache_key1 = str(item1.file_path)
            cache_key2 = str(item2.file_path)
            
            if cache_key1 in self._feature_cache and cache_key2 in self._feature_cache:
                hash1 = self._feature_cache[cache_key1]
                hash2 = self._feature_cache[cache_key2]
            else:
                # 计算感知哈希
                with Image.open(item1.file_path) as img1:
                    # 转换为RGB模式（如果是RGBA或其他模式）
                    if img1.mode != 'RGB':
                        img1 = img1.convert('RGB')
                    # 调整大小以加快计算速度
                    img1 = img1.resize((32, 32), Image.Resampling.LANCZOS)
                    hash1 = imagehash.average_hash(img1)
                    self._feature_cache[cache_key1] = hash1
                
                with Image.open(item2.file_path) as img2:
                    # 转换为RGB模式（如果是RGBA或其他模式）
                    if img2.mode != 'RGB':
                        img2 = img2.convert('RGB')
                    # 调整大小以加快计算速度
                    img2 = img2.resize((32, 32), Image.Resampling.LANCZOS)
                    hash2 = imagehash.average_hash(img2)
                    self._feature_cache[cache_key2] = hash2
            
            # 计算哈希距离（0-64）
            hash_distance = hash1 - hash2
            
            # 将哈希距离转换为相似度（0-1）
            similarity = 1.0 - (hash_distance / 64.0)
            
            return similarity
        except Exception as e:
            self.logger.warning(f"使用PIL计算相似度失败: {e}")
            # 回退到基本方法
            return self._calculate_similarity_basic(item1, item2)
    
    def _calculate_similarity_cv2(self, item1: MediaItem, item2: MediaItem) -> float:
        """使用OpenCV计算两个图像的相似度
        
        Args:
            item1: 第一个媒体项
            item2: 第二个媒体项
            
        Returns:
            相似度，0-1之间，1表示相同
        """
        try:
            # 检查缓存
            cache_key1 = str(item1.file_path)
            cache_key2 = str(item2.file_path)
            
            if cache_key1 in self._feature_cache and cache_key2 in self._feature_cache:
                desc1 = self._feature_cache[cache_key1]
                desc2 = self._feature_cache[cache_key2]
            else:
                # 读取图像
                img1 = cv2.imread(str(item1.file_path))
                img2 = cv2.imread(str(item2.file_path))
                
                if img1 is None or img2 is None:
                    return 0.0
                
                # 调整大小以加快计算速度
                height, width = 256, 256
                img1 = cv2.resize(img1, (width, height))
                img2 = cv2.resize(img2, (width, height))
                
                # 转换为灰度图
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
                
                # 计算ORB特征描述符
                orb = cv2.ORB_create()
                kp1, desc1 = orb.detectAndCompute(gray1, None)
                kp2, desc2 = orb.detectAndCompute(gray2, None)
                
                if desc1 is None or desc2 is None:
                    # 如果无法提取特征，使用结构相似性
                    score = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)[0][0]
                    similarity = max(0.0, min(1.0, score))
                    return similarity
                
                # 缓存特征描述符
                self._feature_cache[cache_key1] = desc1
                self._feature_cache[cache_key2] = desc2
            
            # 创建BFMatcher对象
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            
            # 匹配描述符
            matches = bf.match(desc1, desc2)
            
            # 计算匹配分数
            if len(matches) == 0:
                return 0.0
            
            # 计算平均匹配距离
            avg_distance = sum(m.distance for m in matches) / len(matches)
            
            # 将距离转换为相似度（ORB的距离范围是0-256）
            similarity = 1.0 - (avg_distance / 256.0)
            
            return similarity
        except Exception as e:
            self.logger.warning(f"使用OpenCV计算相似度失败: {e}")
            # 回退到基本方法
            return self._calculate_similarity_basic(item1, item2)
    
    def _is_image_file(self, file_path: Path) -> bool:
        """检查文件是否为图像文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            如果是图像文件则返回True，否则返回False
        """
        # 检查文件扩展名
        ext = file_path.suffix.lower()
        return ext in self.image_extensions
    
    def is_running(self) -> bool:
        """检查线程是否正在运行
        
        Returns:
            如果线程正在运行则返回True，否则返回False
        """
        return self._is_running