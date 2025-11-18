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
        
        # Performance optimization: Initialize components lazily
        self._lazy_init_components = {}
        self._component_initializers = {
            'folder_page': lambda: FolderPage(self),
            'classification': lambda: SmartArrange(self, self.folder_page),
            'contrast': lambda: Contrast(self, self.folder_page),
            'write_exif': lambda: WriteExif(self, self.folder_page),
            'text_recognition': lambda: TextRecognition(self, self.folder_page)
        }

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
        
        # Create missing folder management components
        self._create_folder_management_components()
        
        # Create component mappings for SmartArrange
        self._create_smart_arrange_component_mappings()

        # Performance optimization: Defer component initialization
        # Components will be initialized on first use
    
    def _get_lazy_component(self, component_name):
        """Get a component, initializing it lazily if needed"""
        if component_name not in self._lazy_init_components:
            if component_name in self._component_initializers:
                self._lazy_init_components[component_name] = self._component_initializers[component_name]()
        return self._lazy_init_components.get(component_name)
    
    @property
    def folder_page(self):
        return self._get_lazy_component('folder_page')
    
    @property
    def classification(self):
        return self._get_lazy_component('classification')
    
    @property
    def contrast(self):
        return self._get_lazy_component('contrast')
    
    @property
    def write_exif(self):
        return self._get_lazy_component('write_exif')
    
    @property
    def text_recognition(self):
        return self._get_lazy_component('text_recognition')

    def _connect_buttons(self):
        self.btn_close.clicked.connect(self.close)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        self.btn_minimize.clicked.connect(self.showMinimized)
        
        self.btn_service.clicked.connect(self.feedback)
        self.btn_settings.clicked.connect(author)
        self.widget_vip_badge_container.mousePressEvent = self._on_head_vip_clicked

    def _on_head_vip_clicked(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            QtWidgets.QMessageBox.information(self, "demo版", "当前为演示版本，服务可能随时终止。\n\n如果您需要继续使用，请考虑购买专业版。")
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
    
    def _create_folder_management_components(self):
        """Create missing folder management UI components with lazy initialization"""
        # Create scroll area for folder management (should be in media import page)
        self.scrollArea_folds = QtWidgets.QScrollArea(self.page_mediaImport)
        self.scrollArea_folds.setWidgetResizable(True)
        self.scrollArea_folds.setObjectName("scrollArea_folds")
        
        # Create widget contents for the scroll area
        self.scrollAreaWidgetContents_folds = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_folds.setObjectName("scrollAreaWidgetContents_folds")
        
        # Create grid layout for folder items
        self.gridLayout_6 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents_folds)
        self.gridLayout_6.setObjectName("gridLayout_6")
        
        # Set the widget contents to the scroll area
        self.scrollArea_folds.setWidget(self.scrollAreaWidgetContents_folds)
        
        # Create add folder widget and button
        self.widget_add_folder = QtWidgets.QWidget(self.page_mediaImport)
        self.widget_add_folder.setObjectName("widget_add_folder")
        
        self.pushButton_add_folder = QtWidgets.QPushButton(self.page_mediaImport)
        self.pushButton_add_folder.setObjectName("pushButton_add_folder")
        
        # Add the scroll area to the media import page layout
        self.layout_media_import_content.addWidget(self.scrollArea_folds)
        
        # Performance optimization: Hide initially to reduce initial rendering load
        self.scrollArea_folds.hide()
        
    def _create_smart_arrange_component_mappings(self):
        """Create mappings for SmartArrange components with different naming conventions"""
        # Map the expected component names to the actual UI components
        if hasattr(self, 'btn_tag_original'):
            self.pushButton_original_tag = self.btn_tag_original
        if hasattr(self, 'btn_tag_year'):
            self.pushButton_year_tag = self.btn_tag_year
        if hasattr(self, 'btn_tag_month'):
            self.pushButton_month_tag = self.btn_tag_month
        if hasattr(self, 'btn_tag_date'):
            self.pushButton_date_tag = self.btn_tag_date
        if hasattr(self, 'btn_tag_day'):
            self.pushButton_day_tag = self.btn_tag_day
        if hasattr(self, 'btn_tag_time'):
            self.pushButton_time_tag = self.btn_tag_time
        if hasattr(self, 'btn_tag_brand'):
            self.pushButton_make_tag = self.btn_tag_brand
        if hasattr(self, 'btn_tag_model'):
            self.pushButton_model_tag = self.btn_tag_model
        if hasattr(self, 'btn_tag_location'):
            self.pushButton_address_tag = self.btn_tag_location
        if hasattr(self, 'btn_tag_customize'):
            self.pushButton_customize_tag = self.btn_tag_customize
            
        # Map layout components
        if hasattr(self, 'layout_rename_tags'):
            self.layout_rename_tags = self.layout_rename_tags
        if hasattr(self, 'layout_rename_selected'):
            # This layout might not exist, create it if needed
            pass
            
        # Create missing layout_rename_selected if it doesn't exist
        if not hasattr(self, 'layout_rename_selected'):
            self.layout_rename_selected = QtWidgets.QHBoxLayout()
            self.layout_rename_selected.setObjectName("layout_rename_selected")
            
        # Map combo boxes
        for i in range(1, 5):  # Only 4 combo boxes exist in UI (primary, secondary, tertiary, quaternary)
            combo_name = f'combo_classification_level_{["primary", "secondary", "tertiary", "quaternary"][i-1]}'
            expected_name = f'comboBox_level_{i}'
            if hasattr(self, combo_name):
                setattr(self, expected_name, getattr(self, combo_name))
                
        # Create comboBox_level_5 if it doesn't exist (SmartArrange expects 5)
        if not hasattr(self, 'comboBox_level_5'):
            self.comboBox_level_5 = QtWidgets.QComboBox()
            self.comboBox_level_5.addItems(["不分类", "年份", "月份", "日期", "位置", "品牌", "型号"])
            self.comboBox_level_5.setObjectName("comboBox_level_5")
                
        # Map other components
        if hasattr(self, 'btn_start_smart_arrange'):
            self.toolButton_startSmartArrange = self.btn_start_smart_arrange
        if hasattr(self, 'progressBar_smartArrange'):
            self.progressBar_classification = self.progressBar_smartArrange
            
        # Map combo boxes with different naming
        if hasattr(self, 'combo_operation_type'):
            self.comboBox_operation = self.combo_operation_type
        if hasattr(self, 'combo_separator'):
            self.comboBox_separator = self.combo_separator
            
        # Create missing components if they don't exist
        if not hasattr(self, 'comboBox_operation'):
            self.comboBox_operation = QtWidgets.QComboBox()
            self.comboBox_operation.addItems(["移动文件", "复制文件"])
            self.comboBox_operation.setObjectName("comboBox_operation")
            
        if not hasattr(self, 'comboBox_separator'):
            self.comboBox_separator = QtWidgets.QComboBox()
            self.comboBox_separator.addItems(["-", "无", "空格", "_", ".", ",", "|", "~"])
            self.comboBox_separator.setObjectName("comboBox_separator")
            
        if not hasattr(self, 'label_CopyRoute'):
            self.label_CopyRoute = QtWidgets.QLabel("移动文件（默认操作）")
            self.label_CopyRoute.setObjectName("label_CopyRoute")
            
        if not hasattr(self, 'comboBox_timeSource'):
            self.comboBox_timeSource = QtWidgets.QComboBox()
            self.comboBox_timeSource.addItems(["EXIF时间", "文件修改时间", "文件创建时间"])
            self.comboBox_timeSource.setObjectName("comboBox_timeSource")
            
        # Create missing preview components
        if not hasattr(self, 'label_PreviewRoute'):
            self.label_PreviewRoute = QtWidgets.QLabel("")
            self.label_PreviewRoute.setObjectName("label_PreviewRoute")
        if not hasattr(self, 'label_PreviewName'):
            self.label_PreviewName = QtWidgets.QLabel("")
            self.label_PreviewName.setObjectName("label_PreviewName")

        # Create WriteExif star rating buttons if missing
        for i in range(1, 6):
            btn_name = f'pushButton_star_{i}'
            if not hasattr(self, btn_name):
                btn = QtWidgets.QPushButton()
                btn.setObjectName(btn_name)
                setattr(self, btn_name, btn)
        
        # Create WriteExif combo boxes if missing
        if not hasattr(self, 'comboBox_brand'):
            self.comboBox_brand = QtWidgets.QComboBox()
            self.comboBox_brand.setObjectName("comboBox_brand")
        
        if not hasattr(self, 'comboBox_model'):
            self.comboBox_model = QtWidgets.QComboBox()
            self.comboBox_model.setObjectName("comboBox_model")
        
        if not hasattr(self, 'comboBox_shootTime'):
            self.comboBox_shootTime = QtWidgets.QComboBox()
            self.comboBox_shootTime.addItems(["无", "当前时间", "自定义时间"])
            self.comboBox_shootTime.setObjectName("comboBox_shootTime")
        
        if not hasattr(self, 'comboBox_location'):
            self.comboBox_location = QtWidgets.QComboBox()
            self.comboBox_location.addItems(["无", "当前位置", "自定义位置"])
            self.comboBox_location.setObjectName("comboBox_location")
        
        if not hasattr(self, 'dateTimeEdit_shootTime'):
            self.dateTimeEdit_shootTime = QtWidgets.QDateTimeEdit()
            self.dateTimeEdit_shootTime.setObjectName("dateTimeEdit_shootTime")
        
        if not hasattr(self, 'lineEdit_EXIF_Title'):
            self.lineEdit_EXIF_Title = QtWidgets.QLineEdit()
            self.lineEdit_EXIF_Title.setObjectName("lineEdit_EXIF_Title")
        
        if not hasattr(self, 'lineEdit_EXIF_Author'):
            self.lineEdit_EXIF_Author = QtWidgets.QLineEdit()
            self.lineEdit_EXIF_Author.setObjectName("lineEdit_EXIF_Author")
        
        if not hasattr(self, 'lineEdit_EXIF_Theme'):
            self.lineEdit_EXIF_Theme = QtWidgets.QLineEdit()
            self.lineEdit_EXIF_Theme.setObjectName("lineEdit_EXIF_Theme")
        
        if not hasattr(self, 'lineEdit_EXIF_Copyright'):
            self.lineEdit_EXIF_Copyright = QtWidgets.QLineEdit()
            self.lineEdit_EXIF_Copyright.setObjectName("lineEdit_EXIF_Copyright")
        
        if not hasattr(self, 'lineEdit_EXIF_Position'):
            self.lineEdit_EXIF_Position = QtWidgets.QLineEdit()
            self.lineEdit_EXIF_Position.setObjectName("lineEdit_EXIF_Position")
        
        if not hasattr(self, 'lineEdit_EXIF_latitude'):
            self.lineEdit_EXIF_latitude = QtWidgets.QLineEdit()
            self.lineEdit_EXIF_latitude.setObjectName("lineEdit_EXIF_latitude")
        
        if not hasattr(self, 'lineEdit_EXIF_longitude'):
            self.lineEdit_EXIF_longitude = QtWidgets.QLineEdit()
            self.lineEdit_EXIF_longitude.setObjectName("lineEdit_EXIF_longitude")
        
        if not hasattr(self, 'toolButton_StartEXIF'):
            self.toolButton_StartEXIF = QtWidgets.QToolButton()
            self.toolButton_StartEXIF.setText("开始")
            self.toolButton_StartEXIF.setObjectName("toolButton_StartEXIF")
        
        if not hasattr(self, 'pushButton_Position'):
            self.pushButton_Position = QtWidgets.QPushButton()
            self.pushButton_Position.setText("获取位置")
            self.pushButton_Position.setObjectName("pushButton_Position")
        
        if not hasattr(self, 'horizontalFrame'):
            self.horizontalFrame = QtWidgets.QFrame()
            self.horizontalFrame.setObjectName("horizontalFrame")
        
        if not hasattr(self, 'progressBar_EXIF'):
            self.progressBar_EXIF = QtWidgets.QProgressBar()
            self.progressBar_EXIF.setObjectName("progressBar_EXIF")

        # Create Contrast-related components if missing
        if not hasattr(self, 'horizontalSlider_levelContrast'):
            self.horizontalSlider_levelContrast = QtWidgets.QSlider()
            self.horizontalSlider_levelContrast.setOrientation(QtCore.Qt.Orientation.Horizontal)
            self.horizontalSlider_levelContrast.setObjectName("horizontalSlider_levelContrast")
        
        if not hasattr(self, 'label_levelContrast'):
            self.label_levelContrast = QtWidgets.QLabel("完全一致 (100%)")
            self.label_levelContrast.setObjectName("label_levelContrast")
        
        if not hasattr(self, 'toolButton_startContrast'):
            self.toolButton_startContrast = QtWidgets.QToolButton()
            self.toolButton_startContrast.setText("开始对比")
            self.toolButton_startContrast.setObjectName("toolButton_startContrast")
        
        if not hasattr(self, 'progressBar_Contrast'):
            self.progressBar_Contrast = QtWidgets.QProgressBar()
            self.progressBar_Contrast.setObjectName("progressBar_Contrast")
        
        if not hasattr(self, 'layout_contrast_images'):
            self.layout_contrast_images = QtWidgets.QVBoxLayout()
            self.layout_contrast_images.setObjectName("layout_contrast_images")
        
        if not hasattr(self, 'verticalFrame_similar'):
            self.verticalFrame_similar = QtWidgets.QFrame()
            self.verticalFrame_similar.setObjectName("verticalFrame_similar")
        
        # Map toolButton_move, toolButton_autoSelect, toolButton_delete for Contrast
        if not hasattr(self, 'toolButton_move'):
            self.toolButton_move = QtWidgets.QToolButton()
            self.toolButton_move.setText("移动选中")
            self.toolButton_move.setObjectName("toolButton_move")
        
        if not hasattr(self, 'toolButton_autoSelect'):
            self.toolButton_autoSelect = QtWidgets.QToolButton()
            self.toolButton_autoSelect.setText("自动选择")
            self.toolButton_autoSelect.setObjectName("toolButton_autoSelect")
        
        if not hasattr(self, 'toolButton_delete'):
            self.toolButton_delete = QtWidgets.QToolButton()
            self.toolButton_delete.setText("删除选中")
            self.toolButton_delete.setObjectName("toolButton_delete")
        
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
