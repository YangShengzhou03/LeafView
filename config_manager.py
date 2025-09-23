import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    
    def __init__(self, config_file: str = "_internal/leafview_config.json", 
                 cache_file: str = "_internal/cache_location.json"):
        self.config_file = Path(config_file)
        self.cache_file = Path(cache_file)
        self.config = self._load_config()
        self.location_cache = self._load_location_cache()
    
    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "folders": [],
            "api_limits": {
                "gaode": {
                    "daily_calls": 0,
                    "last_reset_date": "",
                    "max_daily_calls": 500
                }
            },
            "settings": {}
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key in default_config:
                        if key not in config:
                            config[key] = default_config[key]
                        elif key == "api_limits":
                            # 确保api_limits结构完整
                            for api_name, api_defaults in default_config["api_limits"].items():
                                if api_name not in config["api_limits"]:
                                    config["api_limits"][api_name] = api_defaults
                                else:
                                    for field, default_value in api_defaults.items():
                                        if field not in config["api_limits"][api_name]:
                                            config["api_limits"][api_name][field] = default_value
                    return config
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载配置文件时出错了: {e}")
        
        return default_config
    
    def _load_location_cache(self) -> Dict[str, Any]:
        default_cache = {}
        
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载位置缓存文件时出错了: {e}")
        
        return default_cache
    
    def save_config(self) -> bool:
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            logger.error(f"保存配置文件时出错了: {e}")
            return False
    
    def save_location_cache(self) -> bool:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.location_cache, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            logger.error(f"保存位置缓存文件时出错了: {e}")
            return False
    
    def add_folder(self, folder_path: str, include_sub: bool = True) -> bool:
        folder_path = os.path.normpath(folder_path)
        
        for folder in self.config["folders"]:
            if folder["path"] == folder_path:
                return False
        
        self.config["folders"].append({
            "path": folder_path,
            "include_sub": include_sub
        })
        
        return self.save_config()
    
    def remove_folder(self, folder_path: str) -> bool:
        folder_path = os.path.normpath(folder_path)
        
        for i, folder in enumerate(self.config["folders"]):
            if folder["path"] == folder_path:
                self.config["folders"].pop(i)
                return self.save_config()
        
        return False
    
    def update_folder_include_sub(self, folder_path: str, include_sub: bool) -> bool:
        folder_path = os.path.normpath(folder_path)
        
        for folder in self.config["folders"]:
            if folder["path"] == folder_path:
                folder["include_sub"] = include_sub
                return self.save_config()
        
        return False
    
    def get_folders(self) -> List[Dict[str, Any]]:
        return self.config["folders"]
    
    def get_valid_folders(self) -> List[Dict[str, Any]]:
        valid_folders = []
        for folder in self.config["folders"]:
            if os.path.exists(folder["path"]) and os.path.isdir(folder["path"]):
                valid_folders.append(folder)
        return valid_folders
    
    def clear_invalid_folders(self) -> int:
        original_count = len(self.config["folders"])
        self.config["folders"] = self.get_valid_folders()
        removed_count = original_count - len(self.config["folders"])
        
        if removed_count > 0:
            self.save_config()
        
        return removed_count
    
    def cache_location(self, latitude: float, longitude: float, address: str) -> bool:
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        self.location_cache[cache_key] = {
            "address": address,
            "timestamp": int(os.path.getctime(self.cache_file)) if self.cache_file.exists() else 0
        }
        
        if len(self.location_cache) > 50000:
            cache_items = list(self.location_cache.items())
            cache_items.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
            self.location_cache = dict(cache_items[:25000])
        
        return self.save_location_cache()
    
    def get_cached_location(self, latitude: float, longitude: float) -> Optional[str]:
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        cached_data = self.location_cache.get(cache_key)
        
        if cached_data:
            return cached_data["address"]
        
        return None
    
    def get_cached_location_with_tolerance(self, latitude: float, longitude: float, tolerance: float = 0.01) -> Optional[str]:
        exact_match = self.get_cached_location(latitude, longitude)
        if exact_match:
            return exact_match
        
        for cache_key, cached_data in self.location_cache.items():
            try:
                cached_lat, cached_lon = map(float, cache_key.split(','))
                distance = ((latitude - cached_lat) ** 2 + (longitude - cached_lon) ** 2) ** 0.5
                if distance <= tolerance:
                    return cached_data["address"]
            except (ValueError, IndexError):
                continue
        
        return None
    
    def clear_location_cache(self) -> bool:
        self.location_cache = {}
        return self.save_location_cache()
    
    def clear_folders(self) -> bool:
        self.config["folders"] = []
        return self.save_config()
    
    def clear_locations(self) -> bool:
        self.location_cache = {}
        return self.save_location_cache()
    
    def update_setting(self, key: str, value: Any) -> bool:
        self.config["settings"][key] = value
        return self.save_config()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.config["settings"].get(key, default)
    
    def can_call_gaode_api(self) -> bool:
        """检查是否可以调用高德API（每日限制500次）"""
        import datetime
        
        # 获取当前日期
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 检查是否需要重置计数器
        gaode_config = self.config["api_limits"]["gaode"]
        if gaode_config["last_reset_date"] != current_date:
            # 重置计数器
            gaode_config["daily_calls"] = 0
            gaode_config["last_reset_date"] = current_date
            self.save_config()
        
        # 检查是否超过限制
        return gaode_config["daily_calls"] < gaode_config["max_daily_calls"]
    
    def record_gaode_api_call(self) -> bool:
        """记录一次高德API调用"""
        import datetime
        
        # 获取当前日期
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 检查是否需要重置计数器
        gaode_config = self.config["api_limits"]["gaode"]
        if gaode_config["last_reset_date"] != current_date:
            # 重置计数器
            gaode_config["daily_calls"] = 0
            gaode_config["last_reset_date"] = current_date
        
        # 增加调用计数
        gaode_config["daily_calls"] += 1
        
        return self.save_config()
    
    def get_gaode_api_stats(self) -> Dict[str, Any]:
        """获取高德API调用统计信息"""
        return self.config["api_limits"]["gaode"].copy()


config_manager = ConfigManager()
