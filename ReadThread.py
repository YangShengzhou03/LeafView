import os

from PyQt6 import QtCore


class ReadThread(QtCore.QThread):
    image_loaded = QtCore.pyqtSignal(str, str)
    finished_loading = QtCore.pyqtSignal()

    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.running = False

    def run(self):
        self.running = True
        if not os.path.exists(self.directory):
            self.finished_loading.emit()
            return

        image_files = [f for f in os.listdir(self.directory)
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

        for img_file in image_files:
            if not self.running:
                break
            img_path = os.path.join(self.directory, img_file)
            text = os.path.splitext(img_file)[0]
            self.image_loaded.emit(img_path, text)
            self.msleep(50)

        self.finished_loading.emit()

    def stop(self):
        self.running = False
        self.wait()

