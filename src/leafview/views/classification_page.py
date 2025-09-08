# -*- coding: utf-8 -*-

from PyQt6 import QtCore, QtGui, QtWidgets


class ClassificationPageWidget(QtWidgets.QWidget):
    """分类管理页面组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("classificationPageWidget")
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
        self.toolbar.setObjectName("classificationToolbar")
        self.toolbar.setFixedHeight(50)
        
        # 工具栏布局
        self.toolbarLayout = QtWidgets.QHBoxLayout(self.toolbar)
        self.toolbarLayout.setContentsMargins(10, 10, 10, 10)
        
        # 创建工具栏按钮
        self.classifyButton = QtWidgets.QPushButton("开始分类")
        self.classifyButton.setObjectName("classifyButton")
        
        self.stopClassificationButton = QtWidgets.QPushButton("停止分类")
        self.stopClassificationButton.setObjectName("stopClassificationButton")
        
        self.addCategoryButton = QtWidgets.QPushButton("添加分类")
        self.addCategoryButton.setObjectName("addCategoryButton")
        
        self.editCategoryButton = QtWidgets.QPushButton("编辑分类")
        self.editCategoryButton.setObjectName("editCategoryButton")
        
        # 添加到工具栏布局
        self.toolbarLayout.addWidget(self.classifyButton)
        self.toolbarLayout.addWidget(self.stopClassificationButton)
        self.toolbarLayout.addWidget(self.addCategoryButton)
        self.toolbarLayout.addWidget(self.editCategoryButton)
        self.toolbarLayout.addStretch()
        
        # 创建分类设置区域
        self.settingsFrame = QtWidgets.QFrame()
        self.settingsFrame.setObjectName("settingsFrame")
        self.settingsFrame.setFixedHeight(100)
        
        # 设置区域布局
        self.settingsLayout = QtWidgets.QHBoxLayout(self.settingsFrame)
        self.settingsLayout.setContentsMargins(10, 10, 10, 10)
        
        # 创建分类设置控件
        self.methodComboBox = QtWidgets.QComboBox()
        self.methodComboBox.setObjectName("methodComboBox")
        self.methodComboBox.addItems(["按文件类型", "按日期", "按文件夹", "按自定义规则"])
        
        self.autoClassifyCheckBox = QtWidgets.QCheckBox("自动分类")
        self.autoClassifyCheckBox.setObjectName("autoClassifyCheckBox")
        
        self.createSubfoldersCheckBox = QtWidgets.QCheckBox("创建子文件夹")
        self.createSubfoldersCheckBox.setObjectName("createSubfoldersCheckBox")
        
        self.moveFilesCheckBox = QtWidgets.QCheckBox("移动文件")
        self.moveFilesCheckBox.setObjectName("moveFilesCheckBox")
        
        # 添加到设置区域布局
        self.settingsLayout.addWidget(QtWidgets.QLabel("分类方法:"))
        self.settingsLayout.addWidget(self.methodComboBox)
        self.settingsLayout.addStretch()
        self.settingsLayout.addWidget(self.autoClassifyCheckBox)
        self.settingsLayout.addWidget(self.createSubfoldersCheckBox)
        self.settingsLayout.addWidget(self.moveFilesCheckBox)
        
        # 创建分类结果区域
        self.resultSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        
        # 分类列表
        self.categoryListWidget = QtWidgets.QListWidget()
        self.categoryListWidget.setObjectName("categoryListWidget")
        self.categoryListWidget.setMaximumWidth(200)
        
        # 分类内容区域
        self.categoryContentWidget = QtWidgets.QWidget()
        self.categoryContentLayout = QtWidgets.QVBoxLayout(self.categoryContentWidget)
        self.categoryContentLayout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分类筛选栏
        self.filterBar = QtWidgets.QFrame()
        self.filterBar.setObjectName("categoryFilterBar")
        self.filterBar.setFixedHeight(40)
        
        # 筛选栏布局
        self.filterBarLayout = QtWidgets.QHBoxLayout(self.filterBar)
        self.filterBarLayout.setContentsMargins(10, 5, 10, 5)
        
        # 创建筛选控件
        self.searchLineEdit = QtWidgets.QLineEdit()
        self.searchLineEdit.setPlaceholderText("搜索分类中的文件...")
        self.searchLineEdit.setObjectName("categorySearchLineEdit")
        
        self.sortComboBox = QtWidgets.QComboBox()
        self.sortComboBox.setObjectName("categorySortComboBox")
        self.sortComboBox.addItems(["按名称", "按日期", "按大小"])
        
        # 添加到筛选栏布局
        self.filterBarLayout.addWidget(self.searchLineEdit)
        self.filterBarLayout.addWidget(self.sortComboBox)
        
        # 创建分类文件显示区域
        self.categoryDisplayWidget = QtWidgets.QStackedWidget()
        
        # 网格视图
        self.categoryGridViewWidget = QtWidgets.QWidget()
        self.categoryGridViewLayout = QtWidgets.QVBoxLayout(self.categoryGridViewWidget)
        self.categoryGridViewLayout.setContentsMargins(10, 10, 10, 10)
        
        self.categoryGridScrollArea = QtWidgets.QScrollArea()
        self.categoryGridScrollArea.setWidgetResizable(True)
        self.categoryGridScrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.categoryGridScrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.categoryGridWidget = QtWidgets.QWidget()
        self.categoryGridLayout = QtWidgets.QGridLayout(self.categoryGridWidget)
        self.categoryGridLayout.setSpacing(10)
        
        self.categoryGridScrollArea.setWidget(self.categoryGridWidget)
        self.categoryGridViewLayout.addWidget(self.categoryGridScrollArea)
        
        # 列表视图
        self.categoryListViewWidget = QtWidgets.QWidget()
        self.categoryListViewLayout = QtWidgets.QVBoxLayout(self.categoryListViewWidget)
        self.categoryListViewLayout.setContentsMargins(10, 10, 10, 10)
        
        self.categoryTableWidget = QtWidgets.QTableWidget()
        self.categoryTableWidget.setObjectName("categoryTableWidget")
        self.categoryTableWidget.setColumnCount(4)
        self.categoryTableWidget.setHorizontalHeaderLabels(["名称", "类型", "大小", "修改日期"])
        self.categoryTableWidget.horizontalHeader().setStretchLastSection(True)
        
        self.categoryListViewLayout.addWidget(self.categoryTableWidget)
        
        # 添加视图到堆叠窗口
        self.categoryDisplayWidget.addWidget(self.categoryGridViewWidget)
        self.categoryDisplayWidget.addWidget(self.categoryListViewWidget)
        
        # 添加到分类内容布局
        self.categoryContentLayout.addWidget(self.filterBar)
        self.categoryContentLayout.addWidget(self.categoryDisplayWidget)
        
        # 添加到分割器
        self.resultSplitter.addWidget(self.categoryListWidget)
        self.resultSplitter.addWidget(self.categoryContentWidget)
        self.resultSplitter.setSizes([200, 800])
        
        # 创建进度条
        self.progressFrame = QtWidgets.QFrame()
        self.progressFrame.setObjectName("progressFrame")
        self.progressFrame.setFixedHeight(30)
        
        # 进度条布局
        self.progressLayout = QtWidgets.QHBoxLayout(self.progressFrame)
        self.progressLayout.setContentsMargins(10, 5, 10, 5)
        
        # 创建进度条控件
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setObjectName("classificationProgressBar")
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        
        self.progressLabel = QtWidgets.QLabel("就绪")
        self.progressLabel.setObjectName("progressLabel")
        
        # 添加到进度条布局
        self.progressLayout.addWidget(self.progressBar)
        self.progressLayout.addWidget(self.progressLabel)
        
        # 添加到主布局
        self.mainLayout.addWidget(self.toolbar)
        self.mainLayout.addWidget(self.settingsFrame)
        self.mainLayout.addWidget(self.resultSplitter)
        self.mainLayout.addWidget(self.progressFrame)
        
        # 设置默认视图为网格视图
        self.categoryDisplayWidget.setCurrentIndex(0)
    
    def _setup_styles(self):
        """设置样式表"""
        # 工具栏样式
        self.toolbar.setStyleSheet("""
            QFrame#classificationToolbar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 工具栏按钮样式
        self.classifyButton.setStyleSheet("""
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
        
        self.stopClassificationButton.setStyleSheet("""
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
        
        self.addCategoryButton.setStyleSheet("""
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
        
        self.editCategoryButton.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)
        
        # 设置区域样式
        self.settingsFrame.setStyleSheet("""
            QFrame#settingsFrame {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 下拉框样式
        self.methodComboBox.setStyleSheet("""
            QComboBox#methodComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        # 复选框样式
        self.autoClassifyCheckBox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        self.createSubfoldersCheckBox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        self.moveFilesCheckBox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        # 分类列表样式
        self.categoryListWidget.setStyleSheet("""
            QListWidget#categoryListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget#categoryListWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget#categoryListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # 筛选栏样式
        self.filterBar.setStyleSheet("""
            QFrame#categoryFilterBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 搜索框样式
        self.searchLineEdit.setStyleSheet("""
            QLineEdit#categorySearchLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        # 下拉框样式
        self.sortComboBox.setStyleSheet("""
            QComboBox#categorySortComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        # 表格样式
        self.categoryTableWidget.setStyleSheet("""
            QTableWidget#categoryTableWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                gridline-color: #f8f9fa;
            }
            QTableWidget#categoryTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f8f9fa;
            }
            QTableWidget#categoryTableWidget::item:selected {
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
        
        # 进度条样式
        self.progressFrame.setStyleSheet("""
            QFrame#progressFrame {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
            }
        """)
        
        self.progressBar.setStyleSheet("""
            QProgressBar#classificationProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                text-align: center;
                background-color: #e9ecef;
            }
            QProgressBar#classificationProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        
        self.progressLabel.setStyleSheet("""
            QLabel#progressLabel {
                color: #495057;
            }
        """)
    
    def toggleViewMode(self):
        """切换视图模式"""
        current_index = self.categoryDisplayWidget.currentIndex()
        new_index = 1 - current_index  # 0和1之间切换
        self.categoryDisplayWidget.setCurrentIndex(new_index)
    
    def addCategory(self, category_name):
        """添加分类到列表"""
        item = QtWidgets.QListWidgetItem(category_name)
        self.categoryListWidget.addItem(item)
    
    def removeSelectedCategory(self):
        """移除选中的分类"""
        current_item = self.categoryListWidget.currentItem()
        if current_item:
            self.categoryListWidget.takeItem(self.categoryListWidget.row(current_item))
    
    def clearCategories(self):
        """清空分类列表"""
        self.categoryListWidget.clear()
    
    def getSelectedCategory(self):
        """获取选中的分类"""
        current_item = self.categoryListWidget.currentItem()
        if current_item:
            return current_item.text()
        return None
    
    def getSearchText(self):
        """获取搜索文本"""
        return self.searchLineEdit.text()
    
    def getSortType(self):
        """获取排序类型"""
        return self.sortComboBox.currentText()
    
    def getClassificationMethod(self):
        """获取分类方法"""
        return self.methodComboBox.currentText()
    
    def isAutoClassifyEnabled(self):
        """是否启用自动分类"""
        return self.autoClassifyCheckBox.isChecked()
    
    def isCreateSubfoldersEnabled(self):
        """是否启用创建子文件夹"""
        return self.createSubfoldersCheckBox.isChecked()
    
    def isMoveFilesEnabled(self):
        """是否启用移动文件"""
        return self.moveFilesCheckBox.isChecked()
    
    def updateProgress(self, value, text=None):
        """更新进度条"""
        self.progressBar.setValue(value)
        if text:
            self.progressLabel.setText(text)
    
    def resetProgress(self):
        """重置进度条"""
        self.progressBar.setValue(0)
        self.progressLabel.setText("就绪")