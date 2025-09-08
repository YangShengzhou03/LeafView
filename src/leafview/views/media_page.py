# -*- coding: utf-8 -*-

from PyQt6 import QtCore, QtGui, QtWidgets


class MediaPageWidget(QtWidgets.QWidget):
    """媒体管理页面组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mediaPageWidget")
        self._setup_ui()
        self._setup_styles()
    
    def _setup_ui(self):
        """设置UI布局"""
        # 主布局
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        
        # 创建工具栏
        self.toolbar = QtWidgets.QFrame()
        self.toolbar.setObjectName("mediaToolbar")
        self.toolbar.setFixedHeight(50)
        
        # 工具栏布局
        self.toolbarLayout = QtWidgets.QHBoxLayout(self.toolbar)
        self.toolbarLayout.setContentsMargins(10, 10, 10, 10)
        
        # 创建工具栏按钮
        self.addFolderButton = QtWidgets.QPushButton("添加文件夹")
        self.addFolderButton.setObjectName("addFolderButton")
        
        self.removeFolderButton = QtWidgets.QPushButton("移除文件夹")
        self.removeFolderButton.setObjectName("removeFolderButton")
        
        self.refreshButton = QtWidgets.QPushButton("刷新")
        self.refreshButton.setObjectName("refreshButton")
        
        self.viewModeButton = QtWidgets.QPushButton("视图模式")
        self.viewModeButton.setObjectName("viewModeButton")
        
        # 添加到工具栏布局
        self.toolbarLayout.addWidget(self.addFolderButton)
        self.toolbarLayout.addWidget(self.removeFolderButton)
        self.toolbarLayout.addWidget(self.refreshButton)
        self.toolbarLayout.addWidget(self.viewModeButton)
        self.toolbarLayout.addStretch()
        
        # 创建文件夹列表和媒体内容区域
        self.contentSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        
        # 文件夹列表
        self.folderListWidget = QtWidgets.QListWidget()
        self.folderListWidget.setObjectName("folderListWidget")
        self.folderListWidget.setMaximumWidth(200)
        
        # 媒体内容区域
        self.mediaContentWidget = QtWidgets.QWidget()
        self.mediaContentLayout = QtWidgets.QVBoxLayout(self.mediaContentWidget)
        self.mediaContentLayout.setContentsMargins(0, 0, 0, 0)
        
        # 创建媒体筛选栏
        self.filterBar = QtWidgets.QFrame()
        self.filterBar.setObjectName("filterBar")
        self.filterBar.setFixedHeight(40)
        
        # 筛选栏布局
        self.filterBarLayout = QtWidgets.QHBoxLayout(self.filterBar)
        self.filterBarLayout.setContentsMargins(10, 5, 10, 5)
        
        # 创建筛选控件
        self.searchLineEdit = QtWidgets.QLineEdit()
        self.searchLineEdit.setPlaceholderText("搜索媒体文件...")
        self.searchLineEdit.setObjectName("searchLineEdit")
        
        self.filterTypeComboBox = QtWidgets.QComboBox()
        self.filterTypeComboBox.setObjectName("filterTypeComboBox")
        self.filterTypeComboBox.addItems(["全部", "图片", "视频"])
        
        self.sortComboBox = QtWidgets.QComboBox()
        self.sortComboBox.setObjectName("sortComboBox")
        self.sortComboBox.addItems(["按名称", "按日期", "按大小"])
        
        # 添加到筛选栏布局
        self.filterBarLayout.addWidget(self.searchLineEdit)
        self.filterBarLayout.addWidget(self.filterTypeComboBox)
        self.filterBarLayout.addWidget(self.sortComboBox)
        
        # 创建媒体显示区域
        self.mediaDisplayWidget = QtWidgets.QStackedWidget()
        
        # 网格视图
        self.gridViewWidget = QtWidgets.QWidget()
        self.gridViewLayout = QtWidgets.QVBoxLayout(self.gridViewWidget)
        self.gridViewLayout.setContentsMargins(10, 10, 10, 10)
        
        self.gridScrollArea = QtWidgets.QScrollArea()
        self.gridScrollArea.setWidgetResizable(True)
        self.gridScrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.gridScrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.gridWidget = QtWidgets.QWidget()
        self.gridLayout = QtWidgets.QGridLayout(self.gridWidget)
        self.gridLayout.setSpacing(10)
        
        self.gridScrollArea.setWidget(self.gridWidget)
        self.gridViewLayout.addWidget(self.gridScrollArea)
        
        # 列表视图
        self.listViewWidget = QtWidgets.QWidget()
        self.listViewLayout = QtWidgets.QVBoxLayout(self.listViewWidget)
        self.listViewLayout.setContentsMargins(10, 10, 10, 10)
        
        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setObjectName("mediaTableWidget")
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setHorizontalHeaderLabels(["名称", "类型", "大小", "修改日期"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        
        self.listViewLayout.addWidget(self.tableWidget)
        
        # 添加视图到堆叠窗口
        self.mediaDisplayWidget.addWidget(self.gridViewWidget)
        self.mediaDisplayWidget.addWidget(self.listViewWidget)
        
        # 添加到媒体内容布局
        self.mediaContentLayout.addWidget(self.filterBar)
        self.mediaContentLayout.addWidget(self.mediaDisplayWidget)
        
        # 添加到分割器
        self.contentSplitter.addWidget(self.folderListWidget)
        self.contentSplitter.addWidget(self.mediaContentWidget)
        self.contentSplitter.setSizes([200, 800])
        
        # 添加到主布局
        self.mainLayout.addWidget(self.toolbar)
        self.mainLayout.addWidget(self.contentSplitter)
        
        # 设置默认视图为网格视图
        self.mediaDisplayWidget.setCurrentIndex(0)
    
    def _setup_styles(self):
        """设置样式表"""
        # 工具栏样式
        self.toolbar.setStyleSheet("""
            QFrame#mediaToolbar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 工具栏按钮样式
        self.addFolderButton.setStyleSheet("""
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
        
        self.removeFolderButton.setStyleSheet("""
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
        
        self.refreshButton.setStyleSheet("""
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
        
        self.viewModeButton.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        
        # 文件夹列表样式
        self.folderListWidget.setStyleSheet("""
            QListWidget#folderListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget#folderListWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget#folderListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # 筛选栏样式
        self.filterBar.setStyleSheet("""
            QFrame#filterBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 搜索框样式
        self.searchLineEdit.setStyleSheet("""
            QLineEdit#searchLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        # 下拉框样式
        self.filterTypeComboBox.setStyleSheet("""
            QComboBox#filterTypeComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        self.sortComboBox.setStyleSheet("""
            QComboBox#sortComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        # 表格样式
        self.tableWidget.setStyleSheet("""
            QTableWidget#mediaTableWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                gridline-color: #f8f9fa;
            }
            QTableWidget#mediaTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f8f9fa;
            }
            QTableWidget#mediaTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 5px;
                border: 1px solid #dee2e6;
                font-weight: bold;
            }
        """)
    
    def toggleViewMode(self):
        """切换视图模式"""
        current_index = self.mediaDisplayWidget.currentIndex()
        new_index = 1 - current_index  # 0和1之间切换
        self.mediaDisplayWidget.setCurrentIndex(new_index)
        
        if new_index == 0:
            self.viewModeButton.setText("网格视图")
        else:
            self.viewModeButton.setText("列表视图")
    
    def addFolder(self, folder_path):
        """添加文件夹到列表"""
        item = QtWidgets.QListWidgetItem(folder_path)
        self.folderListWidget.addItem(item)
    
    def removeSelectedFolder(self):
        """移除选中的文件夹"""
        current_item = self.folderListWidget.currentItem()
        if current_item:
            self.folderListWidget.takeItem(self.folderListWidget.row(current_item))
    
    def clearFolders(self):
        """清空文件夹列表"""
        self.folderListWidget.clear()
    
    def getSelectedFolders(self):
        """获取选中的文件夹路径列表"""
        folders = []
        for i in range(self.folderListWidget.count()):
            item = self.folderListWidget.item(i)
            folders.append(item.text())
        return folders
    
    def getSearchText(self):
        """获取搜索文本"""
        return self.searchLineEdit.text()
    
    def getFilterType(self):
        """获取筛选类型"""
        return self.filterTypeComboBox.currentText()
    
    def getSortType(self):
        """获取排序类型"""
        return self.sortComboBox.currentText()