import json
import os
import re
import time
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime

import imagehash
import piexif
import requests
from PIL import Image, PngImagePlugin
from PyQt6.QtCore import QThread, pyqtSignal

from common import detect_media_type


class WriteExifThread(QThread):
    progress_updated = pyqtSignal(int)
    finished_conversion = pyqtSignal()
    log = pyqtSignal(str, str)

    def __init__(self, folders_dict, autoMark=True, title='', author='', subject='', rating='', copyright='',
                 position='', shootTime=''):
        super().__init__()
        self.folders_dict = {item['path']: item['include_sub'] for item in folders_dict}
        self.autoMark = autoMark
        self.title = title
        self.author = author
        self.subject = subject
        self.rating = rating
        self.copyright = copyright
        self.position = position
        self.shootTime = shootTime
        self._stop_requested = False
        self.lat = None
        self.lon = None
        self.cache_file = "_internal/analyze_image_cache.json"
        self.image_cache = {}

        if self.autoMark:
            self._load_cache()

        if position and ',' in position:
            try:
                self.lon, self.lat = map(float, position.split(','))
                if not (-90 <= self.lat <= 90) or not (-180 <= self.lon <= 180):
                    self.lat, self.lon = None, None
            except ValueError:
                pass

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.image_cache = json.load(f)
            except:
                try:
                    self.image_cache = {}
                    with open(self.cache_file, 'r') as f:
                        for line in f:
                            try:
                                data = json.loads(line)
                                self.image_cache.update(data)
                            except:
                                continue
                except:
                    pass

    def _save_cache(self):
        try:
            os.makedirs("_internal", exist_ok=True)
            with open(self.cache_file, 'w') as f:
                for img_hash, data in self.image_cache.items():
                    line = json.dumps({img_hash: data})
                    f.write(line + '\n')
        except Exception as e:
            self.log.emit("ERROR", f"保存数据失败: {str(e)}")

    def _calculate_image_hash(self, file_path):
        try:
            with Image.open(file_path) as img:
                img = img.convert('L').resize((8, 8), Image.Resampling.LANCZOS)
                return str(imagehash.dhash(img))
        except:
            return None

    def _find_similar_in_cache(self, img_hash):
        for cached_hash in self.image_cache:
            if imagehash.hex_to_hash(img_hash) - imagehash.hex_to_hash(cached_hash) <= 24:
                return self.image_cache[cached_hash]
        return None

    def analyze_image(self, file_path):
        if not self.autoMark or self._stop_requested:
            return [], ""

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > 10:
            return [], ""

        img_hash = self._calculate_image_hash(file_path)
        if not img_hash:
            return [], ""

        cached_result = self._find_similar_in_cache(img_hash)
        if cached_result:
            return cached_result['keywords'], cached_result['description']

        try:
            # 从配置文件或环境变量中获取API密钥，避免硬编码
            # 这里使用默认值作为示例
            secret_id = os.environ.get('STONEDT_SECRET_ID', 'default_id')
            secret_key = os.environ.get('STONEDT_SECRET_KEY', 'default_key')
            
            if secret_id == 'default_id' or secret_key == 'default_key':
                self.log.emit("ERROR", "请设置STONEDT_SECRET_ID和STONEDT_SECRET_KEY环境变量")
                return [], ""
                
            response = requests.post(
                "https://nlp.stonedt.com/api/classpic",
                headers={
                    'secret-id': secret_id,
                    'secret-key': secret_key
                },
                files={'images': ('filename.jpg', open(file_path, 'rb'), 'image/jpeg')},
                timeout=60
            )

            if self._stop_requested:
                return [], ""

            if response.status_code == 200:
                result = response.json()
                keywords_list = [item['keyword'] for item in result['results']['result']]
                description = result['results']['describe']

                self.image_cache[img_hash] = {
                    'keywords': keywords_list,
                    'description': description
                }
                self._save_cache()
                return keywords_list, description
            self.log.emit("ERROR", f"发送服务器请求出错")
            return [], ""
        except Exception as e:
            self.log.emit("ERROR", f"图像分析服务器请求超时")
            return [], ""
        finally:
            if 'response' in locals():
                response.close()

    def run(self):
        image_paths = self._collect_image_paths()
        total_files = len(image_paths)
        if not image_paths:
            self.finished_conversion.emit()
            return
        self.progress_updated.emit(0)
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as executor:
            futures = {executor.submit(self.process_image, path): path for path in image_paths}
            try:
                for i, future in enumerate(as_completed(futures), 1):
                    if self._stop_requested:
                        for f in futures:
                            f.cancel()
                        time.sleep(0.1)
                        break
                    try:
                        future.result()
                        progress = int((i / total_files) * 100)
                        self.progress_updated.emit(progress)
                    except Exception as e:
                        file_path = futures[future]
            finally:
                executor.shutdown(wait=False)
        self.finished_conversion.emit()

    def _collect_image_paths(self):
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        image_paths = []
        for folder_path, include_sub in self.folders_dict.items():
            if include_sub == 1:
                for root, _, files in os.walk(folder_path):
                    image_paths.extend(
                        os.path.join(root, file)
                        for file in files
                        if file.lower().endswith(image_extensions)
                    )
            else:
                if os.path.isdir(folder_path):
                    image_paths.extend(
                        os.path.join(folder_path, file)
                        for file in os.listdir(folder_path)
                        if file.lower().endswith(image_extensions)
                    )
        return image_paths

    def process_image(self, image_path):
        try:
            if self._stop_requested:
                self.log.emit("INFO", f"处理被取消: {image_path}")
                return
            if not image_path.lower().endswith('.png'):
                exif_dict = piexif.load(image_path)
                updated_fields = []
                if self.title:
                    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = self.title.encode('utf-8')
                    updated_fields.append(f"标题: {self.title}")
                if self.author:
                    exif_dict["0th"][315] = self.author.encode('utf-8')
                    updated_fields.append(f"作者: {self.author}")
                if self.subject:
                    exif_dict["0th"][piexif.ImageIFD.XPSubject] = self.subject.encode('utf-16le')
                    updated_fields.append(f"主题: {self.subject}")
                if self.rating:
                    exif_dict["0th"][piexif.ImageIFD.Rating] = int(self.rating)
                    updated_fields.append(f"评分: {self.rating}星")
                if self.copyright:
                    exif_dict["0th"][piexif.ImageIFD.Copyright] = self.copyright.encode('utf-8')
                    updated_fields.append(f"版权: {self.copyright}")
                if self.shootTime != 0:
                    if self.shootTime == 1:
                        date_from_filename = self.get_date_from_filename(image_path)
                        if date_from_filename:
                            if "Exif" not in exif_dict:
                                exif_dict["Exif"] = {}
                            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_from_filename.strftime(
                                "%Y:%m:%d %H:%M:%S")
                            updated_fields.append(
                                f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
                    else:
                        if "Exif" not in exif_dict:
                            exif_dict["Exif"] = {}
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self.shootTime
                        updated_fields.append(f"拍摄时间: {self.shootTime}")
                if self.autoMark:
                    if self._stop_requested:
                        self.log.emit("INFO", f"操作被终止: {image_path}")
                        return
                    keywords_list, description = self.analyze_image(image_path)
                    keywords_str = ",".join(keywords_list)
                    exif_dict["0th"][piexif.ImageIFD.XPComment] = description.encode('utf-16le')
                    exif_dict["Exif"][piexif.ExifIFD.UserComment] = description.encode('utf-8')
                    exif_dict["0th"][piexif.ImageIFD.XPKeywords] = (keywords_str + "\x00").encode(
                        "utf-16-le") + b'\x00\x00'
                    updated_fields.append(f"标记:{keywords_str}；描述:{description}")
                if self.lat is not None and self.lon is not None:
                    exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
                    updated_fields.append(
                        f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, {abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}")
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, image_path)
                if updated_fields:
                    self.log.emit("INFO", f"已成功更新 {image_path}: {'; '.join(updated_fields)}")
                else:
                    self.log.emit("WARNING", f"未对 {image_path} 进行任何更改")
            else:
                if self.shootTime != 0:
                    if self.shootTime == 1:
                        date_from_filename = self.get_date_from_filename(image_path)
                        if date_from_filename:
                            with Image.open(image_path) as img:
                                png_info = PngImagePlugin.PngInfo()
                                for key in img.text:
                                    if key.lower() != "creation time":
                                        png_info.add_text(key, img.text[key])
                                png_info.add_text("Creation Time", str(date_from_filename))
                                temp_path = image_path + ".tmp"
                                img.save(temp_path, format="PNG", pnginfo=png_info)
                                os.replace(temp_path, image_path)
                                self.log.emit("INFO", f"成功写入 {image_path} 的拍摄时间 {date_from_filename}")
                    else:
                        with Image.open(image_path) as img:
                            png_info = PngImagePlugin.PngInfo()
                            for key in img.text:
                                if key.lower() != "creation time":
                                    png_info.add_text(key, img.text[key])
                            png_info.add_text("Creation Time", self.shootTime)
                            temp_path = image_path + ".tmp"
                            img.save(temp_path, format="PNG", pnginfo=png_info)
                            os.replace(temp_path, image_path)
                            self.log.emit("INFO", f"成功写入 {image_path} 的拍摄时间 {self.shootTime}")

        except Exception as e:
            result = detect_media_type(image_path)
            if not result["valid"]:
                self.log("ERROR", f"{image_path}文件已损坏")
            elif not result["extension_match"]:
                self.log("ERROR", f"扩展名不匹配，{image_path}正确的格式是{result['extension']}")
            else:
                self.log("ERROR", f"{image_path}出错{e}")

    def _create_gps_data(self, lat: float, lon: float) -> dict:
        def decimal_to_dms(decimal: float) -> tuple:
            degrees = int(decimal)
            minutes_float = (decimal - degrees) * 60
            minutes = int(minutes_float)
            seconds = round((minutes_float - minutes) * 60, 4)
            return ((degrees, 1), (minutes, 1), (int(seconds * 10000), 10000))

        gps_ifd = {
            piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
            piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
            piexif.GPSIFD.GPSLatitude: decimal_to_dms(abs(lat)),
            piexif.GPSIFD.GPSLongitudeRef: 'E' if lon >= 0 else 'W',
            piexif.GPSIFD.GPSLongitude: decimal_to_dms(abs(lon)),
            piexif.GPSIFD.GPSMapDatum: b"WGS-84",
            piexif.GPSIFD.GPSDateStamp: datetime.now().strftime("%Y:%m:%d").encode('ascii'),
        }
        return gps_ifd

    def stop(self):
        self._stop_requested = True

    def get_date_from_filename(self, image_path):
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
