"""
LeafView 应用程序入口模块

实现单实例应用程序模式，确保同一时间只有一个应用实例运行。
使用共享内存和本地服务器进行进程间通信。

主要功能：
1. 单实例检测：防止应用重复启动
2. 进程间通信：通过本地Socket实现实例间通信
3. 窗口激活：将已运行的实例窗口置前显示
"""

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from contextlib import closing
from MainWindow import MainWindow
import sys

# 应用标识常量
APP_SERVER_NAME = "LeafView_Server"      # 本地服务器名称
SHARED_MEMORY_KEY = "LeafView_SharedMemory"  # 共享内存键名
BRING_TO_FRONT_COMMAND = b'bringToFront'  # 窗口置前命令


def bring_existing_to_front():
    """
    尝试连接到已运行的应用程序实例并发送置前命令
    
    Returns:
        bool: 是否成功连接到现有实例
    """
    try:
        with closing(QLocalSocket()) as socket:
            socket.connectToServer(APP_SERVER_NAME)
            if socket.waitForConnected(500):  # 500ms超时
                socket.write(BRING_TO_FRONT_COMMAND)
                socket.waitForBytesWritten(1000)  # 等待写入完成
                return True
    except Exception as e:
        # 静默处理连接异常，通常是因为没有现有实例运行
        pass
    return False


def setup_local_server():
    """
    设置本地服务器用于进程间通信
    
    Returns:
        QLocalServer: 配置好的本地服务器实例，失败时返回None
    """
    server = QLocalServer()
    if not server.listen(APP_SERVER_NAME):
        print(f"警告: 无法启动本地服务器: {server.errorString()}")
        return None
    return server


def main():
    """
    应用程序主入口函数
    
    实现单实例应用模式：
    1. 检查是否已有实例运行
    2. 如果没有，创建主窗口并运行
    3. 如果已有，激活现有实例并退出
    """
    # 创建Qt应用实例
    app = QtWidgets.QApplication(sys.argv)
    
    # 检查共享内存，判断是否已有实例运行
    shared_memory = QtCore.QSharedMemory(SHARED_MEMORY_KEY)
    if shared_memory.attach():
        # 已有实例运行，尝试激活它
        if bring_existing_to_front():
            print("检测到已有LeafView实例运行，已将其置前")
        else:
            print("检测到已有LeafView实例运行，但无法激活")
        sys.exit(0)  # 正常退出
    
    # 创建共享内存，标记为新实例
    if not shared_memory.create(1):  # 1字节足够用于标识
        print(f"错误: 无法创建共享内存: {shared_memory.errorString()}")
        sys.exit(1)
    
    # 设置本地服务器用于进程间通信
    local_server = setup_local_server()
    if not local_server:
        print("错误: 本地服务器启动失败")
        sys.exit(1)
    
    def handle_new_connection():
        """处理新连接请求"""
        socket = local_server.nextPendingConnection()
        if socket:
            socket.readyRead.connect(lambda: handle_socket_data(socket))
    
    def handle_socket_data(socket):
        """处理socket接收到的数据"""
        try:
            data = socket.readAll().data()
            if data == BRING_TO_FRONT_COMMAND:
                # 激活窗口并置前
                window.activateWindow()
                window.raise_()
                window.showNormal()
        finally:
            socket.deleteLater()  # 确保资源清理
    
    # 连接新连接信号
    local_server.newConnection.connect(handle_new_connection)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.move(300, 100)  # 初始位置偏移，避免完全重叠
    window.show()
    
    # 添加启动警告日志
    window.log("WARNING", "文件整理、重命名和属性写入操作一旦执行就无法撤销，请务必备份原数据")
    
    # 进入主事件循环
    exit_code = app.exec()
    
    # 清理资源
    if shared_memory.isAttached():
        shared_memory.detach()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
