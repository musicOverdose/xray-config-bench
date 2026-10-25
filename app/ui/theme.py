"""High-DPI scalable modern dark theme stylesheet and color palette."""

DARK_THEME_QSS = """
/* Global Window and Base Styles */
QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Ubuntu', 'Noto Sans', sans-serif;
    font-size: 10pt;
    selection-background-color: #3d59a1;
    selection-color: #ffffff;
}

QMainWindow, QDialog {
    background-color: #16161e;
}

/* Sidebar Navigation Frame */
#sidebarFrame {
    background-color: #13141c;
    border-right: 1px solid #24283b;
    min-width: 170px;
    max-width: 210px;
}

#navBtn {
    background-color: transparent;
    color: #7982a9;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 10.5pt;
    font-weight: 600;
}

#navBtn:hover {
    background-color: #1f2335;
    color: #c0caf5;
}

#navBtn:checked {
    background-color: #24283b;
    color: #7aa2f7;
    font-weight: bold;
    border-left: 3px solid #7aa2f7;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
}

/* Content Area */
#contentStack {
    background-color: #1a1b26;
}

/* Page Header */
#pageHeader {
    background-color: #16161e;
    border-bottom: 1px solid #24283b;
    padding: 12px 18px;
}

#pageTitle {
    font-size: 14pt;
    font-weight: bold;
    color: #7aa2f7;
}

/* Push Buttons */
QPushButton {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 20px;
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

/* LineEdits and Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 18px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #7aa2f7;
    background-color: #24283b;
}

/* Tables */
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
    padding: 7px;
    border: 1px solid #292e42;
    font-weight: bold;
    font-size: 9.5pt;
}

/* Progress Bar */
QProgressBar {
    background-color: #1f2335;
    border: 1px solid #414868;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    min-height: 20px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7aa2f7, stop:1 #bb9af7);
    border-radius: 5px;
}

/* Scroll Bars */
QScrollBar:vertical {
    background: #16161e;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #414868;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #7aa2f7;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* GroupBoxes */
QGroupBox {
    font-weight: bold;
    color: #bb9af7;
    border: 1px solid #292e42;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    background-color: #1f2335;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    color: #c0caf5;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
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
    background-color: #13141c;
    color: #7aa2f7;
    border-top: 1px solid #24283b;
    padding: 4px 8px;
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
        return "#f7768e"  # Tokyo coral
    elif p in ("shadowsocks", "ss"):
        return "#e0af68"  # Tokyo amber
    return "#7dcfff"


def get_status_color(status: str) -> str:
    """Return styling color for status badges."""
    s = (status or "").lower()
    if s == "working":
        return "#9ece6a"  # Green
    elif s == "failed":
        return "#f7768e"  # Red
    return "#565f89"  # Gray
