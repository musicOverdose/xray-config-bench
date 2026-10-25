"""Settings tab managing Xray Core backend, test targets, concurrency, and scoring weights."""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core_manager import find_xray_binary, get_xray_version
from ..database import Database
from ..ranking import ScoringWeights


import sys

class SettingsTab(QWidget):
    """Configuration view for backend paths, network targets, concurrency, and scoring."""

    settings_saved = Signal()
    download_xray_requested = Signal()

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. Backend Xray Core Group
        backend_group = QGroupBox("Xray Core Backend")
        backend_layout = QVBoxLayout(backend_group)
        backend_layout.setSpacing(10)

        self.xray_path_input = QLineEdit()
        self.xray_path_input.setMinimumWidth(220)
        placeholder = (
            "C:\\path\\to\\xray.exe or %LOCALAPPDATA%\\xray-config-bench\\bin\\xray.exe"
            if sys.platform == "win32"
            else "/usr/local/bin/xray or ~/.config/xray-config-bench/bin/xray"
        )
        self.xray_path_input.setPlaceholderText(placeholder)
        backend_layout.addWidget(self.xray_path_input)

        path_btn_layout = QHBoxLayout()
        path_btn_layout.setSpacing(8)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_xray)
        path_btn_layout.addWidget(browse_btn)

        detect_btn = QPushButton("Auto-Detect")
        detect_btn.clicked.connect(self._auto_detect_xray)
        path_btn_layout.addWidget(detect_btn)

        self.download_btn = QPushButton("Download Official Xray")
        self.download_btn.setObjectName("primaryBtn")
        self.download_btn.clicked.connect(self.download_xray_requested.emit)
        path_btn_layout.addWidget(self.download_btn)

        path_btn_layout.addStretch()
        backend_layout.addLayout(path_btn_layout)

        self.version_lbl = QLabel("Status: Checking backend...")
        self.version_lbl.setStyleSheet("color: #7aa2f7; font-weight: bold; margin-top: 2px;")
        backend_layout.addWidget(self.version_lbl)

        main_layout.addWidget(backend_group)

        # 2. Network Test Endpoints Group
        net_group = QGroupBox("Test Endpoints & Download Targets")
        net_form = QFormLayout(net_group)

        self.endpoints_edit = QTextEdit()
        self.endpoints_edit.setMinimumHeight(75)
        self.endpoints_edit.setMaximumHeight(130)
        self.endpoints_edit.setPlaceholderText("https://cp.cloudflare.com/generate_204\nhttps://www.google.com/generate_204")
        net_form.addRow("Latency Probes (one per line):", self.endpoints_edit)

        self.download_url_input = QLineEdit()
        self.download_url_input.setMinimumWidth(220)
        self.download_url_input.setPlaceholderText("https://speed.cloudflare.com/__down?bytes=2097152")
        net_form.addRow("Speed Test URL:", self.download_url_input)

        self.download_mb_spin = QSpinBox()
        self.download_mb_spin.setRange(1, 10)
        self.download_mb_spin.setValue(2)
        self.download_mb_spin.setSuffix(" MB")
        net_form.addRow("Max Download Size:", self.download_mb_spin)

        main_layout.addWidget(net_group)

        # 3. Concurrency and Scan Limits Group
        perf_group = QGroupBox("Concurrency and Limits")
        perf_form = QFormLayout(perf_group)

        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 10)
        self.parallel_spin.setValue(3)
        perf_form.addRow("Max Concurrent Workers:", self.parallel_spin)

        self.attempts_spin = QSpinBox()
        self.attempts_spin.setRange(1, 5)
        self.attempts_spin.setValue(3)
        perf_form.addRow("Latency Attempts per Candidate:", self.attempts_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(2, 30)
        self.timeout_spin.setValue(5)
        self.timeout_spin.setSuffix(" seconds")
        perf_form.addRow("Connection Timeout:", self.timeout_spin)

        self.top_speed_spin = QSpinBox()
        self.top_speed_spin.setRange(1, 100)
        self.top_speed_spin.setValue(10)
        perf_form.addRow("Speed Test Top Candidates Limit:", self.top_speed_spin)

        self.enable_speed_check = QCheckBox("Enable download speed benchmarking (Disable for latency-only scans)")
        self.enable_speed_check.setChecked(True)
        perf_form.addRow("", self.enable_speed_check)

        main_layout.addWidget(perf_group)

        # 4. Composite Scoring Weights Group
        weights_group = QGroupBox("Scoring Algorithm Weights")
        weights_form = QFormLayout(weights_group)

        self.weight_success_spin = QDoubleSpinBox()
        self.weight_success_spin.setRange(0.0, 1.0)
        self.weight_success_spin.setSingleStep(0.05)
        self.weight_success_spin.setValue(0.35)
        weights_form.addRow("Connectivity / Success Weight:", self.weight_success_spin)

        self.weight_latency_spin = QDoubleSpinBox()
        self.weight_latency_spin.setRange(0.0, 1.0)
        self.weight_latency_spin.setSingleStep(0.05)
        self.weight_latency_spin.setValue(0.30)
        weights_form.addRow("Latency Weight:", self.weight_latency_spin)

        self.weight_speed_spin = QDoubleSpinBox()
        self.weight_speed_spin.setRange(0.0, 1.0)
        self.weight_speed_spin.setSingleStep(0.05)
        self.weight_speed_spin.setValue(0.25)
        weights_form.addRow("Download Throughput Weight:", self.weight_speed_spin)

        self.weight_stab_spin = QDoubleSpinBox()
        self.weight_stab_spin.setRange(0.0, 1.0)
        self.weight_stab_spin.setSingleStep(0.05)
        self.weight_stab_spin.setValue(0.10)
        weights_form.addRow("Stability / Low Jitter Weight:", self.weight_stab_spin)

        reset_weights_btn = QPushButton("Reset Default Weights")
        reset_weights_btn.clicked.connect(self._reset_weights)
        weights_form.addRow("", reset_weights_btn)

        main_layout.addWidget(weights_group)

        # 5. GitHub API Authentication Group
        github_group = QGroupBox("GitHub API Authentication (Optional)")
        github_form = QFormLayout(github_group)

        self.github_token_input = QLineEdit()
        self.github_token_input.setMinimumWidth(220)
        self.github_token_input.setEchoMode(QLineEdit.Password)
        self.github_token_input.setPlaceholderText("ghp_... (Saved only locally in settings DB, never committed)")
        github_form.addRow("Personal Access Token:", self.github_token_input)

        main_layout.addWidget(github_group)

        # Bottom Save Button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self.save_settings)
        save_layout.addWidget(self.save_btn)
        main_layout.addLayout(save_layout)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def load_settings(self):
        """Load settings from database and populate form fields."""
        xray_path = self.db.get_setting("xray_path", "")
        if not xray_path:
            detected = find_xray_binary()
            if detected:
                xray_path = str(detected)
        self.xray_path_input.setText(xray_path)
        self._check_xray_version(xray_path)

        default_endpoints = (
            "https://cp.cloudflare.com/generate_204\n"
            "https://www.google.com/generate_204\n"
            "https://www.gstatic.com/generate_204"
        )
        self.endpoints_edit.setPlainText(self.db.get_setting("test_endpoints", default_endpoints))

        self.download_url_input.setText(
            self.db.get_setting("download_url", "https://speed.cloudflare.com/__down?bytes=2097152")
        )
        self.download_mb_spin.setValue(int(self.db.get_setting("download_mb", "2")))
        self.parallel_spin.setValue(int(self.db.get_setting("max_parallel", "3")))
        self.attempts_spin.setValue(int(self.db.get_setting("latency_attempts", "3")))
        self.timeout_spin.setValue(int(self.db.get_setting("timeout_seconds", "5")))
        self.top_speed_spin.setValue(int(self.db.get_setting("top_speed_count", "10")))
        self.enable_speed_check.setChecked(self.db.get_setting("enable_speed_test", "1") == "1")

        self.weight_success_spin.setValue(float(self.db.get_setting("weight_success", "0.35")))
        self.weight_latency_spin.setValue(float(self.db.get_setting("weight_latency", "0.30")))
        self.weight_speed_spin.setValue(float(self.db.get_setting("weight_speed", "0.25")))
        self.weight_stab_spin.setValue(float(self.db.get_setting("weight_stability", "0.10")))

        self.github_token_input.setText(self.db.get_setting("github_token", ""))

    def save_settings(self):
        """Save form fields to database."""
        self.db.set_setting("xray_path", self.xray_path_input.text().strip())
        self.db.set_setting("test_endpoints", self.endpoints_edit.toPlainText().strip())
        self.db.set_setting("download_url", self.download_url_input.text().strip())
        self.db.set_setting("download_mb", str(self.download_mb_spin.value()))
        self.db.set_setting("max_parallel", str(self.parallel_spin.value()))
        self.db.set_setting("latency_attempts", str(self.attempts_spin.value()))
        self.db.set_setting("timeout_seconds", str(self.timeout_spin.value()))
        self.db.set_setting("top_speed_count", str(self.top_speed_spin.value()))
        self.db.set_setting("enable_speed_test", "1" if self.enable_speed_check.isChecked() else "0")

        self.db.set_setting("weight_success", str(self.weight_success_spin.value()))
        self.db.set_setting("weight_latency", str(self.weight_latency_spin.value()))
        self.db.set_setting("weight_speed", str(self.weight_speed_spin.value()))
        self.db.set_setting("weight_stability", str(self.weight_stab_spin.value()))

        self.db.set_setting("github_token", self.github_token_input.text().strip())

        self._check_xray_version(self.xray_path_input.text().strip())
        self.settings_saved.emit()
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    def _reset_weights(self):
        self.weight_success_spin.setValue(0.35)
        self.weight_latency_spin.setValue(0.30)
        self.weight_speed_spin.setValue(0.25)
        self.weight_stab_spin.setValue(0.10)

    def _browse_xray(self):
        filt = "Executable (*.exe);;All Files (*.*)" if sys.platform == "win32" else "Executable (*);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Xray Core Binary", "", filt)
        if path:
            self.xray_path_input.setText(path)
            self._check_xray_version(path)

    def _auto_detect_xray(self):
        found = find_xray_binary()
        if found:
            self.xray_path_input.setText(str(found))
            self._check_xray_version(str(found))
            QMessageBox.information(self, "Xray Detected", f"Found Xray binary at:\n{found}")
        else:
            QMessageBox.warning(
                self,
                "Not Found",
                "Xray Core was not found in PATH or standard directories.\nClick 'Download Official Xray' to install it automatically.",
            )

    def _check_xray_version(self, path_str: str):
        if not path_str:
            self.version_lbl.setText("<span style='color: #f7768e;'>Backend: No Xray binary configured</span>")
            return

        p = Path(path_str).expanduser()
        valid, ver = get_xray_version(p)
        if valid:
            self.version_lbl.setText(f"<span style='color: #9ece6a;'>✓ Active: {ver}</span>")
        else:
            self.version_lbl.setText(f"<span style='color: #f7768e;'>✗ Invalid binary: {ver}</span>")

    def get_scoring_weights(self) -> ScoringWeights:
        return ScoringWeights(
            weight_success=self.weight_success_spin.value(),
            weight_latency=self.weight_latency_spin.value(),
            weight_speed=self.weight_speed_spin.value(),
            weight_stability=self.weight_stab_spin.value(),
        )

    def get_endpoints(self) -> list[str]:
        raw = self.endpoints_edit.toPlainText()
        return [line.strip() for line in raw.splitlines() if line.strip()]
