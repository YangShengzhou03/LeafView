#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试GPS坐标解析功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from SmartArrangeThread import SmartArrangeThread

def test_gps_parsing():
    """测试GPS坐标解析功能"""
    
    # 创建线程实例
    thread = SmartArrangeThread()
    
    # 测试数据 - 你提供的GPS信息
    gps_info = {
        'Location Accuracy Horizontal': '35.000000',
        'GPS Coordinates': '23 deg 8\' 2.04\" N, 113 deg 19\' 15.60\" E',
        'GPS Altitude': '22.102 m',
        'GPS Altitude Ref': 'Above Sea Level',
        'GPS Latitude': '23 deg 8\' 2.04\" N',
        'GPS Longitude': '113 deg 19\' 15.60\" E',
        'GPS Position': '23 deg 8\' 2.04\" N, 113 deg 19\' 15.60\" E'
    }
    
    print("测试GPS信息解析:")
    print("=" * 50)
    
    # 打印原始GPS信息
    print("原始GPS信息:")
    for key, value in gps_info.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    
    # 测试解析
    lat, lon = thread.parse_gps_coordinates(gps_info)
    
    if lat is not None and lon is not None:
        print(f"解析结果:")
        print(f"  纬度: {lat:.6f}°")
        print(f"  经度: {lon:.6f}°")
        print(f"  坐标格式: {abs(lat):.6f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.6f}°{'E' if lon >= 0 else 'W'}")
        
        # 验证结果（预期值）
        expected_lat = 23.133900  # 23°8'2.04"N = 23 + 8/60 + 2.04/3600
        expected_lon = 113.321000  # 113°19'15.60"E = 113 + 19/60 + 15.60/3600
        
        print(f"\n验证结果:")
        print(f"  预期纬度: {expected_lat:.6f}°")
        print(f"  实际纬度: {lat:.6f}°")
        print(f"  纬度误差: {abs(lat - expected_lat):.6f}°")
        
        print(f"  预期经度: {expected_lon:.6f}°")
        print(f"  实际经度: {lon:.6f}°")
        print(f"  经度误差: {abs(lon - expected_lon):.6f}°")
        
        # 检查误差是否在可接受范围内
        tolerance = 0.000001  # 1微度的误差
        if abs(lat - expected_lat) < tolerance and abs(lon - expected_lon) < tolerance:
            print("\n✅ 测试通过！GPS坐标解析正确。")
        else:
            print("\n❌ 测试失败！GPS坐标解析有误。")
            
    else:
        print("❌ 解析失败，无法提取经纬度坐标")

if __name__ == "__main__":
    test_gps_parsing()