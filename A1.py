import subprocess
import os
import time
from datetime import datetime

from common import get_resource_path


def get_video_metadata(file_path, timeout=30):
    try:

        file_path_normalized = file_path.replace('\\', '/')
        cmd = f"{get_resource_path('resources/exiftool/exiftool.exe')} -fast \"{file_path_normalized}\""

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True
        )

        metadata = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        return metadata

    except Exception as e:
        print(f"读取文件时出错: {str(e)}")
        return None


def extract_key_info(metadata):
    """提取关键信息：相机品牌和型号（如果存在）"""
    key_info = {
        '相机品牌': None,
        '相机型号': None,
        'GPS位置': None,
        '拍摄时间': None,
        '备注标记': None
    }

    # 查找相机品牌相关信息
    brand_keys = [
        'Make', 'Camera Make', 'Manufacturer', 'Camera Manufacturer'
    ]
    for key in brand_keys:
        if key in metadata:
            key_info['相机品牌'] = metadata[key]
            print(f"找到相机品牌: {key} = {metadata[key]}")
            break
    else:
        # 如果没找到，尝试更通用的搜索
        for key, value in metadata.items():
            if 'make' in key.lower() or 'manufacturer' in key.lower():
                key_info['相机品牌'] = value
                print(f"通过通用搜索找到相机品牌: {key} = {value}")
                break

    # 查找相机型号相关信息
    model_keys = [
        'Model', 'Camera Model', 'Device Model', 'Camera Model Name'
    ]
    for key in model_keys:
        if key in metadata:
            key_info['相机型号'] = metadata[key]
            print(f"找到相机型号: {key} = {metadata[key]}")
            break
    else:
        # 如果没找到，尝试更通用的搜索
        for key, value in metadata.items():
            if 'model' in key.lower() and ('camera' in key.lower() or 'device' in key.lower()):
                key_info['相机型号'] = value
                print(f"通过通用搜索找到相机型号: {key} = {value}")
                break

    # 查找GPS位置信息
    gps_keys = [
        'GPS Position', 'GPS Latitude', 'GPS Longitude', 'Location'
    ]
    for key in gps_keys:
        if key in metadata:
            key_info['GPS位置'] = metadata[key]
            print(f"找到GPS位置: {key} = {metadata[key]}")
            break

    # 查找拍摄时间信息
    time_keys = [
        'Create Date', 'Media Create Date', 'Track Create Date', 'Date/Time Original'
    ]
    for key in time_keys:
        if key in metadata:
            key_info['拍摄时间'] = metadata[key]
            print(f"找到拍摄时间: {key} = {metadata[key]}")
            break

    # 查找备注标记信息
    comment_keys = [
        'Comment', 'Description', 'Image Description', 'User Comment'
    ]
    for key in comment_keys:
        if key in metadata:
            key_info['备注标记'] = metadata[key]
            print(f"找到备注标记: {key} = {metadata[key]}")
            break

    return key_info


def decimal_to_dms(decimal):
    """
    将十进制坐标转换为度分秒格式
    例如: 31.2222 -> "31 deg 13' 19.92\""
    """
    try:
        # 处理正负号
        is_negative = decimal < 0
        decimal = abs(decimal)
        
        # 计算度、分、秒
        degrees = int(decimal)
        minutes_decimal = (decimal - degrees) * 60
        minutes = int(minutes_decimal)
        seconds = (minutes_decimal - minutes) * 60
        
        # 格式化输出
        dms_str = f"{degrees} deg {minutes}' {seconds:.2f}\""
        
        return dms_str
    except Exception as e:
        print(f"坐标转换错误: {str(e)}")
        return str(decimal)


def convert_dms_to_decimal(dms_str):
    """
    将度分秒格式的GPS坐标转换为十进制格式
    例如: "23 deg 8' 2.04\" N" -> 23.1339
    """
    try:
        # 解析度分秒格式
        import re
        
        # 匹配度分秒格式
        pattern = r'(\d+) deg (\d+)\'( (\d+(?:\.\d+)?)\")? ([NSWE])'
        match = re.search(pattern, dms_str)
        
        if match:
            degrees = float(match.group(1))
            minutes = float(match.group(2))
            seconds = float(match.group(4)) if match.group(4) else 0.0
            direction = match.group(5)
            
            # 计算十进制坐标
            decimal = degrees + minutes/60 + seconds/3600
            
            # 处理方向（南纬和西经为负数）
            if direction in ['S', 'W']:
                decimal = -decimal
                
            return decimal
        else:
            # 尝试直接解析十进制格式
            try:
                return float(dms_str)
            except ValueError:
                return None
                
    except Exception as e:
        print(f"GPS坐标转换错误: {str(e)}")
        return None


def edit_video_exif(file_path, brand=None, model=None, gps_position=None, shoot_time=None, comment=None, max_retries=3):
    """
    编辑视频文件的EXIF数据
    
    Args:
        file_path: 视频文件路径
        brand: 相机品牌
        model: 相机型号
        gps_position: GPS位置，格式为"纬度,经度"，例如"31.2222, 121.4581"
        shoot_time: 拍摄时间，格式为"YYYY:MM:DD HH:MM:SS"
        comment: 备注标记
        max_retries: 最大重试次数
        
    Returns:
        bool: 是否成功修改
    """
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return False
    
    file_path_normalized = file_path.replace('\\', '/')
    exiftool_path = get_resource_path('resources/exiftool/exiftool.exe')
    
    # 构建exiftool命令
    cmd_parts = [exiftool_path]
    
    # 添加要修改的标签
    if brand:
        cmd_parts.append(f'-Make="{brand}"')
    
    if model:
        cmd_parts.append(f'-Model="{model}"')
    
    if gps_position:
        # 解析GPS位置
        try:
            lat, lon = map(float, gps_position.split(','))
            # 将十进制坐标转换为度分秒格式
            lat_dms = decimal_to_dms(lat)
            lon_dms = decimal_to_dms(lon)
            
            # 使用度分秒格式设置GPS标签（用引号括起来）
            cmd_parts.append(f'-GPSLatitude="{lat_dms}"')
            cmd_parts.append(f'-GPSLongitude="{lon_dms}"')
            cmd_parts.append('-GPSLatitudeRef=N' if lat >= 0 else '-GPSLatitudeRef=S')
            cmd_parts.append('-GPSLongitudeRef=E' if lon >= 0 else '-GPSLongitudeRef=W')
            # 添加GPSCoordinates标签（MOV文件可能需要这个）
            cmd_parts.append(f'-GPSCoordinates="{lat}, {lon}"')
        except ValueError:
            print(f"GPS位置格式无效: {gps_position}")
            return False
    
    if shoot_time:
        # 验证时间格式
        try:
            datetime.strptime(shoot_time, "%Y:%m:%d %H:%M:%S")
            cmd_parts.append(f'-CreateDate="{shoot_time}"')
            cmd_parts.append(f'-MediaCreateDate="{shoot_time}"')
            cmd_parts.append(f'-TrackCreateDate="{shoot_time}"')
        except ValueError:
            print(f"拍摄时间格式无效: {shoot_time}，请使用 YYYY:MM:DD HH:MM:SS 格式")
            return False
    
    if comment:
        cmd_parts.append(f'-Comment="{comment}"')
        cmd_parts.append(f'-Description="{comment}"')
    
    # 添加文件路径
    cmd_parts.append(f'"{file_path_normalized}"')
    
    # 构建完整命令
    cmd = ' '.join(cmd_parts)
    
    # 尝试修改EXIF数据
    for attempt in range(max_retries):
        try:
            print(f"尝试修改EXIF数据 (第 {attempt + 1} 次)...")
            
            # 执行命令
            print(f"执行命令: {cmd}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True
            )
            
            print(f"命令返回码: {result.returncode}")
            print(f"命令输出: {result.stdout}")
            if result.stderr:
                print(f"命令错误: {result.stderr}")
            
            if result.returncode == 0:
                print("EXIF数据修改成功")
                
                # 验证修改结果
                new_metadata = get_video_metadata(file_path)
                if new_metadata:
                    # 检查修改是否生效
                    success = True
                    
                    if brand and new_metadata.get('Make') != brand:
                        print(f"相机品牌修改失败: 期望 {brand}, 实际 {new_metadata.get('Make')}")
                        success = False
                    
                    if model and new_metadata.get('Model') != model:
                        print(f"相机型号修改失败: 期望 {model}, 实际 {new_metadata.get('Model')}")
                        success = False
                    
                    if gps_position:
                        try:
                            # 解析期望的GPS坐标
                            expected_lat, expected_lon = map(float, gps_position.split(','))
                            
                            # 获取实际的GPS坐标（可能是度分秒格式）
                            actual_lat_str = new_metadata.get('GPS Latitude')
                            actual_lon_str = new_metadata.get('GPS Longitude')
                            
                            if actual_lat_str and actual_lon_str:
                                # 将度分秒格式转换为十进制进行比较
                                actual_lat_decimal = convert_dms_to_decimal(actual_lat_str)
                                actual_lon_decimal = convert_dms_to_decimal(actual_lon_str)
                                
                                if actual_lat_decimal is not None and actual_lon_decimal is not None:
                                    # 允许一定的精度误差
                                    lat_tolerance = 0.0001
                                    lon_tolerance = 0.0001
                                    
                                    if abs(actual_lat_decimal - expected_lat) > lat_tolerance:
                                        print(f"GPS纬度修改失败: 期望 {expected_lat}, 实际 {actual_lat_decimal}")
                                        success = False
                                    
                                    if abs(actual_lon_decimal - expected_lon) > lon_tolerance:
                                        print(f"GPS经度修改失败: 期望 {expected_lon}, 实际 {actual_lon_decimal}")
                                        success = False
                                else:
                                    print("无法解析GPS坐标格式")
                                    success = False
                            else:
                                print("未找到GPS坐标信息")
                                success = False
                        except ValueError:
                            print("GPS坐标格式无效")
                            success = False
                    
                    if shoot_time:
                        time_found = False
                        for key in ['Create Date', 'Media Create Date', 'Track Create Date']:
                            if key in new_metadata and shoot_time in new_metadata[key]:
                                time_found = True
                                break
                        
                        if not time_found:
                            print(f"拍摄时间修改失败: 期望 {shoot_time}")
                            success = False
                    
                    if comment:
                        comment_found = False
                        for key in ['Comment', 'Description', 'Image Description']:
                            if key in new_metadata and comment in new_metadata[key]:
                                comment_found = True
                                break
                        
                        if not comment_found:
                            print(f"备注标记修改失败: 期望 {comment}")
                            success = False
                    
                    if success:
                        print("所有EXIF数据验证通过")
                        return True
                    else:
                        print("EXIF数据验证失败，将重试...")
                        if attempt < max_retries - 1:
                            time.sleep(1)  # 等待一秒后重试
                        continue
                else:
                    print("无法读取修改后的EXIF数据")
                    return False
            else:
                print(f"EXIF数据修改失败: {result.stderr}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待一秒后重试
                continue
                
        except Exception as e:
            print(f"修改EXIF数据时出错: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # 等待一秒后重试
            continue
    
    print(f"已达到最大重试次数 {max_retries}，修改失败")
    return False


def main():
    video_path = r"D:\待分类\test.MOV"

    # 读取原始EXIF数据
    print("读取原始EXIF数据...")
    metadata = get_video_metadata(video_path)
    
    if metadata:
        key_info = extract_key_info(metadata)
        
        print("\n原始EXIF数据:")
        if key_info['相机品牌']:
            print(f"相机品牌: {key_info['相机品牌']}")
        else:
            print("未找到相机品牌信息")

        if key_info['相机型号']:
            print(f"相机型号: {key_info['相机型号']}")
        else:
            print("未找到相机型号信息")
            
        if key_info['GPS位置']:
            print(f"GPS位置: {key_info['GPS位置']}")
        else:
            print("未找到GPS位置信息")
            
        if key_info['拍摄时间']:
            print(f"拍摄时间: {key_info['拍摄时间']}")
        else:
            print("未找到拍摄时间信息")
            
        if key_info['备注标记']:
            print(f"备注标记: {key_info['备注标记']}")
        else:
            print("未找到备注标记信息")
    else:
        print("无法读取视频文件的EXIF数据")
        return
    
    # 修改EXIF数据
    print("\n开始修改EXIF数据...")
    
    # 示例数据
    new_brand = "Appla"
    new_model = "iPhone 14 Pro Max"
    new_gps = "31.2222, 121.4581"  # 上海的经纬度
    new_time = "2025:10:15 14:30:00"
    new_comment = "这是一个快乐视频"
    
    success = edit_video_exif(
        video_path,
        brand=new_brand,
        model=new_model,
        gps_position=new_gps,
        shoot_time=new_time,
        comment=new_comment
    )
    
    if success:
        print("\nEXIF数据修改成功！")
        
        # 再次读取EXIF数据以验证
        print("\n验证修改后的EXIF数据...")
        new_metadata = get_video_metadata(video_path)
        
        if new_metadata:
            new_key_info = extract_key_info(new_metadata)
            
            print("\n修改后的EXIF数据:")
            if new_key_info['相机品牌']:
                print(f"相机品牌: {new_key_info['相机品牌']}")
            else:
                print("未找到相机品牌信息")

            if new_key_info['相机型号']:
                print(f"相机型号: {new_key_info['相机型号']}")
            else:
                print("未找到相机型号信息")
                
            if new_key_info['GPS位置']:
                print(f"GPS位置: {new_key_info['GPS位置']}")
            else:
                print("未找到GPS位置信息")
                
            if new_key_info['拍摄时间']:
                print(f"拍摄时间: {new_key_info['拍摄时间']}")
            else:
                print("未找到拍摄时间信息")
                
            if new_key_info['备注标记']:
                print(f"备注标记: {new_key_info['备注标记']}")
            else:
                print("未找到备注标记信息")
        else:
            print("无法读取修改后的EXIF数据")
    else:
        print("\nEXIF数据修改失败！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序出错: {str(e)}")
