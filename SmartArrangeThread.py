import datetime
import io
import json
import os
import time
from pathlib import Path

import exifread
import pillow_heif
import requests
from PIL import Image
from PyQt6 import QtCore

from common import get_resource_path
from config_manager import config_manager

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
                 destination_root=None, separator="-", time_derive="文件创建时间"):
        super().__init__(parent)
        self.parent = parent
        self.folders = folders or []
        self.classification_structure = classification_structure
        self.file_name_structure = file_name_structure  # 现在这是一个包含tag和content的字典列表
        self.destination_root = destination_root
        self.separator = separator
        self.time_derive = time_derive
        self._is_running = True
        self._stop_flag = False  # 添加_stop_flag属性初始化
        self.total_files = 0
        self.processed_files = 0
        self.log_signal = parent.log_signal if parent else None
        self.files_to_rename = []  # 初始化文件重命名列表

    def load_geographic_data(self):
        try:
            with open(get_resource_path('resources/json/City_Reverse_Geocode.json'), 'r', encoding='utf-8') as f:
                self.city_data = json.load(f)
            with open(get_resource_path('resources/json/Province_Reverse_Geocode.json'), 'r', encoding='utf-8') as f:
                self.province_data = json.load(f)
        except Exception as e:
            self.city_data, self.province_data = {'features': []}, {'features': []}

    def run(self):
        try:
            # 加载地理位置数据
            self.load_geographic_data()

            # 记录成功和失败的文件数
            success_count = 0
            fail_count = 0

            for folder_info in self.folders:
                if self._stop_flag:
                    self.log("WARNING", "智能整理操作已被用户中断")
                    break
                if self.destination_root:
                    destination_path = Path(self.destination_root).resolve()
                    folder_path = Path(folder_info['path']).resolve()
                    if len(destination_path.parts) > len(folder_path.parts) and destination_path.parts[
                                                                                :len(
                                                                                    folder_path.parts)] == folder_path.parts:
                        self.log("ERROR", "目标路径不能是待整理文件夹的子路径，这会导致无限循环！")
                        break
                try:
                    if not self.classification_structure and not self.file_name_structure:
                        self.organize_without_classification(folder_info['path'])
                    else:
                        self.process_folder_with_classification(folder_info)
                except Exception as e:
                    self.log("ERROR", f"处理文件夹 {folder_info['path']} 时发生错误: {str(e)}")
                    fail_count += 1
            
            if not self._stop_flag:
                try:
                    self.process_renaming()
                    success_count = len(self.files_to_rename) - fail_count
                except Exception as e:
                    self.log("ERROR", f"文件重命名过程中发生错误: {str(e)}")
                    fail_count += 1
                
                # 整理完成后删除所有空文件夹
                if not self.destination_root:  # 只在移动操作时删除空文件夹
                    try:
                        self.delete_empty_folders()
                    except Exception as e:
                        self.log("WARNING", f"删除空文件夹时发生错误: {str(e)}")
                
                self.log("INFO", f"智能整理操作已完成，共处理 {success_count} 个文件成功，{fail_count} 个文件失败")
            else:
                self.log("WARNING", "智能整理操作已被用户取消")
                
        except Exception as e:
            self.log("ERROR", f"智能整理过程中发生严重错误: {str(e)}")

    def process_folder_with_classification(self, folder_info):
        folder_path = Path(folder_info['path'])
        total_files = sum([len(files) for _, _, files in os.walk(folder_path)]) if folder_info.get('include_sub',
                                                                                                   0) else len(
            os.listdir(folder_path))
        processed_files = 0

        if folder_info.get('include_sub', 0):
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if self._stop_flag:
                        self.log("WARNING", "文件夹处理被用户中断")
                        return
                    full_file_path = Path(root) / file
                    # 移除文件类型过滤，处理所有文件
                    self.process_single_file(full_file_path, base_folder=folder_path)
                    processed_files += 1
                    percent_complete = int((processed_files / total_files) * 100)
                    self.progress_signal.emit(percent_complete)
        else:
            for file in os.listdir(folder_path):
                if self._stop_flag:
                    self.log("WARNING", "文件夹处理被用户中断")
                    return
                full_file_path = folder_path / file
                if full_file_path.is_file():
                    # 移除文件类型过滤，处理所有文件
                    self.process_single_file(full_file_path)
                    processed_files += 1
                    percent_complete = int((processed_files / total_files) * 100)
                    self.progress_signal.emit(percent_complete)

    def process_renaming(self):
        # 记录每个目标路径下的文件名计数，用于确保唯一性
        file_count = {}
        
        for file_info in self.files_to_rename:
            if self._stop_flag:
                self.log("WARNING", "文件重命名操作被用户中断")
                break
            
            old_path = Path(file_info['old_path'])
            new_path = Path(file_info['new_path'])
            
            # 确保目标目录存在
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
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
                    # 移动文件到目标目录（使用shutil.move而不是rename）
                    import shutil
                    shutil.move(old_path, unique_path)
                    self.log("DEBUG", f"移动文件: {old_path} -> {unique_path}")
                
            except Exception as e:
                self.log("ERROR", f"处理文件 {old_path} 时出错: {str(e)}")

    def organize_without_classification(self, folder_path):
        self.log("INFO", f"不进行分类，仅重命名文件在 {folder_path}")
        folder_path = Path(folder_path)
        
        # 添加调试信息
        self.log("DEBUG", f"开始处理文件夹: {folder_path}")
        
        # 递归处理所有子文件夹中的文件
        file_count = 0
        for root, dirs, files in os.walk(folder_path):
            if self._stop_flag:
                self.log("WARNING", "文件提取操作被用户中断")
                break
            
            self.log("DEBUG", f"处理子文件夹: {root}, 文件数: {len(files)}")
            
            for file in files:
                if self._stop_flag:
                    self.log("WARNING", "文件提取操作被用户中断")
                    break
                
                file_path = Path(root) / file
                # 移除文件类型过滤，处理所有文件
                # 将文件从当前子文件夹移动到导入文件夹的顶层目录
                target_path = folder_path / file_path.name
                if file_path != target_path:
                    try:
                        import shutil
                        self.log("DEBUG", f"准备移动文件: {file_path} -> {target_path}")
                        shutil.move(file_path, target_path)
                        self.log("DEBUG", f"成功移动文件: {file_path} -> {target_path}")
                        file_count += 1
                    except Exception as e:
                        self.log("ERROR", f"移动文件 {file_path} 时出错: {str(e)}")
        
        self.log("INFO", f"处理完成，共移动 {file_count} 个文件")

    def delete_empty_folders(self):
        """删除所有处理过的文件夹中的空文件夹"""
        self.log("INFO", "开始删除空文件夹...")
        
        deleted_count = 0
        processed_folders = set()
        
        # 保存所有源文件夹路径，防止误删
        source_folders = [Path(folder_info['path']).resolve() for folder_info in self.folders]
        
        # 收集所有处理过的文件夹路径
        for folder_info in self.folders:
            folder_path = Path(folder_info['path'])
            processed_folders.add(folder_path.resolve())
            
            # 如果包含子文件夹，还需要处理所有子文件夹
            if folder_info.get('include_sub', 0):
                for root, dirs, files in os.walk(folder_path):
                    processed_folders.add(Path(root).resolve())
        
        # 递归删除空文件夹
        for folder in processed_folders:
            if self._stop_flag:
                self.log("WARNING", "空文件夹删除操作被用户中断")
                break
            
            if folder.exists() and folder.is_dir():
                try:
                    # 递归删除空文件夹
                    deleted_in_this_folder = self._recursive_delete_empty_folders(folder, source_folders)
                    deleted_count += deleted_in_this_folder
                except Exception as e:
                    self.log("ERROR", f"删除文件夹 {folder} 时出错: {str(e)}")
        
        self.log("INFO", f"删除空文件夹完成，共删除 {deleted_count} 个空文件夹")
    
    def stop(self):
        """请求停止处理"""
        self._stop_flag = True
        self.log("INFO", "正在停止智能整理操作...")

    def _recursive_delete_empty_folders(self, folder_path, source_folders):
        """递归删除空文件夹"""
        deleted_count = 0
        
        if not folder_path.exists() or not folder_path.is_dir():
            return deleted_count
        
        # 检查是否为源文件夹或系统保护的文件夹
        if self._is_protected_folder(folder_path, source_folders):
            return deleted_count
            
        try:
            # 先递归处理子文件夹
            for item in folder_path.iterdir():
                if item.is_dir():
                    deleted_count += self._recursive_delete_empty_folders(item, source_folders)
            
            # 检查当前文件夹是否为空（不包含任何文件或文件夹）
            if not any(folder_path.iterdir()):
                # 确保不是根目录（避免误删重要文件夹）
                if folder_path != folder_path.resolve().anchor:
                    try:
                        folder_path.rmdir()
                        self.log("DEBUG", f"删除空文件夹: {folder_path}")
                        deleted_count += 1
                    except Exception as e:
                        self.log("WARNING", f"无法删除文件夹 {folder_path}: {str(e)}")
                         
        except PermissionError:
            self.log("WARNING", f"权限不足，无法访问文件夹: {folder_path}")
        except Exception as e:
            self.log("ERROR", f"处理文件夹 {folder_path} 时出错: {str(e)}")
        
        return deleted_count
        
    def _is_protected_folder(self, folder_path, source_folders):
        """检查文件夹是否为用户指定的源文件夹或系统保护的文件夹"""
        # 检查是否为源文件夹
        if folder_path in source_folders:
            return True
            
        # 检查是否为系统目录（Windows系统）
        windows_system_dirs = [
            Path(os.environ.get('WINDIR', 'C:\Windows')),
            Path(os.environ.get('SYSTEMROOT', 'C:\Windows')),
            Path(os.environ.get('ProgramFiles', 'C:\Program Files')),
            Path(os.environ.get('ProgramFiles(x86)', 'C:\Program Files (x86)')),
            Path(os.path.expanduser('~')),  # 用户目录
            Path('C:\\')
        ]
        
        # 规范化路径进行比较
        folder_path = folder_path.resolve()
        for system_dir in windows_system_dirs:
            if system_dir and folder_path.is_relative_to(system_dir):
                return True
                
        return False

    def log(self, level, message):
        current_time = datetime.datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] [{level}] {message}"
        self.log_signal.emit(level, log_message)
    
    def get_exif_data(self, file_path):
        """获取文件的EXIF元数据"""
        exif_data = {}
        file_path_obj = Path(file_path)  # 将文件路径转换为Path对象
        suffix = file_path_obj.suffix.lower()
        create_time = datetime.datetime.fromtimestamp(file_path_obj.stat().st_ctime)
        modify_time = datetime.datetime.fromtimestamp(file_path_obj.stat().st_mtime)
        
        # 添加调试信息
        self.log("DEBUG", f"开始处理文件: {file_path}, 文件类型: {suffix}")
        
        try:
            if suffix in ('.jpg', '.jpeg', '.tiff', '.tif'):
                with open(file_path_obj, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                date_taken = self.parse_exif_datetime(tags)
                lat_ref = str(tags.get('GPS GPSLatitudeRef', '')).strip()
                lon_ref = str(tags.get('GPS GPSLongitudeRef', '')).strip()
                
                # 获取GPS坐标，正确处理坐标格式
                gps_lat = tags.get('GPS GPSLatitude')
                gps_lon = tags.get('GPS GPSLongitude')
                
                if gps_lat and gps_lon:
                    if isinstance(gps_lat, (int, float)) and isinstance(gps_lon, (int, float)):
                        lat = gps_lat
                        lon = gps_lon
                    else:
                        # 转换为十进制度数
                        lat = self.convert_to_degrees(gps_lat)
                        lon = self.convert_to_degrees(gps_lon)
                    
                    if lat and lon:
                        lat = -lat if lat_ref and lat_ref.lower() == 's' else lat
                        lon = -lon if lon_ref and lon_ref.lower() == 'w' else lon
                        exif_data.update({'GPS GPSLatitude': lat, 'GPS GPSLongitude': lon})
                else:
                    self.log("DEBUG", "GPS坐标数据不存在")
                
                make = str(tags.get('Image Make', '')).strip()
                model = str(tags.get('Image Model', '')).strip()
                
                exif_data.update({
                    'Make': make or None,
                    'Model': model or None
                })
            elif suffix == '.heic':
                heif_file = pillow_heif.read_heif(file_path_obj)
                exif_raw = heif_file.info.get('exif', b'')
                if exif_raw.startswith(b'Exif\x00\x00'):
                    exif_raw = exif_raw[6:]
                if exif_raw:
                    tags = exifread.process_file(io.BytesIO(exif_raw), details=False)
                    date_taken = self.parse_exif_datetime(tags)
                    lat_ref = str(tags.get('GPS GPSLatitudeRef', '')).strip()
                    lon_ref = str(tags.get('GPS GPSLongitudeRef', '')).strip()
                    
                    # 获取GPS坐标，正确处理坐标格式
                    gps_lat = tags.get('GPS GPSLatitude')
                    gps_lon = tags.get('GPS GPSLongitude')
                    
                    if gps_lat and gps_lon:
                        # 检查坐标是否为十进制格式
                        if isinstance(gps_lat, (int, float)) and isinstance(gps_lon, (int, float)):
                            lat = gps_lat
                            lon = gps_lon
                        else:
                            # 转换为十进制度数
                            lat = self.convert_to_degrees(gps_lat)
                            lon = self.convert_to_degrees(gps_lon)
                        
                        if lat and lon:
                            lat = -lat if lat_ref and lat_ref.lower() == 's' else lat
                            lon = -lon if lon_ref and lon_ref.lower() == 'w' else lon
                            exif_data.update({'GPS GPSLatitude': lat, 'GPS GPSLongitude': lon})
                    else:
                        self.log("DEBUG", "HEIC文件GPS坐标数据不存在")
                    
                    make = str(tags.get('Image Make', '')).strip()
                    model = str(tags.get('Image Model', '')).strip()
                    
                    exif_data.update({
                        'Make': make or None,
                        'Model': model or None,
                    })
                else:
                    self.log("DEBUG", "HEIC文件没有EXIF数据")
            elif suffix == '.png':
                with Image.open(file_path_obj) as img:
                    # 尝试从PNG元数据中获取创建时间
                    creation_time = img.info.get('Creation Time')
                    if creation_time:
                        date_taken = self.parse_datetime(creation_time)
                    else:
                        date_taken = None
            else:
                date_taken = None
                self.log("DEBUG", f"不支持的文件类型或无EXIF数据: {suffix}")

            # 设置日期时间
            if self.time_derive == "拍摄日期":
                exif_data['DateTime'] = date_taken.strftime('%Y-%m-%d %H:%M:%S') if date_taken else None
            elif self.time_derive == "创建时间":
                exif_data['DateTime'] = create_time.strftime('%Y-%m-%d %H:%M:%S')
            elif self.time_derive == "修改时间":
                exif_data['DateTime'] = modify_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                times = [t for t in [date_taken, create_time, modify_time] if t is not None]
                earliest_time = min(times) if times else modify_time
                exif_data['DateTime'] = earliest_time.strftime('%Y-%m-%d %H:%M:%S')
                
        except Exception as e:
            self.log("DEBUG", f"获取 {file_path} 的EXIF数据时出错: {str(e)}")
            # 出错时使用文件系统时间
            exif_data['DateTime'] = create_time.strftime('%Y-%m-%d %H:%M:%S')
        return exif_data

    def parse_exif_datetime(self, tags):
        """解析EXIF中的日期时间信息"""
        try:
            # 尝试获取DateTimeOriginal（原始拍摄时间）
            datetime_str = str(tags.get('EXIF DateTimeOriginal', ''))
            if datetime_str and datetime_str != 'None':
                return datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
            
            # 尝试获取DateTime（修改时间）
            datetime_str = str(tags.get('Image DateTime', ''))
            if datetime_str and datetime_str != 'None':
                return datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
                
        except (ValueError, TypeError):
            pass
            
        return None

    def parse_datetime(self, datetime_str):
        """解析各种格式的日期时间字符串"""
        if not datetime_str:
            return None
            
        try:
            # 尝试常见格式
            formats = [
                '%Y:%m:%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S', 
                '%Y/%m/%d %H:%M:%S',
                '%Y%m%d%H%M%S',
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y%m%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue
                    
        except (ValueError, TypeError):
            pass
            
        return None

    def get_city_and_province(self, lat, lon):
        """根据经纬度获取省份和城市信息"""
        if not hasattr(self, 'province_data') or not hasattr(self, 'city_data'):
            return "未知省份", "未知城市"

        def is_point_in_polygon(x, y, polygon):
            """判断点是否在多边形内（使用射线法）"""
            if not isinstance(polygon, (list, tuple)) or len(polygon) < 3:
                return False
            
            n = len(polygon)
            inside = False
            
            p1x, p1y = polygon[0]
            for i in range(n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            
            return inside

        def query_location(longitude, latitude, data):
            """查询位置信息"""
            for i, feature in enumerate(data['features']):
                name, coordinates = feature['properties']['name'], feature['geometry']['coordinates']
                polygons = [polygon for multi_polygon in coordinates for polygon in
                            ([multi_polygon] if isinstance(multi_polygon[0][0], (float, int)) else multi_polygon)]
                
                for j, polygon in enumerate(polygons):
                    if is_point_in_polygon(longitude, latitude, polygon):
                        return name

            return None

        # 检查坐标是否为十进制格式
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            lat_deg = lat
            lon_deg = lon
        else:
            # 转换为十进制度数
            lat_deg = self.convert_to_degrees(lat)
            lon_deg = self.convert_to_degrees(lon)
        
        if lat_deg and lon_deg:
            province = query_location(lon_deg, lat_deg, self.province_data)
            city = query_location(lon_deg, lat_deg, self.city_data)

            
            return (
                province if province else "未知省份",
                city if city else "未知城市"
            )
        else:
            return "未知省份", "未知城市"

    @staticmethod
    def get_address(lat, lon, max_retries=3, wait_time_on_limit=2):
        """通过高德地图API获取详细地址，支持缓存机制"""
        # 首先检查缓存中是否有该经纬度的地址
        cached_address = config_manager.get_cached_location(lat, lon)
        if cached_address:
            return cached_address
        
        # 获取用户设置的高德地图API密钥
        user_key = config_manager.get_setting("amap_api_key", "")
        
        # 使用用户配置的API密钥
        keys_to_try = [user_key] if user_key else []
        
        for key in keys_to_try:
            url = f'https://restapi.amap.com/v3/geocode/regeo?key={key}&location={lon},{lat}'
            
            for retry in range(max_retries):
                try:
                    response = requests.get(url, timeout=10).json()
                    if response.get('status') == '1' and response.get('info', '').lower() == 'ok':
                        address = response['regeocode']['formatted_address']
                        # 将获取到的地址保存到缓存中
                        config_manager.cache_location(lat, lon, address)
                        return address
                    elif 'cuqps_has_exceeded_the_limit' in response.get('info', '').lower() and retry < max_retries - 1:
                        time.sleep(wait_time_on_limit)
                    elif 'invalid' in response.get('info', '').lower() or 'invalid_key' in response.get('info', '').lower():
                        # 密钥无效，尝试下一个密钥
                        break
                except Exception as e:
                    pass
                if retry < max_retries - 1:
                    time.sleep(wait_time_on_limit)
        
        return None

    @staticmethod
    def convert_to_degrees(value):
        """将EXIF中的GPS坐标转换为十进制度数"""
        if not value:
            return None
        
        try:
            d = float(value.values[0].num) / float(value.values[0].den)
            m = float(value.values[1].num) / float(value.values[1].den)
            s = float(value.values[2].num) / float(value.values[2].den)
            result = d + (m / 60.0) + (s / 3600.0)

            return result
        except Exception as e:
            return None

    def build_new_file_name(self, file_path, file_time, original_name):
        """构建新的文件名"""
        if not self.file_name_structure:
            return original_name
        
        # 根据选择的标签和顺序构建文件名
        parts = []
        for tag in self.file_name_structure:
            parts.append(self.get_file_name_part(tag, file_path, file_time, original_name))
        
        # 使用分隔符连接各个部分
        return self.separator.join(parts)
        
    def process_single_file(self, file_path, base_folder=None):
        """处理单个文件，根据分类结构和文件名结构决定文件的目标位置和名称"""
        try:
            # 获取文件的EXIF数据
            exif_data = self.get_exif_data(file_path)
            
            # 获取文件时间信息
            file_time = datetime.datetime.strptime(exif_data['DateTime'], '%Y-%m-%d %H:%M:%S') if exif_data.get('DateTime') else None
            
            # 构建目标路径
            target_path = self.build_target_path(file_path, exif_data, file_time, base_folder)
            
            # 构建新的文件名
            original_name = file_path.stem
            new_file_name = self.build_new_file_name(file_path, file_time, original_name)
            
            # 添加文件扩展名
            new_file_name_with_ext = f"{new_file_name}{file_path.suffix}"
            
            # 构建完整的目标路径
            full_target_path = target_path / new_file_name_with_ext
            
            # 记录需要重命名的文件信息
            self.files_to_rename.append({
                'old_path': str(file_path),
                'new_path': str(full_target_path)
            })
            
            self.log("DEBUG", f"处理文件: {file_path.name} -> {full_target_path}")
            
        except Exception as e:
            self.log("ERROR", f"处理文件 {file_path} 时出错: {str(e)}")

    def build_target_path(self, file_path, exif_data, file_time, base_folder):
        """构建文件的目标路径"""
        if not self.classification_structure:
            # 如果没有分类结构，使用原文件夹
            return file_path.parent
        
        # 从基础文件夹开始构建路径
        if base_folder:
            target_path = Path(base_folder)
        else:
            target_path = file_path.parent
        
        # 根据分类结构构建子目录
        for level in self.classification_structure:
            folder_name = self.get_folder_name(level, exif_data, file_time, file_path)
            if folder_name:
                target_path = target_path / folder_name
        
        # 无论用户设置什么分类结构，始终在最终目录下按文件类型分类
        file_type = get_file_type(file_path)
        target_path = target_path / file_type
        
        return target_path

    def get_folder_name(self, level, exif_data, file_time, file_path):
        """根据分类级别获取文件夹名称"""
        if level == "不分类":
            return None
        elif level == "年份" and file_time:
            return str(file_time.year)
        elif level == "月份" and file_time:
            return f"{file_time.month:02d}"
        elif level == "日期" and file_time:
            return f"{file_time.day:02d}"
        elif level == "星期" and file_time:
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return weekdays[file_time.weekday()]
        elif level == "拍摄设备" and exif_data.get('Make'):
            # 拍摄设备：使用相机品牌作为文件夹名称
            return exif_data['Make']
        elif level == "设备品牌" and exif_data.get('Make'):
            return exif_data['Make']
        elif level == "设备型号" and exif_data.get('Model'):
            return exif_data['Model']
        elif level == "拍摄省份" and exif_data.get('GPS GPSLatitude') and exif_data.get('GPS GPSLongitude'):
            province, city = self.get_city_and_province(exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude'])
            return province
        elif level == "拍摄城市" and exif_data.get('GPS GPSLatitude') and exif_data.get('GPS GPSLongitude'):
            province, city = self.get_city_and_province(exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude'])
            return city
        elif level == "文件类型":
            return get_file_type(file_path)
        else:
            # 对于未知的分类级别，使用原文件名或其他默认值
            return "其他"

    def get_file_name_part(self, tag, file_path, file_time, original_name):
        """根据标签获取文件名的组成部分"""
        if isinstance(tag, dict) and 'tag' in tag and 'content' in tag:
            # 处理包含tag和content的字典结构
            tag_name = tag['tag']
            if tag_name == "自定义":
                return tag['content']  # 返回用户输入的自定义内容
            else:
                # 对于其他标签，使用原始逻辑，但保留content信息
                # 如果content不为None，使用content；否则使用原始标签逻辑
                if tag['content'] is not None:
                    return tag['content']
                else:
                    # 对于其他标签，使用原始逻辑
                    tag = tag_name
        
        if tag == "原文件名":
            return original_name
        elif tag == "年份" and file_time:
            return str(file_time.year)
        elif tag == "月份" and file_time:
            return f"{file_time.month:02d}"
        elif tag == "日" and file_time:
            return f"{file_time.day:02d}"
        elif tag == "星期" and file_time:
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return weekdays[file_time.weekday()]
        elif tag == "时间" and file_time:
            return file_time.strftime('%H%M%S')
        elif tag == "品牌":
            exif_data = self.get_exif_data(file_path)
            brand = exif_data.get('Make', '未知品牌')
            return str(brand) if brand is not None else '未知品牌'
        elif tag == "位置":
            exif_data = self.get_exif_data(file_path)
            if exif_data.get('GPS GPSLatitude') and exif_data.get('GPS GPSLongitude'):
                # 使用高德地图API获取详细地址
                address = self.get_address(exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude'])
                if address:
                    return address
                # 如果API调用失败，回退到本地数据
                province, city = self.get_city_and_province(exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude'])
                return f"{province}{city}" if city != "未知城市" else province
            return "未知位置"
        elif tag == "自定义":
            # 这里可以添加自定义标签的处理逻辑
            return "自定义"
        else:
            return ""
        
