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
        self.parent.dateTimeEdit_shootTime.hide()
        self.parent.lineEdit_EXIF_longitude.hide()
        self.parent.lineEdit_EXIF_latitude.hide()
        self.load_exif_settings()
        self.save_exif_settings()
        self.log("INFO", "欢迎使用图像属性写入，不写入项留空即可。文件一旦写入无法还原。")
        
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
            self.get_lens_info_for_camera(brand, model)
        
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
            self.log("WARNING", f"当前纬度={lat}, 经度={lon}，位置已加载，可直接开始。")
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
            'shootTime': self.parent.dateTimeEdit_shootTime.dateTime().toString(
                "yyyy:MM:dd HH:mm:ss")
            if self.parent.comboBox_shootTime.currentIndex() == 2
            else self.parent.comboBox_shootTime.currentIndex(),
            'cameraBrand': camera_brand,
            'cameraModel': camera_model,
            'lensModel': self.get_lens_info_for_camera(camera_brand, camera_model)
        }
        
        location_type = self.parent.comboBox_location.currentIndex()
        if location_type == 0:
            address = self.parent.lineEdit_EXIF_Position.text()
            if address:
                import re
                coord_pattern = r'^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$'
                coord_match = re.match(coord_pattern, address)
                
                if coord_match:
                    lat, lon = coord_match.groups()
                    try:
                        lat_float = float(lat)
                        lon_float = float(lon)
                        if -90 <= lat_float <= 90 and -180 <= lon_float <= 180:
                            params['position'] = f"{lat_float},{lon_float}"
                        else:
                            self.log("ERROR", "坐标范围无效\n\n"
                                     "• 经度应在-180到180之间\n"
                                     "• 纬度应在-90到90之间")
                            return False
                    except ValueError:
                        self.log("ERROR", "坐标格式无效\n\n"
                                 "请输入有效的数字格式")
                        return False
                else:
                    dms_pattern = r'纬度\s*([0-9;.\s]+)\s*经度\s*([0-9;.\s]+)'
                    dms_match = re.match(dms_pattern, address)
                    
                    if not dms_match:
                        dms_pattern = r'([0-9;.\s]+)\s*,\s*([0-9;.\s]+)'
                        dms_match = re.match(dms_pattern, address)
                    
                    if dms_match:
                        lat_str, lon_str = dms_match.groups()
                        coords = self.parse_dms_coordinates(lat_str, lon_str)
                        if coords:
                            lat_decimal, lon_decimal = coords
                            params['position'] = f"{lat_decimal},{lon_decimal}"
                            self.log("INFO", f"成功解析度分秒坐标: 纬度={lat_decimal}, 经度={lon_decimal}")
                        else:
                            self.log("ERROR", "度分秒坐标格式无效\n\n"
                                     "请确保格式为：纬度30;6;51.50999999999474 经度120;23;53.3499999999766317")
                            return False
                    else:
                        if coords := self.get_location(address):
                            params['position'] = ','.join(coords)
                        else:
                            self.log("ERROR", f"无法找到地址'{address}'对应的地理坐标\n\n"
                                       "请检查：\n"
                                       "• 地址拼写是否正确\n"
                                       "• 是否包含详细的门牌号或地标\n"
                                       "• 高德地图API密钥是否有效")
                            return False
        elif location_type == 1:
            longitude = self.parent.lineEdit_EXIF_longitude.text()
            latitude = self.parent.lineEdit_EXIF_latitude.text()
            if longitude and latitude:
                try:
                    lon = float(longitude)
                    lat = float(latitude)
                    if -180 <= lon <= 180 and -90 <= lat <= 90:
                        params['position'] = f"{lat},{lon}"
                    else:
                        self.log("ERROR", "经纬度范围无效\n\n"
                                 "• 经度应在-180到180之间\n"
                                 "• 纬度应在-90到90之间\n\n"
                                 "请检查输入的数值是否正确")
                        return False
                except ValueError:
                    coords = self.parse_dms_coordinates(latitude, longitude)
                    if coords:
                        lat_decimal, lon_decimal = coords
                        if -180 <= lon_decimal <= 180 and -90 <= lat_decimal <= 90:
                            params['position'] = f"{lat_decimal},{lon_decimal}"
                            self.log("INFO", f"成功解析度分秒坐标: 纬度={lat_decimal}, 经度={lon_decimal}")
                        else:
                            self.log("ERROR", "经纬度范围无效\n\n"
                                     "• 经度应在-180到180之间\n"
                                     "• 纬度应在-90到90之间\n\n"
                                     "请检查输入的数值是否正确")
                            return False
                    else:
                        self.log("ERROR", "经纬度格式无效\n\n"
                                 "请输入有效的数字格式，例如：\n"
                                 "• 十进制格式: 经度116.397128, 纬度39.916527\n"
                                 "• 度分秒格式: 经度120;23;53.34, 纬度30;6;51.51")
                        return False
            else:
                self.log("ERROR", "请输入经纬度信息\n\n"
                             "请在对应的文本框中输入经度和纬度值")
                return False
        
        self.save_exif_settings()
        
        operation_summary = f"操作类型: EXIF信息写入"
        if params.get('title'):
            operation_summary += f", 标题: {params['title']}"
        if params.get('author'):
            operation_summary += f", 作者: {params['author']}"
        if params.get('position'):
            operation_summary += f", 位置: {params['position']}"
        if params.get('rating') != '0':
            operation_summary += f", 评分: {params['rating']}星"
        
        self.log("INFO", f"摘要: {operation_summary}")
        
        self.error_messages = []
        
        self.worker = WriteExifThread(**params)
        self.connect_worker_signals()
        self.worker.start()
        self.parent.progressBar_EXIF.setValue(0)
        return True

    def stop_exif_writing(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(1000)
            if self.worker.isRunning():
                self.worker.terminate()
            self.log("WARNING", "正在停止EXIF写入操作...")
        self.is_running = False
        self.update_button_state()

    def update_progress(self, value):
        self.parent.progressBar_EXIF.setValue(value)

    def log(self, level, message):
        c = {'ERROR': '#FF0000', 'WARNING': '#FFA500', 'DEBUG': '#008000', 'INFO': '#8677FD'}
        
        if level == 'ERROR':
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.error_messages.append(f"[{timestamp}] [{level}] {message}")
        
        try:
            self.parent.textEdit_WriteEXIF_Log.append(
                f'<span style="color:{c.get(level, "#000000")}">[{datetime.now().strftime("%H:%M:%S")}] [{level}] {message}</span>')
        except Exception as e:
            print(f"日志更新错误: {e}")

    def on_finished(self):
        self.is_running = False
        self.update_button_state()
        
        if self.error_messages:
            QMessageBox.information(
                self.parent, 
                "操作完成", 
                f"写入操作完成，但是有 {len(self.error_messages)} 个错误！\n\n"
                "您可以在原文件夹中查看更新后的文件。"
            )
        else:
            QMessageBox.information(
                self.parent, 
                "操作完成", 
                "EXIF信息写入操作已完成！\n\n"
                "所有选定的图片文件已成功更新EXIF信息。\n\n"
                "您可以在原文件夹中查看更新后的文件。"
            )

    def load_exif_settings(self):
        try:
            if title := config_manager.get_setting("exif_title"):
                self.parent.lineEdit_EXIF_Title.setText(title)
            
            if author := config_manager.get_setting("exif_author"):
                self.parent.lineEdit_EXIF_Author.setText(author)
                
            if subject := config_manager.get_setting("exif_subject"):
                self.parent.lineEdit_EXIF_Theme.setText(subject)
                
            if copyright := config_manager.get_setting("exif_copyright"):
                self.parent.lineEdit_EXIF_Copyright.setText(copyright)
            
            if position := config_manager.get_setting("exif_position"):
                self.parent.lineEdit_EXIF_Position.setText(position)
                
            if latitude := config_manager.get_setting("exif_latitude"):
                self.parent.lineEdit_EXIF_latitude.setText(latitude)
                
            if longitude := config_manager.get_setting("exif_longitude"):
                self.parent.lineEdit_EXIF_longitude.setText(longitude)
            
            if location_index := config_manager.get_setting("exif_location_index"):
                self.parent.comboBox_location.setCurrentIndex(int(location_index))
                self.on_combobox_location_changed(int(location_index))
            
            if camera_brand := config_manager.get_setting("exif_camera_brand"):
                index = self.parent.comboBox_brand.findText(camera_brand)
                if index >= 0:
                    self.parent.comboBox_brand.setCurrentIndex(index)
                    self._on_brand_changed(index)
            
            if camera_model := config_manager.get_setting("exif_camera_model"):
                index = self.parent.comboBox_model.findText(camera_model)
                if index >= 0:
                    self.parent.comboBox_model.setCurrentIndex(index)
            
            if shoot_time_index := config_manager.get_setting("exif_shoot_time_index"):
                self.parent.comboBox_shootTime.setCurrentIndex(int(shoot_time_index))
                self.on_combobox_time_changed(int(shoot_time_index))
            
            if star_rating := config_manager.get_setting("exif_star_rating"):
                self.set_selected_star(int(star_rating))
        except Exception as e:
            self.log("WARNING", f"加载EXIF设置时出错: {str(e)}")

    def save_exif_settings(self):
        try:
            config_manager.update_setting("exif_title", self.parent.lineEdit_EXIF_Title.text())
            config_manager.update_setting("exif_author", self.parent.lineEdit_EXIF_Author.text())
            config_manager.update_setting("exif_subject", self.parent.lineEdit_EXIF_Theme.text())
            config_manager.update_setting("exif_copyright", self.parent.lineEdit_EXIF_Copyright.text())
            
            config_manager.update_setting("exif_position", self.parent.lineEdit_EXIF_Position.text())
            config_manager.update_setting("exif_latitude", self.parent.lineEdit_EXIF_latitude.text())
            config_manager.update_setting("exif_longitude", self.parent.lineEdit_EXIF_longitude.text())
            
            config_manager.update_setting("exif_location_index", self.parent.comboBox_location.currentIndex())
            
            config_manager.update_setting("exif_camera_brand", self.parent.comboBox_brand.currentText())
            config_manager.update_setting("exif_camera_model", self.parent.comboBox_model.currentText())
            
            config_manager.update_setting("exif_shoot_time_index", self.parent.comboBox_shootTime.currentIndex())
            config_manager.update_setting("exif_shoot_time", 
                                        self.parent.dateTimeEdit_shootTime.dateTime().toString("yyyy:MM:dd HH:mm:ss"))
            
            config_manager.update_setting("exif_star_rating", self.selected_star)
        except Exception as e:
            self.log("WARNING", f"保存EXIF设置时出错: {str(e)}")
