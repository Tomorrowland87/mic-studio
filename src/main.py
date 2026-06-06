import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QFrame, QMessageBox, QSystemTrayIcon,
    QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction, QPixmap, QPainter, QColor

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
from engine import Engine


def make_tray_icon(green):
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(76, 175, 80) if green else QColor(244, 67, 54)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, 14, 14)
    painter.end()
    return QIcon(pixmap)


class MicStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = Engine()
        self.tray = None
        self.tray_menu = None
        self.active_preset_label = None
        self._setup_ui()
        self._setup_tray()
        self._load_presets()

    def _setup_ui(self):
        self.setWindowTitle("MicStudio")
        self.setFixedSize(440, 340)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("MicStudio")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = title.font()
        f.setPointSize(20)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        subtitle = QLabel("Microphone Audio Processor")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        self.status_label = QLabel("Status: checking...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.active_preset_label = QLabel("Active: none")
        self.active_preset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_preset_label.setStyleSheet("color: #666;")
        layout.addWidget(self.active_preset_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        layout.addSpacing(4)

        preset_row = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setFont(QFont("", 11))
        preset_row.addWidget(preset_label)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(220)
        preset_row.addWidget(self.preset_combo)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; color: white;
                padding: 6px 18px; border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #43a047; }
            QPushButton:disabled { background-color: #888; }
        """)
        self.apply_btn.clicked.connect(self._apply_preset)
        preset_row.addWidget(self.apply_btn)
        layout.addLayout(preset_row)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()

        self.bypass_btn = QPushButton("Toggle Bypass")
        self.bypass_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px; border-radius: 4px;
                background-color: #ff9800; color: white; font-weight: bold;
            }
            QPushButton:hover { background-color: #f57c00; }
        """)
        self.bypass_btn.clicked.connect(self._toggle_bypass)
        btn_row.addWidget(self.bypass_btn)

        self.open_ee_btn = QPushButton("Open EasyEffects")
        self.open_ee_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px; border-radius: 4px;
                background-color: #2196f3; color: white; font-weight: bold;
            }
            QPushButton:hover { background-color: #1976d2; }
        """)
        self.open_ee_btn.clicked.connect(self._open_ee)
        btn_row.addWidget(self.open_ee_btn)

        self.quit_btn = QPushButton("Quit")
        self.quit_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px; border-radius: 4px;
                background-color: #f44336; color: white; font-weight: bold;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.quit_btn.clicked.connect(self._quit_app)
        btn_row.addWidget(self.quit_btn)

        layout.addLayout(btn_row)

        layout.addStretch()

        footer = QLabel("v1.0 — uses EasyEffects + PipeWire")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(footer)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(make_tray_icon(False))
        self.tray.setToolTip("MicStudio")

        self.tray_menu = QMenu()

        self.tray_menu.addAction("Show Window", self.showNormal)
        self.tray_menu.addSeparator()

        self.tray_preset_menu = self.tray_menu.addMenu("Switch Preset")
        self.tray_menu.addSeparator()

        self.tray_bypass_action = QAction("Toggle Bypass", self)
        self.tray_bypass_action.triggered.connect(self._toggle_bypass)
        self.tray_menu.addAction(self.tray_bypass_action)

        self.tray_menu.addSeparator()
        self.tray_menu.addAction("Quit", self._quit_app)

        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _update_tray_menu(self):
        if not self.tray_menu:
            return
        self.tray_preset_menu.clear()
        for name in self.engine.get_preset_names():
            action = self.tray_preset_menu.addAction(name)
            action.triggered.connect(lambda checked, n=name: self._apply_preset_from_tray(n))

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def _load_presets(self):
        preset_dir = os.path.join(APP_DIR, "presets")
        self.engine.load_presets(preset_dir)
        names = self.engine.get_preset_names()
        self.preset_combo.addItems(names)
        if names:
            self.preset_combo.setCurrentIndex(0)
        self._update_tray_menu()
        self._update_status()

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(3000)

    def _update_status(self):
        running = self.engine.is_running()
        if running:
            self.status_label.setText("Status: EasyEffects running")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            if self.tray:
                self.tray.setIcon(make_tray_icon(True))
                self.tray.setToolTip("MicStudio — Active")
        else:
            self.status_label.setText("Status: EasyEffects not running")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            if self.tray:
                self.tray.setIcon(make_tray_icon(False))
                self.tray.setToolTip("MicStudio — Stopped")

    def _set_active_preset(self, name):
        if self.active_preset_label:
            self.active_preset_label.setText(f"Active: {name}")
            self.active_preset_label.setStyleSheet("color: #4caf50; font-weight: bold;")

    def _apply_preset(self):
        name = self.preset_combo.currentText()
        if not name:
            return
        self.apply_btn.setEnabled(False)
        self.apply_btn.setText("Applying...")
        QApplication.processEvents()
        ok = self.engine.apply_preset(name)
        self.apply_btn.setEnabled(True)
        self.apply_btn.setText("Apply")
        if ok:
            self._update_status()
            self._set_active_preset(name)
        else:
            QMessageBox.warning(self, "Error", f"Failed to apply preset: {name}")

    def _apply_preset_from_tray(self, name):
        idx = self.preset_combo.findText(name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.engine.apply_preset(name)
        self._update_status()
        self._set_active_preset(name)

    def _toggle_bypass(self):
        self.engine.toggle_bypass()
        self._update_status()

    def _open_ee(self):
        import subprocess
        subprocess.Popen(["easyeffects"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

    def _quit_app(self):
        if self.tray:
            self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if self.tray and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "MicStudio",
                "Still running in system tray",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MicStudio")
    app.setQuitOnLastWindowClosed(False)
    w = MicStudio()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
