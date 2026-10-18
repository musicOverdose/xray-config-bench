"""Consistent modern dark theme stylesheet and color palette for PySide6."""

DARK_THEME_QSS = """
/* Global Window and Base Styles */
QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: 'Segoe UI', 'Ubuntu', 'Noto Sans', sans-serif;
    font-size: 13px;
    selection-background-color: #3d59a1;
    selection-color: #ffffff;
}

QMainWindow, QDialog {
    background-color: #16161e;
}

/* Tab Bar */
QTabWidget::pane {
    border: 1px solid #292e42;
    background-color: #1a1b26;
    border-radius: 6px;
    padding: 4px;
}

QTabBar::tab {
    background-color: #1f2335;
    color: #7aa2f7;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #292e42;
    border-bottom: none;
    font-weight: bold;
}

QTabBar::tab:selected {
    background-color: #24283b;
    color: #bb9af7;
    border-bottom: 2px solid #7aa2f7;
}

QTabBar::tab:hover:!selected {
    background-color: #292e42;
    color: #7dcfff;
}

/* Push Buttons */
QPushButton {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #3b4261;
    border-color: #7aa2f7;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #2ac3de;
    color: #1a1b26;
}

QPushButton:disabled {
    background-color: #1f2335;
    color: #565f89;
    border-color: #292e42;
}

/* Primary Action Buttons */
QPushButton#primaryBtn {
    background-color: #7aa2f7;
    color: #15161e;
    border: 1px solid #7aa2f7;
}

QPushButton#primaryBtn:hover {
    background-color: #89b4fa;
    color: #15161e;
}

QPushButton#dangerBtn {
    background-color: #f7768e;
    color: #15161e;
    border: 1px solid #f7768e;
}

QPushButton#dangerBtn:hover {
    background-color: #ff9eaf;
}

/* LineEdits and TextEdits */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #7aa2f7;
    background-color: #24283b;
}

/* Tables and Tree Views */
QTableWidget, QTableView {
    background-color: #1a1b26;
    alternate-background-color: #1f2335;
    gridline-color: #292e42;
    border: 1px solid #292e42;
    border-radius: 6px;
    color: #c0caf5;
    selection-background-color: #3d59a1;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #1f2335;
    color: #7aa2f7;
    padding: 8px;
    border: 1px solid #292e42;
    font-weight: bold;
}

/* Progress Bar */
QProgressBar {
    background-color: #1f2335;
    border: 1px solid #414868;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 22px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7aa2f7, stop:1 #bb9af7);
    border-radius: 5px;
}

/* Scroll Bars */
QScrollBar:vertical {
    background: #16161e;
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #414868;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #7aa2f7;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Labels and GroupBoxes */
QGroupBox {
    font-weight: bold;
    color: #bb9af7;
    border: 1px solid #292e42;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    background-color: #1f2335;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    color: #c0caf5;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #414868;
    border-radius: 4px;
    background-color: #1f2335;
}

QCheckBox::indicator:checked {
    background-color: #7aa2f7;
    border-color: #7aa2f7;
}

/* Status Bar */
QStatusBar {
    background-color: #16161e;
    color: #7aa2f7;
    border-top: 1px solid #292e42;
}
"""


def get_protocol_badge_color(protocol: str) -> str:
    """Return styling color for protocol badges."""
    p = protocol.lower()
    if p == "vless":
        return "#7aa2f7"  # Tokyo blue
    elif p == "vmess":
        return "#bb9af7"  # Tokyo purple
    elif p == "trojan":
        return "#f7768e"  # Tokyo red / coral
    elif p in ("shadowsocks", "ss"):
        return "#e0af68"  # Tokyo yellow / amber
    return "#7dcfff"


def get_status_color(status: str) -> str:
    """Return styling color for status badges."""
    s = (status or "").lower()
    if s == "working":
        return "#9ece6a"  # Green
    elif s == "failed":
        return "#f7768e"  # Red
    return "#565f89"  # Gray / Untested
