import cv2
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path
from typing import Optional


class CameraDialog(QtWidgets.QDialog):
    """
    A dialog that accesses the default webcam to capture a member's photo.
    Saves the image temporarily to the user's home directory.
    """
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("📷 Take Photo")
        self.resize(600, 500)
        
        self.captured_path: Optional[str] = None
        self.timer = QtCore.QTimer()
        self.cap: Optional[cv2.VideoCapture] = None
        self.current_frame = None
        
        self.init_ui()

        # Start camera automatically
        self.start_camera()

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Camera Feed Display
        self.lbl_feed = QtWidgets.QLabel("Starting Camera...")
        self.lbl_feed.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_feed.setStyleSheet("background: black; color: white; font-size: 18px;")
        self.lbl_feed.setMinimumSize(600, 400)
        layout.addWidget(self.lbl_feed)

        # Capture Button
        btn = QtWidgets.QPushButton("📸 CAPTURE")
        btn.setFixedHeight(60)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background: #b71c1c; color: white; font-weight: bold; font-size: 18px; border: none; }
            QPushButton:hover { background: #ff0000; }
        """)
        btn.clicked.connect(self.capture_image)
        layout.addWidget(btn)

    def start_camera(self) -> None:
        # 0 is usually the default webcam
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QtWidgets.QMessageBox.warning(self, "Error", "Could not access webcam.\nPlease check connection.")
            self.reject()
            return

        # Update frame every 30ms (approx 30 FPS)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self) -> None:
        if not self.cap:
            return
            
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            # Convert OpenCV (BGR) to Qt (RGB)
            rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w

            q_img = QtGui.QImage(rgb_img.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)

            # Scale to fit label while keeping aspect ratio
            pixmap = QtGui.QPixmap.fromImage(q_img)
            self.lbl_feed.setPixmap(pixmap.scaled(self.lbl_feed.size(), QtCore.Qt.KeepAspectRatio))

    def capture_image(self) -> None:
        if hasattr(self, 'current_frame') and self.current_frame is not None:
            # Save to a temporary file in user's home directory
            # Using Path.home() ensures no personal path is hardcoded in the repo
            temp_path = Path.home() / "solidgym_temp_capture.jpg"
            cv2.imwrite(str(temp_path), self.current_frame)

            self.captured_path = str(temp_path)
            self.accept()  # Close dialog with "Success" result

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.stop_camera()
        event.accept()

    def stop_camera(self) -> None:
        self.timer.stop()
        if self.cap:
            self.cap.release()