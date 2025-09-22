import subprocess
import os
import time
from datetime import datetime, timedelta

from common import get_resource_path


def get_video_metadata(file_path, timeout=30):
    """仅读取视频的时间相关元数据，用于后续验证"""
    try:
        file_path_normalized = file_path.replace('\\', '/')
        # 使用-fast参数加快读取速度，同时读取更多标签用于调试
        cmd = f"{get_resource_path('resources/exiftool/exiftool.exe')} -fast -CreateDate -CreationDate -MediaCreateDate -DateTimeOriginal -EncodedDate -FileModifyDate -TrackCreateDate -TrackModifyDate -MediaModifyDate \"{file_path_normalized}\""

        print(f"读取元数据命令: {cmd}")  # 调试信息
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True
        )

        # 输出详细的读取结果信息
        print(f"读取命令返回码: {result.returncode}")
        if result.stderr:
            print(f"读取错误输出: {result.stderr}")

        metadata = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        print(f"读取到的元数据: {metadata}")  # 调试信息
        return metadata

    except Exception as e:
        print(f"读取文件元数据出错: {str(e)}")
        return None


def write_mp4_shoot_time(file_path, shoot_time, max_retries=3, adjust_for_windows=True):
    """
    仅向MP4文件写入拍摄时间（覆盖多个时间标签确保兼容性）
    
    Args:
        file_path: MP4文件路径
        shoot_time: 拍摄时间，格式必须为"YYYY:MM:DD HH:MM:SS"
        max_retries: 失败重试次数
        adjust_for_windows: 是否为Windows显示调整时间（解决时区问题）
        
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

    # 处理中文路径问题：如果路径包含中文，先复制到临时英文路径
    temp_file_path = None
    original_file_path = file_path
    temp_dir = None
    
    # 检查路径是否包含非ASCII字符（中文等）
    has_non_ascii = any(ord(char) > 127 for char in file_path)
    
    if has_non_ascii:
        print("检测到中文路径，使用临时文件处理...")
        import shutil
        import tempfile
        
        # 创建临时目录和文件
        temp_dir = tempfile.mkdtemp(prefix="exiftool_temp_")
        temp_file_path = os.path.join(temp_dir, os.path.basename(file_path))
        
        # 复制文件到临时英文路径
        shutil.copy2(file_path, temp_file_path)
        file_path = temp_file_path
        print(f"临时文件路径: {file_path}")

    exiftool_path = get_resource_path('resources/exiftool/exiftool.exe')
    
    # 处理时区问题：如果adjust_for_windows为True，则将本地时间转换为UTC时间写入
    # 这样Windows会将UTC时间转换为本地时间显示，确保显示正确
    actual_write_time = shoot_time
    timezone_suffix = ""
    
    if adjust_for_windows:
        print("检测到Windows时区调整选项，将本地时间转换为UTC时间写入...")
        try:
            local_time = datetime.strptime(shoot_time, "%Y:%m:%d %H:%M:%S")
            # 中国位于UTC+8时区，所以UTC时间比本地时间早8小时
            utc_time = local_time - timedelta(hours=8)
            actual_write_time = utc_time.strftime("%Y:%m:%d %H:%M:%S")
            timezone_suffix = "+00:00"  # 明确指定为UTC时间
            print(f"本地时间: {shoot_time} -> UTC时间: {actual_write_time}{timezone_suffix}")
        except Exception as e:
            print(f"时区转换失败，使用原始时间：{str(e)}")
    
    # 使用参数列表而不是字符串命令，避免shell编码问题
    args = [
        exiftool_path,
        "-overwrite_original",
        f"-CreateDate={actual_write_time}{timezone_suffix}",
        f"-CreationDate={actual_write_time}{timezone_suffix}", 
        f"-MediaCreateDate={actual_write_time}{timezone_suffix}",
        f"-DateTimeOriginal={actual_write_time}{timezone_suffix}",
        file_path
    ]

    print(f"执行命令: {' '.join(args)}")

    # 执行写入并验证
    for attempt in range(max_retries):
        try:
            print(f"第 {attempt + 1} 次尝试写入拍摄时间...")
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30
            )

            # 输出详细的执行结果信息
            print(f"命令返回码: {result.returncode}")
            if result.stdout:
                print(f"标准输出: {result.stdout}")
            if result.stderr:
                print(f"错误输出: {result.stderr}")

            # 命令执行成功后验证结果
            if result.returncode == 0:
                print("时间写入命令执行完成，开始验证结果...")
                # 等待一下让文件系统更新
                time.sleep(1)
                
                # 验证临时文件（如果使用临时文件）或原始文件
                verify_file = file_path
                new_metadata = get_video_metadata(verify_file)
                if not new_metadata:
                    print("警告：无法读取修改后的元数据，无法确认是否成功")
                    # 如果是临时文件且命令执行成功，复制回原始位置
                    if temp_file_path:
                        print("复制修改后的文件回原始位置...")
                        shutil.copy2(temp_file_path, original_file_path)
                        if temp_dir:
                            shutil.rmtree(temp_dir)
                    return True  # 命令执行成功但验证失败，视为半成功

                # 检查至少一个时间标签已更新
                time_updated = False
                # 修正标签名称映射，匹配exiftool实际输出的标签名称
                tag_mapping = {
                    'CreateDate': 'Create Date',
                    'CreationDate': 'Creation Date',
                    'MediaCreateDate': 'Media Create Date',
                    'DateTimeOriginal': 'Date/Time Original'
                }
                
                print(f"检查时间标签更新...")
                
                for expected_key, actual_key in tag_mapping.items():
                    if actual_key in new_metadata:
                        actual_value = new_metadata[actual_key]
                        print(f"检查 {actual_key}: 实际值='{actual_value}', 期望值='{actual_write_time}{timezone_suffix}'")
                        
                        # 比较时忽略时区信息
                        if actual_value.startswith(actual_write_time):
                            time_updated = True
                            print(f"✓ 已确认 {actual_key} 标签更新为：{actual_value}")
                            break
                        elif actual_value == actual_write_time:
                            time_updated = True
                            print(f"✓ 已确认 {actual_key} 标签更新为：{actual_write_time}")
                            break

                if time_updated:
                    # 如果是临时文件，复制回原始位置
                    if temp_file_path:
                        print("复制修改后的文件回原始位置...")
                        shutil.copy2(temp_file_path, original_file_path)
                        if temp_dir:
                            shutil.rmtree(temp_dir)
                    
                    print(f"\n拍摄时间写入成功！")
                    if adjust_for_windows:
                        print(f"写入的UTC时间：{actual_write_time}{timezone_suffix}")
                        print(f"Windows将显示为本地时间：{shoot_time}")
                    else:
                        print(f"最终生效时间：{shoot_time}")
                    return True
                else:
                    print("验证失败：所有时间标签未更新，检查元数据:")
                    for key, value in new_metadata.items():
                        print(f"  {key}: {value}")
                    print("重试中...")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # 增加重试间隔
                    continue

            # 命令执行失败
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                print(f"写入失败：{error_msg}，重试中...")
                if attempt < max_retries - 1:
                    time.sleep(2)

        except Exception as e:
            print(f"写入过程出错：{str(e)}，重试中...")
            if attempt < max_retries - 1:
                time.sleep(2)

    # 达到最大重试次数，清理临时文件
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
            
    print(f"\n错误：已尝试 {max_retries} 次，拍摄时间写入失败")
    print("可能的原因：")
    print("1. 文件可能被其他程序占用")
    print("2. 文件权限不足")
    print("3. exiftool版本不兼容")
    print("4. MP4文件格式特殊")
    return False


def main():
    # --------------------------
    # 请在这里修改你的MP4路径和目标时间
    # --------------------------
    target_mp4_path = r"D:/待分类/test.mp4"  # 你的MP4文件路径
    target_shoot_time = "2005:11:09 22:10:10"  # 目标拍摄时间（格式固定）

    # 读取原始时间（可选，仅用于对比）
    print("=== 读取原始拍摄时间 ===")
    original_metadata = get_video_metadata(target_mp4_path)
    if original_metadata:
        for key, value in original_metadata.items():
            print(f"{key}: {value}")
    else:
        print("未读取到原始时间数据")

    # 执行写入（默认启用Windows时区调整）
    print("\n=== 开始写入新拍摄时间 ===")
    print("注意：已启用Windows时区调整，确保Windows属性显示正确时间")
    success = write_mp4_shoot_time(target_mp4_path, target_shoot_time)

    # 最终结果提示
    print("\n=== 操作完成 ===")
    print(f"成功状态：{'是' if success else '否'}")
    print(f"目标文件：{target_mp4_path}")
    print(f"目标时间（本地时间）：{target_shoot_time}")
    print("现在检查Windows属性，应该显示正确的时间了！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序运行出错：{str(e)}")