"""Real-time operational logs tab with automatic credential redaction."""

from datetime import datetime
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..security import redact_credentials


class LogsTab(QWidget):
    """Log viewer automatically sanitizing sensitive tokens and connection details."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Toolbar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)
        btn_layout.addWidget(clear_btn)

        save_btn = QPushButton("Export Logs to File...")
        save_btn.clicked.connect(self.export_logs)
        btn_layout.addWidget(save_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Text Console
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #16161e;
                color: #9aa5ce;
                font-family: 'Consolas', 'Courier New', 'Liberation Mono', monospace;
                font-size: 12px;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 8px;
            }
            """
        )
        layout.addWidget(self.log_console)

    def append_log(self, text: str):
        """Append a log message with timestamp, ensuring credentials are redacted."""
        clean_text = redact_credentials(text)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_console.appendPlainText(f"[{timestamp}] {clean_text}")
        self.log_console.moveCursor(QTextCursor.End)

    def clear_logs(self):
        self.log_console.clear()

    def export_logs(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            "xray_bench_logs.txt",
            "Log Files (*.log *.txt);;All Files (*)",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_console.toPlainText())
            QMessageBox.information(self, "Exported", f"Logs saved to {file_path}")
