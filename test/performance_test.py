#!/usr/bin/env python3
"""
性能测试脚本：测试优化后的重复图片删除算法
"""

import time
import numpy as np
from RemoveDuplicationThread import ImageHasher

def test_performance():
    """测试算法性能"""
    print("=" * 60)
    print("重复图片删除算法性能测试")
    print("=" * 60)
    
    hasher = ImageHasher()
    
    # 生成测试数据
    print("生成测试数据...")
    num_images = 1000
    hash_size = 64  # 8x8 哈希
    
    # 创建一些相似的哈希值
    test_hashes = {}
    base_hash = np.random.choice([True, False], size=hash_size)
    
    for i in range(num_images):
        # 创建相似的哈希（大部分位相同，少量位不同）
        if i % 10 == 0:  # 每10张图片创建一个新的基础哈希
            base_hash = np.random.choice([True, False], size=hash_size)
        
        # 添加一些随机差异
        modified_hash = base_hash.copy()
        num_changes = np.random.randint(0, 5)  # 0-4位差异
        change_indices = np.random.choice(hash_size, num_changes, replace=False)
        for idx in change_indices:
            modified_hash[idx] = not modified_hash[idx]
        
        test_hashes[f"image_{i}.jpg"] = modified_hash
    
    print(f"生成 {len(test_hashes)} 个测试哈希值")
    
    # 测试旧算法（暴力对比）
    print("\n测试旧算法（暴力对比）...")
    start_time = time.time()
    
    groups_old = {}
    remaining_paths = set(test_hashes.keys())
    group_id = 0
    threshold = 5
    
    while remaining_paths:
        seed_path = remaining_paths.pop()
        groups_old[group_id] = [seed_path]
        seed_hash = test_hashes[seed_path]
        
        to_remove = []
        for path in list(remaining_paths):
            distance = hasher.hamming_distance(seed_hash, test_hashes[path])
            if distance <= threshold:
                groups_old[group_id].append(path)
                to_remove.append(path)
        
        for path in to_remove:
            remaining_paths.discard(path)
        
        group_id += 1
        
        # 进度显示
        if group_id % 100 == 0:
            elapsed = time.time() - start_time
            print(f"  已处理 {group_id} 组，耗时: {elapsed:.2f}秒")
    
    old_time = time.time() - start_time
    print(f"旧算法完成，耗时: {old_time:.2f}秒")
    print(f"找到 {len(groups_old)} 个图片组")
    
    # 测试新算法（哈希桶优化）
    print("\n测试新算法（哈希桶优化）...")
    start_time = time.time()
    
    groups_new = {}
    hash_buckets = {}
    
    # 将哈希值分组到桶中
    for path, hash_bits in test_hashes.items():
        hash_int = hasher.hash_to_int(hash_bits)
        if hash_int not in hash_buckets:
            hash_buckets[hash_int] = []
        hash_buckets[hash_int].append(path)
    
    # 先处理完全相同的图片
    group_id = 0
    for hash_int, paths in list(hash_buckets.items()):
        if len(paths) > 1:
            groups_new[group_id] = paths
            group_id += 1
            del hash_buckets[hash_int]
    
    # 处理相似但不完全相同的图片
    remaining_hashes = list(hash_buckets.keys())
    
    for i, hash1_int in enumerate(remaining_hashes):
        paths1 = hash_buckets.get(hash1_int, [])
        if not paths1:
            continue
        
        hash1_bits = test_hashes[paths1[0]]
        
        for j in range(i + 1, len(remaining_hashes)):
            hash2_int = remaining_hashes[j]
            paths2 = hash_buckets.get(hash2_int, [])
            if not paths2:
                continue
            
            hash2_bits = test_hashes[paths2[0]]
            distance = hasher.hamming_distance(hash1_bits, hash2_bits)
            
            if distance <= threshold:
                if group_id not in groups_new:
                    groups_new[group_id] = paths1.copy()
                groups_new[group_id].extend(paths2)
                hash_buckets[hash2_int] = []
        
        # 进度显示
        if group_id % 100 == 0:
            elapsed = time.time() - start_time
            print(f"  已处理 {group_id} 组，耗时: {elapsed:.2f}秒")
    
    # 添加剩余的单个图片
    for paths in hash_buckets.values():
        if paths and len(paths) == 1:
            groups_new[group_id] = paths
            group_id += 1
    
    new_time = time.time() - start_time
    print(f"新算法完成，耗时: {new_time:.2f}秒")
    print(f"找到 {len(groups_new)} 个图片组")
    
    # 性能对比
    print("\n" + "=" * 60)
    print("性能对比结果:")
    print("=" * 60)
    print(f"旧算法耗时: {old_time:.2f} 秒")
    print(f"新算法耗时: {new_time:.2f} 秒")
    print(f"性能提升: {old_time/new_time:.1f} 倍")
    
    # 验证结果一致性
    old_duplicates = sum(1 for group in groups_old.values() if len(group) > 1)
    new_duplicates = sum(1 for group in groups_new.values() if len(group) > 1)
    
    print(f"\n结果验证:")
    print(f"旧算法找到重复组: {old_duplicates}")
    print(f"新算法找到重复组: {new_duplicates}")
    
    if old_duplicates == new_duplicates:
        print("✅ 两种算法结果一致")
    else:
        print("❌ 算法结果不一致，需要检查")
    
    return old_time, new_time

if __name__ == "__main__":
    try:
        old_time, new_time = test_performance()
        
        if new_time < old_time / 2:  # 至少快2倍
            print("\n🎉 性能优化成功！")
        else:
            print("\n⚠️  性能优化效果不明显")
            
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()