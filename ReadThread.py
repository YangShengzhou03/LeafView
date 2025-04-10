import os
from pathlib import Path
from PyQt6 import QtCore


class ReadThread(QtCore.QThread):
    image_loaded = QtCore.pyqtSignal(str, str)
    finished = QtCore.pyqtSignal()

    def __init__(self, folders=None):
        super().__init__()
        self.folders = folders or []
        self._is_running = True

    def run(self):
        for folder_info in self.folders:
            if not self._is_running:
                break
            folder_path = Path(folder_info['path'])
            include_sub = folder_info.get('include_sub', 0)

            try:
                if not folder_path.exists():
                    continue

                if include_sub:
                    for root, _, files in os.walk(folder_path):
                        if not self._is_running:
                            break
                        for file_name in files:
                            full_path = os.path.join(root, file_name)
                            self.process_file(full_path)
                            self.msleep(50)
                else:
                    for file_name in os.listdir(folder_path):
                        if not self._is_running:
                            break
                        full_path = os.path.join(folder_path, file_name)
                        if os.path.isfile(full_path):
                            self.process_file(full_path)
                            self.msleep(50)

            except Exception as e:
                pass

        self.finished.emit()

    def process_file(self, full_path):
        file_name = os.path.basename(full_path).lower()
        if file_name.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            layout = "gridLayout_5"
        elif file_name.endswith(('.mp4', '.avi', '.mov')):
            layout = "gridLayout_4"
        else:
            return

        text = os.path.splitext(file_name)[0]
        self.image_loaded.emit(full_path, layout)

    def stop(self):
        self._is_running = False
        self.wait()