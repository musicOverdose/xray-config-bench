"""Unit tests for isolated ProxyRunner process lifecycle and port allocation."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.config_parser.vless import parse_vless
from app.proxy_runner import ProxyRunner, allocate_free_port


def test_allocate_free_port():
    port1 = allocate_free_port()
    port2 = allocate_free_port()
    assert 1024 <= port1 <= 65535
    assert 1024 <= port2 <= 65535


@patch("subprocess.Popen")
@patch("app.proxy_runner.wait_for_port", return_value=True)
def test_proxy_runner_context_manager_cleanup(mock_wait, mock_popen, tmp_path):
    # Mock active subprocess
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_popen.return_value = mock_proc

    link = "vless://test-uuid@1.2.3.4:443#TestNode"
    cfg = parse_vless(link)

    fake_xray = tmp_path / "xray"
    fake_xray.touch()

    runner = ProxyRunner(fake_xray, cfg)
    with runner as port:
        assert port > 1024
        assert runner.temp_file.exists()
        saved_temp_path = runner.temp_file

    # After exit: process terminated and temp file deleted
    mock_proc.terminate.assert_called_once()
    assert not saved_temp_path.exists()
    assert runner.temp_file is None
