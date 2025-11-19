from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from contextlib import closing
from MainWindow import MainWindow
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('leafview.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

APP_SERVER_NAME = "LeafView_Server"
SHARED_MEMORY_KEY = "LeafView_SharedMemory"
BRING_TO_FRONT_COMMAND = b'bringToFront'


def bring_existing_to_front():
    """Try to bring existing instance to front with better error handling"""
    try:
        with closing(QLocalSocket()) as socket:
            socket.connectToServer(APP_SERVER_NAME)
            if socket.waitForConnected(500):
                socket.write(BRING_TO_FRONT_COMMAND)
                socket.waitForBytesWritten(1000)
                return True
    except Exception as e:
        logger.warning(f"Failed to connect to existing instance: {e}")
    return False


def setup_local_server():
    """Setup local server with better error handling"""
    try:
        server = QLocalServer()
        if not server.listen(APP_SERVER_NAME):
            logger.error(f"Failed to start local server: {server.errorString()}")
            return None
        return server
    except Exception as e:
        logger.error(f"Exception while setting up local server: {e}")
        return None


def handle_application_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Try to show error to user if possible
    try:
        if QtWidgets.QApplication.instance():
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setWindowTitle("Application Error")
            msg.setText("An unexpected error occurred. The application will close.")
            msg.setDetailedText(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            msg.exec()
    except:
        pass


def main():
    """Main application entry point with improved error handling"""
    try:
        # Set global exception handler
        sys.excepthook = handle_application_exception
        
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("LeafView")
        app.setApplicationVersion("1.3")
        
        # Try to detect existing instance
        try:
            shared_memory = QtCore.QSharedMemory(SHARED_MEMORY_KEY)
            if shared_memory.attach():
                if bring_existing_to_front():
                    logger.info("Existing instance detected and brought to front")
                    sys.exit(0)
                else:
                    logger.warning("Existing instance detected but failed to bring to front")
                    sys.exit(1)
            
            if not shared_memory.create(1):
                logger.error("Failed to create shared memory segment")
                QtWidgets.QMessageBox.critical(None, "Startup Error", 
                    "Failed to initialize application. Another instance may be running.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Shared memory initialization failed: {e}")
            # Continue anyway, but log the error
        
        # Setup local server for inter-process communication
        local_server = setup_local_server()
        if not local_server:
            logger.warning("Local server setup failed, continuing without IPC")
        
        def handle_new_connection():
            try:
                socket = local_server.nextPendingConnection()
                if socket:
                    socket.readyRead.connect(lambda: handle_socket_data(socket))
            except Exception as e:
                logger.error(f"Error handling new connection: {e}")
        
        def handle_socket_data(socket):
            try:
                data = socket.readAll().data()
                if data == BRING_TO_FRONT_COMMAND:
                    window.activateWindow()
                    window.raise_()
                    window.showNormal()
            except Exception as e:
                logger.error(f"Error handling socket data: {e}")
            finally:
                try:
                    socket.deleteLater()
                except:
                    pass
        
        if local_server:
            local_server.newConnection.connect(handle_new_connection)
        
        # Create and show main window
        window = MainWindow()
        window.move(300, 100)
        window.show()
        
        # Show warning message
        try:
            window.log("WARNING", "文件整理、重命名和属性写入等操作一旦执行无法恢复，操作前请务必备份好原数据。")
        except Exception as e:
            logger.warning(f"Failed to show warning message: {e}")
        
        # Start event loop
        exit_code = app.exec()
        
        # Cleanup
        try:
            if 'shared_memory' in locals() and shared_memory.isAttached():
                shared_memory.detach()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Fatal error in main(): {e}", exc_info=True)
        QtWidgets.QMessageBox.critical(None, "Fatal Error", 
            f"Application failed to start: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
