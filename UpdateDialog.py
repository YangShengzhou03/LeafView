import requests
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import Qt, QUrl
from bs4 import BeautifulSoup
from UI_UpdateDialog import Ui_UpdateDialog


class UpdateDialog(QDialog):
    def __init__(self, url, title, content, necessary=False):
        super().__init__()
        self.ui = Ui_UpdateDialog()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.ui.label_title.setText(title)
        self.ui.label_content.setText(content)
        if necessary:
            self.ui.pushButton_cancel.hide()
        self.ui.pushButton_download.clicked.connect(
            lambda: (QDesktopServices.openUrl(QUrl(url)), QApplication.instance().quit()))


def check_update():
    url = 'https://www.cnblogs.com/YangShengzhou/p/18679899'
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title_element = soup.find('a', class_='postTitle2')
        post_body = soup.find('div', class_='postBody')
        if not title_element or not post_body:
            raise ValueError("服务器异常")
        title_parts = title_element.text.strip().split('==', 2)
        content_parts = post_body.get_text().strip().split('==', 1)
        if len(title_parts) == 3:
            latest_version_str, update_link = title_parts[1:]
            update_content = content_parts[0]
            lastlyVersion = float(latest_version_str.strip())
            lastlyVersionUrl = update_link.strip()
            current_version = 1.2
            if lastlyVersion > current_version:
                necessary = lastlyVersion != current_version
                dialog = UpdateDialog(lastlyVersionUrl, title_parts[0], update_content, necessary)
                dialog.exec()
    except Exception:
        error_message = f"网络连接失败"
        dialog = UpdateDialog('https://blog.csdn.net/Yang_shengzhou', '网络连接失败',
                              '软件内测,须连网启动,感谢您的理解\n' + error_message, True)
        dialog.exec()
