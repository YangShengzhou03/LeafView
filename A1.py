import os
import sys
import subprocess
import platform
import time


def get_exiftool_path():
    """获取嵌入的exiftool可执行文件路径"""
    system = platform.system()

    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Windows系统处理带(-k)的文件名
    if system == "Windows":
        exiftool_name = "exiftool(-k).exe"
    else:
        exiftool_name = "exiftool"

    exiftool_path = os.path.join(base_dir, "resources", "exiftool", exiftool_name)

    # 检查文件是否存在且可执行
    if not os.path.exists(exiftool_path):
        raise FileNotFoundError(f"未找到exiftool可执行文件: {exiftool_path}")

    if not os.access(exiftool_path, os.X_OK):
        raise PermissionError(f"exiftool没有执行权限: {exiftool_path}")

    # 对于Windows系统，给路径添加引号以处理特殊字符
    if system == "Windows":
        exiftool_path = f'"{exiftool_path}"'

    return exiftool_path


def get_video_metadata(file_path, timeout=30):
    """
    使用嵌入的exiftool读取视频文件的元数据，增加详细错误输出
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在")
        return None

    if not os.path.isfile(file_path):
        print(f"错误: '{file_path}' 不是一个有效的文件")
        return None

    try:
        exiftool_path = get_exiftool_path()
        # 使用复制的exiftool.exe文件（如果存在）
        exiftool_path_copy = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "exiftool", "exiftool.exe")
        if os.path.exists(exiftool_path_copy):
            exiftool_path = f'"{exiftool_path_copy}"'

        # 调整参数：处理带引号的路径，使用字符串命令而非列表
        # 对于Windows，使用正斜杠并确保路径被正确引用
        file_path_normalized = file_path.replace('\\', '/')
        # 使用-fast参数提高读取速度
        cmd = f"{exiftool_path} -fast \"{file_path_normalized}\""

        # 执行命令，同时捕获stdout和stderr
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True  # Windows下必须启用shell才能正确处理带引号的路径
        )

        # 解析结果为字典
        metadata = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        # 如果没有获取到元数据，尝试使用-ee参数
        if not metadata:
            cmd = f"{exiftool_path} -ee \"{file_path_normalized}\""
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True
            )
            
            # 解析结果为字典
            metadata = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

        return metadata

    except subprocess.TimeoutExpired:
        print(f"错误: 读取元数据超时（超过{timeout}秒）")
        return None
    except Exception as e:
        print(f"读取文件时出错: {str(e)}")
        return None


def extract_key_info(metadata):
    """提取关键信息：拍摄日期和GPS（如果存在）"""
    key_info = {
        '拍摄日期': None,
        'GPS信息': None
    }

    # 查找拍摄日期相关信息，扩展更多可能的键名
    date_keys = [
        'Create Date', 'Creation Date', 'DateTimeOriginal', 
        'Media Create Date', 'File Modification Date/Time',
        'Create Date', 'Date/Time Original', 'Date/Time Created'
    ]
    for key in date_keys:
        if key in metadata:
            key_info['拍摄日期'] = metadata[key]
            print(f"找到拍摄日期: {key} = {metadata[key]}")
            break
    else:
        # 如果没找到，尝试更通用的搜索
        for key, value in metadata.items():
            if 'date' in key.lower() and ('create' in key.lower() or 'media' in key.lower()):
                key_info['拍摄日期'] = value
                print(f"通过通用搜索找到拍摄日期: {key} = {value}")
                break

    # 查找GPS相关信息
    gps_info = {}
    for key, value in metadata.items():
        if 'gps' in key.lower() or 'location' in key.lower():
            gps_info[key] = value

    if gps_info:
        key_info['GPS信息'] = gps_info

    return key_info


def main():
    video_path = r"D:\待分类\test.MOV"

    print("开始读取视频元数据...")
    start_time = time.time()

    metadata = get_video_metadata(video_path)

    end_time = time.time()
    print(f"读取完成，耗时: {end_time - start_time:.2f}秒")

    if metadata:
        print("\n视频所有元数据信息:")
        print("----------------------------------------")

        # 只打印前20条元数据
        for i, (key, value) in enumerate(metadata.items()):
            print(f"{key}: {value}")
            if i >= 19:
                print("... 更多元数据省略 ...")
                break

        print("\n关键信息提取:")
        print("----------------------------------------")

        key_info = extract_key_info(metadata)

        if key_info['拍摄日期']:
            print(f"拍摄日期: {key_info['拍摄日期']}")
        else:
            print("未找到拍摄日期信息")

        if key_info['GPS信息']:
            print("GPS信息:")
            for key, value in key_info['GPS信息'].items():
                print(f"  {key}: {value}")
        else:
            print("未找到GPS信息")


if __name__ == "__main__":
    try:
        get_exiftool_path()
        main()
    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确认exiftool文件位置是否正确:")
        print("预期路径: resources/exiftool/exiftool(-k).exe")
    except PermissionError as e:
        print(f"权限错误: {e}")
        print("请检查exiftool文件是否有执行权限")
    except Exception as e:
        print(f"程序出错: {str(e)}")
