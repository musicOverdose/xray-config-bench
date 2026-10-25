"""Isolated Xray child process runner with ephemeral port assignment and guaranteed cross-platform cleanup."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Optional

from .config_generator import generate_test_xray_config
from .config_parser.models import ProxyConfig
from .paths import get_tmp_dir
from .security import redact_credentials


def allocate_free_port() -> int:
    """Find and allocate an unused ephemeral TCP port on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        return port


def wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    """Check if the local SOCKS port is listening and accepting connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except (socket.error, ConnectionRefusedError, OSError):
            time.sleep(0.05)
    return False


class ProxyRunner:
    """Context manager for running an isolated Xray instance for a single candidate."""

    def __init__(self, xray_path: Path, config: ProxyConfig):
        self.xray_path = xray_path
        self.config = config
        self.port: Optional[int] = None
        self.temp_file: Optional[Path] = None
        self.process: Optional[subprocess.Popen] = None

    def __enter__(self) -> int:
        self.port = allocate_free_port()
        tmp_dir = get_tmp_dir()
        self.temp_file = tmp_dir / f"bench_{self.port}_{self.config.unique_hash[:8]}.json"

        # Generate config
        conf_dict = generate_test_xray_config(self.config, self.port)
        with open(self.temp_file, "w", encoding="utf-8") as f:
            json.dump(conf_dict, f, indent=2)

        # Cross-platform subprocess flags (suppress console pop-up on Windows)
        extra_kwargs = {}
        if sys.platform == "win32":
            extra_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        # Launch Xray process
        try:
            self.process = subprocess.Popen(
                [str(self.xray_path), "run", "-c", str(self.temp_file.resolve())],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.xray_path.parent),
                **extra_kwargs,
            )
        except Exception as exc:
            self._cleanup()
            raise RuntimeError(f"Failed to start Xray process: {redact_credentials(str(exc))}")

        # Check if process crashed immediately
        time.sleep(0.1)
        if self.process.poll() is not None:
            _, stderr = self.process.communicate()
            self._cleanup()
            raise RuntimeError(f"Xray terminated immediately: {redact_credentials(stderr.strip())}")

        # Wait for port readiness
        if not wait_for_port(self.port, timeout=2.5):
            if self.process.poll() is not None:
                _, stderr = self.process.communicate()
                err_msg = stderr.strip()
            else:
                err_msg = "SOCKS inbound port did not open in time"
            self._cleanup()
            raise RuntimeError(f"Backend startup failure: {redact_credentials(err_msg)}")

        return self.port

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    def _cleanup(self):
        if self.process:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=0.5)
            except Exception:
                pass
            self.process = None

        if self.temp_file:
            # On Windows, file locks may take a few moments to release
            for _ in range(5):
                try:
                    if self.temp_file.is_file():
                        self.temp_file.unlink(missing_ok=True)
                    break
                except (PermissionError, OSError):
                    time.sleep(0.1)
            self.temp_file = None
