#!/usr/bin/env python3
"""
Xray Config Bench — A Python GUI for Finding the Best V2Ray/Xray Configurations.
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.database import Database
from app.ui.dialogs.error_dialog import setup_exception_hook
from app.ui.main_window import MainWindow


def main():
    # Enable High DPI scaling across Windows, Linux, and macOS
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Xray Config Bench")
    app.setApplicationDisplayName("Xray Config Bench")
    app.setOrganizationName("XrayConfigBench")

    # Install global exception handler to prevent silent crashes
    setup_exception_hook()

    db = Database()
    window = MainWindow(db)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
