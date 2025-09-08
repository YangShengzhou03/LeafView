"""媒体项模型模块

这个模块定义了LeafView应用程序中使用的媒体项数据模型。
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image
import filetype


class MediaItem:
    """媒体项类
    
    表示一个媒体文件（图片或视频），包含其元数据和相关信息。
    """
    
    def __init__(self, file_path: str):
        """初始化媒体项
        
        Args:
            file_path: 媒体文件路径
        """
        self.file_path = Path(file_path)
        self.filename = self.file_path.name
        self.file_size = self.file_path.stat().st_size if self.file_path.exists() else 0
        
        # 检测媒体类型
        self.media_type = self._detect_media_type()
        
        # 初始化属性
        self.thumbnail_path = None
        self.creation_date = None
        self.modification_date = None
        self.exif_data = {}
        self.hash_value = None
        self.is_screenshot = False
        self.tags = []
        
        # 延迟加载属性
        self._thumbnail_loaded = False
        self._exif_loaded = False
        self._hash_calculated = False
    
    def _detect_media_type(self) -> str:
        """检测媒体类型
        
        Returns:
            媒体类型字符串
        """
        if not self.file_path.exists():
            return "unknown"
        
        kind = filetype.guess(str(self.file_path))
        if kind is None:
            return "unknown"
        
        if kind.mime.startswith('image/'):
            return "image"
        elif kind.mime.startswith('video/'):
            return "video"
        else:
            return "unknown"
    
    def load_thumbnail(self, thumbnail_dir: Path, size: tuple = (200, 200)) -> Optional[str]:
        """加载或创建缩略图
        
        Args:
            thumbnail_dir: 缩略图存储目录
            size: 缩略图尺寸
            
        Returns:
            缩略图路径，如果创建失败则返回None
        """
        if self._thumbnail_loaded and self.thumbnail_path:
            return self.thumbnail_path
        
        # 确保缩略图目录存在
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建缩略图文件名
        file_hash = self.get_hash()
        thumbnail_filename = f"{file_hash}_{size[0]}x{size[1]}.jpg"
        thumbnail_path = thumbnail_dir / thumbnail_filename
        
        # 如果缩略图已存在，直接返回
        if thumbnail_path.exists():
            self.thumbnail_path = str(thumbnail_path)
            self._thumbnail_loaded = True
            return self.thumbnail_path
        
        # 创建缩略图
        try:
            if self.media_type == "image":
                # 使用PIL创建图像缩略图
                with Image.open(self.file_path) as img:
                    img.thumbnail(size)
                    img.save(thumbnail_path, "JPEG", quality=85)
                    self.thumbnail_path = str(thumbnail_path)
                    self._thumbnail_loaded = True
                    return self.thumbnail_path
            elif self.media_type == "video":
                # 对于视频，可以使用OpenCV或其他库提取第一帧作为缩略图
                # 这里简化处理，直接返回None
                # 实际实现可以使用OpenCV或ffmpeg提取视频帧
                pass
        except Exception as e:
            print(f"创建缩略图失败: {e}")
        
        return None
    
    def load_exif_data(self) -> Dict[str, Any]:
        """加载EXIF数据
        
        Returns:
            EXIF数据字典
        """
        if self._exif_loaded:
            return self.exif_data
        
        if self.media_type != "image" or not self.file_path.exists():
            self._exif_loaded = True
            return self.exif_data
        
        try:
            with Image.open(self.file_path) as img:
                # 获取EXIF数据
                exif_data = img._getexif()
                if exif_data:
                    # 转换EXIF标签ID为可读名称
                    from PIL.ExifTags import TAGS
                    self.exif_data = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
                    
                    # 解析日期时间
                    if 'DateTimeOriginal' in self.exif_data:
                        try:
                            self.creation_date = datetime.strptime(
                                self.exif_data['DateTimeOriginal'],
                                '%Y:%m:%d %H:%M:%S'
                            )
                        except ValueError:
                            pass
        except Exception as e:
            print(f"加载EXIF数据失败: {e}")
        
        self._exif_loaded = True
        return self.exif_data
    
    def get_creation_date(self) -> Optional[datetime]:
        """获取创建日期
        
        Returns:
            创建日期，如果无法获取则返回None
        """
        if self.creation_date:
            return self.creation_date
        
        # 尝试从文件属性获取创建日期
        try:
            stat = self.file_path.stat()
            creation_time = stat.st_ctime
            self.creation_date = datetime.fromtimestamp(creation_time)
        except Exception:
            pass
        
        return self.creation_date
    
    def get_modification_date(self) -> Optional[datetime]:
        """获取修改日期
        
        Returns:
            修改日期，如果无法获取则返回None
        """
        if self.modification_date:
            return self.modification_date
        
        # 尝试从文件属性获取修改日期
        try:
            stat = self.file_path.stat()
            modification_time = stat.st_mtime
            self.modification_date = datetime.fromtimestamp(modification_time)
        except Exception:
            pass
        
        return self.modification_date
    
    def get_hash(self) -> str:
        """获取文件哈希值
        
        Returns:
            文件的MD5哈希值
        """
        if self._hash_calculated and self.hash_value:
            return self.hash_value
        
        if not self.file_path.exists():
            return ""
        
        try:
            hash_md5 = hashlib.md5()
            with open(self.file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            self.hash_value = hash_md5.hexdigest()
            self._hash_calculated = True
        except Exception as e:
            print(f"计算文件哈希失败: {e}")
            self.hash_value = ""
        
        return self.hash_value
    
    def is_duplicate(self, other: 'MediaItem') -> bool:
        """检查是否与其他媒体项重复
        
        Args:
            other: 另一个媒体项
            
        Returns:
            如果重复则返回True，否则返回False
        """
        if self.file_size != other.file_size:
            return False
        
        return self.get_hash() == other.get_hash()
    
    def get_year(self) -> Optional[int]:
        """获取年份
        
        Returns:
            年份，如果无法获取则返回None
        """
        creation_date = self.get_creation_date()
        return creation_date.year if creation_date else None
    
    def get_month(self) -> Optional[int]:
        """获取月份
        
        Returns:
            月份，如果无法获取则返回None
        """
        creation_date = self.get_creation_date()
        return creation_date.month if creation_date else None
    
    def get_day(self) -> Optional[int]:
        """获取日期
        
        Returns:
            日期，如果无法获取则返回None
        """
        creation_date = self.get_creation_date()
        return creation_date.day if creation_date else None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            媒体项的字典表示
        """
        return {
            "file_path": str(self.file_path),
            "filename": self.filename,
            "file_size": self.file_size,
            "media_type": self.media_type,
            "creation_date": self.get_creation_date().isoformat() if self.get_creation_date() else None,
            "modification_date": self.get_modification_date().isoformat() if self.get_modification_date() else None,
            "year": self.get_year(),
            "month": self.get_month(),
            "day": self.get_day(),
            "hash_value": self.get_hash(),
            "is_screenshot": self.is_screenshot,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaItem':
        """从字典创建媒体项
        
        Args:
            data: 媒体项字典
            
        Returns:
            媒体项实例
        """
        item = cls(data["file_path"])
        
        # 设置属性
        if "creation_date" in data and data["creation_date"]:
            item.creation_date = datetime.fromisoformat(data["creation_date"])
        
        if "modification_date" in data and data["modification_date"]:
            item.modification_date = datetime.fromisoformat(data["modification_date"])
        
        if "hash_value" in data:
            item.hash_value = data["hash_value"]
            item._hash_calculated = True
        
        if "is_screenshot" in data:
            item.is_screenshot = data["is_screenshot"]
        
        if "tags" in data:
            item.tags = data["tags"]
        
        return item