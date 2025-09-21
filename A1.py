import subprocess

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
    """提取关键信息：拍摄日期和GPS（如果存在）"""
    key_info = {
        '拍摄日期': None,
        'GPS信息': None
    }

    # 查找拍摄日期相关信息
    date_keys = [
        'Create Date', 'Creation Date', 'DateTimeOriginal', 
        'Media Create Date', 'Date/Time Original', 'Date/Time Created'
    ]
    for key in date_keys:
        if key in metadata:
            key_info['拍摄日期'] = metadata[key]
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

    metadata = get_video_metadata(video_path)
    if not metadata:
        print("无法读取视频元数据")
        return

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
    main()
