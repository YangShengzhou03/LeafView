import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import exifread
import pillow_heif
import requests
from PIL import Image
from PyQt6 import QtCore
from scipy import io

from common import get_resource_path, detect_media_type

SUPPORTED_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.heic', '.tiff', '.tif', '.bmp', '.webp', '.gif', '.svg', '.psd', '.arw', '.cr2', '.cr3',
    '.nef', '.orf', '.sr2', '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc', '.mos', '.iiq', '.fff', '.x3f', '.3fr',
    '.mef',
    '.mrw', '.erf', '.raw', '.rwz', '.ari', '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.mpeg',
    '.mpg',
    '.mts', '.mxf', '.webm', '.ogv', '.livp')
_ocr_model = None


# def init_ocr_model():
#     global _ocr_model
#     if _ocr_model is None:
#         _ocr_model = paddleocr.PaddleOCR(
#             use_angle_cls=True,
#             lang="ch",
#             use_gpu=True,
#             det_db_box_thresh=0.1,
#             use_dilation=True,
#             det_model_dir='weight/ch_PP-OCRv4_det_server_infer',
#             cls_model_dir='weight/ch_ppocr_mobile_v2.0_cls_infer',
#             rec_model_dir='weight/ch_PP-OCRv4_rec_server_infer'
#         )
#
#
# init_ocr_model()


class ClassificationThread(QtCore.QThread):
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
            self.log("INFO", f"开始处理 {len(self.folders)} 个文件夹")
            for folder_info in self.folders:
                if self._stop_flag:
                    self.log("WARNING", "处理被用户中断")
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
        self.delete_empty_folders(folder_path)

    def process_single_file(self, file_path, base_folder=None):
        try:
            exif_data = self.get_exif_data(file_path)
            new_path = None
            if self.classification_structure:
                new_path = self.construct_classification_path(exif_data, file_path, base_folder)
                if new_path:
                    self.copy_or_move_image(file_path, new_path)
            if self.file_name_structure:
                target_path = new_path if new_path else file_path
                self.files_to_rename.append((target_path, exif_data))
        except Exception as e:
            result = detect_media_type(file_path)
            if not result["valid"]:
                self.log("ERROR", f"{file_path}文件已损坏")
            elif not result["extension_match"]:
                self.log("ERROR", f"扩展名不匹配，{file_path}正确的格式是{result['extension']}")
            else:
                self.log("ERROR", f"{file_path}发生未知故障")

    def process_renaming(self):
        for file_path, exif_data in self.files_to_rename:
            try:
                if self._stop_flag:
                    return
                new_name = self.construct_new_filename(exif_data, file_path)
                if new_name:
                    os.rename(file_path, new_name)
            except Exception as e:
                print(e)
                result = detect_media_type(file_path)
                if not result["valid"]:
                    self.log("ERROR", f"{file_path}文件已损坏")
                elif not result["extension_match"]:
                    self.log("ERROR", f"扩展名不匹配，{file_path}正确的格式是{result['extension']}")
                else:
                    self.log("ERROR", f"{file_path}出错{e}")

    def construct_classification_path(self, exif_data, file_path, base_folder=None):
        structure_parts = []
        for part in self.classification_structure:
            if part == "拍摄设备":
                make, model = exif_data.get('Make', ''), exif_data.get('Model', '')
                device = f"{make} {model}".strip() or '未知设备'
                structure_parts.append(device)
            elif part in ["拍摄省份", "拍摄城市"]:
                lat, lon = exif_data.get('GPS GPSLatitude'), exif_data.get('GPS GPSLongitude')
                if lat and lon:
                    province, city = self.get_city_and_province(lat, lon)
                    location = province if part == "拍摄省份" else city
                    structure_parts.append(location)
                else:
                    structure_parts.append(f'未知位置')
            elif part in ["年份", "月份"]:
                date_str = exif_data.get('DateTime')
                if date_str:
                    try:
                        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        date_part = str(date.year) if part == "年份" else f"{date.month:02d}"
                        structure_parts.append(date_part)
                    except:
                        structure_parts.append(f"未知{part}")
                else:
                    structure_parts.append(f"未知{part}")
            else:
                structure_parts.append(f"{part}")

        base_folder = Path(base_folder) if base_folder else (
            self.destination_root if self.destination_root else file_path.parent)
        new_folder = base_folder.joinpath(*structure_parts)
        new_folder.mkdir(parents=True, exist_ok=True)

        unique_filename = self.make_unique_filename(new_folder, file_path.name)
        return unique_filename

    def construct_new_filename(self, exif_data, file_path):
        parts = []
        date_str = exif_data.get('DateTime')

        for part in self.file_name_structure:
            if part in ["年份", "月份", "日", "星期", "时间"] and date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    if part == "年份":
                        part_str = str(date.year)
                    elif part == "月份":
                        part_str = f"{date.month:02d}"
                    elif part == "日":
                        part_str = f"{date.day:02d}"
                    elif part == "星期":
                        part_str = self._get_weekday(date)
                    elif part == "时间":
                        part_str = date.strftime('%H%M%S')
                    parts.append(part_str)
                except Exception:
                    continue

            elif part == "位置":
                lat, lon = exif_data.get('GPS GPSLatitude'), exif_data.get('GPS GPSLongitude')
                if lat and lon:
                    address = self.get_address(lat, lon)
                    if address:
                        parts.append(address)

            elif part == "品牌":
                make = exif_data.get('Make')
                if make:
                    parts.append(make)

            elif part == "型号":
                model = exif_data.get('Model')
                if model:
                    parts.append(model)

        if parts:
            new_name = self.separator.join(parts) + file_path.suffix.lower()
            unique_name = self.make_unique_filename(file_path.parent, new_name)
            return unique_name
        return None

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
                exif_data.update({'GPS GPSLatitude': lat, 'GPS GPSLongitude': lon})
            exif_data.update({
                'Make': str(tags.get('Image Make', '')).strip() or None,
                'Model': str(tags.get('Image Model', '')).strip() or None
            })
        elif suffix == '.heic':
            heif_file = pillow_heif.read_heif(file_path)
            exif_raw = heif_file.info.get('exif', b'')
            if exif_raw.startswith(b'Exif\x00\x00'): exif_raw = exif_raw[6:]
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
                datetime_str = str(tags[tag])
                return self.parse_datetime(datetime_str)
        return None

    def parse_datetime(self, datetime_str):
        if not datetime_str:
            return None

        for fmt in ['%Y:%m:%d %H:%M:%S', '%Y:%m:%d %H:%M', '%Y:%m:%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                    '%Y-%m-%d']:
            try:
                result = datetime.strptime(datetime_str, fmt)
                return result
            except Exception as e:
                continue
        return None

    def get_city_and_province(self, lat, lon):

        def is_point_in_polygon(x, y, polygon):
            if not isinstance(polygon, (list, tuple)) or len(polygon) < 3:
                return False
            inside, n = False, len(polygon)
            for i in range(n + 1):
                p1x, p1y = polygon[i % n]
                p2x, p2y = polygon[(i + 1) % n]
                if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                    if p1y != p2y: x_intercept = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= x_intercept: inside = not inside
            return inside

        def query_location(longitude, latitude, data):
            for feature in data['features']:
                name, coordinates = feature['properties']['name'], feature['geometry']['coordinates']
                polygons = [polygon for multi_polygon in coordinates for polygon in
                            ([multi_polygon] if isinstance(multi_polygon[0][0], (float, int)) else multi_polygon)]
                if any(is_point_in_polygon(longitude, latitude, polygon) for polygon in polygons):
                    return name
            return None

        province = query_location(lon, lat, self.province_data)
        city = query_location(lon, lat, self.city_data)

        result = (
            (province, '未知省份')[province is None],
            (city, '未知城市')[city is None]
        )
        return result

    @staticmethod
    def get_address(lat, lon, max_retries=3, wait_time_on_limit=2):
        key = 'bc383698582923d55b5137c3439cf4b2'
        url = f'https://restapi.amap.com/v3/geocode/regeo?key={key}&location={lon},{lat}'

        for retry in range(max_retries):
            try:
                response = requests.get(url).json()
                if response.get('status') == '1' and response.get('info', '').lower() == 'ok':
                    address = response['regeocode']['formatted_address']
                    return address
                elif 'cuqps_has_exceeded_the_limit' in response.get('info', '').lower() and retry < max_retries - 1:
                    time.sleep(wait_time_on_limit)
            except Exception as e:
                pass
            if retry < max_retries - 1:
                time.sleep(wait_time_on_limit)
        return None

    @staticmethod
    def convert_to_degrees(value):
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

    def copy_or_move_image(self, src_path, dst_path):
        try:
            if str(src_path.parent) == str(dst_path.parent):
                return

            operation = "复制" if self.destination_root is not None else "移动"
            if self.destination_root is not None:
                shutil.copy2(str(src_path), str(dst_path))
            else:
                shutil.move(str(src_path), str(dst_path))
            self.log("DEBUG", f"成功{operation}文件: {src_path} -> {dst_path}")
        except Exception as e:
            self.log("ERROR", f"操作文件 {src_path} 出错:{str(e)}")

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
                        has_files_remaining = True

            if not has_files_remaining and not any(dir_path.iterdir()) and dir_path != Path(folder):
                try:
                    dir_path.rmdir()
                except OSError as e:
                    pass

    @staticmethod
    def make_unique_filename(target_dir, filename):
        base, ext = os.path.splitext(filename)
        counter = 0
        while True:
            target_path = target_dir / f"{base}{f'-{counter}' if counter else ''}{ext}"
            if not target_path.exists():
                return target_path
            counter += 1

    def delete_empty_folders(self, root_path):
        root = Path(root_path)
        for current_dir, _, _ in os.walk(root, topdown=False):
            dir_path = Path(current_dir)
            if dir_path == root:
                continue
            try:
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    self.log("WARNING", f"已删除空文件夹 {dir_path}")
            except Exception as e:
                pass

    @staticmethod
    def _get_weekday(date):
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]

    def log(self, level, message):
        self.log_signal.emit(level, message)

# def perform_ocr(filepath, keyword):
#     try:
#         if _ocr_model is None:
#             init_ocr_model()
#         result = _ocr_model.ocr(img=str(filepath), det=True, rec=True, cls=True)
#         if not result or not result[0]:
#             return False
#         detected_texts = [line[1][0] for line in result[0]]
#         for text in detected_texts:
#             if keyword in text:
#                 return True
#         return False
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return False
