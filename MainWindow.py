from PyQt6 import QtWidgets, QtCore, QtGui

from FolderPage import FolderPage
from Ui_MainWindow import Ui_MainWindow
from UpdateDialog import check_update
from common import get_resource_path, author
from src.leafview.controllers.classification_controller import ClassificationController
from src.leafview.controllers.media_controller import MediaController
from src.leafview.controllers.duplicate_finder_controller import DuplicateFinderController
from src.leafview.views.duplicates_page import DuplicatesPageWidget


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
        self.folder_page = FolderPage(self)
        # 使用新的控制器类替代原来的类
        self.media_controller = MediaController(self)
        self.classification_controller = ClassificationController(self)
        self.duplicate_finder_controller = DuplicateFinderController(self)
        
        # 注意：不再创建独立的去重页面，而是使用UI文件中已定义的页面
        # 去重页面已经在Ui_MainWindow.ui中定义，并通过setupUi方法创建
        
        # 连接去重相关信号
        self._connect_duplicate_finder_buttons()
        
        # 设置导航列表项点击事件
        self.listWidget_base.itemClicked.connect(self._on_navigation_item_clicked)

    def _connect_buttons(self):
        self.toolButton_close.clicked.connect(self.close)
        self.toolButton_maximum.clicked.connect(self._toggle_maximize)
        self.toolButton_minimum.clicked.connect(self.showMinimized)
        self.toolButton_serve.clicked.connect(author)
        self.toolButton_setting.clicked.connect(author)
    
    def _on_navigation_item_clicked(self, item):
        """处理导航项点击事件
        
        Args:
            item: 被点击的列表项
        """
        row = self.listWidget_base.row(item)
        # 根据点击的导航项切换stackedWidget的页面
        # 0: 媒体导入, 1: 智能整理, 2: 文件去重, 3: 属性写入
        self.stackedWidget.setCurrentIndex(row)
        
        # 如果点击的是文件去重项，初始化去重功能
        if row == 2:  # 文件去重
            self._init_duplicate_finder()
    
    def _init_duplicate_finder(self):
        """初始化去重功能"""
        # 检查是否已添加去重页面
        if self.stackedWidget.count() <= 3:  # 只有默认的4个页面
            # 创建去重页面
            self.duplicates_page = DuplicatesPageWidget(self)
            # 添加到stackedWidget
            self.stackedWidget.addWidget(self.duplicates_page)
        else:
            # 获取已存在的去重页面
            self.duplicates_page = self.stackedWidget.widget(4)  # 第5个页面
        
        # 连接去重控制器信号
        self._connect_duplicate_finder_signals()
    
    def _connect_duplicate_finder_signals(self):
        """连接去重控制器信号"""
        # 连接去重控制器信号
        # 注意：DuplicateFinderController类中没有定义duplicate_finder_started信号
        # 使用finished信号替代duplicate_finder_completed
        self.duplicate_finder_controller.finished.connect(self._on_duplicate_finder_completed)
        self.duplicate_finder_controller.progress_updated.connect(self._on_duplicate_finder_progress_updated)
        self.duplicate_finder_controller.duplicate_found.connect(self._on_duplicate_found)
        self.duplicate_finder_controller.error_occurred.connect(self._on_duplicate_finder_error_occurred)
    
    def _connect_duplicate_finder_buttons(self):
        """连接图像去重相关按钮信号"""
        # 连接开始查找按钮
        self.toolButton_startContrast.clicked.connect(self._on_start_duplicate_finder)
        
        # 连接其他去重相关按钮
        self.toolButton_move.clicked.connect(self._on_move_duplicates)
        self.toolButton_autoSelect.clicked.connect(self._on_auto_select_duplicates)
        self.toolButton_delete.clicked.connect(self._on_delete_duplicates)
    
    def _on_start_duplicate_finder(self):
        """开始查找重复图像"""
        # 确保去重页面已初始化
        if not hasattr(self, 'duplicates_page'):
            self._init_duplicate_finder()
        
        # 显示去重页面
        self.stackedWidget.setCurrentWidget(self.duplicates_page)
        
        # 获取当前媒体项列表
        media_items = self.media_controller.get_media_items()
        
        if not media_items:
            if hasattr(self, 'duplicates_page'):
                self.duplicates_page.updateProgress(0, 100, "没有可检查的文件")
            else:
                self.label_levelContrast.setText("没有可检查的文件")
            return
        
        # 获取去重页面中的设置
        similarity_threshold = self.duplicates_page.getSimilarityThreshold()
        duplicate_method = self.duplicates_page.getDuplicateMethod()
        auto_select = self.duplicates_page.isAutoSelectEnabled()
        auto_select_criteria = self.duplicates_page.getAutoSelectCriteria()
        
        # 重置去重页面
        self.duplicates_page.clearDuplicateGroups()
        self.duplicates_page.resetProgress()
        
        # 手动触发去重开始事件，因为DuplicateFinderController没有定义duplicate_finder_started信号
        self._on_duplicate_finder_started()
        
        # 启动去重查找
        self.duplicate_finder_controller.find_duplicates(
            media_items, 
            similarity_threshold,
            method=duplicate_method,
            auto_select=auto_select,
            auto_select_criteria=auto_select_criteria
        )
    
    def _on_duplicate_finder_started(self):
        """去重开始处理"""
        if hasattr(self, 'duplicates_page'):
            self.duplicates_page.updateProgress(0, 100, "正在查找重复文件...")
        else:
            self.label_levelContrast.setText("正在查找重复文件...")
        self.toolButton_startContrast.setEnabled(False)
    
    def _on_duplicate_finder_completed(self, success):
        """去重完成处理"""
        self.toolButton_startContrast.setEnabled(True)
        
        if success:
            duplicates = self.duplicate_finder_controller.get_duplicates()
            if hasattr(self, 'duplicates_page'):
                if duplicates:
                    self.duplicates_page.updateProgress(100, 100, f"发现 {len(duplicates)} 组重复文件")
                    
                    # 将重复组添加到去重页面
                    for group in duplicates:
                        self.duplicates_page.addDuplicateGroup(group)
                        
                    # 如果启用了自动选择，执行自动选择
                    if self.duplicates_page.isAutoSelectEnabled():
                        self.duplicate_finder_controller.auto_select_best_items(
                            self.duplicates_page.getAutoSelectCriteria()
                        )
                else:
                    self.duplicates_page.updateProgress(100, 100, "未发现重复文件")
            else:
                if duplicates:
                    self.label_levelContrast.setText(f"发现 {len(duplicates)} 组重复文件")
                else:
                    self.label_levelContrast.setText("未发现重复文件")
        else:
            if hasattr(self, 'duplicates_page'):
                self.duplicates_page.updateProgress(0, 100, "查找失败")
            else:
                self.label_levelContrast.setText("查找失败")
    
    def _on_duplicate_finder_progress_updated(self, value, maximum, message):
        """去重进度更新处理"""
        if hasattr(self, 'duplicates_page'):
            self.duplicates_page.updateProgress(value, maximum, message)
        else:
            self.label_levelContrast.setText(message)
    
    def _on_duplicate_found(self, item1, item2, similarity):
        """发现重复项处理"""
        # 这个方法在去重控制器中可能不再需要，因为现在我们使用重复组的方式
        pass
    
    def _on_duplicate_finder_error_occurred(self, error_message):
        """去重错误处理"""
        if hasattr(self, 'duplicates_page'):
            self.duplicates_page.updateProgress(0, 100, f"错误: {error_message}")
        else:
            self.label_levelContrast.setText(f"错误: {error_message}")
        self.toolButton_startContrast.setEnabled(True)
    
    def _on_move_duplicates(self):
        """移动重复文件"""
        # 确保去重页面已初始化
        if not hasattr(self, 'duplicates_page'):
            self._init_duplicate_finder()
            return
        
        # 获取当前选中的重复组
        current_group_index = self.duplicates_page.duplicateGroupsListWidget.currentRow()
        if current_group_index < 0:
            self.duplicates_page.updateProgress(0, 100, "请先选择一个重复组")
            return
            
        # 获取目标路径
        target_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if not target_path:
            return
            
        # 应用去重结果（移动操作）
        result = self.duplicate_finder_controller.apply_result("move", target_path)
        
        # 更新UI
        if result.get("success", False):
            self.duplicates_page.updateProgress(100, 100, f"移动成功: {result.get('moved_count', 0)} 个文件")
            # 从列表中移除已处理的重复组
            self.duplicates_page.removeSelectedGroup()
        else:
            self.duplicates_page.updateProgress(0, 100, f"移动失败: {result.get('error', '未知错误')}")
    
    def _on_auto_select_duplicates(self):
        """自动选择重复文件"""
        # 确保去重页面已初始化
        if not hasattr(self, 'duplicates_page'):
            self._init_duplicate_finder()
            return
        
        # 获取自动选择标准
        criteria = self.duplicates_page.getAutoSelectCriteria()
        
        # 执行自动选择
        result = self.duplicate_finder_controller.auto_select_best_items(criteria)
        
        # 更新UI
        if result.get("success", False):
            self.duplicates_page.updateProgress(100, 100, "自动选择完成")
            # 刷新当前显示的重复组
            current_group_index = self.duplicates_page.duplicateGroupsListWidget.currentRow()
            if current_group_index >= 0:
                self.duplicates_page._display_group_items(current_group_index)
        else:
            self.duplicates_page.updateProgress(0, 100, f"自动选择失败: {result.get('error', '未知错误')}")
    
    def _on_delete_duplicates(self):
        """删除重复文件"""
        # 确保去重页面已初始化
        if not hasattr(self, 'duplicates_page'):
            self._init_duplicate_finder()
            return
        
        # 确认删除操作
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除", 
            "确定要删除选中的重复文件吗？此操作不可撤销！",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return
            
        # 应用去重结果（删除操作）
        result = self.duplicate_finder_controller.apply_result("delete")
        
        # 更新UI
        if result.get("success", False):
            self.duplicates_page.updateProgress(100, 100, f"删除成功: {result.get('deleted_count', 0)} 个文件")
            # 从列表中移除已处理的重复组
            self.duplicates_page.removeSelectedGroup()
        else:
            self.duplicates_page.updateProgress(0, 100, f"删除失败: {result.get('error', '未知错误')}")

    def _setup_drag_handlers(self):
        def start_drag(event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

        def move_window(event):
            if event.buttons() & QtCore.Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

        self.frame_head.mousePressEvent = start_drag
        self.frame_head.mouseMoveEvent = move_window

    def _toggle_maximize(self):
        is_max = self.isMaximized()
        self.showNormal() if is_max else self.showMaximized()
        icon = '最大化.svg' if is_max else '还原.svg'
        self.toolButton_maximum.setIcon(QtGui.QIcon(get_resource_path(f'resources/img/窗口控制/{icon}')))
        self.label_image_A.clear()
        self.label_image_A.setStyleSheet(f"image: url({get_resource_path('resources/img/page_3/对比.jpg')})")
        self.label_image_B.clear()
        self.label_image_B.setStyleSheet(f"image: url({get_resource_path('resources/img/page_3/对比.jpg')})")

    def _create_empty_widget(self, parentLayout):
        verticalLayout = QtWidgets.QVBoxLayout()
        verticalLayout.setObjectName(f"verticalLayout_emptyStatus_{parentLayout.objectName()}")
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum,
                                            QtWidgets.QSizePolicy.Policy.Expanding)
        verticalLayout.addItem(spacerItem1)
        widget = QtWidgets.QWidget(parent=self.scrollAreaWidgetContents_folds)
        widget.setStyleSheet(f"""
            QWidget {{
                background: rgba(0, 0, 0, 0);
                image: url({get_resource_path('resources/img/page_0/空状态.svg')});
                background-repeat: no-repeat;
                background-position: center;
                background-size: contain;
                min-width: 100px;
                min-height: 100px;
            }}
        """)
        widget.setObjectName(f"emptyWidget_{parentLayout.objectName()}")
        verticalLayout.addWidget(widget)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum,
                                            QtWidgets.QSizePolicy.Policy.Expanding)
        verticalLayout.addItem(spacerItem2)
        parentLayout.addLayout(verticalLayout, 0, 0, 1, 1)
        return widget

    def update_empty_status(self, layout_name, has_content):
        # Always use gridLayout_6 since it's the only layout that exists
        if 'gridLayout_6' in self.empty_widgets:
            widget = self.empty_widgets['gridLayout_6']
            widget.setVisible(not has_content)
