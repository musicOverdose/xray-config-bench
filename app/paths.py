"""Cross-platform directory and path resolution using platformdirs."""

import os
from pathlib import Path
import sys
import platformdirs

APP_NAME = "xray-config-bench"


def get_app_config_dir() -> Path:
    """
    Get platform-appropriate configuration directory.
    Preserves existing Linux ~/.config/xray-config-bench if present.
    """
    # Backwards compatibility check for existing Linux configs
    legacy_linux_dir = Path.home() / ".config" / APP_NAME
    if sys.platform != "win32" and legacy_linux_dir.exists():
        return legacy_linux_dir

    config_dir = Path(platformdirs.user_config_dir(appname=APP_NAME, appauthor=False))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_app_data_dir() -> Path:
    """Get platform-appropriate application data directory."""
    # If legacy Linux dir exists and has data, reuse it
    legacy_linux_dir = Path.home() / ".config" / APP_NAME
    if sys.platform != "win32" and legacy_linux_dir.exists():
        return legacy_linux_dir

    data_dir = Path(platformdirs.user_data_dir(appname=APP_NAME, appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    """Return default path to SQLite database."""
    return get_app_config_dir() / "xray_bench.db"


def get_bin_dir() -> Path:
    """Return directory for managed Xray binaries."""
    bin_dir = get_app_data_dir() / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


def get_tmp_dir() -> Path:
    """Return directory for temporary configuration files."""
    tmp_dir = get_app_data_dir() / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir
