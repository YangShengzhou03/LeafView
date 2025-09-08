"""主窗口模块

这个模块定义了LeafView应用程序的主窗口。
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QScrollArea, QFrame,
    QSplitter, QStackedWidget, QTabWidget, QGroupBox, QCheckBox,
    QSlider, QSpinBox, QDoubleSpinBox, QComboBox, QFileDialog,
    QMessageBox, QSizePolicy, QSpacerItem, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, pyqtSlot, QPoint, QRect
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QFont

from .ui_main_window import Ui_MainWindow
from ..controllers.media_controller import MediaController
from ..controllers.classification_controller import ClassificationController
from ..controllers.duplicate_finder_controller import DuplicateFinderController
from ..models.media_item import MediaItem
from ..models.duplicate_result import DuplicateResult, DuplicateGroup, DuplicateAction
from ..utils.logger import LoggerMixin
from ..utils.config import Config


class MainWindow(QMainWindow, LoggerMixin):
    """主窗口类
    
    LeafView应用程序的主窗口，包含所有UI元素和功能。
    """
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 设置UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # 设置窗口属性
        self.setWindowTitle("LeafView - 媒体管理工具")
        self.setWindowIcon(QIcon("resources/icons/app_icon.png"))
        
        # 初始化控制器
        self.media_controller = MediaController(self)
        self.classification_controller = ClassificationController(self)
        self.duplicate_finder_controller = DuplicateFinderController(self)
        
        # 初始化变量
        self._media_items = []
        self._duplicate_result = None
        self._current_view = "media"  # 当前视图：media, classification, duplicates
        
        # 初始化UI组件
        self._init_ui()
        
        # 连接信号和槽
        self._connect_signals()
        
        # 加载配置
        self._load_config()
        
        # 记录日志
        self.logger.info("主窗口初始化完成")
    
    def _init_ui(self):
        """初始化UI组件"""
        # 设置窗口无边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # 设置窗口大小
        self.resize(1200, 800)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建标题栏
        self._create_title_bar()
        
        # 创建内容区域
        self._create_content_area()
        
        # 创建状态栏
        self._create_status_bar()
        
        # 设置中央部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def _create_title_bar(self):
        """创建标题栏"""
        # 创建标题栏容器
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("""
            QFrame#titleBar {
                background-color: #2c3e50;
                border-bottom: 1px solid #1a252f;
            }
        """)
        
        # 创建标题栏布局
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 0, 10, 0)
        
        # 创建应用图标
        app_icon = QLabel()
        app_icon.setPixmap(QIcon("resources/icons/app_icon.png").pixmap(24, 24))
        
        # 创建应用标题
        app_title = QLabel("LeafView")
        app_title.setObjectName("appTitle")
        app_title.setStyleSheet("""
            QLabel#appTitle {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # 创建窗口控制按钮
        self.minimize_button = QPushButton()
        self.minimize_button.setObjectName("minimizeButton")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setIcon(QIcon("resources/icons/minimize.png"))
        self.minimize_button.setStyleSheet("""
            QPushButton#minimizeButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton#minimizeButton:hover {
                background-color: #34495e;
            }
        """)
        
        self.maximize_button = QPushButton()
        self.maximize_button.setObjectName("maximizeButton")
        self.maximize_button.setFixedSize(30, 30)
        self.maximize_button.setIcon(QIcon("resources/icons/maximize.png"))
        self.maximize_button.setStyleSheet("""
            QPushButton#maximizeButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton#maximizeButton:hover {
                background-color: #34495e;
            }
        """)
        
        self.close_button = QPushButton()
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setIcon(QIcon("resources/icons/close.png"))
        self.close_button.setStyleSheet("""
            QPushButton#closeButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton#closeButton:hover {
                background-color: #e74c3c;
            }
        """)
        
        # 添加到布局
        title_layout.addWidget(app_icon)
        title_layout.addWidget(app_title)
        title_layout.addStretch()
        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(self.maximize_button)
        title_layout.addWidget(self.close_button)
        
        title_bar.setLayout(title_layout)
        
        # 添加到主布局
        self.layout().addWidget(title_bar)
    
    def _create_content_area(self):
        """创建内容区域"""
        # 创建内容容器
        content_container = QFrame()
        content_container.setObjectName("contentContainer")
        content_container.setStyleSheet("""
            QFrame#contentContainer {
                background-color: #ecf0f1;
            }
        """)
        
        # 创建内容布局
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建导航栏
        self._create_navigation_bar()
        
        # 创建主内容区
        self._create_main_content()
        
        # 添加到布局
        content_layout.addWidget(self.navigation_frame)
        content_layout.addWidget(self.main_content_frame, 1)
        
        content_container.setLayout(content_layout)
        
        # 添加到主布局
        self.layout().addWidget(content_container, 1)
    
    def _create_navigation_bar(self):
        """创建导航栏"""
        # 创建导航栏容器
        self.navigation_frame = QFrame()
        self.navigation_frame.setObjectName("navigationFrame")
        self.navigation_frame.setFixedWidth(200)
        self.navigation_frame.setStyleSheet("""
            QFrame#navigationFrame {
                background-color: #34495e;
                border-right: 1px solid #2c3e50;
            }
        """)
        
        # 创建导航栏布局
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(10)
        
        # 创建导航按钮
        self.media_button = QPushButton("媒体管理")
        self.media_button.setObjectName("mediaButton")
        self.media_button.setFixedHeight(40)
        self.media_button.setIcon(QIcon("resources/icons/media.png"))
        self.media_button.setStyleSheet("""
            QPushButton#mediaButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
                font-weight: bold;
            }
            QPushButton#mediaButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.classification_button = QPushButton("分类管理")
        self.classification_button.setObjectName("classificationButton")
        self.classification_button.setFixedHeight(40)
        self.classification_button.setIcon(QIcon("resources/icons/classification.png"))
        self.classification_button.setStyleSheet("""
            QPushButton#classificationButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton#classificationButton:hover {
                background-color: #2c3e50;
            }
        """)
        
        self.duplicates_button = QPushButton("去重管理")
        self.duplicates_button.setObjectName("duplicatesButton")
        self.duplicates_button.setFixedHeight(40)
        self.duplicates_button.setIcon(QIcon("resources/icons/duplicates.png"))
        self.duplicates_button.setStyleSheet("""
            QPushButton#duplicatesButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton#duplicates_button:hover {
                background-color: #2c3e50;
            }
        """)
        
        # 添加到布局
        nav_layout.addWidget(self.media_button)
        nav_layout.addWidget(self.classification_button)
        nav_layout.addWidget(self.duplicates_button)
        nav_layout.addStretch()
        
        self.navigation_frame.setLayout(nav_layout)
    
    def _create_main_content(self):
        """创建主内容区"""
        # 创建主内容容器
        self.main_content_frame = QFrame()
        self.main_content_frame.setObjectName("mainContentFrame")
        self.main_content_frame.setStyleSheet("""
            QFrame#mainContentFrame {
                background-color: white;
                border-radius: 5px;
            }
        """)
        
        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget()
        
        # 创建各个页面
        self._create_media_page()
        self._create_classification_page()
        self._create_duplicates_page()
        
        # 添加到堆叠窗口
        self.stacked_widget.addWidget(self.media_page)
        self.stacked_widget.addWidget(self.classification_page)
        self.stacked_widget.addWidget(self.duplicates_page)
        
        # 设置默认页面
        self.stacked_widget.setCurrentWidget(self.media_page)
        
        # 创建主内容布局
        main_content_layout = QVBoxLayout()
        main_content_layout.setContentsMargins(10, 10, 10, 10)
        main_content_layout.addWidget(self.stacked_widget)
        
        self.main_content_frame.setLayout(main_content_layout)
    
    def _create_media_page(self):
        """创建媒体管理页面"""
        # 创建媒体页面容器
        self.media_page = QWidget()
        
        # 创建媒体页面布局
        media_layout = QVBoxLayout()
        media_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加工具栏按钮
        add_folder_button = QPushButton("添加文件夹")
        add_folder_button.setIcon(QIcon("resources/icons/add_folder.png"))
        add_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        remove_folder_button = QPushButton("移除文件夹")
        remove_folder_button.setIcon(QIcon("resources/icons/remove_folder.png"))
        remove_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        refresh_button = QPushButton("刷新")
        refresh_button.setIcon(QIcon("resources/icons/refresh.png"))
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        
        # 添加到工具栏布局
        toolbar_layout.addWidget(add_folder_button)
        toolbar_layout.addWidget(remove_folder_button)
        toolbar_layout.addWidget(refresh_button)
        toolbar_layout.addStretch()
        
        toolbar.setLayout(toolbar_layout)
        
        # 创建文件夹列表区域
        folder_list_frame = QFrame()
        folder_list_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        folder_list_layout = QVBoxLayout()
        folder_list_layout.setContentsMargins(10, 10, 10, 10)
        
        folder_list_label = QLabel("已添加的文件夹:")
        folder_list_label.setStyleSheet("font-weight: bold;")
        
        # 创建文件夹列表（这里使用简单的标签代替，实际应用中应该使用列表控件）
        self.folder_list_label = QLabel("暂无文件夹")
        self.folder_list_label.setWordWrap(True)
        
        # 添加到文件夹列表布局
        folder_list_layout.addWidget(folder_list_label)
        folder_list_layout.addWidget(self.folder_list_label)
        
        folder_list_frame.setLayout(folder_list_layout)
        
        # 创建媒体预览区域
        media_preview_frame = QFrame()
        media_preview_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        media_preview_layout = QVBoxLayout()
        media_preview_layout.setContentsMargins(10, 10, 10, 10)
        
        media_preview_label = QLabel("媒体预览:")
        media_preview_label.setStyleSheet("font-weight: bold;")
        
        # 创建媒体预览区域（这里使用简单的标签代替，实际应用中应该使用网格布局显示缩略图）
        self.media_preview_label = QLabel("暂无媒体文件")
        self.media_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_preview_label.setStyleSheet("""
            QLabel {
                background-color: #e9ecef;
                border: 1px dashed #adb5bd;
                border-radius: 5px;
                padding: 20px;
                min-height: 200px;
            }
        """)
        
        # 添加到媒体预览布局
        media_preview_layout.addWidget(media_preview_label)
        media_preview_layout.addWidget(self.media_preview_label)
        
        media_preview_frame.setLayout(media_preview_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(folder_list_frame)
        splitter.addWidget(media_preview_frame)
        splitter.setSizes([200, 400])
        
        # 添加到媒体页面布局
        media_layout.addWidget(toolbar)
        media_layout.addWidget(splitter, 1)
        
        self.media_page.setLayout(media_layout)
    
    def _create_classification_page(self):
        """创建分类管理页面"""
        # 创建分类页面容器
        self.classification_page = QWidget()
        
        # 创建分类页面布局
        classification_layout = QVBoxLayout()
        classification_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加工具栏按钮
        classify_button = QPushButton("开始分类")
        classify_button.setIcon(QIcon("resources/icons/classify.png"))
        classify_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        stop_button = QPushButton("停止分类")
        stop_button.setIcon(QIcon("resources/icons/stop.png"))
        stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        # 添加到工具栏布局
        toolbar_layout.addWidget(classify_button)
        toolbar_layout.addWidget(stop_button)
        toolbar_layout.addStretch()
        
        toolbar.setLayout(toolbar_layout)
        
        # 创建分类设置区域
        settings_frame = QFrame()
        settings_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        settings_layout = QVBoxLayout()
        settings_layout.setContentsMargins(10, 10, 10, 10)
        
        settings_label = QLabel("分类设置:")
        settings_label.setStyleSheet("font-weight: bold;")
        
        # 创建分类设置表单（这里使用简单的标签代替，实际应用中应该使用表单控件）
        settings_form_label = QLabel("分类设置选项将显示在这里")
        settings_form_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_form_label.setStyleSheet("""
            QLabel {
                background-color: #e9ecef;
                border: 1px dashed #adb5bd;
                border-radius: 5px;
                padding: 20px;
                min-height: 100px;
            }
        """)
        
        # 添加到分类设置布局
        settings_layout.addWidget(settings_label)
        settings_layout.addWidget(settings_form_label)
        
        settings_frame.setLayout(settings_layout)
        
        # 创建分类结果区域
        results_frame = QFrame()
        results_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(10, 10, 10, 10)
        
        results_label = QLabel("分类结果:")
        results_label.setStyleSheet("font-weight: bold;")
        
        # 创建分类结果区域（这里使用简单的标签代替，实际应用中应该使用树形控件显示分类结果）
        self.results_label = QLabel("暂无分类结果")
        self.results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_label.setStyleSheet("""
            QLabel {
                background-color: #e9ecef;
                border: 1px dashed #adb5bd;
                border-radius: 5px;
                padding: 20px;
                min-height: 300px;
            }
        """)
        
        # 添加到分类结果布局
        results_layout.addWidget(results_label)
        results_layout.addWidget(self.results_label)
        
        results_frame.setLayout(results_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(settings_frame)
        splitter.addWidget(results_frame)
        splitter.setSizes([150, 450])
        
        # 添加到分类页面布局
        classification_layout.addWidget(toolbar)
        classification_layout.addWidget(splitter, 1)
        
        self.classification_page.setLayout(classification_layout)
    
    def _create_duplicates_page(self):
        """创建去重管理页面"""
        # 创建去重页面容器
        self.duplicates_page = QWidget()
        
        # 创建去重页面布局
        duplicates_layout = QVBoxLayout()
        duplicates_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加工具栏按钮
        self.start_duplicate_button = QPushButton("开始去重")
        self.start_duplicate_button.setIcon(QIcon("resources/icons/start_duplicate.png"))
        self.start_duplicate_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.stop_duplicate_button = QPushButton("停止去重")
        self.stop_duplicate_button.setIcon(QIcon("resources/icons/stop_duplicate.png"))
        self.stop_duplicate_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        self.apply_duplicate_button = QPushButton("应用结果")
        self.apply_duplicate_button.setIcon(QIcon("resources/icons/apply_duplicate.png"))
        self.apply_duplicate_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        
        self.apply_duplicate_button.setEnabled(False)  # 初始状态下禁用
        
        # 添加到工具栏布局
        toolbar_layout.addWidget(self.start_duplicate_button)
        toolbar_layout.addWidget(self.stop_duplicate_button)
        toolbar_layout.addWidget(self.apply_duplicate_button)
        toolbar_layout.addStretch()
        
        toolbar.setLayout(toolbar_layout)
        
        # 创建去重设置区域
        settings_frame = QFrame()
        settings_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        settings_layout = QHBoxLayout()
        settings_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建相似度阈值设置
        threshold_group = QGroupBox("相似度阈值")
        threshold_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        threshold_layout = QHBoxLayout()
        
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(50)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(90)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        
        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setMinimum(0.5)
        self.threshold_spinbox.setMaximum(1.0)
        self.threshold_spinbox.setValue(0.9)
        self.threshold_spinbox.setSingleStep(0.05)
        self.threshold_spinbox.setDecimals(2)
        
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_spinbox)
        
        threshold_group.setLayout(threshold_layout)
        
        # 创建去重选项设置
        options_group = QGroupBox("去重选项")
        options_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        options_layout = QVBoxLayout()
        
        self.auto_select_checkbox = QCheckBox("自动选择最佳保留项")
        self.auto_select_checkbox.setChecked(True)
        
        self.prefer_resolution_checkbox = QCheckBox("优先保留高分辨率图像")
        self.prefer_resolution_checkbox.setChecked(True)
        
        self.prefer_date_checkbox = QCheckBox("优先保留较早日期的图像")
        self.prefer_date_checkbox.setChecked(True)
        
        options_layout.addWidget(self.auto_select_checkbox)
        options_layout.addWidget(self.prefer_resolution_checkbox)
        options_layout.addWidget(self.prefer_date_checkbox)
        
        options_group.setLayout(options_layout)
        
        # 添加到设置布局
        settings_layout.addWidget(threshold_group)
        settings_layout.addWidget(options_group)
        
        settings_frame.setLayout(settings_layout)
        
        # 创建进度条区域
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        progress_layout = QVBoxLayout()
        progress_layout.setContentsMargins(10, 10, 10, 10)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        progress_frame.setLayout(progress_layout)
        
        # 创建去重结果区域
        results_frame = QFrame()
        results_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(10, 10, 10, 10)
        
        results_label = QLabel("去重结果:")
        results_label.setStyleSheet("font-weight: bold;")
        
        # 创建去重结果区域（这里使用简单的标签代替，实际应用中应该使用表格或自定义控件显示去重结果）
        self.duplicate_results_label = QLabel("暂无去重结果")
        self.duplicate_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duplicate_results_label.setStyleSheet("""
            QLabel {
                background-color: #e9ecef;
                border: 1px dashed #adb5bd;
                border-radius: 5px;
                padding: 20px;
                min-height: 300px;
            }
        """)
        
        # 添加到去重结果布局
        results_layout.addWidget(results_label)
        results_layout.addWidget(self.duplicate_results_label)
        
        results_frame.setLayout(results_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(settings_frame)
        splitter.addWidget(progress_frame)
        splitter.addWidget(results_frame)
        splitter.setSizes([100, 50, 400])
        
        # 添加到去重页面布局
        duplicates_layout.addWidget(toolbar)
        duplicates_layout.addWidget(splitter, 1)
        
        self.duplicates_page.setLayout(duplicates_layout)
    
    def _create_status_bar(self):
        """创建状态栏"""
        # 创建状态栏容器
        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(30)
        status_bar.setStyleSheet("""
            QFrame#statusBar {
                background-color: #34495e;
                border-top: 1px solid #2c3e50;
            }
        """)
        
        # 创建状态栏布局
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(10, 0, 10, 0)
        
        # 创建状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("""
            QLabel#statusLabel {
                color: white;
            }
        """)
        
        # 添加到布局
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        status_bar.setLayout(status_layout)
        
        # 添加到主布局
        self.layout().addWidget(status_bar)
    
    def _connect_signals(self):
        """连接信号和槽"""
        # 窗口控制按钮
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button.clicked.connect(self._toggle_maximize)
        self.close_button.clicked.connect(self.close)
        
        # 导航按钮
        self.media_button.clicked.connect(lambda: self._switch_view("media"))
        self.classification_button.clicked.connect(lambda: self._switch_view("classification"))
        self.duplicates_button.clicked.connect(lambda: self._switch_view("duplicates"))
        
        # 去重功能按钮
        self.start_duplicate_button.clicked.connect(self._on_start_duplicate_clicked)
        self.stop_duplicate_button.clicked.connect(self._on_stop_duplicate_clicked)
        self.apply_duplicate_button.clicked.connect(self._on_apply_duplicate_clicked)
        
        # 相似度阈值控件
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        self.threshold_spinbox.valueChanged.connect(self._on_threshold_changed)
        
        # 去重选项控件
        self.auto_select_checkbox.stateChanged.connect(self._on_auto_select_changed)
        self.prefer_resolution_checkbox.stateChanged.connect(self._on_prefer_resolution_changed)
        self.prefer_date_checkbox.stateChanged.connect(self._on_prefer_date_changed)
        
        # 去重控制器信号
        self.duplicate_finder_controller.progress_updated.connect(self._on_duplicate_progress_updated)
        self.duplicate_finder_controller.duplicate_found.connect(self._on_duplicate_found)
        self.duplicate_finder_controller.duplicates_found.connect(self._on_duplicates_found)
        self.duplicate_finder_controller.finished.connect(self._on_duplicate_finished)
        self.duplicate_finder_controller.error_occurred.connect(self._on_duplicate_error)
        self.duplicate_finder_controller.result_applied.connect(self._on_duplicate_result_applied)
    
    def _load_config(self):
        """加载配置"""
        # 加载窗口大小和位置
        config = Config()
        window_size = config.get("window_size", [1200, 800])
        self.resize(window_size[0], window_size[1])
        
        window_pos = config.get("window_position", [100, 100])
        self.move(window_pos[0], window_pos[1])
        
        # 加载去重设置
        similarity_threshold = config.get("similarity_threshold", 0.9)
        self.duplicate_finder_controller.set_similarity_threshold(similarity_threshold)
        self.threshold_slider.setValue(int(similarity_threshold * 100))
        self.threshold_spinbox.setValue(similarity_threshold)
        
        # 加载去重选项
        auto_select = config.get("auto_select_best", True)
        self.duplicate_finder_controller.set_config("auto_select_best", auto_select)
        self.auto_select_checkbox.setChecked(auto_select)
        
        prefer_resolution = config.get("prefer_larger_resolution", True)
        self.duplicate_finder_controller.set_config("prefer_larger_resolution", prefer_resolution)
        self.prefer_resolution_checkbox.setChecked(prefer_resolution)
        
        prefer_date = config.get("prefer_earlier_date", True)
        self.duplicate_finder_controller.set_config("prefer_earlier_date", prefer_date)
        self.prefer_date_checkbox.setChecked(prefer_date)
    
    def _save_config(self):
        """保存配置"""
        config = Config()
        
        # 保存窗口大小和位置
        config.set("window_size", [self.width(), self.height()])
        config.set("window_position", [self.x(), self.y()])
        
        # 保存去重设置
        config.set("similarity_threshold", self.duplicate_finder_controller.get_similarity_threshold())
        config.set("auto_select_best", self.duplicate_finder_controller.get_config("auto_select_best"))
        config.set("prefer_larger_resolution", self.duplicate_finder_controller.get_config("prefer_larger_resolution"))
        config.set("prefer_earlier_date", self.duplicate_finder_controller.get_config("prefer_earlier_date"))
        
        config.save()
    
    def _switch_view(self, view_name: str):
        """切换视图
        
        Args:
            view_name: 视图名称，可以是"media", "classification", "duplicates"
        """
        # 更新当前视图
        self._current_view = view_name
        
        # 更新导航按钮样式
        self.media_button.setStyleSheet("""
            QPushButton#mediaButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
                font-weight: bold;
            }
            QPushButton#mediaButton:hover {
                background-color: #2980b9;
            }
        """) if view_name == "media" else self.media_button.setStyleSheet("""
            QPushButton#mediaButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton#mediaButton:hover {
                background-color: #2c3e50;
            }
        """)
        
        self.classification_button.setStyleSheet("""
            QPushButton#classificationButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
                font-weight: bold;
            }
            QPushButton#classificationButton:hover {
                background-color: #2980b9;
            }
        """) if view_name == "classification" else self.classification_button.setStyleSheet("""
            QPushButton#classificationButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton#classificationButton:hover {
                background-color: #2c3e50;
            }
        """)
        
        self.duplicates_button.setStyleSheet("""
            QPushButton#duplicatesButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
                font-weight: bold;
            }
            QPushButton#duplicatesButton:hover {
                background-color: #2980b9;
            }
        """) if view_name == "duplicates" else self.duplicates_button.setStyleSheet("""
            QPushButton#duplicatesButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton#duplicatesButton:hover {
                background-color: #2c3e50;
            }
        """)
        
        # 切换页面
        if view_name == "media":
            self.stacked_widget.setCurrentWidget(self.media_page)
        elif view_name == "classification":
            self.stacked_widget.setCurrentWidget(self.classification_page)
        elif view_name == "duplicates":
            self.stacked_widget.setCurrentWidget(self.duplicates_page)
        
        # 更新状态栏
        self.status_label.setText(f"当前视图: {self._get_view_display_name(view_name)}")
    
    def _get_view_display_name(self, view_name: str) -> str:
        """获取视图显示名称
        
        Args:
            view_name: 视图名称
            
        Returns:
            视图显示名称
        """
        if view_name == "media":
            return "媒体管理"
        elif view_name == "classification":
            return "分类管理"
        elif view_name == "duplicates":
            return "去重管理"
        else:
            return "未知视图"
    
    def _toggle_maximize(self):
        """切换最大化状态"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setIcon(QIcon("resources/icons/maximize.png"))
        else:
            self.showMaximized()
            self.maximize_button.setIcon(QIcon("resources/icons/restore.png"))
    
    def _on_start_duplicate_clicked(self):
        """处理开始去重按钮点击事件"""
        if not self._media_items:
            QMessageBox.warning(self, "警告", "没有媒体文件需要去重，请先添加媒体文件夹")
            return
        
        # 设置媒体项到去重控制器
        self.duplicate_finder_controller.set_media_items(self._media_items)
        
        # 开始去重
        self.duplicate_finder_controller.start_finding_duplicates()
        
        # 更新UI状态
        self.start_duplicate_button.setEnabled(False)
        self.stop_duplicate_button.setEnabled(True)
        self.apply_duplicate_button.setEnabled(False)
        self.threshold_slider.setEnabled(False)
        self.threshold_spinbox.setEnabled(False)
        self.auto_select_checkbox.setEnabled(False)
        self.prefer_resolution_checkbox.setEnabled(False)
        self.prefer_date_checkbox.setEnabled(False)
        
        # 更新进度条
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在查找重复文件...")
    
    def _on_stop_duplicate_clicked(self):
        """处理停止去重按钮点击事件"""
        # 停止去重
        self.duplicate_finder_controller.stop_finding_duplicates()
        
        # 更新UI状态
        self.start_duplicate_button.setEnabled(True)
        self.stop_duplicate_button.setEnabled(False)
        self.apply_duplicate_button.setEnabled(self._duplicate_result is not None)
        self.threshold_slider.setEnabled(True)
        self.threshold_spinbox.setEnabled(True)
        self.auto_select_checkbox.setEnabled(True)
        self.prefer_resolution_checkbox.setEnabled(True)
        self.prefer_date_checkbox.setEnabled(True)
        
        # 更新进度条
        self.progress_label.setText("已停止查找重复文件")
    
    def _on_apply_duplicate_clicked(self):
        """处理应用去重结果按钮点击事件"""
        if not self._duplicate_result:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认操作",
            f"确定要应用去重结果吗？这将处理 {self._duplicate_result.total_files} 个文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 应用去重结果
            self.duplicate_finder_controller.apply_result()
    
    def _on_threshold_changed(self, value):
        """处理相似度阈值改变事件
        
        Args:
            value: 新的阈值值
        """
        # 同步滑块和微调框的值
        if isinstance(value, int):
            # 来自滑块的值
            threshold = value / 100.0
            self.threshold_spinbox.setValue(threshold)
        else:
            # 来自微调框的值
            threshold = value
            self.threshold_slider.setValue(int(value * 100))
        
        # 更新去重控制器的阈值
        self.duplicate_finder_controller.set_similarity_threshold(threshold)
    
    def _on_auto_select_changed(self, state):
        """处理自动选择选项改变事件
        
        Args:
            state: 复选框状态
        """
        checked = state == Qt.CheckState.Checked.value
        self.duplicate_finder_controller.set_config("auto_select_best", checked)
    
    def _on_prefer_resolution_changed(self, state):
        """处理优先分辨率选项改变事件
        
        Args:
            state: 复选框状态
        """
        checked = state == Qt.CheckState.Checked.value
        self.duplicate_finder_controller.set_config("prefer_larger_resolution", checked)
    
    def _on_prefer_date_changed(self, state):
        """处理优先日期选项改变事件
        
        Args:
            state: 复选框状态
        """
        checked = state == Qt.CheckState.Checked.value
        self.duplicate_finder_controller.set_config("prefer_earlier_date", checked)
    
    @pyqtSlot(int, int, str)
    def _on_duplicate_progress_updated(self, current: int, total: int, message: str):
        """处理去重进度更新事件
        
        Args:
            current: 当前进度
            total: 总进度
            message: 进度消息
        """
        # 更新进度条
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
    
    @pyqtSlot(object, object, float)
    def _on_duplicate_found(self, item1: MediaItem, item2: MediaItem, similarity: float):
        """处理发现重复项事件
        
        Args:
            item1: 第一个媒体项
            item2: 第二个媒体项
            similarity: 相似度
        """
        # 这里可以添加实时显示发现的重复项的逻辑
        pass
    
    @pyqtSlot(object)
    def _on_duplicates_found(self, result: DuplicateResult):
        """处理批量重复项事件
        
        Args:
            result: 去重结果对象
        """
        # 保存结果
        self._duplicate_result = result
        
        # 更新UI
        self.duplicate_results_label.setText(
            f"发现 {result.total_groups} 组重复文件，共 {result.total_files} 个文件"
        )
        
        # 启用应用按钮
        self.apply_duplicate_button.setEnabled(True)
    
    @pyqtSlot(bool)
    def _on_duplicate_finished(self, success: bool):
        """处理去重完成事件
        
        Args:
            success: 是否成功
        """
        # 更新UI状态
        self.start_duplicate_button.setEnabled(True)
        self.stop_duplicate_button.setEnabled(False)
        self.threshold_slider.setEnabled(True)
        self.threshold_spinbox.setEnabled(True)
        self.auto_select_checkbox.setEnabled(True)
        self.prefer_resolution_checkbox.setEnabled(True)
        self.prefer_date_checkbox.setEnabled(True)
        
        # 更新进度条
        if success:
            self.progress_bar.setValue(100)
            self.progress_label.setText("去重完成")
        else:
            self.progress_label.setText("去重失败")
    
    @pyqtSlot(str)
    def _on_duplicate_error(self, error_message: str):
        """处理去重错误事件
        
        Args:
            error_message: 错误消息
        """
        # 显示错误消息
        QMessageBox.critical(self, "错误", error_message)
        
        # 更新UI状态
        self.start_duplicate_button.setEnabled(True)
        self.stop_duplicate_button.setEnabled(False)
        self.threshold_slider.setEnabled(True)
        self.threshold_spinbox.setEnabled(True)
        self.auto_select_checkbox.setEnabled(True)
        self.prefer_resolution_checkbox.setEnabled(True)
        self.prefer_date_checkbox.setEnabled(True)
        
        # 更新进度条
        self.progress_label.setText("去重失败")
    
    @pyqtSlot(object)
    def _on_duplicate_result_applied(self, result: DuplicateResult):
        """处理去重结果应用事件
        
        Args:
            result: 去重结果对象
        """
        # 显示成功消息
        QMessageBox.information(
            self, "成功",
            f"已成功应用去重结果，处理了 {result.total_files} 个文件"
        )
        
        # 清除结果
        self._duplicate_result = None
        self.duplicate_finder_controller.clear_result()
        
        # 更新UI
        self.duplicate_results_label.setText("暂无去重结果")
        self.apply_duplicate_button.setEnabled(False)
        
        # 刷新媒体列表
        self._refresh_media_list()
    
    def _refresh_media_list(self):
        """刷新媒体列表"""
        # 这里应该实现刷新媒体列表的逻辑
        # 简单起见，这里只是更新状态栏
        self.status_label.setText("已刷新媒体列表")
    
    def mousePressEvent(self, event):
        """处理鼠标按下事件
        
        Args:
            event: 鼠标事件
        """
        # 记录鼠标位置，用于窗口拖动
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件
        
        Args:
            event: 鼠标事件
        """
        # 窗口拖动
        if event.buttons() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'drag_position'):
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()
    
    def closeEvent(self, event):
        """处理窗口关闭事件
        
        Args:
            event: 关闭事件
        """
        # 保存配置
        self._save_config()
        
        # 停止去重线程
        if self.duplicate_finder_controller.is_running():
            self.duplicate_finder_controller.stop_finding_duplicates()
        
        # 接受关闭事件
        event.accept()