import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QDialog, QWidget, QVBoxLayout, QLabel, QPushButton
from filetype import guess


def load_stylesheet(filename):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(script_dir, 'resources', 'stylesheet', filename)

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return f"文件 {filename} 未找到。"


def get_resource_path(relative_path):
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent if '__file__' in globals() else Path.cwd()

    return str((base_path / relative_path).resolve()).replace('\\', '/')


def detect_media_type(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    mime_to_ext = {
        'image/jpeg': ('jpg', 'image'),
        'image/png': ('png', 'image'),
        'image/gif': ('gif', 'image'),
        'image/tiff': ('tiff', 'image'),
        'image/webp': ('webp', 'image'),
        'image/heic': ('heic', 'image'),
        'image/avif': ('avif', 'image'),
        'video/mp4': ('mp4', 'video'),
        'video/x-msvideo': ('avi', 'video'),
        'video/x-matroska': ('mkv', 'video'),
        'video/quicktime': ('mov', 'video'),
        'video/x-ms-wmv': ('wmv', 'video'),
        'video/mpeg': ('mpeg', 'video'),
        'video/webm': ('webm', 'video'),
    }

    file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    try:
        kind = guess(file_path)
    except Exception as e:
        raise IOError(f"文件读取失败: {str(e)}")

    if not kind:
        return {
            'valid': False,
            'type': None,
            'mime': None,
            'extension': None,
            'extension_match': False
        }

    mime = kind.mime
    result = {
        'valid': mime in mime_to_ext,
        'mime': mime,
        'extension': None,
        'type': None,
        'extension_match': False
    }

    if result['valid']:
        ext, media_type = mime_to_ext[mime]
        result.update({
            'extension': ext,
            'type': media_type,
            'extension_match': (ext == file_ext)
        })

    return result


def author():
    dialog = QDialog()
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.FramelessWindowHint)
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dialog.setFixedSize(320, 450)

    container = QWidget(dialog)
    container.setStyleSheet(load_stylesheet("author.dialog.setStyleSheet.css"))
    container.setGeometry(0, 0, dialog.width(), dialog.height())

    layout = QVBoxLayout(container)

    qr_code_label = QLabel(container)
    resource_path = get_resource_path("resources/img/activity/QQ_名片.png")
    pixmap = QPixmap(resource_path)
    qr_code_label.setPixmap(pixmap)
    qr_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    confirm_button = QPushButton("手机QQ扫码·联系开发者", container)
    confirm_button.clicked.connect(dialog.accept)
    layout.addWidget(qr_code_label)
    layout.addWidget(confirm_button)

    close_button = QPushButton(container)
    close_button.setIcon(QIcon(get_resource_path("resources/img/窗口控制/关闭作者.svg")))
    close_button.setFixedSize(28, 28)
    close_button.move(container.width() - close_button.width() - 12, 6)
    close_button.clicked.connect(dialog.reject)
    close_button.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    close_button.setStyleSheet(load_stylesheet("close_button.setStyleSheet.css"))

    dialog.exec()
