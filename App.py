import sys

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalSocket, QLocalServer

from MainWindow import MainWindow

"""
pyinstaller App.spec
"""


def bring_existing_to_front():
    socket = QLocalSocket()
    socket.connectToServer("LeafView_Server")
    if socket.waitForConnected(500):
        socket.write(b'bringToFront')
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        socket.waitForDisconnected(1000)


def main():
    app = QtWidgets.QApplication(sys.argv)
    shared_memory = QtCore.QSharedMemory("LeafView_SharedMemory")

    if shared_memory.attach():
        bring_existing_to_front()
        sys.exit()

    if not shared_memory.create(1):
        sys.exit()

    local_server = QLocalServer()
    if local_server.listen("LeafView_Server"):
        def new_connection():
            socket = local_server.nextPendingConnection()
            if socket.waitForReadyRead(1000):
                data = socket.readAll().data()
                if data == b'bringToFront':
                    window.activateWindow()
                    window.raise_()
                    window.showNormal()

        local_server.newConnection.connect(new_connection)

    window = MainWindow()
    window.move(300, 100)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
