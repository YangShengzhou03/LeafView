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
        
        self.scrollArea_navigation.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading | 
            QtCore.Qt.AlignmentFlag.AlignLeft | 
            QtCore.Qt.AlignmentFlag.AlignTop
        )
    


    def _connect_buttons(self):
        self.btn_close.clicked.connect(self.close)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        self.btn_minimize.clicked.connect(self.showMinimized)
        
        self.btn_service.clicked.connect(self.feedback)
        self.btn_settings.clicked.connect(author)

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
    
    def _create_quick_toolbar(self):
        """创建快速操作工具栏 - 新增功能"""
        # 在左侧导航区域添加快速工具栏
        quick_toolbar = QtWidgets.QFrame(parent=self.frame_left)
        quick_toolbar.setObjectName("quick_toolbar")
        quick_toolbar.setStyleSheet("""
            QFrame#quick_toolbar {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 8px;
                margin: 8px 4px;
                padding: 4px;
            }
            
            QPushButton {
                background-color: #6c5ce7;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                margin: 2px;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #5a4bc7;
            }
            
            QPushButton:pressed {
                background-color: #4a3ba7;
            }
        """)
        
        toolbar_layout = QtWidgets.QVBoxLayout(quick_toolbar)
        toolbar_layout.setContentsMargins(6, 6, 6, 6)
        toolbar_layout.setSpacing(4)
        
        # 添加快速操作按钮
        self.btn_quick_add = QtWidgets.QPushButton("📁 添加文件夹")
        self.btn_quick_add.clicked.connect(lambda: self._show_page(0))
        toolbar_layout.addWidget(self.btn_quick_add)
        
        self.btn_quick_batch = QtWidgets.QPushButton("📂 批量添加")
        self.btn_quick_batch.clicked.connect(lambda: self._show_page(0))
        toolbar_layout.addWidget(self.btn_quick_batch)
        
        toolbar_layout.addSpacing(8)
        
        self.btn_quick_smart = QtWidgets.QPushButton("🤖 智能整理")
        self.btn_quick_smart.clicked.connect(lambda: self._show_page(1))
        toolbar_layout.addWidget(self.btn_quick_smart)
        
        self.btn_quick_remove_dup = QtWidgets.QPushButton("🗑️ 去重")
        self.btn_quick_remove_dup.clicked.connect(lambda: self._show_page(2))
        toolbar_layout.addWidget(self.btn_quick_remove_dup)
        
        toolbar_layout.addSpacing(8)
        
        self.btn_quick_exif = QtWidgets.QPushButton("📝 编辑信息")
        self.btn_quick_exif.clicked.connect(lambda: self._show_page(3))
        toolbar_layout.addWidget(self.btn_quick_exif)
        
        # 添加到左侧布局（在logo下方，导航菜单上方）
        self.layout_left_panel.insertWidget(1, quick_toolbar)
    
    def _setup_keyboard_shortcuts(self):
        """设置全局快捷键 - 新增功能"""
        # 创建快捷键
        self.shortcut_add_folder = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+A"), self)
        self.shortcut_add_folder.activated.connect(lambda: self._show_page(0))
        
        self.shortcut_batch_add = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+A"), self)
        self.shortcut_batch_add.activated.connect(lambda: self._show_page(0))
        
        self.shortcut_smart_arrange = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.shortcut_smart_arrange.activated.connect(lambda: self._show_page(1))
        
        self.shortcut_remove_dup = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+D"), self)
        self.shortcut_remove_dup.activated.connect(lambda: self._show_page(2))
        
        self.shortcut_exif = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+E"), self)
        self.shortcut_exif.activated.connect(lambda: self._show_page(3))
        
        self.shortcut_refresh = QtGui.QShortcut(QtGui.QKeySequence("F5"), self)
        self.shortcut_refresh.activated.connect(self._refresh_current_page)
        
        self.shortcut_help = QtGui.QShortcut(QtGui.QKeySequence("F1"), self)
        self.shortcut_help.activated.connect(self._show_help)
        
        # 新增更多快捷键
        self.shortcut_next_page = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Tab"), self)
        self.shortcut_next_page.activated.connect(self._next_page)
        
        self.shortcut_prev_page = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+Tab"), self)
        self.shortcut_prev_page.activated.connect(self._prev_page)
        
        self.shortcut_quit = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self)
        self.shortcut_quit.activated.connect(self.close)
        
        self.shortcut_minimize = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+M"), self)
        self.shortcut_minimize.activated.connect(self.showMinimized)

    def _next_page(self):
        """切换到下一页"""
        current_index = self.stackedWidget.currentIndex()
        next_index = (current_index + 1) % self.stackedWidget.count()
        self._show_page(next_index)
        
    def _prev_page(self):
        """切换到上一页"""
        current_index = self.stackedWidget.currentIndex()
        prev_index = (current_index - 1) % self.stackedWidget.count()
        self._show_page(prev_index)
    
    def _show_page(self, page_index):
        """显示指定页面 - 新增功能"""
        if hasattr(self, 'stackedWidget'):
            self.stackedWidget.setCurrentIndex(page_index)
            # 更新导航菜单选中状态
            self.listWidget_mainMenu.setCurrentRow(page_index)
    
    def _refresh_current_page(self):
        """刷新当前页面 - 新增功能"""
        current_index = 0
        if hasattr(self, 'stackedWidget'):
            current_index = self.stackedWidget.currentIndex()
        
        # 根据不同页面执行相应刷新操作
        if current_index == 0 and hasattr(self, 'folder_page'):
            # 刷新文件夹页面
            if hasattr(self.folder_page, '_refresh_all_folders'):
                self.folder_page._refresh_all_folders()
        elif current_index == 1 and hasattr(self, 'smart_arrange_page'):
            # 刷新智能整理页面
            pass
        elif current_index == 2 and hasattr(self, 'remove_dup_page'):
            # 刷新去重页面
            pass
    
    def _show_help(self):
        """显示帮助信息 - 新增功能"""
        help_text = """
        <h3>枫叶相册 - 快捷键帮助</h3>
        <p><b>页面切换：</b></p>
        <ul>
        <li>Ctrl+A - 添加文件夹页面</li>
        <li>Ctrl+S - 智能整理页面</li>
        <li>Ctrl+D - 去重页面</li>
        <li>Ctrl+E - 编辑信息页面</li>
        </ul>
        <p><b>通用操作：</b></p>
        <ul>
        <li>F5 - 刷新当前页面</li>
        <li>F1 - 显示帮助</li>
        <li>拖拽文件夹 - 快速添加</li>
        </ul>
        <p><b>窗口控制：</b></p>
        <ul>
        <li>双击标题栏 - 最大化/还原</li>
        <li>拖拽标题栏 - 移动窗口</li>
        </ul>
        """
        
        QtWidgets.QMessageBox.information(self, "快捷键帮助", help_text)

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
