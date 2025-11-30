import shutil
import datetime
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6 import QtWidgets, QtCore, QtGui
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

import config
from core.utils import add_months, month_name
from models.member import Member

# Workers
from workers.save_worker import SaveWorker
from workers.search_worker import SearchWorker
from workers.report_worker import MonthlyListWorker, StatusListWorker

# Services
from services.analytics_service import generate_daily_brief
from services.attendance_service import mark_attendance
from services.member_service import (
    get_member_by_id, renew_membership, get_pending_members, 
    update_member_status, delete_member
)
from services.auth_service import (
    create_user, get_all_users, delete_user_by_id, update_user
)
from services.finance_service import get_fee_logs
from ai_module.analytics import GymAI

# Dialogs
from ui.dialogs.backup_dialog import BackupDialog
from ui.dialogs.renew_dialog import RenewDialog
from ui.dialogs.camera_dialog import CameraDialog


class AdminDashboard(QtWidgets.QMainWindow):
    """
    The main administration window for the gym application.
    Handles Member Management, Approvals, Attendance, Fees, and Users.
    """
    logout_signal = QtCore.Signal()
    member_saved = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("💪 SOLID GYM — Admin Dashboard")
        self.resize(1400, 900)
        
        # ThreadPool for background tasks (Search, Save, etc.)
        self.pool = QtCore.QThreadPool()
        self.pool.setMaxThreadCount(4)
        
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
        sidebar.setContentsMargins(10, 10, 10, 10)
        sidebar.addWidget(QtWidgets.QLabel("💪 ADMIN PANEL"))
        sidebar.addSpacing(10)

        # Navigation Buttons
        self.b_mem = QtWidgets.QPushButton("👤 Member Management")
        self.b_app = QtWidgets.QPushButton("🔔 Approvals")
        self.b_att = QtWidgets.QPushButton("⏱️ Attendance")
        self.b_fees = QtWidgets.QPushButton("💰 Fee Logs")
        self.b_mon = QtWidgets.QPushButton("📅 Monthly List")
        self.b_exp = QtWidgets.QPushButton("📄 Export PDF")
        self.b_act = QtWidgets.QPushButton("🟢 Active Members")
        self.b_die = QtWidgets.QPushButton("🔴 Expired Members")

        nav_buttons = [
            self.b_mem, self.b_app, self.b_att, self.b_fees, 
            self.b_mon, self.b_exp, self.b_act, self.b_die
        ]

        for b in nav_buttons:
            b.setMinimumHeight(40)
            b.setCursor(QtCore.Qt.PointingHandCursor)
            sidebar.addWidget(b)

        sidebar.addSpacing(15)
        self.b_usr = QtWidgets.QPushButton("👥 User Management")
        self.b_usr.setMinimumHeight(40)
        sidebar.addWidget(self.b_usr)

        self.b_brief = QtWidgets.QPushButton("📄 Yesterday's Brief")
        self.b_brief.clicked.connect(self.show_brief)
        sidebar.addWidget(self.b_brief)
        
        self.b_bkp = QtWidgets.QPushButton("☁️ Cloud Backup")
        self.b_bkp.setStyleSheet("background:#006600;font-weight:bold")
        self.b_bkp.clicked.connect(self.open_backup)
        sidebar.addWidget(self.b_bkp)

        sidebar.addStretch()
        self.b_out = QtWidgets.QPushButton("🚪 Logout")
        self.b_out.clicked.connect(self.logout)
        sidebar.addWidget(self.b_out)

        sw = QtWidgets.QWidget()
        sw.setLayout(sidebar)
        sw.setMaximumWidth(250)
        sw.setStyleSheet("border-right:2px solid #333;background:#111")
        layout.addWidget(sw)

        # --- CONTENT AREA (Stacked Widget) ---
        self.stacked = QtWidgets.QStackedWidget()
        layout.addWidget(self.stacked, 1)
        
        self.p_mem = QtWidgets.QWidget()
        self.init_member_page()
        self.stacked.addWidget(self.p_mem)
        
        self.p_app = QtWidgets.QWidget()
        self.init_approval_page()
        self.stacked.addWidget(self.p_app)
        
        self.p_att = QtWidgets.QWidget()
        self.init_attendance_page()
        self.stacked.addWidget(self.p_att)
        
        self.p_fees = QtWidgets.QWidget()
        self.init_fees_page()
        self.stacked.addWidget(self.p_fees)
        
        self.p_usr = QtWidgets.QWidget()
        self.init_user_page()
        self.stacked.addWidget(self.p_usr)
        
        self.p_act = QtWidgets.QWidget()
        self.init_status_page(self.p_act, "Active")
        self.stacked.addWidget(self.p_act)
        
        self.p_die = QtWidgets.QWidget()
        self.init_status_page(self.p_die, "Expired")
        self.stacked.addWidget(self.p_die)

        # Navigation Signals
        self.b_mem.clicked.connect(lambda: self.stacked.setCurrentWidget(self.p_mem))
        self.b_app.clicked.connect(lambda: [self.stacked.setCurrentWidget(self.p_app), self.load_approvals()])
        self.b_att.clicked.connect(lambda: self.stacked.setCurrentWidget(self.p_att))
        self.b_fees.clicked.connect(lambda: [self.stacked.setCurrentWidget(self.p_fees), self.load_fee_table()])
        self.b_usr.clicked.connect(lambda: [self.stacked.setCurrentWidget(self.p_usr), self.load_users_table()])
        self.b_act.clicked.connect(lambda: self.load_status_page(self.p_act, "Active"))
        self.b_die.clicked.connect(lambda: self.load_status_page(self.p_die, "Expired"))
        self.b_mon.clicked.connect(self.monthly)
        self.b_exp.clicked.connect(self.export_pdf)
        
        # Refresh lists when a member is saved
        self.member_saved.connect(lambda: self.load_status_page(self.p_act, "Active"))

    # --- MEMBER MANAGEMENT ---
    def init_member_page(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.p_mem)
        layout.addWidget(QtWidgets.QLabel("👤 Search, Edit or Ban Members"))
        
        top = QtWidgets.QHBoxLayout()
        self.ph_lbl = QtWidgets.QLabel("📷 No Photo")
        self.ph_lbl.setFixedSize(150, 150)
        self.ph_lbl.setStyleSheet("border:2px solid #444;background:black")
        self.ph_lbl.setAlignment(QtCore.Qt.AlignCenter)

        # Photo Buttons
        btns = QtWidgets.QVBoxLayout()
        b1 = QtWidgets.QPushButton("📁 Upload")
        b1.clicked.connect(self.upl)

        b_cam = QtWidgets.QPushButton("📷 Take Photo")
        b_cam.setStyleSheet("background: #0044cc; color: white;")
        b_cam.clicked.connect(self.take_photo)

        b2 = QtWidgets.QPushButton("🗑️ Clear")
        b2.clicked.connect(self.clr_ph)
        btns.addWidget(b1)
        btns.addWidget(b_cam)
        btns.addWidget(b2)
        top.addWidget(self.ph_lbl)
        top.addLayout(btns)
        top.addStretch()
        layout.addLayout(top)

        # Search Bar
        h_search = QtWidgets.QHBoxLayout()
        self.id = QtWidgets.QLineEdit()
        self.id.setPlaceholderText("ID to Search/Add")
        
        b_src = QtWidgets.QPushButton("🔍 Search ID")
        b_src.setStyleSheet("background:#0044cc;font-weight:bold")
        b_src.clicked.connect(self.on_search)
        
        self.b_renew = QtWidgets.QPushButton("💰 Update Fee")
        self.b_renew.setStyleSheet("background:#d4af37;color:black;font-weight:bold")
        self.b_renew.clicked.connect(self.open_renew)
        
        self.b_ban = QtWidgets.QPushButton("🚫 TERMINATE")
        self.b_ban.setStyleSheet("background:#500;color:white;font-weight:bold;border:1px solid red")
        self.b_ban.clicked.connect(self.do_ban)
        
        h_search.addWidget(self.id)
        h_search.addWidget(b_src)
        h_search.addWidget(self.b_renew)
        h_search.addWidget(self.b_ban)
        
        form = QtWidgets.QFormLayout()
        form.addRow("ID / Action*", h_search)

        # Member Details Form
        self.nm = QtWidgets.QLineEdit()
        self.ph = QtWidgets.QLineEdit()
        self.bl = QtWidgets.QLineEdit()
        self.cnic = QtWidgets.QLineEdit()
        self.g = QtWidgets.QComboBox()
        self.g.addItems(["Select Gender", "Male", "Female"])
        
        form.addRow("Name*", self.nm)
        form.addRow("Phone", self.ph)
        form.addRow("Blood", self.bl)
        form.addRow("Gender*", self.g)
        form.addRow("CNIC*", self.cnic)
        
        self.pkg = QtWidgets.QComboBox()
        self.pkg.addItems(["Bronze", "Silver", "Gold", "Platinum"])
        form.addRow("Package*", self.pkg)

        # Date Selection
        td = datetime.date.today()
        self.dd = QtWidgets.QSpinBox()
        self.dd.setRange(1, 31)
        self.dd.setValue(td.day)
        
        self.mm = QtWidgets.QComboBox()
        self.mm.addItems([str(i) for i in range(1, 13)])
        self.mm.setCurrentIndex(td.month - 1)
        
        self.yy = QtWidgets.QComboBox()
        self.yy.addItems([str(y) for y in range(td.year - 20, td.year + 6)])
        self.yy.setCurrentText(str(td.year))
        
        dH = QtWidgets.QHBoxLayout()
        dH.addWidget(self.dd)
        dH.addWidget(self.mm)
        dH.addWidget(self.yy)
        form.addRow("Join Date:", dH)

        self.dur = QtWidgets.QComboBox()
        self.dur.addItems(["1 Month", "3 Months", "6 Months", "12 Months"])
        form.addRow("Months:", self.dur)

        # Form Actions
        bS = QtWidgets.QPushButton("💾 Save (Create / Update All)")
        bS.setStyleSheet("background:#006600")
        bS.clicked.connect(self.on_save)
        
        bC = QtWidgets.QPushButton("🧹 Clear")
        bC.clicked.connect(self.clr_frm)
        
        bH = QtWidgets.QHBoxLayout()
        bH.addWidget(bS)
        bH.addWidget(bC)
        form.addRow(bH)
        layout.addLayout(form)

        # Search Result Display
        self.res_badge = QtWidgets.QLabel("STATUS")
        self.res_badge.setAlignment(QtCore.Qt.AlignCenter)
        self.res_badge.setStyleSheet("background:#333;font-weight:bold;padding:5px")
        layout.addWidget(self.res_badge)
        
        self.res = QtWidgets.QTextEdit()
        self.res.setReadOnly(True)
        self.res.setMaximumHeight(100)
        layout.addWidget(self.res)

    def do_ban(self) -> None:
        mid = self.id.text().strip()
        if not mid: 
            QtWidgets.QMessageBox.warning(self, "Error", "Search ID first")
            return
            
        if QtWidgets.QMessageBox.question(
            self, "Confirm Ban", f"Terminate {mid}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) == QtWidgets.QMessageBox.Yes:
            try:
                update_member_status(mid, "BANNED")
                QtWidgets.QMessageBox.information(self, "Terminated", f"Member {mid} Banned.")
                self.on_search()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def on_save(self) -> None:
        if not self.id.text() or not self.nm.text(): 
            return
            
        try:
            clean_id = self.id.text().strip()
            pp = None
            
            # Handle Photo Copying
            if self.current_photo_path and os.path.exists(self.current_photo_path):
                if not config.PHOTOS_FOLDER.exists():
                    config.PHOTOS_FOLDER.mkdir(parents=True, exist_ok=True)
                    
                dest = config.PHOTOS_FOLDER / f"{clean_id}{Path(self.current_photo_path).suffix}"
                
                # Only copy if it's not already in the destination
                if Path(self.current_photo_path).resolve() != dest.resolve():
                    shutil.copy2(self.current_photo_path, dest)
                    
                pp = str(dest)
                self.current_photo_path = pp 

            # Calculate Dates
            jd = datetime.date(int(self.yy.currentText()), int(self.mm.currentText()), self.dd.value())
            months_int = int(self.dur.currentText().split()[0])
            ed = add_months(jd, months_int)
            
            # Preserve existing status or default to Active
            st = "Active"
            exist = get_member_by_id(clean_id)
            if exist: 
                st = exist.get('status', 'Active')

            m = Member(
                id=clean_id, 
                name=self.nm.text(), 
                phone=self.ph.text(), 
                blood=self.bl.text(),
                gender=self.g.currentText(), 
                cnic=self.cnic.text(), 
                day=jd.day, 
                month=jd.month, 
                year=jd.year,
                membership_months=months_int, 
                package=self.pkg.currentText(),
                end_date=str(ed), 
                status=st, 
                photo_path=pp
            )
            
            w = SaveWorker(m)
            w.signals.finished.connect(self._saved)
            self.pool.start(w)
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def _saved(self, path: str) -> None:
        QtWidgets.QMessageBox.information(self, "Success", f"Saved: {path}")
        self.member_saved.emit()
        
        # Refresh photo display
        if self.current_photo_path:
            self.ph_lbl.setPixmap(
                QtGui.QPixmap(self.current_photo_path).scaled(150, 150, QtCore.Qt.KeepAspectRatio)
            )

    def on_search(self) -> None:
        self.stacked.setCurrentWidget(self.p_mem)
        q = self.id.text().strip() or self.nm.text().strip()
        if not q: 
            return
            
        w = SearchWorker(q, is_admin=True)
        w.signals.finished.connect(self._found)
        self.pool.start(w)

    def _found(self, d: dict) -> None:
        if not d.get("matches"): 
            self.res.setPlainText("Not found")
            self.res_badge.setText("UNKNOWN")
            self.res_badge.setStyleSheet("background:#333")
            return
            
        p = d.get("parsed")
        if p:
            st = p.get('status', 'Expired')
            self.res.setPlainText(f"Found: {p.get('name')}\nStatus: {st}\nExpires: {p.get('end_date')}")
            
            # Badge Color Logic
            c = "green" if st.lower() == "active" else "red"
            if st.lower() == "banned":
                c = "red"
            elif st.lower() == "pending":
                c = "orange"
                
            self.res_badge.setText(f"{'✅' if c == 'green' else '❌'} {st.upper()}")
            self.res_badge.setStyleSheet(f"background:{c};color:white;font-weight:bold;padding:5px")
            
            # Fill Form
            self.id.setText(p.get('id'))
            self.nm.setText(p.get('name'))
            self.ph.setText(p.get('phone'))
            self.bl.setText(p.get('blood'))
            self.cnic.setText(p.get('cnic'))
            
            # Load Photo
            if p.get('photo_path') and Path(p['photo_path']).exists():
                self.current_photo_path = p['photo_path']
                self.ph_lbl.setPixmap(
                    QtGui.QPixmap(p['photo_path']).scaled(150, 150, QtCore.Qt.KeepAspectRatio)
                )
            else:
                self.ph_lbl.clear()
                self.ph_lbl.setText("No Photo")
                self.current_photo_path = None

    def open_renew(self) -> None:
        mid = self.id.text().strip()
        if not mid: 
            QtWidgets.QMessageBox.warning(self, "Error", "Search for an ID first")
            return
            
        d = get_member_by_id(mid)
        exp = d.get('end_date', '') if d else None
        
        dlg = RenewDialog(self, exp)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            data = dlg.result_data
            try:
                renew_membership(mid, data['start_date'], data['end_date'], data['months'])
                QtWidgets.QMessageBox.information(self, "Success", "Updated")
                self.on_search()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    # --- APPROVALS ---
    def init_approval_page(self) -> None:
        l = QtWidgets.QVBoxLayout(self.p_app)
        l.addWidget(QtWidgets.QLabel("🔔 Pending Member Approvals"))
        
        self.app_table = QtWidgets.QTableWidget()
        self.app_table.setColumnCount(5)
        self.app_table.setHorizontalHeaderLabels(["ID", "Name", "Gender", "Join Date", "Action"])
        self.app_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.app_table.setStyleSheet(
            "QHeaderView::section { background-color: #333; color: white; padding: 5px; } "
            "QTableWidget { gridline-color: #444; }"
        )
        
        btn_refresh = QtWidgets.QPushButton("🔄 Refresh List")
        btn_refresh.clicked.connect(self.load_approvals)
        l.addWidget(self.app_table)
        l.addWidget(btn_refresh)

    def load_approvals(self) -> None:
        self.app_table.setRowCount(0)
        pending = get_pending_members()
        
        for i, m in enumerate(pending):
            self.app_table.insertRow(i)
            self.app_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(m['id'])))
            self.app_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(m['name'])))
            self.app_table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(m.get('gender', '-'))))
            self.app_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(m['date'])))
            
            w = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            
            b_ok = QtWidgets.QPushButton("✅ Approve")
            b_ok.setStyleSheet("background: #006600; font-size:11px;")
            b_ok.clicked.connect(lambda c, x=m['id']: self.do_approve(x))
            
            b_no = QtWidgets.QPushButton("🗑️ Reject")
            b_no.setStyleSheet("background: #b71c1c; font-size:11px;")
            b_no.clicked.connect(lambda c, x=m['id']: self.do_reject(x))
            
            h.addWidget(b_ok)
            h.addWidget(b_no)
            self.app_table.setCellWidget(i, 4, w)

    def do_approve(self, mid: str) -> None:
        try:
            update_member_status(mid, "Active")
            self.load_approvals()
            QtWidgets.QMessageBox.information(self, "Success", f"Member {mid} Approved & Added to Active List!")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def do_reject(self, mid: str) -> None:
        if QtWidgets.QMessageBox.question(
            self, "Confirm", f"Reject {mid}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) == QtWidgets.QMessageBox.Yes:
            delete_member(mid)
            self.load_approvals()

    # --- FEES ---
    def init_fees_page(self) -> None:
        l = QtWidgets.QVBoxLayout(self.p_fees)
        l.addWidget(QtWidgets.QLabel("💰 Fee Update History"))
        
        self.fee_table = QtWidgets.QTableWidget()
        self.fee_table.setColumnCount(4)
        self.fee_table.setHorizontalHeaderLabels(["Time", "Staff Member", "Member ID", "Months Added"])
        self.fee_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.fee_table.setStyleSheet(
            "QHeaderView::section { background-color: #333; color: white; padding: 5px; } "
            "QTableWidget { gridline-color: #444; }"
        )
        
        btn_refresh = QtWidgets.QPushButton("🔄 Refresh Logs")
        btn_refresh.clicked.connect(self.load_fee_table)
        l.addWidget(self.fee_table)
        l.addWidget(btn_refresh)

    def load_fee_table(self) -> None:
        self.fee_table.setRowCount(0)
        logs = get_fee_logs()
        
        for i, data in enumerate(logs):
            self.fee_table.insertRow(i)
            self.fee_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(data[1])))
            self.fee_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(data[2])))
            self.fee_table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(data[3])))
            self.fee_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(data[4])))

    # --- ATTENDANCE ---
    def init_attendance_page(self) -> None:
        l = QtWidgets.QVBoxLayout(self.p_att)
        l.addWidget(QtWidgets.QLabel("⏱️ Security"))
        
        self.ai_lbl = QtWidgets.QLabel("🤖 AI: Gathering...")
        self.ai_lbl.setStyleSheet("color:#0af")
        l.addWidget(self.ai_lbl)

        gb = QtWidgets.QGroupBox("Check-In")
        hb = QtWidgets.QHBoxLayout(gb)
        self.att_in = QtWidgets.QLineEdit()
        self.att_in.setPlaceholderText("ID")
        self.att_in.returnPressed.connect(self.chk_in)
        
        b = QtWidgets.QPushButton("Check In")
        b.clicked.connect(self.chk_in)
        b.setStyleSheet("background:#006600")
        
        hb.addWidget(self.att_in)
        hb.addWidget(b)
        l.addWidget(gb)

        inf = QtWidgets.QGroupBox("Identity")
        v = QtWidgets.QVBoxLayout(inf)
        self.c_ph = QtWidgets.QLabel("Waiting")
        self.c_ph.setFixedSize(200, 200)
        self.c_ph.setStyleSheet("border:3px solid #333;background:black")

        # Details
        self.c_nm = QtWidgets.QLabel("-")
        self.c_nm.setStyleSheet("font-size:20px;font-weight:bold;color:#fc0")
        
        self.c_pkg = QtWidgets.QLabel("Package: -")
        self.c_pkg.setStyleSheet("font-size:14px;color:#ddd")
        
        self.c_st = QtWidgets.QLabel("-")
        self.c_st.setStyleSheet("font-size:16px;font-weight:bold")
        
        self.c_ex = QtWidgets.QLabel("Expires: -")
        self.c_ex.setStyleSheet("font-size:14px;color:#aaa")

        hh = QtWidgets.QHBoxLayout()
        hh.addStretch()
        hh.addWidget(self.c_ph)
        hh.addStretch()
        
        v.addLayout(hh)
        v.addWidget(self.c_nm, alignment=QtCore.Qt.AlignCenter)
        v.addWidget(self.c_pkg, alignment=QtCore.Qt.AlignCenter)
        v.addWidget(self.c_st, alignment=QtCore.Qt.AlignCenter)
        v.addWidget(self.c_ex, alignment=QtCore.Qt.AlignCenter)

        l.addWidget(inf)
        l.addStretch()

    def chk_in(self) -> None:
        mid = self.att_in.text().strip()
        if not mid: 
            return
            
        d = get_member_by_id(mid)

        if not d:
            QtWidgets.QMessageBox.warning(self, "Unknown", "ID not found")
            self.att_in.clear()
            self.c_nm.setText("Unknown")
            self.c_st.setText("NOT FOUND")
            self.c_pkg.setText("Package: -")
            self.c_ex.setText("Expires: -")
            return

        # Update UI
        self.c_nm.setText(d.get('name'))
        self.c_pkg.setText(f"Package: {d.get('package', 'Bronze')}")
        self.c_ex.setText(f"Expires: {d.get('end_date', '-')}")

        st = d.get('status', 'Expired')
        self.c_st.setText(st)
        self.c_st.setStyleSheet(
            f"font-size:16px;font-weight:bold;color:{'#0f0' if st.lower() == 'active' else '#f00'}"
        )

        if d.get('photo_path'):
            self.c_ph.setPixmap(
                QtGui.QPixmap(d['photo_path']).scaled(200, 200, QtCore.Qt.KeepAspectRatio)
            )
        else:
            self.c_ph.clear()
            self.c_ph.setText("No Photo")

        mark_attendance(mid)
        self.att_in.clear()
        
        ai = GymAI()
        self.ai_lbl.setText(f"AI: {ai.predict_peak_hours()}")

    # --- USER MANAGEMENT ---
    def init_user_page(self) -> None:
        ml = QtWidgets.QHBoxLayout(self.p_usr)
        lw = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(lw)
        
        l.addWidget(QtWidgets.QLabel("➕ Create User"))
        f = QtWidgets.QFormLayout()
        
        self.nu = QtWidgets.QLineEdit()
        self.npa = QtWidgets.QLineEdit()
        self.nr = QtWidgets.QComboBox()
        self.nr.addItems(["user", "admin"])
        
        self.ng = QtWidgets.QComboBox()
        self.ng.addItems(["Select Gender", "Male", "Female"])
        
        f.addRow("User", self.nu)
        f.addRow("Pass", self.npa)
        f.addRow("Role", self.nr)
        f.addRow("Gender", self.ng)
        
        b = QtWidgets.QPushButton("Create")
        b.clicked.connect(self.do_create_user)
        
        l.addLayout(f)
        l.addWidget(b)
        l.addStretch()
        
        rw = QtWidgets.QWidget()
        r = QtWidgets.QVBoxLayout(rw)
        r.addWidget(QtWidgets.QLabel("📋 Staff"))
        
        self.ut = QtWidgets.QTableWidget()
        self.ut.setColumnCount(5)
        self.ut.setHorizontalHeaderLabels(["ID", "Name", "Role", "Gender", "Action"])
        self.ut.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.ut.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ut.cellDoubleClicked.connect(self.edit_user_click)
        
        r.addWidget(self.ut)
        ml.addWidget(lw, 1)
        ml.addWidget(rw, 2)

    def load_users_table(self) -> None:
        self.ut.setRowCount(0)
        us = get_all_users()
        
        for i, u in enumerate(us):
            self.ut.insertRow(i)
            self.ut.setItem(i, 0, QtWidgets.QTableWidgetItem(str(u[0])))
            self.ut.setItem(i, 1, QtWidgets.QTableWidgetItem(str(u[1])))
            self.ut.setItem(i, 2, QtWidgets.QTableWidgetItem(str(u[2])))
            self.ut.setItem(i, 3, QtWidgets.QTableWidgetItem(str(u[3])))
            
            if u[2] == 'admin' and u[1] == 'admin':
                btn = QtWidgets.QLabel("(Protected)")
            else:
                btn = QtWidgets.QPushButton("Del")
                btn.setStyleSheet("background:#b00")
                btn.clicked.connect(lambda c, x=u[0]: self.del_user(x))
            self.ut.setCellWidget(i, 4, btn)

    def do_create_user(self) -> None:
        try:
            g = self.ng.currentText() if self.nr.currentText() == "user" else None
            create_user(self.nu.text(), self.npa.text(), self.nr.currentText(), g)
            QtWidgets.QMessageBox.information(self, "Success", "Created")
            self.load_users_table()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def del_user(self, uid: int) -> None:
        if QtWidgets.QMessageBox.question(self, "Confirm", "Delete?") == QtWidgets.QMessageBox.Yes:
            delete_user_by_id(uid)
            self.load_users_table()

    def edit_user_click(self, r: int, c: int) -> None:
        uid = self.ut.item(r, 0).text()
        rl = self.ut.item(r, 2).text()
        gd = self.ut.item(r, 3).text()
        
        d = QtWidgets.QDialog(self)
        d.setStyleSheet("background:#111;color:white")
        f = QtWidgets.QFormLayout(d)
        
        np = QtWidgets.QLineEdit()
        
        nr = QtWidgets.QComboBox()
        nr.addItems(["user", "admin"])
        nr.setCurrentText(rl)
        
        ng = QtWidgets.QComboBox()
        ng.addItems(["Male", "Female"])
        ng.setCurrentText(gd if gd != 'None' else 'Male')
        
        f.addRow("New Pass", np)
        f.addRow("Role", nr)
        f.addRow("Gender", ng)
        
        b = QtWidgets.QPushButton("Update")
        b.clicked.connect(lambda: [
            update_user(uid, np.text() or None, nr.currentText(), ng.currentText()), 
            d.accept(),
            self.load_users_table()
        ])
        f.addWidget(b)
        d.exec()

    # --- UTILS ---
    def upl(self) -> None:
        f, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Photo", "", "Images (*.png *.jpg *.jpeg)"
        )
        if f:
            self.current_photo_path = f
            self.ph_lbl.setPixmap(
                QtGui.QPixmap(f).scaled(150, 150, QtCore.Qt.KeepAspectRatio)
            )

    def take_photo(self) -> None:
        dlg = CameraDialog(self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.current_photo_path = dlg.captured_path
            self.ph_lbl.setPixmap(
                QtGui.QPixmap(self.current_photo_path).scaled(150, 150, QtCore.Qt.KeepAspectRatio)
            )

    def clr_ph(self) -> None:
        self.current_photo_path = None
        self.ph_lbl.setText("No Photo")

    def clr_frm(self) -> None:
        self.id.clear()
        self.nm.clear()
        self.clr_ph()
        self.res.clear()
        self.res_badge.setText("STATUS")
        self.res_badge.setStyleSheet("background:#333")

    def init_status_page(self, p: QtWidgets.QWidget, s: str) -> None:
        l = QtWidgets.QVBoxLayout(p)
        l.addWidget(QtWidgets.QLabel(f"{s} Members"))
        t = QtWidgets.QTextEdit()
        t.setReadOnly(True)
        l.addWidget(t)
        setattr(self, f"t_{s}", t)

    def load_status_page(self, p: QtWidgets.QWidget, s: str) -> None:
        self.stacked.setCurrentWidget(p)
        t = getattr(self, f"t_{s}")
        t.setPlainText("Loading...")
        w = StatusListWorker(s)
        w.signals.finished.connect(lambda txt: t.setPlainText(txt))
        self.pool.start(w)

    def monthly(self) -> None:
        w = MonthlyListWorker(int(self.yy.currentText()), int(self.mm.currentText()))
        w.signals.finished.connect(lambda t: QtWidgets.QMessageBox.information(self, "List", t))
        self.pool.start(w)

    def export_pdf(self) -> None:
        y = int(self.yy.currentText())
        m = int(self.mm.currentText())
        f = config.BASE_FOLDER / str(y) / month_name(m) / "monthly_members.txt"
        
        if not f.exists(): 
            return
            
        s, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export", f"R_{m}_{y}.pdf", "PDF (*.pdf)")
        if s:
            c = canvas.Canvas(s, pagesize=A4)
            yy = 800
            c.drawString(50, yy, f"Report {m}/{y}")
            yy -= 30
            
            for l in f.read_text(encoding='utf-8').splitlines():
                c.drawString(50, yy, l)
                yy -= 15
                if yy < 50: 
                    c.showPage()
                    yy = 800
            
            c.save()
            QtWidgets.QMessageBox.information(self, "Done", "Exported")

    def show_brief(self) -> None:
        txt = generate_daily_brief(datetime.date.today() - datetime.timedelta(days=1))
        d = QtWidgets.QDialog(self)
        d.resize(500, 600)
        d.setStyleSheet("background:#111;color:white")
        l = QtWidgets.QVBoxLayout(d)
        t = QtWidgets.QTextEdit()
        t.setMarkdown(txt)
        l.addWidget(t)
        d.exec()

    def open_backup(self) -> None:
        BackupDialog(self).exec()

    def logout(self) -> None:
        self.logout_signal.emit()
        self.close()

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow{background:#0c0c0c;color:white}
            QLineEdit,QComboBox,QSpinBox,QTextEdit{padding:8px;background:#222;color:white;border:1px solid #444}
            QPushButton{background:#333;color:white;padding:8px}
            QPushButton:hover{background:#fc0;color:black}
        """)