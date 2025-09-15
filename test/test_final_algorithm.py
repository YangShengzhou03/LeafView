#!/usr/bin/env python3
"""
最终算法测试 - 验证修复后的对比算法
"""

import numpy as np
import time
from RemoveDuplicationThread import ImageHasher, ContrastWorker
from PyQt6 import QtCore

def generate_test_hashes(num_images=200, similarity_rate=0.2):
    """生成测试哈希值"""
    hashes = {}
    
    for i in range(num_images):
        hash_bits = np.random.choice([True, False], size=64)
        hashes[f'image_{i}.jpg'] = hash_bits
    
    similar_count = int(num_images * similarity_rate)
    for i in range(similar_count):
        base_idx = i % (num_images - similar_count)
        base_hash = hashes[f'image_{base_idx}.jpg']
        
        similar_hash = base_hash.copy()
        flip_positions = np.random.choice(64, size=np.random.randint(1, 6), replace=False)
        similar_hash[flip_positions] = ~similar_hash[flip_positions]
        
        hashes[f'similar_{i}.jpg'] = similar_hash
    
    return hashes

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
            pass
    
    signal = TestSignal()
    
    worker = ContrastWorker(hashes, threshold)
    worker.groups_completed.connect(signal.groups_completed)
    worker.progress_updated.connect(signal.progress_updated)
    worker.image_matched.connect(signal.image_matched)
    
    start_time = time.time()
    worker.run()  # 直接调用run方法，不启动线程
    end_time = time.time()
    
    print(f"耗时: {end_time - start_time:.3f}秒")
    print(f"找到 {len(signal.groups)} 个组")
    
    duplicate_groups = sum(1 for group in signal.groups.values() if len(group) > 1)
    print(f"其中 {duplicate_groups} 个是重复组")
    
    return signal.groups, end_time - start_time

def main():
    print("=== 最终算法测试 ===")
    
    # 生成测试数据
    print("生成测试数据...")
    test_hashes = generate_test_hashes(150, 0.15)
    print(f"生成 {len(test_hashes)} 个测试哈希")
    
    # 测试ContrastWorker
    print("\n" + "="*50)
    groups, elapsed_time = test_contrast_worker(test_hashes)
    
    # 显示一些组信息
    print("\n前10个组:")
    for i, (group_id, paths) in enumerate(list(groups.items())[:10]):
        print(f"组 {group_id}: {len(paths)} 张图片")
        if len(paths) > 1:
            print(f"  示例: {paths[0]} -> {paths[1]}")
    
    print(f"\n总耗时: {elapsed_time:.3f}秒")
    print("测试完成!")

if __name__ == "__main__":
    main()