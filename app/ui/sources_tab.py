"""Sources management tab for subscriptions, GitHub repositories, and local files."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..database import Database
from .dialogs.source_dialog import SourceDialog


class SourcesTab(QWidget):
    """Tab allowing users to manage, enable, disable, and refresh configuration feeds."""

    source_refresh_requested = Signal(str)  # source_id
    refresh_all_requested = Signal()
    sources_changed = Signal()

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Top Button Toolbar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.add_btn = QPushButton("+ Add Source")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.clicked.connect(self._add_source)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_selected)
        btn_layout.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addSpacing(16)

        self.refresh_btn = QPushButton("Refresh Selected")
        self.refresh_btn.clicked.connect(self._refresh_selected)
        btn_layout.addWidget(self.refresh_btn)

        self.refresh_all_btn = QPushButton("Refresh All Enabled")
        self.refresh_all_btn.clicked.connect(self.refresh_all_requested.emit)
        btn_layout.addWidget(self.refresh_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Sources Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Active",
            "Name",
            "Type",
            "URL / File Path",
            "Discovered",
            "Valid",
            "Last Refresh / Error",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.table.doubleClicked.connect(self._edit_selected)

        layout.addWidget(self.table)

        self.reload_sources()

    def reload_sources(self):
        """Reload sources table from database."""
        self.table.blockSignals(True)
        sources = self.db.get_sources()
        self.table.setRowCount(len(sources))

        for row, s in enumerate(sources):
            # Active Checkbox
            active_item = QTableWidgetItem()
            active_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            active_item.setCheckState(Qt.Checked if s["enabled"] else Qt.Unchecked)
            active_item.setData(Qt.UserRole, s["id"])
            self.table.setItem(row, 0, active_item)

            # Name
            name_item = QTableWidgetItem(s["name"])
            name_item.setData(Qt.UserRole, s["id"])
            self.table.setItem(row, 1, name_item)

            # Type
            type_label = s["source_type"].replace("_", " ").title()
            self.table.setItem(row, 2, QTableWidgetItem(type_label))

            # Path
            self.table.setItem(row, 3, QTableWidgetItem(s["url_or_path"]))

            # Discovered
            disc_item = QTableWidgetItem(str(s.get("discovered_count", 0)))
            disc_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, disc_item)

            # Valid
            val_item = QTableWidgetItem(str(s.get("valid_count", 0)))
            val_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, val_item)

            # Last Refresh / Error
            err = s.get("error_message")
            last_ref = s.get("last_refresh")
            if err:
                status_item = QTableWidgetItem(f"Error: {err[:50]}")
                status_item.setForeground(Qt.red)
                status_item.setToolTip(err)
            elif last_ref:
                # Format friendly date
                short_dt = last_ref[:19].replace("T", " ")
                status_item = QTableWidgetItem(short_dt)
            else:
                status_item = QTableWidgetItem("Never refreshed")
                status_item.setForeground(Qt.gray)

            self.table.setItem(row, 6, status_item)

        self.table.blockSignals(False)

    def _on_table_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0:
            source_id = item.data(Qt.UserRole)
            is_enabled = (item.checkState() == Qt.Checked)
            self.db.set_source_enabled(source_id, is_enabled)
            self.sources_changed.emit()

    def _get_selected_source_id(self) -> Optional[str]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _add_source(self):
        dialog = SourceDialog(self)
        if dialog.exec():
            data = dialog.get_source_data()
            self.db.add_source(
                source_id=data["id"],
                name=data["name"],
                source_type=data["source_type"],
                url_or_path=data["url_or_path"],
                enabled=data["enabled"],
            )
            self.reload_sources()
            self.sources_changed.emit()

    def _edit_selected(self):
        source_id = self._get_selected_source_id()
        if not source_id:
            return
        src = self.db.get_source(source_id)
        if not src:
            return

        dialog = SourceDialog(self, source=src)
        if dialog.exec():
            data = dialog.get_source_data()
            self.db.add_source(
                source_id=source_id,
                name=data["name"],
                source_type=data["source_type"],
                url_or_path=data["url_or_path"],
                enabled=data["enabled"],
            )
            self.reload_sources()
            self.sources_changed.emit()

    def _remove_selected(self):
        source_id = self._get_selected_source_id()
        if not source_id:
            return

        reply = QMessageBox.question(
            self,
            "Remove Source",
            "Are you sure you want to remove this source?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.db.delete_source(source_id)
            self.reload_sources()
            self.sources_changed.emit()

    def _refresh_selected(self):
        source_id = self._get_selected_source_id()
        if source_id:
            self.source_refresh_requested.emit(source_id)
