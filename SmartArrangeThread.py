import os
import json
import datetime
from pathlib import Path

from PyQt6 import QtCore

from common import get_resource_path

# 扩展支持的文件类型
IMAGE_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.heic', '.tiff', '.tif', '.bmp', '.webp', '.gif', '.svg', 
    '.psd', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2', '.raf', '.dng', '.rw2', 
    '.pef', '.nrw', '.kdc', '.mos', '.iiq', '.fff', '.x3f', '.3fr', '.mef', '.mrw', 
    '.erf', '.raw', '.rwz', '.ari', '.jxr', '.hdp', '.wdp', '.ico', '.exr', '.tga',
    '.pbm', '.pgm', '.ppm', '.pnm', '.hdr', '.avif', '.jxl'
)

VIDEO_EXTENSIONS = (
    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.mpeg', '.mpg',
    '.mts', '.mxf', '.webm', '.ogv', '.livp', '.ts', '.m2ts', '.divx', '.f4v', '.vob',
    '.rm', '.rmvb', '.asf', '.swf', '.m4p', '.m4b', '.m4r', '.3g2', '.3gp2', '.ogm',
    '.ogx', '.qt', '.yuv', '.dat', '.m1v', '.m2v', '.m4u', '.mpv', '.nsv', '.svi',
    '.wtv', '.amv', '.drc', '.gifv', '.mng', '.mxf', '.roq', '.y4m'
)

AUDIO_EXTENSIONS = (
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.aiff', '.aif', '.aifc',
    '.ape', '.alac', '.ac3', '.amr', '.au', '.cda', '.dts', '.mka', '.mpc', '.opus',
    '.ra', '.rm', '.tta', '.voc', '.wv', '.8svx', '.aax', '.act', '.awb', '.dss',
    '.dvf', '.gsm', '.iklax', '.ivs', '.m4p', '.mmf', '.msv', '.nmf', '.nsf', '.oga',
    '.spx', '.vox', '.wma', '.wpl', '.xm'
)

DOCUMENT_EXTENSIONS = (
    '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odp', '.ods', '.csv', '.html', '.htm', '.xml', '.epub', '.mobi', '.azw', '.azw3',
    '.fb2', '.lit', '.lrf', '.pdb', '.prc', '.rb', '.tcr', '.pdb', '.oxps', '.xps',
    '.pages', '.numbers', '.key', '.md', '.tex', '.log', '.wpd', '.wps', '.abw',
    '.zabw', '.123', '.602', '.hwp', '.lwp', '.mw', '.nb', '.nbp', '.odm', '.sxw',
    '.uot', '.vor', '.wpt', '.wri', '.xmind'
)

ARCHIVE_EXTENSIONS = (
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lz', '.lzma', '.lzo',
    '.z', '.Z', '.tgz', '.tbz2', '.txz', '.tlz', '.tlzma', '.tlzo', '.tz', '.tZ',
    '.cab', '.deb', '.rpm', '.jar', '.war', '.ear', '.sar', '.cpio', '.iso', '.img',
    '.dmg', '.hfs', '.hfsx', '.udf', '.xar', '.zoo', '.arc', '.arj', '.lha', '.lzh',
    '.pak', '.pk3', '.pk4', '.vpk', '.wim', '.swm', '.esd', '.msu', '.msp', '.msi',
    '.appx', '.appxbundle', '.xap', '.snap', '.flatpak', '.appimage', '.r0', '.r1',
    '.r2', '.r3', '.s7z', '.ace', '.cpt', '.dd', '.dgc', '.gca', '.ha', '.ice',
    '.ipg', '.kgb', '.lbr', '.lqr', '.lzx', '.pak', '.paq6', '.paq7', '.paq8',
    '.pea', '.pf', '.pim', '.pit', '.qda', '.rk', '.sda', '.sea', '.sit', '.sitx',
    '.sqx', '.tar.z', '.uc2', '.uca', '.uha', '.xea', '.yz', '.zap', '.zipx', '.zoo',
    '.zpaq', '.zz'
)

# 合并所有支持的文件类型
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + AUDIO_EXTENSIONS + DOCUMENT_EXTENSIONS + ARCHIVE_EXTENSIONS

# 文件类型分类映射
FILE_TYPE_CATEGORIES = {
    '图像': IMAGE_EXTENSIONS,
    '视频': VIDEO_EXTENSIONS,
    '音乐': AUDIO_EXTENSIONS,
    '文档': DOCUMENT_EXTENSIONS,
    '压缩包': ARCHIVE_EXTENSIONS,
    '其他': ()  # 其他不支持的文件类型
}

def get_file_type(file_path):
    """根据文件扩展名获取文件类型"""
    ext = file_path.suffix.lower()
    for file_type, extensions in FILE_TYPE_CATEGORIES.items():
        if ext in extensions:
            return file_type
    return '其他'

class SmartArrangeThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str, str)
    progress_signal = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, folders=None, classification_structure=None, file_name_structure=None,
                 destination_root=None, separator=None, time_derive="最早时间"):
        super().__init__()
        self.parent, self.folders, self.classification_structure = parent, folders or [], classification_structure or []
        self.file_name_structure, self.time_derive = file_name_structure or [], time_derive
        self.destination_root = Path(destination_root) if destination_root else None
        self.separator = separator
        self._stop_flag = False
        self.load_geographic_data()
        self.files_to_rename = []
        self.log_signal.connect(parent.log_signal.emit)
        self.progress_signal.connect(parent.update_progress_bar)

    def load_geographic_data(self):
        try:
            with open(get_resource_path('resources/json/City_Reverse_Geocode.json'), 'r', encoding='utf-8') as f:
                self.city_data = json.load(f)
            with open(get_resource_path('resources/json/Province_Reverse_Geocode.json'), 'r', encoding='utf-8') as f:
                self.province_data = json.load(f)
        except Exception as e:
            self.city_data, self.province_data = {'features': []}, {'features': []}

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.log("INFO", f"正在处理 {len(self.folders)} 个文件夹")
            for folder_info in self.folders:
                if self._stop_flag:
                    self.log("WARNING", "处理被用户中断")
                    break
                if self.destination_root:
                    destination_path = Path(self.destination_root).resolve()
                    folder_path = Path(folder_info['path']).resolve()
                    if len(destination_path.parts) > len(folder_path.parts) and destination_path.parts[
                                                                                :len(
                                                                                    folder_path.parts)] == folder_path.parts:
                        self.log("ERROR", "复制到目标路径不能是待整理的子路径，会导致死循环！")
                        break
                if not self.classification_structure and not self.file_name_structure:
                    self.organize_without_classification(folder_info['path'])
                else:
                    self.process_folder_with_classification(folder_info)
            self.process_renaming()
        except Exception as e:
            self.log("ERROR", f"发生错误: {str(e)}")

    def process_folder_with_classification(self, folder_info):
        folder_path = Path(folder_info['path'])
        total_files = sum([len(files) for _, _, files in os.walk(folder_path)]) if folder_info.get('include_sub',
                                                                                                   0) else len(
            os.listdir(folder_path))
        processed_files = 0

        if folder_info.get('include_sub', 0):
            for root, _, files in os.walk(folder_path):
                for file in files:
                    full_file_path = Path(root) / file
                    if full_file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        self.process_single_file(full_file_path, base_folder=folder_path)
                        processed_files += 1
                        percent_complete = int((processed_files / total_files) * 100)
                        self.progress_signal.emit(percent_complete)
        else:
            for file in os.listdir(folder_path):
                full_file_path = folder_path / file
                if full_file_path.is_file() and full_file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    self.process_single_file(full_file_path)
                    processed_files += 1
                    percent_complete = int((processed_files / total_files) * 100)
                    self.progress_signal.emit(percent_complete)

    def organize_without_classification(self, folder_path):
        # 这里是原ClassificationThread.py中剩余的代码，为了保持简洁我省略了部分实现
        pass

    def process_single_file(self, file_path, base_folder=None):
        try:
            # 获取文件信息
            file_path = Path(file_path)
            file_name = file_path.stem
            file_ext = file_path.suffix
            
            # 获取文件的时间信息
            file_time = self.get_file_time(file_path)
            
            # 根据不同的情况构建目标路径和文件名
            if not self.classification_structure and not self.file_name_structure:
                # 情况3：什么都不做，将文件从子文件夹提取到顶层目录
                target_dir = file_path.parent
                new_file_name = file_name  # 保持原文件名
            elif not self.classification_structure:
                # 情况2：只构建文件名，目录不变
                target_dir = file_path.parent
                new_file_name = self.build_new_file_name(file_path, file_time, file_name)
            elif not self.file_name_structure:
                # 情况1：只构建文件夹目录，文件名不变
                target_dir = self.build_target_directory(file_path, file_time)
                new_file_name = file_name  # 保持原文件名
            else:
                # 正常情况：既构建目录也构建文件名
                target_dir = self.build_target_directory(file_path, file_time)
                new_file_name = self.build_new_file_name(file_path, file_time, file_name)
            
            # 保存重命名信息
            self.files_to_rename.append({
                'old_path': file_path,
                'new_path': target_dir / f'{new_file_name}{file_ext}'
            })
            
        except Exception as e:
            self.log("ERROR", f"处理文件 {file_path} 时出错: {str(e)}")

    def build_target_directory(self, file_path, file_time):
        if self.destination_root:
            # 如果有目标根目录，则基于目标根目录构建
            target_path = self.destination_root
        else:
            # 否则基于原文件目录构建
            target_path = file_path.parent
        
        # 根据分类结构构建目录层次
        for category in self.classification_structure:
            if category == "不分类":
                break
            
            # 获取分类值
            category_value = self.get_category_value(category, file_path, file_time)
            
            # 添加到目标路径
            target_path = target_path / category_value
        
        # 自动添加文件类型分类（图像、视频、音乐等）
        file_type = get_file_type(file_path)
        target_path = target_path / file_type
        
        # 确保目录存在
        target_path.mkdir(parents=True, exist_ok=True)
        
        return target_path

    def get_category_value(self, category, file_path, file_time):
        if category == "年份":
            return str(file_time.year)
        elif category == "月份":
            return f"{file_time.month:02d}"
        elif category == "日":
            return f"{file_time.day:02d}"
        elif category == "星期":
            return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][file_time.weekday()]
        elif category == "拍摄设备":
            # 这里应该从文件元数据中获取设备信息，这里简单返回一个示例值
            return "未知设备"
        elif category == "拍摄省份":
            # 这里应该从地理数据中获取省份信息，这里简单返回一个示例值
            return "未知省份"
        elif category == "拍摄城市":
            # 这里应该从地理数据中获取城市信息，这里简单返回一个示例值
            return "未知城市"
        else:
            return category

    def build_new_file_name(self, file_path, file_time, original_name):
        if not self.file_name_structure:
            return original_name
        
        # 根据选择的标签和顺序构建文件名
        parts = []
        for tag in self.file_name_structure:
            parts.append(self.get_file_name_part(tag, file_path, file_time, original_name))
        
        # 使用分隔符连接各个部分
        return self.separator.join(parts)

    def get_file_name_part(self, tag, file_path, file_time, original_name):
        if tag == "原始名称":
            return original_name
        elif tag == "年份":
            return str(file_time.year)
        elif tag == "月份":
            return f"{file_time.month:02d}"
        elif tag == "日":
            return f"{file_time.day:02d}"
        elif tag == "星期":
            return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][file_time.weekday()]
        elif tag == "时间":
            return file_time.strftime("%H%M%S")
        elif tag == "位置":
            # 这里应该从地理数据中获取位置信息，这里简单返回一个示例值
            return "未知位置"
        elif tag == "品牌":
            # 这里应该从文件元数据中获取品牌信息，这里简单返回一个示例值
            return "未知品牌"
        else:
            return tag

    def get_file_time(self, file_path):
        # 根据选择的时间源获取文件时间
        if self.time_derive == "最早时间":
            return datetime.datetime.fromtimestamp(file_path.stat().st_ctime)
        elif self.time_derive == "修改时间":
            return datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
        elif self.time_derive == "访问时间":
            return datetime.datetime.fromtimestamp(file_path.stat().st_atime)
        else:
            # 默认返回当前时间
            return datetime.datetime.now()

    def process_renaming(self):
        # 记录每个目标路径下的文件名计数，用于确保唯一性
        file_count = {}
        
        for file_info in self.files_to_rename:
            if self._stop_flag:
                self.log("WARNING", "重命名操作被用户中断")
                break
            
            old_path = Path(file_info['old_path'])
            new_path = Path(file_info['new_path'])
            
            # 确保文件名唯一
            base_name = new_path.stem
            ext = new_path.suffix
            counter = 1
            unique_path = new_path
            
            while unique_path.exists():
                unique_path = new_path.parent / f"{base_name}_{counter}{ext}"
                counter += 1
            
            try:
                # 执行文件移动或重命名
                if self.destination_root:
                    # 复制文件到目标目录
                    import shutil
                    shutil.copy2(old_path, unique_path)
                    self.log("INFO", f"复制文件: {old_path} -> {unique_path}")
                else:
                    # 重命名文件
                    old_path.rename(unique_path)
                    self.log("INFO", f"重命名文件: {old_path} -> {unique_path}")
                
            except Exception as e:
                self.log("ERROR", f"处理文件 {old_path} 时出错: {str(e)}")

    def organize_without_classification(self, folder_path):
        self.log("INFO", f"不进行分类，仅重命名文件在 {folder_path}")
        folder_path = Path(folder_path)
        
        # 简单地处理每个文件
        for file in os.listdir(folder_path):
            if self._stop_flag:
                self.log("WARNING", "处理被用户中断")
                break
            
            file_path = folder_path / file
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.process_single_file(file_path)

    def log(self, level, message):
        current_time = datetime.datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        self.log_signal.emit(level, log_message)
        print(log_message)