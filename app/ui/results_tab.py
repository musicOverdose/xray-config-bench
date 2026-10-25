"""Benchmark results table with filtering, sorting, diagnostic inspection, and exports."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config_parser.models import ProxyConfig
from ..database import Database
from .dialogs.config_details import ConfigDetailsDialog
from .theme import get_protocol_badge_color, get_status_color


class ResultsTab(QWidget):
    """Tab presenting benchmarked configurations with diagnostic actions and exports."""

    retest_requested = Signal(list)  # list of unique_hashes

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._results_cache: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 1. Filters Bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Protocol:"))
        self.proto_combo = QComboBox()
        self.proto_combo.addItems(["All", "VLESS", "VMess", "Trojan", "Shadowsocks"])
        self.proto_combo.currentTextChanged.connect(self.reload_results)
        filter_layout.addWidget(self.proto_combo)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Working", "Failed", "Untested"])
        self.status_combo.currentTextChanged.connect(self.reload_results)
        filter_layout.addWidget(self.status_combo)

        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter name, server, or source...")
        self.search_input.textChanged.connect(self.reload_results)
        filter_layout.addWidget(self.search_input)

        filter_layout.addStretch()

        self.retest_btn = QPushButton("Retest Selected")
        self.retest_btn.clicked.connect(self._retest_selected)
        filter_layout.addWidget(self.retest_btn)

        self.details_btn = QPushButton("Inspect Details")
        self.details_btn.clicked.connect(self._inspect_selected)
        filter_layout.addWidget(self.details_btn)

        layout.addLayout(filter_layout)

        # 2. Main Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Rank",
            "Name / Server",
            "Source",
            "Protocol",
            "Status",
            "Latency (ms)",
            "Speed (Mbps)",
            "Success (%)",
            "Variance (ms)",
            "Score",
            "Last Tested",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._inspect_selected)

        layout.addWidget(self.table)

        # 3. Export Action Bar
        export_layout = QHBoxLayout()
        export_layout.setSpacing(8)

        copy_link_btn = QPushButton("Copy Share Link")
        copy_link_btn.clicked.connect(self._copy_selected_link)
        export_layout.addWidget(copy_link_btn)

        copy_summary_btn = QPushButton("Copy Safe Summary")
        copy_summary_btn.clicked.connect(self._copy_safe_summary)
        export_layout.addWidget(copy_summary_btn)

        export_layout.addSpacing(16)

        export_sel_btn = QPushButton("Export Selected")
        export_sel_btn.clicked.connect(self._export_selected)
        export_layout.addWidget(export_sel_btn)

        export_all_btn = QPushButton("Export All Working")
        export_all_btn.clicked.connect(self._export_all_working)
        export_layout.addWidget(export_all_btn)

        export_top_btn = QPushButton("Export Top N...")
        export_top_btn.setObjectName("primaryBtn")
        export_top_btn.clicked.connect(self._export_top_n)
        export_layout.addWidget(export_top_btn)

        export_layout.addStretch()
        layout.addLayout(export_layout)

        self.reload_results()

    def reload_results(self):
        """Fetch results from DB, apply search filter, and populate table."""
        proto = self.proto_combo.currentText()
        status = self.status_combo.currentText()
        search_txt = self.search_input.text().strip().lower()

        # Disable sorting while populating to avoid indexing artifacts
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        rows = self.db.get_latest_results(protocol=proto, status=status)
        self._results_cache = rows

        filtered_rows = []
        for r in rows:
            if search_txt:
                name_match = search_txt in (r.get("name") or "").lower()
                server_match = search_txt in (r.get("server") or "").lower()
                source_match = search_txt in (r.get("source_name") or "").lower()
                proto_match = search_txt in (r.get("protocol") or "").lower()
                if not (name_match or server_match or source_match or proto_match):
                    continue
            filtered_rows.append(r)

        self.table.setRowCount(len(filtered_rows))

        for idx, r in enumerate(filtered_rows):
            rank = idx + 1
            config_hash = r["unique_hash"]

            # Rank
            rank_item = QTableWidgetItem()
            rank_item.setData(Qt.DisplayRole, rank)
            rank_item.setData(Qt.UserRole, config_hash)
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 0, rank_item)

            # Name / Server
            name = r.get("name") or f"{r.get('server')}:{r.get('port')}"
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, config_hash)
            self.table.setItem(idx, 1, name_item)

            # Source
            src_name = r.get("source_name") or "Direct"
            self.table.setItem(idx, 2, QTableWidgetItem(src_name))

            # Protocol (badge color)
            proto_str = (r.get("protocol") or "").upper()
            proto_item = QTableWidgetItem(proto_str)
            proto_item.setForeground(QColor(get_protocol_badge_color(proto_str)))
            proto_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 3, proto_item)

            # Status (colored)
            st = (r.get("status") or "untested").title()
            status_item = QTableWidgetItem(st)
            status_item.setForeground(QColor(get_status_color(st)))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 4, status_item)

            # Latency (ms)
            lat_item = QTableWidgetItem()
            lat = r.get("latency_ms")
            if lat is not None:
                lat_item.setData(Qt.DisplayRole, round(lat, 1))
            else:
                lat_item.setText("—")
            lat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(idx, 5, lat_item)

            # Speed (Mbps)
            speed_item = QTableWidgetItem()
            spd = r.get("download_speed_mbps")
            if spd is not None:
                speed_item.setData(Qt.DisplayRole, round(spd, 2))
            else:
                speed_item.setText("—")
            speed_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(idx, 6, speed_item)

            # Success (%)
            succ_item = QTableWidgetItem()
            succ = r.get("success_rate")
            if succ is not None:
                succ_item.setData(Qt.DisplayRole, round(succ, 1))
            else:
                succ_item.setText("—")
            succ_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(idx, 7, succ_item)

            # Variance (ms)
            var_item = QTableWidgetItem()
            var = r.get("latency_variance")
            if var is not None:
                var_item.setData(Qt.DisplayRole, round(var, 1))
            else:
                var_item.setText("—")
            var_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(idx, 8, var_item)

            # Score
            score_item = QTableWidgetItem()
            sc = r.get("score")
            if sc is not None:
                score_item.setData(Qt.DisplayRole, round(sc, 1))
                if sc >= 75.0:
                    score_item.setForeground(QColor("#9ece6a"))  # Green
                elif sc >= 50.0:
                    score_item.setForeground(QColor("#7aa2f7"))  # Blue
            else:
                score_item.setText("—")
            score_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(idx, 9, score_item)

            # Last Tested
            tested_at = r.get("tested_at")
            tested_str = tested_at[:19].replace("T", " ") if tested_at else "Never"
            self.table.setItem(idx, 10, QTableWidgetItem(tested_str))

        self.table.setSortingEnabled(True)

    def _get_selected_hashes(self) -> List[str]:
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        hashes = []
        for row in selected_rows:
            item = self.table.item(row, 0)
            if item:
                h = item.data(Qt.UserRole)
                if h:
                    hashes.append(h)
        return hashes

    def _copy_selected_link(self):
        hashes = self._get_selected_hashes()
        if not hashes:
            return
        cfg = self.db.get_config_by_hash(hashes[0])
        if cfg and cfg.raw_link:
            QGuiApplication.clipboard().setText(cfg.raw_link)
            QMessageBox.information(self, "Copied", "Share link copied to clipboard.")

    def _copy_safe_summary(self):
        hashes = self._get_selected_hashes()
        if not hashes:
            return
        cfg = self.db.get_config_by_hash(hashes[0])
        if cfg:
            summary = cfg.safe_summary()
            QGuiApplication.clipboard().setText(summary)
            QMessageBox.information(self, "Copied", f"Summary copied:\n{summary}")

    def _inspect_selected(self):
        hashes = self._get_selected_hashes()
        if not hashes:
            return
        config_hash = hashes[0]
        cfg = self.db.get_config_by_hash(config_hash)
        if not cfg:
            return

        # Find result record
        result = next((r for r in self._results_cache if r["unique_hash"] == config_hash), {})
        dialog = ConfigDetailsDialog(self, config=cfg, result=result)
        dialog.exec()

    def _retest_selected(self):
        hashes = self._get_selected_hashes()
        if hashes:
            self.retest_requested.emit(hashes)

    def _export_selected(self):
        hashes = self._get_selected_hashes()
        if not hashes:
            QMessageBox.information(self, "Export", "No configurations selected.")
            return

        links = []
        for h in hashes:
            cfg = self.db.get_config_by_hash(h)
            if cfg and cfg.raw_link:
                links.append(cfg.raw_link)

        self._save_or_copy_links(links, "Export Selected Configurations")

    def _export_all_working(self):
        working_results = [r for r in self._results_cache if r.get("status") == "working"]
        links = []
        for r in working_results:
            cfg = self.db.get_config_by_hash(r["unique_hash"])
            if cfg and cfg.raw_link:
                links.append(cfg.raw_link)

        if not links:
            QMessageBox.information(self, "Export", "No working configurations to export.")
            return

        self._save_or_copy_links(links, f"Export All Working Configurations ({len(links)})")

    def _export_top_n(self):
        working_results = [r for r in self._results_cache if r.get("status") == "working"]
        if not working_results:
            QMessageBox.information(self, "Export", "No working configurations to export.")
            return

        num, ok = QInputDialog.getInt(
            self,
            "Export Top Configurations",
            "Enter number of top configurations to export:",
            10,
            1,
            len(working_results),
            1,
        )
        if not ok:
            return

        top_candidates = working_results[:num]
        links = []
        for r in top_candidates:
            cfg = self.db.get_config_by_hash(r["unique_hash"])
            if cfg and cfg.raw_link:
                links.append(cfg.raw_link)

        self._save_or_copy_links(links, f"Export Top {len(links)} Configurations")

    def _save_or_copy_links(self, links: List[str], title: str):
        content = "\n".join(links)
        choice = QMessageBox.question(
            self,
            title,
            f"Found {len(links)} configuration links.\n\nSave to a local file? (Choose 'No' to copy to clipboard instead)",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )
        if choice == QMessageBox.Yes:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Configurations",
                "xray_configs.txt",
                "Text Files (*.txt);;All Files (*)",
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "Export Succeeded", f"Exported {len(links)} configs to:\n{file_path}")
        elif choice == QMessageBox.No:
            QGuiApplication.clipboard().setText(content)
            QMessageBox.information(self, "Copied", f"Copied {len(links)} configuration links to clipboard.")
