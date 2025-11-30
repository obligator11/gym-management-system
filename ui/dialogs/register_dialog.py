from PySide6 import QtWidgets, QtCore
from services.auth_service import create_user
from typing import Optional


class RegisterDialog(QtWidgets.QDialog):
    """
    Dialog for creating new accounts.
    Allows creating 'User' accounts freely, but requires a Master Key
    to create 'Admin' accounts.
    """
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Create Account - SOLID GYM")
        self.setModal(True)
        self.setFixedSize(450, 500)
        
        self.init_ui()
        self.apply_style()

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Title
        title = QtWidgets.QLabel("📝 Create Account")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffcc00; margin-bottom: 10px;")
        layout.addWidget(title)

        # Form Inputs
        self.uname = QtWidgets.QLineEdit()
        self.uname.setPlaceholderText("Choose a Username")
        self.uname.setMinimumHeight(40)

        self.passwd = QtWidgets.QLineEdit()
        self.passwd.setPlaceholderText("Choose a Password")
        self.passwd.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwd.setMinimumHeight(40)

        self.gender = QtWidgets.QComboBox()
        self.gender.addItems(["Select Gender", "Male", "Female"])
        self.gender.setMinimumHeight(40)

        # Role Selection
        self.role_select = QtWidgets.QComboBox()
        self.role_select.addItems(["Standard User (Staff)", "Admin"])
        self.role_select.setMinimumHeight(40)
        self.role_select.currentTextChanged.connect(self.toggle_admin_input)

        # Master Password (Hidden by default)
        self.master_pass = QtWidgets.QLineEdit()
        self.master_pass.setPlaceholderText("Enter Master Key (Required for Admin)")
        self.master_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.master_pass.setMinimumHeight(40)
        self.master_pass.setVisible(False)
        self.master_pass.setStyleSheet("border: 1px solid #ffcc00;")

        # Layout Assembly
        layout.addWidget(QtWidgets.QLabel("Username:"))
        layout.addWidget(self.uname)
        
        layout.addWidget(QtWidgets.QLabel("Password:"))
        layout.addWidget(self.passwd)
        
        layout.addWidget(QtWidgets.QLabel("Gender:"))
        layout.addWidget(self.gender)
        
        layout.addWidget(QtWidgets.QLabel("Account Role:"))
        layout.addWidget(self.role_select)
        
        # Only visible if Admin is selected
        layout.addWidget(self.master_pass)

        layout.addSpacing(10)

        # Register Button
        btn_reg = QtWidgets.QPushButton("✓ Create Account")
        btn_reg.setFixedHeight(45)
        btn_reg.clicked.connect(self.do_register)
        btn_reg.setCursor(QtCore.Qt.PointingHandCursor)
        layout.addWidget(btn_reg)

    def toggle_admin_input(self, text: str) -> None:
        """Shows the master password field only if 'Admin' is selected."""
        self.master_pass.setVisible(text == "Admin")

    def do_register(self) -> None:
        u = self.uname.text().strip()
        p = self.passwd.text()
        g = self.gender.currentText()
        role_selection = self.role_select.currentText()

        # Map UI text to Database role codes
        db_role = 'admin' if role_selection == "Admin" else 'user'

        if not u or not p:
            QtWidgets.QMessageBox.warning(self, "Missing Data", "Please fill in all fields.")
            return

        if g == "Select Gender":
            QtWidgets.QMessageBox.warning(self, "Missing Data", "Please select your gender.")
            return

        # --- SECURITY CHECK ---
        if db_role == 'admin':
            # IMPORTANT: Replaced hardcoded password with a placeholder for GitHub safety.
            # Change this string to your actual secret key before running.
            if self.master_pass.text() != "YOUR_MASTER_KEY_HERE":
                QtWidgets.QMessageBox.critical(
                    self, "Security Alert",
                    "Incorrect Master Key!\nYou are not authorized to create an Admin account."
                )
                return

        try:
            create_user(u, p, db_role, g)
            QtWidgets.QMessageBox.information(
                self, "Success", f"Account created successfully!\nRole: {role_selection}"
            )
            self.accept()
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog { background: #0c0c0c; color: white; font-family: 'Segoe UI'; }
            QLabel { color: white; font-size: 14px; }
            QLineEdit, QComboBox { 
                background: #1b1b1b; color: white; border: 1px solid #333; 
                border-radius: 6px; padding: 5px; font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #ffcc00; }
            QPushButton { 
                background: #b71c1c; color: white; border-radius: 8px; 
                font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background: #d32f2f; }
            QComboBox::drop-down { border: none; }
        """)