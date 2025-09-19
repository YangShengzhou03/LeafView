from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from AddFolder import FolderPage
from SmartArrange import SmartArrange
from RemoveDuplication import Contrast
from WriteExif import WriteExif
from TextRecognition import TextRecognition
from Ui_MainWindow import Ui_MainWindow
from UpdateDialog import check_update
from common import get_resource_path, author


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self._init_window()
        check_update()
        self._setup_drag_handlers()

    def _init_window(self):
        self.setWindowTitle("枫叶相册")
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._connect_buttons()
        
        self.scrollArea_page0.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading | 
            QtCore.Qt.AlignmentFlag.AlignLeft | 
            QtCore.Qt.AlignmentFlag.AlignTop
        )
        
        self.empty_widgets = {}
        
        self.empty_widgets['gridLayout_6'] = self._create_empty_widget(self.gridLayout_6)
        
        self.folder_page = FolderPage(self)
        self.classification = SmartArrange(self, self.folder_page)
        self.contrast = Contrast(self, self.folder_page)
        self.write_exif = WriteExif(self, self.folder_page)
        self.text_recognition = TextRecognition(self, self.folder_page)
        
        pass

    def _connect_buttons(self):
        self.toolButton_close.clicked.connect(self.close)
        self.toolButton_maximum.clicked.connect(self._toggle_maximize)
        self.toolButton_minimum.clicked.connect(self.showMinimized)
        
        self.toolButton_serve.clicked.connect(self.feedback)
        self.toolButton_setting.clicked.connect(author)
        self.widget_headVip.mousePressEvent = self._on_head_vip_clicked
        
        pass

    def _on_head_vip_clicked(self, event):
        """处理widget_headVip的点击事件"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            QtWidgets.QMessageBox.information(self, "demo版", "当前为测试演示版本，服务可能随时终止。\n\n如果您需要继续使用，请考虑购买专业版。")
        event.accept()

    def _init_text_recognition(self):
        pass

    def _setup_drag_handlers(self):
        self.frame_logo.mousePressEvent = self._on_mouse_press
        self.frame_logo.mouseMoveEvent = self._on_mouse_move
        self.frame_logo.mouseReleaseEvent = self._on_mouse_release
        
        self.frame_head.mousePressEvent = self._on_mouse_press
        self.frame_head.mouseMoveEvent = self._on_mouse_move
        self.frame_head.mouseReleaseEvent = self._on_mouse_release
        
        self._is_dragging = False
        self._drag_start_pos = QtCore.QPoint()
    
    def _on_mouse_press(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        event.accept()
    
    def _on_mouse_move(self, event):
        if self._is_dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
        event.accept()
    
    def _on_mouse_release(self, event):
        self._is_dragging = False
        event.accept()
    
    def _create_empty_widget(self, layout):
        empty_widget = QtWidgets.QWidget()
        empty_layout = QtWidgets.QVBoxLayout(empty_widget)
        empty_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QtWidgets.QLabel()
        icon = QtGui.QIcon(get_resource_path('resources/img/page_0/空状态.svg'))
        icon_label.setPixmap(icon.pixmap(128, 128))
        empty_layout.addWidget(icon_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        text_label = QtWidgets.QLabel("暂无媒体文件")
        text_label.setStyleSheet("font-size: 16px; color: #666666;")
        text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(text_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        desc_label = QtWidgets.QLabel("请点击上方按钮添加媒体文件夹")
        desc_label.setStyleSheet("font-size: 12px; color: #999999;")
        desc_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(desc_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        empty_widget.hide()
        
        layout.addWidget(empty_widget)
        
        return empty_widget
    
    def _update_empty_state(self, has_media):
        for widget in self.empty_widgets.values():
            if has_media:
                widget.hide()
            else:
                widget.show()
    
    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def log(self, level, message):
        current_time = QtCore.QTime.currentTime().toString("HH:mm:ss")
        log_message = f"[{current_time}] [{level}] {message}"
        
        if level == "ERROR":
            self._show_user_notification("错误", message, "error")
        elif level == "WARNING":
            self._show_user_notification("警告", message, "warning")
        elif level == "INFO":
            if any(keyword in message for keyword in ["完成", "成功", "开始", "停止", "中断"]):
                self._show_user_notification("提示", message, "info")
        
        print(log_message)

    def _show_user_notification(self, title, message, level):
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            if level == "error":
                QMessageBox.critical(self, title, message)
            elif level == "warning":
                QMessageBox.warning(self, title, message)
            elif level == "info":
                QMessageBox.information(self, title, message)
                
        except ImportError:
            print(f"[{level.upper()}] {title}: {message}")

    def feedback(self):
        QDesktopServices.openUrl(QUrl('https://qun.qq.com/universal-share/share?ac=1&authKey=wjyQkU9iG7wc'
                                      '%2BsIEOWFE6cA0ayLLBdYwpMsKYveyufXSOE5FBe7bb9xxvuNYVsEn&busi_data'
                                      '=eyJncm91cENvZGUiOiIxMDIxNDcxODEzIiwidG9rZW4iOiJDaFYxYVpySU9FUVJr'
                                      'RzkwdUZ2QlFVUTQzZzV2VS83TE9mY0NNREluaUZCR05YcnNjWmpKU2V5Q2FYTllFVlJ'
                                      'MIiwidWluIjoiMzU1NTg0NDY3OSJ9&data=M7fVC3YlI68T2S2VpmsR20t9s_xJj6HNpF'
                                      '0GGk2ImSQ9iCE8fZomQgrn_ADRZF0Ee4OSY0x6k2tI5P47NlkWug&svctype=4&tempid'
                                      '=h5_group_info'))
