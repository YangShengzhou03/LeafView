from PyQt6 import QtWidgets, QtCore, QtGui
from AddFolder import FolderPage
from SmartArrange import Classification
from RemoveDuplication import Contrast
from WriteExif import WriteExif
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
        # 修改scrollArea_page0的对齐方式，从垂直居中改为垂直顶部对齐
        self.scrollArea_page0.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading | QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.empty_widgets = {}
        # Note: Only gridLayout_6 exists in the UI, so we'll use it for all media types
        self.empty_widgets['gridLayout_6'] = self._create_empty_widget(self.gridLayout_6)  # 主布局（用于所有媒体类型）
        
        # 初始化各个功能模块
        self.folder_page = FolderPage(self)
        self.classification = Classification(self, self.folder_page)
        self.contrast = Contrast(self, self.folder_page)
        self.write_exif = WriteExif(self, self.folder_page)
        
        # 初始化显示空状态
        self._update_empty_state(False)

    def _connect_buttons(self):
        # 窗口控制按钮
        self.toolButton_close.clicked.connect(self.close)
        self.toolButton_maximum.clicked.connect(self._toggle_maximize)
        self.toolButton_minimum.clicked.connect(self.showMinimized)
        
        # 功能按钮
        self.toolButton_serve.clicked.connect(author)
        self.toolButton_setting.clicked.connect(author)
        
        # 页面切换通过listWidget_base自动实现，不需要手动连接按钮
        pass

    def _init_text_recognition(self):
        """初始化识字整理功能 - 根据要求暂不实现"""
        pass

    def _setup_drag_handlers(self):
        # 启用窗口拖拽
        self.frame_logo.mousePressEvent = self._on_mouse_press
        self.frame_logo.mouseMoveEvent = self._on_mouse_move
        self.frame_logo.mouseReleaseEvent = self._on_mouse_release
        
        # 为窗口顶部区域添加拖拽功能
        self.frame_head.mousePressEvent = self._on_mouse_press
        self.frame_head.mouseMoveEvent = self._on_mouse_move
        self.frame_head.mouseReleaseEvent = self._on_mouse_release
        
        # 记录拖拽状态
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
        """创建空状态部件"""
        empty_widget = QtWidgets.QWidget()
        empty_layout = QtWidgets.QVBoxLayout(empty_widget)
        empty_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # 添加图标
        icon_label = QtWidgets.QLabel()
        icon = QtGui.QIcon(get_resource_path('resources/img/page_0/空状态.svg'))
        icon_label.setPixmap(icon.pixmap(128, 128))
        empty_layout.addWidget(icon_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # 添加文本
        text_label = QtWidgets.QLabel("暂无媒体文件")
        text_label.setStyleSheet("font-size: 16px; color: #666666;")
        text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(text_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # 添加说明文本
        desc_label = QtWidgets.QLabel("请点击上方按钮添加媒体文件夹")
        desc_label.setStyleSheet("font-size: 12px; color: #999999;")
        desc_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(desc_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # 隐藏空状态部件
        empty_widget.hide()
        
        # 添加到布局
        layout.addWidget(empty_widget)
        
        return empty_widget
    
    def _update_empty_state(self, has_media):
        """更新空状态显示"""
        for widget in self.empty_widgets.values():
            if has_media:
                widget.hide()
            else:
                widget.show()
    
    def _toggle_maximize(self):
        """切换窗口最大化状态"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def log(self, level, message):
        """记录日志信息"""
        # 确保日志显示在状态栏或其他适当位置
        current_time = QtCore.QTime.currentTime().toString("HH:mm:ss")
        log_message = f"[{current_time}] [{level}] {message}"
        
        # 如果有状态栏，可以在这里更新
        # self.statusBar().showMessage(log_message, 5000)  # 5秒后自动清除
        
        # 如果有专门的日志区域，可以在这里添加
        print(log_message)  # 临时输出到控制台
