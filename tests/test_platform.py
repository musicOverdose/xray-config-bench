"""Cross-platform unit tests for paths, asset naming, binary detection, and process handling."""

import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch
import pytest

from app.core_manager import (
    get_xray_asset_name,
    get_xray_binary_name,
    find_xray_binary,
    get_xray_version,
)
from app.paths import (
    get_app_config_dir,
    get_app_data_dir,
    get_bin_dir,
    get_db_path,
    get_tmp_dir,
)
from app.proxy_runner import ProxyRunner
from app.config_parser.vless import parse_vless


def test_paths_creation():
    config_dir = get_app_config_dir()
    data_dir = get_app_data_dir()
    db_path = get_db_path()
    bin_dir = get_bin_dir()
    tmp_dir = get_tmp_dir()

    assert config_dir.exists()
    assert data_dir.exists()
    assert bin_dir.exists()
    assert tmp_dir.exists()
    assert db_path.parent == config_dir


def test_windows_paths_mock(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    with patch("platformdirs.user_config_dir", return_value="C:\\Users\\User\\AppData\\Roaming\\xray-config-bench"):
        with patch("platformdirs.user_data_dir", return_value="C:\\Users\\User\\AppData\\Local\\xray-config-bench"):
            with patch("pathlib.Path.mkdir"):
                cfg_dir = get_app_config_dir()
                data_dir = get_app_data_dir()
                assert "AppData" in str(cfg_dir)
                assert "AppData" in str(data_dir)


def test_xray_binary_name():
    assert get_xray_binary_name("linux") == "xray"
    assert get_xray_binary_name("Linux") == "xray"
    assert get_xray_binary_name("windows") == "xray.exe"
    assert get_xray_binary_name("win32") == "xray.exe"
    assert get_xray_binary_name("Windows") == "xray.exe"
    assert get_xray_binary_name("darwin") == "xray"


def test_xray_asset_selection():
    # Windows
    assert get_xray_asset_name("windows", "x86_64") == "Xray-windows-64.zip"
    assert get_xray_asset_name("win32", "AMD64") == "Xray-windows-64.zip"
    assert get_xray_asset_name("windows", "arm64") == "Xray-windows-arm64-v8a.zip"
    assert get_xray_asset_name("windows", "i386") == "Xray-windows-32.zip"

    # Linux
    assert get_xray_asset_name("linux", "x86_64") == "Xray-linux-64.zip"
    assert get_xray_asset_name("Linux", "aarch64") == "Xray-linux-arm64-v8a.zip"
    assert get_xray_asset_name("linux", "arm64") == "Xray-linux-arm64-v8a.zip"

    # macOS
    assert get_xray_asset_name("darwin", "arm64") == "Xray-macos-arm64-v8a.zip"
    assert get_xray_asset_name("darwin", "x86_64") == "Xray-macos-64.zip"


def test_find_xray_binary_custom_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    fake_exe = tmp_path / "xray.exe"
    fake_exe.touch()

    # Pass without .exe extension; should automatically resolve on Windows
    found = find_xray_binary(str(tmp_path / "xray"))
    assert found == fake_exe


@patch("subprocess.run")
def test_get_xray_version_windows_flags(mock_run, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    fake_exe = tmp_path / "xray.exe"
    fake_exe.touch()

    mock_run.return_value = subprocess.CompletedProcess(
        args=[str(fake_exe), "version"],
        returncode=0,
        stdout="Xray 1.8.24 (Xray, Penetrates Everything.)\n",
        stderr="",
    )

    ok, ver = get_xray_version(fake_exe)
    assert ok is True
    assert "1.8.24" in ver

    # Check that creationflags were passed on Windows
    kwargs = mock_run.call_args.kwargs
    assert "creationflags" in kwargs


@patch("subprocess.Popen")
@patch("app.proxy_runner.wait_for_port", return_value=True)
def test_proxy_runner_windows_creationflags(mock_wait, mock_popen, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_popen.return_value = mock_proc

    link = "vless://uuid-test@1.2.3.4:443#WinTest"
    cfg = parse_vless(link)
    fake_exe = tmp_path / "xray.exe"
    fake_exe.touch()

    runner = ProxyRunner(fake_exe, cfg)
    with runner as port:
        assert port > 1024
        # Verify creationflags passed to Popen
        kwargs = mock_popen.call_args.kwargs
        assert "creationflags" in kwargs

    mock_proc.terminate.assert_called_once()


def test_download_official_xray_extraction(tmp_path, monkeypatch):
    """Verify that download_official_xray extracts binary and assets from zip properly without NameError."""
    import io
    import zipfile
    from app.core_manager import download_official_xray

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setattr("app.core_manager.get_bin_dir", lambda: bin_dir)

    # Create dummy zip with xray binary and geoip.dat
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("xray", b"fake-xray-binary-content")
        zf.writestr("geoip.dat", b"fake-geoip-data")
    zip_bytes = zip_buffer.getvalue()

    # Mock requests.get
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(zip_bytes))}
    mock_resp.iter_content.return_value = [zip_bytes]
    mock_resp.text = ""
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("requests.get", return_value=mock_resp):
        installed_path = download_official_xray(system="linux", machine="x86_64")

    assert installed_path.exists()
    assert installed_path.read_bytes() == b"fake-xray-binary-content"
    assert (bin_dir / "geoip.dat").exists()
    assert (bin_dir / "geoip.dat").read_bytes() == b"fake-geoip-data"

