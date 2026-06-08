"""
KerfCut — License Activation Dialog
A premium-styled entry point for license verification.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QApplication, QFrame
)
from PyQt6.QtCore import Qt
from core.auth import (
    verify_license, check_offline_token, dev_license_enabled,
    force_trial_mode_enabled, get_machine_id_display
)

class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KerfCut Activation")
        self.setFixedSize(500, 320)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Header
        self.header = QLabel("Activate KerfCut")
        self.header.setObjectName("header")
        layout.addWidget(self.header)

        # Subtitle
        self.subtitle = QLabel("Please enter your license key to continue.")
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)

        # Machine ID display
        mid_frame = QFrame()
        mid_frame.setObjectName("machineIdFrame")
        mid_layout = QHBoxLayout(mid_frame)
        mid_layout.setContentsMargins(10, 6, 10, 6)
        mid_layout.setSpacing(8)

        mid_label = QLabel("Machine ID:")
        mid_label.setObjectName("machineIdLabel")
        mid_layout.addWidget(mid_label)

        self.mid_value = QLabel(get_machine_id_display())
        self.mid_value.setObjectName("machineIdValue")
        self.mid_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mid_layout.addWidget(self.mid_value, 1)

        self.copy_btn = QPushButton("📋")
        self.copy_btn.setObjectName("copy_btn")
        self.copy_btn.setFixedSize(32, 28)
        self.copy_btn.setToolTip("Copy Machine ID to clipboard")
        self.copy_btn.clicked.connect(self._copy_machine_id)
        mid_layout.addWidget(self.copy_btn)

        layout.addWidget(mid_frame)

        # Input Field
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setMinimumHeight(45)
        layout.addWidget(self.key_input)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.setMinimumHeight(40)
        self.quit_btn.clicked.connect(self.reject)
        
        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setMinimumHeight(40)
        self.activate_btn.setDefault(True)
        self.activate_btn.clicked.connect(self.handle_activation)
        
        btn_layout.addWidget(self.quit_btn)
        btn_layout.addWidget(self.activate_btn)
        layout.addLayout(btn_layout)

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7f9;
            }
            #header {
                font-size: 24px;
                font-weight: bold;
                color: #2d6a9f;
            }
            QLabel {
                font-size: 14px;
                color: #2c3e50;
            }
            #machineIdFrame {
                background-color: #eef2f7;
                border: 1px solid #d1d9e6;
                border-radius: 6px;
            }
            #machineIdLabel {
                font-size: 12px;
                color: #7f8c8d;
                font-weight: bold;
            }
            #machineIdValue {
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
                color: #2c3e50;
                font-weight: bold;
            }
            QPushButton#copy_btn {
                background-color: transparent;
                border: 1px solid #d1d9e6;
                border-radius: 4px;
                padding: 2px;
                font-size: 14px;
            }
            QPushButton#copy_btn:hover {
                background-color: #d1d9e6;
            }
            QLineEdit {
                border: 1px solid #d1d9e6;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                background-color: #ffffff;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QPushButton {
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton#activate_btn {
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton#activate_btn:hover {
                background-color: #2980b9;
            }
            QPushButton#quit_btn {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #d1d9e6;
            }
            QPushButton#quit_btn:hover {
                background-color: #eef2f7;
            }
            QMessageBox QLabel {
                color: #2c3e50;
            }
            QMessageBox QPushButton {
                background-color: #f5f7f9;
                color: #2c3e50;
                border: 1px solid #d1d9e6;
            }
        """)
        self.activate_btn.setObjectName("activate_btn")
        self.quit_btn.setObjectName("quit_btn")

    def _copy_machine_id(self):
        """Copy the machine ID to the system clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.mid_value.text())
        self.copy_btn.setText("✅")
        # Reset icon after 1.5 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋"))

    def handle_activation(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Invalid Key", "Please enter a license key.")
            return

        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Verifying...")
        self.repaint() # Force UI update

        if verify_license(key):
            self.accept()
        else:
            QMessageBox.critical(self, "Activation Failed", 
                                "Invalid or inactive license key.\n\n"
                                "Please check your key or contact support.")
            self.activate_btn.setEnabled(True)
            self.activate_btn.setText("Activate")

def request_license():
    """Helper function to show the dialog and return result."""
    if force_trial_mode_enabled():
        return True

    if dev_license_enabled():
        return verify_license("KERFCUT-DEV-99")

    if check_offline_token():
        return True

    dialog = LicenseDialog()
    return dialog.exec() == QDialog.DialogCode.Accepted
