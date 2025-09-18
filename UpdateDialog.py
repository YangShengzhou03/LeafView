import requests
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, QUrl
from bs4 import BeautifulSoup
from UI_UpdateDialog import Ui_UpdateDialog


class UpdateDialog(QDialog):
    def __init__(self, url, title, content, version="", necessary=False):
        super().__init__()
        self.ui = Ui_UpdateDialog()
        self.ui.setupUi(self)
        self.necessary = necessary
                # 设置无边框和透明背景以实现自定义窗口样式
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        # 禁用关闭按钮和窗口关闭功能
        self.setWindowFlag(QtCore.Qt.WindowType.WindowCloseButtonHint, False)
        self.ui.label_title.setText(title)
        self.ui.label_content.setText(content)
        # label_version 组件不存在，已移除相关代码
        if necessary:
            self.ui.pushButton_cancel.hide()
            # 对于强制退出的情况，点击按钮直接退出程序
            self.ui.pushButton_download.clicked.connect(self.force_quit)
        else:
            # 对于正常更新情况，保持原来的打开浏览器行为
            self.ui.pushButton_download.clicked.connect(
                lambda: (QDesktopServices.openUrl(QUrl(url)), self.force_quit()))
    
    def force_quit(self):
        """强制退出程序"""
        import sys
        sys.exit(1)
    
    def closeEvent(self, event):
        # 重写关闭事件，如果是强制退出模式，不允许关闭窗口
        if self.necessary:
            event.ignore()  # 忽略关闭事件
        else:
            super().closeEvent(event)


def check_update():
    """检查应用更新，网络连接失败时强制退出程序"""
    url = 'https://www.cnblogs.com/YangShengzhou/p/18679899'
    try:
        # Set a reasonable timeout for the request
        response = requests.get(url, timeout=5)
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
            current_version = 1.3
            if lastlyVersion > current_version:
                necessary = lastlyVersion != current_version
                version_text = f"LeafView v{latest_version_str.strip()}"
                dialog = UpdateDialog(lastlyVersionUrl, title_parts[0], update_content, version_text, necessary)
                dialog.exec()
    except requests.exceptions.RequestException:
        # Handle network connection errors - force quit on network failure
        error_message = "网络连接失败，无法检查更新"
        dialog = UpdateDialog('https://blog.csdn.net/Yang_shengzhou', '网络连接失败',
                              '枫叶内测版,须连网启动,感谢您的理解\n\n' + error_message + 
                              '\n\n程序将自动退出，请检查网络连接后重试。', "", True)
        # 修改按钮文字为"我知道了"
        dialog.ui.pushButton_download.setText("我知道了")
        dialog.exec()
    except Exception as e:
        # Handle other exceptions
        error_message = f"检查更新时发生错误: {str(e)}"
        dialog = UpdateDialog('https://blog.csdn.net/Yang_shengzhou', '更新检查失败',
                              '枫叶内测版,感谢您的理解\n' + error_message, "", True)
        # 修改按钮文字为"我知道了"
        dialog.ui.pushButton_download.setText("我知道了")
        dialog.exec()