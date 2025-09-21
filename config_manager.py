import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    
    def __init__(self, config_file: str = "_internal/leafview_config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "folders": [],
            "location_cache": {},
            "settings": {}
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key in default_config:
                        if key not in config:
                            config[key] = default_config[key]
                    return config
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载配置文件时出错了: {e}")
        
        return default_config
    
    def save_config(self) -> bool:
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            logger.error(f"保存配置文件时出错了: {e}")
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
        self.config["location_cache"][cache_key] = {
            "address": address,
            "timestamp": int(os.path.getctime(self.config_file)) if self.config_file.exists() else 0
        }
        
        if len(self.config["location_cache"]) > 10000:
            cache_items = list(self.config["location_cache"].items())
            cache_items.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
            self.config["location_cache"] = dict(cache_items[:5000])
        
        return self.save_config()
    
    def get_cached_location(self, latitude: float, longitude: float) -> Optional[str]:
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        cached_data = self.config["location_cache"].get(cache_key)
        
        if cached_data:
            return cached_data["address"]
        
        return None
    
    def get_cached_location_with_tolerance(self, latitude: float, longitude: float, tolerance: float = 0.01) -> Optional[str]:
        exact_match = self.get_cached_location(latitude, longitude)
        if exact_match:
            return exact_match
        
        for cache_key, cached_data in self.config["location_cache"].items():
            try:
                cached_lat, cached_lon = map(float, cache_key.split(','))
                distance = ((latitude - cached_lat) ** 2 + (longitude - cached_lon) ** 2) ** 0.5
                if distance <= tolerance:
                    return cached_data["address"]
            except (ValueError, IndexError):
                continue
        
        return None
    
    def clear_location_cache(self) -> bool:
        self.config["location_cache"] = {}
        return self.save_config()
    
    def clear_folders(self) -> bool:
        self.config["folders"] = []
        return self.save_config()
    
    def clear_locations(self) -> bool:
        self.config["location_cache"] = {}
        return self.save_config()
    
    def update_setting(self, key: str, value: Any) -> bool:
        self.config["settings"][key] = value
        return self.save_config()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.config["settings"].get(key, default)


config_manager = ConfigManager()