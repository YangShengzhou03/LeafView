# -*- coding: utf-8 -*-

from PyQt6 import QtCore, QtGui, QtWidgets


class DuplicatesPageWidget(QtWidgets.QWidget):
    """去重管理页面组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("duplicatesPageWidget")
        self._is_grid_view = True  # 添加视图模式状态变量
        self.duplicate_groups = []  # 添加重复组列表
        self._setup_ui()
        self._setup_styles()
        
        # 连接信号槽
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI布局"""
        # 主布局
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        
        # 创建工具栏
        self.toolbar = QtWidgets.QFrame()
        self.toolbar.setObjectName("duplicatesToolbar")
        self.toolbar.setFixedHeight(50)
        
        # 工具栏布局
        self.toolbarLayout = QtWidgets.QHBoxLayout(self.toolbar)
        self.toolbarLayout.setContentsMargins(10, 10, 10, 10)
        
        # 创建工具栏按钮
        self.startDuplicateButton = QtWidgets.QPushButton("开始去重")
        self.startDuplicateButton.setObjectName("startDuplicateButton")
        
        self.stopDuplicateButton = QtWidgets.QPushButton("停止去重")
        self.stopDuplicateButton.setObjectName("stopDuplicateButton")
        
        self.applyDuplicateButton = QtWidgets.QPushButton("应用结果")
        self.applyDuplicateButton.setObjectName("applyDuplicateButton")
        
        # 添加到工具栏布局
        self.toolbarLayout.addWidget(self.startDuplicateButton)
        self.toolbarLayout.addWidget(self.stopDuplicateButton)
        self.toolbarLayout.addWidget(self.applyDuplicateButton)
        self.toolbarLayout.addStretch()
        
        # 创建去重设置区域
        self.settingsFrame = QtWidgets.QFrame()
        self.settingsFrame.setObjectName("duplicatesSettingsFrame")
        self.settingsFrame.setFixedHeight(100)
        
        # 设置区域布局
        self.settingsLayout = QtWidgets.QHBoxLayout(self.settingsFrame)
        self.settingsLayout.setContentsMargins(10, 10, 10, 10)
        
        # 创建去重设置控件
        self.methodComboBox = QtWidgets.QComboBox()
        self.methodComboBox.setObjectName("duplicatesMethodComboBox")
        self.methodComboBox.addItems(["按文件内容", "按文件名", "按文件大小", "按图像相似度"])
        
        # 相似度阈值滑块和标签
        self.similarityLabel = QtWidgets.QLabel("相似度阈值:")
        self.similaritySlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.similaritySlider.setObjectName("similaritySlider")
        self.similaritySlider.setRange(50, 100)
        self.similaritySlider.setValue(85)
        self.similaritySlider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.similaritySlider.setTickInterval(5)
        
        self.similaritySpinBox = QtWidgets.QSpinBox()
        self.similaritySpinBox.setObjectName("similaritySpinBox")
        self.similaritySpinBox.setRange(50, 100)
        self.similaritySpinBox.setValue(85)
        self.similaritySpinBox.setSuffix("%")
        
        # 自动选择选项
        self.autoSelectCheckBox = QtWidgets.QCheckBox("自动选择最佳文件")
        self.autoSelectCheckBox.setObjectName("autoSelectCheckBox")
        
        self.autoSelectCriteriaComboBox = QtWidgets.QComboBox()
        self.autoSelectCriteriaComboBox.setObjectName("autoSelectCriteriaComboBox")
        self.autoSelectCriteriaComboBox.addItems(["最高分辨率", "最新修改", "最大文件", "最短路径"])
        
        # 添加到设置区域布局
        self.settingsLayout.addWidget(QtWidgets.QLabel("去重方法:"))
        self.settingsLayout.addWidget(self.methodComboBox)
        self.settingsLayout.addSpacing(20)
        self.settingsLayout.addWidget(self.similarityLabel)
        self.settingsLayout.addWidget(self.similaritySlider)
        self.settingsLayout.addWidget(self.similaritySpinBox)
        self.settingsLayout.addSpacing(20)
        self.settingsLayout.addWidget(self.autoSelectCheckBox)
        self.settingsLayout.addWidget(self.autoSelectCriteriaComboBox)
        self.settingsLayout.addStretch()
        
        # 创建去重结果区域
        self.resultSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        
        # 重复组列表
        self.duplicateGroupsListWidget = QtWidgets.QListWidget()
        self.duplicateGroupsListWidget.setObjectName("duplicateGroupsListWidget")
        self.duplicateGroupsListWidget.setMaximumWidth(250)
        
        # 重复文件内容区域
        self.duplicateContentWidget = QtWidgets.QWidget()
        self.duplicateContentLayout = QtWidgets.QVBoxLayout(self.duplicateContentWidget)
        self.duplicateContentLayout.setContentsMargins(0, 0, 0, 0)
        
        # 创建重复文件信息栏
        self.infoBar = QtWidgets.QFrame()
        self.infoBar.setObjectName("duplicateInfoBar")
        self.infoBar.setFixedHeight(40)
        
        # 信息栏布局
        self.infoBarLayout = QtWidgets.QHBoxLayout(self.infoBar)
        self.infoBarLayout.setContentsMargins(10, 5, 10, 5)
        
        # 创建信息栏控件
        self.groupInfoLabel = QtWidgets.QLabel("选择一个重复组查看详情")
        self.groupInfoLabel.setObjectName("groupInfoLabel")
        
        self.selectAllButton = QtWidgets.QPushButton("全选")
        self.selectAllButton.setObjectName("selectAllButton")
        
        self.deselectAllButton = QtWidgets.QPushButton("取消全选")
        self.deselectAllButton.setObjectName("deselectAllButton")
        
        # 添加到信息栏布局
        self.infoBarLayout.addWidget(self.groupInfoLabel)
        self.infoBarLayout.addStretch()
        self.infoBarLayout.addWidget(self.selectAllButton)
        self.infoBarLayout.addWidget(self.deselectAllButton)
        
        # 创建重复文件显示区域
        self.duplicate_items_view = QtWidgets.QListWidget()
        self.duplicate_items_view.setObjectName("duplicateItemsView")
        
        # 添加到重复文件内容布局
        self.duplicateContentLayout.addWidget(self.infoBar)
        self.duplicateContentLayout.addWidget(self.duplicate_items_view)
        
        # 添加到分割器
        self.resultSplitter.addWidget(self.duplicateGroupsListWidget)
        self.resultSplitter.addWidget(self.duplicateContentWidget)
        self.resultSplitter.setSizes([250, 750])
        
        # 创建进度条
        self.progressFrame = QtWidgets.QFrame()
        self.progressFrame.setObjectName("duplicateProgressFrame")
        self.progressFrame.setFixedHeight(30)
        
        # 进度条布局
        self.progressLayout = QtWidgets.QHBoxLayout(self.progressFrame)
        self.progressLayout.setContentsMargins(10, 5, 10, 5)
        
        # 创建进度条控件
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setObjectName("duplicateProgressBar")
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        
        self.progressLabel = QtWidgets.QLabel("就绪")
        self.progressLabel.setObjectName("duplicateProgressLabel")
        
        # 添加到进度条布局
        self.progressLayout.addWidget(self.progressBar)
        self.progressLayout.addWidget(self.progressLabel)
        
        # 添加到主布局
        self.mainLayout.addWidget(self.toolbar)
        self.mainLayout.addWidget(self.settingsFrame)
        self.mainLayout.addWidget(self.resultSplitter)
        self.mainLayout.addWidget(self.progressFrame)
        
        # 添加视图切换按钮
        self.viewToggleBtn = QtWidgets.QPushButton("切换视图")
        self.viewToggleBtn.setObjectName("viewToggleBtn")
        self.toolbarLayout.addWidget(self.viewToggleBtn)
        
        # 添加选择和删除按钮
        self.selectButton = QtWidgets.QPushButton("选择")
        self.selectButton.setObjectName("selectButton")
        
        self.deleteButton = QtWidgets.QPushButton("删除")
        self.deleteButton.setObjectName("deleteButton")
        
        self.infoBarLayout.addWidget(self.selectButton)
        self.infoBarLayout.addWidget(self.deleteButton)
    
    def _setup_styles(self):
        """设置样式表"""
        # 工具栏样式
        self.toolbar.setStyleSheet("""
            QFrame#duplicatesToolbar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 工具栏按钮样式
        self.startDuplicateButton.setStyleSheet("""
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
        
        self.stopDuplicateButton.setStyleSheet("""
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
        
        self.applyDuplicateButton.setStyleSheet("""
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
        
        # 设置区域样式
        self.settingsFrame.setStyleSheet("""
            QFrame#duplicatesSettingsFrame {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 下拉框样式
        self.methodComboBox.setStyleSheet("""
            QComboBox#duplicatesMethodComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        self.autoSelectCriteriaComboBox.setStyleSheet("""
            QComboBox#autoSelectCriteriaComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        # 滑块样式
        self.similaritySlider.setStyleSheet("""
            QSlider#similaritySlider::groove:horizontal {
                border: 1px solid #ced4da;
                height: 8px;
                background: white;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider#similaritySlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #3498db;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        
        # 微调框样式
        self.similaritySpinBox.setStyleSheet("""
            QSpinBox#similaritySpinBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        # 复选框样式
        self.autoSelectCheckBox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        # 重复组列表样式
        self.duplicateGroupsListWidget.setStyleSheet("""
            QListWidget#duplicateGroupsListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget#duplicateGroupsListWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget#duplicateGroupsListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # 信息栏样式
        self.infoBar.setStyleSheet("""
            QFrame#duplicateInfoBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # 信息标签样式
        self.groupInfoLabel.setStyleSheet("""
            QLabel#groupInfoLabel {
                color: #495057;
                font-weight: bold;
            }
        """)
        
        # 选择按钮样式
        self.selectAllButton.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.deselectAllButton.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        # 重复项列表样式
        self.duplicate_items_view.setStyleSheet("""
            QListWidget#duplicateItemsView {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QListWidget#duplicateItemsView::item {
                padding: 5px;
                border-bottom: 1px solid #f8f9fa;
            }
            QListWidget#duplicateItemsView::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # 进度条样式
        self.progressFrame.setStyleSheet("""
            QFrame#duplicateProgressFrame {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
            }
        """)
        
        self.progressBar.setStyleSheet("""
            QProgressBar#duplicateProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                text-align: center;
                background-color: #e9ecef;
            }
            QProgressBar#duplicateProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        
        self.progressLabel.setStyleSheet("""
            QLabel#duplicateProgressLabel {
                color: #495057;
            }
        """)
        
        # 视图切换按钮样式
        self.viewToggleBtn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        # 选择和删除按钮样式
        self.selectButton.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        self.deleteButton.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)

    def _connect_signals(self):
        """连接信号槽"""
        # 视图切换按钮
        self.viewToggleBtn.clicked.connect(self.toggleViewMode)
        
        # 重复组列表选择
        self.duplicateGroupsListWidget.currentRowChanged.connect(self._on_group_selected)
        
        # 重复项列表选择
        self.duplicate_items_view.currentRowChanged.connect(self._on_item_selected)
        
        # 选择和删除按钮
        self.selectButton.clicked.connect(self._on_select_button_clicked)
        self.deleteButton.clicked.connect(self._on_delete_button_clicked)
        
        # 全选和取消全选按钮
        self.selectAllButton.clicked.connect(self._on_select_all_clicked)
        self.deselectAllButton.clicked.connect(self._on_deselect_all_clicked)
        
        # 相似度滑块和数值框同步
        self.similaritySlider.valueChanged.connect(self.similaritySpinBox.setValue)
        self.similaritySpinBox.valueChanged.connect(self.similaritySlider.setValue)
        
        # 工具栏按钮
        self.startDuplicateButton.clicked.connect(self._on_start_duplicate_clicked)
        self.stopDuplicateButton.clicked.connect(self._on_stop_duplicate_clicked)
        self.applyDuplicateButton.clicked.connect(self._on_apply_duplicate_clicked)
    
    def _on_start_duplicate_clicked(self):
        """处理开始去重按钮点击事件"""
        # 这里会连接到控制器的开始去重方法
        pass
    
    def _on_stop_duplicate_clicked(self):
        """处理停止去重按钮点击事件"""
        # 这里会连接到控制器的停止去重方法
        pass
    
    def _on_apply_duplicate_clicked(self):
        """处理应用去重结果按钮点击事件"""
        # 这里会连接到控制器的应用去重结果方法
        pass
    
    def _on_select_all_clicked(self):
        """处理全选按钮点击事件"""
        group_row = self.duplicateGroupsListWidget.currentRow()
        if 0 <= group_row < len(self.duplicate_groups):
            group = self.duplicate_groups[group_row]
            for i in range(len(group.items)):
                group.set_action(i, "keep")
            self._display_group_items(group_row)
    
    def _on_deselect_all_clicked(self):
        """处理取消全选按钮点击事件"""
        group_row = self.duplicateGroupsListWidget.currentRow()
        if 0 <= group_row < len(self.duplicate_groups):
            group = self.duplicate_groups[group_row]
            for i in range(len(group.items)):
                group.set_action(i, "none")
            self._display_group_items(group_row)
    
    def toggleViewMode(self):
        """切换视图模式（网格/列表）"""
        self._is_grid_view = not self._is_grid_view
        
        if self._is_grid_view:
            # 网格视图模式
            self.duplicateGroupsListWidget.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
            self.duplicateGroupsListWidget.setGridSize(QtCore.QSize(120, 120))
            self.duplicateGroupsListWidget.setIconSize(QtCore.QSize(100, 100))
            self.duplicate_items_view.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
            self.duplicate_items_view.setGridSize(QtCore.QSize(120, 120))
            self.duplicate_items_view.setIconSize(QtCore.QSize(100, 100))
        else:
            # 列表视图模式
            self.duplicateGroupsListWidget.setViewMode(QtWidgets.QListView.ViewMode.ListMode)
            self.duplicate_items_view.setViewMode(QtWidgets.QListView.ViewMode.ListMode)
        
        # 刷新当前显示
        current_group = self.duplicateGroupsListWidget.currentRow()
        if current_group >= 0:
            self._display_group_items(current_group)
    
    def addDuplicateGroup(self, group):
        """添加重复组到列表
        
        Args:
            group: 重复组对象
        """
        # 创建组项
        item = QtWidgets.QListWidgetItem()
        
        # 设置组信息
        item.setText(f"组 {len(self.duplicate_groups) + 1} ({len(group.items)} 项)")
        
        # 设置组图标（使用第一项的缩略图）
        if group.items and hasattr(group.items[0], 'thumbnail_path') and group.items[0].thumbnail_path:
            item.setIcon(QtGui.QIcon(group.items[0].thumbnail_path))
        else:
            # 使用默认图标
            item.setIcon(QtGui.QIcon.fromTheme("image-x-generic"))
        
        # 添加到列表
        self.duplicateGroupsListWidget.addItem(item)
        self.duplicate_groups.append(group)
    
    def removeSelectedGroup(self):
        """移除选中的重复组"""
        current_row = self.duplicateGroupsListWidget.currentRow()
        if current_row >= 0:
            # 从列表中移除
            self.duplicateGroupsListWidget.takeItem(current_row)
            self.duplicate_groups.pop(current_row)
            
            # 清空详情显示
            self.duplicate_items_view.clear()
            self.groupInfoLabel.setText("选择一个重复组查看详情")
    
    def clearDuplicateGroups(self):
        """清空所有重复组"""
        self.duplicateGroupsListWidget.clear()
        self.duplicate_items_view.clear()
        self.groupInfoLabel.setText("选择一个重复组查看详情")
        self.duplicate_groups.clear()
    
    def getDuplicateMethod(self):
        """获取当前选择的去重方法
        
        Returns:
            去重方法字符串
        """
        return self.methodComboBox.currentText()
    
    def getSimilarityThreshold(self):
        """获取当前设置的相似度阈值
        
        Returns:
            相似度阈值（0-1之间的浮点数）
        """
        return self.similaritySlider.value() / 100.0
    
    def getAutoSelectCriteria(self):
        """获取自动选择标准
        
        Returns:
            自动选择标准字符串
        """
        return self.autoSelectCriteriaComboBox.currentText()
    
    def isAutoSelectEnabled(self):
        """是否启用自动选择
        
        Returns:
            布尔值，表示是否启用自动选择
        """
        return self.autoSelectCheckBox.isChecked()
    
    def updateProgress(self, value, maximum=None, message=None):
        """更新进度条
        
        Args:
            value: 当前进度值
            maximum: 最大进度值（可选）
            message: 进度消息（可选）
        """
        self.progressBar.setValue(value)
        if maximum is not None:
            self.progressBar.setMaximum(maximum)
        if message is not None:
            self.progressLabel.setText(message)
    
    def resetProgress(self):
        """重置进度条"""
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(100)
        self.progressLabel.setText("就绪")
    
    def _display_group_items(self, group_index):
        """显示指定组的所有项
        
        Args:
            group_index: 组索引
        """
        if 0 <= group_index < len(self.duplicate_groups):
            group = self.duplicate_groups[group_index]
            
            # 清空当前显示
            self.duplicate_items_view.clear()
            
            # 添加组中的所有项
            for i, item in enumerate(group.items):
                list_item = QtWidgets.QListWidgetItem()
                
                # 设置项信息
                file_size_mb = item.file_size / (1024 * 1024)
                list_item.setText(f"{item.filename}\n{file_size_mb:.2f} MB")
                
                # 设置图标（使用缩略图）
                if hasattr(item, 'thumbnail_path') and item.thumbnail_path:
                    list_item.setIcon(QtGui.QIcon(item.thumbnail_path))
                else:
                    # 使用默认图标
                    list_item.setIcon(QtGui.QIcon.fromTheme("image-x-generic"))
                
                # 设置数据，用于后续操作
                list_item.setData(QtCore.Qt.ItemDataRole.UserRole, i)
                
                # 根据操作类型设置不同的样式
                action = group.get_action(i)
                if action == "delete":
                    list_item.setBackground(QtGui.QColor(255, 200, 200))  # 浅红色背景
                elif action == "keep":
                    list_item.setBackground(QtGui.QColor(200, 255, 200))  # 浅绿色背景
                
                self.duplicate_items_view.addItem(list_item)
            
            # 更新信息栏
            self.groupInfoLabel.setText(f"组 {group_index + 1}: {len(group.items)} 个文件")
    
    def _on_group_selected(self, current_row):
        """处理组选择事件
        
        Args:
            current_row: 选中的行索引
        """
        if current_row >= 0:
            self._display_group_items(current_row)
    
    def _on_item_selected(self, current_row):
        """处理项选择事件
        
        Args:
            current_row: 选中的行索引
        """
        if current_row >= 0:
            # 获取当前选中的组
            group_row = self.duplicateGroupsListWidget.currentRow()
            if 0 <= group_row < len(self.duplicate_groups):
                group = self.duplicate_groups[group_row]
                
                # 获取选中的项
                item_index = self.duplicate_items_view.item(current_row).data(QtCore.Qt.ItemDataRole.UserRole)
                if 0 <= item_index < len(group.items):
                    item = group.items[item_index]
                    
                    # 更新信息栏
                    file_size_mb = item.file_size / (1024 * 1024)
                    self.groupInfoLabel.setText(f"{item.filename} - {file_size_mb:.2f} MB")
    
    def _on_select_button_clicked(self):
        """处理选择按钮点击事件"""
        # 获取当前选中的组和项
        group_row = self.duplicateGroupsListWidget.currentRow()
        item_row = self.duplicate_items_view.currentRow()
        
        if group_row >= 0 and item_row >= 0:
            group = self.duplicate_groups[group_row]
            item_index = self.duplicate_items_view.item(item_row).data(QtCore.Qt.ItemDataRole.UserRole)
            
            if 0 <= item_index < len(group.items):
                # 切换选择状态
                current_action = group.get_action(item_index)
                if current_action == "keep":
                    group.set_action(item_index, "none")
                else:
                    group.set_action(item_index, "keep")
                
                # 刷新显示
                self._display_group_items(group_row)
    
    def _on_delete_button_clicked(self):
        """处理删除按钮点击事件"""
        # 获取当前选中的组和项
        group_row = self.duplicateGroupsListWidget.currentRow()
        item_row = self.duplicate_items_view.currentRow()
        
        if group_row >= 0 and item_row >= 0:
            group = self.duplicate_groups[group_row]
            item_index = self.duplicate_items_view.item(item_row).data(QtCore.Qt.ItemDataRole.UserRole)
            
            if 0 <= item_index < len(group.items):
                # 切换删除状态
                current_action = group.get_action(item_index)
                if current_action == "delete":
                    group.set_action(item_index, "none")
                else:
                    group.set_action(item_index, "delete")
                
                # 刷新显示
                self._display_group_items(group_row)