#!/usr/bin/env python3
"""
测试配置文件管理模块
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import config_manager

def test_folder_operations():
    """测试文件夹路径操作"""
    print("=== 测试文件夹路径操作 ===")
    
    # 清理现有数据
    config_manager.clear_folders()
    
    # 添加文件夹路径
    test_paths = [
        "C:\\Users\\Test\\Documents",
        "D:\\Photos\\2024",
        "E:\\Videos"
    ]
    
    for path in test_paths:
        config_manager.add_folder(path)
        print(f"添加文件夹: {path}")
    
    # 获取所有文件夹
    folders = config_manager.get_folders()
    print(f"获取到的文件夹: {folders}")
    
    # 移除一个文件夹
    config_manager.remove_folder(test_paths[1])
    print(f"移除文件夹: {test_paths[1]}")
    
    # 再次获取验证
    folders = config_manager.get_folders()
    print(f"移除后的文件夹: {folders}")
    
    print("文件夹操作测试完成!\n")

def test_location_cache():
    """测试地理位置缓存"""
    print("=== 测试地理位置缓存 ===")
    
    # 清理现有数据
    config_manager.clear_locations()
    
    # 添加地理位置缓存
    test_locations = [
        (39.9042, 116.4074, "北京市东城区"),
        (31.2304, 121.4737, "上海市黄浦区"),
        (23.1291, 113.2644, "广州市天河区")
    ]
    
    for lat, lon, address in test_locations:
        config_manager.cache_location(lat, lon, address)
        print(f"缓存位置: ({lat}, {lon}) -> {address}")
    
    # 获取缓存的位置
    for lat, lon, expected_address in test_locations:
        cached_address = config_manager.get_cached_location(lat, lon)
        print(f"获取位置 ({lat}, {lon}): {cached_address} (期望: {expected_address})")
        assert cached_address == expected_address, f"缓存地址不匹配: {cached_address} != {expected_address}"
    
    # 测试不存在的经纬度
    nonexistent = config_manager.get_cached_location(0, 0)
    print(f"不存在的经纬度: {nonexistent}")
    assert nonexistent is None, "不存在的经纬度应该返回None"
    
    print("地理位置缓存测试完成!\n")

def test_config_persistence():
    """测试配置持久化"""
    print("=== 测试配置持久化 ===")
    
    # 创建新的配置管理器实例来测试持久化
    from config_manager import ConfigManager
    test_manager = ConfigManager()
    
    # 添加一些测试数据
    test_manager.add_folder("C:\\Test\\Persistence")
    test_manager.cache_location(40.7128, -74.0060, "New York, NY")
    
    # 获取数据验证
    folders = test_manager.get_folders()
    location = test_manager.get_cached_location(40.7128, -74.0060)
    
    print(f"持久化文件夹: {folders}")
    print(f"持久化位置: {location}")
    
    # 清理测试数据
    test_manager.clear_folders()
    test_manager.clear_locations()
    
    print("配置持久化测试完成!\n")

if __name__ == "__main__":
    try:
        test_folder_operations()
        test_location_cache()
        test_config_persistence()
        print("✅ 所有测试通过!")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()