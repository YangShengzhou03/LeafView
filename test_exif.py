#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试EXIF数据读取脚本
用于测试品牌、型号和地理位置信息的读取
"""

import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from SmartArrangeThread import SmartArrangeThread

def test_exif_reading(directory_path):
    """测试指定目录下图片文件的EXIF数据读取"""
    
    if not os.path.exists(directory_path):
        print(f"目录不存在: {directory_path}")
        print("请将测试文件复制到该目录，或者修改目录路径")
        return
    
    # 创建测试线程实例
    thread = SmartArrangeThread()
    thread.load_geographic_data()  # 加载地理数据
    
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.tiff', '.tif', '.heic', '.png'}
    
    print(f"正在扫描目录: {directory_path}")
    print("=" * 60)
    
    file_count = 0
    processed_count = 0
    
    for file_path in Path(directory_path).rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            file_count += 1
            
            print(f"\n处理文件 {file_count}: {file_path.name}")
            print("-" * 40)
            
            try:
                # 获取EXIF数据
                exif_data = thread.get_exif_data(str(file_path))
                
                if exif_data:
                    processed_count += 1
                    
                    # 输出品牌和型号信息
                    brand = exif_data.get('Make', '未知品牌')
                    model = exif_data.get('Model', '未知型号')
                    print(f"品牌: {brand}")
                    print(f"型号: {model}")
                    
                    # 输出GPS信息
                    gps_lat = exif_data.get('GPS GPSLatitude')
                    gps_lon = exif_data.get('GPS GPSLongitude')
                    
                    if gps_lat and gps_lon:
                        print(f"GPS纬度: {gps_lat}")
                        print(f"GPS经度: {gps_lon}")
                        
                        # 检查坐标是否为十进制格式
                        if isinstance(gps_lat, (int, float)) and isinstance(gps_lon, (int, float)):
                            lat_deg = gps_lat
                            lon_deg = gps_lon
                        else:
                            # 转换为十进制度数
                            lat_deg = thread.convert_to_degrees(gps_lat)
                            lon_deg = thread.convert_to_degrees(gps_lon)
                        
                        if lat_deg and lon_deg:
                            print(f"纬度(十进制): {lat_deg:.6f}")
                            print(f"经度(十进制): {lon_deg:.6f}")
                            
                            # 获取省份和城市信息
                            province, city = thread.get_city_and_province(lat_deg, lon_deg)
                            print(f"省份: {province}")
                            print(f"城市: {city}")
                        else:
                            print("GPS坐标转换失败")
                    else:
                        print("无GPS信息")
                    
                    # 输出拍摄时间
                    datetime = exif_data.get('DateTime', '未知时间')
                    print(f"拍摄时间: {datetime}")
                    
                else:
                    print("无法读取EXIF数据")
                    
            except Exception as e:
                print(f"处理文件 {file_path.name} 时出错: {e}")
    
    print("\n" + "=" * 60)
    print(f"扫描完成! 共找到 {file_count} 个图片文件，成功处理 {processed_count} 个文件")

def main():
    """主函数"""
    # 测试目录路径 - 你可以修改这个路径
    test_directory = "D:\待分类"  # 在当前目录下创建test_images文件夹
    
    # 如果测试目录不存在，创建它
    if not os.path.exists(test_directory):
        os.makedirs(test_directory)
        print(f"已创建测试目录: {test_directory}")
        print("请将测试的jpg文件复制到此目录，然后重新运行脚本")
        return
    
    print("EXIF数据读取测试")
    print("=" * 60)
    test_exif_reading(test_directory)

if __name__ == "__main__":
    main()