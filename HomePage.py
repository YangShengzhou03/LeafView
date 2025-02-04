import glob
import os
import random

from PyQt6 import QtWidgets, QtGui, QtCore

from Thread import ClassificationThread


class HomePage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_page()

    def init_page(self):
        self.connect_signal()
        self.setup_widget_add_folder()
        self.parent.progressBar_readImg.setVisible(False)

    def setup_widget_add_folder(self):
        self.parent.widget_add_folder.setAcceptDrops(True)
        self.parent.widget_add_folder.setMouseTracking(True)
        self.parent.widget_add_folder.dragEnterEvent = self.dragEnterEvent
        self.parent.widget_add_folder.dropEvent = self.dropEvent

    def on_widget_add_folder_click(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.import_folder()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        folder_paths = [os.path.normpath(url.toLocalFile()) for url in event.mimeData().urls() if os.path.isdir(url.toLocalFile())]
        for folder_path in folder_paths:
            if folder_path not in self.parent.imported_folders:
                self.add_folder(folder_path)
        event.acceptProposedAction()

    def connect_signal(self):
        self.parent.pushButton_importfolder.clicked.connect(self.import_folder)
        self.parent.pushButton_add_folder.clicked.connect(self.import_folder)
        self.parent.toolButton_readImg.clicked.connect(self.readImg_clicked)
        self.parent.widget_add_folder.mouseReleaseEvent = self.on_widget_add_folder_click

    def add_folder(self, folder_path):
        normalized_path = os.path.normpath(folder_path)
        if not os.path.isdir(normalized_path) or normalized_path in map(os.path.normpath, self.parent.imported_folders):
            return

        self.parent.imported_folders.append(normalized_path)
        widget = self.parent.item_widget.create_folder_item(normalized_path)
        self.parent.flow_layout_imported_folders.addWidget(widget)
        self.parent.update_empty_state_visibility(
            self.parent.flow_layout_imported_folders,
            self.parent.empty_label_imported_folders
        )
        self.update_recommend_page()
        self.parent.set_folder_names_to_arrange()
        if self.parent.checkBox_includeSubfolders.isChecked():
            for root, dirs, _ in os.walk(folder_path):
                for dir_name in dirs:
                    subfolder_path = os.path.join(root, dir_name)
                    if os.path.isdir(subfolder_path):
                        self.add_folder(subfolder_path)

    def import_folder(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "导入文件夹")
        if folder_path:
            self.add_folder(folder_path)

    def classified_threads(self):
        if not self.parent.imported_folders:
            self.import_folder()
            return
        thread = ClassificationThread(folder_paths=self.parent.imported_folders)
        thread.item_classified.connect(self.parent.on_item_classified)
        thread.progress_updated.connect(self.update_progress_bar)
        thread.finished.connect(self.on_thread_finished)
        self.parent.classified_threads.clear()
        self.parent.classified_threads.append(thread)
        self.parent.progressBar_readImg.setVisible(True)
        thread.start()
        self.parent.toolButton_readImg.setText('停止识图')

    def update_progress_bar(self, value):
        self.parent.progressBar_readImg.setValue(value)

    def readImg_clicked(self):
        if self.parent.toolButton_readImg.text() == '开始识图':
            self.classified_threads()
        else:
            self.on_stop_classification()

    def on_stop_classification(self):
        for thread in self.parent.classified_threads.copy():
            thread.stop()
        self.on_thread_finished()

    def on_thread_finished(self):
        while self.parent.classification_buffer:
            self.parent.dynamic_process_classification_buffer()
        self.parent.classification_buffer.clear()
        self.refresh_counter = 0
        self.parent.progressBar_readImg.setVisible(False)
        self.parent.toolButton_readImg.setText('开始识图')
        self.repaint()

    def get_candidate_images(self):
        image_extensions = ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.heic', '*.tiff', '*.tif', '*.webp')
        candidate_images = []
        for folder in self.parent.imported_folders:
            for ext in image_extensions:
                for file_path in glob.glob(os.path.join(folder, ext)):
                    file_name = os.path.basename(file_path)
                    candidate_images.append((file_path, file_name))
        return candidate_images

    def update_recommend_page(self, clear_existing=False):
        layout = self.parent.flow_layout_recommend
        if clear_existing:
            for i in reversed(range(layout.count())):
                widgetToRemove = layout.itemAt(i).widget()
                if widgetToRemove:
                    layout.removeWidget(widgetToRemove)
                    widgetToRemove.setParent(None)
        candidate_images = self.get_candidate_images()
        if not candidate_images:
            self.parent.update_empty_state_visibility(layout, self.parent.widget_import)
            return
        selected_images = random.sample(candidate_images, min(len(candidate_images), 2))
        non_default_items = []
        for file_path, file_name in selected_images:
            pixmap = QtGui.QPixmap(file_path)
            if not pixmap.isNull():
                item_widget = self.parent.item_widget.create_image_item(
                    file_path, file_name, self.parent.flow_container_recommend, selectable=False)
                if item_widget is not None:
                    label = item_widget.findChild(QtWidgets.QLabel)
                    if label and not label.pixmap().isNull():
                        non_default_items.append(item_widget)
        for item_widget in non_default_items:
            layout.addWidget(item_widget)
        self.parent.update_empty_state_visibility(layout, self.parent.widget_import)
