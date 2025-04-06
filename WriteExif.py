from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget


class WriteExif(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.star_buttons = []
        self.selected_star = 0
        self.init_page()

    def init_page(self):
        for i in range(1, 6):
            button = getattr(self.parent, f'pushButton_star_{i}')
            button.setStyleSheet("QPushButton {image: url(resources/img/page_4/星级_暗.svg);}")
            button.enterEvent = lambda event, index=i: self.highlight_stars(index)
            button.leaveEvent = lambda event: self.highlight_stars(self.selected_star)
            button.clicked.connect(lambda checked, index=i: self.set_selected_star(index))
            self.star_buttons.append(button)

    @pyqtSlot(int)
    def highlight_stars(self, to_star):
        for i, button in enumerate(self.star_buttons, start=1):
            if i <= to_star:
                button.setStyleSheet("QPushButton {image: url(resources/img/page_4/星级_亮.svg);}")
            else:
                button.setStyleSheet("QPushButton {image: url(resources/img/page_4/星级_暗.svg);}")

    @pyqtSlot()
    def set_selected_star(self, star):
        self.selected_star = star
        self.highlight_stars(star)
