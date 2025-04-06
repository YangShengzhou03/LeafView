from datetime import datetime
from pathlib import Path
import os
import shutil
import json
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image
import exifread
import io
import pillow_heif
from common import get_resource_path

SUPPORTED_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.heic', '.tiff', '.tif',
    '.bmp', '.webp', '.gif', '.svg', '.psd',
    '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
    '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc',
    '.mos', '.iiq', '.fff', '.x3f', '.3fr', '.mef',
    '.mrw', '.erf', '.raw', '.rwz', '.ari',
    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv',
    '.m4v', '.3gp', '.mpeg', '.mpg', '.mts', '.mxf',
    '.webm', '.ogv', '.livp'
)


class ClassificationThread(QThread):
    def __init__(self, parent=None, folders=None, classification_structure=None,
                 file_name_structure=None, destination_root=None, time_derive="最早时间"):
        super().__init__()
        self.parent = parent
        self.folders = folders or []
        self.classification_structure = classification_structure or []
        self.file_name_structure = file_name_structure or []
        self.destination_root = Path(destination_root) if destination_root else None
        self.time_derive = time_derive
        print(folders, classification_structure, file_name_structure, destination_root, time_derive)
        self.total_files = 0
        self.processed_files = 0
        self.processed_files_set = set()
        self._stop_flag = False
        self.load_geographic_data()

    def load_geographic_data(self):
        try:
            city_path = get_resource_path('resources/json/City_Reverse_Geocode.json')
            province_path = get_resource_path('resources/json/Province_Reverse_Geocode.json')

            with open(city_path, 'r', encoding='utf-8') as f:
                self.city_data = json.load(f)
            with open(province_path, 'r', encoding='utf-8') as f:
                self.province_data = json.load(f)
        except Exception as e:
            print(f"加载地理数据失败: {str(e)}")
            self.city_data = {'features': []}
            self.province_data = {'features': []}

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.total_files = sum(
                1 for folder_info in self.folders for root, _, files in os.walk(Path(folder_info['path']))
                for file in files if file.lower().endswith(SUPPORTED_EXTENSIONS)
            )
            for folder_info in self.folders:
                if self._stop_flag:
                    break

                if not self.classification_structure and not self.file_name_structure:
                    self.organize_without_classification(folder_info['path'])
                else:
                    self.process_folder_with_classification(folder_info)
        except Exception as e:
            print(f"线程运行时发生错误: {str(e)}")

    def count_total_files(self):
        return sum(
            1 for folder in self.folders
            for _, _, files in os.walk(folder)
            for file in files
            if file.lower().endswith(SUPPORTED_EXTENSIONS)
        )

    def process_folder_with_classification(self, folder_info):
        folder_path = Path(folder_info['path'])
        include_sub = folder_info.get('include_sub', 0)

        if include_sub:
            for root, _, files in os.walk(folder_path):
                if self._stop_flag:
                    break
                for file in files:
                    if self._stop_flag:
                        break
                    full_file_path = Path(root) / file
                    if full_file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        self.process_single_file(full_file_path)
        else:
            for file in os.listdir(folder_path):
                full_file_path = folder_path / file
                if full_file_path.is_file() and full_file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    self.process_single_file(full_file_path)

    def process_single_file(self, file_path):
        try:
            exif_data = self.get_exif_data(file_path)
            if self.classification_structure:
                new_path = self.construct_classification_path(exif_data, file_path)
                if new_path:
                    self.copy_or_move_image(file_path, new_path)
            if self.file_name_structure:
                new_name = self.construct_new_filename(exif_data)
                if new_name:
                    new_path = file_path.parent / f"{new_name}{file_path.suffix}"
                    os.rename(file_path, new_path)
                    print(f"重命名成功: {file_path.name} -> {new_path.name}")
        except Exception as e:
            print(f"处理文件 {file_path.name} 时出错: {str(e)}")
        finally:
            print("sha")
            

    def construct_classification_path(self, exif_data, file_path):
        structure_parts = []
        for part in self.classification_structure:
            if part == "拍摄设备":
                make = exif_data.get('Make', '')
                model = exif_data.get('Model', '')
                device_info = f"{make} {model}".strip() or '未知设备'
                structure_parts.append(device_info)
            elif part in ["拍摄省份", "拍摄城市"]:
                lat = exif_data.get('GPS GPSLatitude')
                lon = exif_data.get('GPS GPSLongitude')
                if lat and lon:
                    province, city = self.get_city_and_province(lat, lon)
                    structure_parts.append(province if part == "拍摄省份" else city)
                else:
                    structure_parts.append('未知位置')
            elif part == "年份":
                date_str = exif_data.get('DateTime')
                if date_str:
                    try:
                        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        structure_parts.append(str(date.year))
                    except ValueError:
                        structure_parts.append("未知年份")
                else:
                    structure_parts.append("未知年份")
            elif part == "月份":
                date_str = exif_data.get('DateTime')
                if date_str:
                    try:
                        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        structure_parts.append(f"{date.month:02d}")
                    except ValueError:
                        structure_parts.append("未知月份")
                else:
                    structure_parts.append("未知月份")
            else:
                structure_parts.append(part)

        base_folder = self.destination_root if self.destination_root else file_path.parent
        new_folder = base_folder.joinpath(*structure_parts)
        new_folder.mkdir(parents=True, exist_ok=True)
        return self.make_unique_filename(new_folder, file_path.name)

    def construct_new_filename(self, exif_data):
        parts = []
        date_str = exif_data.get('DateTime')
        for part in self.file_name_structure:
            if part == "年份" and date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    parts.append(str(date.year))
                except ValueError:
                    pass
            elif part == "月份" and date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    parts.append(f"{date.month:02d}")
                except ValueError:
                    pass
            elif part == "日" and date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    parts.append(f"{date.day:02d}")
                except ValueError:
                    pass
            elif part == "星期" and date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    parts.append(self._get_weekday(date))
                except ValueError:
                    pass
            elif part == "时间" and date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    parts.append(date.strftime('%H%M'))
                except ValueError:
                    pass
            elif part == "位置":
                lat = exif_data.get('GPS GPSLatitude')
                lon = exif_data.get('GPS GPSLongitude')
                if lat and lon:
                    _, city = self.get_city_and_province(lat, lon)
                    parts.append(city or "未知位置")
            elif part == "品牌":
                parts.append(exif_data.get('Make', '未知品牌'))
            elif part == "型号":
                parts.append(exif_data.get('Model', '未知型号'))
        return "-".join(parts) if parts else None

    def get_exif_data(self, file_path):
        exif_data = {}
        suffix = file_path.suffix.lower()

        create_time = datetime.fromtimestamp(file_path.stat().st_ctime)
        modify_time = datetime.fromtimestamp(file_path.stat().st_mtime)

        if suffix in ('.jpg', '.jpeg', '.tiff', '.tif'):
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            date_taken = self.parse_exif_datetime(tags)

            lat_ref = str(tags.get('GPS GPSLatitudeRef', '')).strip()
            lon_ref = str(tags.get('GPS GPSLongitudeRef', '')).strip()
            lat = self.convert_to_degrees(tags.get('GPS GPSLatitude'))
            lon = self.convert_to_degrees(tags.get('GPS GPSLongitude'))

            if lat and lon:
                lat = -lat if lat_ref.lower() == 's' else lat
                lon = -lon if lon_ref.lower() == 'w' else lon
                exif_data['GPS GPSLatitude'] = lat
                exif_data['GPS GPSLongitude'] = lon

            exif_data['Make'] = str(tags.get('Image Make', '')).strip() or None
            exif_data['Model'] = str(tags.get('Image Model', '')).strip() or None

        elif suffix == '.heic':
            heif_file = pillow_heif.read_heif(file_path)
            exif_raw = heif_file.info.get('exif', b'')
            if exif_raw.startswith(b'Exif\x00\x00'):
                exif_raw = exif_raw[6:]
            tags = exifread.process_file(io.BytesIO(exif_raw), details=False)
            date_taken = self.parse_exif_datetime(tags)

        elif suffix == '.png':
            with Image.open(file_path) as img:
                date_taken = self.parse_datetime(img.info.get('Creation Time'))
        else:
            date_taken = None

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

        return exif_data

    def parse_exif_datetime(self, tags):
        for tag in ['EXIF DateTimeOriginal', 'Image DateTime']:
            if tag in tags:
                return self.parse_datetime(str(tags[tag]))
        return None

    def parse_datetime(self, datetime_str):
        formats = [
            '%Y:%m:%d %H:%M:%S',
            '%Y:%m:%d %H:%M',
            '%Y:%m:%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except (ValueError, TypeError):
                continue
        return None

    def get_city_and_province(self, lat, lon):
        def is_point_in_polygon(x, y, polygon):
            n = len(polygon)
            inside = False
            p1x, p1y = polygon[0]
            for i in range(n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                    x_intercept = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x if p1y != p2y else p1x
                    if p1x == p2x or x <= x_intercept:
                        inside = not inside
                p1x, p1y = p2x, p2y
            return inside
        for feature in self.province_data['features']:
            province_name = feature['properties']['name']
            for polygon in feature['geometry']['coordinates']:
                if is_point_in_polygon(lon, lat, polygon):
                    for city_feature in self.city_data['features']:
                        city_name = city_feature['properties']['name']
                        for city_polygon in city_feature['geometry']['coordinates']:
                            if is_point_in_polygon(lon, lat, city_polygon):
                                return province_name, city_name
                    return province_name, '未知城市'
        return '未知省份', '未知城市'

    def convert_to_degrees(self, value):
        try:
            if not value:
                return None
            d = float(value.values[0].num) / float(value.values[0].den)
            m = float(value.values[1].num) / float(value.values[1].den)
            s = float(value.values[2].num) / float(value.values[2].den)
            return d + (m / 60.0) + (s / 3600.0)
        except Exception:
            return None

    def copy_or_move_image(self, src_path, dst_path):
        try:
            if str(src_path.parent) == str(dst_path.parent):
                return

            if self.destination_root is not None:
                if str(src_path) in self.processed_files_set:
                    return
                shutil.copy2(str(src_path), str(dst_path))
                self.processed_files_set.add(str(src_path))
                print(f"复制成功: {src_path} -> {dst_path}", "INFO")
            else:
                shutil.move(str(src_path), str(dst_path))
                print(f"移动成功: {src_path} -> {dst_path}", "INFO")
        except Exception as e:
            print(f"文件操作失败: {src_path}, 错误: {str(e)}", "ERROR")

    def organize_without_classification(self, folder):
        destination = self.destination_root if self.destination_root else Path(folder)

        for current_dir, _, files in os.walk(folder, topdown=False):
            dir_path = Path(current_dir)
            has_files_remaining = False

            for file in files:
                if file.lower().endswith(SUPPORTED_EXTENSIONS):
                    src_path = dir_path / file
                    dst_path = self.make_unique_filename(destination, file)

                    try:
                        self.copy_or_move_image(src_path, dst_path)
                        
                    except Exception as e:
                        print(f"处理文件 {src_path} 时出错: {str(e)}", "ERROR")
                        
                        has_files_remaining = True
            if not has_files_remaining and not any(dir_path.iterdir()) and dir_path != Path(folder):
                try:
                    dir_path.rmdir()
                    print(f"删除空目录: {dir_path}", "INFO")
                except OSError as e:
                    print(f"无法删除目录 {dir_path}: {str(e)}", "WARNING")

    def make_unique_filename(self, target_dir, filename):
        base, ext = os.path.splitext(filename)
        target_path = target_dir / filename
        counter = 1
        while target_path.exists():
            new_name = f"{base}_{counter}{ext}"
            target_path = target_dir / new_name
            counter += 1
        return target_path

    @staticmethod
    def _get_weekday(date):
        """Get Chinese weekday name."""
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays[date.weekday()]