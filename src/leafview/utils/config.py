"""配置管理模块

这个模块提供了LeafView应用程序的配置管理功能。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """配置管理类
    
    负责加载、保存和管理应用程序配置。
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 使用用户目录下的配置文件
            user_config_dir = Path.home() / ".leafview"
            user_config_dir.mkdir(exist_ok=True)
            self.config_path = user_config_dir / "config.json"
        else:
            self.config_path = Path(config_path)
        
        # 加载配置
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件
        
        Returns:
            配置字典
        """
        default_config = {
            "ui": {
                "window_size": {"width": 800, "height": 600},
                "window_position": {"x": 300, "y": 100},
                "theme": "default",
                "language": "zh_CN"
            },
            "performance": {
                "thumbnail_cache_size": 1000,
                "batch_update_interval": 100,
                "max_thread_count": 4
            },
            "features": {
                "auto_check_updates": True,
                "enable_geocoding": True,
                "backup_before_operation": True
            },
            "classification": {
                "default_structure": ["year", "month"],
                "default_operation": "move",
                "separator": "_"
            },
            "last_used": {
                "folders": [],
                "export_directory": str(Path.home() / "Pictures")
            }
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合并默认配置和用户配置
                    return self._merge_configs(default_config, user_config)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
        
        return default_config
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """合并默认配置和用户配置
        
        Args:
            default: 默认配置
            user: 用户配置
            
        Returns:
            合并后的配置
        """
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save(self) -> bool:
        """保存配置到文件
        
        Returns:
            保存是否成功
        """
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称
            value: 配置值
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取整个配置节
        
        Args:
            section: 配置节名称
            
        Returns:
            配置节字典
        """
        return self.config.get(section, {})
    
    def reset_to_defaults(self) -> None:
        """重置配置为默认值"""
        self.config = self._load_config()
        self.save()
    
    def reset_section(self, section: str) -> None:
        """重置指定配置节为默认值
        
        Args:
            section: 配置节名称
        """
        default_config = self._load_config()
        if section in default_config:
            self.config[section] = default_config[section]
            self.save()