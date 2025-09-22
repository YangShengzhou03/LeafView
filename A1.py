import subprocess
import os
import time
from datetime import datetime

from common import get_resource_path


def get_video_metadata(file_path, timeout=30):
    """仅读取视频的时间相关元数据，用于后续验证"""
    try:
        file_path_normalized = file_path.replace('\\', '/')
        # 只读取时间相关标签，减少数据处理量
        cmd = f"{get_resource_path('resources/exiftool/exiftool.exe')} -CreateDate -CreationDate -MediaCreateDate -DateTimeOriginal -EncodedDate \"{file_path_normalized}\""

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
        print(f"读取文件元数据出错: {str(e)}")
        return None


def write_mp4_shoot_time(file_path, shoot_time, max_retries=3):
    """
    仅向MP4文件写入拍摄时间（覆盖多个时间标签确保兼容性）
    
    Args:
        file_path: MP4文件路径
        shoot_time: 拍摄时间，格式必须为"YYYY:MM:DD HH:MM:SS"
        max_retries: 失败重试次数
        
    Returns:
        bool: 是否成功写入
    """
    # 基础校验：文件格式和存在性
    if not file_path.lower().endswith('.mp4'):
        print(f"错误：仅支持MP4格式文件，当前文件：{file_path}")
        return False
    if not os.path.exists(file_path):
        print(f"错误：文件不存在：{file_path}")
        return False

    # 时间格式校验
    try:
        datetime.strptime(shoot_time, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        print(f"错误：时间格式无效！需使用 'YYYY:MM:DD HH:MM:SS'，当前输入：{shoot_time}")
        return False

    # 构建核心命令（仅包含时间写入相关参数）
    file_path_normalized = file_path.replace('\\', '/')
    exiftool_path = get_resource_path('resources/exiftool/exiftool.exe')
    cmd_parts = [
        exiftool_path,
        "-overwrite_original",  # 覆盖原文件，不生成备份
        f'-CreateDate="{shoot_time}"',
        f'-CreationDate="{shoot_time}"',
        f'-MediaCreateDate="{shoot_time}"',
        f'-DateTimeOriginal="{shoot_time}"',
        f'-EncodedDate="{shoot_time}"',
        f'"{file_path_normalized}"'
    ]
    cmd = ' '.join(cmd_parts)

    # 执行写入并验证
    for attempt in range(max_retries):
        try:
            print(f"第 {attempt + 1} 次尝试写入拍摄时间...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True
            )

            # 命令执行成功后验证结果
            if result.returncode == 0:
                print("时间写入命令执行完成，开始验证结果...")
                new_metadata = get_video_metadata(file_path)
                if not new_metadata:
                    print("警告：无法读取修改后的元数据，无法确认是否成功")
                    return True  # 命令执行成功但验证失败，视为半成功

                # 检查至少一个时间标签已更新
                time_updated = False
                for key in ['CreateDate', 'CreationDate', 'MediaCreateDate', 'DateTimeOriginal']:
                    if key in new_metadata and new_metadata[key] == shoot_time:
                        time_updated = True
                        print(f"✓ 已确认 {key} 标签更新为：{shoot_time}")
                        break

                if time_updated:
                    print(f"\n拍摄时间写入成功！最终生效时间：{shoot_time}")
                    return True
                else:
                    print(f"验证失败：所有时间标签未更新，重试中...")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    continue

            # 命令执行失败
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                print(f"写入失败：{error_msg}，重试中...")
                if attempt < max_retries - 1:
                    time.sleep(1)

        except Exception as e:
            print(f"写入过程出错：{str(e)}，重试中...")
            if attempt < max_retries - 1:
                time.sleep(1)

    # 达到最大重试次数
    print(f"\n错误：已尝试 {max_retries} 次，拍摄时间写入失败")
    return False


def main():
    # --------------------------
    # 请在这里修改你的MP4路径和目标时间
    # --------------------------
    target_mp4_path = r"D:/待分类/test.mp4"  # 你的MP4文件路径
    target_shoot_time = "2025:12:15 14:30:00"  # 目标拍摄时间（格式固定）

    # 读取原始时间（可选，仅用于对比）
    print("=== 读取原始拍摄时间 ===")
    original_metadata = get_video_metadata(target_mp4_path)
    if original_metadata:
        for key, value in original_metadata.items():
            print(f"{key}: {value}")
    else:
        print("未读取到原始时间数据")

    # 执行写入
    print("\n=== 开始写入新拍摄时间 ===")
    success = write_mp4_shoot_time(target_mp4_path, target_shoot_time)

    # 最终结果提示
    print("\n=== 操作完成 ===")
    print(f"成功状态：{'是' if success else '否'}")
    print(f"目标文件：{target_mp4_path}")
    print(f"目标时间：{target_shoot_time}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序运行出错：{str(e)}")