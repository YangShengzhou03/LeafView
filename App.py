from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from contextlib import closing
from MainWindow import MainWindow
import sys

APP_SERVER_NAME = "LeafView_Server"
SHARED_MEMORY_KEY = "LeafView_SharedMemory"
BRING_TO_FRONT_COMMAND = b'bringToFront'


def bring_existing_to_front():
    try:
        with closing(QLocalSocket()) as socket:
            socket.connectToServer(APP_SERVER_NAME)
            if socket.waitForConnected(500):
                socket.write(BRING_TO_FRONT_COMMAND)
                socket.waitForBytesWritten(1000)
                return True
    except Exception as e:
        pass
    return False


def setup_local_server():
    server = QLocalServer()
    if not server.listen(APP_SERVER_NAME):
        return None
    return server


def main():
    app = QtWidgets.QApplication(sys.argv)
    
    shared_memory = QtCore.QSharedMemory(SHARED_MEMORY_KEY)
    if shared_memory.attach():
        if bring_existing_to_front():
            pass
        sys.exit(0)
    
    if not shared_memory.create(1):
        sys.exit(1)
    
    local_server = setup_local_server()
    if not local_server:
        sys.exit(1)
    
    def handle_new_connection():
        socket = local_server.nextPendingConnection()
        if socket:
            socket.readyRead.connect(lambda: handle_socket_data(socket))
    
    def handle_socket_data(socket):
        try:
            data = socket.readAll().data()
            if data == BRING_TO_FRONT_COMMAND:
                window.activateWindow()
                window.raise_()
                window.showNormal()
        finally:
            socket.deleteLater()
    
    local_server.newConnection.connect(handle_new_connection)
    
    window = MainWindow()
    window.move(300, 100)
    window.show()
    
    window.log("WARNING", "文件整理、重命名和属性写入等操作一旦执行无法恢复，操作前请务必备份好原数据。")
    
    exit_code = app.exec()
    
    if shared_memory.isAttached():
        shared_memory.detach()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
