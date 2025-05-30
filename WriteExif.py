from datetime import datetime
import requests
from PyQt6.QtCore import pyqtSlot, QDateTime
from PyQt6.QtWidgets import QWidget
from WriteExifThread import WriteExifThread
from common import get_resource_path


class WriteExif(QWidget):
    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.selected_star = 0
        self.worker = None
        self.star_buttons = []
        self.is_running = False
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        for i in range(1, 6):
            btn = getattr(self.parent, f'pushButton_star_{i}')
            btn.setStyleSheet(
                "QPushButton { \n"
                f"image: url({get_resource_path('resources/img/page_4/星级_暗.svg')});\n"
                "border: none; padding: 0; }" "\n"
                "QPushButton:hover { background-color: transparent; }"
            )
            btn.enterEvent = lambda e, idx=i: self.highlight_stars(idx)
            btn.leaveEvent = lambda e: self.highlight_stars(self.selected_star)
            btn.clicked.connect(lambda _, idx=i: self.set_selected_star(idx))
            self.star_buttons.append(btn)
        self.update_button_state()
        self.parent.dateTimeEdit_shootTime.setDateTime(QDateTime.currentDateTime())
        self.parent.dateTimeEdit_shootTime.hide()
        self.log("DEBUG", "欢迎使用图像属性写入功能，不写入项目留空即可。")

    def setup_connections(self):
        self.parent.toolButton_StartEXIF.clicked.connect(self.toggle_exif_writing)
        self.parent.pushButton_Position.clicked.connect(self.update_position_by_ip)
        self.parent.comboBox_shootTime.currentIndexChanged.connect(self.on_combobox_time_changed)

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
            btn.setStyleSheet(f"QPushButton {{ image: url({get_resource_path(f'resources/img/page_4/{icon})')};}}")

    @pyqtSlot(int)
    def set_selected_star(self, star):
        self.selected_star = star
        self.highlight_stars(star)

    def get_location(self, address):
        try:
            url = "https://restapi.amap.com/v3/geocode/geo"
            params = {'address': address, 'key': 'bc383698582923d55b5137c3439cf4b2', 'output': 'JSON'}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == '1' and int(data.get('count', 0)) > 0:
                return data['geocodes'][0]['location'].split(',')
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
                self.log("ERROR", "无法解析位置信息")
                return None
        except Exception as e:
            self.log("ERROR", f"获取位置失败: {str(e)}")
            return None

    def update_position_by_ip(self):
        location_info = self.get_location_by_ip()
        if location_info is not None:
            lat, lon = location_info
            self.log("INFO", f"成功获取位置信息: 纬度={lat}, 经度={lon}")
        else:
            self.log("ERROR", "获取位置信息失败，请检查网络连接。")

    def start_exif_writing(self):
        folders = self.folder_page.get_all_folders() if self.folder_page else {}
        if not folders:
            self.log("WARNING", "请先导入一个有效的文件夹。")
            return False
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
            else self.parent.comboBox_shootTime.currentIndex()
        }
        address = self.parent.lineEdit_EXIF_Position.text()
        if address:
            if coords := self.get_location(address):
                params['position'] = ','.join(coords)
            else:
                self.log("ERROR", f"无法找到地址'{address}'对应的地理坐标")
                return False
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
            self.log("WARNING", "正在停止EXIF写入。")

    def update_progress(self, value):
        self.parent.progressBar_EXIF.setValue(value)

    def log(self, level, message):
        c = {'ERROR': '#FF0000', 'WARNING': '#FFA500', 'DEBUG': '#008000', 'INFO': '#8677FD'}
        self.parent.textEdit_WriteEXIF_Log.append(
            f'<span style="color:{c.get(level, "#000000")}">[{datetime.now().strftime("%H:%M:%S")}] [{level}] {message}</span>')

    def on_finished(self):
        self.log("DEBUG", "EXIF信息写入任务结束!")
        self.is_running = False
        self.update_button_state()
