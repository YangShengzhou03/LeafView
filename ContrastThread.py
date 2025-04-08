from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image
from PyQt6.QtCore import pyqtSignal, QThread


class ImageHasher:
    @staticmethod
    def dhash(image_path, hash_size=8):
        try:
            with Image.open(image_path) as img:
                w, h = img.size
                if w < 50 or h < 50:
                    return None
                if (w / h) < 0.2 or (w / h) > 5:
                    return None

                image = img.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
                pixels = np.array(image, dtype=np.int16)
                diff = pixels[:, 1:] > pixels[:, :-1]
                return diff.flatten()
        except Exception:
            return None

    @staticmethod
    def hamming_distance(bits1, bits2):
        return np.count_nonzero(bits1 != bits2)


class HashWorker(QThread):
    hash_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, image_paths, hash_size=8, max_workers=4):
        super().__init__()
        self.image_paths = image_paths
        self.hash_size = hash_size
        self.max_workers = max_workers
        self._is_running = True

    def run(self):
        try:
            hashes = {}
            total = len(self.image_paths)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_path = {
                    executor.submit(ImageHasher.dhash, path, self.hash_size): path
                    for path in self.image_paths
                }

                for i, future in enumerate(as_completed(future_to_path)):
                    if not self._is_running:
                        return

                    path = future_to_path[future]
                    result = future.result()
                    if result is not None:
                        hashes[path] = result

                    self.progress_updated.emit(int((i + 1) / total * 40))

            if self._is_running:
                self.hash_completed.emit(hashes)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False


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

                to_remove = []
                for path in remaining_paths:
                    if not self._is_running:
                        return

                    distance = ImageHasher.hamming_distance(seed_hash, self.image_hashes[path])
                    if distance <= self.threshold:
                        groups[group_id].append(path)
                        to_remove.append(path)

                    processed += 1
                    progress = min(40 + int((processed / total) * 40), 80)
                    self.progress_updated.emit(progress)

                for path in to_remove:
                    remaining_paths.remove(path)

                group_id += 1

            if self._is_running:
                self.groups_completed.emit(groups)
        except Exception as e:
            print(f"Error in contrast worker: {str(e)}")

    def stop(self):
        self._is_running = False
