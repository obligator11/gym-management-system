import datetime
from typing import Optional, Dict, Any
from PySide6 import QtWidgets, QtCore
from core.utils import add_months


class RenewDialog(QtWidgets.QDialog):
    """
    Dialog for renewing a member's subscription or updating their fee status.
    Automatically calculates the new expiration date based on the selected duration.
    """
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, current_expiry_str: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("💰 Update Fee / Renew")
        self.setFixedSize(400, 350)
        
        self.current_expiry_str = current_expiry_str
        self.result_data: Optional[Dict[str, Any]] = None  # Will hold (start_date, months, new_end_date)
        
        # State variables for calculation
        self.calculated_start = datetime.date.today()
        self.calculated_end = datetime.date.today()

        self.init_ui()
        self.apply_style()
        self.calculate_end_date()  # Initial calculation

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)

        # --- Header Info ---
        info_box = QtWidgets.QGroupBox("Current Status")
        ib_layout = QtWidgets.QVBoxLayout(info_box)
        
        lbl_curr = QtWidgets.QLabel(f"Current Expiration: {self.current_expiry_str or 'N/A'}")
        lbl_curr.setStyleSheet("color: #aaa; font-weight: bold;")
        ib_layout.addWidget(lbl_curr)
        layout.addWidget(info_box)

        # --- Renewal Form ---
        form_box = QtWidgets.QGroupBox("Renewal Details")
        form = QtWidgets.QFormLayout(form_box)

        # 1. Activation Date (Start Date)
        self.inp_start_date = QtWidgets.QDateEdit()
        self.inp_start_date.setCalendarPopup(True)
        self.inp_start_date.setDisplayFormat("yyyy-MM-dd")

        # Logic: If expired, default to Today. If active, default to Day After Expiry.
        today = datetime.date.today()
        default_date = today
        
        if self.current_expiry_str:
            try:
                exp_date = datetime.datetime.strptime(self.current_expiry_str, "%Y-%m-%d").date()
                if exp_date >= today:
                    # If still active, start the new package the day after it expires
                    default_date = exp_date + datetime.timedelta(days=1)
            except ValueError:
                pass

        self.inp_start_date.setDate(default_date)
        self.inp_start_date.dateChanged.connect(self.calculate_end_date)

        # 2. Duration (Months)
        self.inp_months = QtWidgets.QSpinBox()
        self.inp_months.setRange(1, 60)
        self.inp_months.setValue(1)
        self.inp_months.valueChanged.connect(self.calculate_end_date)

        form.addRow("Activation Date:", self.inp_start_date)
        form.addRow("Duration (Months):", self.inp_months)
        layout.addWidget(form_box)

        # --- Result Preview ---
        self.lbl_result = QtWidgets.QLabel("New Expiry: -")
        self.lbl_result.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_result.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ff00; margin: 10px;")
        layout.addWidget(self.lbl_result)

        # --- Buttons ---
        btn_layout = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton("✅ Confirm Update")
        btn_save.setFixedHeight(40)
        btn_save.setStyleSheet("background: #006600; font-weight: bold;")
        btn_save.clicked.connect(self.save_and_close)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.setFixedHeight(40)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def calculate_end_date(self) -> None:
        """Live calculation of the end date based on user input."""
        start_qdate = self.inp_start_date.date()
        # Convert QDate to python datetime.date
        start_date = datetime.date(start_qdate.year(), start_qdate.month(), start_qdate.day())
        months = self.inp_months.value()

        # Use our utility function from core.utils
        end_date = add_months(start_date, months)
        
        self.lbl_result.setText(f"New Expiry: {end_date}")
        self.calculated_end = end_date
        self.calculated_start = start_date

    def save_and_close(self) -> None:
        """Saves result and closes dialog."""
        self.result_data = {
            "start_date": self.calculated_start,
            "months": self.inp_months.value(),
            "end_date": self.calculated_end
        }
        self.accept()

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog { background: #1a1a1a; color: white; font-family: 'Segoe UI'; }
            QGroupBox { border: 1px solid #444; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLabel { color: white; }
            QDateEdit, QSpinBox { background: #222; color: white; border: 1px solid #555; padding: 5px; }
            QPushButton { background: #333; color: white; border: 1px solid #555; border-radius: 4px; }
            QPushButton:hover { background: #444; }
        """)