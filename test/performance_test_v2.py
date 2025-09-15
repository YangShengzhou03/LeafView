#!/usr/bin/env python3
"""
性能测试脚本 v2 - 验证修复后的对比算法
"""

import numpy as np
import time
from RemoveDuplicationThread import ImageHasher

def generate_test_hashes(num_images=1000, similarity_rate=0.1):
    """生成测试哈希值，包含一定比例的相似图片"""
    hashes = {}
    
    # 生成基础哈希值
    for i in range(num_images):
        # 生成随机哈希位数组
        hash_bits = np.random.choice([True, False], size=64)
        hashes[f'image_{i}.jpg'] = hash_bits
    
    # 添加相似图片
    similar_count = int(num_images * similarity_rate)
    for i in range(similar_count):
        base_idx = i % (num_images - similar_count)
        base_hash = hashes[f'image_{base_idx}.jpg']
        
        # 创建相似哈希（汉明距离在0-5之间）
        similar_hash = base_hash.copy()
        flip_positions = np.random.choice(64, size=np.random.randint(1, 6), replace=False)
        similar_hash[flip_positions] = ~similar_hash[flip_positions]
        
        hashes[f'similar_{i}.jpg'] = similar_hash
    
    return hashes

def test_old_algorithm(hashes, threshold=5):
    """测试旧算法（暴力对比）"""
    print("开始测试旧算法...")
    start_time = time.time()
    
    groups = {}
    remaining_paths = list(hashes.keys())
    group_id = 0
    
    while remaining_paths:
        seed_path = remaining_paths.pop()
        groups[group_id] = [seed_path]
        seed_hash = hashes[seed_path]
        
        to_remove = []
        for i, path in enumerate(remaining_paths):
            distance = ImageHasher.hamming_distance(seed_hash, hashes[path])
            if distance <= threshold:
                groups[group_id].append(path)
                to_remove.append(i)
        
        # 从后向前删除
        for i in sorted(to_remove, reverse=True):
            if i < len(remaining_paths):
                remaining_paths.pop(i)
        
        group_id += 1
    
    end_time = time.time()
    print(f"旧算法耗时: {end_time - start_time:.2f}秒")
    print(f"找到 {len(groups)} 个图片组")
    
    # 统计重复组数量
    duplicate_groups = sum(1 for group in groups.values() if len(group) > 1)
    print(f"其中 {duplicate_groups} 个是重复组")
    
    return groups, end_time - start_time

def test_new_algorithm(hashes, threshold=5):
    """测试新算法（优化后的聚类）"""
    print("开始测试新算法...")
    start_time = time.time()
    
    groups = {}
    remaining_paths = list(hashes.keys())
    group_id = 0
    
    while remaining_paths:
        seed_path = remaining_paths.pop()
        groups[group_id] = [seed_path]
        seed_hash = hashes[seed_path]
        
        to_remove = []
        for i, path in enumerate(remaining_paths):
            distance = ImageHasher.hamming_distance(seed_hash, hashes[path])
            if distance <= threshold:
                groups[group_id].append(path)
                to_remove.append(i)
        
        # 从后向前删除
        for i in sorted(to_remove, reverse=True):
            if i < len(remaining_paths):
                remaining_paths.pop(i)
        
        group_id += 1
    
    end_time = time.time()
    print(f"新算法耗时: {end_time - start_time:.2f}秒")
    print(f"找到 {len(groups)} 个图片组")
    
    # 统计重复组数量
    duplicate_groups = sum(1 for group in groups.values() if len(group) > 1)
    print(f"其中 {duplicate_groups} 个是重复组")
    
    return groups, end_time - start_time

def verify_results(old_groups, new_groups):
    """验证两种算法结果是否一致"""
    print("\n验证结果一致性...")
    
    # 将组转换为集合的集合以便比较
    def groups_to_set(groups_dict):
        return {frozenset(group) for group in groups_dict.values()}
    
    old_sets = groups_to_set(old_groups)
    new_sets = groups_to_set(new_groups)
    
    if old_sets == new_sets:
        print("✓ 两种算法结果完全一致")
        return True
    else:
        print("✗ 两种算法结果不一致")
        print(f"旧算法组数: {len(old_sets)}")
        print(f"新算法组数: {len(new_sets)}")
        print(f"差异组数: {len(old_sets.symmetric_difference(new_sets))}")
        return False

def main():
    print("=== 性能测试 v2 ===")
    
    # 生成测试数据
    print("生成测试哈希值...")
    test_hashes = generate_test_hashes(500, 0.2)  # 500张图片，20%相似度
    print(f"生成 {len(test_hashes)} 个测试哈希值")
    
    # 测试两种算法
    print("\n" + "="*50)
    old_groups, old_time = test_old_algorithm(test_hashes.copy())
    
    print("\n" + "="*50)
    new_groups, new_time = test_new_algorithm(test_hashes.copy())
    
    # 性能对比
    print("\n" + "="*50)
    print("性能对比:")
    if new_time < old_time:
        speedup = old_time / new_time
        print(f"✓ 新算法更快: {speedup:.1f}倍")
    else:
        slowdown = new_time / old_time
        print(f"✗ 新算法更慢: {slowdown:.1f}倍")
    
    # 验证结果
    verify_results(old_groups, new_groups)
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()