import json
import os
import time
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime

import imagehash
import piexif
import requests
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal


class WriteExifThread(QThread):
    progress_updated = pyqtSignal(int)
    finished_conversion = pyqtSignal()
    log = pyqtSignal(str, str)

    def __init__(self, folders_dict, autoMark=True, title='', author='', subject='', rating='', copyright='',
                 position=''):
        super().__init__()
        self.folders_dict = {item['path']: item['include_sub'] for item in folders_dict}
        self.autoMark = autoMark
        self.title = title
        self.author = author
        self.subject = subject
        self.rating = rating
        self.copyright = copyright
        self.position = position
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
            response = requests.post(
                "https://nlp.stonedt.com/api/classpic",
                headers={
                    'secret-id': '342acb99-d024-4be6-a27f-487d7db87e21',
                    'secret-key': '5172e39a322288d2850234aba857b625'
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
            exif_dict = piexif.load(image_path)
            updated_fields = []
            if self._stop_requested:
                return
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
            if self.autoMark:
                if self._stop_requested:
                    self.log.emit("INFO", f"操作被终止: {image_path}")
                    return
                keywords_list, description = self.analyze_image(image_path)
                keywords_str = ",".join(keywords_list)
                exif_dict["0th"][piexif.ImageIFD.XPComment] = description.encode('utf-16le')
                exif_dict["Exif"][piexif.ExifIFD.UserComment] = description.encode('utf-8')
                exif_dict["0th"][piexif.ImageIFD.XPKeywords] = (keywords_str + "\x00").encode("utf-16-le") + b'\x00\x00'
                updated_fields.append(f"标记:{keywords_str}；描述:{description}")
            if self.lat is not None and self.lon is not None:
                exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
                updated_fields.append(
                    f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, "
                    f"{abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}"
                )
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
            if updated_fields:
                self.log.emit("INFO", f"已成功更新 {image_path}: {'; '.join(updated_fields)}")
            else:
                self.log.emit("WARNING", f"未对 {image_path} 进行任何更改")

        except Exception as e:
            self.log.emit("ERROR", f"处理 {image_path} 时出错: {str(e)}")

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
