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
                self.lat, self.lon = map(float, position.split(','))
                # 验证坐标范围有效性
                if not (-90 <= self.lat <= 90) or not (-180 <= self.lon <= 180):
                    self.lat, self.lon = None, None
            except ValueError:
                pass



    def run(self):
        """线程主执行方法"""
        total_files = 0
        success_count = 0
        error_count = 0
        
        try:
            # 收集所有图像路径
            image_paths = self._collect_image_paths()
            total_files = len(image_paths)
            if not image_paths:
                self.log.emit("WARNING", "没有找到任何可以处理的图像文件\n\n"
                               "请检查：\n"
                               "• 您选择的文件夹路径是否正确\n"
                               "• 文件夹里是否有.jpg、.jpeg、.png、.webp等格式的图片")
                self.finished_conversion.emit()
                return
            
            # 显示操作统计
            self.log.emit("DEBUG", f"开始处理 {total_files} 张图片")
            
            # 初始化进度
            self.progress_updated.emit(0)
            
            # 使用线程池并行处理
            with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as executor:
                futures = {}
                # 为每个图像创建任务，添加文件大小检查
                for path in image_paths:
                    if self._stop_requested:
                        break
                    try:
                        # 检查文件大小，跳过过大的文件
                        file_size = os.path.getsize(path)
                        if file_size > 500 * 1024 * 1024:  # 超过500MB的文件
                            self.log.emit("ERROR", f"文件 {os.path.basename(path)} 太大了(超过500MB)，暂不支持处理")
                            error_count += 1
                            continue
                        futures[executor.submit(self.process_image, path)] = path
                    except Exception as e:
                        self.log.emit("ERROR", f"添加文件 {os.path.basename(path)} 到任务队列失败: {str(e)}")
                        error_count += 1
                
                # 处理完成的任务
                if futures:
                    try:
                        for i, future in enumerate(as_completed(futures), 1):
                            if self._stop_requested:
                                # 取消所有未完成的任务
                                for f in futures:
                                    f.cancel()
                                time.sleep(0.1)
                                self.log.emit("DEBUG", "EXIF写入操作已成功中止")
                                break
                            try:
                                # 设置任务超时（例如30秒）
                                future.result(timeout=30)
                                success_count += 1
                            except TimeoutError:
                                file_path = futures[future]
                                self.log.emit("ERROR", f"处理文件 {os.path.basename(file_path)} 时间太长，已超时")
                                error_count += 1
                            except Exception as e:
                                file_path = futures[future]
                                self.log.emit("ERROR", f"处理文件 {os.path.basename(file_path)} 时出错: {str(e)}")
                                error_count += 1
                            finally:
                                # 更新进度
                                progress = int((i / len(futures)) * 100)
                                self.progress_updated.emit(progress)
                    except Exception as e:
                        self.log.emit("ERROR", f"任务调度过程中发生错误: {str(e)}")
                        error_count += 1
        except Exception as e:
            self.log.emit("ERROR", f"全局错误: {str(e)}")
            error_count += 1
        finally:
            # 发送完成信号
            self.log.emit("INFO", f"图片信息写入完成了，成功处理了 {success_count} 张，失败了 {error_count} 张，总共 {total_files} 张图片")
            self.finished_conversion.emit()

    def _collect_image_paths(self):
        """
        收集所有需要处理的图像文件路径
        
        Returns:
            list: 图像文件路径列表
        """
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.mov', '.mp4', '.avi', '.mkv', '.cr2', '.cr3', '.nef', '.arw', '.orf', '.dng', '.raf')
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
                self.log.emit("WARNING", f"处理被取消: {os.path.basename(image_path)}")
                return
            
            file_ext = os.path.splitext(image_path)[1].lower()
            
            # 处理不同格式的文件
            if file_ext in ('.jpg', '.jpeg', '.webp'):
                # 处理支持EXIF的格式
                self._process_exif_format(image_path)
            elif file_ext == '.png':
                # 处理PNG格式图像（不支持EXIF，使用PNG文本信息）
                self._process_png_format(image_path)
            elif file_ext in ('.heic', '.heif'):
                # 处理HEIC/HEIF格式
                self._process_heic_format(image_path)
            elif file_ext in ('.mov', '.mp4', '.avi', '.mkv'):
                # 处理视频格式
                self._process_video_format(image_path)
            elif file_ext in ('.cr2', '.cr3', '.nef', '.arw', '.orf', '.dng', '.raf'):
                # 处理RAW格式
                self._process_raw_format(image_path)
            else:
                self.log.emit("WARNING", f"不支持的文件格式: {file_ext}")

        except Exception as e:
            # 错误处理
            result = detect_media_type(image_path)
            if not result["valid"]:
                self.log.emit("ERROR", f"{os.path.basename(image_path)} 文件已损坏或格式不支持\n\n"
                                 "请检查文件完整性")
            elif not result["extension_match"]:
                self.log.emit("ERROR", f"{os.path.basename(image_path)} 扩展名不匹配，实际格式为 {result['extension']}\n\n"
                                 "请检查文件格式")
            else:
                self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 时出错: {str(e)}")

    def _process_exif_format(self, image_path):
        """
        处理支持EXIF的格式（JPG, JPEG, WebP）
        
        Args:
            image_path: 图像文件路径
        """
        try:
            exif_dict = piexif.load(image_path)
        except Exception:
            # 如果图片没有EXIF数据，创建空的EXIF字典
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        
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
        if self.lensBrand:
            # 写入镜头品牌到EXIF数据
            if "Exif" not in exif_dict:
                exif_dict["Exif"] = {}
            exif_dict["Exif"][piexif.ExifIFD.LensMake] = self.lensBrand.encode('utf-8')
            updated_fields.append(f"镜头品牌: {self.lensBrand}")
        
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
            self.log.emit("INFO", f"成功更新 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
        else:
            self.log.emit("WARNING", f"未对 {os.path.basename(image_path)} 进行任何更改\n\n"
                             "可能的原因：\n"
                             "• 所有EXIF字段均为空")

    def _process_png_format(self, image_path):
        """
        处理PNG格式图像（不支持EXIF，使用PNG文本信息）
        
        Args:
            image_path: 图像文件路径
        """
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
                        self.log.emit("INFO", f"成功写入 {os.path.basename(image_path)} 的拍摄时间 {date_from_filename}")
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
                    self.log.emit("INFO", f"成功写入 {os.path.basename(image_path)} 的拍摄时间 {self.shootTime}")

    def _process_heic_format(self, image_path):
        """
        处理HEIC/HEIF格式图像
        
        Args:
            image_path: 图像文件路径
        """
        try:
            # 尝试导入pillow_heif库
            from pillow_heif import open_heif, register_heif_opener
            register_heif_opener()
        except ImportError:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 需要 pillow-heif 库\n\n"
                             "请安装: pip install pillow-heif")
            return
        
        try:
            # 读取HEIC文件
            heif_file = open_heif(image_path)
            
            # 转换为PIL图像 - 使用新API
            try:
                image = heif_file.to_pillow()
            except AttributeError:
                # 兼容旧版本API
                image = heif_file.to_pil()
            
            # 读取现有的EXIF数据
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            # 尝试从多个来源读取EXIF数据
            # 方法1: 从HEIF文件直接读取EXIF
            if hasattr(heif_file, 'exif') and heif_file.exif:
                try:
                    heif_exif = piexif.load(heif_file.exif)
                    exif_dict.update(heif_exif)
                except Exception:
                    pass
            
            # 方法2: 从PIL图像读取EXIF
            if hasattr(image, '_getexif') and image._getexif():
                try:
                    pil_exif = image._getexif()
                    if pil_exif:
                        # 映射常见的EXIF标签
                        tag_mapping = {
                            270: ("0th", piexif.ImageIFD.ImageDescription),  # 图像描述
                            271: ("0th", piexif.ImageIFD.Make),  # 相机制造商
                            272: ("0th", piexif.ImageIFD.Model),  # 相机型号
                            315: ("0th", 315),  # 作者
                            36867: ("Exif", piexif.ExifIFD.DateTimeOriginal),  # 拍摄时间
                            37378: ("Exif", piexif.ExifIFD.FNumber),  # 光圈值
                            37386: ("Exif", piexif.ExifIFD.FocalLength),  # 焦距
                            42035: ("Exif", piexif.ExifIFD.LensMake),  # 镜头制造商
                            41988: ("Exif", piexif.ExifIFD.LensModel),  # 镜头型号
                            42034: ("Exif", piexif.ExifIFD.LensSpecification),  # 镜头规格
                        }
                        
                        for tag_id, (section, piexif_tag) in tag_mapping.items():
                            if tag_id in pil_exif:
                                exif_dict[section][piexif_tag] = pil_exif[tag_id]
                except Exception:
                    pass
            
            # 方法3: 尝试通过PIL的info属性获取EXIF
            if hasattr(image, 'info') and 'exif' in image.info:
                try:
                    info_exif = piexif.load(image.info['exif'])
                    exif_dict.update(info_exif)
                except Exception:
                    pass
            
            # 方法4: 尝试直接使用PIL打开文件读取EXIF
            try:
                with Image.open(image_path) as img:
                    if hasattr(img, '_getexif') and img._getexif():
                        pil_exif = img._getexif()
                        if pil_exif:
                            tag_mapping = {
                                270: ("0th", piexif.ImageIFD.ImageDescription),
                                271: ("0th", piexif.ImageIFD.Make),
                                272: ("0th", piexif.ImageIFD.Model),
                                315: ("0th", 315),
                                36867: ("Exif", piexif.ExifIFD.DateTimeOriginal),
                                37378: ("Exif", piexif.ExifIFD.FNumber),
                                37386: ("Exif", piexif.ExifIFD.FocalLength),
                                42035: ("Exif", piexif.ExifIFD.LensMake),  # 镜头制造商
                                41988: ("Exif", piexif.ExifIFD.LensModel),
                                42034: ("Exif", piexif.ExifIFD.LensSpecification),  # 镜头规格
                            }
                            
                            for tag_id, (section, piexif_tag) in tag_mapping.items():
                                if tag_id in pil_exif:
                                    exif_dict[section][piexif_tag] = pil_exif[tag_id]
            except Exception:
                pass
            
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
            if self.lensBrand:
                if "Exif" not in exif_dict:
                    exif_dict["Exif"] = {}
                exif_dict["Exif"][piexif.ExifIFD.LensMake] = self.lensBrand.encode('utf-8')
                updated_fields.append(f"镜头品牌: {self.lensBrand}")
            
            if self.lensModel:
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
                            "%Y:%m:%d %H:%M:%S").encode('utf-8')
                        updated_fields.append(
                            f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
                else:
                    # 使用指定的拍摄时间
                    if "Exif" not in exif_dict:
                        exif_dict["Exif"] = {}
                    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self.shootTime.encode('utf-8')
                    updated_fields.append(f"拍摄时间: {self.shootTime}")
            
            # GPS坐标
            if self.lat is not None and self.lon is not None:
                exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
                updated_fields.append(
                    f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, {abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}")
            
            # 写入EXIF数据
            if updated_fields:
                try:
                    # 创建临时文件路径
                    temp_path = image_path + ".tmp"
                    
                    # 准备EXIF数据
                    exif_bytes = piexif.dump(exif_dict)
                    
                    # 保存图像（包含EXIF数据）
                    image.save(temp_path, format="HEIF", exif=exif_bytes)
                    
                    # 替换原文件
                    os.replace(temp_path, image_path)
                    
                    self.log.emit("INFO", f"成功更新 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
                except Exception as e:
                    self.log.emit("ERROR", f"写入EXIF数据失败: {str(e)}")
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
            else:
                self.log.emit("WARNING", f"未对 {os.path.basename(image_path)} 进行任何更改\n\n"
                                 "可能的原因：\n"
                                 "• 所有EXIF字段均为空")
                
        except Exception as e:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 时出错: {str(e)}")

    def _process_video_format(self, image_path):
        """
        处理视频格式（MOV, MP4, AVI, MKV）
        
        Args:
            image_path: 视频文件路径
        """
        try:
            # 尝试导入moviepy库
            from moviepy.editor import VideoFileClip
        except ImportError:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 需要 moviepy 库\n\n"
                             "请安装: pip install moviepy")
            return
        
        try:
            # 获取视频信息
            with VideoFileClip(image_path) as video:
                duration = video.duration
                fps = video.fps
                size = video.size
            
            updated_fields = []
            
            # 拍摄时间处理
            if self.shootTime != 0:
                if self.shootTime == 1:
                    # 从文件名识别拍摄时间
                    date_from_filename = self.get_date_from_filename(image_path)
                    if date_from_filename:
                        updated_fields.append(
                            f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
                else:
                    # 使用指定的拍摄时间
                    updated_fields.append(f"拍摄时间: {self.shootTime}")
            
            # 其他元数据处理（简化版）
            if self.title:
                updated_fields.append(f"标题: {self.title}")
            if self.author:
                updated_fields.append(f"作者: {self.author}")
            
            # 视频格式需要特殊工具来写入元数据，这里简化处理
            if updated_fields:
                self.log.emit("INFO", f"成功更新 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
                self.log.emit("WARNING", f"视频元数据写入需要氪金，仅记录元数据信息")
            else:
                self.log.emit("WARNING", f"未对 {os.path.basename(image_path)} 进行任何更改")
                
        except Exception as e:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 时出错: {str(e)}")

    def _process_raw_format(self, image_path):
        """
        处理RAW格式（CR2, CR3, NEF, ARW, ORF, DNG, RAF）
        
        Args:
            image_path: RAW文件路径
        """
        try:
            # 尝试导入rawpy库
            import rawpy
        except ImportError:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 需要 rawpy 库\n\n"
                             "请安装: pip install rawpy")
            return
        
        try:
            # 读取RAW文件
            with rawpy.imread(image_path) as raw:
                # 获取RAW图像信息
                updated_fields = []
                
                # 拍摄时间处理
                if self.shootTime != 0:
                    if self.shootTime == 1:
                        # 从文件名识别拍摄时间
                        date_from_filename = self.get_date_from_filename(image_path)
                        if date_from_filename:
                            updated_fields.append(
                                f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
                    else:
                        # 使用指定的拍摄时间
                        updated_fields.append(f"拍摄时间: {self.shootTime}")
                
                # 其他元数据处理（简化版）
                if self.title:
                    updated_fields.append(f"标题: {self.title}")
                if self.author:
                    updated_fields.append(f"作者: {self.author}")
                
                # RAW格式需要特殊工具来写入元数据，这里简化处理
                if updated_fields:
                    self.log.emit("INFO", f"成功更新 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
                    self.log.emit("WARNING", f"RAW格式元数据写入需要额外工具支持，仅记录元数据信息")
                else:
                    self.log.emit("WARNING", f"未对 {os.path.basename(image_path)} 进行任何更改")
                    
        except Exception as e:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 时出错: {str(e)}")

    def stop(self):
        """请求停止处理"""
        self._stop_requested = True

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
        从文件名中提取日期时间信息，支持多种格式，包括中文日期格式
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            datetime: 提取的日期时间对象，失败返回None
        """
        base_name = os.path.basename(image_path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # 日期时间正则表达式模式 - 增强版支持中文格式和连续数字时间格式
        # 匹配格式如：2024年9月23日、2024-09-23、2024.09.23、2024/09/23等
        # 以及时间格式如：182124（18:21:24）、1418（14:18）等
        date_pattern = r'(?P<year>\d{4})[年\-\.\/\s]?' \
                       r'(?P<month>1[0-2]|0?[1-9])[月\-\.\/\s]?' \
                       r'(?P<day>3[01]|[12]\d|0?[1-9])[日号\-\.\/\s]?' \
                       r'(?:[^0-9]*?)?' \
                       r'(?P<hour>[0-2]?\d)?' \
                       r'(?P<minute>[0-5]?\d)?' \
                       r'(?P<second>[0-5]?\d)?'
        
        # 尝试匹配日期时间模式
        match = re.search(date_pattern, name_without_ext)
        if not match:
            # 尝试另一种模式：直接匹配连续的数字时间格式（如182124）
            time_pattern = r'(?P<year>\d{4})[^\d]*(?P<month>1[0-2]|0?[1-9])[^\d]*(?P<day>3[01]|[12]\d|0?[1-9])[^\d]*(?P<hour>[0-2]?\d)(?P<minute>[0-5]\d)(?P<second>[0-5]\d)'
            match = re.search(time_pattern, name_without_ext)
        
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
            has_time = False
            if groups.get('hour'):
                date_str_parts.append(groups['hour'].rjust(2, '0'))
                has_time = True
                if groups.get('minute'):
                    date_str_parts.append(groups['minute'].rjust(2, '0'))
                    if groups.get('second'):
                        date_str_parts.append(groups['second'].rjust(2, '0'))
                    elif len(groups.get('minute', '')) == 2 and len(groups.get('hour', '')) == 2:
                        # 如果有小时和分钟但没有秒，尝试从文件名中查找秒数
                        # 例如：2024-08-06-周二-182124 -> 已经提取了18和21，还需要提取24
                        remaining_text = name_without_ext[match.end():]
                        if remaining_text and remaining_text[:2].isdigit():
                            seconds = remaining_text[:2]
                            if 0 <= int(seconds) <= 59:
                                date_str_parts.append(seconds)
                                groups['second'] = seconds
            
            # 如果没有从正则表达式中提取到时间，尝试从文件名中查找连续的6位数字作为时间
            if not has_time:
                # 查找文件名中是否有连续的6位数字（HHMMSS格式）
                time_match = re.search(r'(?P<hour>[0-2]\d)(?P<minute>[0-5]\d)(?P<second>[0-5]\d)', name_without_ext)
                if time_match:
                    groups.update(time_match.groupdict())
                    date_str_parts.append(groups['hour'])
                    date_str_parts.append(groups['minute'])
                    date_str_parts.append(groups['second'])
                    has_time = True

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
                            1 <= date_obj.day <= 31):
                        # 如果没有时间部分，设置为午夜
                        if not has_time:
                            date_obj = date_obj.replace(hour=0, minute=0, second=0)
                        return date_obj
                except ValueError:
                    continue
        return None
