"""GUI initialization and widget integration test using pytest-qt."""

import pytest
from PySide6.QtCore import Qt
from app.config_parser.models import ProxyConfig
from app.database import Database
from app.ui.main_window import MainWindow


def test_main_window_initialization(qtbot, tmp_path):
    db_path = tmp_path / "gui_test.db"
    db = Database(str(db_path))

    window = MainWindow(db)
    qtbot.addWidget(window)

    # Verify window title and tabs
    assert "Xray Config Bench" in window.windowTitle()
    assert window.tabs.count() == 5
    assert window.tabs.tabText(0) == "Dashboard"
    assert window.tabs.tabText(1) == "Sources"
    assert window.tabs.tabText(2) == "Results"
    assert window.tabs.tabText(3) == "Settings"
    assert window.tabs.tabText(4) == "Logs"

    # Add dummy config and verify it appears in results tab
    cfg = ProxyConfig(
        protocol="vless",
        server="1.2.3.4",
        port=443,
        name="Test Node GUI",
        uuid="test-uuid-1234",
        raw_link="vless://test-uuid-1234@1.2.3.4:443#TestNode",
    )
    db.upsert_config(cfg)
    window.results_tab.reload_results()
    assert window.results_tab.table.rowCount() == 1

    # Verify log console works
    window.logs_tab.append_log("Hello from GUI test with secret ghp_abcdef1234567890")
    log_text = window.logs_tab.log_console.toPlainText()
    assert "Hello from GUI test" in log_text
    assert "ghp_" not in log_text
    assert "[REDACTED-TOKEN]" in log_text
