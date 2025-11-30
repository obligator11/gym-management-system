import shutil
import datetime
import os
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6 import QtWidgets, QtCore, QtGui
import config
from core.utils import add_months
from models.member import Member

# Workers
from workers.search_worker import SearchWorker
from workers.save_worker import SaveWorker

# Services
from services.attendance_service import mark_attendance
from services.member_service import get_member_by_id, renew_membership
from services.finance_service import log_fee_update
from ai_module.analytics import GymAI

# Dialogs
from ui.dialogs.renew_dialog import RenewDialog
from ui.dialogs.camera_dialog import CameraDialog


class UserDashboard(QtWidgets.QMainWindow):
    """
    The Staff Portal dashboard.
    Restricted access compared to Admin:
    - Can Add Members
    - Can Search (Limited by Gender usually)
    - Can Mark Attendance
    - Can Update Fees
    - CANNOT delete members or manage users.
    """
    logout_signal = QtCore.Signal()

    def __init__(self, user_gender: str, username: str):
        super().__init__()
        # Force Title Case for gender to match DB (e.g. "Male")
        self.user_gender = str(user_gender).capitalize() if user_gender else "Male"
        self.current_username = username
        
        self.setWindowTitle(f"Solid Gym - Staff Portal ({username})")
        self.resize(1100, 750)
        
        self.pool = QtCore.QThreadPool()
        self.current_photo_path: Optional[str] = None
        
        self.init_ui()
        self.apply_style()

    def init_ui(self) -> None:
        cw = QtWidgets.QWidget()
        self.setCentralWidget(cw)
        layout = QtWidgets.QHBoxLayout(cw)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- SIDEBAR ---
        sidebar = QtWidgets.QVBoxLayout()
        sidebar.setContentsMargins(10, 20, 10, 10)
        sidebar.setSpacing(10)
        
        lbl_role = QtWidgets.QLabel("👤 STAFF PANEL")
        lbl_role.setStyleSheet("color: #ffcc00; font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        sidebar.addWidget(lbl_role)

        self.btn_search = QtWidgets.QPushButton("🔍 Search / Pay Fee")
        self.btn_add = QtWidgets.QPushButton("➕ Add New Member")
        self.btn_att = QtWidgets.QPushButton("⏱️ Attendance")

        for btn in [self.btn_search, self.btn_add, self.btn_att]:
            btn.setMinimumHeight(40)
            btn.setCheckable(True)
            sidebar.addWidget(btn)

        sidebar.addStretch()
        
        btn_logout = QtWidgets.QPushButton("🚪 Logout")
        btn_logout.clicked.connect(lambda: [self.logout_signal.emit(), self.close()])
        sidebar.addWidget(btn_logout)

        sw = QtWidgets.QWidget()
        sw.setLayout(sidebar)
        sw.setFixedWidth(200)
        sw.setStyleSheet("background: #111; border-right: 1px solid #333;")
        layout.addWidget(sw)

        # --- CONTENT AREA ---
        self.stacked = QtWidgets.QStackedWidget()
        layout.addWidget(self.stacked)

        self.page_search = QtWidgets.QWidget()
        self.init_search_page()
        self.stacked.addWidget(self.page_search)
        
        self.page_add = QtWidgets.QWidget()
        self.init_add_page()
        self.stacked.addWidget(self.page_add)
        
        self.page_att = QtWidgets.QWidget()
        self.init_attendance_page()
        self.stacked.addWidget(self.page_att)

        # Navigation Logic
        self.btn_search.clicked.connect(lambda: self.switch_page(0))
        self.btn_add.clicked.connect(lambda: self.switch_page(1))
        self.btn_att.clicked.connect(lambda: self.switch_page(2))
        
        # Default Page
        self.switch_page(0)

    def switch_page(self, index: int) -> None:
        self.stacked.setCurrentIndex(index)
        self.btn_search.setChecked(index == 0)
        self.btn_add.setChecked(index == 1)
        self.btn_att.setChecked(index == 2)

    # --- 1. SEARCH PAGE ---
    def init_search_page(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.page_search)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QtWidgets.QLabel(f"Viewing: {self.user_gender} Members Only"))

        box = QtWidgets.QHBoxLayout()
        self.search_in = QtWidgets.QLineEdit()
        self.search_in.setPlaceholderText("Enter ID or Name")
        self.search_in.returnPressed.connect(self.on_search)
        
        btn = QtWidgets.QPushButton("Search")
        btn.clicked.connect(self.on_search)
        
        box.addWidget(self.search_in)
        box.addWidget(btn)
        layout.addLayout(box)

        # Member Info Panel (Hidden by default)
        self.info_w = QtWidgets.QWidget()
        self.info_w.setVisible(False)
        self.info_w.setStyleSheet("background: #1b1b1b; border-radius: 8px; padding: 15px;")
        
        v_main = QtWidgets.QVBoxLayout(self.info_w)
        h_top = QtWidgets.QHBoxLayout()
        
        self.v_ph = QtWidgets.QLabel()
        self.v_ph.setFixedSize(120, 120)
        self.v_ph.setStyleSheet("border:2px solid #555")
        
        self.v_badge = QtWidgets.QLabel("ACTIVE")
        self.v_badge.setFixedSize(120, 40)
        self.v_badge.setAlignment(QtCore.Qt.AlignCenter)
        
        ph_col = QtWidgets.QVBoxLayout()
        ph_col.addWidget(self.v_ph)
        ph_col.addWidget(self.v_badge)
        
        self.v_det = QtWidgets.QTextEdit()
        self.v_det.setReadOnly(True)
        self.v_det.setStyleSheet("border:none;background:transparent; font-size: 14px;")
        
        h_top.addLayout(ph_col)
        h_top.addWidget(self.v_det)
        v_main.addLayout(h_top)

        self.btn_renew = QtWidgets.QPushButton("💰 Update Fee / Renew Membership")
        self.btn_renew.setFixedHeight(45)
        self.btn_renew.setStyleSheet("background: #d4af37; color: black; font-weight: bold; border: 1px solid #b8860b;")
        self.btn_renew.clicked.connect(self.open_renew_dialog)
        
        v_main.addWidget(self.btn_renew)
        layout.addWidget(self.info_w)
        layout.addStretch()

    def on_search(self) -> None:
        q = self.search_in.text().strip()
        if not q: 
            return
        
        # Search constrained by User's gender
        w = SearchWorker(q, is_admin=False, user_gender=self.user_gender)
        w.signals.finished.connect(self._found)
        self.pool.start(w)

    def _found(self, d: Dict[str, Any]) -> None:
        if d.get("access_denied"): 
            QtWidgets.QMessageBox.warning(self, "Denied", "Restricted access: Cannot view member of opposite gender.")
            return
            
        p = d.get("parsed")
        if not p: 
            self.info_w.setVisible(False)
            return
            
        self.info_w.setVisible(True)
        self.current_view_id = p.get('id')
        st = p.get('status', 'Expired')

        # Badge Style
        c = "#b00"
        if st.lower() == "active":
            c = "#006600"
        elif st.lower() == "pending":
            c = "orange"

        self.v_badge.setText(st.upper())
        self.v_badge.setStyleSheet(
            f"background: {c}; color: white; font-weight: bold; border-radius: 4px; font-size: 14px;"
        )

        pkg = p.get('package', 'Bronze')
        join_date = f"{p.get('day', 0):02d}/{p.get('month', 0):02d}/{p.get('year', 0)}"
        
        txt = (f"Name: {p.get('name')}\n"
               f"ID: {p.get('id')}\n"
               f"Package: {pkg}\n\n"
               f"📞 Phone: {p.get('phone')}\n"
               f"📅 Join/Start: {join_date}\n"
               f"🛑 Expires On: {p.get('end_date')}")
               
        self.v_det.setPlainText(txt)
        
        if p.get('photo_path') and os.path.exists(p['photo_path']):
            self.v_ph.setPixmap(QtGui.QPixmap(p['photo_path']).scaled(120, 120, QtCore.Qt.KeepAspectRatio))
        else:
            self.v_ph.clear()
            self.v_ph.setText("No Photo")

    def open_renew_dialog(self) -> None:
        if not hasattr(self, 'current_view_id') or not self.current_view_id: 
            return
            
        current_data = get_member_by_id(self.current_view_id)
        current_expiry = current_data.get('end_date', '') if current_data else None
        
        dlg = RenewDialog(self, current_expiry)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            data = dlg.result_data
            try:
                renew_membership(self.current_view_id, data['start_date'], data['end_date'], data['months'])
                log_fee_update(self.current_username, self.current_view_id, data['months'])
                
                QtWidgets.QMessageBox.information(self, "Success", "Fee Updated & Logged!")
                self.on_search()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    # --- 2. ADD PAGE ---
    def init_add_page(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.page_add)
        layout.addWidget(QtWidgets.QLabel("📝 Add New Member"))
        
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        
        fw = QtWidgets.QWidget()
        fl = QtWidgets.QVBoxLayout(fw)

        # Photo Section
        ph = QtWidgets.QHBoxLayout()
        self.add_ph_lbl = QtWidgets.QLabel("No Photo")
        self.add_ph_lbl.setFixedSize(120, 120)
        self.add_ph_lbl.setStyleSheet("border:1px solid #555")

        b = QtWidgets.QPushButton("Upload")
        b.clicked.connect(self.upl)
        
        b_cam = QtWidgets.QPushButton("📷 Camera")
        b_cam.clicked.connect(self.take_photo)

        ph.addWidget(self.add_ph_lbl)
        ph.addWidget(b)
        ph.addWidget(b_cam)
        ph.addStretch()
        fl.addLayout(ph)

        # Inputs
        self.aid = QtWidgets.QLineEdit()
        self.aname = QtWidgets.QLineEdit()
        self.aph = QtWidgets.QLineEdit()
        self.abl = QtWidgets.QLineEdit()
        self.acnic = QtWidgets.QLineEdit()

        self.agen = QtWidgets.QLabel(self.user_gender)
        self.agen.setStyleSheet("color:#00ff00; font-weight:bold; font-size:14px; border:1px solid #333; padding:5px;")

        form = QtWidgets.QFormLayout()
        form.addRow("ID*", self.aid)
        form.addRow("Name*", self.aname)
        form.addRow("Gender (Auto)", self.agen)
        form.addRow("Phone", self.aph)
        form.addRow("Blood", self.abl)
        form.addRow("CNIC*", self.acnic)
        
        self.apkg = QtWidgets.QComboBox()
        self.apkg.addItems(["Bronze", "Silver", "Gold", "Platinum"])
        form.addRow("Package*", self.apkg)

        # Date
        today = datetime.date.today()
        self.aday = QtWidgets.QSpinBox()
        self.aday.setRange(1, 31)
        self.aday.setValue(today.day)
        
        self.amonth = QtWidgets.QComboBox()
        self.amonth.addItems([str(i) for i in range(1, 13)])
        self.amonth.setCurrentIndex(today.month - 1)
        
        self.ayear = QtWidgets.QComboBox()
        self.ayear.addItems([str(y) for y in range(today.year - 1, today.year + 5)])
        self.ayear.setCurrentText(str(today.year))
        
        dateH = QtWidgets.QHBoxLayout()
        dateH.addWidget(self.aday)
        dateH.addWidget(self.amonth)
        dateH.addWidget(self.ayear)
        form.addRow("Start Date*", dateH)

        self.amonths = QtWidgets.QComboBox()
        self.amonths.addItems(["1 Month", "3 Months", "6 Months", "12 Months"])
        form.addRow("Months*", self.amonths)

        fl.addLayout(form)
        
        bs = QtWidgets.QPushButton("💾 Save")
        bs.clicked.connect(self.do_save)
        fl.addWidget(bs)
        fl.addStretch()
        
        scroll.setWidget(fw)
        layout.addWidget(scroll)

    def upl(self) -> None:
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Photo", "", "Images (*.png *.jpg *.jpeg)")
        if f:
            self.current_photo_path = f
            self.add_ph_lbl.setPixmap(QtGui.QPixmap(f).scaled(120, 120, QtCore.Qt.KeepAspectRatio))

    def take_photo(self) -> None:
        dlg = CameraDialog(self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.current_photo_path = dlg.captured_path
            self.add_ph_lbl.setPixmap(
                QtGui.QPixmap(self.current_photo_path).scaled(120, 120, QtCore.Qt.KeepAspectRatio)
            )

    def do_save(self) -> None:
        if not self.aid.text() or not self.aname.text():
            QtWidgets.QMessageBox.warning(self, "Required", "ID and Name are missing!")
            return
            
        try:
            pp = None
            clean_id = self.aid.text().strip().upper()

            # Handle Photo
            if self.current_photo_path and os.path.exists(self.current_photo_path):
                if not config.PHOTOS_FOLDER.exists(): 
                    config.PHOTOS_FOLDER.mkdir(parents=True, exist_ok=True)
                    
                dest = config.PHOTOS_FOLDER / f"{clean_id}{Path(self.current_photo_path).suffix}"
                if Path(self.current_photo_path).resolve() != dest.resolve():
                    shutil.copy2(self.current_photo_path, dest)
                pp = str(dest)

            jd = datetime.date(int(self.ayear.currentText()), int(self.amonth.currentText()), self.aday.value())
            months_int = int(self.amonths.currentText().split()[0])
            ed = add_months(jd, months_int)

            # Create Member (Defaults to 'Pending' for Staff users)
            m = Member(
                id=clean_id, 
                name=self.aname.text().strip(), 
                phone=self.aph.text(), 
                blood=self.abl.text(),
                gender=self.user_gender, 
                cnic=self.acnic.text(),
                day=jd.day, 
                month=jd.month, 
                year=jd.year,
                membership_months=months_int, 
                package=self.apkg.currentText(),
                end_date=str(ed), 
                status="Pending", 
                photo_path=pp
            )

            w = SaveWorker(m)
            w.signals.finished.connect(lambda: [
                self.clear_add(), 
                QtWidgets.QMessageBox.information(self, "Success", "Member sent for Approval!")
            ])
            self.pool.start(w)
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def clear_add(self) -> None:
        self.aid.clear()
        self.aname.clear()
        self.aph.clear()
        self.abl.clear()
        self.acnic.clear()
        self.add_ph_lbl.setText("No Photo")
        self.current_photo_path = None

    # --- 3. ATTENDANCE ---
    def init_attendance_page(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.page_att)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QtWidgets.QLabel("⏱️ Security & Attendance"))
        
        self.lbl_ai = QtWidgets.QLabel("🤖 AI: Gathering...")
        self.lbl_ai.setStyleSheet("color:#0af")
        layout.addWidget(self.lbl_ai)
        
        ib = QtWidgets.QGroupBox("Check-In")
        h = QtWidgets.QHBoxLayout(ib)
        
        self.att_id = QtWidgets.QLineEdit()
        self.att_id.setPlaceholderText("Scan/Enter ID")
        self.att_id.returnPressed.connect(self.do_checkin)
        
        b = QtWidgets.QPushButton("✅ Check In")
        b.setStyleSheet("background:#006600")
        b.clicked.connect(self.do_checkin)
        
        h.addWidget(self.att_id)
        h.addWidget(b)
        layout.addWidget(ib)

        db = QtWidgets.QGroupBox("Identity")
        v = QtWidgets.QVBoxLayout(db)
        
        self.chk_ph = QtWidgets.QLabel("Waiting...")
        self.chk_ph.setFixedSize(200, 200)
        self.chk_ph.setStyleSheet("border:3px solid #333;background:#000")
        
        self.chk_nm = QtWidgets.QLabel("Name: -")
        self.chk_nm.setStyleSheet("font-size:20px;font-weight:bold;color:#fc0")
        
        self.chk_pkg = QtWidgets.QLabel("Package: -")
        self.chk_pkg.setStyleSheet("font-size:14px;color:#ddd")
        
        self.chk_st = QtWidgets.QLabel("Status: -")
        self.chk_st.setStyleSheet("font-size:16px;font-weight:bold")
        
        self.chk_ex = QtWidgets.QLabel("Expires: -")
        self.chk_ex.setStyleSheet("font-size:14px;color:#aaa")

        hc = QtWidgets.QHBoxLayout()
        hc.addStretch()
        hc.addWidget(self.chk_ph)
        hc.addStretch()
        
        v.addLayout(hc)
        v.addWidget(self.chk_nm, alignment=QtCore.Qt.AlignCenter)
        v.addWidget(self.chk_pkg, alignment=QtCore.Qt.AlignCenter)
        v.addWidget(self.chk_st, alignment=QtCore.Qt.AlignCenter)
        v.addWidget(self.chk_ex, alignment=QtCore.Qt.AlignCenter)
        
        layout.addWidget(db)
        layout.addStretch()

    def do_checkin(self) -> None:
        mid = self.att_id.text().strip()
        if not mid: 
            return
            
        d = get_member_by_id(mid)
        if not d:
            QtWidgets.QMessageBox.warning(self, "Unknown", "ID not found")
            self.att_id.clear()
            self.chk_nm.setText("-")
            self.chk_st.setText("NOT FOUND")
            return

        self.chk_nm.setText(d.get('name'))
        self.chk_pkg.setText(f"Package: {d.get('package', 'Bronze')}")
        self.chk_ex.setText(f"Expires: {d.get('end_date', '-')}")

        st = d.get('status', 'Expired')
        self.chk_st.setText(f"Status: {st}")
        self.chk_st.setStyleSheet(
            f"font-size:16px;font-weight:bold;color:{'#0f0' if st.lower() == 'active' else '#f00'}"
        )

        if d.get('photo_path'):
            self.chk_ph.setPixmap(
                QtGui.QPixmap(d['photo_path']).scaled(200, 200, QtCore.Qt.KeepAspectRatio)
            )
        else:
            self.chk_ph.clear()
            self.chk_ph.setText("No Photo")

        mark_attendance(mid)
        self.att_id.clear()
        
        ai = GymAI()
        self.lbl_ai.setText(f"AI: {ai.predict_peak_hours()}")

    def logout(self) -> None:
        self.logout_signal.emit()
        self.close()

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow{background:#0c0c0c;color:white}
            QLineEdit,QComboBox,QSpinBox,QTextEdit{padding:8px;background:#222;color:white;border:1px solid #444}
            QPushButton{padding:8px;background:#333;color:white;border:1px solid #555}
            QPushButton:hover{background:#ffcc00;color:black}
        """)