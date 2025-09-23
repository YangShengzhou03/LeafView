import datetime
import io
import json
import os
import subprocess
from pathlib import Path

import exifread
import pillow_heif
import requests
from PIL import Image
from PyQt6 import QtCore

from common import get_resource_path

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
    '.sqx', '.tar.z', '.uc2', '.uca', '.uha', '.ea', '.yz', '.zap', '.zipx', '.zoo',
    '.zpaq', '.zz'
)

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + AUDIO_EXTENSIONS + DOCUMENT_EXTENSIONS + ARCHIVE_EXTENSIONS

FILE_TYPE_CATEGORIES = {
    '图像': IMAGE_EXTENSIONS,
    '视频': VIDEO_EXTENSIONS,
    '音乐': AUDIO_EXTENSIONS,
    '文档': DOCUMENT_EXTENSIONS,
    '压缩包': ARCHIVE_EXTENSIONS,
    '其他': ()
}

def get_file_type(file_path):
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
        self.file_name_structure = file_name_structure
        self.destination_root = destination_root
        self.separator = separator
        self.time_derive = time_derive
        self._is_running = True
        self._stop_flag = False
        self.total_files = 0
        self.processed_files = 0
        self.log_signal = parent.log_signal if parent else None
        self.files_to_rename = []

    def calculate_total_files(self):
        self.total_files = 0
        for folder_info in self.folders:
            folder_path = Path(folder_info['path'])
            if folder_info.get('include_sub', 0):
                for root, _, files in os.walk(folder_path):
                    self.total_files += len(files)
            else:
                self.total_files += len([f for f in os.listdir(folder_path) if (folder_path / f).is_file()])
        
        self.log("DEBUG", f"总文件数: {self.total_files}")

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
            self.load_geographic_data()
            self.calculate_total_files()
            
            success_count = 0
            fail_count = 0
            self.processed_files = 0

            for folder_info in self.folders:
                if self._stop_flag:
                    self.log("WARNING", "您已经取消了整理文件的操作")
                    break
                if self.destination_root:
                    destination_path = Path(self.destination_root).resolve()
                    folder_path = Path(folder_info['path']).resolve()
                    if len(destination_path.parts) > len(folder_path.parts) and destination_path.parts[:len(folder_path.parts)] == folder_path.parts:
                        self.log("ERROR", "目标文件夹不能是要整理的文件夹的子文件夹，这样会导致重复处理！")
                        break
                try:
                    if not self.classification_structure and not self.file_name_structure:
                        self.organize_without_classification(folder_info['path'])
                    else:
                        self.process_folder_with_classification(folder_info)
                except Exception as e:
                    self.log("ERROR", f"处理文件夹 {folder_info['path']} 时出错了: {str(e)}")
                    fail_count += 1
            
            if not self._stop_flag:
                try:
                    self.process_renaming()
                    success_count = len(self.files_to_rename) - fail_count
                except Exception as e:
                    self.log("ERROR", f"给文件重命名时出错了: {str(e)}")
                    fail_count += 1
                
                if not self.destination_root:
                    try:
                        self.delete_empty_folders()
                    except Exception as e:
                        self.log("WARNING", f"删除空文件夹时出错了: {str(e)}")
                
                self.log("INFO", f"文件整理完成了，成功处理了 {success_count} 个文件，失败了 {fail_count} 个文件")
                self.progress_signal.emit(100)
            else:
                self.log("WARNING", "您已经取消了整理文件的操作")
                
        except Exception as e:
            self.log("ERROR", f"整理文件时遇到了严重问题: {str(e)}")

    def process_folder_with_classification(self, folder_info):
        folder_path = Path(folder_info['path'])
        
        if folder_info.get('include_sub', 0):
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if self._stop_flag:
                        self.log("WARNING", "您已经取消了当前文件夹的处理")
                        return
                    full_file_path = Path(root) / file
                    self.process_single_file(full_file_path, base_folder=folder_path)
                    self.processed_files += 1
                    if self.total_files > 0:
                        percent_complete = int((self.processed_files / self.total_files) * 80)
                        self.progress_signal.emit(percent_complete)
        else:
            for file in os.listdir(folder_path):
                if self._stop_flag:
                    self.log("WARNING", "文件夹处理被用户中断")
                    return
                full_file_path = folder_path / file
                if full_file_path.is_file():
                    self.process_single_file(full_file_path)
                    self.processed_files += 1
                    if self.total_files > 0:
                        percent_complete = int((self.processed_files / self.total_files) * 80)
                        self.progress_signal.emit(percent_complete)

    def process_renaming(self):
        file_count = {}
        total_rename_files = len(self.files_to_rename)
        renamed_files = 0
        
        for file_info in self.files_to_rename:
            if self._stop_flag:
                self.log("WARNING", "文件重命名操作被用户中断")
                break
            
            old_path = Path(file_info['old_path'])
            new_path = Path(file_info['new_path'])
            
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            base_name = new_path.stem
            ext = new_path.suffix
            counter = 1
            unique_path = new_path
            
            while unique_path.exists():
                unique_path = new_path.parent / f"{base_name}_{counter}{ext}"
                counter += 1
            
            try:
                if self.destination_root:
                    import shutil
                    shutil.copy2(old_path, unique_path)
                    self.log("INFO", f"复制文件: {old_path} -> {unique_path}")
                else:
                    if old_path.parent == unique_path.parent:
                        old_path.rename(unique_path)
                        self.log("DEBUG", f"重命名文件: {old_path.name} -> {unique_path.name}")
                    else:
                        import shutil
                        shutil.move(old_path, unique_path)
                        self.log("DEBUG", f"移动文件: {old_path} -> {unique_path}")
                
                renamed_files += 1
                if total_rename_files > 0:
                    rename_progress = int((renamed_files / total_rename_files) * 20)
                    total_progress = 80 + rename_progress
                    self.progress_signal.emit(min(total_progress, 99))
                
            except Exception as e:
                self.log("ERROR", f"处理文件 {old_path} 时出错: {str(e)}")

    def organize_without_classification(self, folder_path):
        folder_path = Path(folder_path)
        
        self.log("DEBUG", f"开始处理文件夹: {folder_path}")
        
        file_count = 0
        for root, dirs, files in os.walk(folder_path):
            if self._stop_flag:
                self.log("WARNING", "文件提取操作被用户中断")
                break
            
            self.log("DEBUG", f"处理子文件夹: {root}, 文件数: {len(files)}")
            
            for file in files:
                if self._stop_flag:
                    self.log("WARNING", "您已经取消了文件提取操作")
                    break
                
                file_path = Path(root) / file
                target_path = folder_path / file_path.name
                if file_path != target_path:
                    try:
                        import shutil
                        self.log("WARNING", f"准备移动文件: {file_path} -> {target_path}")
                        shutil.move(file_path, target_path)
                        self.log("WARNING", f"成功移动文件: {file_path} -> {target_path}")
                        file_count += 1
                        
                        self.processed_files += 1
                        if self.total_files > 0:
                            percent_complete = int((self.processed_files / self.total_files) * 80)
                            self.progress_signal.emit(percent_complete)
                    except Exception as e:
                        self.log("ERROR", f"移动文件 {file_path} 时出错: {str(e)}")
        
        self.log("INFO", f"处理完成，共移动 {file_count} 个文件")

    def delete_empty_folders(self):
        deleted_count = 0
        processed_folders = set()
        
        source_folders = [Path(folder_info['path']).resolve() for folder_info in self.folders]
        
        for folder_info in self.folders:
            folder_path = Path(folder_info['path'])
            processed_folders.add(folder_path.resolve())
            
            if folder_info.get('include_sub', 0):
                for root, dirs, files in os.walk(folder_path):
                    processed_folders.add(Path(root).resolve())
        
        for folder in processed_folders:
            if self._stop_flag:
                self.log("WARNING", "您已经取消了空文件夹删除操作")
                break
            
            if folder.exists() and folder.is_dir():
                try:
                    deleted_in_this_folder = self._recursive_delete_empty_folders(folder, source_folders)
                    deleted_count += deleted_in_this_folder
                except Exception as e:
                    self.log("ERROR", f"删除文件夹 {folder} 时出错: {str(e)}")
        
        self.log("INFO", f"删除空文件夹完成，共删除 {deleted_count} 个空文件夹")
    
    def stop(self):
        self._stop_flag = True
        self.log("INFO", "正在停止智能整理操作...")

    def _recursive_delete_empty_folders(self, folder_path, source_folders):
        deleted_count = 0
        
        if not folder_path.exists() or not folder_path.is_dir():
            return deleted_count
        
        if self._is_protected_folder(folder_path, source_folders):
            return deleted_count
            
        try:
            for item in folder_path.iterdir():
                if item.is_dir():
                    deleted_count += self._recursive_delete_empty_folders(item, source_folders)
            
            if not any(folder_path.iterdir()):
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
        if folder_path in source_folders:
            return True
            
        windows_system_dirs = [
            Path(os.environ.get('WINDIR', 'C:\Windows')),
            Path(os.environ.get('SYSTEMROOT', 'C:\Windows')),
            Path(os.environ.get('ProgramFiles', 'C:\Program Files')),
            Path(os.environ.get('ProgramFiles(x86)', 'C:\Program Files (x86)')),
            Path(os.path.expanduser('~')),
            Path('C:\\')
        ]
        
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
        exif_data = {}
        file_path_obj = Path(file_path)
        suffix = file_path_obj.suffix.lower()
        create_time = datetime.datetime.fromtimestamp(file_path_obj.stat().st_ctime)
        modify_time = datetime.datetime.fromtimestamp(file_path_obj.stat().st_mtime)
        
        self.log("WARNING", f"开始处理文件: {file_path}, 文件类型: {suffix}")
        
        date_taken = None
        
        try:
            if suffix in ('.jpg', '.jpeg', '.tiff', '.tif'):
                date_taken = self._process_image_exif(file_path_obj, exif_data)
            elif suffix == '.heic':
                date_taken = self._process_heic_exif(file_path_obj, exif_data)
            elif suffix == '.png':
                date_taken = self._process_png_exif(file_path_obj)
            elif suffix == '.mov':
                date_taken = self._process_mov_exif(file_path_obj, exif_data)
            elif suffix == '.mp4':
                date_taken = self._process_mp4_exif(file_path_obj, exif_data)
            else:
                self.log("DEBUG", f"不支持的文件类型或无EXIF数据: {suffix}")

            exif_data['DateTime'] = self._determine_best_datetime(
                date_taken, create_time, modify_time
            )
                
        except Exception as e:
            self.log("DEBUG", f"获取 {file_path} 的EXIF数据时出错: {str(e)}")
            exif_data['DateTime'] = create_time.strftime('%Y-%m-%d %H:%M:%S')
        return exif_data

    def _process_image_exif(self, file_path, exif_data):
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        date_taken = self.parse_exif_datetime(tags)
        self._extract_gps_and_camera_info(tags, exif_data)
        return date_taken

    def _process_heic_exif(self, file_path, exif_data):
        heif_file = pillow_heif.read_heif(file_path)
        exif_raw = heif_file.info.get('exif', b'')
        if exif_raw.startswith(b'Exif\x00\x00'):
            exif_raw = exif_raw[6:]
        if exif_raw:
            tags = exifread.process_file(io.BytesIO(exif_raw), details=False)
            date_taken = self.parse_exif_datetime(tags)
            self._extract_gps_and_camera_info(tags, exif_data)
            return date_taken
        else:
            self.log("DEBUG", "HEIC文件没有EXIF数据")
            return None

    def _process_png_exif(self, file_path):
        with Image.open(file_path) as img:
            creation_time = img.info.get('Creation Time')
            if creation_time:
                return self.parse_datetime(creation_time)
        return None

    def _process_mp4_exif(self, file_path, exif_data):
        video_metadata = self._get_video_metadata(file_path)
        if not video_metadata:
            return None
            
        date_taken = None
        date_keys = [
            'Create Date', 'Creation Date', 'Media Create Date', 'Date/Time Original',
            'Track Create Date', 'Creation Date (Windows)', 'Modify Date'
        ]
        
        for key in date_keys:
            if key in video_metadata:
                date_str = video_metadata[key]
                if '+' in date_str or '-' in date_str[-5:]:
                    date_taken = self.parse_datetime(date_str)
                else:
                    try:
                        dt = datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
                        date_taken = utc_dt.astimezone().replace(tzinfo=None)
                    except ValueError:
                        date_taken = self.parse_datetime(date_str)
                if date_taken:
                    break
        
        make_keys = [
            'Make', 'Camera Make', 'Manufacturer', 'Camera Manufacturer'
        ]
        
        for key in make_keys:
            if key in video_metadata:
                make_value = video_metadata[key]
                if make_value:
                    # Remove quotes from camera brand name
                    if isinstance(make_value, str):
                        make_value = make_value.strip().strip('"\'')
                    exif_data['Make'] = make_value
                break
        
        model_keys = [
            'Model', 'Camera Model', 'Device Model', 'Product Name'
        ]
        
        for key in model_keys:
            if key in video_metadata:
                model_value = video_metadata[key]
                if model_value:
                    # Remove quotes from camera model name
                    if isinstance(model_value, str):
                        model_value = model_value.strip().strip('"\'')
                    exif_data['Model'] = model_value
                break
        
        gps_found = False
        for key, value in video_metadata.items():
            if 'gps' in key.lower() or 'location' in key.lower():
                gps_found = True
                if 'Coordinates' in key or 'Position' in key:
                    lat, lon = self._parse_combined_coordinates(value)
                    if lat is not None and lon is not None:
                        exif_data.update({'GPS GPSLatitude': lat, 'GPS GPSLongitude': lon})
                elif 'Latitude' in key:
                    lat = self._parse_dms_coordinate(value)
                    if lat is not None:
                        exif_data['GPS GPSLatitude'] = lat
                elif 'Longitude' in key:
                    lon = self._parse_dms_coordinate(value)
                    if lon is not None:
                        exif_data['GPS GPSLongitude'] = lon
        
        if gps_found and ('GPS GPSLatitude' not in exif_data or 'GPS GPSLongitude' not in exif_data):
            lat = exif_data.get('GPS GPSLatitude')
            lon = exif_data.get('GPS GPSLongitude')
        return date_taken

    def _process_mov_exif(self, file_path, exif_data):
        video_metadata = self._get_video_metadata(file_path)
        if not video_metadata:
            return None
            
        date_taken = None
        
        date_keys = [
            'Create Date', 'Creation Date', 'DateTimeOriginal',
            'Media Create Date', 'Date/Time Original', 'Date/Time Created'
        ]
        
        for key in date_keys:
            if key in video_metadata:
                date_str = video_metadata[key]
                if '+' in date_str or '-' in date_str[-5:]:
                    date_taken = self.parse_datetime(date_str)
                else:
                    try:
                        dt = datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
                        date_taken = utc_dt.astimezone().replace(tzinfo=None)
                    except ValueError:
                        date_taken = self.parse_datetime(date_str)
                
                if date_taken:
                    break
        
        make_keys = [
            'Make', 'Camera Make', 'Manufacturer', 'Camera Manufacturer'
        ]
        
        for key in make_keys:
            if key in video_metadata:
                make_value = video_metadata[key]
                if make_value:
                    # Remove quotes from camera brand name
                    if isinstance(make_value, str):
                        make_value = make_value.strip().strip('"\'')
                    exif_data['Make'] = make_value
                    if not date_taken:
                        date_taken = make_value
                break
        
        model_keys = [
            'Model', 'Camera Model', 'Device Model', 'Product Name'
        ]
        
        for key in model_keys:
            if key in video_metadata:
                model_value = video_metadata[key]
                if model_value:
                    exif_data['Model'] = model_value
                break
        
        gps_found = False
        for key, value in video_metadata.items():
            if 'gps' in key.lower() or 'location' in key.lower():
                gps_found = True
                if 'Coordinates' in key or 'Position' in key:
                    lat, lon = self._parse_combined_coordinates(value)
                    if lat is not None and lon is not None:
                        exif_data.update({'GPS GPSLatitude': lat, 'GPS GPSLongitude': lon})
                elif 'Latitude' in key:
                    lat = self._parse_dms_coordinate(value)
                    if lat is not None:
                        exif_data['GPS GPSLatitude'] = lat
                elif 'Longitude' in key:
                    lon = self._parse_dms_coordinate(value)
                    if lon is not None:
                        exif_data['GPS GPSLongitude'] = lon
        
        if gps_found and ('GPS GPSLatitude' not in exif_data or 'GPS GPSLongitude' not in exif_data):
            lat = exif_data.get('GPS GPSLatitude')
            lon = exif_data.get('GPS GPSLongitude')
            if lat is not None and lon is not None:
                self.log("DEBUG", f"GPS坐标: 纬度={lat}, 经度={lon}")
        return date_taken

    def _determine_best_datetime(self, date_taken, create_time, modify_time):
        if self.time_derive == "拍摄日期":
            return date_taken.strftime('%Y-%m-%d %H:%M:%S') if date_taken else None
        elif self.time_derive == "创建时间":
            return create_time.strftime('%Y-%m-%d %H:%M:%S')
        elif self.time_derive == "修改时间":
            return modify_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            times = [t for t in [date_taken, create_time, modify_time] if t is not None]
            earliest_time = min(times) if times else modify_time
            return earliest_time.strftime('%Y-%m-%d %H:%M:%S')

    def _extract_gps_and_camera_info(self, tags, exif_data):
        lat_ref = str(tags.get('GPS GPSLatitudeRef', '')).strip()
        lon_ref = str(tags.get('GPS GPSLongitudeRef', '')).strip()
        
        gps_lat = tags.get('GPS GPSLatitude')
        gps_lon = tags.get('GPS GPSLongitude')
        
        if gps_lat and gps_lon:
            # 检查GPS数据是否已经是浮点数格式
            if isinstance(gps_lat, (int, float)) and isinstance(gps_lon, (int, float)):
                # 如果是浮点数格式，直接使用
                lat = gps_lat
                lon = gps_lon
            elif hasattr(gps_lat, 'values') and hasattr(gps_lon, 'values'):
                # 如果是EXIF格式的度分秒数据，使用convert_to_degrees方法转换
                lat = self.convert_to_degrees(gps_lat)
                lon = self.convert_to_degrees(gps_lon)
            else:
                # 其他情况，尝试转换为浮点数
                try:
                    lat = float(gps_lat)
                    lon = float(gps_lon)
                except (ValueError, TypeError):
                    lat = None
                    lon = None
            
            if lat is not None and lon is not None:
                # 应用方向参考
                if lat_ref and lat_ref.lower() == 's':
                    lat = -abs(lat)
                elif lat_ref and lat_ref.lower() == 'n':
                    lat = abs(lat)
                    
                if lon_ref and lon_ref.lower() == 'w':
                    lon = -abs(lon)
                elif lon_ref and lon_ref.lower() == 'e':
                    lon = abs(lon)
                
                exif_data.update({'GPS GPSLatitude': lat, 'GPS GPSLongitude': lon})
        
        make = str(tags.get('Image Make', '')).strip()
        model = str(tags.get('Image Model', '')).strip()
        
        # Remove quotes from camera brand and model names
        if isinstance(make, str):
            make = make.strip().strip('"\'')
        if isinstance(model, str):
            model = model.strip().strip('"\'')
        
        exif_data.update({
            'Make': make or None,
            'Model': model or None
        })

    def _get_video_metadata(self, file_path, timeout=30):
        try:
            file_path_normalized = str(file_path).replace('\\', '/')
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
            return None

    def parse_exif_datetime(self, tags):
        try:
            datetime_str = str(tags.get('EXIF DateTimeOriginal', ''))
            if datetime_str and datetime_str != 'None':
                if '+' in datetime_str or '-' in datetime_str[-5:]:
                    try:
                        dt = datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S%z')
                        if dt.tzinfo is not None:
                            dt = dt.astimezone()
                            return dt.replace(tzinfo=None)
                    except ValueError:
                        pass
                
                return datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
            
            datetime_str = str(tags.get('Image DateTime', ''))
            if datetime_str and datetime_str != 'None':
                if '+' in datetime_str or '-' in datetime_str[-5:]:
                    try:
                        dt = datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S%z')
                        if dt.tzinfo is not None:
                            dt = dt.astimezone()
                            return dt.replace(tzinfo=None)
                    except ValueError:
                        pass
                
                return datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
                
        except (ValueError, TypeError):
            pass
            
        return None

    def parse_datetime(self, datetime_str):
        if not datetime_str:
            return None
            
        try:
            formats_with_timezone = [
                '%Y:%m:%d %H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S%z',
                '%Y/%m/%d %H:%M:%S%z',
            ]
            
            formats_without_timezone = [
                '%Y:%m:%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S', 
                '%Y/%m/%d %H:%M:%S',
                '%Y%m%d%H%M%S',
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y%m%d'
            ]
            
            for fmt in formats_with_timezone:
                try:
                    dt = datetime.datetime.strptime(datetime_str, fmt)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone()
                        return dt.replace(tzinfo=None)
                    return dt
                except ValueError:
                    continue
            
            for fmt in formats_without_timezone:
                try:
                    dt = datetime.datetime.strptime(datetime_str, fmt)
                    if 'mov' in fmt.lower() or fmt in ['%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                        import time
                        utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
                        local_dt = utc_dt.astimezone()
                        return local_dt.replace(tzinfo=None)
                    
                    return dt
                except ValueError:
                    continue
        except (ValueError, TypeError) as e:
            pass
            
        return None

    def parse_gps_coordinates(self, gps_info):
        if not gps_info:
            return None, None
            
        for key in ['GPS Coordinates', 'GPS Position']:
            if key in gps_info:
                coords_str = gps_info[key]
                lat, lon = self._parse_combined_coordinates(coords_str)
                if lat is not None and lon is not None:
                    return lat, lon
        
        lat = self._parse_dms_coordinate(gps_info.get('GPS Latitude', ''))
        lon = self._parse_dms_coordinate(gps_info.get('GPS Longitude', ''))
        
        return lat, lon
    
    def _parse_combined_coordinates(self, coords_str):
        try:
            parts = coords_str.split(',')
            if len(parts) == 2:
                lat_str = parts[0].strip()
                lon_str = parts[1].strip()
                
                lat = self._parse_dms_coordinate(lat_str)
                lon = self._parse_dms_coordinate(lon_str)
                
                return lat, lon
        except Exception:
            pass
            
        return None, None
    
    def _parse_dms_coordinate(self, coord_str):
        if not coord_str:
            return None
            
        try:
            direction = None
            for dir_char in ['N', 'S', 'E', 'W']:
                if dir_char in coord_str:
                    direction = dir_char
                    break
            
            clean_str = coord_str
            for char in ['N', 'S', 'E', 'W']:
                clean_str = clean_str.replace(char, '')
            
            clean_str = clean_str.replace('deg', '°').replace('°', ' ').replace("'", ' ').replace('"', ' ')
            
            parts = [p for p in clean_str.split() if p.strip()]
            degrees = minutes = seconds = 0.0
            
            if len(parts) >= 1:
                degrees = float(parts[0])
            if len(parts) >= 2:
                minutes = float(parts[1])
            if len(parts) >= 3:
                seconds = float(parts[2])
            
            decimal = degrees + minutes / 60.0 + seconds / 3600.0
            
            if direction in ['S', 'W']:
                decimal = -decimal
                
            return decimal
            
        except Exception as e:
            return None

    def get_city_and_province(self, lat, lon):
        if not hasattr(self, 'province_data') or not hasattr(self, 'city_data'):
            return "未知省份", "未知城市"

        def is_point_in_polygon(x, y, polygon):
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
            for i, feature in enumerate(data['features']):
                name, coordinates = feature['properties']['name'], feature['geometry']['coordinates']
                polygons = [polygon for multi_polygon in coordinates for polygon in
                            ([multi_polygon] if isinstance(multi_polygon[0][0], (float, int)) else multi_polygon)]
                
                for j, polygon in enumerate(polygons):
                    if is_point_in_polygon(longitude, latitude, polygon):
                        return name

            return None

        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            lat_deg = lat
            lon_deg = lon
        else:
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
    def get_address(latitude: float, longitude: float) -> str:
        if not (isinstance(latitude, (int, float)) and isinstance(longitude, (int, float))):
            return "未知位置"
        
        try:
            user_key = "0db079da53e08cbb62b52a42f657b994"
            
            if not user_key:
                return "未知位置"
            
            url = f"https://restapi.amap.com/v3/geocode/regeo?key={user_key}&location={longitude},{latitude}&extensions=base"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if data.get("status") == "1":
                address = data.get("regeocode", {}).get("formatted_address", "")
                if address:
                    return address
                else:
                    return "未知位置"
            else:
                return "未知位置"
        except Exception as e:
            return "未知位置"

    @staticmethod
    def convert_to_degrees(value):
        if not value:
            return None
        
        # 如果已经是浮点数或整数，直接返回
        if isinstance(value, (int, float)):
            return float(value)
        
        # 如果是字符串，尝试解析为浮点数
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
        
        # 如果是EXIF格式的度分秒数据（包含values属性）
        try:
            if hasattr(value, 'values') and len(value.values) >= 3:
                d = float(value.values[0].num) / float(value.values[0].den)
                m = float(value.values[1].num) / float(value.values[1].den)
                s = float(value.values[2].num) / float(value.values[2].den)
                result = d + (m / 60.0) + (s / 3600.0)
                return result
        except Exception:
            pass
        
        # 其他情况，尝试直接转换为浮点数
        try:
            return float(value)
        except Exception:
            return None

    def build_new_file_name(self, file_path, file_time, original_name, exif_data=None):
        if not self.file_name_structure:
            return original_name
        
        if exif_data is None:
            exif_data = self.get_exif_data(file_path)
        
        parts = []
        for tag in self.file_name_structure:
            parts.append(self.get_file_name_part(tag, file_path, file_time, original_name, exif_data))
        
        return self.separator.join(parts)
        
    def process_single_file(self, file_path, base_folder=None):
        try:
            exif_data = self.get_exif_data(file_path)
            
            file_time = datetime.datetime.strptime(exif_data['DateTime'], '%Y-%m-%d %H:%M:%S') if exif_data.get('DateTime') else None
            
            # 如果有目标根路径（复制操作），则使用它作为base_folder
            if self.destination_root:
                base_folder = self.destination_root
            
            target_path = self.build_target_path(file_path, exif_data, file_time, base_folder)
            
            original_name = file_path.stem
            new_file_name = self.build_new_file_name(file_path, file_time, original_name, exif_data)
            
            new_file_name_with_ext = f"{new_file_name}{file_path.suffix}"
            
            full_target_path = target_path / new_file_name_with_ext
            
            needs_operation = False
            operation_type = "重命名"
            
            if file_path.name != new_file_name_with_ext:
                needs_operation = True
                operation_type = "重命名"
            
            if file_path.parent != target_path:
                needs_operation = True
                operation_type = "移动"
            
            if needs_operation:
                self.files_to_rename.append({
                    'old_path': str(file_path),
                    'new_path': str(full_target_path)
                })
                self.log("DEBUG", f"处理文件: {file_path.name} -> {full_target_path} ({operation_type})")
            else:
                self.log("DEBUG", f"跳过文件: {file_path.name} (无需操作)")
            
        except Exception as e:
            self.log("ERROR", f"处理文件 {file_path} 时出错: {str(e)}")

    def get_file_name_part(self, tag, file_path, file_time, original_name, exif_data=None):
        if isinstance(tag, dict) and 'tag' in tag and 'content' in tag:
            tag_name = tag['tag']
            if tag_name == "自定义":
                return tag['content']  
            else:
                if tag['content'] is not None:
                    return tag['content']
                else:
                    tag = tag_name
        
        if exif_data is None:
            exif_data = self.get_exif_data(file_path)
        
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
            brand = exif_data.get('Make', '未知品牌')
            if isinstance(brand, str):
                brand = brand.strip().strip('"\'')
            return str(brand) if brand is not None else '未知品牌'
        elif tag == "型号":
            model = exif_data.get('Model', '未知型号')
            if isinstance(model, str):
                model = model.strip().strip('"\'')
            return str(model) if model is not None else '未知型号'
        elif tag == "位置":
            if exif_data.get('GPS GPSLatitude') and exif_data.get('GPS GPSLongitude'):
                address = self.get_address(exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude'])
                if address and address != "未知位置":
                    return address
                
                province, city = self.get_city_and_province(exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude'])
                return f"{province}{city}" if city != "未知城市" else province
            return "未知位置"
        elif tag == "自定义":
            return "自定义"
        else:
            return ""

    def build_target_path(self, file_path, exif_data, file_time, base_folder):
        if not self.classification_structure:
            return file_path.parent
        
        if base_folder:
            target_path = Path(base_folder)
        else:
            target_path = file_path.parent
        
        for level in self.classification_structure:
            folder_name = self.get_folder_name(level, exif_data, file_time, file_path)
            if folder_name:
                target_path = target_path / folder_name
        
        file_type = get_file_type(file_path)
        target_path = target_path / file_type
        
        return target_path

    def get_folder_name(self, level, exif_data, file_time, file_path):
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
        
        elif level in ["拍摄设备"]:
            if exif_data.get('Make'):
                make = exif_data['Make']
                if isinstance(make, str):
                    make = make.strip().strip('"\'')
                return make
            else:
                return "未知设备"
        elif level == "相机型号":
            if exif_data.get('Model'):
                model = exif_data['Model']
                if isinstance(model, str):
                    model = model.strip().strip('"\'')
                return model
            else:
                return "未知设备"
        
        elif level == "拍摄省份":
            if exif_data.get('GPS GPSLatitude') and exif_data.get('GPS GPSLongitude'):
                province, _ = self.get_city_and_province(
                    exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude']
                )
                return province
            else:
                return "未知省份"
        elif level == "拍摄城市":
            if exif_data.get('GPS GPSLatitude') and exif_data.get('GPS GPSLongitude'):
                _, city = self.get_city_and_province(
                    exif_data['GPS GPSLatitude'], exif_data['GPS GPSLongitude']
                )
                return city
            else:
                return "未知城市"
        
        elif level == "文件类型":
            return get_file_type(file_path)
        
        else:
            return "未知"