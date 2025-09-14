from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from contextlib import closing
from MainWindow import MainWindow
import sys


def bring_existing_to_front():
    try:
        with closing(QLocalSocket()) as socket:
            socket.connectToServer("LeafView_Server")
            if socket.waitForConnected(500):
                socket.write(b'bringToFront')
                socket.waitForBytesWritten(1000)
    except Exception:
        pass


def main():
    app = QtWidgets.QApplication(sys.argv)
    shared_memory = QtCore.QSharedMemory("LeafView_SharedMemory")
    if shared_memory.attach():
        bring_existing_to_front()
        sys.exit()
    if not shared_memory.create(1):
        sys.exit()
    local_server = QLocalServer()
    if not local_server.listen("LeafView_Server"):
        sys.exit()

    def new_connection():
        socket = local_server.nextPendingConnection()
        socket.readyRead.connect(lambda: handle_ready_read(socket))

    def handle_ready_read(socket):
        data = socket.readAll().data()
        if data == b'bringToFront':
            window.activateWindow()
            window.raise_()
            window.showNormal()
        socket.deleteLater()

    local_server.newConnection.connect(new_connection)
    window = MainWindow()
    window.move(300, 100)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
