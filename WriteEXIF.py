from datetime import datetime

import requests
from PyQt6 import QtCore
from PyQt6.QtCore import pyqtSignal, QDateTime
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QWidget

from Thread import WriteExifThread


class WriteEXIF(QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_page()

    def init_page(self):
        self.connect_signals()
        self.on_log_message('欢迎使用 LeafView 属性写入功能！目前支持JPEG(JPG)格式。', 'INFO')
        self.on_log_message('注意：属性写入操作将直接影响数据，请确认信息无误后再进行操作。', 'WARNING')
        self.parent.dateTimeEdit_EXIF.setDateTime(QDateTime.currentDateTime())

    def connect_signals(self):
        self.parent.toolButton_StartEXIF.clicked.connect(self.start_write_exif)
        self.parent.checkBox_AutomaticTime.stateChanged.connect(self.onAutomaticTimeChecked)
        self.updateDateTimeEditStatus()

    @QtCore.pyqtSlot(int)
    def onAutomaticTimeChecked(self, state):
        self.updateDateTimeEditStatus()

    def updateDateTimeEditStatus(self):
        is_checked = self.parent.checkBox_AutomaticTime.isChecked()
        self.parent.dateTimeEdit_EXIF.setEnabled(not is_checked)

    def start_write_exif(self):
        if not self.parent.imported_folders:
            self.on_log_message('您还未导入文件夹,请先导入', 'ERROR')
            return
        title = self.parent.lineEdit_EXIF_Title.text() or None
        author = self.parent.lineEdit_EXIF_Author.text() or None
        subject = self.parent.lineEdit_EXIF_Theme.text() or None
        tag = self.parent.lineEdit_EXIF_Mark.text() or None
        copy = self.parent.lineEdit_EXIF_Copyright.text() or None
        position = self.get_location_by_address(self.parent.lineEdit_EXIF_Position.text()) or None
        automatic_time = self.parent.checkBox_AutomaticTime.isChecked()
        date_to_write = None if automatic_time else self.parent.dateTimeEdit_EXIF.dateTime().toString(
            "yyyy:MM:dd HH:mm:ss")
        time_option = self.parent.comboBox_EXIF_Time.currentIndex()
        try:
            self.thread = WriteExifThread(
                folders=self.parent.imported_folders,
                title=title,
                author=author,
                subject=subject,
                tag=tag,
                copy=copy,
                update_date=date_to_write,
                automatic_time=automatic_time,
                position=position,
                time_option=time_option
            )
            self.thread.progress_updated.connect(self.update_progress_bar)
            self.thread.log_message.connect(self.on_log_message)
            self.thread.finished_conversion.connect(lambda: self.parent.toolButton_StartEXIF.setText("开始写入"))
            self.thread.start()
            self.parent.toolButton_StartEXIF.setText("停止")
            self.parent.toolButton_StartEXIF.clicked.disconnect()
            self.parent.toolButton_StartEXIF.clicked.connect(self.stop_write_exif)
        except Exception as e:
            self.on_log_message(f'按按钮就出错了{e}', 'ERROR')

    def stop_write_exif(self):
        if hasattr(self, 'thread'):
            self.thread.stop()
            self.parent.toolButton_StartEXIF.setText("开始写入")
            self.parent.toolButton_StartEXIF.clicked.disconnect()
            self.parent.toolButton_StartEXIF.clicked.connect(self.start_write_exif)

    def get_location_by_address(self, address):
        url = "https://restapi.amap.com/v3/geocode/geo"
        api_key = 'bc383698582923d55b5137c3439cf4b2'
        params = {
            'address': address,
            'key': api_key,
            'city': '',
            'output': 'JSON'
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            result = response.json()
            if result['status'] == '1' and int(result['count']) > 0:
                location = result['geocodes'][0]['location']
                return location.split(',')
        else:
            return None
        return None

    def update_progress_bar(self, value):
        self.parent.progressBar_EXIF.setValue(value)

    def append_log(self, message):
        cursor = self.parent.textEdit_WriteEXIF_Log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.parent.textEdit_WriteEXIF_Log.setTextCursor(cursor)
        self.parent.textEdit_WriteEXIF_Log.insertHtml(message)
        self.parent.textEdit_WriteEXIF_Log.ensureCursorVisible()

    def on_log_message(self, message, level):
        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
        formatted_message = f'[{timestamp}] [{level.upper()}]: {message}<br>'
        colors = {"INFO": "#691bfd", "WARNING": "#FFA500", "ERROR": "#FF0000", "DEBUG": "#00CC33"}
        color = colors.get(level.upper(), "#00CC33")
        formatted_message = f'<span style="color:{color}"> {formatted_message}</span>'
        self.append_log(formatted_message)
