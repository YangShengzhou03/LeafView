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
        'image/heif': ('heif', 'image'),
        'image/x-canon-cr2': ('cr2', 'image'),
        'image/x-canon-cr3': ('cr3', 'image'),
        'image/x-nikon-nef': ('nef', 'image'),
        'image/x-sony-arw': ('arw', 'image'),
        'image/x-olympus-orf': ('orf', 'image'),
        'image/x-panasonic-raw': ('raw', 'image'),
        'image/x-fuji-raf': ('raf', 'image'),
        'image/x-adobe-dng': ('dng', 'image'),
        'image/x-samsung-srw': ('srw', 'image'),
        'image/x-pentax-pef': ('pef', 'image'),
        'image/x-kodak-dcr': ('dcr', 'image'),
        'image/x-kodak-k25': ('k25', 'image'),
        'image/x-kodak-kdc': ('kdc', 'image'),
        'image/x-minolta-mrw': ('mrw', 'image'),
        'image/x-sigma-x3f': ('x3f', 'image'),
        'video/mp4': ('mp4', 'video'),
        'video/x-msvideo': ('avi', 'video'),
        'video/x-matroska': ('mkv', 'video'),
        'video/quicktime': ('mov', 'video'),
        'video/x-ms-wmv': ('wmv', 'video'),
        'video/mpeg': ('mpeg', 'video'),
        'video/webm': ('webm', 'video'),
        'video/x-flv': ('flv', 'video'),
        'video/3gpp': ('3gp', 'video'),
        'video/3gpp2': ('3g2', 'video'),
        'video/x-m4v': ('m4v', 'video'),
        'video/x-ms-asf': ('asf', 'video'),
        'video/x-mng': ('mng', 'video'),
        'video/x-sgi-movie': ('movie', 'video'),
        'application/vnd.apple.mpegurl': ('m3u8', 'video'),
        'application/x-mpegurl': ('m3u8', 'video'),
        'video/mp2t': ('ts', 'video'),
        'video/MP2T': ('ts', 'video'),
        'audio/mpeg': ('mp3', 'audio'),
        'audio/wav': ('wav', 'audio'),
        'audio/x-wav': ('wav', 'audio'),
        'audio/flac': ('flac', 'audio'),
        'audio/aac': ('aac', 'audio'),
        'audio/x-m4a': ('m4a', 'audio'),
        'audio/ogg': ('ogg', 'audio'),
        'audio/webm': ('webm', 'audio'),
        'audio/amr': ('amr', 'audio'),
        'audio/x-ms-wma': ('wma', 'audio'),
        'audio/x-aiff': ('aiff', 'audio'),
        'audio/x-midi': ('midi', 'audio'),
        'application/octet-stream': ('bin', 'other'),
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
