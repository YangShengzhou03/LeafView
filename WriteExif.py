import json
import os
import requests
from datetime import datetime
from PyQt6.QtCore import pyqtSlot, QDateTime
from PyQt6.QtWidgets import QWidget, QMessageBox
from WriteExifThread import WriteExifThread
from common import get_resource_path
from config_manager import config_manager


class WriteExif(QWidget):
    
    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.selected_star = 0
        self.worker = None
        self.star_buttons = []
        self.is_running = False
        self.camera_lens_mapping = {}
        self.error_messages = []
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
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
        
        self.init_camera_brand_model()
        
        self.load_camera_lens_mapping()
        
        self.update_button_state()
        self.parent.dateTimeEdit_shootTime.setDateTime(QDateTime.currentDateTime())
        self.load_exif_settings()
        self.save_exif_settings()
        self.log("DEBUG", "欢迎使用图像属性写入功能，不写入项留空即可。")
        
    def load_camera_lens_mapping(self):
        try:
            data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'resources', 'json', 'camera_lens_mapping.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    self.camera_lens_mapping = json.load(f)
            else:
                self.log("WARNING", "相机镜头映射文件不存在，将使用默认镜头信息")
        except Exception as e:
            self.log("WARNING", f"加载相机镜头映射数据失败: {str(e)}")
            self.camera_lens_mapping = {}

    def get_lens_info_for_camera(self, brand, model):
        if brand in self.camera_lens_mapping:
            brand_data = self.camera_lens_mapping[brand]
            if model in brand_data:
                return brand_data[model]
        return None

    def get_default_model_for_brand(self, brand):
        if brand in self.camera_data:
            models = self.camera_data[brand]
            if models:
                return models[0]
        return None

    def _on_model_changed(self, index):
        if index > 0:
            brand = self.parent.comboBox_brand.currentText()
            model = self.parent.comboBox_model.currentText()
            
            lens_info = self.get_lens_info_for_camera(brand, model)
            
            if lens_info:
                self.log("INFO", f"已自动设置镜头: {brand} {lens_info}")
            else:
                self.log("DEBUG", f"未找到 {brand} {model} 对应的镜头信息")
        
        self.update_button_state()
        self.parent.dateTimeEdit_shootTime.setDateTime(QDateTime.currentDateTime())
        self.parent.dateTimeEdit_shootTime.hide()


    def init_camera_brand_model(self):
        camera_data = self._load_camera_data()
        
        if not camera_data:
            camera_data = {
                "Apple": ["iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15", "iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14", "iPhone 13 Pro Max", "iPhone 13 Pro"],
                "Samsung": ["Galaxy S24 Ultra", "Galaxy S24+", "Galaxy S24", "Galaxy S23 Ultra", "Galaxy S23+", "Galaxy S23", "Galaxy Z Fold5", "Galaxy Z Flip5"],
                "Google": ["Pixel 8 Pro", "Pixel 8", "Pixel 7 Pro", "Pixel 7", "Pixel 6 Pro", "Pixel 6", "Pixel 5"],
                "OnePlus": ["12 Pro", "12", "11 Pro", "11", "10 Pro", "10", "9 Pro", "9"],
                "Xiaomi": ["14 Ultra", "14 Pro", "14", "13 Ultra", "13 Pro", "13", "12S Ultra", "12S Pro"],
                "Huawei": ["P60 Pro", "P60", "Mate 60 Pro", "Mate 60", "P50 Pro", "P50", "Mate 50 Pro", "Mate 50"],
                "OPPO": ["Find X6 Pro", "Find X6", "Find X5 Pro", "Find X5", "Reno10 Pro+", "Reno10 Pro", "Reno10", "Reno9 Pro+"],
                "Vivo": ["X100 Pro", "X100", "X90 Pro+", "X90 Pro", "X90", "X80 Pro", "X80", "S18 Pro"]
            }
        for brand in sorted(camera_data.keys()):
            self.parent.comboBox_brand.addItem(brand)
        
        self.camera_data = camera_data
        
        self.parent.comboBox_brand.currentIndexChanged.connect(self._on_brand_changed)
        self.parent.comboBox_model.currentIndexChanged.connect(self._on_model_changed)
        
    def _load_camera_data(self):
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
        self.parent.comboBox_model.clear()
        
        if index > 0:
            brand = self.parent.comboBox_brand.currentText()
            if brand in self.camera_data:
                for model in sorted(self.camera_data[brand]):
                    self.parent.comboBox_model.addItem(model)
        


    def setup_connections(self):
        self.parent.toolButton_StartEXIF.clicked.connect(self.toggle_exif_writing)
        self.parent.pushButton_Position.clicked.connect(self.update_position_by_ip)
        self.parent.comboBox_shootTime.currentIndexChanged.connect(self.on_combobox_time_changed)
        self.parent.comboBox_location.currentIndexChanged.connect(self.on_combobox_location_changed)
        
        self.parent.lineEdit_EXIF_Title.textChanged.connect(self.save_exif_settings)
        self.parent.lineEdit_EXIF_Author.textChanged.connect(self.save_exif_settings)
        self.parent.lineEdit_EXIF_Theme.textChanged.connect(self.save_exif_settings)
        self.parent.lineEdit_EXIF_Copyright.textChanged.connect(self.save_exif_settings)
        self.parent.lineEdit_EXIF_Position.textChanged.connect(self.save_exif_settings)
        self.parent.lineEdit_EXIF_latitude.textChanged.connect(self.save_exif_settings)
        self.parent.lineEdit_EXIF_longitude.textChanged.connect(self.save_exif_settings)
        
        self.parent.comboBox_brand.currentIndexChanged.connect(self.save_exif_settings)
        self.parent.comboBox_model.currentIndexChanged.connect(self.save_exif_settings)
        self.parent.comboBox_shootTime.currentIndexChanged.connect(self.save_exif_settings)
        self.parent.comboBox_location.currentIndexChanged.connect(self.save_exif_settings)
        
        for i in range(1, 6):
            getattr(self.parent, f'pushButton_star_{i}').clicked.connect(self.save_exif_settings)

    def on_combobox_location_changed(self, index):
        if index == 1:
            self.parent.lineEdit_EXIF_longitude.show()
            self.parent.lineEdit_EXIF_latitude.show()
            self.parent.horizontalFrame.hide()
        else:
            self.parent.lineEdit_EXIF_longitude.hide()
            self.parent.lineEdit_EXIF_latitude.hide()
            self.parent.horizontalFrame.show()

    def on_combobox_time_changed(self, index):
        if index == 2:
            self.parent.dateTimeEdit_shootTime.show()
        else:
            self.parent.dateTimeEdit_shootTime.hide()

    def update_button_state(self):
        if self.is_running:
            self.parent.toolButton_StartEXIF.setText("停止")
        else:
            self.parent.toolButton_StartEXIF.setText("开始")

    def toggle_exif_writing(self):
        if self.is_running:
            self.stop_exif_writing()
            self.is_running = False
        else:
            success = self.start_exif_writing()
            if success:
                self.is_running = True
        self.update_button_state()

    def connect_worker_signals(self):
        if self.worker:
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.log.connect(self.log)
            self.worker.finished_conversion.connect(self.on_finished)

    @pyqtSlot(int)
    def highlight_stars(self, count):
        for i, btn in enumerate(self.star_buttons, 1):
            icon = "星级_亮.svg" if i <= count else "星级_暗.svg"
            btn.setStyleSheet(f"QPushButton {{ image: url({get_resource_path(f'resources/img/page_4/{icon}')}); border: none; padding: 0; }}")

    @pyqtSlot(int)
    def set_selected_star(self, star):
        self.selected_star = star
        self.highlight_stars(star)

    def get_location(self, address):
        try:
            url = "https://restapi.amap.com/v3/geocode/geo"
            amap_key = '0db079da53e08cbb62b52a42f657b994'
            
            params = {
                'address': address, 
                'key': amap_key, 
                'output': 'JSON',
                'city': '全国'
            }
            
            self.log("INFO", f"正在请求高德地图API，地址: {address}")
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            self.log("INFO", f"高德地图API返回数据: {data}")
            
            if data.get('status') == '1' and int(data.get('count', 0)) > 0:
                location = data['geocodes'][0]['location'].split(',')
                self.log("INFO", f"成功获取位置坐标: 纬度={location[1]}, 经度={location[0]}")
                return location
            else:
                error_info = data.get('info', '未知错误')
                error_code = data.get('infocode', '未知错误码')
                self.log("ERROR", f"高德地图API返回错误: {error_info} (错误码: {error_code})")
                
                if len(address) > 10:
                    simplified_address = address[:10]
                    self.log("INFO", f"尝试使用简化地址再次请求: {simplified_address}")
                    params['address'] = simplified_address
                    response = requests.get(url, params=params, timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get('status') == '1' and int(data.get('count', 0)) > 0:
                        location = data['geocodes'][0]['location'].split(',')
                        self.log("INFO", f"使用简化地址成功获取位置坐标: 纬度={location[1]}, 经度={location[0]}")
                        return location
        except Exception as e:
            self.log("ERROR", f"获取位置失败: {str(e)}")
        return None

    def get_location_by_ip(self):
        try:
            response = requests.get('https://ipinfo.io', timeout=5)
            data = response.json()
            if 'loc' in data:
                lat, lon = data['loc'].split(',')
                location = f"{data.get('city', '')}, {data.get('region', '')}, {data.get('country', '')}"
                self.parent.lineEdit_EXIF_Position.setText(location)
                return lat, lon
            else:
                self.log("ERROR", "无法解析位置信息\n\n"
                             "IP地址定位服务返回的数据格式异常")
                return None
        except Exception as e:
            self.log("ERROR", f"获取位置信息失败: {str(e)}\n\n"
                         "请检查网络连接或稍后重试")
            return None

    def parse_dms_coordinates(self, lat_str, lon_str):
        try:
            lat_parts = lat_str.strip().replace(' ', '').split(';')
            if len(lat_parts) != 3:
                return None
                
            lat_deg = float(lat_parts[0])
            lat_min = float(lat_parts[1])
            lat_sec = float(lat_parts[2])
            
            lon_parts = lon_str.strip().replace(' ', '').split(';')
            if len(lon_parts) != 3:
                return None
                
            lon_deg = float(lon_parts[0])
            lon_min = float(lon_parts[1])
            lon_sec = float(lon_parts[2])
            
            lat_decimal = lat_deg + lat_min / 60 + lat_sec / 3600
            lon_decimal = lon_deg + lon_min / 60 + lon_sec / 3600
            
            if -90 <= lat_decimal <= 90 and -180 <= lon_decimal <= 180:
                return lat_decimal, lon_decimal
            else:
                return None
                
        except Exception as e:
            self.log("ERROR", f"解析度分秒坐标失败: {str(e)}")
            return None

    def update_position_by_ip(self):
        location_info = self.get_location_by_ip()
        if location_info is not None:
            lat, lon = location_info
            self.parent.lineEdit_EXIF_Position.setText(f"{lat}, {lon}")
            self.log("INFO", f"成功获取位置信息: 纬度={lat}, 经度={lon}")
            self.log("INFO", "坐标已设置到位置输入框，可以直接使用")
        else:
            self.log("ERROR", "获取位置信息失败\n\n"
                         "可能的原因：\n"
                         "• 网络连接异常\n"
                         "• 定位服务暂时不可用\n"
                         "• 防火墙或代理设置阻止了网络请求")

    def start_exif_writing(self):
        if not self.folder_page:
            self.log("ERROR", "文件夹页面未初始化\n\n"
                         "请重新启动应用程序或联系技术支持")
            return False
            
        folders = self.folder_page.get_all_folders()
        if not folders:
            self.log("WARNING", "请先导入一个有效的文件夹\n\n"
                           "点击\"导入文件夹\"按钮添加包含图片的文件夹")
            return False
        
        camera_brand = self.parent.comboBox_brand.currentText() if self.parent.comboBox_brand.currentIndex() > 0 else None
        camera_model = self.parent.comboBox_model.currentText() if self.parent.comboBox_model.currentIndex() > 0 else None
        
        if camera_brand and not camera_model:
            camera_model = self.get_default_model_for_brand(camera_brand)
        
        params = {
            'folders_dict': folders,
            'title': self.parent.lineEdit_EXIF_Title.text(),
            'author': self.parent.lineEdit_EXIF_Author.text(),
            'subject': self.parent.lineEdit_EXIF_Theme.text(),
            'rating': str(self.selected_star),
            'copyright': self.parent.lineEdit_EXIF_Copyright.text(),
            'position': None,
            'latitude': None,
            'longitude': None,
            'camera_brand': camera_brand,
            'camera_model': camera_model
        }
        
        time_option = self.parent.comboBox_shootTime.currentIndex()
        if time_option == 0:
            params['shoot_time'] = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
        elif time_option == 1:
            params['shoot_time'] = 'original'
        elif time_option == 2:
            custom_time = self.parent.dateTimeEdit_shootTime.dateTime().toString("yyyy:MM:dd HH:mm:ss")
            params['shoot_time'] = custom_time
        else:
            params['shoot_time'] = None
            
        location_option = self.parent.comboBox_location.currentIndex()
        if location_option == 0:
            params['position'] = None
            params['latitude'] = None
            params['longitude'] = None
        elif location_option == 1:
            lat_text = self.parent.lineEdit_EXIF_latitude.text().strip()
            lon_text = self.parent.lineEdit_EXIF_longitude.text().strip()
            
            if lat_text and lon_text:
                try:
                    lat_float = float(lat_text)
                    lon_float = float(lon_text)
                    
                    if -90 <= lat_float <= 90 and -180 <= lon_float <= 180:
                        params['latitude'] = lat_float
                        params['longitude'] = lon_float
                        self.log("INFO", f"已设置经纬度坐标: 纬度={lat_float}, 经度={lon_float}")
                    else:
                        self.log("ERROR", "经纬度值超出有效范围\n\n"
                                     "纬度范围: -90 到 90\n"
                                     "经度范围: -180 到 180")
                        return False
                except ValueError:
                    self.log("ERROR", "经纬度输入格式错误\n\n"
                                 "请输入有效的数字格式，例如: 39.9042")
                    return False
            else:
                self.log("WARNING", "经纬度输入不完整\n\n"
                               "请同时输入纬度和经度坐标")
                return False
        elif location_option == 2:
            address = self.parent.lineEdit_EXIF_Position.text().strip()
            if address:
                dms_coords = self.parse_dms_coordinates(lat_text, lon_text)
                if dms_coords:
                    lat_decimal, lon_decimal = dms_coords
                    params['latitude'] = lat_decimal
                    params['longitude'] = lon_decimal
                    self.log("INFO", f"已解析度分秒坐标: 纬度={lat_decimal}, 经度={lon_decimal}")
                else:
                    location = self.get_location(address)
                    if location:
                        params['latitude'] = float(location[1])
                        params['longitude'] = float(location[0])
                        params['position'] = address
                        self.log("INFO", f"已获取地址坐标: {address}")
                    else:
                        self.log("ERROR", "无法获取位置坐标\n\n"
                                     "请检查地址是否正确或尝试手动输入经纬度")
                        return False
            else:
                self.log("WARNING", "请输入位置信息\n\n"
                               "在文本框中输入地址或位置描述")
                return False
        
        try:
            self.worker = WriteExifThread(params)
            self.connect_worker_signals()
            self.worker.start()
            self.is_running = True
            self.log("INFO", "开始写入EXIF信息...")
            return True
        except Exception as e:
            self.log("ERROR", f"启动EXIF写入线程失败: {str(e)}")
            return False

    def stop_exif_writing(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.is_running = False
            self.log("INFO", "已停止EXIF写入操作")
        else:
            self.log("WARNING", "当前没有正在运行的EXIF写入任务")

    def update_progress(self, value):
        self.parent.progressBar.setValue(value)

    def log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        
        # Use parent's log method if available, otherwise use textEdit_WriteEXIF_Log
        if hasattr(self.parent, 'log'):
            self.parent.log(level, message)
        elif hasattr(self.parent, 'textEdit_WriteEXIF_Log'):
            self.parent.textEdit_WriteEXIF_Log.append(formatted_message)
        else:
            print(formatted_message)
        
        if level in ["ERROR", "WARNING"]:
            self.error_messages.append(formatted_message)
            
        if level == "ERROR":
            QMessageBox.critical(self.parent, "错误", message)
        elif level == "WARNING":
            QMessageBox.warning(self.parent, "警告", message)

    def on_finished(self, success_count, fail_count, total_count):
        self.is_running = False
        self.update_button_state()
        
        summary = self.generate_operation_summary(success_count, fail_count, total_count)
        
        if fail_count == 0:
            self.log("INFO", f"EXIF写入完成: {success_count}/{total_count} 个文件成功处理")
            QMessageBox.information(self.parent, "完成", summary)
        else:
            self.log("WARNING", f"EXIF写入完成: {success_count}/{total_count} 个文件成功处理, {fail_count} 个文件失败")
            error_detail = "\n\n".join(self.error_messages[-fail_count:]) if self.error_messages else ""
            QMessageBox.warning(self.parent, "完成", f"{summary}\n\n{error_detail}")
        
        self.error_messages.clear()

    def load_exif_settings(self):
        try:
            settings = config_manager.get_setting("exif_settings", {})
            if settings:
                self.parent.lineEdit_EXIF_Title.setText(settings.get("title", ""))
                self.parent.lineEdit_EXIF_Author.setText(settings.get("author", ""))
                self.parent.lineEdit_EXIF_Theme.setText(settings.get("subject", ""))
                self.parent.lineEdit_EXIF_Copyright.setText(settings.get("copyright", ""))
                self.parent.lineEdit_EXIF_Position.setText(settings.get("position", ""))
                self.parent.lineEdit_EXIF_latitude.setText(settings.get("latitude", ""))
                self.parent.lineEdit_EXIF_longitude.setText(settings.get("longitude", ""))
                
                brand = settings.get("camera_brand")
                model = settings.get("camera_model")
                if brand:
                    index = self.parent.comboBox_brand.findText(brand)
                    if index >= 0:
                        self.parent.comboBox_brand.setCurrentIndex(index)
                if model:
                    index = self.parent.comboBox_model.findText(model)
                    if index >= 0:
                        self.parent.comboBox_model.setCurrentIndex(index)
                        
                rating = settings.get("rating", "0")
                self.selected_star = int(rating)
                self.highlight_stars(self.selected_star)
                
                self.log("DEBUG", "已加载保存的EXIF设置")
        except Exception as e:
            self.log("WARNING", f"加载EXIF设置失败: {str(e)}")

    def save_exif_settings(self):
        try:
            settings = {
                "title": self.parent.lineEdit_EXIF_Title.text(),
                "author": self.parent.lineEdit_EXIF_Author.text(),
                "subject": self.parent.lineEdit_EXIF_Theme.text(),
                "rating": str(self.selected_star),
                "copyright": self.parent.lineEdit_EXIF_Copyright.text(),
                "position": self.parent.lineEdit_EXIF_Position.text(),
                "latitude": self.parent.lineEdit_EXIF_latitude.text(),
                "longitude": self.parent.lineEdit_EXIF_longitude.text(),
                "camera_brand": self.parent.comboBox_brand.currentText() if self.parent.comboBox_brand.currentIndex() > 0 else "",
                "camera_model": self.parent.comboBox_model.currentText() if self.parent.comboBox_model.currentIndex() > 0 else "",
            }
            config_manager.update_setting("exif_settings", settings)
        except Exception as e:
            self.log("WARNING", f"保存EXIF设置失败: {str(e)}")
