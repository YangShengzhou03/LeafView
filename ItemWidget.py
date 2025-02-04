# ItemWidget
import os
import numpy as np
from PIL import Image
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from moviepy import VideoFileClip


class ItemWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init()

    def init(self):
        pass

    def generate_video_thumbnail(self, file_path):
        try:
            with VideoFileClip(file_path) as video:
                frame = video.get_frame(t=1)
                image = Image.fromarray(np.uint8(frame))
                qimage = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                scaled_pixmap = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                return scaled_pixmap
        except Exception as e:
            placeholder = QtGui.QPixmap(128, 128)
            placeholder.fill(QtGui.QColor('black'))
            return placeholder

    def round_corners(self, pixmap, radius):
        rounded = QtGui.QPixmap(pixmap.size())
        rounded.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(rounded)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(pixmap.rect()), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    def format_filename(self, filename):
        if len(filename) > 15:
            return f"{filename[:6]}...{filename[-6:]}"
        return filename

    def create_folder_item(self, folder_path, parent=None):
        item_widget = QtWidgets.QWidget(parent)
        layout = QtWidgets.QVBoxLayout(item_widget)
        icon_provider = QtWidgets.QFileIconProvider()
        icon = icon_provider.icon(QtCore.QFileInfo(folder_path))
        label_icon = QtWidgets.QLabel(item_widget)
        pixmap = icon.pixmap(QtCore.QSize(128, 128))
        label_icon.setPixmap(pixmap)
        label_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_icon)

        folder_name = os.path.basename(folder_path) or folder_path
        label_folder_name = QtWidgets.QLabel(folder_name, item_widget)
        label_folder_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_folder_name)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum
        )
        item_widget.setSizePolicy(size_policy)
        item_widget.setMinimumSize(QtCore.QSize(128, 128))

        item_widget.setProperty('isSelected', False)
        item_widget.setStyleSheet("""
            QWidget[isSelected="true"] {
                box-shadow: 0px 0px 10px rgba(0, 128, 255, 0.5);
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(240, 240, 255, 0.7), stop:1 rgba(230, 230, 255, 0.7));
            }
            QWidget:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.9), stop:1 rgba(245, 245, 255, 0.9));
            }
        """)

        overlay_label = QtWidgets.QLabel("移除", item_widget)
        overlay_label.setStyleSheet("""
                background-color: qradialgradient(
                    cx:0.5, cy:0.5, radius:1, fx:0.5, fy:0.5,
                    stop:0 rgba(255, 0, 0, 70%),
                    stop:1 rgba(200, 0, 0, 45%)
                );
                color: white;
                font-weight: bold;
                font-family: '幼圆';
                font-size: 12px;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        overlay_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        overlay_label.setVisible(False)
        def on_overlay_click(event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.parent.on_delete_clicked(folder_path)
                event.accept()
            else:
                event.ignore()
        overlay_label.mousePressEvent = on_overlay_click
        layout.addWidget(overlay_label)
        item_widget.installEventFilter(self)
        self.parent.item_selection_state[id(item_widget)] = {
            'overlay': overlay_label,
            'selected': False,
            'folder_path': folder_path
        }
        return item_widget

    def create_video_item(self, file_path, file_name, parent=None):
        item_widget = QtWidgets.QWidget(parent)
        item_widget.setProperty('isSelected', False)

        layout = QtWidgets.QVBoxLayout(item_widget)

        thumbnail = self.generate_video_thumbnail(file_path)
        label = QtWidgets.QLabel(item_widget)

        if not thumbnail.isNull():
            rounded_thumbnail = self.round_corners(thumbnail, 4)
            label.setPixmap(rounded_thumbnail)
        else:
            label.setText("缩略图加载出错")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.mouseDoubleClickEvent = lambda event: self.open_file(file_path)

        overlay_label = QtWidgets.QLabel(item_widget)
        overlay_label.setStyleSheet("""
            QLabel {
                background-color: qradialgradient(
    cx:0.5, cy:0.5, radius:1, fx:0.5, fy:0.5,
    stop:0.66 rgba(134, 119, 253, 75%),
    stop:1 rgba(119, 111, 252, 75%));
                color: white;
                font-weight: bold;
                font-family: '幼圆';
                font-size: 12px;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        overlay_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        overlay_label.setText("选中")
        overlay_label.setVisible(False)
        overlay_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        formatted_filename = self.format_filename(file_name)
        filename_label = QtWidgets.QLabel(formatted_filename, item_widget)
        filename_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        filename_label.setStyleSheet("font-size: 12px; font-weight: normal;")

        layout.addWidget(label)
        layout.addWidget(filename_label)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        item_widget.setStyleSheet("""
            QWidget[isSelected="true"] {
                box-shadow: 0px 0px 10px rgba(0, 128, 255, 0.5);
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(240, 240, 255, 0.7), stop:1 rgba(230, 230, 255, 0.7));
            }
            QWidget:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.9), stop:1 rgba(245, 245, 255, 0.9));
            }
        """)

        item_widget.installEventFilter(self)
        self.parent.item_selection_state[id(item_widget)] = {'overlay': overlay_label, 'selected': False}

        return item_widget

    def create_image_item(self, file_path, file_name, parent=None, selectable=True):
        item_widget = QtWidgets.QWidget(parent)
        item_widget.setProperty('isSelected', False)
        item_widget.setProperty('filePath', file_path)
        layout = QtWidgets.QVBoxLayout(item_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QtWidgets.QLabel(item_widget)
        pixmap = QtGui.QPixmap(file_path)
        if pixmap.isNull():
            placeholder = QtGui.QPixmap(128, 128)
            placeholder.fill(QtGui.QColor('black'))
            pixmap = placeholder

        scaled_pixmap = pixmap.scaled(QtCore.QSize(128, 128), QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                      QtCore.Qt.TransformationMode.SmoothTransformation)
        rounded_pixmap = self.round_corners(scaled_pixmap, 4)
        label.setPixmap(rounded_pixmap)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.mouseDoubleClickEvent = lambda event: self.open_file(file_path)

        overlay_label = QtWidgets.QLabel(item_widget)
        overlay_label.setStyleSheet("""
            QLabel {
                background-color: qradialgradient(cx:0.5, cy:0.5, radius:1, fx:0.5, fy:0.5,
                stop:0.66 rgba(134, 119, 253, 75%), stop:1 rgba(119, 111, 252, 75%));
                color: white;
                font-weight: bold;
                font-family: '幼圆';
                font-size: 12px;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        overlay_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        overlay_label.setText("选中")
        overlay_label.setVisible(False)
        overlay_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        formatted_filename = self.format_filename(file_name)
        filename_label = QtWidgets.QLabel(formatted_filename, item_widget)
        filename_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        filename_label.setStyleSheet("font-size: 12px; font-weight: normal;")
        layout.addWidget(label)
        layout.addWidget(filename_label)

        item_widget.setStyleSheet("""
            QWidget[isSelected="true"] {
                box-shadow: 0px 0px 10px rgba(0, 128, 255, 0.5);
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(240, 240, 255, 0.7), stop:1 rgba(230, 230, 255, 0.7));
            }
            QWidget:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.9), stop:1 rgba(245, 245, 255, 0.9));
            }
        """)
        if selectable:
            item_widget.installEventFilter(self)
            self.parent.item_selection_state[id(item_widget)] = {
                'overlay': overlay_label,
                'selected': False,
                'file_path': file_path
            }

        return item_widget

    def open_file(self, file_path):
        os.startfile(file_path)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonPress and id(obj) in self.parent.item_selection_state:
            state = self.parent.item_selection_state[id(obj)]
            new_selected_state = not state['selected']
            state['selected'] = new_selected_state
            obj.setProperty('isSelected', new_selected_state)
            state['overlay'].setVisible(new_selected_state)

            layout = obj.layout()
            if layout:
                layout.update()
            self.parent.media_page.on_item_selection_changed()

        return super().eventFilter(obj, event)