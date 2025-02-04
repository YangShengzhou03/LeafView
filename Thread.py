import json
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import cv2
import exifread
import filetype
import imagehash
import numpy as np
import piexif
import pillow_heif
import requests
from PIL import Image, PngImagePlugin
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QThread, pyqtSignal
import io
from skimage import feature

from common import get_resource_path


def check_and_report_image_type(file_path):
    ext_to_mime = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.tiff': 'image/tiff',
        '.heic': 'image/heic'
    }
    ext = os.path.splitext(file_path)[1].lower()
    kind = filetype.guess(file_path)
    actual_mime = kind.mime if kind else None
    if ext in ext_to_mime:
        if ext_to_mime[ext] != actual_mime:
            expected_ext = [k for k, v in ext_to_mime.items() if v == actual_mime]
            expected_ext_str = expected_ext[0] if expected_ext else "未知"
            return expected_ext_str
        else:
            return True
    else:
        return True


class ConversionThread(QThread):
    log_message = pyqtSignal(str, str)
    progress_updated = pyqtSignal(int)
    finished_conversion = pyqtSignal()

    def __init__(self, folders, original_format, target_format):
        super().__init__()
        self.folders = folders if isinstance(folders, list) else [folders]
        self.original_format = original_format.lower()
        self.target_format = target_format.lower()
        self._is_interrupted = False

    def run(self):
        total_files = self.count_files()
        if total_files == 0:
            self.log_message.emit("没有找到可以处理的文件", "WARNING")
            self.finished_conversion.emit()
            return
        self.progress_updated.emit(0)

        image_paths = self.collect_image_paths()
        completed = 0

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(self.convert_and_move, file_path): file_path for file_path in image_paths}
            for future in as_completed(futures):
                if self.isInterruptionRequested():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    future.result()
                    completed += 1
                    self.progress_updated.emit(int(completed / total_files * 100))
                except Exception as e:
                    file_path = futures[future]
                    self.log_message.emit(f"处理文件 {file_path} 发生错误: {e}", "ERROR")

        self.finished_conversion.emit()

    def collect_image_paths(self):
        image_paths = []
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if self.is_valid_image_format(file):
                        img_path = os.path.join(root, file)
                        image_paths.append(img_path)
        return image_paths

    def count_files(self):
        count = 0
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if self.is_valid_image_format(file):
                        count += 1
        return count

    def is_valid_image_format(self, filename):
        extensions = {self.original_format}
        if self.original_format == 'jpeg':
            extensions.add('jpg')
        return any(filename.lower().endswith('.' + ext) for ext in extensions)

    def convert_and_move(self, file_path):
        if self.isInterruptionRequested():
            return
        output_folder = os.path.join(os.path.dirname(file_path), self.target_format.upper())
        os.makedirs(output_folder, exist_ok=True)
        output_filename = os.path.splitext(os.path.basename(file_path))[0] + f'.{self.target_format}'
        output_path = os.path.join(output_folder, output_filename)

        try:
            with Image.open(file_path) as img:
                img.save(output_path)
            if self.isInterruptionRequested():
                return
            original_folder = os.path.join(os.path.dirname(file_path), self.original_format.upper())
            os.makedirs(original_folder, exist_ok=True)
            moved_path = os.path.join(original_folder, os.path.basename(file_path))
            os.rename(file_path, moved_path)
            self.log_message.emit(f"已转换到 {output_filename},原文件移至 {moved_path}", "INFO")
        except Exception as e:
            self.log_message.emit(f"处理文件 {file_path} 时发生错误: {e}", "ERROR")

    def requestInterruption(self):
        self._is_interrupted = True

    def isInterruptionRequested(self):
        return self._is_interrupted


class WriteExifThread(QThread):
    log_message = pyqtSignal(str, str)
    progress_updated = pyqtSignal(int)
    finished_conversion = pyqtSignal()

    def __init__(self, folders, title, author, subject, tag, copy, update_date, automatic_time, position, time_option):
        super().__init__()
        self.folders = folders if isinstance(folders, list) else [folders]
        self.title = title
        self.author = author
        self.subject = subject
        self.tag = tag
        self.copy = copy
        self.update_date = update_date
        self.automatic_time = automatic_time
        self.lon, self.lat = (map(float, position[:2]) if position is not None else (None, None))
        self.time_option = time_option
        self.total_files = 0
        self.processed_files = 0
        self._stop_requested = False

    def run(self):
        try:
            self.total_files = self.count_files()
            if self.total_files == 0:
                self.log_message.emit("没有找到可以处理的文件", "INFO")
                self.finished_conversion.emit()
                return
            self.progress_updated.emit(0)
            image_paths = self.collect_image_paths()
            completed = 0
            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = {executor.submit(self.set_exif_info, file_path): file_path for file_path in image_paths}
                for future in as_completed(futures):
                    if self._stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        future.result()
                        completed += 1
                        self.progress_updated.emit(int((completed / self.total_files) * 100))
                    except Exception as e:
                        file_path = futures[future]
                        self.log_message.emit(f"处理文件 {file_path} 时发生错误: {e}", "ERROR")
            self.finished_conversion.emit()
        except Exception as e:
            self.log_message.emit(f'线程运行过程中发生错误: {e}', 'ERROR')

    def collect_image_paths(self):
        image_paths = []
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        img_path = os.path.join(root, file)
                        image_paths.append(img_path)
        return image_paths

    def count_files(self):
        count = 0
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        count += 1
        return count

    def set_exif_info(self, image_path):
        try:
            ext = os.path.splitext(image_path)[1].lower()
            if ext in ('.jpg', '.jpeg', '.webp'):
                self._set_jpeg_exif_info(image_path)
            elif ext == '.png':
                self._set_png_exif_info(image_path)
        except IOError as e:
            self.log_message.emit(f"处理文件 {image_path} 时发生 IO 错误: {e}", "ERROR")
        except Exception as e:
            self.log_message.emit(f"处理文件 {image_path} 时发生意外错误: {e}", "ERROR")

    def _set_jpeg_exif_info(self, image_path):
        exif_dict = piexif.load(image_path)
        updated_fields = []

        if self.title:
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = self.title.encode("utf-8")
            updated_fields.append(f"标题: {self.title}")

        if self.subject:
            exif_dict["0th"][piexif.ImageIFD.XPSubject] = (self.subject + "\x00").encode("utf-16-le") + b'\x00\x00'
            updated_fields.append(f"主题: {self.subject}")

        if self.tag:
            exif_dict["0th"][piexif.ImageIFD.XPKeywords] = (self.tag + "\x00").encode("utf-16-le") + b'\x00\x00'
            updated_fields.append(f"标签: {self.tag}")

        if self.author:
            exif_dict["0th"][315] = self.author.encode('utf-8')
            updated_fields.append(f"作者: {self.author}")

        if self.copy:
            exif_dict["0th"][piexif.ImageIFD.Copyright] = (self.copy + "\x00").encode('utf-8')
            updated_fields.append(f"版权: {self.copy}")

        def decimal_to_dms(value):
            d = int(value)
            m = int((value - d) * 60)
            s = int((value - d - m / 60) * 3600 * 10000)
            return ((d, 1), (m, 1), (s, 10000))

        if self.lat and self.lon:
            gps_ifd = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSLatitudeRef: 'N',
                piexif.GPSIFD.GPSLatitude: decimal_to_dms(self.lat),
                piexif.GPSIFD.GPSLongitudeRef: 'E',
                piexif.GPSIFD.GPSLongitude: decimal_to_dms(self.lon),
            }
            if "GPS" not in exif_dict:
                exif_dict["GPS"] = {}
            exif_dict["GPS"].update(gps_ifd)
            updated_fields.append(f"拍摄位置")

        if self.time_option != 0:
            if self.automatic_time:
                date_from_filename = self.extract_date_from_filename(image_path)
                if date_from_filename:
                    if "Exif" not in exif_dict:
                        exif_dict["Exif"] = {}
                    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_from_filename.strftime(
                        "%Y:%m:%d %H:%M:%S")
                    updated_fields.append(
                        f"拍摄时间 (文件名识别): {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
            elif self.update_date and self.time_option == 1:
                if "Exif" not in exif_dict:
                    exif_dict["Exif"] = {}
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self.update_date
                updated_fields.append(f"拍摄时间: {self.update_date}")

        if "0th" not in exif_dict or not exif_dict["0th"].get(piexif.ImageIFD.Make, b''):
            exif_dict.setdefault("0th", {})[piexif.ImageIFD.Make] = "LeafView".encode('utf-8')
        if "0th" not in exif_dict or not exif_dict["0th"].get(piexif.ImageIFD.Model, b''):
            exif_dict.setdefault("0th", {})[piexif.ImageIFD.Model] = "LeafView".encode('utf-8')
        exif_bytes = piexif.dump(exif_dict)
        with Image.open(image_path) as img:
            img.save(image_path, exif=exif_bytes)
        self._log_updated_fields(image_path, updated_fields)

    def _set_png_exif_info(self, image_path):
        with Image.open(image_path) as img:
            png_info = PngImagePlugin.PngInfo()
            for key, value in img.info.items():
                if isinstance(value, str):
                    png_info.add_text(key, value)

            if self.time_option != 0:
                if self.automatic_time:
                    date_from_filename = self.extract_date_from_filename(image_path)
                    if date_from_filename:
                        png_info.add_text('Creation Time', date_from_filename.strftime("%Y:%m:%d %H:%M:%S"))
                        self.log_message.emit(
                            f"写入PNG文件 {image_path} 拍摄时间(文件名识别): {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}",
                            "INFO")
                elif self.update_date and self.time_option == 1:
                    png_info.add_text('Creation Time', self.update_date)
                    self.log_message.emit(f"写入PNG文件 {image_path} 拍摄时间: {self.update_date}", "INFO")
                output_file_path = image_path + ".new"
                img.save(output_file_path, "PNG", pnginfo=png_info)
                os.replace(output_file_path, image_path)
            else:
                self.log_message.emit(f"未对 {image_path} EXIF数据 进行任何更改", "WARNING")

    def _log_updated_fields(self, image_path, updated_fields):
        if updated_fields:
            fields_str = ', '.join(updated_fields)
            self.log_message.emit(f"写入 {image_path} EXIF数据 成功：{fields_str}", "INFO")
        else:
            self.log_message.emit(f"未对 {image_path} EXIF数据 进行任何更改", "WARNING")

    @staticmethod
    def extract_date_from_filename(image_path):
        base_name = os.path.basename(image_path)
        name_without_ext = os.path.splitext(base_name)[0]
        date_pattern = r'(?P<year>\d{4})[^0-9]*' \
                       r'(?P<month>1[0-2]|0?[1-9])[^0-9]*' \
                       r'(?P<day>3[01]|[12]\d|0?[1-9])[^0-9]*' \
                       r'(?P<hour>2[0-3]|[01]?\d)?[^0-9]*' \
                       r'(?P<minute>[0-5]?\d)?[^0-9]*' \
                       r'(?P<second>[0-5]?\d)?'
        match = re.search(date_pattern, name_without_ext)
        if match:
            groups = match.groupdict()
            if not all([groups.get('year'), groups.get('month'), groups.get('day')]):
                return None
            date_str_parts = [
                groups['year'],
                groups['month'].rjust(2, '0'),
                groups['day'].rjust(2, '0')
            ]
            if groups.get('hour'):
                date_str_parts.append(groups['hour'].rjust(2, '0'))
                if groups.get('minute'):
                    date_str_parts.append(groups['minute'].rjust(2, '0'))
                    if groups.get('second'):
                        date_str_parts.append(groups['second'].rjust(2, '0'))

            date_str = ''.join(date_str_parts)
            possible_formats = []
            if len(date_str) == 8:
                possible_formats.append("%Y%m%d")
            elif len(date_str) == 12:
                possible_formats.append("%Y%m%d%H%M")
            elif len(date_str) == 14:
                possible_formats.append("%Y%m%d%H%M%S")

            for fmt in possible_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    if (1900 <= date_obj.year <= 2100 and
                            1 <= date_obj.month <= 12 and
                            1 <= date_obj.day <= 31 and
                            0 <= date_obj.hour <= 23 and
                            0 <= date_obj.minute <= 59 and
                            0 <= date_obj.second <= 59):
                        return date_obj
                    else:
                        return None
                except ValueError:
                    continue
        return None

    def stop(self):
        self._stop_requested = True

    def __del__(self):
        self.wait()


class SimilarImageThread(QtCore.QThread):
    similar_images_found = QtCore.pyqtSignal(list)
    thumbnail_loaded = QtCore.pyqtSignal(str, QtGui.QPixmap)
    progress_updated = QtCore.pyqtSignal(int)
    stopped = QtCore.pyqtSignal()

    def __init__(self, folders, similarity_threshold=100, file_size_threshold=None, parent=None):
        super().__init__(parent)
        self.folders = folders
        self.similarity_threshold = similarity_threshold / 100
        self.file_size_threshold = file_size_threshold
        self.stop_flag = False

    def run(self):
        images_paths = self.collect_image_paths()
        total_pairs = (len(images_paths) * (len(images_paths) - 1)) // 2
        processed_pairs = 0
        duplicates = {}

        for img_path in images_paths:
            if self.stop_flag:
                break
            pixmap = self.load_thumbnail(img_path)
            if not pixmap.isNull():
                self.thumbnail_loaded.emit(img_path, pixmap)

        for i, img_path1 in enumerate(images_paths):
            if self.stop_flag:
                break
            for j in range(i + 1, len(images_paths)):
                if self.stop_flag:
                    break
                img_path2 = images_paths[j]
                if self.are_images_similar(img_path1, img_path2):
                    self.add_to_duplicates(duplicates, img_path1, img_path2)
                processed_pairs += 1
                self.progress_updated.emit(int((processed_pairs / total_pairs) * 100))

        filtered_duplicates = [list(group) for group in duplicates.values() if len(group) > 1]
        if filtered_duplicates:
            self.similar_images_found.emit(filtered_duplicates)
        else:
            self.stopped.emit()

        if self.stop_flag:
            self.stopped.emit()

    def collect_image_paths(self):
        supported_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.pcx',
            '.ppm', '.pgm', '.pbm', '.sgi', '.spi', '.tga', '.wmf', '.xbm', '.xpm', '.svg', '.mng'
        }
        images_paths = []
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in supported_extensions:
                        img_path = os.path.abspath(os.path.join(root, file))
                        if self.file_size_threshold is None or os.path.getsize(
                                img_path) <= self.file_size_threshold * 1024 * 1024:
                            images_paths.append(img_path)
        return images_paths

    def are_images_similar(self, path1, path2):
        try:
            hash1 = imagehash.phash(Image.open(path1))
            hash2 = imagehash.phash(Image.open(path2))
            diff = hash1 - hash2
            max_distance = 64
            return 1 - (diff / max_distance) >= self.similarity_threshold
        except:
            return False

    def add_to_duplicates(self, duplicates, img_path1, img_path2):
        key = next((k for k, v in duplicates.items() if img_path1 in v or img_path2 in v), None)
        if key is not None:
            duplicates[key].update([img_path1, img_path2])
        else:
            new_group_id = len(duplicates)
            duplicates[new_group_id] = {img_path1, img_path2}

    def load_thumbnail(self, img_path, size=(50, 50)):
        try:
            return QtGui.QPixmap(img_path).scaled(
                size[0], size[1],
                aspectRatioMode=QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                transformMode=QtCore.Qt.TransformationMode.SmoothTransformation
            )
        except:
            return QtGui.QPixmap()

    def stop(self):
        self.stop_flag = True


class RenameThread(QThread):
    finished = pyqtSignal()
    log_signal = pyqtSignal(str, str)
    update_progress_bar = pyqtSignal(int)

    def __init__(self, parent=None, selected_buttons=None, separator="", folders=None, time_derive="最早时间"):
        super().__init__(parent)
        self.selected_buttons = selected_buttons or []
        self.separator = separator
        self.folders = folders or []
        self.time_derive = time_derive
        self._stop_flag = False

    def run(self):
        total_files = self._count_total_files()
        processed_files = 0

        for folder in self.folders:
            if not Path(folder).exists():
                self.log(f"指定的文件夹不存在: {folder}", "ERROR")
                continue

            for current_dir, _, files in os.walk(folder, topdown=False):
                if self._stop_flag:
                    self.log("重命名操作已停止", "INFO")
                    self.finished.emit()
                    return

                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
                        img_path = Path(current_dir) / file
                        try:
                            new_name = self.construct_new_filename(img_path)
                            if new_name:
                                new_path = self.make_unique_filename(Path(current_dir), f"{new_name}{img_path.suffix}")
                                os.rename(img_path, new_path)
                                self.log(f"已重命名: {img_path.name} -> {new_path.name}", "INFO")
                                processed_files += 1
                                self.update_progress_bar.emit(int(processed_files * 100 / total_files))
                        except Exception as e:
                            self.log(f"重命名失败: {img_path}, 错误信息: {str(e)}", "ERROR")
        if not self._stop_flag:
            self.log("所有图片重命名完成", "DEBUG")
            self.finished.emit()

    def _count_total_files(self):
        count = 0
        for folder in self.folders:
            if Path(folder).exists():
                for _, _, files in os.walk(folder):
                    count += sum(file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')) for file in files)
        return count

    @staticmethod
    def get_exif_data(img_path):
        suffix = img_path.suffix.lower()
        if suffix == '.heic':
            heif_file = pillow_heif.read_heif(str(img_path))
            exif_data_raw = heif_file.info.get('exif', b'')
            tags = exifread.process_file(
                io.BytesIO(exif_data_raw[6:] if exif_data_raw.startswith(b'Exif\x00\x00') else exif_data_raw),
                details=False)
        else:
            with open(img_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
        return tags

    def get_date_taken(self, img_path):
        tags = self.get_exif_data(img_path)
        create_time = datetime.fromtimestamp(img_path.stat().st_ctime)
        modify_time = datetime.fromtimestamp(img_path.stat().st_mtime)
        date_taken = self.parse_datetime(tags.get('EXIF DateTimeOriginal')) or self.parse_datetime(
            tags.get('Image DateTime'))
        if self.time_derive == "拍摄日期":
            return date_taken or modify_time
        elif self.time_derive == "创建时间":
            return create_time or modify_time
        elif self.time_derive == "修改时间":
            return modify_time
        else:
            times = [t for t in [date_taken, create_time, modify_time] if t is not None]
            return min(times) if times else modify_time

    @staticmethod
    def parse_datetime(tag_value, format_str='%Y:%m:%d %H:%M:%S'):
        try:
            return datetime.strptime(str(tag_value), format_str)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def extract_gps(img_path):
        tags = RenameThread.get_exif_data(img_path)
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef')
        if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
            lat = RenameThread._convert_to_degrees(gps_latitude)
            lon = RenameThread._convert_to_degrees(gps_longitude)
            if lat is None or lon is None:
                return None, None
            if str(gps_latitude_ref) != 'N':
                lat = -lat
            if str(gps_longitude_ref) != 'E':
                lon = -lon
            return lat, lon
        return None, None

    @staticmethod
    def _convert_to_degrees(value):
        try:
            d = float(value.values[0].num) / float(value.values[0].den)
            m = float(value.values[1].num) / float(value.values[1].den)
            s = float(value.values[2].num) / float(value.values[2].den)
            return d + (m / 60.0) + (s / 3600.0)
        except Exception:
            return None

    @staticmethod
    def get_exif_tag(img_path, tag, default=None):
        tags = RenameThread.get_exif_data(img_path)
        return str(tags.get(tag, default)).strip() or default

    def construct_new_filename(self, img_path):
        date_taken = self.get_date_taken(img_path)
        if not date_taken:
            self.log(f"图片 {img_path} 没有有效的拍摄日期", "WARNING")
            return None
        lat, lon = self.extract_gps(img_path)
        address = self.get_address(lat, lon) if lat and lon else ''
        parts = []
        for button_text in self.selected_buttons:
            part = {
                '年份': lambda: f"{date_taken.year}",
                '月份': lambda: f"{date_taken.month:02d}",
                '日': lambda: f"{date_taken.day:02d}",
                '星期': lambda: f"{self._get_weekday(date_taken)}",
                '时间': lambda: f"{date_taken.strftime('%H%M')}",
                '位置': lambda: f"{address}" if address else "",
                '相机品牌': lambda: self.get_exif_tag(img_path, 'Image Make', '未知品牌'),
                '相机型号': lambda: self.get_exif_tag(img_path, 'Image Model')
            }.get(button_text, lambda: "")()
            parts.append(part)
        return self.separator.join(parts).rstrip(self.separator) if parts else None

    @staticmethod
    def get_address(lat, lon, max_retries=3, wait_time_on_limit=2):
        key = 'bc383698582923d55b5137c3439cf4b2'
        url = f'https://restapi.amap.com/v3/geocode/regeo?key={key}&location={lon},{lat}'
        for retry in range(max_retries):
            try:
                response = requests.get(url).json()
                if response.get('status') == '1' and response.get('info', '').lower() == 'ok':
                    formatted_address = response['regeocode']['formatted_address']
                    return formatted_address
                elif 'cuqps_has_exceeded_the_limit' in response.get('info', '').lower() and retry < max_retries - 1:
                    time.sleep(wait_time_on_limit)
            except Exception:
                pass
            if retry < max_retries - 1:
                time.sleep(wait_time_on_limit)
        return '未知位置'

    @staticmethod
    def _get_weekday(date):
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays[date.weekday()]

    def log(self, message, level="INFO"):
        self.log_signal.emit(message, level.upper())

    def make_unique_filename(self, target_dir, filename):
        base, ext = os.path.splitext(filename)
        target_path = target_dir / filename
        i = 1
        while target_path.exists():
            new_name = f"{base}_{i}{ext}"
            target_path = target_dir / new_name
            i += 1
        return target_path

    def stop(self):
        self._stop_flag = True


class ImageOrganizerThread(QThread):
    progress_value = pyqtSignal(int)
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()

    def __init__(self, parent=None, folders=None, classification_structure=None, destination_root=None,
                 time_derive="最早时间"):
        super().__init__()
        self.parent = parent
        self.folders = folders or []
        self.classification_structure = classification_structure or []
        self.destination_root = Path(destination_root) if destination_root else None
        self.total_files = 0
        self.processed_files = 0
        self.time_derive = time_derive
        self.processed_files_set = set()
        self._stop_flag = False

        city_name_path = get_resource_path('resources/json/City_Reverse_Geocode.json')
        sf_file_path = get_resource_path('resources/json/Province_Reverse_Geocode.json')
        with open(city_name_path, 'r', encoding='utf-8') as file:
            self.city_name_path_data = json.load(file)
        with open(sf_file_path, 'r', encoding='utf-8') as file:
            self.sf_file_path_data = json.load(file)

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.total_files = self.count_total_files()
            for folder in self.folders:
                if self._stop_flag:
                    break
                if not self.classification_structure:
                    self.organize_without_classification(folder)
                else:
                    for root, _, files in os.walk(folder):
                        if self._stop_flag:
                            break
                        for file in files:
                            if self._stop_flag:
                                break
                            if file.lower().endswith((
                                    # 图片格式
                                    '.jpg', '.jpeg', '.png', '.heic', '.tiff', '.tif',
                                    '.bmp', '.webp', '.gif', '.svg', '.psd',
                                    '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
                                    '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc',
                                    '.mos', '.iiq', '.fff', '.x3f', '.3fr', '.mef',
                                    '.mrw', '.erf', '.raw', '.rwz', '.ari',
                                    # 视频格式
                                    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv',
                                    '.m4v', '.3gp', '.mpeg', '.mpg', '.mts', '.mxf',
                                    '.webm', '.ogv', '.livp')):
                                img_path = Path(root) / file
                                try:
                                    exif_data = self.get_exif_data(img_path)
                                    new_path = self.construct_new_path(exif_data, img_path)
                                    if new_path:
                                        self.copy_or_move_image(img_path, new_path)
                                        self.update_progress()
                                except Exception as e:
                                    result = check_and_report_image_type(img_path)
                                    if type(result) is bool:
                                        self.log(f"处理 {img_path} 发生Run错误: {str(e)}", "ERROR")
                                    else:
                                        self.log(f"{img_path} 文件类型错误,正确的文件类型是{result.upper()}", "ERROR")
                                    self.update_progress()
            if not self._stop_flag:
                self.progress_value.emit(100)
                self.finished_signal.emit()
        except Exception as e:
            self.log(f"线程运行时发生错误: {str(e)}", "ERROR")

    def count_total_files(self):
        supported_extensions = (
            # 图片格式
            '.jpg', '.jpeg', '.png', '.heic', '.tiff', '.tif',
            '.bmp', '.webp', '.gif', '.svg', '.psd',
            '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
            '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc',
            '.mos', '.iiq', '.fff', '.x3f', '.3fr', '.mef',
            '.mrw', '.erf', '.raw', '.rwz', '.ari',
            # 视频格式
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv',
            '.m4v', '.3gp', '.mpeg', '.mpg', '.mts', '.mxf',
            '.webm', '.ogv', '.livp'
        )
        total_files = sum(
            sum(1 for file in files if file.lower().endswith(supported_extensions))
            for folder in self.folders
            for _, _, files in os.walk(folder)
        )
        return total_files

    def update_progress(self):
        self.processed_files += 1
        progress_percentage = int((self.processed_files / self.total_files) * 100)
        self.progress_value.emit(progress_percentage)

    def get_exif_data(self, img_path):
        exif_data = {}
        img_path = Path(img_path)

        def parse_datetime(tag_value):
            if not tag_value:
                return None
            format_strings = [
                '%Y:%m:%d %H:%M:%S',
                '%Y:%m:%d %H:%M',
                '%Y:%m:%d',
            ]
            for fmt in format_strings:
                try:
                    return datetime.strptime(str(tag_value), fmt)
                except ValueError:
                    continue
            else:
                return None

        def format_time(time_obj):
            return time_obj.strftime('%Y-%m-%d %H:%M:%S') if time_obj else None

        def extract_exif(tags):
            date_taken = parse_datetime(tags.get('EXIF DateTimeOriginal'))
            create_time = datetime.fromtimestamp(img_path.stat().st_ctime)
            modify_time = datetime.fromtimestamp(img_path.stat().st_mtime)

            exif_data['Make'] = str(tags.get('Image Make', '')).strip() or None
            exif_data['Model'] = str(tags.get('Image Model', '')).strip() or None

            lat_ref = str(tags.get('GPS GPSLatitudeRef', '')).strip()
            lon_ref = str(tags.get('GPS GPSLongitudeRef', '')).strip()
            lat = self._convert_to_degrees(tags.get('GPS GPSLatitude'))
            lon = self._convert_to_degrees(tags.get('GPS GPSLongitude'))

            if lat and lon:
                lat = -lat if lat_ref.lower() == 's' else lat
                lon = -lon if lon_ref.lower() == 'w' else lon
                exif_data['GPS GPSLatitude'] = lat
                exif_data['GPS GPSLongitude'] = lon
            else:
                exif_data['GPS GPSLatitude'] = None
                exif_data['GPS GPSLongitude'] = None

            return date_taken, create_time, modify_time

        tags = {}
        if img_path.suffix.lower() in ('.jpg', '.jpeg', '.heic', '.tiff', '.tif'):
            if img_path.suffix.lower() == '.heic':
                heif_file = pillow_heif.read_heif(img_path)
                exif_data_raw = heif_file.info.get('exif', b'')
                if exif_data_raw:
                    if exif_data_raw.startswith(b'Exif\x00\x00'):
                        exif_data_raw = exif_data_raw[6:]
                    tags = exifread.process_file(io.BytesIO(exif_data_raw), details=False)

            else:
                with open(img_path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)

            date_taken, create_time, modify_time = extract_exif(tags)

        elif img_path.suffix.lower() == '.png':
            with Image.open(img_path) as img:
                png_info = img.info
                creation_time_str = png_info.get('Creation Time')
                create_time = parse_datetime(creation_time_str) if creation_time_str else None
                date_taken = create_time
                modify_time = datetime.fromtimestamp(img_path.stat().st_mtime)
        elif img_path.suffix.lower() in (
            # 图片格式
            '.bmp', '.webp', '.gif', '.svg', '.psd',
            '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
            '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc',
            '.mos', '.iiq', '.fff', '.x3f', '.3fr', '.mef',
            '.mrw', '.erf', '.raw', '.rwz', '.ari',
            # 视频格式
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv',
            '.m4v', '.3gp', '.mpeg', '.mpg', '.mts', '.mxf',
            '.webm', '.ogv', '.livp'
        ):
            create_time = datetime.fromtimestamp(img_path.stat().st_ctime)
            modify_time = datetime.fromtimestamp(img_path.stat().st_mtime)
            date_taken = create_time
        else:
            date_taken = create_time = modify_time = None

        if self.time_derive == "拍摄日期":
            exif_data['DateTime'] = format_time(date_taken) if date_taken else None
        elif self.time_derive == "创建时间":
            exif_data['DateTime'] = format_time(create_time)
        elif self.time_derive == "修改时间":
            exif_data['DateTime'] = format_time(modify_time)
        else:
            times = [t for t in [date_taken, create_time, modify_time] if t is not None]
            earliest_time = min(times) if times else modify_time
            exif_data['DateTime'] = format_time(earliest_time)
        return exif_data

    def _convert_to_degrees(self, value):
        try:
            if not value:
                return None
            d = float(value.values[0].num) / float(value.values[0].den)
            m = float(value.values[1].num) / float(value.values[1].den)
            s = float(value.values[2].num) / float(value.values[2].den)
            return d + (m / 60.0) + (s / 3600.0)
        except Exception as e:
            return None

    def construct_new_path(self, exif_data, image_path):
        if not exif_data:
            no_exif_folder_name = "无EXIF数据"
            self.log(f"无EXIF数据 {image_path.name}", "ERROR")
            no_exif_folder = self.destination_root / no_exif_folder_name if self.destination_root else image_path.parent / no_exif_folder_name
            no_exif_folder.mkdir(parents=True, exist_ok=True)
            return self.make_unique_filename(no_exif_folder, image_path.name)

        structure_parts = []

        for part in self.classification_structure:
            if part == "拍摄设备":
                make = exif_data.get('Make', '')
                model = exif_data.get('Model', '')
                device_info = f"{make} {model}".strip() or '未知设备'
                structure_parts.append(device_info)
            elif part == "拍摄省份":
                lat = exif_data.get('GPS GPSLatitude')
                lon = exif_data.get('GPS GPSLongitude')
                if lat and lon:
                    city, _ = self.get_city_and_district(lat, lon)
                    structure_parts.append(city or '未知省份')
                else:
                    structure_parts.append('未知省份')
            elif part == "拍摄城市":
                lat = exif_data.get('GPS GPSLatitude')
                lon = exif_data.get('GPS GPSLongitude')
                if lat and lon:
                    _, district = self.get_city_and_district(lat, lon)
                    structure_parts.append(district or '未知城市')
                else:
                    structure_parts.append('未知城市')
            elif part == "年份":
                date_taken = exif_data.get('DateTime')
                if date_taken:
                    try:
                        date_taken = datetime.strptime(date_taken, '%Y-%m-%d %H:%M:%S')
                        structure_parts.append(str(date_taken.year))
                    except (ValueError, TypeError) as e:
                        self.log(f"解析时间失败: {date_taken}, 错误信息: {str(e)}", "ERROR")
                        structure_parts.append("未知拍摄时间")
                else:
                    structure_parts.append("未知拍摄时间")
            elif part == "月份":
                date_taken = exif_data.get('DateTime')
                if date_taken:
                    try:
                        date_taken = datetime.strptime(date_taken, '%Y-%m-%d %H:%M:%S')
                        structure_parts.append(str(date_taken.month).zfill(2))
                    except (ValueError, TypeError) as e:
                        self.log(f"解析时间失败: {date_taken}, 错误信息: {str(e)}", "ERROR")
                        structure_parts.append("未知拍摄时间")
                else:
                    structure_parts.append("未知拍摄时间")

        base_folder = self.destination_root if self.destination_root else image_path.parent
        new_folder = base_folder.joinpath(*structure_parts)
        new_folder.mkdir(parents=True, exist_ok=True)
        return self.make_unique_filename(new_folder, image_path.name)

    def make_unique_filename(self, target_dir, filename):
        base, ext = os.path.splitext(filename)
        target_path = target_dir / filename
        i = 1
        while target_path.exists():
            new_name = f"{base}_{i}{ext}"
            target_path = target_dir / new_name
            i += 1
        return target_path

    def copy_or_move_image(self, old_path, new_path):
        try:
            if str(old_path.parent) == str(new_path.parent):
                return

            action = "移动" if self.destination_root is None else "复制"

            if self.destination_root is not None:
                if str(old_path) in self.processed_files_set:
                    return

            if self.destination_root is None:
                shutil.move(str(old_path), str(new_path))
            else:
                shutil.copy2(str(old_path), str(new_path))
                self.processed_files_set.add(str(old_path))

            self.log(f"{action}成功: {old_path} -> {new_path}", "INFO")
        except Exception as e:
            self.log(f"{action}失败: {old_path}, 错误信息: {str(e)}", "ERROR")

    def organize_without_classification(self, root_folder):
        destination_path = self.destination_root if self.destination_root else Path(root_folder)
        root_path = Path(root_folder)
        for current_dir, _, files in os.walk(root_folder, topdown=False):
            dir_path = Path(current_dir)
            has_files_remaining = False
            for file in files:
                if file.lower().endswith((
                                    # 图片格式
                                    '.jpg', '.jpeg', '.png', '.heic', '.tiff', '.tif',
                                    '.bmp', '.webp', '.gif', '.svg', '.psd',
                                    '.arw', '.cr2', '.cr3', '.nef', '.orf', '.sr2',
                                    '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc',
                                    '.mos', '.iiq', '.fff', '.x3f', '.3fr', '.mef',
                                    '.mrw', '.erf', '.raw', '.rwz', '.ari',
                                    # 视频格式
                                    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv',
                                    '.m4v', '.3gp', '.mpeg', '.mpg', '.mts', '.mxf',
                                    '.webm', '.ogv', '.livp')):
                    img_path = dir_path / file
                    target_path = self.make_unique_filename(destination_path, img_path.name)
                    try:
                        self.copy_or_move_image(img_path, target_path)
                        self.update_progress()
                    except Exception as e:
                        self.log(f"处理文件 {img_path} 时发生错误: {str(e)}", "ERROR")
                        self.update_progress()
                        has_files_remaining = True
            if not has_files_remaining and not any(dir_path.iterdir()) and dir_path != root_path:
                try:
                    dir_path.rmdir()
                    self.parent.parent.on_delete_clicked(str(dir_path))
                    self.log(f"删除空目录: {dir_path}", "WARNING")
                except OSError as e:
                    self.log(f"无法删除空目录 {dir_path}: {str(e)}", "ERROR")

    def log(self, message, level="INFO"):
        self.log_signal.emit(message, level.upper())

    def get_city_and_district(self, lat, lon):
        def is_point_in_polygon(x, y, polygon):
            if not isinstance(polygon, (list, tuple)):
                return False

            n = len(polygon)
            if n < 3:
                return False

            inside = False
            p1x, p1y = polygon[0]
            for i in range(n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                    if p1y != p2y:
                        x_intercept = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= x_intercept:
                        inside = not inside
                p1x, p1y = p2x, p2y
            return inside

        def get_city_name(longitude, latitude):
            features = self.city_name_path_data['features']
            for feature in features:
                city_name = feature['properties']['name']
                coordinates = feature['geometry']['coordinates']

                polygon_list = []
                if isinstance(coordinates[0][0], (float, int)):
                    polygon_list.append(coordinates)
                else:
                    for multi_polygon in coordinates:
                        for polygon in multi_polygon:
                            polygon_list.append(polygon)

                if any(is_point_in_polygon(longitude, latitude, polygon) for polygon in polygon_list):
                    return city_name
            return None

        def get_province_name(longitude, latitude):
            features = self.sf_file_path_data['features']
            for feature in features:
                province_name = feature['properties']['name']
                coordinates = feature['geometry']['coordinates']

                polygon_list = []
                if isinstance(coordinates[0][0], (float, int)):
                    polygon_list.append(coordinates)
                else:
                    for multi_polygon in coordinates:
                        for polygon in multi_polygon:
                            polygon_list.append(polygon)

                if any(is_point_in_polygon(longitude, latitude, polygon) for polygon in polygon_list):
                    return province_name
            return None

        province = get_province_name(lon, lat)
        city = get_city_name(lon, lat)

        return province if province else '未知省份', city if city else '未知城市'


class ClassificationThread(QThread):
    item_classified = pyqtSignal(str, str, list)
    finished = pyqtSignal()
    progress_updated = pyqtSignal(int)
    face_cascade = cv2.CascadeClassifier(
        get_resource_path('resources/cv2_date/haarcascade_frontalface_alt2.xml'))

    def __init__(self, folder_paths, batch_size=100, parent=None):
        super().__init__(parent)
        self.folder_paths = folder_paths
        self.batch_size = batch_size
        self.image_extensions = (
            '.png', '.jpg', '.jpeg', '.bmp',
            '.dib', '.gif', '.ppm', '.blp', '.bufr',
            '.cur', '.pcx', '.dcx', '.dds', '.eps',
            '.fits', '.fli', '.ftex', '.gbr', '.grib',
            '.hdf5', '.icns', '.ico', '.im', '.imt',
            '.iptc', '.mcidas', '.mpeg', '.tiff',
            '.msp', '.pcd', '.pixar', '.psd', '.qoi',
            '.sgi', '.spider', '.sun', '.tga', '.webp',
            '.wmf', '.xbm', '.xpm', '.xvthumb'
        )
        self.video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.mpeg')
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        total_files = sum(len([f for f in os.listdir(folder_path) if
                               self.should_process_file(f.lower()) and os.path.isfile(os.path.join(folder_path, f))])
                          for folder_path in self.folder_paths)
        processed_files = 0

        for folder_path in self.folder_paths:
            if self._stop_flag:
                break
            processed_files += self.process_folder(folder_path, total_files, processed_files)

        self.finished.emit()

    def process_folder(self, folder_path, total_files, processed_files):
        file_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
                      if self.should_process_file(f.lower()) and os.path.isfile(os.path.join(folder_path, f))]

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(self.classify_file, fp, os.path.basename(fp)): fp for fp in file_paths}

            for future in as_completed(futures):
                if self._stop_flag:
                    break
                file_path, file_name, categories = future.result()
                self.item_classified.emit(file_path, file_name, categories)
                processed_files += 1
                progress = int((processed_files / total_files) * 100)
                self.progress_updated.emit(progress)

        return processed_files

    def should_process_file(self, lower_file_name):
        return lower_file_name.endswith(self.image_extensions) or lower_file_name.endswith(self.video_extensions)

    @staticmethod
    def is_screenshot(image_path):
        img = Image.open(image_path).convert('RGB')
        gray_img = img.convert('L')
        gray_np = np.array(gray_img, dtype=np.uint8)
        return ClassificationThread.check_lbp(gray_np)

    @staticmethod
    def check_lbp(gray_np):
        lbp = feature.local_binary_pattern(gray_np, P=8, R=1, method="uniform")
        hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, 10), range=(0, 9))
        hist = hist.astype("float")
        hist /= (hist.sum() + 1e-6)
        return np.any(hist > 0.55)

    @staticmethod
    def read_image_with_imutils(image_path, target_size=(640, 480), max_size=2048):
        byte_content = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(byte_content, cv2.IMREAD_COLOR)
        if img is None:
            return None
        height, width = img.shape[:2]
        if max(height, width) > max_size:
            scale_factor = max_size / max(height, width)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            img = cv2.resize(img, new_size)
        img = cv2.resize(img, target_size)
        return img

    @staticmethod
    def is_people(image_path):
        img = ClassificationThread.read_image_with_imutils(image_path)
        if img is None:
            return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = ClassificationThread.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                                                   minSize=(60, 60))
        return len(faces) > 0

    @staticmethod
    def is_landscape(image_path):
        img = ClassificationThread.read_image_with_imutils(image_path)
        if img is None:
            return False
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        color_ranges = [
            ([35, 43, 46], [77, 255, 255]),
            ([100, 43, 46], [124, 255, 255]),
            ([10, 43, 46], [34, 255, 255]),
            ([0, 0, 200], [180, 30, 255])
        ]
        masks = []
        for lower, upper in color_ranges:
            lower_bound = np.array(lower)
            upper_bound = np.array(upper)
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
            masks.append(mask)
        total_pixels = img.shape[0] * img.shape[1]
        combined_mask = np.zeros_like(masks[0])
        for mask in masks:
            combined_mask |= mask
        color_ratio = cv2.countNonZero(combined_mask) / total_pixels
        edges = cv2.Canny(img, 100, 200)
        edge_ratio = cv2.countNonZero(edges) / total_pixels
        color_threshold = 0.1
        edge_threshold = 0.05
        return color_ratio > color_threshold and edge_ratio > edge_threshold

    def classify_file(self, file_path, file_name):
        lower_file_name = file_name.lower()
        if lower_file_name.endswith(self.video_extensions):
            return self.classify_video(file_path, file_name)
        elif lower_file_name.endswith(self.image_extensions):
            return self.classify_image(file_path, file_name)
        return file_path, file_name, []

    def classify_image(self, file_path, file_name):
        categories = []
        if self.is_screenshot(file_path):
            categories.append('screen')
        if self.is_people(file_path):
            categories.append('people')
        if self.is_landscape(file_path):
            categories.append('landscape')
        return file_path, file_name, categories

    def classify_video(self, file_path, file_name):
        classifications = ['video']
        return file_path, file_name, classifications
