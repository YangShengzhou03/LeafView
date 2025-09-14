import json
import os
from pathlib import Path

from PyQt6 import QtCore

from common import get_resource_path

SUPPORTED_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.heic', '.tiff', '.tif', '.bmp', '.webp', '.gif', '.svg', '.psd', '.arw', '.cr2', '.cr3',
    '.nef', '.orf', '.sr2', '.raf', '.dng', '.rw2', '.pef', '.nrw', '.kdc', '.mos', '.iiq', '.fff', '.x3f', '.3fr',
    '.mef',
    '.mrw', '.erf', '.raw', '.rwz', '.ari', '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.mpeg',
    '.mpg',
    '.mts', '.mxf', '.webm', '.ogv', '.livp')


class SmartArrangeThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str, str)
    progress_signal = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, folders=None, classification_structure=None, file_name_structure=None,
                 destination_root=None, separator=None, time_derive="最早时间"):
        super().__init__()
        self.parent, self.folders, self.classification_structure = parent, folders or [], classification_structure or []
        self.file_name_structure, self.time_derive = file_name_structure or [], time_derive
        self.destination_root = Path(destination_root) if destination_root else None
        self.separator = separator
        self._stop_flag = False
        self.load_geographic_data()
        self.files_to_rename = []
        self.log_signal.connect(parent.log_signal.emit)
        self.progress_signal.connect(parent.update_progress_bar)

    def load_geographic_data(self):
        try:
            with open(get_resource_path('resources/json/City_Reverse_Geocode.json'), 'r', encoding='utf-8') as f:
                self.city_data = json.load(f)
            with open(get_resource_path('resources/json/Province_Reverse_Geocode.json'), 'r', encoding='utf-8') as f:
                self.province_data = json.load(f)
        except Exception as e:
            self.city_data, self.province_data = {'features': []}, {'features': []}

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.log("INFO", f"正在处理 {len(self.folders)} 个文件夹")
            for folder_info in self.folders:
                if self._stop_flag:
                    self.log("WARNING", "处理被用户中断")
                    break
                if self.destination_root:
                    destination_path = Path(self.destination_root).resolve()
                    folder_path = Path(folder_info['path']).resolve()
                    if len(destination_path.parts) > len(folder_path.parts) and destination_path.parts[
                                                                                :len(
                                                                                    folder_path.parts)] == folder_path.parts:
                        self.log("ERROR", "复制到目标路径不能是待整理的子路径，会导致死循环！")
                        break
                if not self.classification_structure and not self.file_name_structure:
                    self.organize_without_classification(folder_info['path'])
                else:
                    self.process_folder_with_classification(folder_info)
            self.process_renaming()
        except Exception as e:
            self.log("ERROR", f"发生错误: {str(e)}")

    def process_folder_with_classification(self, folder_info):
        folder_path = Path(folder_info['path'])
        total_files = sum([len(files) for _, _, files in os.walk(folder_path)]) if folder_info.get('include_sub',
                                                                                                   0) else len(
            os.listdir(folder_path))
        processed_files = 0

        if folder_info.get('include_sub', 0):
            for root, _, files in os.walk(folder_path):
                for file in files:
                    full_file_path = Path(root) / file
                    if full_file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        self.process_single_file(full_file_path, base_folder=folder_path)
                        processed_files += 1
                        percent_complete = int((processed_files / total_files) * 100)
                        self.progress_signal.emit(percent_complete)
        else:
            for file in os.listdir(folder_path):
                full_file_path = folder_path / file
                if full_file_path.is_file() and full_file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    self.process_single_file(full_file_path)
                    processed_files += 1
                    percent_complete = int((processed_files / total_files) * 100)
                    self.progress_signal.emit(percent_complete)

    def organize_without_classification(self, folder_path):
        # 这里是原ClassificationThread.py中剩余的代码，为了保持简洁我省略了部分实现
        pass

    def process_single_file(self, file_path, base_folder=None):
        # 这里是原ClassificationThread.py中剩余的代码，为了保持简洁我省略了部分实现
        pass

    def process_renaming(self):
        # 这里是原ClassificationThread.py中剩余的代码，为了保持简洁我省略了部分实现
        pass

    def log(self, level, message):
        # 这里是原ClassificationThread.py中剩余的代码，为了保持简洁我省略了部分实现
        pass