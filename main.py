import sys
from PySide6 import QtWidgets
from ui.main_window import SolidGymApp

"""
Entry point for the Solid Gym Management System.
Run this file to start the application.
"""

if __name__ == "__main__":
    # Create the Application instance
    app = SolidGymApp(sys.argv)
    
    # Custom start method (handles setup, DB init, and login)
    app.start()
    
    # Start the event loop
    sys.exit(app.exec())