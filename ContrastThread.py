import numpy as np
from PIL import Image
from PyQt6.QtCore import pyqtSignal, QObject, QThread


class ImageHasher:
    @staticmethod
    def dhash(image_path, hash_size=8):
        try:
            with Image.open(image_path) as img:
                if img.size[0] < 50 or img.size[1] < 50:
                    raise ValueError("Image too small")
                aspect_ratio = img.size[0] / img.size[1]
                if aspect_ratio < 0.2 or aspect_ratio > 5:
                    raise ValueError("Extreme aspect ratio")
                image = img.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
                pixels = np.array(image)
                diff = pixels[:, 1:] > pixels[:, :-1]
                return ImageHasher._binary_array_to_hex(diff.flatten())
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            return None

    @staticmethod
    def hamming_distance(hash1, hash2):
        if hash1 is None or hash2 is None:
            return float('inf')
        return bin(int(hash1, 16) ^ int(hash2, 16)).count('1')

    @staticmethod
    def _binary_array_to_hex(arr):
        bit_string = ''.join(str(b) for b in arr.astype(int))
        return f'{int(bit_string, 2):0>{(len(bit_string) + 3) // 4}x}'


class HashWorkerSignals(QObject):
    hash_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)


class HashWorker(QThread):
    hash_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, image_paths, hash_size=8):
        super().__init__()
        self.image_paths = image_paths
        self.hash_size = hash_size
        self._is_running = True

    def run(self):
        try:
            hashes = {}
            total = len(self.image_paths)
            for index, path in enumerate(self.image_paths):
                if not self._is_running:
                    return
                result = ImageHasher.dhash(path, self.hash_size)
                if result is not None:
                    hashes[path] = result
                self.progress_updated.emit(int((index + 1) / total * 40))

            if self._is_running:
                self.hash_completed.emit(hashes)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False


class ContrastWorkerSignals(QObject):
    groups_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    image_matched = pyqtSignal(str, str)


class ContrastWorker(QThread):
    groups_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    image_matched = pyqtSignal(str, str)

    def __init__(self, image_hashes, threshold):
        super().__init__()
        self.image_hashes = image_hashes
        self.threshold = threshold
        self._is_running = True

    def run(self):
        try:
            groups = {}
            remaining_paths = set(self.image_hashes.keys())
            group_id = 0
            total = len(remaining_paths)
            processed = 0

            while remaining_paths and self._is_running:
                seed_path = remaining_paths.pop()
                groups[group_id] = [seed_path]
                seed_hash = self.image_hashes[seed_path]

                for path in list(remaining_paths):
                    if not self._is_running:
                        return
                    distance = ImageHasher.hamming_distance(seed_hash, self.image_hashes.get(path))
                    if distance <= self.threshold:
                        groups[group_id].append(path)
                        remaining_paths.remove(path)

                    processed += 1
                    progress = min(40 + int((processed / total) * 40), 80)
                    self.progress_updated.emit(progress)

                group_id += 1

            if self._is_running:
                self.groups_completed.emit(groups)
        except Exception as e:
            print(f"Error in contrast worker: {str(e)}")

    def stop(self):
        self._is_running = False
