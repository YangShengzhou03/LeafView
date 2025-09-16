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
    """
    EXIF写入工作线程类
    
    负责在后台线程中执行图像EXIF元数据的批量写入操作，支持：
    - 多线程并行处理
    - 图像内容自动分析标记
    - 地理位置信息写入
    - 相机品牌型号信息写入
    - 拍摄时间自动识别
    """
    
    # 信号定义
    progress_updated = pyqtSignal(int)  # 进度更新信号
    finished_conversion = pyqtSignal()  # 完成转换信号
    log = pyqtSignal(str, str)  # 日志信号

    def __init__(self, folders_dict, autoMark=True, title='', author='', subject='', rating='', copyright='',
                 position='', shootTime='', cameraBrand=None, cameraModel=None):
        """
        初始化EXIF写入线程
        
        Args:
            folders_dict: 文件夹字典，包含路径和是否包含子文件夹标志
            autoMark: 是否自动分析图像内容并标记
            title: 图像标题
            author: 作者信息
            subject: 主题信息
            rating: 星级评分
            copyright: 版权信息
            position: 地理位置坐标
            shootTime: 拍摄时间
            cameraBrand: 相机品牌
            cameraModel: 相机型号
        """
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
        self.cameraBrand = cameraBrand
        self.cameraModel = cameraModel
        self._stop_requested = False  # 停止请求标志
        self.lat = None  # 纬度
        self.lon = None  # 经度
        self.cache_file = "_internal/analyze_image_cache.json"  # 图像分析缓存文件
        self.image_cache = {}  # 图像分析缓存

        # 如果启用自动标记，加载缓存
        if self.autoMark:
            self._load_cache()

        # 解析位置坐标
        if position and ',' in position:
            try:
                self.lon, self.lat = map(float, position.split(','))
                # 验证坐标范围有效性
                if not (-90 <= self.lat <= 90) or not (-180 <= self.lon <= 180):
                    self.lat, self.lon = None, None
            except ValueError:
                pass

    def _load_cache(self):
        """加载图像分析缓存"""
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
        """保存图像分析缓存"""
        try:
            os.makedirs("_internal", exist_ok=True)
            with open(self.cache_file, 'w') as f:
                for img_hash, data in self.image_cache.items():
                    line = json.dumps({img_hash: data})
                    f.write(line + '\n')
        except Exception as e:
            self.log.emit("ERROR", f"保存数据失败: {str(e)}")

    def _calculate_image_hash(self, file_path):
        """
        计算图像哈希值用于缓存查找
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            str: 图像哈希值，失败返回None
        """
        try:
            with Image.open(file_path) as img:
                img = img.convert('L').resize((8, 8), Image.Resampling.LANCZOS)
                return str(imagehash.dhash(img))
        except:
            return None

    def _find_similar_in_cache(self, img_hash):
        """
        在缓存中查找相似的图像分析结果
        
        Args:
            img_hash: 图像哈希值
            
        Returns:
            dict: 相似图像的缓存数据，未找到返回None
        """
        for cached_hash in self.image_cache:
            if imagehash.hex_to_hash(img_hash) - imagehash.hex_to_hash(cached_hash) <= 24:
                return self.image_cache[cached_hash]
        return None

    def analyze_image(self, file_path):
        """
        分析图像内容并生成关键词和描述
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            tuple: (关键词列表, 描述文本)
        """
        if not self.autoMark or self._stop_requested:
            return [], ""

        # 跳过大于10MB的文件
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > 10:
            return [], ""

        # 计算图像哈希
        img_hash = self._calculate_image_hash(file_path)
        if not img_hash:
            return [], ""

        # 在缓存中查找相似图像
        cached_result = self._find_similar_in_cache(img_hash)
        if cached_result:
            return cached_result['keywords'], cached_result['description']

        try:
            # 从环境变量中获取API密钥
            secret_id = os.environ.get('STONEDT_SECRET_ID', 'default_id')
            secret_key = os.environ.get('STONEDT_SECRET_KEY', 'default_key')
            
            if secret_id == 'default_id' or secret_key == 'default_key':
                self.log.emit("ERROR", "请设置STONEDT_SECRET_ID和STONEDT_SECRET_KEY环境变量")
                return [], ""
                
            # 调用图像分析API
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

                # 缓存分析结果
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
        """线程主执行方法"""
        # 收集所有图像路径
        image_paths = self._collect_image_paths()
        total_files = len(image_paths)
        if not image_paths:
            self.finished_conversion.emit()
            return
        
        # 初始化进度
        self.progress_updated.emit(0)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as executor:
            futures = {executor.submit(self.process_image, path): path for path in image_paths}
            try:
                for i, future in enumerate(as_completed(futures), 1):
                    if self._stop_requested:
                        # 取消所有未完成的任务
                        for f in futures:
                            f.cancel()
                        time.sleep(0.1)
                        break
                    try:
                        future.result()
                        # 更新进度
                        progress = int((i / total_files) * 100)
                        self.progress_updated.emit(progress)
                    except Exception as e:
                        file_path = futures[future]
            finally:
                executor.shutdown(wait=False)
        
        # 发送完成信号
        self.finished_conversion.emit()

    def _collect_image_paths(self):
        """
        收集所有需要处理的图像文件路径
        
        Returns:
            list: 图像文件路径列表
        """
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        image_paths = []
        for folder_path, include_sub in self.folders_dict.items():
            if include_sub == 1:
                # 包含子文件夹
                for root, _, files in os.walk(folder_path):
                    image_paths.extend(
                        os.path.join(root, file)
                        for file in files
                        if file.lower().endswith(image_extensions)
                    )
            else:
                # 不包含子文件夹
                if os.path.isdir(folder_path):
                    image_paths.extend(
                        os.path.join(folder_path, file)
                        for file in os.listdir(folder_path)
                        if file.lower().endswith(image_extensions)
                    )
        return image_paths

    def process_image(self, image_path):
        """
        处理单个图像文件的EXIF写入
        
        Args:
            image_path: 图像文件路径
        """
        try:
            if self._stop_requested:
                self.log.emit("INFO", f"处理被取消: {image_path}")
                return
            
            # 处理非PNG格式图像（支持EXIF）
            if not image_path.lower().endswith('.png'):
                exif_dict = piexif.load(image_path)
                updated_fields = []
                
                # 标题
                if self.title:
                    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = self.title.encode('utf-8')
                    updated_fields.append(f"标题: {self.title}")
                
                # 作者
                if self.author:
                    exif_dict["0th"][315] = self.author.encode('utf-8')
                    updated_fields.append(f"作者: {self.author}")
                
                # 主题
                if self.subject:
                    exif_dict["0th"][piexif.ImageIFD.XPSubject] = self.subject.encode('utf-16le')
                    updated_fields.append(f"主题: {self.subject}")
                
                # 评分
                if self.rating:
                    exif_dict["0th"][piexif.ImageIFD.Rating] = int(self.rating)
                    updated_fields.append(f"评分: {self.rating}星")
                
                # 版权
                if self.copyright:
                    exif_dict["0th"][piexif.ImageIFD.Copyright] = self.copyright.encode('utf-8')
                    updated_fields.append(f"版权: {self.copyright}")
                
                # 拍摄时间处理
                if self.shootTime != 0:
                    if self.shootTime == 1:
                        # 从文件名识别拍摄时间
                        date_from_filename = self.get_date_from_filename(image_path)
                        if date_from_filename:
                            if "Exif" not in exif_dict:
                                exif_dict["Exif"] = {}
                            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_from_filename.strftime(
                                "%Y:%m:%d %H:%M:%S")
                            updated_fields.append(
                                f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
                    else:
                        # 使用指定的拍摄时间
                        if "Exif" not in exif_dict:
                            exif_dict["Exif"] = {}
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self.shootTime
                        updated_fields.append(f"拍摄时间: {self.shootTime}")
                
                # 自动标记
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
                
                # GPS坐标
                if self.lat is not None and self.lon is not None:
                    exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
                    updated_fields.append(
                        f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, {abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}")
                
                # 写入EXIF数据
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, image_path)
                
                if updated_fields:
                    self.log.emit("INFO", f"已成功更新 {image_path}: {'; '.join(updated_fields)}")
                else:
                    self.log.emit("WARNING", f"未对 {image_path} 进行任何更改")
            else:
                # 处理PNG格式图像（不支持EXIF，使用PNG文本信息）
                if self.shootTime != 0:
                    if self.shootTime == 1:
                        # 从文件名识别拍摄时间
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
                        # 使用指定的拍摄时间
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
            # 错误处理
            result = detect_media_type(image_path)
            if not result["valid"]:
                self.log("ERROR", f"{image_path}文件已损坏")
            elif not result["extension_match"]:
                self.log("ERROR", f"扩展名不匹配，{image_path}正确的格式是{result['extension']}")
            else:
                self.log("ERROR", f"{image_path}出错{e}")

    def _create_gps_data(self, lat: float, lon: float) -> dict:
        """
        创建GPS EXIF数据
        
        Args:
            lat: 纬度
            lon: 经度
            
        Returns:
            dict: GPS EXIF数据字典
        """
        def decimal_to_dms(decimal: float) -> tuple:
            """将十进制坐标转换为度分秒格式"""
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
        """请求停止处理"""
        self._stop_requested = True

    def get_date_from_filename(self, image_path):
        """
        从文件名中提取日期时间信息
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            datetime: 提取的日期时间对象，失败返回None
        """
        base_name = os.path.basename(image_path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # 日期时间正则表达式模式
        date_pattern = r'(?P<year>\d{4})[^0-9]*' \
                       r'(?P<month>1[0-2]|0?[1-9])[^0-9]*' \
                       r'(?P<day>3[01]|[12]\d|0?[1-9])[^0-9]*' \
                       r'(?P<hour>2[0-3]|[01]?\d)?[^0-9]*' \
                       r'(?P<minute>[0-5]?\d)?[^0-9]*' \
                       r'(?P<second>[0-5]?\d)?'
        
        match = re.search(date_pattern, name_without_ext)
        if match:
            groups = match.groupdict()
            # 验证年月日是否完整
            if not all([groups.get('year'), groups.get('month'), groups.get('day')]):
                return None
            
            # 构建日期时间字符串
            date_str_parts = [
                groups['year'],
                groups['month'].rjust(2, '0'),
                groups['day'].rjust(2, '0')
            ]
            
            # 添加时分秒（如果存在）
            if groups.get('hour'):
                date_str_parts.append(groups['hour'].rjust(2, '0'))
                if groups.get('minute'):
                    date_str_parts.append(groups['minute'].rjust(2, '0'))
                    if groups.get('second'):
                        date_str_parts.append(groups['second'].rjust(2, '0'))

            date_str = ''.join(date_str_parts)
            
            # 尝试不同的日期格式
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
                    # 验证日期时间有效性
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
