"""Main application window using modern, responsive sidebar navigation."""

from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core_manager import find_xray_binary, get_xray_version
from ..database import Database
from ..workers import BenchmarkWorker, SourceFetchWorker, XrayDownloadWorker
from .dashboard import DashboardTab
from .logs_tab import LogsTab
from .results_tab import ResultsTab
from .settings_tab import SettingsTab
from .sources_tab import SourcesTab
from .theme import DARK_THEME_QSS


class MainWindow(QMainWindow):
    """Modern cross-platform desktop interface for Xray Config Bench."""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.fetch_worker: Optional[SourceFetchWorker] = None
        self.bench_worker: Optional[BenchmarkWorker] = None
        self.download_worker: Optional[XrayDownloadWorker] = None

        self.setWindowTitle("Xray Config Bench")
        self.resize(1140, 720)
        self.setMinimumSize(780, 480)
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_ui()
        self._update_status_bar()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------
        # Left Sidebar Navigation (Never squeezes under Windows DPI scaling)
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 16)
        sidebar_layout.setSpacing(6)

        # Brand header
        brand_label = QLabel("Xray Bench")
        brand_label.setStyleSheet("font-size: 13.5pt; font-weight: bold; color: #7aa2f7; padding: 6px 8px;")
        sidebar_layout.addWidget(brand_label)

        sub_label = QLabel("v1.1 Cross-Platform")
        sub_label.setStyleSheet("color: #565f89; font-size: 8.5pt; padding-left: 8px; margin-bottom: 12px;")
        sidebar_layout.addWidget(sub_label)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.nav_btns: List[QPushButton] = []
        nav_items = [
            ("Dashboard", 0),
            ("Sources", 1),
            ("Results", 2),
            ("Settings", 3),
            ("Logs", 4),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            self.nav_group.addButton(btn, index)
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)

        self.nav_group.idClicked.connect(self._on_nav_clicked)

        sidebar_layout.addStretch()

        # Sidebar footer quick action
        self.quick_scan_btn = QPushButton("Start Scan")
        self.quick_scan_btn.setObjectName("primaryBtn")
        self.quick_scan_btn.clicked.connect(self._start_scan)
        sidebar_layout.addWidget(self.quick_scan_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_active_task)
        sidebar_layout.addWidget(self.cancel_btn)

        root_layout.addWidget(sidebar)

        # -------------------------------------------------------------
        # Right Content Area (QStackedWidget)
        # -------------------------------------------------------------
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")

        self.dashboard_tab = DashboardTab(self.db)
        self.dashboard_tab.fetch_sources_clicked.connect(self._fetch_all_sources)
        self.dashboard_tab.start_scan_clicked.connect(self._start_scan)
        self.content_stack.addWidget(self.dashboard_tab)

        self.sources_tab = SourcesTab(self.db)
        self.sources_tab.source_refresh_requested.connect(self._fetch_single_source)
        self.sources_tab.refresh_all_requested.connect(self._fetch_all_sources)
        self.sources_tab.sources_changed.connect(self._on_sources_changed)
        self.content_stack.addWidget(self.sources_tab)

        self.results_tab = ResultsTab(self.db)
        self.results_tab.retest_requested.connect(self._retest_candidates)
        self.content_stack.addWidget(self.results_tab)

        self.settings_tab = SettingsTab(self.db)
        self.settings_tab.settings_saved.connect(self._on_settings_saved)
        self.settings_tab.download_xray_requested.connect(self._start_xray_download)
        self.content_stack.addWidget(self.settings_tab)

        self.logs_tab = LogsTab()
        self.content_stack.addWidget(self.logs_tab)

        root_layout.addWidget(self.content_stack, stretch=1)

        # Set default active tab
        self.nav_btns[0].setChecked(True)
        self.content_stack.setCurrentIndex(0)

        # -------------------------------------------------------------
        # Status Bar
        # -------------------------------------------------------------
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_backend_lbl = QLabel("Backend: Checking...")
        self.status_bar.addWidget(self.status_backend_lbl, 1)

        self.status_count_lbl = QLabel("Configs: 0")
        self.status_bar.addPermanentWidget(self.status_count_lbl)

    def _on_nav_clicked(self, index: int):
        self.content_stack.setCurrentIndex(index)
        if index == 0:
            self.dashboard_tab.refresh_stats()
        elif index == 1:
            self.sources_tab.reload_sources()
        elif index == 2:
            self.results_tab.reload_results()

    def _update_status_bar(self):
        xray_path = self.db.get_setting("xray_path", "")
        p = Path(xray_path) if xray_path else find_xray_binary()
        if p and p.is_file():
            ok, ver = get_xray_version(p)
            if ok:
                self.status_backend_lbl.setText(f"✓ Backend: {ver}")
            else:
                self.status_backend_lbl.setText("✗ Backend: Binary error")
        else:
            self.status_backend_lbl.setText("⚠ Backend: Xray Core not installed (See Settings)")

        count = self.db.get_configs_count()
        self.status_count_lbl.setText(f"Total Configs: {count}")

    def _set_running_state(self, is_running: bool):
        self.quick_scan_btn.setEnabled(not is_running)
        self.cancel_btn.setEnabled(is_running)

    def _on_sources_changed(self):
        self.dashboard_tab.refresh_stats()
        self._update_status_bar()

    def _on_settings_saved(self):
        self._update_status_bar()

    # --- Source Fetching ---

    def _fetch_all_sources(self):
        self._start_source_fetch(source_id=None)

    def _fetch_single_source(self, source_id: str):
        self._start_source_fetch(source_id=source_id)

    def _start_source_fetch(self, source_id: Optional[str] = None):
        if self.fetch_worker and self.fetch_worker.isRunning():
            return

        self._set_running_state(True)
        github_token = self.db.get_setting("github_token", "")

        self.fetch_worker = SourceFetchWorker(
            db=self.db,
            source_id=source_id,
            github_token=github_token,
        )
        self.fetch_worker.progress.connect(self.dashboard_tab.update_progress)
        self.fetch_worker.log_message.connect(self.logs_tab.append_log)
        self.fetch_worker.all_finished.connect(self._on_fetch_finished)
        self.fetch_worker.start()

    def _on_fetch_finished(self, discovered: int, valid: int, errors: list):
        self._set_running_state(False)
        self.sources_tab.reload_sources()
        self.dashboard_tab.refresh_stats()
        self.results_tab.reload_results()
        self._update_status_bar()

        msg = f"Sources refreshed: Discovered {discovered}, valid {valid} configurations."
        self.logs_tab.append_log(msg)
        self.dashboard_tab.update_progress(100, 100, msg)

        if errors:
            err_summary = "\n".join(errors[:5])
            QMessageBox.warning(self, "Source Fetch Warnings", f"Encountered warnings during fetch:\n\n{err_summary}")

    # --- Benchmarking ---

    def _start_scan(self):
        xray_path_str = self.db.get_setting("xray_path", "")
        p = Path(xray_path_str) if xray_path_str else find_xray_binary()
        if not p or not p.is_file():
            choice = QMessageBox.question(
                self,
                "Xray Backend Missing",
                "Xray Core was not found. Would you like to download the official Xray release now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if choice == QMessageBox.Yes:
                self._start_xray_download()
            return

        all_configs = self.db.get_all_configs()
        if not all_configs:
            QMessageBox.information(
                self,
                "No Configurations",
                "No configurations found. Go to 'Sources' to add and fetch proxy feeds first.",
            )
            self.content_stack.setCurrentIndex(1)
            self.nav_btns[1].setChecked(True)
            return

        self._execute_benchmark(all_configs, p)

    def _retest_candidates(self, hashes: List[str]):
        xray_path_str = self.db.get_setting("xray_path", "")
        p = Path(xray_path_str) if xray_path_str else find_xray_binary()
        if not p or not p.is_file():
            QMessageBox.warning(self, "Backend Missing", "Configured Xray binary does not exist.")
            return

        configs = [self.db.get_config_by_hash(h) for h in hashes]
        configs = [c for c in configs if c is not None]
        if configs:
            self._execute_benchmark(configs, p)

    def _execute_benchmark(self, configs, xray_path: Path):
        if self.bench_worker and self.bench_worker.isRunning():
            return

        self._set_running_state(True)
        max_parallel = int(self.db.get_setting("max_parallel", "3"))
        attempts = int(self.db.get_setting("latency_attempts", "3"))
        timeout = float(self.db.get_setting("timeout_seconds", "5"))
        enable_speed = self.db.get_setting("enable_speed_test", "1") == "1"
        download_url = self.db.get_setting(
            "download_url", "https://speed.cloudflare.com/__down?bytes=2097152"
        )
        download_bytes = int(self.db.get_setting("download_mb", "2")) * 1024 * 1024
        top_speed_count = int(self.db.get_setting("top_speed_count", "10"))
        weights = self.settings_tab.get_scoring_weights()

        self.bench_worker = BenchmarkWorker(
            db=self.db,
            xray_path=xray_path,
            configs=configs,
            max_parallel=max_parallel,
            latency_attempts=attempts,
            timeout=timeout,
            enable_speed_test=enable_speed,
            download_url=download_url,
            download_bytes=download_bytes,
            max_speed_candidates=top_speed_count,
            weights=weights,
        )
        self.bench_worker.progress.connect(self.dashboard_tab.update_progress)
        self.bench_worker.log_message.connect(self.logs_tab.append_log)
        self.bench_worker.candidate_tested.connect(self._on_candidate_tested)
        self.bench_worker.finished.connect(self._on_benchmark_finished)
        self.bench_worker.error.connect(self._on_benchmark_error)
        self.bench_worker.start()

    def _on_candidate_tested(self, result: dict):
        self.dashboard_tab.refresh_stats()
        self.results_tab.reload_results()

    def _on_benchmark_finished(self, working: int, failed: int):
        self._set_running_state(False)
        self.dashboard_tab.refresh_stats()
        self.results_tab.reload_results()
        self._update_status_bar()
        msg = f"Benchmark scan finished: {working} working, {failed} failed."
        self.logs_tab.append_log(msg)
        self.dashboard_tab.update_progress(100, 100, msg)

    def _on_benchmark_error(self, err_msg: str):
        self._set_running_state(False)
        self.logs_tab.append_log(f"Benchmark error: {err_msg}")
        QMessageBox.critical(self, "Benchmark Error", err_msg)

    # --- Cancellation ---

    def _cancel_active_task(self):
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.cancel()
            self.logs_tab.append_log("Cancelling source fetch...")
        if self.bench_worker and self.bench_worker.isRunning():
            self.bench_worker.cancel()
            self.logs_tab.append_log("Cancelling benchmark scan...")
        self._set_running_state(False)

    # --- Xray Managed Download ---

    def _start_xray_download(self):
        if self.download_worker and self.download_worker.isRunning():
            return

        self._set_running_state(True)
        self.logs_tab.append_log("Starting managed download of official Xray Core...")
        self.download_worker = XrayDownloadWorker()
        self.download_worker.progress.connect(self.dashboard_tab.update_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_finished(self, success: bool, message: str):
        self._set_running_state(False)
        self.logs_tab.append_log(message)
        if success:
            found = find_xray_binary()
            if found:
                self.db.set_setting("xray_path", str(found))
                self.settings_tab.load_settings()
                self._update_status_bar()
            QMessageBox.information(self, "Download Complete", message)
        else:
            QMessageBox.critical(self, "Download Failed", f"Failed to download Xray Core:\n{message}")
