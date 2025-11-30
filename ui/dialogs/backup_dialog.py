from typing import Optional
from PySide6 import QtWidgets, QtCore, QtGui
from services.cloud_service import create_local_backup, upload_to_drive


class BackupDialog(QtWidgets.QDialog):
    """
    A dialog that allows the user to trigger a local backup (Zip)
    and optionally upload it to Google Drive.
    """
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Cloud Backup")
        self.setFixedSize(400, 250)
        # Frameless popup style for a modern look
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)
        self.init_ui()
        self.apply_style()

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Header ---
        title = QtWidgets.QLabel("☁️ Secure Your Data")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffcc00; margin-bottom: 5px;")
        layout.addWidget(title)

        info = QtWidgets.QLabel(
            "Would you like to create a backup on Google Drive?\n"
            "This prevents data loss if your computer crashes."
        )
        info.setWordWrap(True)
        info.setAlignment(QtCore.Qt.AlignCenter)
        info.setStyleSheet("color: #ccc; font-size: 13px;")
        layout.addWidget(info)

        layout.addSpacing(20)

        # --- Visual Input (Optional) ---
        # Note: Actual auth is handled by OAuth in browser, this is just for UX
        self.email_inp = QtWidgets.QLineEdit()
        self.email_inp.setPlaceholderText("Enter Admin Email (Optional)")
        layout.addWidget(self.email_inp)

        # --- Buttons ---
        btn_backup = QtWidgets.QPushButton("🚀 Start Cloud Backup")
        btn_backup.setFixedHeight(40)
        btn_backup.setStyleSheet("background: #006600; font-size: 14px;")
        btn_backup.clicked.connect(self.start_backup)
        layout.addWidget(btn_backup)

        btn_ignore = QtWidgets.QPushButton("Ignore / Skip")
        btn_ignore.setStyleSheet("background: transparent; color: #666; text-decoration: underline;")
        btn_ignore.clicked.connect(self.close)
        layout.addWidget(btn_ignore)

    def start_backup(self) -> None:
        # 1. Create Local Zip
        self.hide()  # Hide popup during process to prevent double clicks
        
        # create_local_backup returns (path, error_message)
        zip_path, err = create_local_backup()

        if not zip_path:
            QtWidgets.QMessageBox.critical(None, "Error", f"Failed to zip data: {err}")
            self.accept() # Close dialog even on error
            return

        # 2. Upload to Cloud
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Uploading...")
        msg.setText("Connecting to Google Drive...\nPlease check your browser to login if prompted.")
        msg.show()

        # upload_to_drive returns (success_bool, file_id_or_error)
        success, result = upload_to_drive(zip_path)
        msg.close()

        if success:
            QtWidgets.QMessageBox.information(
                None, "Success", "✅ Backup successfully uploaded to Google Drive!"
            )
        else:
            # Fallback message if cloud fails but local zip worked
            QtWidgets.QMessageBox.warning(
                None, "Partial Success",
                f"Could not connect to Google Drive ({result}).\n\n"
                f"HOWEVER: A local backup was saved to your Desktop:\n{zip_path}"
            )

        self.accept()

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog { background: #1a1a1a; border: 2px solid #ffcc00; border-radius: 10px; }
            QLabel { color: white; font-family: 'Segoe UI'; }
            QLineEdit { padding: 8px; border: 1px solid #444; background: #111; color: white; border-radius: 4px; }
            QPushButton { color: white; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background: #ffcc00; color: black; }
        """)