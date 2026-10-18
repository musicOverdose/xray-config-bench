"""Xray Core binary detector, version checker, and official release downloader."""

import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
from typing import Callable, Optional, Tuple
import zipfile
import requests

from .database import DEFAULT_CONFIG_DIR

MANAGED_BIN_DIR = DEFAULT_CONFIG_DIR / "bin"
MANAGED_XRAY_PATH = MANAGED_BIN_DIR / "xray"

XRAY_RELEASE_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
XRAY_CHECKSUM_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip.dgst"


def find_xray_binary(custom_path: Optional[str] = None) -> Optional[Path]:
    """Find the Xray binary path."""
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            return p

    # Check managed installation
    if MANAGED_XRAY_PATH.is_file() and os.access(MANAGED_XRAY_PATH, os.X_OK):
        return MANAGED_XRAY_PATH

    # Check PATH
    which_path = shutil.which("xray")
    if which_path:
        return Path(which_path)

    # Check standard Unix locations
    candidates = [
        Path.home() / ".local" / "bin" / "xray",
        Path("/usr/local/bin/xray"),
        Path("/usr/bin/xray"),
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c

    return None


def get_xray_version(binary_path: Path) -> Tuple[bool, str]:
    """Run `xray version` and return (is_valid, version_string)."""
    if not binary_path or not binary_path.is_file():
        return False, "Binary not found"
    try:
        proc = subprocess.run(
            [str(binary_path), "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            first_line = proc.stdout.strip().splitlines()[0] if proc.stdout else "Xray (unknown version)"
            return True, first_line
        return False, f"Process returned code {proc.returncode}: {proc.stderr.strip()}"
    except Exception as exc:
        return False, str(exc)


def download_official_xray(
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    timeout: int = 30,
) -> Path:
    """
    Download official Xray-linux-64.zip from XTLS/Xray-core, verify checksum if available,
    extract the xray binary to ~/.config/xray-config-bench/bin/xray, and make it executable.
    """
    MANAGED_BIN_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = MANAGED_BIN_DIR / "Xray-linux-64.zip"

    if progress_callback:
        progress_callback(0, 100, "Downloading Xray-core release...")

    # Download archive
    with requests.get(XRAY_RELEASE_URL, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(archive_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        percent = int((downloaded / total_size) * 80)
                        progress_callback(percent, 100, f"Downloading: {downloaded // 1024} KB / {total_size // 1024} KB")

    # Attempt checksum verification
    try:
        if progress_callback:
            progress_callback(85, 100, "Verifying checksum...")
        dgst_resp = requests.get(XRAY_CHECKSUM_URL, timeout=10)
        if dgst_resp.status_code == 200:
            dgst_text = dgst_resp.text
            # Look for SHA256 or SHA512 in dgst text
            sha256_match = re.search(r"SHA256\s*=\s*([a-fA-F0-9]{64})", dgst_text)
            if sha256_match:
                expected_sha256 = sha256_match.group(1).lower()
                hasher = hashlib.sha256()
                with open(archive_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        hasher.update(chunk)
                actual_sha256 = hasher.hexdigest().lower()
                if actual_sha256 != expected_sha256:
                    archive_path.unlink(missing_ok=True)
                    raise ValueError(f"Checksum mismatch: expected {expected_sha256}, got {actual_sha256}")
    except requests.RequestException:
        # Checksum file not reachable, proceed with downloaded zip
        pass

    # Extract binary
    if progress_callback:
        progress_callback(90, 100, "Extracting binary...")

    with zipfile.ZipFile(archive_path, "r") as zf:
        if "xray" not in zf.namelist():
            raise ValueError("Invalid Xray release archive: missing 'xray' binary")
        zf.extract("xray", path=MANAGED_BIN_DIR)

    # Make executable
    MANAGED_XRAY_PATH.chmod(MANAGED_XRAY_PATH.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Clean up zip
    archive_path.unlink(missing_ok=True)

    if progress_callback:
        progress_callback(100, 100, "Xray-core successfully installed")

    return MANAGED_XRAY_PATH
