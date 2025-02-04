from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QTimer

from Arrange import Arrange
from Convert import Convert
from FlowLayout import FlowLayout
from HomePage import HomePage
from ItemWidget import ItemWidget
from MediaPage import MediaPage
from RemoveRepeat import RemoveRepeat
from Rename import Rename
from Ui_MainWindow import Ui_MainWindow
from UpdateDialog import check_update
from WriteEXIF import WriteEXIF
from common import author, get_resource_path


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.home_page = HomePage(self)
        self.media_page = MediaPage(self)
        self.item_widget = ItemWidget(self)
        self.arrange_page = Arrange(self)
        self.rename_page = Rename(self)
        self.repeat_page = RemoveRepeat(self)
        self.convert_page = Convert(self)
        self.writeExif_page = WriteEXIF(self)
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        self.classified_threads = []
        self.all_classified_items = []
        self.classification_buffer = []
        self.imported_folders = []
        self.item_selection_state = {}
        self.refresh_counter = 0
        self.connect_signal()
        self.flow_container()
        self.widget_import.setVisible(True)
        self.toolButton_saveAs.setVisible(False)
        if self.listWidget_base.count() > 0:
            self.listWidget_base.setCurrentRow(0)
        elif self.listWidget_process.count() > 0:
            self.listWidget_process.setCurrentRow(0)
        self.update_empty_state_visibility(self.flow_layout_imported_folders, self.empty_label_imported_folders)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.mousePosition = None
        self.frame_head.mousePressEvent = self._frame_head_mouse_press_event
        self.frame_head.mouseMoveEvent = self._frame_head_mouse_move_event
        self.frame_head.mouseReleaseEvent = self._frame_head_mouse_release_event
        self.setAcceptDrops(True)
        check_update()

    def _frame_head_mouse_press_event(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.mousePosition = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def _frame_head_mouse_move_event(self, event):
        if self.mousePosition is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.mousePosition)
            event.accept()

    def _frame_head_mouse_release_event(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.mousePosition = None
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()

    def connect_signal(self):
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.dynamic_process_classification_buffer)
        self.listWidget_base.currentRowChanged.connect(self.on_base_list_row_changed)
        self.listWidget_process.currentRowChanged.connect(self.on_process_list_row_changed)

        self.toolButton_close.clicked.connect(self.head_close)
        self.toolButton_maximum.clicked.connect(self.toggle_maximize_restore)
        self.toolButton_minimum.clicked.connect(self.minimize_window)
        self.toolButton_setting.clicked.connect(author)
        self.toolButton_service.clicked.connect(author)

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.resize(1375, 768)
            self.toolButton_maximum.setIcon(QtGui.QIcon(get_resource_path(
                'resources/img/窗口控制/最大化.svg')))
        else:
            self.showMaximized()
            self.toolButton_maximum.setIcon(QtGui.QIcon(get_resource_path('resources/img/窗口控制/还原.svg')))

    def minimize_window(self):
        self.showMinimized()

    def head_close(self):
        QtWidgets.QApplication.quit()

    def flow_container(self):
        self.flow_container_recommend = QtWidgets.QWidget(parent=self.widget_recommend)
        self.flow_layout_recommend = FlowLayout(self.flow_container_recommend)
        self.flow_container_recommend.setLayout(self.flow_layout_recommend)
        self.verticalLayout_12.addWidget(self.flow_container_recommend)

        self.flow_container_img = QtWidgets.QWidget(parent=self.widget_img)
        self.flow_layout_img = FlowLayout(self.flow_container_img)
        self.flow_container_img.setLayout(self.flow_layout_img)
        self.verticalLayout_23.addWidget(self.flow_container_img)

        self.flow_container_video = QtWidgets.QWidget(parent=self.widget_video)
        self.flow_layout_video = FlowLayout(self.flow_container_video)
        self.flow_container_video.setLayout(self.flow_layout_video)
        self.verticalLayout_13.addWidget(self.flow_container_video)

        self.flow_container_screen = QtWidgets.QWidget(parent=self.widget_screen)
        self.flow_layout_screen = FlowLayout(self.flow_container_screen)
        self.flow_container_screen.setLayout(self.flow_layout_screen)
        self.verticalLayout_21.addWidget(self.flow_container_screen)

        self.flow_container_landscape = QtWidgets.QWidget(parent=self.widget_landscape)
        self.flow_layout_landscape = FlowLayout(self.flow_container_landscape)
        self.flow_container_landscape.setLayout(self.flow_layout_landscape)
        self.verticalLayout_22.addWidget(self.flow_container_landscape)

        self.flow_container_people = QtWidgets.QWidget(parent=self.widget_people)
        self.flow_layout_people = FlowLayout(self.flow_container_people)
        self.flow_container_people.setLayout(self.flow_layout_people)
        self.verticalLayout_10.addWidget(self.flow_container_people)

        self.flow_container_imported_folders = QtWidgets.QWidget(parent=self.widget_Imported_folder)
        self.flow_layout_imported_folders = FlowLayout(self.flow_container_imported_folders)
        self.flow_container_imported_folders.setLayout(self.flow_layout_imported_folders)
        self.verticalLayout_33.addWidget(self.flow_container_imported_folders)

        self.empty_label_img = self.create_empty_label("暂无图片", parent=self.widget_img, font_size=18)
        self.verticalLayout_23.addWidget(self.empty_label_img)

        self.empty_label_video = self.create_empty_label("暂无视频", parent=self.widget_video, font_size=18)
        self.verticalLayout_13.addWidget(self.empty_label_video)

        self.empty_label_screen = self.create_empty_label("暂无截图", parent=self.widget_screen, font_size=18)
        self.verticalLayout_21.addWidget(self.empty_label_screen)

        self.empty_label_landscape = self.create_empty_label("暂无风景", parent=self.widget_landscape, font_size=18)
        self.verticalLayout_22.addWidget(self.empty_label_landscape)

        self.empty_label_people = self.create_empty_label("暂无人像", parent=self.widget_people, font_size=18)
        self.verticalLayout_10.addWidget(self.empty_label_people)

        self.empty_label_imported_folders = self.create_empty_label("还没有导入文件夹", parent=self.widget_Imported_folder, font_size=18)
        self.verticalLayout_33.addWidget(self.empty_label_imported_folders)

        for flow_layout in [self.flow_layout_recommend, self.flow_layout_img, self.flow_layout_video, self.flow_layout_screen, self.flow_layout_landscape, self.flow_layout_people]:
            empty_label = None
            if flow_layout == self.flow_layout_recommend:
                empty_label = self.widget_import
            elif flow_layout == self.flow_layout_img:
                empty_label = self.empty_label_img
            elif flow_layout == self.flow_layout_video:
                empty_label = self.empty_label_video
            elif flow_layout == self.flow_layout_screen:
                empty_label = self.empty_label_screen
            elif flow_layout == self.flow_layout_landscape:
                empty_label = self.empty_label_landscape
            elif flow_layout == self.flow_layout_people:
                empty_label = self.empty_label_people

            self.update_empty_state_visibility(flow_layout, empty_label)

    def on_delete_clicked(self, folder_path):
        for widget_id, state in list(self.item_selection_state.items()):
            if state['folder_path'] == folder_path:
                widget_to_remove = [w for w in self.findChildren(QtWidgets.QWidget) if id(w) == widget_id][0]
                widget_to_remove.setParent(None)
                del self.item_selection_state[widget_id]
                layout = self.flow_container_imported_folders.layout()
                if layout:
                    layout.update()
                break
        if folder_path in self.imported_folders:
            self.imported_folders.remove(folder_path)
        self.home_page.update_recommend_page(clear_existing=True)
        self.update_empty_state_visibility(self.flow_layout_imported_folders, self.empty_label_imported_folders)
        self.set_folder_names_to_arrange()

    def update_empty_state_visibility(self, flow_layout, widget=None):
        if widget:
            widget.setVisible(flow_layout.count() == 0)

    def on_item_classified(self, item_path, file_name, classifications):
        item_dict = {
            'path': item_path,
            'name': file_name,
            'classifications': classifications
        }
        self.classification_buffer.append(item_dict)

    def dynamic_process_classification_buffer(self):
        if not self.classification_buffer:
            return
        items_to_process, self.classification_buffer = self.classification_buffer.copy(), []
        for item in items_to_process:
            self._process_single_item(item['path'], item['name'], item['classifications'])
        self.refresh_counter += 1
        if (self.refresh_counter == 1 or
                (self.refresh_counter & (self.refresh_counter - 1) == 0 and
                 ((self.refresh_counter & 0b111) == 0))):
            self.repaint()
        if self.refresh_counter > 512:
            self.refresh_counter = 1

    def _process_single_item(self, item_path, file_name, classifications):
        if any(existing_item[0] == item_path for existing_item in self.all_classified_items):
            return

        container_map = {
            'screen': (self.flow_container_screen, self.flow_layout_screen, self.empty_label_screen),
            'landscape': (self.flow_container_landscape, self.flow_layout_landscape, self.empty_label_landscape),
            'people': (self.flow_container_people, self.flow_layout_people, self.empty_label_people),
            'video': (self.flow_container_video, self.flow_layout_video, self.empty_label_video)
        }
        for category in classifications:
            if category in container_map:
                container, flow_layout, empty_label = container_map[category]
                item_widget = (
                    self.item_widget.create_image_item(item_path, file_name, container)
                    if category != 'video'
                    else self.item_widget.create_video_item(item_path, file_name, container)
                )
                if item_widget:
                    flow_layout.addWidget(item_widget)
                    self.update_empty_state_visibility(flow_layout, empty_label)
        if 'video' not in classifications:
            item_widget = self.item_widget.create_image_item(item_path, file_name, self.flow_container_img)
            if item_widget:
                self.flow_layout_img.addWidget(item_widget)
                self.update_empty_state_visibility(self.flow_layout_img, self.empty_label_img)
        self.all_classified_items.append((item_path, file_name))

    def create_empty_label(self, text, parent, font_size=18):
        empty_label = QtWidgets.QLabel(text, parent=parent)
        empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet(f"font-size: {font_size}px;")
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        empty_label.setSizePolicy(size_policy)
        return empty_label

    def set_folder_names_to_arrange(self):
        if not self.imported_folders:
            placeholder_text = "暂未导入文件夹"
            self.label_organizeFolders.setText(placeholder_text)
            self.label_organizeFolders_2.setText(placeholder_text)
            self.label_organizeFolders_3.setText(placeholder_text)
            self.label_organizeFolders_4.setText(placeholder_text)
            self.label_organizeFolders_5.setText(placeholder_text)
            return
        folder_names = [folder.split('\\')[-1] for folder in self.imported_folders]
        folder_names_str = '、 '.join(folder_names)
        self.label_organizeFolders.setText(folder_names_str)
        self.label_organizeFolders_2.setText(folder_names_str)
        self.label_organizeFolders_3.setText(folder_names_str)
        self.label_organizeFolders_4.setText(folder_names_str)
        self.label_organizeFolders_5.setText(folder_names_str)

    def on_base_list_row_changed(self, current_row):
        if 0 <= current_row < 3:
            self.stackedWidget.setCurrentIndex(current_row)
            self.listWidget_process.clearSelection()
            self.listWidget_process.setCurrentRow(-1)

    def on_process_list_row_changed(self, current_row):
        if 0 <= current_row < 5:
            self.stackedWidget.setCurrentIndex(current_row + 3)
            self.listWidget_base.clearSelection()
            self.listWidget_base.setCurrentRow(-1)
