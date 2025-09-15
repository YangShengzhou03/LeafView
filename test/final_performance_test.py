#!/usr/bin/env python3
"""
最终性能测试 - 验证哈希桶优化算法
"""

import numpy as np
import time
from RemoveDuplicationThread import ImageHasher

def generate_test_hashes(num_images=1000, similarity_rate=0.1):
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

def test_original_algorithm(hashes, threshold=5):
    """测试原始算法"""
    print("测试原始算法...")
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
        
        for i in sorted(to_remove, reverse=True):
            if i < len(remaining_paths):
                remaining_paths.pop(i)
        
        group_id += 1
    
    end_time = time.time()
    return groups, end_time - start_time

def test_optimized_algorithm(hashes, threshold=5):
    """测试优化后的算法（哈希桶）"""
    print("测试优化算法...")
    start_time = time.time()
    
    groups = {}
    
    # 哈希桶预分组
    from collections import defaultdict
    hash_buckets = defaultdict(list)
    for path, hash_bits in hashes.items():
        bucket_key = ImageHasher.hash_to_int(hash_bits, 16)
        hash_buckets[bucket_key].append(path)
    
    group_id = 0
    
    # 处理每个桶
    for bucket_paths in hash_buckets.values():
        if len(bucket_paths) == 1:
            groups[group_id] = bucket_paths
            group_id += 1
            continue
        
        bucket_remaining = bucket_paths.copy()
        while bucket_remaining:
            seed_path = bucket_remaining.pop()
            groups[group_id] = [seed_path]
            seed_hash = hashes[seed_path]
            
            to_remove = []
            for i, path in enumerate(bucket_remaining):
                distance = ImageHasher.hamming_distance(seed_hash, hashes[path])
                if distance <= threshold:
                    groups[group_id].append(path)
                    to_remove.append(i)
            
            for i in sorted(to_remove, reverse=True):
                if i < len(bucket_remaining):
                    bucket_remaining.pop(i)
            
            group_id += 1
    
    end_time = time.time()
    return groups, end_time - start_time

def verify_consistency(original_groups, optimized_groups):
    """验证结果一致性"""
    def groups_to_set(groups_dict):
        return {frozenset(group) for group in groups_dict.values()}
    
    original_sets = groups_to_set(original_groups)
    optimized_sets = groups_to_set(optimized_groups)
    
    return original_sets == optimized_sets

def main():
    print("=== 最终性能测试 ===")
    
    # 生成测试数据
    print("生成测试数据...")
    test_hashes = generate_test_hashes(800, 0.15)
    print(f"生成 {len(test_hashes)} 个测试哈希")
    
    # 测试两种算法
    print("\n" + "="*50)
    original_groups, original_time = test_original_algorithm(test_hashes.copy())
    print(f"原始算法耗时: {original_time:.3f}秒")
    print(f"找到 {len(original_groups)} 个组")
    
    print("\n" + "="*50)
    optimized_groups, optimized_time = test_optimized_algorithm(test_hashes.copy())
    print(f"优化算法耗时: {optimized_time:.3f}秒")
    print(f"找到 {len(optimized_groups)} 个组")
    
    # 性能对比
    print("\n" + "="*50)
    print("性能对比:")
    if optimized_time < original_time:
        speedup = original_time / optimized_time
        print(f"✓ 优化算法更快: {speedup:.1f}倍")
    else:
        slowdown = optimized_time / original_time
        print(f"✗ 优化算法更慢: {slowdown:.1f}倍")
    
    # 验证一致性
    print("\n验证结果一致性...")
    if verify_consistency(original_groups, optimized_groups):
        print("✓ 结果完全一致")
    else:
        print("✗ 结果不一致")
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()