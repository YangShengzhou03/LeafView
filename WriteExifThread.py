import os
import re
import time
import subprocess
import shutil
import tempfile
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime, timedelta

import piexif
from PIL import Image, PngImagePlugin
from PyQt6.QtCore import QThread, pyqtSignal

from common import detect_media_type, get_resource_path


class WriteExifThread(QThread):
    
    progress_updated = pyqtSignal(int)
    finished_conversion = pyqtSignal()
    log = pyqtSignal(str, str)

    def __init__(self, folders_dict, title='', author='', subject='', rating='', copyright='',
                 position='', shootTime='', cameraBrand=None, cameraModel=None, lensBrand=None, lensModel=None):
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
        self._stop_requested = False
        self.lat = None
        self.lon = None

        if position and ',' in position:
            try:
                self.lat, self.lon = map(float, position.split(','))
                if not (-90 <= self.lat <= 90) or not (-180 <= self.lon <= 180):
                    self.lat, self.lon = None, None
            except ValueError:
                pass

    def run(self):
        total_files = 0
        success_count = 0
        error_count = 0
        
        try:
            image_paths = self._collect_image_paths()
            total_files = len(image_paths)
            if not image_paths:
                self.log.emit("WARNING", "没有找到任何可以处理的图像文件\n\n"
                               "请检查：\n"
                               "• 您选择的文件夹路径是否正确\n"
                               "• 文件夹里是否有.jpg、.jpeg、.png、.webp等格式的图片")
                self.finished_conversion.emit()
                return
            
            self.log.emit("WARNING", f"开始处理 {total_files} 张图片")
            
            self.progress_updated.emit(0)
            
            with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as executor:
                futures = {}
                for path in image_paths:
                    if self._stop_requested:
                        break
                    try:
                        file_size = os.path.getsize(path)
                        if file_size > 500 * 1024 * 1024:
                            self.log.emit("ERROR", f"文件 {os.path.basename(path)} 太大了(超过500MB)，暂不支持处理")
                            error_count += 1
                            continue
                        futures[executor.submit(self.process_image, path)] = path
                    except Exception as e:
                        self.log.emit("ERROR", f"添加文件 {os.path.basename(path)} 到任务队列失败: {str(e)}")
                        error_count += 1
                
                if futures:
                    try:
                        for i, future in enumerate(as_completed(futures), 1):
                            if self._stop_requested:
                                for f in futures:
                                    f.cancel()
                                time.sleep(0.1)
                                self.log.emit("DEBUG", "EXIF写入操作已成功中止")
                                break
                            try:
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
                                progress = int((i / len(futures)) * 100)
                                self.progress_updated.emit(progress)
                    except Exception as e:
                        self.log.emit("ERROR", f"任务调度过程中发生错误: {str(e)}")
                        error_count += 1
        except Exception as e:
            self.log.emit("ERROR", f"全局错误: {str(e)}")
            error_count += 1
        finally:
            self.log("DEBUG", "=" * 40)
            self.log.emit("INFO", f"属性写入完成了，成功写入了 {success_count} 张，失败了 {error_count} 张，共 {total_files}。")
            self.log("DEBUG", "=" * 3 + "LeafAuto © 2025 Yangshengzhou.All Rights Reserved" + "=" * 3)
            self.finished_conversion.emit()

    def _collect_image_paths(self):
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.mov', '.mp4', '.avi', '.mkv', '.cr2', '.cr3', '.nef', '.arw', '.orf', '.dng', '.raf')
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
                self.log.emit("WARNING", f"处理被取消: {os.path.basename(image_path)}")
                return
            
            file_ext = os.path.splitext(image_path)[1].lower()
            
            if file_ext in ('.jpg', '.jpeg', '.webp'):
                self._process_exif_format(image_path)
            elif file_ext == '.png':
                self._process_png_format(image_path)
            elif file_ext in ('.heic', '.heif'):
                self._process_heic_format(image_path)
            elif file_ext in ('.mov', '.mp4', '.avi', '.mkv'):
                self._process_video_format(image_path)
            elif file_ext in ('.cr2', '.cr3', '.nef', '.arw', '.orf', '.dng', '.raf'):
                self._process_raw_format(image_path)
            else:
                self.log.emit("WARNING", f"不支持的文件格式: {file_ext}")

        except Exception as e:
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
        try:
            exif_dict = piexif.load(image_path)
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        
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
        
        if self.cameraBrand:
            exif_dict["0th"][piexif.ImageIFD.Make] = self.cameraBrand.encode('utf-8')
            updated_fields.append(f"相机品牌: {self.cameraBrand}")
        
        if self.cameraModel:
            exif_dict["0th"][piexif.ImageIFD.Model] = self.cameraModel.encode('utf-8')
            updated_fields.append(f"相机型号: {self.cameraModel}")
        
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
        
        if self.shootTime != 0:
            if self.shootTime == 1:
                date_from_filename = self.get_date_from_filename(image_path)
                if date_from_filename:
                    if "Exif" not in exif_dict:
                        exif_dict["Exif"] = {}
                    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_from_filename.strftime(
                        "%Y:%m:%d %H:%M:%S").encode('utf-8')
                    updated_fields.append(
                        f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
            else:
                try:
                    datetime.strptime(self.shootTime, "%Y:%m:%d %H:%M:%S")
                    if "Exif" not in exif_dict:
                        exif_dict["Exif"] = {}
                    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self.shootTime.encode('utf-8')
                    updated_fields.append(f"拍摄时间: {self.shootTime}")
                except ValueError:
                    self.log.emit("ERROR", f"拍摄时间格式无效: {self.shootTime}，请使用 YYYY:MM:DD HH:MM:SS 格式")
        
        if self.lat is not None and self.lon is not None:
            exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
            updated_fields.append(
                f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, {abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}")
        
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, image_path)
        
        if updated_fields:
            self.log.emit("INFO", f"写入成功 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
        else:
            self.log.emit("WARNING", f"未对 {os.path.basename(image_path)} 进行任何更改\n\n"
                             "可能的原因：\n"
                             "• 所有EXIF字段均为空")

    def _process_png_format(self, image_path):
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
                        self.log.emit("INFO", f"成功写入 {os.path.basename(image_path)} 的拍摄时间 {date_from_filename}")
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
                    self.log.emit("INFO", f"成功写入 {os.path.basename(image_path)} 的拍摄时间 {self.shootTime}")

    def _process_heic_format(self, image_path):
        try:
            from pillow_heif import open_heif, register_heif_opener
            register_heif_opener()
        except ImportError:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 需要 pillow-heif 库\n\n"
                             "请安装: pip install pillow-heif")
            return
        
        try:
            heif_file = open_heif(image_path)
            
            try:
                image = heif_file.to_pillow()
            except AttributeError:
                image = heif_file.to_pil()
            
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            if hasattr(heif_file, 'exif') and heif_file.exif:
                try:
                    heif_exif = piexif.load(heif_file.exif)
                    exif_dict.update(heif_exif)
                except Exception:
                    pass
            
            if hasattr(image, '_getexif') and image._getexif():
                try:
                    pil_exif = image._getexif()
                    if pil_exif:
                        tag_mapping = {
                            270: ("0th", piexif.ImageIFD.ImageDescription),
                            271: ("0th", piexif.ImageIFD.Make),
                            272: ("0th", piexif.ImageIFD.Model),
                            315: ("0th", 315),
                            36867: ("Exif", piexif.ExifIFD.DateTimeOriginal),
                            37378: ("Exif", piexif.ExifIFD.FNumber),
                            37386: ("Exif", piexif.ExifIFD.FocalLength),
                            42035: ("Exif", piexif.ExifIFD.LensMake),
                            41988: ("Exif", piexif.ExifIFD.LensModel),
                            42034: ("Exif", piexif.ExifIFD.LensSpecification),
                        }
                        
                        for tag_id, (section, piexif_tag) in tag_mapping.items():
                            if tag_id in pil_exif:
                                exif_dict[section][piexif_tag] = pil_exif[tag_id]
                except Exception:
                    pass
            
            if hasattr(image, 'info') and 'exif' in image.info:
                try:
                    info_exif = piexif.load(image.info['exif'])
                    exif_dict.update(info_exif)
                except Exception:
                    pass
            
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
                                42035: ("Exif", piexif.ExifIFD.LensMake),
                                41988: ("Exif", piexif.ExifIFD.LensModel),
                                42034: ("Exif", piexif.ExifIFD.LensSpecification),
                            }
                            
                            for tag_id, (section, piexif_tag) in tag_mapping.items():
                                if tag_id in pil_exif:
                                    exif_dict[section][piexif_tag] = pil_exif[tag_id]
            except Exception:
                pass
            
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
            
            if self.cameraBrand:
                exif_dict["0th"][piexif.ImageIFD.Make] = self.cameraBrand.encode('utf-8')
                updated_fields.append(f"相机品牌: {self.cameraBrand}")
            
            if self.cameraModel:
                exif_dict["0th"][piexif.ImageIFD.Model] = self.cameraModel.encode('utf-8')
                updated_fields.append(f"相机型号: {self.cameraModel}")
            
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
            
            if self.shootTime != 0:
                if self.shootTime == 1:
                    date_from_filename = self.get_date_from_filename(image_path)
                    if date_from_filename:
                        if "Exif" not in exif_dict:
                            exif_dict["Exif"] = {}
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_from_filename.strftime(
                            "%Y:%m:%d %H:%M:%S").encode('utf-8')
                        updated_fields.append(
                            f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
                else:
                    if "Exif" not in exif_dict:
                        exif_dict["Exif"] = {}
                    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self.shootTime.encode('utf-8')
                    updated_fields.append(f"拍摄时间: {self.shootTime}")
            
            if self.lat is not None and self.lon is not None:
                exif_dict["GPS"] = self._create_gps_data(self.lat, self.lon)
                updated_fields.append(
                    f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, {abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}")
            
            if updated_fields:
                try:
                    temp_path = image_path + ".tmp"
                    exif_bytes = piexif.dump(exif_dict)
                    image.save(temp_path, format="HEIF", exif=exif_bytes)
                    os.replace(temp_path, image_path)
                    self.log.emit("INFO", f"写入成功 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
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
        file_ext = os.path.splitext(image_path)[1].lower()
        
        if file_ext in ('.mov', '.mp4', '.avi', '.mkv'):
            self._process_video_with_exiftool(image_path)
        else:
            self.log.emit("WARNING", f"不支持的视频格式: {file_ext}")
    
    def _process_video_with_exiftool(self, image_path):
        
        if not os.path.exists(image_path):
            self.log.emit("ERROR", f"文件不存在: {image_path}")
            return
        temp_file_path = None
        original_file_path = image_path
        temp_dir = None
        has_non_ascii = any(ord(char) > 127 for char in image_path)
        
        if has_non_ascii:
            temp_dir = tempfile.mkdtemp(prefix="exiftool_temp_")
            temp_file_path = os.path.join(temp_dir, os.path.basename(image_path))
            shutil.copy2(image_path, temp_file_path)
            image_path = temp_file_path
        
        file_path_normalized = image_path.replace('\\', '/')
        exiftool_path = get_resource_path('resources/exiftool/exiftool.exe')
        cmd_parts = [exiftool_path, "-overwrite_original"]
        updated_fields = []
        
        if self.cameraBrand:
            cmd_parts.append(f'-Make="{self.cameraBrand}"')
            updated_fields.append(f"相机品牌: {self.cameraBrand}")
        
        if self.cameraModel:
            cmd_parts.append(f'-Model="{self.cameraModel}"')
            updated_fields.append(f"相机型号: {self.cameraModel}")
        
        if self.lat is not None and self.lon is not None:
            lat_dms = self.decimal_to_dms(self.lat)
            lon_dms = self.decimal_to_dms(self.lon)
            cmd_parts.append(f'-GPSLatitude="{lat_dms}"')
            cmd_parts.append(f'-GPSLongitude="{lon_dms}"')
            cmd_parts.append('-GPSLatitudeRef=N' if self.lat >= 0 else '-GPSLatitudeRef=S')
            cmd_parts.append('-GPSLongitudeRef=E' if self.lon >= 0 else '-GPSLongitudeRef=W')
            
            cmd_parts.append(f'-GPSCoordinates="{self.lat}, {self.lon}"')
            updated_fields.append(f"GPS坐标: {abs(self.lat):.6f}°{'N' if self.lat >= 0 else 'S'}, {abs(self.lon):.6f}°{'E' if self.lon >= 0 else 'W'}")
        
        if self.shootTime != 0:
            if self.shootTime == 1:
                date_from_filename = self.get_date_from_filename(original_file_path)
                if date_from_filename:
                    local_time = date_from_filename
                    utc_time = local_time - timedelta(hours=8)
                    actual_write_time = utc_time.strftime("%Y:%m:%d %H:%M:%S")
                    timezone_suffix = "+00:00"
                    cmd_parts.append(f'-CreateDate={actual_write_time}{timezone_suffix}')
                    cmd_parts.append(f'-CreationDate={actual_write_time}{timezone_suffix}')
                    cmd_parts.append(f'-MediaCreateDate={actual_write_time}{timezone_suffix}')
                    cmd_parts.append(f'-DateTimeOriginal={actual_write_time}{timezone_suffix}')
                    updated_fields.append(f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')} (已调整为UTC时间)")
            else:
                try:
                    datetime.strptime(self.shootTime, "%Y:%m:%d %H:%M:%S")
                    local_time = datetime.strptime(self.shootTime, "%Y:%m:%d %H:%M:%S")
                    utc_time = local_time - timedelta(hours=8)
                    actual_write_time = utc_time.strftime("%Y:%m:%d %H:%M:%S")
                    timezone_suffix = "+00:00"
                    cmd_parts.append(f'-CreateDate={actual_write_time}{timezone_suffix}')
                    cmd_parts.append(f'-CreationDate={actual_write_time}{timezone_suffix}')
                    cmd_parts.append(f'-MediaCreateDate={actual_write_time}{timezone_suffix}')
                    cmd_parts.append(f'-DateTimeOriginal={actual_write_time}{timezone_suffix}')
                    updated_fields.append(f"拍摄时间: {self.shootTime} (已调整为UTC时间)")
                except ValueError:
                    self.log.emit("ERROR", f"拍摄时间格式无效: {self.shootTime}，请使用 YYYY:MM:DD HH:MM:SS 格式")
        
        if self.title:
            cmd_parts.append(f'-Comment="{self.title}"')
            cmd_parts.append(f'-Description="{self.title}"')
            updated_fields.append(f"标题: {self.title}")
        
        if self.author:
            cmd_parts.append(f'-Artist="{self.author}"')
            updated_fields.append(f"作者: {self.author}")
        
        if self.subject:
            cmd_parts.append(f'-Subject="{self.subject}"')
            updated_fields.append(f"主题: {self.subject}")
        
        if self.copyright:
            cmd_parts.append(f'-Copyright="{self.copyright}"')
            updated_fields.append(f"版权: {self.copyright}")
        
        try:
            cmd_parts.append(file_path_normalized)
            
            result = subprocess.run(cmd_parts, capture_output=True, text=True, shell=False)
            
            if result.returncode != 0:
                self.log.emit("ERROR", f"写入EXIF数据失败: {result.stderr}")
                return False

            if updated_fields:
                self.log.emit("INFO", f"写入成功 {os.path.basename(original_file_path)}: {'; '.join(updated_fields)}")
            
            verify_cmd = [exiftool_path, '-CreateDate', '-CreationDate', '-MediaCreateDate', '-DateTimeOriginal', file_path_normalized]
            subprocess.run(verify_cmd, capture_output=True, text=True, shell=False)
            
            return True
            
        except Exception as e:
            self.log.emit("ERROR", f"执行exiftool命令时出错: {str(e)}")
            return False
        finally:
            if temp_file_path and os.path.exists(temp_file_path) and original_file_path != image_path:
                try:
                    shutil.copy2(temp_file_path, original_file_path)
                except Exception as e:
                    self.log.emit("ERROR", f"复制文件回原始路径失败: {str(e)}")
            
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    self.log.emit("WARNING", f"无法删除临时文件: {str(e)}")
            
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.log.emit("WARNING", f"无法删除临时目录: {str(e)}")

    def _process_raw_format(self, image_path):
        try:
            import rawpy
        except ImportError:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 需要 rawpy 库\n\n"
                             "请安装: pip install rawpy")
            return
        
        try:
            with rawpy.imread(image_path) as raw:
                updated_fields = []
                
                if self.shootTime != 0:
                    if self.shootTime == 1:
                        date_from_filename = self.get_date_from_filename(image_path)
                        if date_from_filename:
                            updated_fields.append(
                                f"文件名识别拍摄时间: {date_from_filename.strftime('%Y:%m:%d %H:%M:%S')}")
                    else:
                        updated_fields.append(f"拍摄时间: {self.shootTime}")
                
                if self.title:
                    updated_fields.append(f"标题: {self.title}")
                if self.author:
                    updated_fields.append(f"作者: {self.author}")
                
                if updated_fields:
                    self.log.emit("INFO", f"成功更新 {os.path.basename(image_path)}: {'; '.join(updated_fields)}")
                    self.log.emit("WARNING", f"RAW格式元数据写入需要额外工具支持，仅记录元数据信息")
                else:
                    self.log.emit("WARNING", f"未对 {os.path.basename(image_path)} 进行任何更改")
                    
        except Exception as e:
            self.log.emit("ERROR", f"处理 {os.path.basename(image_path)} 时出错: {str(e)}")

    def stop(self):
        self._stop_requested = True

    def decimal_to_dms(self, decimal):
        try:
            is_negative = decimal < 0
            decimal = abs(decimal)
            
            degrees = int(decimal)
            minutes_decimal = (decimal - degrees) * 60
            minutes = int(minutes_decimal)
            seconds = (minutes_decimal - minutes) * 60
            
            dms_str = f"{degrees} deg {minutes}' {seconds:.2f}\""
            
            return dms_str
        except Exception as e:
            self.log.emit("ERROR", f"坐标转换错误: {str(e)}")
            return str(decimal)

    def convert_dms_to_decimal(self, dms_str):
        try:
            import re
            
            pattern = r'(\d+) deg (\d+)\'( (\d+(?:\.\d+)?)\")? ([NSWE])'
            match = re.search(pattern, dms_str)
            
            if match:
                degrees = float(match.group(1))
                minutes = float(match.group(2))
                seconds = float(match.group(4)) if match.group(4) else 0.0
                direction = match.group(5)
                
                decimal = degrees + minutes/60 + seconds/3600
                
                if direction in ['S', 'W']:
                    decimal = -decimal
                    
                return decimal
            else:
                try:
                    return float(dms_str)
                except ValueError:
                    return None
                    
        except Exception as e:
            self.log.emit("ERROR", f"GPS坐标转换错误: {str(e)}")
            return None

    def _create_gps_data(self, lat, lon):
        def decimal_to_dms(decimal):
            degrees = int(abs(decimal))
            minutes_decimal = (abs(decimal) - degrees) * 60
            minutes = int(minutes_decimal)
            seconds = (minutes_decimal - minutes) * 60
            return [(degrees, 1), (minutes, 1), (int(seconds * 100), 100)]
        
        gps_dict = {}
        
        gps_dict[piexif.GPSIFD.GPSLatitude] = decimal_to_dms(abs(lat))
        gps_dict[piexif.GPSIFD.GPSLatitudeRef] = b'N' if lat >= 0 else b'S'
        
        gps_dict[piexif.GPSIFD.GPSLongitude] = decimal_to_dms(abs(lon))
        gps_dict[piexif.GPSIFD.GPSLongitudeRef] = b'E' if lon >= 0 else b'W'
        
        current_time = datetime.now()
        gps_dict[piexif.GPSIFD.GPSDateStamp] = current_time.strftime("%Y:%m:%d")
        gps_dict[piexif.GPSIFD.GPSTimeStamp] = [
            (current_time.hour, 1),
            (current_time.minute, 1),
            (current_time.second, 1)
        ]
        
        gps_dict[piexif.GPSIFD.GPSProcessingMethod] = b'GPS'
        
        return gps_dict

    def get_date_from_filename(self, image_path):
        base_name = os.path.basename(image_path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        date_pattern = r'(?P<year>\d{4})[年\-\.\/\s]?' \
                       r'(?P<month>1[0-2]|0?[1-9])[月\-\.\/\s]?' \
                       r'(?P<day>3[01]|[12]\d|0?[1-9])[日号\-\.\/\s]?' \
                       r'(?:[^0-9]*?)?' \
                       r'(?P<hour>[0-2]?\d)?' \
                       r'(?P<minute>[0-5]?\d)?' \
                       r'(?P<second>[0-5]?\d)?'
        
        match = re.search(date_pattern, name_without_ext)
        if not match:
            time_pattern = r'(?P<year>\d{4})[^\d]*(?P<month>1[0-2]|0?[1-9])[^\d]*(?P<day>3[01]|[12]\d|0?[1-9])[^\d]*(?P<hour>[0-2]?\d)(?P<minute>[0-5]\d)(?P<second>[0-5]\d)'
            match = re.search(time_pattern, name_without_ext)
        
        if match:
            groups = match.groupdict()
            if not all([groups.get('year'), groups.get('month'), groups.get('day')]):
                return None

            date_str_parts = [
                groups['year'],
                groups['month'].rjust(2, '0'),
                groups['day'].rjust(2, '0')
            ]
            
            has_time = False
            if groups.get('hour'):
                date_str_parts.append(groups['hour'].rjust(2, '0'))
                has_time = True
                if groups.get('minute'):
                    date_str_parts.append(groups['minute'].rjust(2, '0'))
                    if groups.get('second'):
                        date_str_parts.append(groups['second'].rjust(2, '0'))
                    elif len(groups.get('minute', '')) == 2 and len(groups.get('hour', '')) == 2:
                        remaining_text = name_without_ext[match.end():]
                        if remaining_text and remaining_text[:2].isdigit():
                            seconds = remaining_text[:2]
                            if 0 <= int(seconds) <= 59:
                                date_str_parts.append(seconds)
                                groups['second'] = seconds
            
            if not has_time:
                time_match = re.search(r'(?P<hour>[0-2]\d)(?P<minute>[0-5]\d)(?P<second>[0-5]\d)', name_without_ext)
                if time_match:
                    groups.update(time_match.groupdict())
                    date_str_parts.append(groups['hour'])
                    date_str_parts.append(groups['minute'])
                    date_str_parts.append(groups['second'])
                    has_time = True

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
                            1 <= date_obj.day <= 31):
                        if not has_time:
                            date_obj = date_obj.replace(hour=0, minute=0, second=0)
                        return date_obj
                except ValueError:
                    continue
        return None
