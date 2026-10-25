"""Dashboard overview tab showing KPI metric cards, scan progress, and best candidate."""

from typing import Any, Dict
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..database import Database


class MetricCard(QFrame):
    """Clean styled metric summary card."""

    def __init__(self, title: str, value: str = "0", color: str = "#7aa2f7", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            MetricCard {{
                background-color: #1f2335;
                border: 1px solid #292e42;
                border-radius: 8px;
                padding: 14px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("color: #7982a9; font-size: 8.5pt; font-weight: bold;")
        layout.addWidget(self.title_lbl)

        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 18pt; font-weight: bold;")
        layout.addWidget(self.val_lbl)

    def set_value(self, val: str):
        self.val_lbl.setText(str(val))


class DashboardTab(QWidget):
    """Dashboard view widget."""

    fetch_sources_clicked = Signal()
    start_scan_clicked = Signal()

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # 1. KPI Metric Cards Grid
        cards_grid = QGridLayout()
        cards_grid.setSpacing(10)

        self.card_discovered = MetricCard("Discovered", "0", "#7dcfff")
        self.card_tested = MetricCard("Tested", "0", "#bb9af7")
        self.card_working = MetricCard("Working", "0", "#9ece6a")
        self.card_failed = MetricCard("Failed", "0", "#f7768e")
        self.card_untested = MetricCard("Pending", "0", "#e0af68")

        cards_grid.addWidget(self.card_discovered, 0, 0)
        cards_grid.addWidget(self.card_tested, 0, 1)
        cards_grid.addWidget(self.card_working, 0, 2)
        cards_grid.addWidget(self.card_failed, 0, 3)
        cards_grid.addWidget(self.card_untested, 0, 4)

        main_layout.addLayout(cards_grid)

        # 2. Active Scan Progress Section
        progress_group = QGroupBox("Active Scan Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.progress_status_lbl = QLabel("Ready. No active scan.")
        self.progress_status_lbl.setStyleSheet("color: #7982a9; font-style: italic; font-size: 9pt;")
        progress_layout.addWidget(self.progress_status_lbl)

        main_layout.addWidget(progress_group)

        # 3. Best Configuration Found Card
        best_group = QGroupBox("Top-Performing Configuration")
        best_layout = QVBoxLayout(best_group)

        self.best_card_frame = QFrame()
        self.best_card_frame.setStyleSheet(
            """
            background-color: #24283b;
            border: 1px solid #414868;
            border-radius: 8px;
            padding: 14px;
            """
        )
        best_card_layout = QHBoxLayout(self.best_card_frame)

        # Left info
        best_info_layout = QVBoxLayout()
        self.best_title_lbl = QLabel("No benchmarked working configuration yet")
        self.best_title_lbl.setStyleSheet("font-size: 12pt; font-weight: bold; color: #7aa2f7;")
        best_info_layout.addWidget(self.best_title_lbl)

        self.best_details_lbl = QLabel("Add sources and run a scan to find the lowest-latency nodes.")
        self.best_details_lbl.setStyleSheet("color: #c0caf5; font-size: 9.5pt;")
        best_info_layout.addWidget(self.best_details_lbl)
        best_card_layout.addLayout(best_info_layout)

        # Right score badge
        self.best_score_lbl = QLabel("—")
        self.best_score_lbl.setStyleSheet(
            """
            font-size: 22pt;
            font-weight: bold;
            color: #9ece6a;
            padding: 6px 14px;
            background-color: #1a1b26;
            border-radius: 8px;
            """
        )
        self.best_score_lbl.setAlignment(Qt.AlignCenter)
        best_card_layout.addWidget(self.best_score_lbl)

        best_layout.addWidget(self.best_card_frame)
        main_layout.addWidget(best_group)

        # 4. Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)

        fetch_btn = QPushButton("Refresh All Sources")
        fetch_btn.clicked.connect(self.fetch_sources_clicked.emit)
        actions_layout.addWidget(fetch_btn)

        scan_btn = QPushButton("Start Benchmark Scan")
        scan_btn.setObjectName("primaryBtn")
        scan_btn.clicked.connect(self.start_scan_clicked.emit)
        actions_layout.addWidget(scan_btn)

        main_layout.addWidget(actions_group)
        main_layout.addStretch()

        self.refresh_stats()

    def refresh_stats(self):
        """Update dashboard numbers and top candidate from database."""
        stats = self.db.get_dashboard_stats()
        self.card_discovered.set_value(str(stats["discovered"]))
        self.card_tested.set_value(str(stats["tested"]))
        self.card_working.set_value(str(stats["working"]))
        self.card_failed.set_value(str(stats["failed"]))
        self.card_untested.set_value(str(stats["untested"]))

        best = stats.get("best_config")
        if best:
            name = best.get("name") or f"{best.get('server')}:{best.get('port')}"
            proto = best.get("protocol", "").upper()
            lat = best.get("latency_ms")
            spd = best.get("download_speed_mbps")
            score = best.get("score", 0)

            lat_str = f"{lat} ms" if lat else "N/A"
            spd_str = f" | {spd} Mbps" if spd else ""

            self.best_title_lbl.setText(f"[{proto}] {name}")
            self.best_details_lbl.setText(
                f"Server: {best.get('server')}:{best.get('port')}  |  Latency: {lat_str}{spd_str}"
            )
            self.best_score_lbl.setText(f"{score}")
        else:
            self.best_title_lbl.setText("No benchmarked working configuration yet")
            self.best_details_lbl.setText("Add sources and run a scan to find the lowest-latency nodes.")
            self.best_score_lbl.setText("—")

    def update_progress(self, current: int, total: int, message: str):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        else:
            self.progress_bar.setValue(0)
        self.progress_status_lbl.setText(message)
