import os
import re
from pathlib import Path
import numpy as np
from PIL import Image
from PyQt6 import QtCore
from skimage import feature

class ReadThread(QtCore.QThread):
    image_loaded = QtCore.pyqtSignal(str, str)
    finished = QtCore.pyqtSignal()
    progress_updated = QtCore.pyqtSignal(int)

    def __init__(self, folders=None):
        super().__init__()
        self.folders = folders or []
        self._is_running = True
        self.screenshot_patterns = [
            r'screenshot', r'screen_shot', r'scrnshot',
            r'截图', r'屏幕截图', r'capture', r'screen\d+',
            r'^img_\d{8}_\d{6}',
            r'^screencap', r'^sc_\d+'
        ]
        self.common_screen_sizes = [
            (750, 1334), (828, 1792), (1080, 1920), (1080, 2160),
            (1080, 2340), (1080, 2400), (1242, 2208), (1242, 2688),
            (1440, 2560), (1440, 2960), (1440, 3200)
        ]

    def run(self):
        all_files = self._collect_files()
        total_files = len(all_files)
        if total_files == 0:
            self.finished.emit()
            return

        for idx, file_path in enumerate(all_files):
            if not self._is_running:
                break
            self.process_file(file_path)
            progress = int((idx + 1) / total_files * 100)
            self.progress_updated.emit(progress)

        self.finished.emit()

    def _collect_files(self):
        all_files = []
        for folder_info in self.folders:
            if not self._is_running:
                break
            folder_path = Path(folder_info['path'])
            include_sub = folder_info.get('include_sub', 0)

            if not folder_path.exists():
                continue

            try:
                if include_sub:
                    for root, _, files in os.walk(folder_path):
                        if not self._is_running:
                            break
                        all_files.extend(self._filter_files(root, files))
                else:
                    all_files.extend(self._filter_files(folder_path))
            except Exception as e:
                pass
        return all_files

    def _filter_files(self, path, files=None):
        valid_files = []
        targets = os.listdir(path) if files is None else files
        for f in targets:
            full_path = os.path.join(path, f) if files else os.path.join(path, f)
            if os.path.isfile(full_path) and f.lower().endswith(
                    ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp',
                     '.mp4', '.avi', '.mov', '.mkv', '.wmv')
            ):
                valid_files.append(full_path)
        return valid_files

    def process_file(self, full_path):
        file_name = os.path.basename(full_path)
        lower_name = file_name.lower()

        if lower_name.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
            self.image_loaded.emit(full_path, "gridLayout_5")
            is_screenshot = self.is_screenshot(full_path)
            if is_screenshot:
                self.image_loaded.emit(full_path, "gridLayout_3")
        elif lower_name.endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv')):
            self.image_loaded.emit(full_path, "gridLayout_4")

    def is_screenshot(self, image_path):
        filename = os.path.basename(image_path).lower()
        for pattern in self.screenshot_patterns:
            if re.search(pattern, filename):
                return True
        img = Image.open(image_path)
        width, height = img.size
        size_match = any(abs(w - width) <= 10 and abs(h - height) <= 10 for w, h in self.common_screen_sizes)
        def check_lbp(gray_np):
            lbp = feature.local_binary_pattern(gray_np, P=8, R=1, method="uniform")
            hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, 10), range=(0, 9))
            hist = hist.astype("float")
            hist /= hist.sum()
            threshold = 0.45 if size_match else 0.55
            return np.any(hist > threshold)
        gray_img = img.convert('L')
        gray_np = np.array(gray_img, dtype=np.uint8)
        return check_lbp(gray_np)

    def stop(self):
        self._is_running = False
        self.wait()