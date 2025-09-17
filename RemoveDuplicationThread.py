"""
重复图片删除线程模块

该模块提供了用于图像哈希计算和相似度对比的线程类，主要用于重复图片删除功能：
- ImageHasher: 静态类，提供图像哈希计算和汉明距离计算功能
- HashWorker: 多线程计算图像哈希值
- ContrastWorker: 对比图像哈希值，找出相似图像组
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pillow_heif
from PIL import Image
from PyQt6 import QtCore
from PyQt6.QtCore import QThread, pyqtSignal


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




class ContrastWorker(QThread):
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(list)
    finished_signal = pyqtSignal()
    log_signal = pyqtSignal(str, str)

    def __init__(self, hash_dict, similarity_threshold, parent=None):
        super().__init__(parent)
        self.hash_dict = hash_dict
        self.similarity_threshold = similarity_threshold
        self._is_running = True

    def log(self, level, message):
        self.log_signal.emit(level, message)

    def run(self):
        try:
            self._is_running = True
            image_paths = list(self.hash_dict.keys())
            
            if not image_paths:
                self.log("WARNING", "没有可对比的图片哈希数据")
                self.result_signal.emit([])
                return
                
            total_comparisons = len(image_paths) * (len(image_paths) - 1) // 2
            self.log("INFO", f"开始对比 {len(image_paths)} 张图片的相似度，共需进行 {total_comparisons} 次对比")
            
            # 使用优化的分组算法
            similar_groups = self._optimized_grouping(image_paths)
            
            if self._is_running:
                self.log("INFO", f"相似度对比完成，发现 {len(similar_groups)} 组相似图片")
                self.result_signal.emit(similar_groups)
                self.finished_signal.emit()
            else:
                self.log("WARNING", "相似度对比操作已被用户取消")
                
        except Exception as e:
            self.log("ERROR", f"相似度对比过程中发生严重错误: {str(e)}")
            self.finished_signal.emit()
    
    def _optimized_grouping(self, image_paths):
        """优化的相似图片分组算法"""
        similar_groups = []
        processed = 0
        total = len(image_paths)
        
        # 第一遍：快速预分组（基于哈希值的前几位）
        hash_groups = {}
        for i, path in enumerate(image_paths):
            if not self._is_running:
                break
                
            hash_bits = self.hash_dict[path]
            # 使用前16位作为分组键（可根据需要调整）
            group_key = tuple(hash_bits[:16])
            if group_key not in hash_groups:
                hash_groups[group_key] = []
            hash_groups[group_key].append(path)
            
            processed += 1
            self.progress_signal.emit(int(processed / total * 50))
        
        # 第二遍：在预分组内进行精确对比
        final_groups = []
        processed_groups = 0
        total_groups = len(hash_groups)
        
        for group_paths in hash_groups.values():
            if not self._is_running:
                break
                
            if len(group_paths) == 1:
                # 单张图片，无需进一步处理
                continue
                
            # 在当前预分组内进行精确对比
            current_group = []
            for i in range(len(group_paths)):
                if not self._is_running:
                    break
                    
                path1 = group_paths[i]
                hash1 = self.hash_dict[path1]
                
                # 检查是否与当前组中的任何图片相似
                similar_in_group = False
                for j in range(len(current_group)):
                    path2 = current_group[j]
                    hash2 = self.hash_dict[path2]
                    
                    try:
                        distance = ImageHasher.hamming_distance(hash1, hash2)
                        if distance <= self.similarity_threshold:
                            similar_in_group = True
                            break
                    except Exception:
                        continue
                
                if similar_in_group or not current_group:
                    current_group.append(path1)
                else:
                    # 创建新组
                    final_groups.append(current_group)
                    current_group = [path1]
            
            if current_group and len(current_group) > 1:
                final_groups.append(current_group)
            
            processed_groups += 1
            self.progress_signal.emit(50 + int(processed_groups / total_groups * 50))
        
        return final_groups

    def stop(self):
        """停止相似度对比"""
        self._is_running = False
        self.log("INFO", "正在停止相似度对比操作...")