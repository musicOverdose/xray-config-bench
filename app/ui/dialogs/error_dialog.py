"""Error reporting dialog capturing tracebacks and diagnostic information."""

import sys
import traceback
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...security import redact_credentials


class ErrorDialog(QDialog):
    """Informative modal dialog displayed when an unhandled exception occurs."""

    def __init__(self, exc_type, exc_value, exc_tb, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Error — Xray Config Bench")
        self.setMinimumSize(560, 360)
        self.resize(640, 420)

        # Format and redact traceback
        raw_tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self.error_text = redact_credentials(raw_tb)

        self._init_ui(str(exc_value))

    def _init_ui(self, short_msg: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header warning
        header_lbl = QLabel(f"<b>An unexpected error occurred:</b><br>{short_msg}")
        header_lbl.setStyleSheet("color: #f7768e; font-size: 13pt;")
        header_lbl.setWordWrap(True)
        layout.addWidget(header_lbl)

        # Diagnostic Details
        details_lbl = QLabel("Diagnostic traceback (credentials automatically redacted):")
        details_lbl.setStyleSheet("color: #7aa2f7; font-weight: bold;")
        layout.addWidget(details_lbl)

        self.tb_box = QTextEdit()
        self.tb_box.setReadOnly(True)
        self.tb_box.setPlainText(self.error_text)
        self.tb_box.setMinimumHeight(150)
        self.tb_box.setStyleSheet(
            """
            QTextEdit {
                background-color: #16161e;
                color: #c0caf5;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5pt;
                border: 1px solid #414868;
                border-radius: 6px;
                padding: 8px;
            }
            """
        )
        layout.addWidget(self.tb_box)

        # Buttons
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("Copy Error Details")
        copy_btn.clicked.connect(self._copy_error)
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Dismiss")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _copy_error(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.error_text)


def setup_exception_hook():
    """Install global exception hook to display error dialog on unhandled crashes."""
    original_hook = sys.excepthook

    def exception_hook(exc_type, exc_value, exc_tb):
        # Ignore KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        print(
            redact_credentials("".join(traceback.format_exception(exc_type, exc_value, exc_tb))),
            file=sys.stderr,
        )
        dialog = ErrorDialog(exc_type, exc_value, exc_tb)
        dialog.exec()

    sys.excepthook = exception_hook
