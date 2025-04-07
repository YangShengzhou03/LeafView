import concurrent.futures

import numpy as np
from PIL import Image
from PyQt6.QtCore import pyqtSignal, QRunnable, QObject


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


class HashWorker(QRunnable):
    def __init__(self, image_paths, hash_size=8):
        super().__init__()
        self.image_paths = image_paths
        self.hash_size = hash_size
        self.signals = HashWorkerSignals()
        self._is_running = True

    def run(self):
        try:
            hashes = {}
            total = len(self.image_paths)
            batch_size = 100
            completed = 0

            for i in range(0, total, batch_size):
                if not self._is_running:
                    return
                batch = self.image_paths[i:i + batch_size]
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {executor.submit(ImageHasher.dhash, path, self.hash_size): path for path in batch}
                    for future in concurrent.futures.as_completed(futures):
                        if not self._is_running:
                            return
                        path = futures[future]
                        result = future.result()
                        if result is not None:
                            hashes[path] = result
                        completed += 1
                        self.signals.progress_updated.emit(completed)

            if self._is_running:
                self.signals.hash_completed.emit(hashes)
        except Exception as e:
            self.signals.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False


class ContrastWorkerSignals(QObject):
    groups_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    image_matched = pyqtSignal(str, str)


class ContrastWorker(QRunnable):
    def __init__(self, image_hashes, threshold):
        super().__init__()
        self.image_hashes = image_hashes
        self.threshold = threshold
        self.signals = ContrastWorkerSignals()
        self._is_running = True

    def run(self):
        try:
            groups = {}
            remaining_paths = set(self.image_hashes.keys())
            group_id = 0
            batch_size = 100
            total = len(remaining_paths)
            processed = 0

            while remaining_paths and self._is_running:
                seed_path = remaining_paths.pop()
                groups[group_id] = [seed_path]
                seed_hash = self.image_hashes[seed_path]
                to_check = list(remaining_paths)

                for i in range(0, len(to_check), batch_size):
                    if not self._is_running:
                        return
                    batch = to_check[i:i + batch_size]
                    matches = []
                    for path in batch:
                        distance = ImageHasher.hamming_distance(seed_hash, self.image_hashes.get(path))
                        if distance <= self.threshold:
                            matches.append(path)

                    if matches:
                        groups[group_id].extend(matches)
                        remaining_paths.difference_update(matches)

                    processed += len(batch)
                    self.signals.progress_updated.emit(int(processed / total * 100))

                group_id += 1

            if self._is_running:
                self.signals.groups_completed.emit(groups)
        except Exception as e:
            print(f"Error in contrast worker: {str(e)}")

    def stop(self):
        self._is_running = False
