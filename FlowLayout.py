from PyQt6 import QtWidgets, QtCore, QtGui


class FlowLayout(QtWidgets.QLayout):
    selectionChanged = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.h_space, self.v_space = 10, 10
        self.item_list = []
        self.selected_items = set()
        self.drag_selection_rect = None
        self.drag_start_pos = None
        self.last_clicked_item = None

    def addItem(self, item):
        self.item_list.append(item)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            self.drag_selection_rect = QtCore.QRect(self.drag_start_pos, QtCore.QSize())
            self.last_clicked_item = None
            for item in self.item_list:
                widget = item.widget()
                if widget.geometry().contains(event.pos()):
                    self.last_clicked_item = item
                    break
            self.update()

    def mouseMoveEvent(self, event):
        if self.drag_start_pos is not None:
            rect_top_left = QtCore.QPoint(
                min(self.drag_start_pos.x(), event.pos().x()),
                min(self.drag_start_pos.y(), event.pos().y())
            )
            rect_bottom_right = QtCore.QPoint(
                max(self.drag_start_pos.x(), event.pos().x()),
                max(self.drag_start_pos.y(), event.pos().y())
            )
            self.drag_selection_rect = QtCore.QRect(rect_top_left, rect_bottom_right)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.drag_selection_rect is not None:
            new_selection = set()
            for item in self.item_list:
                widget = item.widget()
                if self.drag_selection_rect.intersects(widget.geometry()):
                    new_selection.add(item)
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                for item in new_selection:
                    if item in self.selected_items:
                        self.selected_items.remove(item)
                    else:
                        self.selected_items.add(item)
            elif event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier and self.last_clicked_item:
                start_index = self.indexOf(self.last_clicked_item)
                end_index = self.indexOf(self.findItemByWidgetUnderMouse(event))
                start, end = sorted([start_index, end_index])
                for index in range(start, end + 1):
                    item = self.itemAt(index)
                    if item:
                        self.selected_items.add(item)
            else:
                self.selected_items = new_selection
            self.drag_selection_rect = None
            self.drag_start_pos = None
            self.selectionChanged.emit([i.widget() for i in self.selected_items])
            self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self.parentWidget())
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.DotLine)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        if self.drag_selection_rect:
            painter.drawRect(self.drag_selection_rect.normalized())

        painter.setPen(QtCore.Qt.PenStyle.SolidLine)
        for item in self.selected_items:
            widget = item.widget()
            painter.setBrush(QtGui.QColor(0, 128, 255, 64))
            painter.drawRect(widget.geometry())

    def findItemByWidgetUnderMouse(self, event):
        for item in self.item_list:
            widget = item.widget()
            if widget.geometry().contains(event.pos()):
                return item
        return None

    def selectAll(self, select=True):
        if select:
            self.selected_items.update(self.item_list)
        else:
            self.selected_items.clear()
        self.selectionChanged.emit([i.widget() for i in self.selected_items])
        self.update()

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        return self.item_list[index] if 0 <= index < len(self.item_list) else None

    def takeAt(self, index):
        return self.item_list.pop(index) if 0 <= index < len(self.item_list) else None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.do_layout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins().left()
        size += QtCore.QSize(2 * margin, 2 * margin)
        return size

    def do_layout(self, rect, test_only=False):
        x, y = rect.x(), rect.y()
        line_height = 0
        current_line_items = []

        for item in self.item_list:
            item.widget()
            space_x = self.h_space if self.h_space >= 0 else self.spacing()
            space_y = self.v_space if self.v_space >= 0 else self.spacing()
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                self.apply_distributed_alignment(current_line_items, rect, y, test_only)
                current_line_items.clear()
                x, y = rect.x(), y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            current_line_items.append(item)
            if not test_only:
                item.setGeometry(QtCore.QRect(int(x), int(y), item.sizeHint().width(), item.sizeHint().height()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        self.apply_distributed_alignment(current_line_items, rect, y, test_only)
        return y + line_height - rect.y()

    def apply_distributed_alignment(self, items_in_line, rect, y, test_only):
        if not items_in_line:
            return

        total_width = sum(item.sizeHint().width() for item in items_in_line)
        free_space = rect.width() - total_width - (len(items_in_line) - 1) * self.h_space
        extra_space = free_space / (len(items_in_line) - 1) if len(items_in_line) > 1 else 0
        current_x = rect.x()

        for item in items_in_line:
            if not test_only:
                new_geometry = QtCore.QRect(int(current_x), int(y), item.sizeHint().width(), item.sizeHint().height())
                item.setGeometry(new_geometry)
            current_x += item.sizeHint().width() + self.h_space + extra_space

    def indexOf(self, item):
        return self.item_list.index(item) if item in self.item_list else -1
