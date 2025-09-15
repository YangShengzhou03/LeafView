#!/usr/bin/env python3
"""
测试脚本：验证重复图片删除功能的修复
"""

import os
import sys
import time
from PyQt6 import QtWidgets, QtCore
from RemoveDuplicationThread import HashWorker, ContrastWorker

def test_hash_worker():
    """测试哈希计算线程"""
    print("测试哈希计算线程...")
    
    # 创建一些测试图片路径（使用项目中的实际图片）
    test_images = []
    resources_dir = os.path.join(os.path.dirname(__file__), 'resources', 'img')
    
    if os.path.exists(resources_dir):
        for root, _, files in os.walk(resources_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    test_images.append(os.path.join(root, file))
                    if len(test_images) >= 10:  # 限制测试数量
                        break
            if len(test_images) >= 10:
                break
    
    if not test_images:
        print("未找到测试图片，创建虚拟测试数据")
        test_images = [f"/fake/path/image_{i}.jpg" for i in range(5)]
    
    app = QtWidgets.QApplication(sys.argv)
    
    # 测试哈希计算
    hash_worker = HashWorker(test_images)
    
    def on_hash_completed(hashes):
        print(f"哈希计算完成，共计算 {len(hashes)} 张图片的哈希值")
        for path, hash_val in list(hashes.items())[:3]:  # 显示前3个
            print(f"  {os.path.basename(path)}: {hash_val[:10]}...")
        
        # 测试对比线程
        test_contrast_worker(hashes)
    
    def on_hash_error(error):
        print(f"哈希计算错误: {error}")
        sys.exit(1)
    
    hash_worker.hash_completed.connect(on_hash_completed)
    hash_worker.error_occurred.connect(on_hash_error)
    
    print("开始哈希计算...")
    hash_worker.start()
    
    # 等待线程完成
    while hash_worker.isRunning():
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.1)
    
    print("哈希计算线程测试完成")

def test_contrast_worker(hashes):
    """测试对比线程"""
    print("\n测试对比线程...")
    
    if not hashes:
        print("没有哈希数据，跳过对比测试")
        return
    
    # 创建一些相似的哈希值用于测试
    test_hashes = hashes.copy()
    
    # 如果图片太少，创建一些相似的测试数据
    if len(test_hashes) < 3:
        print("图片数量不足，创建测试数据...")
        base_hash = next(iter(test_hashes.values()))
        for i in range(3):
            test_hashes[f"/test/path/dup_{i}.jpg"] = base_hash.copy()
    
    contrast_worker = ContrastWorker(test_hashes, threshold=5)
    
    def on_groups_completed(groups):
        print(f"对比完成，找到 {len(groups)} 个图片组")
        
        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"其中有 {len(duplicate_groups)} 个重复组")
        
        for group_id, paths in list(duplicate_groups.items())[:3]:  # 显示前3个组
            print(f"组 {group_id} ({len(paths)}张):")
            for path in paths[:3]:  # 显示前3个路径
                print(f"  {os.path.basename(path)}")
            if len(paths) > 3:
                print(f"  ... 还有 {len(paths) - 3} 张")
        
        print("对比线程测试完成")
        sys.exit(0)
    
    contrast_worker.groups_completed.connect(on_groups_completed)
    
    print("开始图片对比...")
    contrast_worker.start()
    
    # 设置超时
    timeout = time.time() + 30  # 30秒超时
    while contrast_worker.isRunning() and time.time() < timeout:
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.1)
    
    if contrast_worker.isRunning():
        print("对比线程超时，可能存在卡死问题")
        contrast_worker.stop()
        contrast_worker.wait(2000)  # 等待2秒
        sys.exit(1)
    else:
        print("对比线程正常完成")

if __name__ == "__main__":
    print("=" * 50)
    print("重复图片删除功能修复测试")
    print("=" * 50)
    
    try:
        test_hash_worker()
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)