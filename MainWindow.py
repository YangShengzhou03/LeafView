"""
LeafView 主窗口控制器模块

负责:
1. 主窗口初始化和UI设置
2. 功能模块的初始化和协调
3. 窗口拖拽行为实现
4. 空状态管理
"""

from PyQt6 import QtWidgets, QtCore, QtGui
from AddFolder import FolderPage
from SmartArrange import SmartArrange
from RemoveDuplication import Contrast
from WriteExif import WriteExif
from TextRecognition import TextRecognition
from Ui_MainWindow import Ui_MainWindow
from UpdateDialog import check_update
from common import get_resource_path, author


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """
    LeafView 主窗口类，继承自自动生成的UI界面
    
    实现无边框窗口设计，提供拖拽功能和模块协调
    """
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        self.setupUi(self)  # 设置UI界面
        self._init_window()  # 初始化窗口设置
        check_update()  # 检查应用更新
        self._setup_drag_handlers()  # 设置拖拽事件处理

    def _init_window(self):
        """初始化窗口设置和UI配置"""
        # 设置窗口基本属性
        self.setWindowTitle("枫叶相册")
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        
        # 设置无边框和透明背景以实现自定义窗口样式
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 连接按钮信号槽
        self._connect_buttons()
        
        # 修改滚动区域对齐方式为顶部对齐，避免内容居中显示
        self.scrollArea_page0.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading | 
            QtCore.Qt.AlignmentFlag.AlignLeft | 
            QtCore.Qt.AlignmentFlag.AlignTop
        )
        
        # 初始化空状态部件字典
        self.empty_widgets = {}
        
        # 创建空状态部件（目前只使用gridLayout_6作为主布局）
        self.empty_widgets['gridLayout_6'] = self._create_empty_widget(self.gridLayout_6)
        
        # 初始化各个功能模块，传递必要的依赖
        self.folder_page = FolderPage(self)  # 媒体导入模块
        self.classification = SmartArrange(self, self.folder_page)  # 智能整理模块
        self.contrast = Contrast(self, self.folder_page)  # 文件去重模块
        self.write_exif = WriteExif(self, self.folder_page)  # 属性写入模块
        self.text_recognition = TextRecognition(self, self.folder_page)  # 识字整理模块
        
        # 初始显示空状态（无媒体文件）
        self._update_empty_state(False)

    def _connect_buttons(self):
        """连接窗口控制按钮和功能按钮的信号槽"""
        # 窗口控制按钮
        self.toolButton_close.clicked.connect(self.close)  # 关闭窗口
        self.toolButton_maximum.clicked.connect(self._toggle_maximize)  # 最大化/还原窗口
        self.toolButton_minimum.clicked.connect(self.showMinimized)  # 最小化窗口
        
        # 功能按钮
        self.toolButton_serve.clicked.connect(author)  # 服务按钮（显示作者信息）
        self.toolButton_setting.clicked.connect(author)  # 设置按钮（显示作者信息）
        
        # 页面切换通过listWidget_base自动实现，不需要手动连接按钮
        pass

    def _init_text_recognition(self):
        """初始化识字整理功能 - 根据要求暂不实现"""
        pass

    def _setup_drag_handlers(self):
        """设置窗口拖拽事件处理器"""
        # 启用窗口拖拽功能，为logo区域添加鼠标事件处理
        self.frame_logo.mousePressEvent = self._on_mouse_press
        self.frame_logo.mouseMoveEvent = self._on_mouse_move
        self.frame_logo.mouseReleaseEvent = self._on_mouse_release
        
        # 为窗口顶部区域添加拖拽功能
        self.frame_head.mousePressEvent = self._on_mouse_press
        self.frame_head.mouseMoveEvent = self._on_mouse_move
        self.frame_head.mouseReleaseEvent = self._on_mouse_release
        
        # 记录拖拽状态
        self._is_dragging = False  # 是否正在拖拽
        self._drag_start_pos = QtCore.QPoint()  # 拖拽起始位置
    
    def _on_mouse_press(self, event):
        """鼠标按下事件处理 - 开始拖拽"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._is_dragging = True  # 设置拖拽状态为True
            # 计算拖拽起始位置（鼠标全局位置减去窗口左上角位置）
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        event.accept()  # 接受事件
    
    def _on_mouse_move(self, event):
        """鼠标移动事件处理 - 执行拖拽"""
        if self._is_dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            # 移动窗口到新的位置（鼠标当前位置减去拖拽起始偏移）
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
        event.accept()  # 接受事件
    
    def _on_mouse_release(self, event):
        """鼠标释放事件处理 - 结束拖拽"""
        self._is_dragging = False  # 重置拖拽状态
        event.accept()  # 接受事件
    
    def _create_empty_widget(self, layout):
        """
        创建空状态显示部件
        
        Args:
            layout: 要添加空状态部件的布局对象
            
        Returns:
            QWidget: 创建的空状态部件
        """
        empty_widget = QtWidgets.QWidget()  # 创建空状态容器部件
        empty_layout = QtWidgets.QVBoxLayout(empty_widget)  # 创建垂直布局
        empty_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)  # 设置居中对齐
        
        # 添加空状态图标
        icon_label = QtWidgets.QLabel()
        icon = QtGui.QIcon(get_resource_path('resources/img/page_0/空状态.svg'))
        icon_label.setPixmap(icon.pixmap(128, 128))  # 设置128x128像素图标
        empty_layout.addWidget(icon_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # 添加主文本标签
        text_label = QtWidgets.QLabel("暂无媒体文件")
        text_label.setStyleSheet("font-size: 16px; color: #666666;")  # 设置文本样式
        text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)  # 设置文本居中对齐
        empty_layout.addWidget(text_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # 添加说明文本标签
        desc_label = QtWidgets.QLabel("请点击上方按钮添加媒体文件夹")
        desc_label.setStyleSheet("font-size: 12px; color: #999999;")  # 设置说明文本样式
        desc_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)  # 设置文本居中对齐
        empty_layout.addWidget(desc_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # 初始隐藏空状态部件
        empty_widget.hide()
        
        # 将空状态部件添加到指定布局
        layout.addWidget(empty_widget)
        
        return empty_widget  # 返回创建的空状态部件
    
    def _update_empty_state(self, has_media):
        """
        更新空状态显示
        
        Args:
            has_media: 布尔值，表示是否有媒体文件
        """
        for widget in self.empty_widgets.values():
            if has_media:
                widget.hide()  # 有媒体文件时隐藏空状态
            else:
                widget.show()  # 无媒体文件时显示空状态
    
    def _toggle_maximize(self):
        """切换窗口最大化/还原状态"""
        if self.isMaximized():
            self.showNormal()  # 如果已最大化，则还原为正常大小
        else:
            self.showMaximized()  # 如果未最大化，则最大化窗口

    def log(self, level, message):
        """
        记录日志信息
        
        Args:
            level: 日志级别（如INFO、WARNING、ERROR）
            message: 日志消息内容
        """
        # 生成带时间戳的日志消息
        current_time = QtCore.QTime.currentTime().toString("HH:mm:ss")
        log_message = f"[{current_time}] [{level}] {message}"
        
        # 如果有专门的日志区域，可以在这里添加显示逻辑
        print(log_message)  # 临时输出到控制台
