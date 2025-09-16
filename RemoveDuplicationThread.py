"""
重复图片删除线程模块

该模块提供了用于图像哈希计算和相似度对比的线程类，主要用于重复图片删除功能：
- ImageHasher: 静态类，提供图像哈希计算和汉明距离计算功能
- HashWorker: 多线程计算图像哈希值
- ContrastWorker: 对比图像哈希值，找出相似图像组
"""

import numpy as np
from PIL import Image
from PyQt6 import QtCore
import pillow_heif
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict


class ImageHasher:
    """图像哈希计算工具类 - 提供感知哈希算法相关功能"""
    
    @staticmethod
    def dhash(image_path, hash_size=8):
        """
        计算图像的差异哈希（dHash）值
        
        Args:
            image_path (str): 图像文件路径
            hash_size (int): 哈希尺寸，默认为8（生成64位哈希）
            
        Returns:
            np.ndarray: 哈希位数组，失败时返回None
        """
        try:
            ext = image_path.lower().split('.')[-1]
            # 特殊处理HEIC/HEIF格式
            if ext in ('heic', 'heif'):
                heif_file = pillow_heif.read_heif(image_path)
                img = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                    heif_file.mode,
                    heif_file.stride,
                )
            else:
                with Image.open(image_path) as img:
                    img.load()

            w, h = img.size
            # 过滤过小或宽高比异常的图片
            if w < 50 or h < 50:
                return None
            if (w / h) < 0.2 or (w / h) > 5:
                return None

            # 转换为灰度图并缩放到指定尺寸
            image = img.convert('L').resize(
                (hash_size + 1, hash_size),
                Image.Resampling.BILINEAR
            )

            # 计算相邻像素差异并生成哈希位
            pixels = np.array(image, dtype=np.int16)
            diff = pixels[:, 1:] > pixels[:, :-1]
            return diff.flatten()

        except Exception:
            return None

    @staticmethod
    def hamming_distance(bits1, bits2):
        """
        计算两个哈希位数组的汉明距离
        
        Args:
            bits1 (np.ndarray): 第一个哈希位数组
            bits2 (np.ndarray): 第二个哈希位数组
            
        Returns:
            int: 汉明距离（不同位的数量）
        """
        return np.count_nonzero(bits1 != bits2)

    @staticmethod
    def hash_to_int(hash_bits, num_bits=8):
        """将哈希位数组转换为整数（取前num_bits位）"""
        return int(''.join(['1' if bit else '0' for bit in hash_bits[:num_bits]]), 2)


class HashWorker(QtCore.QThread):
    """哈希计算工作线程 - 多线程计算图像哈希值"""
    
    hash_completed = QtCore.pyqtSignal(dict)  # 哈希计算完成信号
    progress_updated = QtCore.pyqtSignal(int)  # 进度更新信号
    error_occurred = QtCore.pyqtSignal(str)    # 错误发生信号

    def __init__(self, image_paths, hash_size=8, max_workers=4):
        """
        初始化哈希计算工作线程
        
        Args:
            image_paths (list): 图像路径列表
            hash_size (int): 哈希尺寸
            max_workers (int): 最大工作线程数
        """
        super().__init__()
        self.image_paths = image_paths
        self.hash_size = hash_size
        self.max_workers = max_workers
        self._is_running = True  # 线程运行状态标志

    def run(self):
        """线程主执行方法 - 多线程计算图像哈希"""
        try:
            hashes = {}
            # 支持的图片格式集合
            supported_extensions = (
                '.jpg', '.jpeg', '.png', '.bmp', '.gif',
                '.heic', '.heif', '.webp', '.tif', '.tiff'
            )

            # 过滤支持的图片格式
            filtered_paths = [
                path for path in self.image_paths
                if path.lower().endswith(supported_extensions)
            ]
            total = len(filtered_paths)

            # 使用线程池并行计算哈希
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_path = {
                    executor.submit(ImageHasher.dhash, path, self.hash_size): path
                    for path in filtered_paths
                }

                for i, future in enumerate(as_completed(future_to_path)):
                    if not self._is_running:
                        return

                    path = future_to_path[future]
                    result = future.result()
                    if result is not None:
                        hashes[path] = result

                    # 减少进度更新频率，每10张图片或最后一张时更新
                    if (i + 1) % 10 == 0 or (i + 1) == total:
                        self.progress_updated.emit(int((i + 1) / total * 40))

            if self._is_running:
                self.hash_completed.emit(hashes)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        """停止线程执行"""
        self._is_running = False


class ContrastWorker(QtCore.QThread):
    """相似度对比工作线程 - 对比图像哈希值找出相似图像"""
    
    groups_completed = QtCore.pyqtSignal(dict)  # 分组完成信号
    progress_updated = QtCore.pyqtSignal(int)    # 进度更新信号
    image_matched = QtCore.pyqtSignal(str, str)  # 图片匹配信号

    def __init__(self, image_hashes, threshold):
        """
        初始化相似度对比工作线程
        
        Args:
            image_hashes (dict): 图像哈希字典 {路径: 哈希值}
            threshold (int): 相似度阈值（汉明距离）
        """
        super().__init__()
        self.image_hashes = image_hashes
        self.threshold = threshold
        self._is_running = True  # 线程运行状态标志

    def run(self):
        """线程主执行方法 - 对比图像哈希值进行分组"""
        try:
            if not self.image_hashes:
                self.groups_completed.emit({})
                return

            groups = {}
            remaining_paths = list(self.image_hashes.keys())
            group_id = 0
            total = len(remaining_paths)
            processed = 0

            # 使用更保守的哈希桶预分组（前8位）
            hash_buckets = defaultdict(list)
            for path, hash_bits in self.image_hashes.items():
                if not self._is_running:
                    return
                # 使用前8位进行预分组，减少误分组
                bucket_key = ImageHasher.hash_to_int(hash_bits, 8)
                hash_buckets[bucket_key].append(path)

            # 处理每个桶内的图片
            for bucket_paths in hash_buckets.values():
                if not self._is_running:
                    return

                if len(bucket_paths) == 1:
                    # 单个图片直接成组
                    groups[group_id] = bucket_paths
                    group_id += 1
                    processed += 1
                    continue

                # 对桶内图片进行聚类
                bucket_remaining = bucket_paths.copy()
                while bucket_remaining and self._is_running:
                    seed_path = bucket_remaining.pop()
                    groups[group_id] = [seed_path]
                    seed_hash = self.image_hashes[seed_path]

                    to_remove = []
                    for i, path in enumerate(bucket_remaining):
                        if not self._is_running:
                            return

                        distance = ImageHasher.hamming_distance(seed_hash, self.image_hashes[path])
                        if distance <= self.threshold:
                            groups[group_id].append(path)
                            to_remove.append(i)
                            
                            # 发送匹配信号（当组内有两张图片时）
                            if len(groups[group_id]) == 2:
                                self.image_matched.emit(seed_path, path)

                        processed += 1

                    # 更新进度
                    if processed % 50 == 0:
                        progress = min(40 + int((processed / total) * 40), 80)
                        self.progress_updated.emit(progress)

                    # 移除已处理的图片
                    for i in sorted(to_remove, reverse=True):
                        if i < len(bucket_remaining):
                            bucket_remaining.pop(i)

                    group_id += 1

            # 处理跨桶的相似图片（保守策略）
            remaining_singles = {}
            for group_id, paths in list(groups.items()):
                if len(paths) == 1:
                    remaining_singles[paths[0]] = self.image_hashes[paths[0]]
                    del groups[group_id]

            if remaining_singles and self._is_running:
                single_paths = list(remaining_singles.keys())
                single_remaining = single_paths.copy()
                
                while single_remaining and self._is_running:
                    seed_path = single_remaining.pop()
                    seed_hash = remaining_singles[seed_path]
                    
                    to_remove = []
                    for i, path in enumerate(single_remaining):
                        if not self._is_running:
                            return
                        
                        distance = ImageHasher.hamming_distance(seed_hash, remaining_singles[path])
                        if distance <= self.threshold:
                            # 找到新的组
                            groups[group_id] = [seed_path, path]
                            group_id += 1
                            to_remove.append(i)
                            self.image_matched.emit(seed_path, path)
                    
                    for i in sorted(to_remove, reverse=True):
                        if i < len(single_remaining):
                            single_remaining.pop(i)

            if self._is_running:
                self.groups_completed.emit(groups)
                
        except Exception as e:
            print(f"对比过程中出错: {e}")
            # 即使出错也返回空结果，避免UI卡死
            self.groups_completed.emit({})

    def stop(self):
        """停止线程执行"""
        self._is_running = False