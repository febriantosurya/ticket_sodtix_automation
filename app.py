import sys
import os
import json
import threading

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QGroupBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor, QCursor

from automation import run, INFO_FILE, INFO_TEMPLATE


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

    def __init__(self, url, categories, stop_event, version_main=146, auto_proceed=False):
        super().__init__()
        self.url = url
        self.categories = categories
        self.stop_event = stop_event
        self.version_main = version_main
        self.auto_proceed = auto_proceed

    def run(self):
        stream = LogStream()
        stream.message.connect(self.log)
        sys.stdout = stream
        try:
            run(self.url, target_categories=self.categories, stop_event=self.stop_event, version_main=self.version_main, auto_proceed=self.auto_proceed)
        except Exception as e:
            self.log.emit(f"[ERROR] {e}")
        finally:
            sys.stdout = sys.__stdout__
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket Bot [sodtix.com]")
        self.setMinimumWidth(700)
        self._worker = None
        self._stop_event = None
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

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Event URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://sodtix.com/event/...")
        self.url_input.setMinimumWidth(450)
        url_row.addWidget(self.url_input)
        config_layout.addLayout(url_row)

        cats_row = QHBoxLayout()
        cats_row.addWidget(QLabel("Target Categories\n(priority, comma-separated):"))
        self.cats_input = QLineEdit()
        self.cats_input.setPlaceholderText("e.g. TRIBUNE 1, TRIBUNE 2")
        cats_row.addWidget(self.cats_input)
        config_layout.addLayout(cats_row)

        ver_row = QHBoxLayout()
        ver_row.addWidget(QLabel("Chrome Version:"))
        self.ver_input = QSpinBox()
        self.ver_input.setRange(100, 200)
        self.ver_input.setValue(146)
        self.ver_input.setFixedWidth(80)
        ver_row.addWidget(self.ver_input)
        ver_row.addStretch()
        config_layout.addLayout(ver_row)

        self.auto_proceed_check = QCheckBox("Auto proceed to payment after form submit")
        config_layout.addWidget(self.auto_proceed_check)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: green;")
        config_layout.addWidget(self.info_label)

        layout.addWidget(config_group)

        # Buttons
        btn_layout = QHBoxLayout()
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
        self.log_view.setMinimumHeight(300)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group)

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

    def _start(self):
        if not os.path.exists(INFO_FILE):
            QMessageBox.critical(self, "Error", "info.json not found. Click 'Edit info.json' first.")
            return

        url = self.url_input.text().strip()
        cats = [c.strip() for c in self.cats_input.text().split(",") if c.strip()]

        if not url:
            QMessageBox.critical(self, "Error", "URL is required.")
            return
        if not cats:
            QMessageBox.critical(self, "Error", "At least one target category required.")
            return

        self._stop_event = threading.Event()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_view.clear()

        self._worker = BotWorker(url, cats, self._stop_event, version_main=self.ver_input.value(), auto_proceed=self.auto_proceed_check.isChecked())
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
        if self._worker and self._worker.isRunning():
            self._worker.wait(2000)
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
