"""LeafView主应用程序模块

这个模块包含LeafView应用程序的入口点和主要逻辑。
"""

import sys
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from contextlib import closing
from pathlib import Path

# 导入应用程序组件
from .views.main_window import MainWindow
from .utils.config import Config
from .utils.logger import setup_logger


def bring_existing_to_front():
    """将已运行的实例置于前端"""
    try:
        with closing(QLocalSocket()) as socket:
            socket.connectToServer("LeafView_Server")
            if socket.waitForConnected(500):
                socket.write(b'bringToFront')
                socket.waitForBytesWritten(1000)
    except Exception as e:
        # 使用日志记录错误，而不是静默忽略
        logger = setup_logger()
        logger.error(f"无法连接到现有实例: {e}")


class LeafViewApp:
    """LeafView应用程序主类"""
    
    def __init__(self):
        """初始化应用程序"""
        # 初始化配置
        self.config = Config()
        
        # 设置日志
        self.logger = setup_logger()
        
        # 创建Qt应用程序
        self.app = QtWidgets.QApplication(sys.argv)
        
        # 设置应用程序信息
        self.app.setApplicationName("LeafView")
        self.app.setApplicationVersion("1.2.0")
        self.app.setOrganizationName("Yangshengzhou")
        
        # 确保单实例运行
        self._ensure_single_instance()
        
        # 创建主窗口
        self.main_window = MainWindow()
        
        # 设置本地服务器用于单实例通信
        self._setup_local_server()
    
    def _ensure_single_instance(self):
        """确保只有一个应用程序实例在运行"""
        self.shared_memory = QtCore.QSharedMemory("LeafView_SharedMemory")
        
        if self.shared_memory.attach():
            # 已有实例在运行
            bring_existing_to_front()
            sys.exit(0)
        
        if not self.shared_memory.create(1):
            self.logger.error("无法创建共享内存")
            sys.exit(1)
    
    def _setup_local_server(self):
        """设置本地服务器用于单实例通信"""
        self.local_server = QLocalServer()
        
        if not self.local_server.listen("LeafView_Server"):
            self.logger.error("无法启动本地服务器")
            sys.exit(1)
        
        # 连接新连接信号
        self.local_server.newConnection.connect(self._handle_new_connection)
    
    def _handle_new_connection(self):
        """处理新的本地服务器连接"""
        socket = self.local_server.nextPendingConnection()
        socket.readyRead.connect(lambda: self._handle_ready_read(socket))
    
    def _handle_ready_read(self, socket):
        """处理从其他实例接收到的数据"""
        data = socket.readAll().data()
        if data == b'bringToFront':
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.main_window.showNormal()
        socket.deleteLater()
    
    def run(self):
        """运行应用程序"""
        # 显示主窗口
        self.main_window.show()
        
        # 记录应用程序启动
        self.logger.info("LeafView应用程序已启动")
        
        # 运行事件循环
        sys.exit(self.app.exec())


def main():
    """应用程序入口点"""
    app = LeafViewApp()
    app.run()


if __name__ == '__main__':
    main()