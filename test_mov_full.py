import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from SmartArrangeThread import SmartArrangeThread

class TestSmartArrangeThread(SmartArrangeThread):
    """用于测试的SmartArrangeThread子类，重写log方法"""
    def __init__(self):
        super().__init__()
        # 设置时间派生方式为拍摄日期
        self.time_derive = "拍摄日期"
    
    def log(self, level, message):
        """重写log方法，直接打印到控制台"""
        print(f"[{level}] {message}")

def test_mov_metadata():
    """测试MOV文件元数据读取功能"""
    # 创建测试用的SmartArrangeThread实例
    thread = TestSmartArrangeThread()
    
    # 测试MOV文件路径（请根据实际情况修改）
    mov_file_path = r"D:\待分类\test.MOV"
    
    if not os.path.exists(mov_file_path):
        print(f"测试文件不存在: {mov_file_path}")
        return
    
    print(f"开始测试MOV文件: {mov_file_path}")
    
    # 测试exiftool路径获取
    print("\n测试exiftool路径获取:")
    print("-" * 50)
    exiftool_path = thread.get_exiftool_path()
    print(f"exiftool路径: {exiftool_path}")
    
    # 测试视频元数据读取
    print("\n测试视频元数据读取:")
    print("-" * 50)
    metadata = thread.get_video_metadata(mov_file_path)
    if metadata:
        print("视频元数据:")
        for key, value in list(metadata.items())[:20]:  # 只显示前20项
            print(f"{key}: {value}")
        if len(metadata) > 20:
            print("... (更多元数据省略)")
    else:
        print("未获取到视频元数据")
    
    # 测试关键信息提取
    print("\n测试关键信息提取:")
    print("-" * 50)
    if metadata:
        key_info = thread.extract_video_key_info(metadata)
        print("提取的关键信息:")
        for key, value in key_info.items():
            print(f"{key}: {value}")
    else:
        print("无元数据可提取关键信息")
    
    # 获取EXIF数据
    print("\n提取的EXIF数据:")
    print("-" * 50)
    exif_data = thread.get_exif_data(mov_file_path)
    
    if exif_data:
        for key, value in exif_data.items():
            print(f"{key}: {value}")
    else:
        print("未获取到EXIF数据")

if __name__ == "__main__":
    test_mov_metadata()