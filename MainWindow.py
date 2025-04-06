from PyQt6 import QtWidgets, QtCore, QtGui

from Classification import Classification
from Contrast import Contrast
from FolderPage import FolderPage
from Ui_MainWindow import Ui_MainWindow
from UpdateDialog import check_update
from WriteExif import WriteExif
from common import get_resource_path


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self._init_window()
        check_update()
        self._setup_drag_handlers()

    def _init_window(self):
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self._connect_buttons()
        self.empty_widgets = {}
        self.empty_widgets['gridLayout_5'] = self._create_empty_widget(self.gridLayout_5)
        self.empty_widgets['gridLayout_4'] = self._create_empty_widget(self.gridLayout_4)
        self.empty_widgets['gridLayout_3'] = self._create_empty_widget(self.gridLayout_3)
        self.empty_widgets['gridLayout_7'] = self._create_empty_widget(self.gridLayout_7)
        self.empty_widgets['gridLayout_6'] = self._create_empty_widget(self.gridLayout_6)
        self.folder_page = FolderPage(self)
        self.contrast_page = Contrast(self)
        self.writeExif_page = WriteExif(self)
        self.classification_page = Classification(self, self.folder_page)

    def _connect_buttons(self):
        self.toolButton_close.clicked.connect(self.close)
        self.toolButton_maximum.clicked.connect(self._toggle_maximize)
        self.toolButton_minimum.clicked.connect(self.showMinimized)

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
        icon = '还原.svg' if is_max else '最大化.svg'
        self.toolButton_maximum.setIcon(QtGui.QIcon(get_resource_path(f'resources/img/窗口控制/{icon}')))

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
        if layout_name in self.empty_widgets:
            widget = self.empty_widgets[layout_name]
            widget.setVisible(not has_content)
