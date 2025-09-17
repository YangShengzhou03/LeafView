"""
配置文件管理模块

负责应用程序配置的持久化存储和读取，包括：
1. 用户导入的文件夹路径
2. 地理位置查询缓存
3. 应用程序设置
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: str = "leafview_config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "folders": [],
            "location_cache": {},
            "settings": {}
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保配置包含所有必要的键
                    for key in default_config:
                        if key not in config:
                            config[key] = default_config[key]
                    return config
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载配置文件失败: {e}")
        
        return default_config
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def add_folder(self, folder_path: str, include_sub: bool = True) -> bool:
        """
        添加文件夹到配置
        
        Args:
            folder_path: 文件夹路径
            include_sub: 是否包含子文件夹
            
        Returns:
            bool: 是否成功添加
        """
        folder_path = os.path.normpath(folder_path)
        
        # 检查是否已存在
        for folder in self.config["folders"]:
            if folder["path"] == folder_path:
                return False
        
        self.config["folders"].append({
            "path": folder_path,
            "include_sub": include_sub
        })
        
        return self.save_config()
    
    def remove_folder(self, folder_path: str) -> bool:
        """
        从配置中移除文件夹
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            bool: 是否成功移除
        """
        folder_path = os.path.normpath(folder_path)
        
        for i, folder in enumerate(self.config["folders"]):
            if folder["path"] == folder_path:
                self.config["folders"].pop(i)
                return self.save_config()
        
        return False
    
    def update_folder_include_sub(self, folder_path: str, include_sub: bool) -> bool:
        """
        更新文件夹的包含子文件夹状态
        
        Args:
            folder_path: 文件夹路径
            include_sub: 是否包含子文件夹
            
        Returns:
            bool: 是否成功更新
        """
        folder_path = os.path.normpath(folder_path)
        
        for folder in self.config["folders"]:
            if folder["path"] == folder_path:
                folder["include_sub"] = include_sub
                return self.save_config()
        
        return False
    
    def get_folders(self) -> List[Dict[str, Any]]:
        """获取所有文件夹配置"""
        return self.config["folders"]
    
    def get_valid_folders(self) -> List[Dict[str, Any]]:
        """获取所有有效的文件夹（路径存在）"""
        valid_folders = []
        for folder in self.config["folders"]:
            if os.path.exists(folder["path"]) and os.path.isdir(folder["path"]):
                valid_folders.append(folder)
        return valid_folders
    
    def clear_invalid_folders(self) -> int:
        """
        清除无效的文件夹路径
        
        Returns:
            int: 清除的文件夹数量
        """
        original_count = len(self.config["folders"])
        self.config["folders"] = self.get_valid_folders()
        removed_count = original_count - len(self.config["folders"])
        
        if removed_count > 0:
            self.save_config()
        
        return removed_count
    
    def cache_location(self, latitude: float, longitude: float, address: str) -> bool:
        """
        缓存地理位置查询结果
        
        Args:
            latitude: 纬度
            longitude: 经度
            address: 地址信息
            
        Returns:
            bool: 是否成功缓存
        """
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        self.config["location_cache"][cache_key] = {
            "address": address,
            "timestamp": int(os.path.getctime(self.config_file)) if self.config_file.exists() else 0
        }
        
        # 限制缓存大小，避免文件过大
        if len(self.config["location_cache"]) > 1000:
            # 保留最近500个缓存
            cache_items = list(self.config["location_cache"].items())
            cache_items.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
            self.config["location_cache"] = dict(cache_items[:500])
        
        return self.save_config()
    
    def get_cached_location(self, latitude: float, longitude: float) -> Optional[str]:
        """
        获取缓存的地理位置信息
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            Optional[str]: 缓存的地址信息，如果没有缓存则返回None
        """
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        cached_data = self.config["location_cache"].get(cache_key)
        
        if cached_data:
            return cached_data["address"]
        
        return None
    
    def clear_location_cache(self) -> bool:
        """清空地理位置缓存"""
        self.config["location_cache"] = {}
        return self.save_config()
    
    def clear_folders(self) -> bool:
        """清空所有文件夹配置"""
        self.config["folders"] = []
        return self.save_config()
    
    def clear_locations(self) -> bool:
        """清空所有地理位置缓存"""
        self.config["location_cache"] = {}
        return self.save_config()
    
    def update_setting(self, key: str, value: Any) -> bool:
        """
        更新应用程序设置
        
        Args:
            key: 设置键名
            value: 设置值
            
        Returns:
            bool: 是否成功更新
        """
        self.config["settings"][key] = value
        return self.save_config()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取应用程序设置
        
        Args:
            key: 设置键名
            default: 默认值
            
        Returns:
            Any: 设置值
        """
        return self.config["settings"].get(key, default)


# 全局配置管理器实例
config_manager = ConfigManager()