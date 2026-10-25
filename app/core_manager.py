"""Cross-platform Xray Core binary detector, version checker, and official release downloader."""

import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
from typing import Callable, Optional, Tuple
import zipfile
import requests

from .paths import get_bin_dir

XRAY_BASE_RELEASE_URL = "https://github.com/XTLS/Xray-core/releases/latest/download"


def get_xray_binary_name(system: Optional[str] = None) -> str:
    """Return platform-specific binary executable name (xray.exe on Windows, xray on Linux/macOS)."""
    sys_name = (system or platform.system()).lower()
    return "xray.exe" if "windows" in sys_name or sys_name == "win32" else "xray"


def get_xray_asset_name(system: Optional[str] = None, machine: Optional[str] = None) -> str:
    """
    Determine the official GitHub release asset name for current OS and architecture.
    Examples:
      - Windows x86_64: Xray-windows-64.zip
      - Windows arm64:  Xray-windows-arm64-v8a.zip
      - Linux x86_64:   Xray-linux-64.zip
      - Linux aarch64:  Xray-linux-arm64-v8a.zip
      - macOS x86_64:   Xray-macos-64.zip
      - macOS arm64:    Xray-macos-arm64-v8a.zip
    """
    sys_name = (system or platform.system()).lower()
    arch_name = (machine or platform.machine()).lower()

    # Map OS
    if "windows" in sys_name or sys_name == "win32":
        os_tag = "windows"
    elif "darwin" in sys_name or "mac" in sys_name:
        os_tag = "macos"
    else:
        os_tag = "linux"

    # Map architecture
    if arch_name in ("x86_64", "amd64", "x64"):
        arch_tag = "64"
    elif arch_name in ("aarch64", "arm64"):
        arch_tag = "arm64-v8a"
    elif arch_name in ("i386", "i686", "x86"):
        arch_tag = "32"
    elif "armv7" in arch_name:
        arch_tag = "arm32-v7a"
    else:
        arch_tag = "64"  # Default fallback

    return f"Xray-{os_tag}-{arch_tag}.zip"


def find_xray_binary(custom_path: Optional[str] = None) -> Optional[Path]:
    """Find the Xray binary path on Windows, Linux, or macOS."""
    bin_name = get_xray_binary_name()

    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.is_file():
            return p
        if sys.platform == "win32" and not p.suffix and (p.parent / f"{p.name}.exe").is_file():
            return p.parent / f"{p.name}.exe"

    # 1. Check managed installation in user data dir
    managed_path = get_bin_dir() / bin_name
    if managed_path.is_file():
        if sys.platform == "win32" or os.access(managed_path, os.X_OK):
            return managed_path

    # 2. Check system PATH
    which_path = shutil.which(bin_name) or shutil.which("xray")
    if which_path:
        return Path(which_path)

    # 3. Check standard OS locations
    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "xray" / "xray.exe",
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "xray" / "xray.exe",
            Path("C:\\xray\\xray.exe"),
        ]
    else:
        candidates = [
            Path.home() / ".local" / "bin" / "xray",
            Path("/usr/local/bin/xray"),
            Path("/usr/bin/xray"),
        ]

    for c in candidates:
        if c.is_file() and (sys.platform == "win32" or os.access(c, os.X_OK)):
            return c

    return None


def get_xray_version(binary_path: Path) -> Tuple[bool, str]:
    """Run `xray version` and return (is_valid, version_string)."""
    if not binary_path or not binary_path.is_file():
        return False, "Binary not found"

    extra_kwargs = {}
    if sys.platform == "win32":
        extra_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proc = subprocess.run(
            [str(binary_path), "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            **extra_kwargs,
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
    system: Optional[str] = None,
    machine: Optional[str] = None,
) -> Path:
    """
    Download the official Xray release asset for the target OS and architecture from XTLS/Xray-core,
    verify its checksum if available, extract the xray binary into the managed bin directory,
    and configure executable permissions.
    """
    managed_dir = get_bin_dir()
    bin_name = get_xray_binary_name(system)
    asset_name = get_xray_asset_name(system, machine)

    release_url = f"{XRAY_BASE_RELEASE_URL}/{asset_name}"
    checksum_url = f"{XRAY_BASE_RELEASE_URL}/{asset_name}.dgst"

    archive_path = managed_dir / asset_name
    target_bin_path = managed_dir / bin_name

    if progress_callback:
        progress_callback(0, 100, f"Downloading {asset_name}...")

    # 1. Download release archive
    with requests.get(release_url, stream=True, timeout=timeout) as resp:
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
                        progress_callback(
                            percent, 100, f"Downloading: {downloaded // 1024} KB / {total_size // 1024} KB"
                        )

    # 2. Checksum verification
    try:
        if progress_callback:
            progress_callback(85, 100, "Verifying checksum...")
        dgst_resp = requests.get(checksum_url, timeout=10)
        if dgst_resp.status_code == 200:
            dgst_text = dgst_resp.text
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

    # 3. Extract binary
    if progress_callback:
        progress_callback(90, 100, f"Extracting {bin_name}...")

    # Extract binary and supporting asset files (geoip.dat, geosite.dat)
    extracted_bin = False
    with zipfile.ZipFile(archive_path, "r") as zf:
        for member in zf.namelist():
            member_name = Path(member).name
            member_lower = member_name.lower()
            if member_lower == bin_name.lower():
                with zf.open(member) as source, open(target_bin_path, "wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_bin = True
            elif member_lower.endswith((".dat", ".json")) and member_name:
                with zf.open(member) as source, open(managed_dir / member_name, "wb") as target:
                    shutil.copyfileobj(source, target)

    if not extracted_bin:
        raise ValueError(f"Invalid Xray release archive: missing '{bin_name}'")

    # 4. Set executable permissions on non-Windows platforms
    if sys.platform != "win32":
        target_bin_path.chmod(target_bin_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Clean up archive
    archive_path.unlink(missing_ok=True)

    if progress_callback:
        progress_callback(100, 100, f"Xray-core successfully installed at {target_bin_path}")

    return target_bin_path
