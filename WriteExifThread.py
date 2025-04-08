import os
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime

import piexif
from PyQt6.QtCore import QThread, pyqtSignal


class WriteExifThread(QThread):
    progress_updated = pyqtSignal(int)
    finished_conversion = pyqtSignal()
    log = pyqtSignal(str, str)

    def __init__(self, folders_dict, autoMark=True, title='', author='', subject='', rating='', copyright='', position=''):
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
        if position and ',' in position:
            try:
                self.lon, self.lat = map(float, position.split(','))
                if not (-90 <= self.lat <= 90) or not (-180 <= self.lon <= 180):
                    self.log.emit("WARNING", "坐标超出有效范围: 纬度应在-90到90之间，经度应在-180到180之间")
                    self.lat, self.lon = None, None
            except ValueError as e:
                self.log.emit("ERROR", f"无效的坐标格式: {e}")

    def run(self):
        image_paths = self._collect_image_paths()
        total_files = len(image_paths)
        if not image_paths:
            self.log.emit("ERROR", "没有找到可以处理的图片文件")
            self.finished_conversion.emit()
            return
        self.progress_updated.emit(0)
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as executor:
            futures = {executor.submit(self.process_image, path): path for path in image_paths}
            for i, future in enumerate(as_completed(futures), 1):
                if self._stop_requested:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    future.result()
                    progress = int((i / total_files) * 100)
                    self.progress_updated.emit(progress)
                except Exception as e:
                    file_path = futures[future]
                    self.log.emit("ERROR", f"处理文件 {file_path} 失败: {str(e)}")
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
            if self.autoMark:
                exif_dict["0th"][piexif.ImageIFD.XPKeywords] = ("自动标记" + "\x00").encode("utf-16-le") + b'\x00\x00'
            if self.lat is not None and self.lon is not None:
                exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
                updated_fields.append(
                    f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, "
                    f"{abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}"
                )
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
            if updated_fields:
                self.log.emit("INFO", f"成功更新 {image_path}: {', '.join(updated_fields)}")
            else:
                self.log.emit("WARNING", f"未对 {image_path} 进行任何更改")
        except Exception as e:
            self.log.emit("ERROR", f"处理图片 {image_path} 时出错: {str(e)}")
            raise

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