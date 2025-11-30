import sys
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from PySide6 import QtWidgets, QtCore, QtGui

from services.auth_service import verify_user
from ui.dialogs.register_dialog import RegisterDialog
import config


class LoginDialog(QtWidgets.QDialog):
    """
    The main login dialog for the application.
    Handles user authentication and provides access to registration.
    Displays developer credits dynamically from config.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - SOLID GYM")
        self.setModal(True)
        self.setFixedSize(650, 750)
        
        # State variables
        self.role: Optional[str] = None
        self.gender: Optional[str] = None
        
        self.init_ui()
        self.apply_style()

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # --- TITLE ---
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.addStretch()
        title_label = QtWidgets.QLabel("💪 SOLID GYM")
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #ffcc00; margin-bottom: 10px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        subtitle = QtWidgets.QLabel("🔐 Login to Access System")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #ffffff; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # --- FORM ---
        form_layout = QtWidgets.QFormLayout()
        form_layout.setVerticalSpacing(15)

        self.uname = QtWidgets.QLineEdit()
        self.uname.setPlaceholderText("Enter username")
        self.uname.setMinimumHeight(45)

        self.passwd = QtWidgets.QLineEdit()
        self.passwd.setPlaceholderText("Enter password")
        self.passwd.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwd.setMinimumHeight(45)

        form_layout.addRow(QtWidgets.QLabel("Username:"), self.uname)
        form_layout.addRow(QtWidgets.QLabel("Password:"), self.passwd)
        layout.addLayout(form_layout)

        # Login Button
        self.btn_login = QtWidgets.QPushButton("🔐 Login")
        self.btn_login.setFixedHeight(50)
        self.btn_login.clicked.connect(self.do_login)
        self.btn_login.setCursor(QtCore.Qt.PointingHandCursor)
        layout.addWidget(self.btn_login)

        # Register Button
        self.btn_register = QtWidgets.QPushButton("📝 No account? Create one here")
        self.btn_register.setFixedHeight(30)
        self.btn_register.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_register.clicked.connect(self.open_register)
        self.btn_register.setStyleSheet(
            "background: transparent; color: #888; border: none; font-size: 13px; text-decoration: underline;")
        layout.addWidget(self.btn_register)

        layout.addSpacing(10)

        # --- DEVELOPER CONTACT SECTION ---
        # We check if 'DEVELOPERS' exists in config to avoid crashes
        developers = getattr(config, 'DEVELOPERS', [])
        
        if developers:
            contact_group = QtWidgets.QGroupBox("👤 Developer Team")
            contact_layout = QtWidgets.QVBoxLayout(contact_group)
            contact_layout.setContentsMargins(10, 20, 10, 15)

            devs_row = QtWidgets.QHBoxLayout()
            devs_row.setSpacing(50)  # Space between developer columns
            devs_row.addStretch()

            for dev in developers:
                # Vertical layout for each person
                person_layout = QtWidgets.QVBoxLayout()
                person_layout.setSpacing(8)

                # 1. Circular Button
                btn = QtWidgets.QPushButton()
                btn.setFixedSize(64, 64)
                btn.setCursor(QtCore.Qt.PointingHandCursor)

                # Load Icon
                img_path = Path(f"assets/images/{dev.get('icon', 'default.png')}")
                if img_path.exists():
                    btn.setIcon(QtGui.QIcon(str(img_path)))
                    btn.setIconSize(QtCore.QSize(32, 32))
                else:
                    btn.setText("LINK")

                link = dev.get('link', '#')
                btn.clicked.connect(lambda checked=False, u=link: self.open_url(u))

                # Circular Style
                color = dev.get('color', '#ffffff')
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 2px solid {color};
                        border-radius: 32px;
                        padding: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {color};
                    }}
                """)

                # 2. Name Label
                lbl_name = QtWidgets.QLabel(dev.get('name', 'Developer'))
                lbl_name.setAlignment(QtCore.Qt.AlignCenter)
                lbl_name.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")

                person_layout.addWidget(btn, alignment=QtCore.Qt.AlignCenter)
                person_layout.addWidget(lbl_name, alignment=QtCore.Qt.AlignCenter)

                devs_row.addLayout(person_layout)

            devs_row.addStretch()
            contact_layout.addLayout(devs_row)
            layout.addWidget(contact_group)

        layout.addStretch()

        # --- EXIT BUTTON ---
        exit_layout = QtWidgets.QHBoxLayout()
        exit_layout.addStretch()
        self.btn_exit = QtWidgets.QPushButton("🚪 Exit")
        self.btn_exit.setFixedSize(120, 40)
        self.btn_exit.clicked.connect(self.do_exit)
        exit_layout.addWidget(self.btn_exit)
        exit_layout.addStretch()
        layout.addLayout(exit_layout)

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog { background: #0c0c0c; color: #ffffff; font-family: 'Segoe UI'; }
            QLabel { color: #ffffff; font-size: 14px; }
            QLineEdit { 
                background: #1b1b1b; color: #ffffff; border: 1px solid #333; 
                border-radius: 6px; padding: 10px; font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #ffcc00; }
            QPushButton { 
                background: #b71c1c; color: #ffffff; border-radius: 8px; 
                font-weight: bold; font-size: 15px; border: none;
            }
            QPushButton:hover { background: #d32f2f; }
            QGroupBox { border: 1px solid #333; border-radius: 8px; margin-top: 10px; font-weight: bold; color: #aaa; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

    def do_login(self) -> None:
        uname = self.uname.text().strip()
        passwd = self.passwd.text()
        
        # Verify credentials
        result = verify_user(uname, passwd)
        
        if result:
            self.role, self.gender = result
            self.accept()
        else:
            QtWidgets.QMessageBox.critical(self, "Login Failed", "Invalid username or password.")

    def open_register(self) -> None:
        dlg = RegisterDialog(self)
        dlg.exec()

    def do_exit(self) -> None:
        sys.exit(0)

    def open_url(self, url: str) -> None:
        try:
            if sys.platform == 'win32':
                os.startfile(url)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', url])
            else:
                subprocess.Popen(['xdg-open', url])
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Could not open link: {e}")