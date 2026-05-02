import sys
import os
import json
import threading

if getattr(sys, 'frozen', False):
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QGroupBox, QSpinBox, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor, QCursor

from automation import run, open_browser, INFO_FILE, INFO_TEMPLATE


class LogStream(QObject):
    message = pyqtSignal(str)

    def write(self, text):
        if text.strip():
            self.message.emit(text)

    def flush(self):
        pass


class BotWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url, categories, stop_event, version_main=146, auto_proceed=False, driver=None, band_url=None, checkout_code=None, sale_type="ARTIST PRESALE"):
        super().__init__()
        self.url = url
        self.categories = categories
        self.stop_event = stop_event
        self.version_main = version_main
        self.auto_proceed = auto_proceed
        self.driver = driver
        self.band_url = band_url
        self.checkout_code = checkout_code
        self.sale_type = sale_type

    def run(self):
        stream = LogStream()
        stream.message.connect(self.log)
        sys.stdout = stream
        try:
            run(self.url, target_categories=self.categories, stop_event=self.stop_event, version_main=self.version_main, auto_proceed=self.auto_proceed, driver=self.driver, band_url=self.band_url, checkout_code=self.checkout_code, sale_type=self.sale_type)
        except Exception as e:
            self.log.emit(f"[ERROR] {e}")
        finally:
            sys.stdout = sys.__stdout__
            self.finished.emit()


class BrowserWorker(QThread):
    log = pyqtSignal(str)
    driver_ready = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(self, stop_event, version_main=146):
        super().__init__()
        self.stop_event = stop_event
        self.version_main = version_main
        self._driver = None

    def run(self):
        stream = LogStream()
        stream.message.connect(self.log)
        sys.stdout = stream
        try:
            self._driver = open_browser(version_main=self.version_main)
            self.driver_ready.emit(self._driver)
            self.stop_event.wait()
        except Exception as e:
            self.log.emit(f"[ERROR] {e}")
        finally:
            if self._driver:
                try:
                    self._driver.quit()
                except Exception:
                    pass
            sys.stdout = sys.__stdout__
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket Bot [sodtix.com]")
        self.setMinimumSize(700, 600)
        self.resize(750, 900)
        self._worker = None
        self._browser_worker = None
        self._stop_event = None
        self._browser_stop_event = None
        self._driver = None
        self._build_ui()
        self._check_info_file()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Config group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)

        def add_field(label_text, widget):
            config_layout.addWidget(QLabel(label_text))
            config_layout.addWidget(widget)

        self.band_url_input = QLineEdit()
        self.band_url_input.setPlaceholderText("https://5sos.com/... — leave blank for direct sodtix URL")
        add_field("Band Site URL (optional)", self.band_url_input)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://sodtix.com/event/... (required if Band Site URL blank)")
        add_field("Sodtix Event URL", self.url_input)

        self.cats_input = QLineEdit()
        self.cats_input.setPlaceholderText("e.g. TRIBUNE 1, TRIBUNE 2")
        add_field("Target Categories (priority, comma-separated)", self.cats_input)

        self.checkout_code_input = QLineEdit()
        self.checkout_code_input.setPlaceholderText("Leave blank if none")
        add_field("Voucher / Presale Code (optional)", self.checkout_code_input)

        self.sale_type_input = QComboBox()
        self.sale_type_input.addItems(["Artist Presale", "General Sales"])
        self.sale_type_input.setFixedWidth(200)
        add_field("Sale Type", self.sale_type_input)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: green;")
        config_layout.addWidget(self.info_label)

        layout.addWidget(config_group)

        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout(settings_group)
        settings_layout.setSpacing(20)

        self.ver_input = QSpinBox()
        self.ver_input.setRange(100, 200)
        self.ver_input.setValue(146)
        self.ver_input.setFixedWidth(80)
        ver_col = QVBoxLayout()
        ver_col.setSpacing(3)
        ver_col.addWidget(QLabel("Chrome Version"))
        ver_col.addWidget(self.ver_input)
        settings_layout.addLayout(ver_col)

        self.auto_proceed_check = QCheckBox("Auto proceed to payment after form submit")
        settings_layout.addWidget(self.auto_proceed_check, alignment=Qt.AlignmentFlag.AlignBottom)
        settings_layout.addStretch()

        layout.addWidget(settings_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.browser_btn = QPushButton("Open Browser")
        self.browser_btn.setFixedHeight(36)
        self.browser_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; border-radius: 4px;")
        self.browser_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browser_btn.clicked.connect(self._open_browser)

        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedHeight(36)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px;")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._start)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; border-radius: 4px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop)

        self.edit_btn = QPushButton("Edit info.json")
        self.edit_btn.setFixedHeight(36)
        self.edit_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; border-radius: 4px;")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self._open_info)

        self.quit_btn = QPushButton("Quit")
        self.quit_btn.setFixedHeight(36)
        self.quit_btn.setStyleSheet("background-color: #555555; color: white; font-weight: bold; border-radius: 4px;")
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_btn.clicked.connect(self._quit)

        btn_layout.addWidget(self.browser_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.quit_btn)
        layout.addLayout(btn_layout)

        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Courier New", 10))
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border: none;")
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group, 1)

    def _check_info_file(self):
        if os.path.exists(INFO_FILE):
            self.info_label.setText(f"info.json loaded")
            self.info_label.setStyleSheet("color: green;")
        else:
            self.info_label.setText("info.json not found — click 'Edit info.json' to create it")
            self.info_label.setStyleSheet("color: orange;")

    def _open_info(self):
        if not os.path.exists(INFO_FILE):
            with open(INFO_FILE, "w") as f:
                json.dump(INFO_TEMPLATE, f, indent=2)
        if sys.platform == "win32":
            os.startfile(INFO_FILE)
        else:
            os.system(f"xdg-open '{INFO_FILE}' 2>/dev/null || nano '{INFO_FILE}'")
        self._check_info_file()

    def _append_log(self, text):
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)
        self.log_view.insertPlainText(text + "\n")
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _open_browser(self):
        if self._browser_worker and self._browser_worker.isRunning():
            self._browser_stop_event.set()
            return

        self._browser_stop_event = threading.Event()
        self._driver = None
        self.browser_btn.setText("Close Browser")
        self.browser_btn.setStyleSheet("background-color: #e65100; color: white; font-weight: bold; border-radius: 4px;")

        self._browser_worker = BrowserWorker(self._browser_stop_event, version_main=self.ver_input.value())
        self._browser_worker.log.connect(self._append_log)
        self._browser_worker.driver_ready.connect(self._on_driver_ready)
        self._browser_worker.finished.connect(self._on_browser_closed)
        self._browser_worker.start()

    def _on_driver_ready(self, driver):
        self._driver = driver
        self._append_log("[✓] Browser ready — click Start to begin automation")

    def _on_browser_closed(self):
        self._driver = None
        self.browser_btn.setText("Open Browser")
        self.browser_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; border-radius: 4px;")

    def _start(self):
        if not os.path.exists(INFO_FILE):
            QMessageBox.critical(self, "Error", "info.json not found. Click 'Edit info.json' first.")
            return

        url = self.url_input.text().strip()
        band_url = self.band_url_input.text().strip() or None
        checkout_code = self.checkout_code_input.text().strip() or None
        sale_type = self.sale_type_input.currentText().upper()
        cats = [c.strip() for c in self.cats_input.text().split(",") if c.strip()]

        if not url and not band_url:
            QMessageBox.critical(self, "Error", "Provide either Band Site URL or Sodtix Event URL.")
            return
        if not cats:
            QMessageBox.critical(self, "Error", "At least one target category required.")
            return

        self._stop_event = threading.Event()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_view.clear()

        self._worker = BotWorker(url, cats, self._stop_event, version_main=self.ver_input.value(), auto_proceed=self.auto_proceed_check.isChecked(), driver=self._driver, band_url=band_url, checkout_code=checkout_code, sale_type=sale_type)
        self._worker.log.connect(self._append_log)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _stop(self):
        if self._stop_event:
            self._stop_event.set()
            self._append_log("[!] Stop requested...")

    def _on_done(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _quit(self):
        self._stop()
        if self._browser_stop_event:
            self._browser_stop_event.set()
        if self._worker and self._worker.isRunning():
            self._worker.wait(2000)
        if self._browser_worker and self._browser_worker.isRunning():
            self._browser_worker.wait(2000)
        QApplication.quit()

    def closeEvent(self, event):
        self._quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
