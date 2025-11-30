from typing import Optional
from PySide6 import QtWidgets, QtCore
from services.auth_service import create_user


class AdminSetupDialog(QtWidgets.QDialog):
    """
    Dialog displayed on the very first run of the application.
    Forces the user to create the primary Administrator account before using the app.
    """
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Admin Setup - SOLID GYM")
        self.setModal(True)
        self.setFixedSize(450, 250)
        
        self.init_ui()
        self.apply_style()

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("🔐 Create Admin Account")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; margin: 15px;")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        
        self.uname = QtWidgets.QLineEdit()
        self.passwd = QtWidgets.QLineEdit()
        self.passwd.setEchoMode(QtWidgets.QLineEdit.Password)
        
        self.passwd2 = QtWidgets.QLineEdit()
        self.passwd2.setEchoMode(QtWidgets.QLineEdit.Password)

        form.addRow("Admin Username:", self.uname)
        form.addRow("Password:", self.passwd)
        form.addRow("Confirm Password:", self.passwd2)
        layout.addLayout(form)

        btn = QtWidgets.QPushButton("✓ Create Admin")
        btn.setFixedHeight(40)
        btn.clicked.connect(self.create_admin)
        layout.addWidget(btn)

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog { background: #0c0c0c; color: #ffffff; font-family: 'Segoe UI'; }
            QLabel { color: #ffffff; font-size: 14px; }
            QLineEdit { 
                background: #1b1b1b; color: #ffffff; border: 1px solid #333; 
                border-radius: 6px; padding: 8px; font-size: 13px;
            }
            QPushButton { 
                background: #b71c1c; color: #ffffff; border-radius: 8px; 
                padding: 10px 20px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background: #ffcc00; color: #111; }
        """)

    def create_admin(self) -> None:
        uname = self.uname.text().strip()
        p1 = self.passwd.text()
        p2 = self.passwd2.text()

        if not uname or not p1:
            QtWidgets.QMessageBox.warning(self, "Error", "All fields are required.")
            return

        if p1 != p2:
            QtWidgets.QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        try:
            # Create the first user as 'admin'
            create_user(uname, p1, 'admin', None)
            
            QtWidgets.QMessageBox.information(
                self, "Success", "Admin account created successfully!\nPlease login to continue."
            )
            self.accept()
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))