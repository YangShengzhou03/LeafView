#!/usr/bin/env python3
"""
集成测试 - 验证完整的重复图片删除功能
"""

import os
import tempfile
import shutil
from PIL import Image
import numpy as np
from RemoveDuplicationThread import ImageHasher, HashWorker, ContrastWorker
from PyQt6 import QtCore, QtWidgets
import sys

def create_test_images():
    """创建测试图片文件"""
    temp_dir = tempfile.mkdtemp()
    
    # 创建一些基本图片
    for i in range(10):
        img = Image.new('RGB', (100, 100), color=(i*25, i*25, i*25))
        img.save(os.path.join(temp_dir, f'base_{i}.png'))
    
    # 创建一些重复图片（完全相同）
    for i in range(5):
        shutil.copy(
            os.path.join(temp_dir, f'base_{i}.png'),
            os.path.join(temp_dir, f'duplicate_{i}.png')
        )
    
    # 创建一些相似图片（轻微修改）
    for i in range(5, 8):
        img = Image.open(os.path.join(temp_dir, f'base_{i}.png'))
        pixels = np.array(img)
        # 轻微修改像素
        pixels[10:20, 10:20] = [255, 0, 0]  # 添加红色方块
        modified_img = Image.fromarray(pixels)
        modified_img.save(os.path.join(temp_dir, f'similar_{i}.png'))
    
    return temp_dir, [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)]

def test_hash_worker(image_paths):
    """测试HashWorker"""
    print("测试HashWorker...")
    
    class TestSignal:
        def __init__(self):
            self.hashes = None
            self.progress = 0
            self.error = None
        
        def hash_completed(self, hashes):
            self.hashes = hashes
        
        def progress_updated(self, progress):
            self.progress = progress
        
        def error_occurred(self, error):
            self.error = error
    
    signal = TestSignal()
    
    worker = HashWorker(image_paths)
    worker.hash_completed.connect(signal.hash_completed)
    worker.progress_updated.connect(signal.progress_updated)
    worker.error_occurred.connect(signal.error_occurred)
    
    worker.run()  # 直接调用run方法
    
    print(f"成功计算 {len(signal.hashes)} 个哈希值")
    print(f"进度: {signal.progress}%")
    
    if signal.error:
        print(f"错误: {signal.error}")
    
    return signal.hashes

def test_contrast_worker(hashes, threshold=5):
    """测试ContrastWorker"""
    print("测试ContrastWorker...")
    
    class TestSignal:
        def __init__(self):
            self.groups = None
            self.progress = 0
        
        def groups_completed(self, groups):
            self.groups = groups
        
        def progress_updated(self, progress):
            self.progress = progress
        
        def image_matched(self, path1, path2):
            print(f"匹配: {os.path.basename(path1)} <-> {os.path.basename(path2)}")
    
    signal = TestSignal()
    
    worker = ContrastWorker(hashes, threshold)
    worker.groups_completed.connect(signal.groups_completed)
    worker.progress_updated.connect(signal.progress_updated)
    worker.image_matched.connect(signal.image_matched)
    
    worker.run()  # 直接调用run方法
    
    print(f"找到 {len(signal.groups)} 个图片组")
    print(f"进度: {signal.progress}%")
    
    # 显示重复组
    duplicate_groups = []
    for group_id, paths in signal.groups.items():
        if len(paths) > 1:
            duplicate_groups.append((group_id, paths))
    
    print(f"发现 {len(duplicate_groups)} 个重复组:")
    for group_id, paths in duplicate_groups:
        print(f"  组 {group_id}: {[os.path.basename(p) for p in paths]}")
    
    return signal.groups

def main():
    print("=== 集成测试 - 重复图片删除功能 ===")
    
    # 创建测试环境
    app = QtWidgets.QApplication(sys.argv)
    
    # 创建测试图片
    print("创建测试图片...")
    temp_dir, image_paths = create_test_images()
    print(f"创建了 {len(image_paths)} 个测试图片")
    print(f"图片文件: {[os.path.basename(p) for p in image_paths]}")
    
    try:
        # 测试哈希计算
        print("\n" + "="*50)
        hashes = test_hash_worker(image_paths)
        
        # 测试对比
        print("\n" + "="*50)
        groups = test_contrast_worker(hashes)
        
        # 验证结果
        print("\n" + "="*50)
        print("验证结果...")
        
        # 检查是否找到了预期的重复组
        expected_duplicates = 5  # 5个完全重复的图片
        duplicate_count = sum(1 for group in groups.values() if len(group) > 1)
        
        if duplicate_count >= expected_duplicates:
            print(f"✓ 成功找到 {duplicate_count} 个重复组（预期至少 {expected_duplicates} 个）")
        else:
            print(f"✗ 只找到 {duplicate_count} 个重复组，预期 {expected_duplicates} 个")
        
        print("\n测试完成!")
        
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir)
        print(f"已清理临时文件: {temp_dir}")

if __name__ == "__main__":
    main()