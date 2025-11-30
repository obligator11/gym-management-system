import sys
from typing import List, Optional
from PySide6 import QtWidgets, QtCore

from ui.dialogs.login_dialog import LoginDialog
from ui.dashboards.admin_dashboard import AdminDashboard
from ui.dashboards.user_dashboard import UserDashboard
from ui.dialogs.setup_dialog import AdminSetupDialog
from ui.dialogs.backup_dialog import BackupDialog

from core.database import init_db, admin_exists
from services.file_manager import load_or_setup_paths
import config


class SolidGymApp(QtWidgets.QApplication):
    """
    The main Application class that manages the application lifecycle.
    1. Sets up data paths and database.
    2. checks for Admin existence (Setup Wizard).
    3. Handles Login.
    4. Launches the appropriate Dashboard (Admin vs User).
    """
    def __init__(self, args: List[str]):
        super().__init__(args)
        self.main_window: Optional[QtWidgets.QMainWindow] = None

    def start(self) -> None:
        """Initializes the environment and shows the first screen."""
        # 1. Setup File System
        load_or_setup_paths()
        
        # 2. Initialize Database
        init_db()

        # 3. First-Run Check: Force Admin Creation if none exists
        if not admin_exists():
            dlg = AdminSetupDialog()
            if dlg.exec() != QtWidgets.QDialog.Accepted:
                sys.exit(0)

        # 4. Show Login Screen
        self.show_login()

    def show_login(self) -> None:
        """Displays the login dialog and routes to the correct dashboard."""
        dlg = LoginDialog()
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            # User closed the login window without logging in
            sys.exit(0)

        # Retrieve auth details from the dialog
        username = dlg.uname.text().strip()
        role = getattr(dlg, 'role', 'user')
        gender = getattr(dlg, 'gender', 'Male')

        # Route to appropriate dashboard
        if role == 'admin':
            self.main_window = AdminDashboard()
            # Ask for backup shortly after admin login
            QtCore.QTimer.singleShot(1000, self.ask_for_backup)
        else:
            # Pass username to UserDashboard for logging purposes
            self.main_window = UserDashboard(gender, username)

        # Handle Logout Signal to restart the flow
        if hasattr(self.main_window, 'logout_signal'):
            self.main_window.logout_signal.connect(self.on_logout)
            
        self.main_window.show()

    def ask_for_backup(self) -> None:
        """Prompts the admin to backup data to the cloud."""
        if self.main_window:
            dlg = BackupDialog(self.main_window)
            dlg.exec()

    def on_logout(self) -> None:
        """Closes the current dashboard and re-opens the login screen."""
        if self.main_window:
            self.main_window.close()
            self.main_window = None
            
        self.show_login()