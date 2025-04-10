import os
from PyQt6 import QtCore


class ReadThread(QtCore.QThread):
    image_loaded = QtCore.pyqtSignal(str, str, str)
    finished_loading = QtCore.pyqtSignal()

    def __init__(self, directory):
        super().__init__()
        print()
        self.directory = directory
        self.running = False

    def run(self):
        self.running = True
        if not os.path.exists(self.directory):
            print("Directory doesn't exist")
            self.finished_loading.emit()
            return

        for file_name in os.listdir(self.directory):
            if not self.running:
                break
            full_path = os.path.join(self.directory, file_name)

            # 根据文件扩展名选择布局
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                print(full_path)
                layout = "gridLayout_4"  # 图像文件发送到 gridLayout_4
            elif file_name.lower().endswith(('.mp4', '.avi', '.mov')):
                print(full_path)
                layout = "gridLayout_5"  # 视频文件发送到 gridLayout_5
            else:
                print("File type not supported")
                continue  # 跳过不支持的文件类型

            text = os.path.splitext(file_name)[0]
            self.image_loaded.emit(full_path, text, layout)  # 发送路径、文本和布局名称
            self.msleep(50)

        self.finished_loading.emit()

    def stop(self):
        self.running = False
        self.wait()
