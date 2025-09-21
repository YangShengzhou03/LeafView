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
    """提取关键信息：相机品牌和型号（如果存在）"""
    key_info = {
        '相机品牌': None,
        '相机型号': None
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

    return key_info


def main():
    video_path = r"D:\待分类\test.MOV"

    metadata = get_video_metadata(video_path)

    key_info = extract_key_info(metadata)

    if key_info['相机品牌']:
        print(f"相机品牌: {key_info['相机品牌']}")
    else:
        print("未找到相机品牌信息")

    if key_info['相机型号']:
        print(f"相机型号: {key_info['相机型号']}")
    else:
        print("未找到相机型号信息")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序出错: {str(e)}")
