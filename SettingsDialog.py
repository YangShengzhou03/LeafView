"""
设置对话框模块

提供应用程序设置功能，包括API密钥配置
"""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox


class SettingsDialog(QDialog):
    """设置对话框类，用于配置应用程序设置"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("应用程序设置")
        self.setFixedSize(500, 300)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("API密钥设置")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 分隔线
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(line)
        
        # 石盾科技API设置
        stonedt_label = QLabel("石盾科技API")
        stonedt_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(stonedt_label)
        
        # Secret ID
        id_layout = QHBoxLayout()
        id_label = QLabel("Secret ID:")
        id_label.setFixedWidth(80)
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("请输入石盾科技Secret ID")
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.id_edit)
        layout.addLayout(id_layout)
        
        # Secret Key
        key_layout = QHBoxLayout()
        key_label = QLabel("Secret Key:")
        key_label.setFixedWidth(80)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入石盾科技Secret Key")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_edit)
        layout.addLayout(key_layout)
        
        # 高德地图API设置
        amap_label = QLabel("高德地图API")
        amap_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(amap_label)
        
        # API Key
        amap_layout = QHBoxLayout()
        amap_key_label = QLabel("API Key:")
        amap_key_label.setFixedWidth(80)
        self.amap_key_edit = QLineEdit()
        self.amap_key_edit.setPlaceholderText("请输入高德地图API Key")
        amap_layout.addWidget(amap_key_label)
        amap_layout.addWidget(self.amap_key_edit)
        layout.addLayout(amap_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """加载当前设置"""
        # 从环境变量加载石盾科技API密钥
        secret_id = os.environ.get('STONEDT_SECRET_ID', '')
        secret_key = os.environ.get('STONEDT_SECRET_KEY', '')
        
        # 从环境变量加载高德地图API密钥
        amap_key = os.environ.get('AMAP_API_KEY', '')
        
        self.id_edit.setText(secret_id)
        self.key_edit.setText(secret_key)
        self.amap_key_edit.setText(amap_key)
    
    def save_settings(self):
        """保存设置到环境变量"""
        secret_id = self.id_edit.text().strip()
        secret_key = self.key_edit.text().strip()
        amap_key = self.amap_key_edit.text().strip()
        
        # 验证石盾科技API密钥
        if secret_id and not secret_key:
            QMessageBox.warning(self, "警告", "请输入完整的石盾科技API密钥")
            return
        if secret_key and not secret_id:
            QMessageBox.warning(self, "警告", "请输入完整的石盾科技API密钥")
            return
        
        try:
            # 设置环境变量（当前会话有效）
            if secret_id and secret_key:
                os.environ['STONEDT_SECRET_ID'] = secret_id
                os.environ['STONEDT_SECRET_KEY'] = secret_key
            else:
                # 如果清空了密钥，移除环境变量
                if 'STONEDT_SECRET_ID' in os.environ:
                    del os.environ['STONEDT_SECRET_ID']
                if 'STONEDT_SECRET_KEY' in os.environ:
                    del os.environ['STONEDT_SECRET_KEY']
            
            # 设置高德地图API密钥
            if amap_key:
                os.environ['AMAP_API_KEY'] = amap_key
            elif 'AMAP_API_KEY' in os.environ:
                del os.environ['AMAP_API_KEY']
            
            QMessageBox.information(self, "成功", "设置已保存！\n\n注意：这些设置仅在当前应用程序会话中有效。")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置时出错: {str(e)}")

    def get_settings(self):
        """获取当前设置"""
        return {
            'stonedt_secret_id': self.id_edit.text().strip(),
            'stonedt_secret_key': self.key_edit.text().strip(),
            'amap_api_key': self.amap_key_edit.text().strip()
        }