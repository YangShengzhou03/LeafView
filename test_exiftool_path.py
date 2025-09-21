import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from SmartArrangeThread import SmartArrangeThread

class TestSmartArrangeThread(SmartArrangeThread):
    """用于测试的SmartArrangeThread子类，重写log方法"""
    def log(self, level, message):
        """重写log方法，直接打印到控制台"""
        print(f"[{level}] {message}")

def test_exiftool_path():
    """测试exiftool路径获取功能"""
    # 创建测试用的SmartArrangeThread实例
    thread = TestSmartArrangeThread()
    
    print("测试exiftool路径获取:")
    print("-" * 50)
    exiftool_path = thread.get_exiftool_path()
    print(f"exiftool路径: {exiftool_path}")
    
    if exiftool_path:
        # 移除引号以检查实际路径
        actual_path = exiftool_path.strip('"')
        print(f"实际路径: {actual_path}")
        print(f"文件存在: {os.path.exists(actual_path)}")
    else:
        print("获取exiftool路径失败")

if __name__ == "__main__":
    test_exiftool_path()