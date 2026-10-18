"""Dialog inspecting detailed diagnostic results and parameters of a proxy configuration."""

from typing import Any, Dict
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...config_parser.models import ProxyConfig
from ...security import redact_credentials


class ConfigDetailsDialog(QDialog):
    """Modal dialog displaying candidate details and diagnostics."""

    def __init__(self, parent=None, config: ProxyConfig = None, result: Dict[str, Any] = None):
        super().__init__(parent)
        self.config = config
        self.result = result or {}
        self.setWindowTitle(f"Diagnostics — {self.config.display_name}")
        self.setMinimumSize(620, 520)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 1. Benchmark Diagnostics Group
        diag_group = QGroupBox("Benchmark Results & Diagnostics")
        diag_form = QFormLayout(diag_group)

        status_str = self.result.get("status", "untested").upper()
        status_lbl = QLabel(f"<b>{status_str}</b>")
        diag_form.addRow("Status:", status_lbl)

        score_val = self.result.get("score")
        score_str = f"{score_val} / 100" if score_val is not None else "N/A"
        diag_form.addRow("Composite Score:", QLabel(score_str))

        lat_val = self.result.get("latency_ms")
        lat_str = f"{lat_val} ms" if lat_val is not None else "N/A"
        diag_form.addRow("Median Latency:", QLabel(lat_str))

        speed_val = self.result.get("download_speed_mbps")
        speed_str = f"{speed_val} Mbps" if speed_val is not None else "Not measured"
        diag_form.addRow("Download Speed:", QLabel(speed_str))

        succ_val = self.result.get("success_rate")
        succ_str = f"{succ_val}%" if succ_val is not None else "N/A"
        diag_form.addRow("Success Rate:", QLabel(succ_str))

        var_val = self.result.get("latency_variance")
        var_str = f"±{var_val} ms" if var_val is not None else "N/A"
        diag_form.addRow("Latency Variation:", QLabel(var_str))

        err_cat = self.result.get("error_category")
        if err_cat:
            diag_form.addRow("Error Category:", QLabel(f"<span style='color: #f7768e;'>{err_cat}</span>"))

        err_det = self.result.get("error_detail")
        if err_det:
            err_box = QTextEdit()
            err_box.setReadOnly(True)
            err_box.setPlainText(redact_credentials(err_det))
            err_box.setMaximumHeight(70)
            diag_form.addRow("Error Detail:", err_box)

        layout.addWidget(diag_group)

        # 2. Connection Parameters Group
        param_group = QGroupBox("Connection Parameters")
        param_form = QFormLayout(param_group)

        param_form.addRow("Protocol:", QLabel(self.config.protocol.upper()))
        param_form.addRow("Server & Port:", QLabel(f"{self.config.server}:{self.config.port}"))
        param_form.addRow("Transport Network:", QLabel(self.config.network.upper()))
        param_form.addRow("Security:", QLabel(self.config.security.upper()))

        if self.config.sni:
            param_form.addRow("SNI / ServerName:", QLabel(self.config.sni))
        if self.config.fingerprint:
            param_form.addRow("TLS Fingerprint:", QLabel(self.config.fingerprint))
        if self.config.flow:
            param_form.addRow("Flow:", QLabel(self.config.flow))
        if self.config.public_key:
            param_form.addRow("Reality Public Key:", QLabel("[CONFIGURED]"))
        if self.config.ws_path:
            param_form.addRow("WebSocket Path:", QLabel(self.config.ws_path))
        if self.config.grpc_service_name:
            param_form.addRow("gRPC Service:", QLabel(self.config.grpc_service_name))

        layout.addWidget(param_group)

        # 3. Share Link Export
        link_group = QGroupBox("Share Link")
        link_layout = QVBoxLayout(link_group)

        link_row = QHBoxLayout()
        self.link_input = QLineEdit()
        self.link_input.setText(self.config.raw_link)
        self.link_input.setReadOnly(True)
        link_row.addWidget(self.link_input)

        copy_btn = QPushButton("Copy Link")
        copy_btn.clicked.connect(self._copy_link)
        link_row.addWidget(copy_btn)

        link_layout.addLayout(link_row)
        layout.addWidget(link_group)

        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.accept)
        layout.addWidget(btn_box)

    def _copy_link(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.config.raw_link)
