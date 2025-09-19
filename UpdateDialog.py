import requests
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QUrl
from bs4 import BeautifulSoup
from UI_UpdateDialog import Ui_UpdateDialog
from common import get_resource_path


class UpdateDialog(QDialog):
    def __init__(self, url, title, content, version="", necessary=False):
        super().__init__()
        self.ui = Ui_UpdateDialog()
        self.ui.setupUi(self)
        self.necessary = necessary
        self.setWindowTitle("枫叶通知")
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowCloseButtonHint, False)
        self.ui.label_title.setText(title)
        self.ui.label_content.setText(content)
        if necessary:
            self.ui.pushButton_cancel.hide()
            self.ui.pushButton_download.clicked.connect(self.force_quit)
        else:
            self.ui.pushButton_download.clicked.connect(
                lambda: (QDesktopServices.openUrl(QUrl(url)), self.force_quit()))
    
    def force_quit(self):
        import sys
        sys.exit(1)
    
    def closeEvent(self, event):
        if self.necessary:
            event.ignore()
        else:
            super().closeEvent(event)


def check_update():
    url = 'https://www.cnblogs.com/YangShengzhou/p/18679899'
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title_element = soup.find('a', class_='postTitle2')
        post_body = soup.find('div', class_='postBody')
        if not title_element or not post_body:
            raise ValueError("服务器出问题了")
        title_parts = title_element.text.strip().split('==', 2)
        content_parts = post_body.get_text().strip().split('==', 1)
        if len(title_parts) == 3:
            latest_version_str, update_link = title_parts[1:]
            update_content = content_parts[0]
            lastlyVersion = float(latest_version_str.strip())
            lastlyVersionUrl = update_link.strip()
            current_version = 1.3
            if lastlyVersion > current_version:
                necessary = lastlyVersion != current_version
                version_text = f"LeafView v{latest_version_str.strip()}"
                dialog = UpdateDialog(lastlyVersionUrl, title_parts[0], update_content, version_text, necessary)
                dialog.exec()
    except requests.exceptions.RequestException:
        error_message = "网络开了小差，枫叶未能如期而至。"
        dialog = UpdateDialog('https://blog.csdn.net/Yang_shengzhou', '网络连接失败',
                              '别担心，这只是一次小小的插曲，您的满意始终是我们的追求。\n\n' + error_message +
                              '\n\n请检查网络后重新启动，我们期待不久与您相遇。', "", True)
        dialog.ui.pushButton_download.setText("我知道了")
        dialog.exec()
    except Exception as e:
        error_message = f"检查更新时出错了: {str(e)}"
        dialog = UpdateDialog('https://blog.csdn.net/Yang_shengzhou', '检查更新失败',
                              '更新失败，但您的支持始终是我们前行的重要力量。未来可期，敬请放心，我们一直在努力。\n' + error_message, "", True)
        dialog.ui.pushButton_download.setText("我知道了")
        dialog.exec()