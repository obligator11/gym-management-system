import sys
from pathlib import Path
from PySide6 import QtWidgets
import config


def ensure_folder(p: Path) -> None:
    """Creates the folder if it does not exist."""
    p.mkdir(parents=True, exist_ok=True)


def init_paths(base_path: Path) -> None:
    """
    Initialize all global paths based on the selected base path.
    Sets up Gym Data, Database, and Photos folders.
    """
    config.BASE_FOLDER = base_path / "Gym Data"
    ensure_folder(config.BASE_FOLDER)

    config.DB_FILE = base_path / "gym_users.db"

    config.PHOTOS_FOLDER = base_path / "Member Photos"
    ensure_folder(config.PHOTOS_FOLDER)


def load_or_setup_paths() -> None:
    """
    Loads the data path from a local config file.
    If not found, prompts the user to select a folder via a dialog.
    """
    # Saves a hidden config file in the user's home directory
    config_file = Path.home() / ".solidgym_config"

    # 1. Try to load existing config
    if config_file.exists():
        try:
            content = config_file.read_text().strip()
            if content:
                data_path = Path(content)
                if data_path.exists():
                    init_paths(data_path)
                    return
        except Exception:
            # If config is corrupt, ignore and ask user again
            pass

    # 2. If no config, we need to show a GUI dialog.
    # CRITICAL: Check if QApplication exists before creating widgets.
    app = QtWidgets.QApplication.instance()
    if not app:
        # If this runs before main.py creates the app, we must create a temporary one
        # so the dialogs don't crash the script.
        app = QtWidgets.QApplication(sys.argv)

    msg = QtWidgets.QMessageBox()
    msg.setWindowTitle("SOLID GYM - First Time Setup")
    msg.setText("Welcome to SOLID GYM.\nPlease select a folder where all gym data will be stored.")
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.exec()

    selected_dir = QtWidgets.QFileDialog.getExistingDirectory(
        None, "Select Data Storage Folder", str(Path.home())
    )

    if not selected_dir:
        QtWidgets.QMessageBox.critical(None, "Error", "Data storage path is required to continue.")
        sys.exit(0)

    data_path = Path(selected_dir)
    
    # 3. Save the selection for next time
    try:
        config_file.write_text(str(data_path))
        init_paths(data_path)
    except Exception as e:
        QtWidgets.QMessageBox.critical(None, "Error", f"Failed to save configuration: {str(e)}")
        sys.exit(0)