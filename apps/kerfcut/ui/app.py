"""
KerfCut — Application Bootstrap
Creates the QApplication, loads stylesheet, launches main window, and catches unhandled exceptions.
"""
import sys
import traceback
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont

from version import APP_NAME, APP_AUTHOR
from ui.main_window import MainWindow
from utils.logger import logger

from PyQt6.QtCore import QSettings

STYLE_PATH = Path(__file__).parent.parent / "assets" / "style.qss"
STYLE_DARK_PATH = Path(__file__).parent.parent / "assets" / "style_dark.qss"

def load_stylesheet() -> str:
    settings = QSettings(APP_AUTHOR, APP_NAME)
    theme = settings.value("theme", "light")
    
    path = STYLE_DARK_PATH if theme == "dark" else STYLE_PATH
    if not path.exists() and theme == "dark":
        logger.warning("Dark stylesheet not found, falling back to light stylesheet.")
        path = STYLE_PATH
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Catch unhandled exceptions, log them, and show a safe error dialog."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Log the full traceback
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    # Show simple message to user
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Check if a QApplication instance exists to show the dialog
    app = QApplication.instance()
    if app:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Critical Error")
        msg_box.setText("An unexpected error occurred.\nPlease check the log files for details.")
        msg_box.setDetailedText(err_msg)
        msg_box.exec()


def launch() -> int:
    # Install the global exception hook
    sys.excepthook = global_exception_handler
    logger.info(f"Starting {APP_NAME}...")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_AUTHOR)

    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(load_stylesheet())
    
    # Licensing Check (Phase 3)
    from ui.auth_dialog import request_license
    if not request_license():
        logger.info("License activation cancelled or failed. Exiting.")
        return 0

    win = MainWindow()
    win.show()
    logger.info("Main window shown.")
    
    ret_code = app.exec()
    logger.info(f"Application exited with code {ret_code}")
    return ret_code
