#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXIF写入功能模块

该模块提供了用于编辑和写入图像EXIF元数据的UI交互界面，包括：
- 星级评分系统
- 相机品牌和型号选择
- 拍摄时间设置
- 其他EXIF属性编辑

该模块通过WriteExifThread线程类执行实际的EXIF写入操作
"""
import json
import os
import requests
from datetime import datetime
from PyQt6.QtCore import pyqtSlot, QDateTime
from PyQt6.QtWidgets import QWidget
from WriteExifThread import WriteExifThread
from common import get_resource_path


class WriteExif(QWidget):
    """EXIF写入功能的主控制类，负责UI交互和参数传递"""
    
    def __init__(self, parent=None, folder_page=None):
        """
        初始化EXIF写入模块
        
        Args:
            parent: 父窗口组件
            folder_page: 文件夹页面实例，用于获取文件夹信息
        """
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.selected_star = 0  # 当前选中的星级评分
        self.worker = None  # EXIF写入工作线程
        self.star_buttons = []  # 星级按钮列表
        self.is_running = False  # 是否正在运行
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """初始化用户界面组件"""
        # 初始化星级评分按钮
        for i in range(1, 6):
            btn = getattr(self.parent, f'pushButton_star_{i}')
            btn.setStyleSheet(
                "QPushButton { "
                f"image: url({get_resource_path('resources/img/page_4/星级_暗.svg')});\n"
                "border: none; padding: 0; }" "\n"
                "QPushButton:hover { background-color: transparent; }"
            )
            btn.enterEvent = lambda e, idx=i: self.highlight_stars(idx)
            btn.leaveEvent = lambda e: self.highlight_stars(self.selected_star)
            btn.clicked.connect(lambda _, idx=i: self.set_selected_star(idx))
            self.star_buttons.append(btn)
        
        # 初始化相机品牌和型号下拉框
        self.init_camera_brand_model()
        
        self.update_button_state()
        self.parent.dateTimeEdit_shootTime.setDateTime(QDateTime.currentDateTime())
        self.parent.dateTimeEdit_shootTime.hide()
        # 初始化时隐藏经纬度文本框
        self.parent.lineEdit_EXIF_longitude.hide()
        self.parent.lineEdit_EXIF_latitude.hide()
        self.log("DEBUG", "欢迎使用图像属性写入功能，不写入项目留空即可。")
        
    def init_camera_brand_model(self):
        """初始化相机品牌和型号下拉框"""
        # 尝试从JSON文件加载相机品牌和型号数据
        camera_data = self._load_camera_data()
        
        # 如果没有加载到数据，使用默认数据
        if not camera_data:
            camera_data = {
                "佳能": ["EOS R5", "EOS R6", "EOS 5D Mark IV", "EOS 90D"],
                "尼康": ["Z7 II", "Z6 II", "D850", "D750"],
                "索尼": ["A7R IV", "A7S III", "A7 III", "A6400"],
                "富士": ["X-T4", "X-T3", "X-Pro3", "X100V"],
                "徕卡": ["Q2", "M11", "SL2-S", "CL"],
                "松下": ["S1R", "S1H", "GH5", "G9"],
                "奥林巴斯": ["OM-1", "EM-1 Mark III", "EM-5 Mark III"],
                "宾得": ["K-1 II", "K-3 Mark III", "KP"]
            }
        for brand in sorted(camera_data.keys()):
            self.parent.comboBox_brand.addItem(brand)
        
        # 存储相机数据
        self.camera_data = camera_data
        
        # 连接品牌选择变化信号
        self.parent.comboBox_brand.currentIndexChanged.connect(self._on_brand_changed)
        
    def _load_camera_data(self):
        """从JSON文件加载相机品牌和型号数据"""
        try:
            data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'resources', 'json', 'camera_brand_model.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log("WARNING", f"加载相机品牌型号数据失败: {str(e)}")
        return None
        
    def _on_brand_changed(self, index):
        """当相机品牌选择变化时，更新型号下拉框"""
        # 清空型号下拉框
        self.parent.comboBox_model.clear()
        
        # 如果选择了具体品牌，添加对应的型号
        if index > 0:
            brand = self.parent.comboBox_brand.currentText()
            if brand in self.camera_data:
                for model in sorted(self.camera_data[brand]):
                    self.parent.comboBox_model.addItem(model)

    def setup_connections(self):
        """设置信号和槽的连接"""
        self.parent.toolButton_StartEXIF.clicked.connect(self.toggle_exif_writing)
        self.parent.pushButton_Position.clicked.connect(self.update_position_by_ip)
        self.parent.comboBox_shootTime.currentIndexChanged.connect(self.on_combobox_time_changed)
        # 添加位置下拉框的信号连接
        self.parent.comboBox_location.currentIndexChanged.connect(self.on_combobox_location_changed)

    def on_combobox_location_changed(self, index):
        """位置下拉框选择变化处理"""
        if index == 1:  # 选择"经纬度"
            # 显示经纬度文本框，隐藏位置输入框
            self.parent.lineEdit_EXIF_longitude.show()
            self.parent.lineEdit_EXIF_latitude.show()
            self.parent.horizontalFrame.hide()  # 隐藏位置输入框和按钮
        else:  # 选择"搜位置"或其他
            # 隐藏经纬度文本框，显示位置输入框
            self.parent.lineEdit_EXIF_longitude.hide()
            self.parent.lineEdit_EXIF_latitude.hide()
            self.parent.horizontalFrame.show()  # 显示位置输入框和按钮

    def on_combobox_time_changed(self, index):
        """拍摄时间下拉框选择变化处理"""
        if index == 2:
            self.parent.dateTimeEdit_shootTime.show()
        else:
            self.parent.dateTimeEdit_shootTime.hide()

    def update_button_state(self):
        """更新开始/停止按钮状态"""
        if self.is_running:
            self.parent.toolButton_StartEXIF.setText("停止")
        else:
            self.parent.toolButton_StartEXIF.setText("开始")

    def toggle_exif_writing(self):
        """切换EXIF写入状态"""
        if self.is_running:
            self.stop_exif_writing()
            self.is_running = False
        else:
            success = self.start_exif_writing()
            if success:
                self.is_running = True
        self.update_button_state()

    def connect_worker_signals(self):
        """连接工作线程的信号"""
        if self.worker:
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.log.connect(self.log)
            self.worker.finished_conversion.connect(self.on_finished)

    @pyqtSlot(int)
    def highlight_stars(self, count):
        """高亮显示指定数量的星级"""
        for i, btn in enumerate(self.star_buttons, 1):
            icon = "星级_亮.svg" if i <= count else "星级_暗.svg"
            btn.setStyleSheet(f"QPushButton {{ image: url({get_resource_path(f'resources/img/page_4/{icon}')}); border: none; padding: 0; }}")

    @pyqtSlot(int)
    def set_selected_star(self, star):
        """设置选中的星级"""
        self.selected_star = star
        self.highlight_stars(star)

    def get_location(self, address):
        """
        通过高德地图API获取地址的地理坐标
        
        Args:
            address: 地址字符串
            
        Returns:
            tuple: (纬度, 经度)坐标，失败返回None
        """
        try:
            url = "https://restapi.amap.com/v3/geocode/geo"
            # 从环境变量中获取API密钥，避免硬编码
            amap_key = os.environ.get('AMAP_API_KEY', 'default_key')
            
            if amap_key == 'default_key':
                self.log("ERROR", "请设置AMAP_API_KEY环境变量")
                return None
                
            params = {'address': address, 'key': amap_key, 'output': 'JSON'}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == '1' and int(data.get('count', 0)) > 0:
                return data['geocodes'][0]['location'].split(',')
        except Exception as e:
            self.log("ERROR", f"获取位置失败: {str(e)}")
        return None

    def get_location_by_ip(self):
        """通过IP地址获取当前位置信息"""
        try:
            response = requests.get('https://ipinfo.io', timeout=5)
            data = response.json()
            if 'loc' in data:
                lat, lon = data['loc'].split(',')
                location = f"{data.get('city', '')}, {data.get('region', '')}, {data.get('country', '')}"
                self.parent.lineEdit_EXIF_Position.setText(location)
                return lat, lon
            else:
                self.log("ERROR", "无法解析位置信息")
                return None
        except Exception as e:
            self.log("ERROR", f"获取位置失败: {str(e)}")
            return None

    def update_position_by_ip(self):
        """通过IP地址更新位置信息"""
        location_info = self.get_location_by_ip()
        if location_info is not None:
            lat, lon = location_info
            self.log("INFO", f"成功获取位置信息: 纬度={lat}, 经度={lon}")
        else:
            self.log("ERROR", "获取位置信息失败，请检查网络连接。")

    def start_exif_writing(self):
        """
        开始EXIF写入操作
        
        Returns:
            bool: 是否成功启动
        """
        if not self.folder_page:
            self.log("ERROR", "文件夹页面未初始化")
            return False
            
        folders = self.folder_page.get_all_folders()
        if not folders:
            self.log("WARNING", "请先导入一个有效的文件夹。")
            return False
        
        # 准备EXIF写入参数
        params = {
            'folders_dict': folders,
            'autoMark': self.parent.checkBox_autoMark.isChecked(),
            'title': self.parent.lineEdit_EXIF_Title.text(),
            'author': self.parent.lineEdit_EXIF_Author.text(),
            'subject': self.parent.lineEdit_EXIF_Theme.text(),
            'rating': str(self.selected_star),
            'copyright': self.parent.lineEdit_EXIF_Copyright.text(),
            'position': None,
            'shootTime': self.parent.dateTimeEdit_shootTime.dateTime().toString(
                "yyyy:MM:dd HH:mm:ss")
            if self.parent.comboBox_shootTime.currentIndex() == 2
            else self.parent.comboBox_shootTime.currentIndex(),
            # 添加相机品牌和型号信息
            'cameraBrand': self.parent.comboBox_brand.currentText() if self.parent.comboBox_brand.currentIndex() > 0 else None,
            'cameraModel': self.parent.comboBox_model.currentText() if self.parent.comboBox_model.currentIndex() > 0 else None
        }
        
        # 处理位置信息
        location_type = self.parent.comboBox_location.currentIndex()
        if location_type == 0:  # 搜位置
            address = self.parent.lineEdit_EXIF_Position.text()
            if address:
                if coords := self.get_location(address):
                    params['position'] = ','.join(coords)
                else:
                    self.log("ERROR", f"无法找到地址'{address}'对应的地理坐标")
                    return False
        elif location_type == 1:  # 经纬度
            longitude = self.parent.lineEdit_EXIF_longitude.text()
            latitude = self.parent.lineEdit_EXIF_latitude.text()
            if longitude and latitude:
                # 验证经纬度格式
                try:
                    lon = float(longitude)
                    lat = float(latitude)
                    if -180 <= lon <= 180 and -90 <= lat <= 90:
                        params['position'] = f"{lat},{lon}"
                    else:
                        self.log("ERROR", "经纬度范围无效，经度应在-180到180之间，纬度应在-90到90之间")
                        return False
                except ValueError:
                    self.log("ERROR", "经纬度格式无效，请输入有效的数字")
                    return False
            else:
                self.log("ERROR", "请输入经纬度信息")
                return False
        
        # 创建并启动工作线程
        self.worker = WriteExifThread(**params)
        self.connect_worker_signals()
        self.worker.start()
        self.parent.progressBar_EXIF.setValue(0)
        return True

    def stop_exif_writing(self):
        """停止EXIF写入操作"""
        if self.worker:
            self.worker.stop()
            self.worker.wait(1000)
            if self.worker.isRunning():
                self.worker.terminate()
            self.log("WARNING", "正在停止EXIF写入。")
        self.is_running = False
        self.update_button_state()

    def update_progress(self, value):
        """更新进度条"""
        self.parent.progressBar_EXIF.setValue(value)

    def log(self, level, message):
        """
        记录日志信息
        
        Args:
            level: 日志级别 (ERROR, WARNING, DEBUG, INFO)
            message: 日志消息
        """
        c = {'ERROR': '#FF0000', 'WARNING': '#FFA500', 'DEBUG': '#008000', 'INFO': '#8677FD'}
        self.parent.textEdit_WriteEXIF_Log.append(
            f'<span style="color:{c.get(level, "#000000")}">[{datetime.now().strftime("%H:%M:%S")}] [{level}] {message}</span>')

    def on_finished(self):
        """EXIF写入完成处理"""
        self.log("DEBUG", "EXIF信息写入任务结束!")
        self.is_running = False
        self.update_button_state()
