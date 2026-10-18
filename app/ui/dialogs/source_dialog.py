"""Dialog for adding or editing a proxy configuration source."""

import os
import sys
from typing import Any, Dict, Optional
import uuid
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class SourceDialog(QDialog):
    """Dialog for creating or updating a configuration source."""

    def __init__(self, parent=None, source: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.source = source
        self.setWindowTitle("Edit Source" if source else "Add Configuration Source")
        self.setMinimumWidth(540)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Community Free Nodes")
        form.addRow("Display Name:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Subscription URL (Plain/Base64)",
            "GitHub Repository URL",
            "Raw GitHub File URL",
            "HTTP/HTTPS Feed URL",
            "Local Text File",
        ])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Source Type:", self.type_combo)

        # URL / Path input with Browse button
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("https://... or /path/to/configs.txt")
        path_layout.addWidget(self.path_input)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_local_file)
        self.browse_btn.setVisible(False)
        path_layout.addWidget(self.browse_btn)

        form.addRow("URL or Path:", path_layout)

        self.enabled_check = QCheckBox("Enable this source for scans")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)

        layout.addLayout(form)

        # Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        # Populate if editing
        if self.source:
            self.name_input.setText(self.source.get("name", ""))
            self.path_input.setText(self.source.get("url_or_path", ""))
            self.enabled_check.setChecked(bool(self.source.get("enabled", 1)))
            stype = self.source.get("source_type", "subscription")
            idx_map = {
                "subscription": 0,
                "github_repo": 1,
                "raw_github": 2,
                "http_feed": 3,
                "local_file": 4,
            }
            self.type_combo.setCurrentIndex(idx_map.get(stype, 0))

    def _on_type_changed(self, index: int):
        is_local = (index == 4)
        self.browse_btn.setVisible(is_local)
        if is_local:
            ph = "C:\\path\\to\\my_configs.txt" if sys.platform == "win32" else "/home/user/my_configs.txt"
            self.path_input.setPlaceholderText(ph)
        else:
            self.path_input.setPlaceholderText("https://...")

    def _browse_local_file(self):
        filt = (
            "Text and Config Files (*.txt *.yaml *.yml *.json *.sub *.conf);;All Files (*.*)"
            if sys.platform == "win32"
            else "Text and Config Files (*.txt *.yaml *.yml *.json *.sub *.conf);;All Files (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Configuration File",
            "",
            filt,
        )
        if file_path:
            self.path_input.setText(file_path)
            if not self.name_input.text():
                self.name_input.setText(os.path.basename(file_path))

    def _validate_and_accept(self):
        name = self.name_input.text().strip()
        path = self.path_input.text().strip()
        if not path:
            self.path_input.setFocus()
            return

        if not name:
            # Auto-assign name from path
            name = path.split("/")[-1] or "Unnamed Source"
            self.name_input.setText(name)

        self.accept()

    def get_source_data(self) -> Dict[str, Any]:
        types_internal = [
            "subscription",
            "github_repo",
            "raw_github",
            "http_feed",
            "local_file",
        ]
        chosen_type = types_internal[self.type_combo.currentIndex()]

        source_id = self.source.get("id") if self.source else f"src_{uuid.uuid4().hex[:8]}"
        return {
            "id": source_id,
            "name": self.name_input.text().strip(),
            "source_type": chosen_type,
            "url_or_path": self.path_input.text().strip(),
            "enabled": self.enabled_check.isChecked(),
        }
