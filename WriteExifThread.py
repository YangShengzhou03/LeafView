import os
import re
import time
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime

import piexif
from PIL import Image, PngImagePlugin
from PyQt6.QtCore import QThread, pyqtSignal

from common import detect_media_type


class WriteExifThread(QThread):
    """
    EXIF写入工作线程类
    
    负责在后台线程中执行图像EXIF元数据的批量写入操作，支持：
    - 多线程并行处理
    - 地理位置信息写入
    - 相机品牌型号信息写入
    - 拍摄时间自动识别
    """
    
    # 信号定义
    progress_updated = pyqtSignal(int)  # 进度更新信号
    finished_conversion = pyqtSignal()  # 完成转换信号
    log = pyqtSignal(str, str)  # 日志信号

    def __init__(self, folders_dict, title='', author='', subject='', rating='', copyright='',
                 position='', shootTime='', cameraBrand=None, cameraModel=None, lensBrand=None, lensModel=None):
        """
        初始化EXIF写入线程
        
        Args:
            folders_dict: 文件夹字典，包含路径和是否包含子文件夹标志
            title: 图像标题
            author: 作者信息
            subject: 主题信息
            rating: 星级评分
            copyright: 版权信息
            position: 地理位置坐标
            shootTime: 拍摄时间
            cameraBrand: 相机品牌
            cameraModel: 相机型号
            lensBrand: 镜头品牌
            lensModel: 镜头型号
        """
        super().__init__()
        self.folders_dict = {item['path']: item['include_sub'] for item in folders_dict}
        self.title = title
        self.author = author
        self.subject = subject
        self.rating = rating
        self.copyright = copyright
        self.position = position
        self.shootTime = shootTime
        self.cameraBrand = cameraBrand
        self.cameraModel = cameraModel
        self.lensBrand = lensBrand
        self.lensModel = lensModel
        self._stop_requested = False  # 停止请求标志
        self.lat = None  # 纬度
        self.lon = None  # 经度

        # 解析位置坐标
        if position and ',' in position:
            try:
                self.lon, self.lat = map(float, position.split(','))
                # 验证坐标范围有效性
                if not (-90 <= self.lat <= 90) or not (-180 <= self.lon <= 180):
                    self.lat, self.lon = None, None
            except ValueError:
                pass



    def run(self):
        """线程主执行方法"""
        # 收集所有图像路径
        image_paths = self._collect_image_paths()
        total_files = len(image_paths)
        if not image_paths:
            self.log.emit("WARNING", "⚠️ 未找到任何图像文件\n\n"
                           "请检查：\n"
                           "• 文件夹路径是否正确\n"
                           "• 是否包含支持的图像格式(.jpg/.jpeg/.png/.webp)")
            self.finished_conversion.emit()
            return
        
        # 显示操作统计
        self.log.emit("INFO", f"📊 开始处理 {total_files} 个图像文件")
        
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
                        self.log.emit("INFO", "⏹️ EXIF写入操作已成功中止")
                        break
                    try:
                        future.result()
                        # 更新进度
                        progress = int((i / total_files) * 100)
                        self.progress_updated.emit(progress)
                    except Exception as e:
                        file_path = futures[future]
                        self.log.emit("ERROR", f"❌ 处理文件 {os.path.basename(file_path)} 时出错: {str(e)}")
            finally:
                executor.shutdown(wait=False)
        
        # 发送完成信号
        self.log.emit("INFO", f"✅ EXIF写入任务完成，共处理 {total_files} 个文件")
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
                self.log.emit("INFO", f"⏹️ 处理被取消: {os.path.basename(image_path)}")
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
                
                # 相机品牌和型号
                if self.cameraBrand:
                    exif_dict["0th"][piexif.ImageIFD.Make] = self.cameraBrand.encode('utf-8')
                    updated_fields.append(f"相机品牌: {self.cameraBrand}")
                
                if self.cameraModel:
                    exif_dict["0th"][piexif.ImageIFD.Model] = self.cameraModel.encode('utf-8')
                    updated_fields.append(f"相机型号: {self.cameraModel}")
                
                # 镜头信息
                if self.lensModel:
                    # 写入镜头型号到EXIF数据
                    if "Exif" not in exif_dict:
                        exif_dict["Exif"] = {}
                    exif_dict["Exif"][piexif.ExifIFD.LensModel] = self.lensModel.encode('utf-8')
                    updated_fields.append(f"镜头型号: {self.lensModel}")
                
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
                

                
                # GPS坐标
                if self.lat is not None and self.lon is not None:
                    exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
                    updated_fields.append(
                        f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, {abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}")
                
                # 写入EXIF数据
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, image_path)
                
                if updated_fields:
                    self.log.emit("INFO", f"✅ 成功更新 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
                else:
                    self.log.emit("WARNING", f"⚠️ 未对 {os.path.basename(image_path)} 进行任何更改\n\n"
                                 "可能的原因：\n"
                                 "• 所有EXIF字段均为空")
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
                                self.log.emit("INFO", f"✅ 成功写入 {os.path.basename(image_path)} 的拍摄时间 {date_from_filename}")
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
                            self.log.emit("INFO", f"✅ 成功写入 {os.path.basename(image_path)} 的拍摄时间 {self.shootTime}")

        except Exception as e:
            # 错误处理
            result = detect_media_type(image_path)
            if not result["valid"]:
                self.log.emit("ERROR", f"❌ {os.path.basename(image_path)} 文件已损坏或格式不支持\n\n"
                                 "请检查文件完整性")
            elif not result["extension_match"]:
                self.log.emit("ERROR", f"❌ {os.path.basename(image_path)} 扩展名不匹配，实际格式为 {result['extension']}\n\n"
                                 "请检查文件格式")
            else:
                self.log.emit("ERROR", f"❌ 处理 {os.path.basename(image_path)} 时出错: {str(e)}")

    def stop(self):
        """请求停止处理"""
        self._stop_requested = True
        self.log.emit("INFO", "⏹️ 正在停止EXIF写入操作...")

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

    def _create_gps_data(self, lat, lon):
        """
        创建GPS EXIF数据字典
        
        Args:
            lat: 纬度（十进制）
            lon: 经度（十进制）
            
        Returns:
            dict: GPS EXIF数据字典
        """
        def decimal_to_dms(decimal):
            """将十进制度数转换为度分秒格式"""
            degrees = int(abs(decimal))
            minutes_decimal = (abs(decimal) - degrees) * 60
            minutes = int(minutes_decimal)
            seconds = (minutes_decimal - minutes) * 60
            return [(degrees, 1), (minutes, 1), (int(seconds * 100), 100)]
        
        gps_dict = {}
        
        # 纬度
        gps_dict[piexif.GPSIFD.GPSLatitude] = decimal_to_dms(abs(lat))
        gps_dict[piexif.GPSIFD.GPSLatitudeRef] = b'N' if lat >= 0 else b'S'
        
        # 经度
        gps_dict[piexif.GPSIFD.GPSLongitude] = decimal_to_dms(abs(lon))
        gps_dict[piexif.GPSIFD.GPSLongitudeRef] = b'E' if lon >= 0 else b'W'
        
        # 时间戳
        current_time = datetime.now()
        gps_dict[piexif.GPSIFD.GPSDateStamp] = current_time.strftime("%Y:%m:%d")
        gps_dict[piexif.GPSIFD.GPSTimeStamp] = [
            (current_time.hour, 1),
            (current_time.minute, 1),
            (current_time.second, 1)
        ]
        
        # GPS处理方式
        gps_dict[piexif.GPSIFD.GPSProcessingMethod] = b'GPS'
        
        return gps_dict

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
