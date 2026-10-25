# Xray Config Bench

A modern, cross-platform graphical desktop application for discovering, testing, speed benchmarking, and ranking V2Ray/Xray configurations. Built with **Python 3** and **PySide6 (Qt for Python)**, supporting both **Windows 10/11** and **Linux** (Debian, Ubuntu, KDE Plasma, GNOME).

[![CI & Cross-Platform Builds](https://github.com/musicOverdose/xray-config-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/musicOverdose/xray-config-bench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)

---

## Key Features

- **Cross-Platform by Architecture**:
  - Full compatibility with **Windows 10/11** and **Linux** (x86_64 and ARM64).
  - Uses `platformdirs` for OS-compliant configuration and cache directories (`%APPDATA%` on Windows, `~/.config/` on Linux).
  - Process isolation with Windows `CREATE_NO_WINDOW` support and reliable file unlocking.
- **Dynamic Configuration Source Discovery**:
  - **Direct subscription URLs**: Automatically detects and decodes plain-text or Base64-encoded subscription responses.
  - **GitHub repository URLs**: Discovers text configuration feeds across nested directory trees using the GitHub REST API, filtering out binaries with pagination and rate-limit backoff.
  - **Raw GitHub URLs & HTTP/HTTPS text feeds**: Directly streams and extracts candidate proxies.
  - **Local text files**: File browser integration for offline or locally saved configuration lists.
  - Full GUI management: add, edit, remove, enable/disable, and refresh sources individually or all at once.
- **Supported Protocols & Security Preserved**:
  - `vless://`, `vmess://`, `trojan://`, and `ss://` (Shadowsocks SIP002 & legacy).
  - Preserves transport and security parameters: TLS, SNI, ALPN, Reality public keys (`pbk`), short IDs (`sid`), spiderX (`spx`), uTLS fingerprints (`fp`), WebSocket paths/hosts, gRPC service names, and XTLS flow control (`xtls-rprx-vision`).
  - SHA-256 deduplication eliminates redundant testing of identical nodes across different feeds.
- **Isolated Testing Backend**:
  - Automatically identifies local Xray Core executables (`xray.exe` on Windows, `xray` on Linux).
  - Built-in OS-aware downloader automatically fetches and verifies the correct release asset (`Xray-windows-64.zip`, `Xray-linux-64.zip`, `Xray-windows-arm64-v8a.zip`, etc.) from official XTLS/Xray-core releases.
  - Spawns isolated Xray child processes with dynamic ephemeral ports bound strictly to `127.0.0.1`.
- **Multi-Stage Real-World Benchmarking**:
  - **Connectivity validation**: End-to-end HTTP/HTTPS probes.
  - **Error classification**: Categorizes failures (*TLS handshake failure*, *Connection timeout*, *DNS resolution failure*, *Remote server unreachable*, *Authentication or protocol error*, and *Backend startup failure*).
  - **Latency measurement**: Median response time and jitter/variance over multiple attempts.
  - **Download throughput**: Real streaming speed measurement in Mbps (bounded to 2 MB by default, max 10 MB) to prevent bandwidth saturation.
  - **Stability score**: Measures packet delivery and success rate over repeated attempts.
- **Fair Composite Ranking**:
  - Normalized multi-factor score (0 - 100) balancing connectivity, latency, throughput, and stability.
  - Configurable weights and penalty rules (failed nodes score 0).
- **Local Storage & Zero Telemetry**:
  - All configurations, results, and settings persist locally in SQLite (`xray_bench.db`).
  - Automatic credential redaction: UUIDs, passwords, and tokens are scrubbed from diagnostic logs and UI tables.

---

## Installation & Launch

### Windows 10 / 11

#### Prerequisites
Install **Python 3.10 or newer** from the [official website](https://www.python.org/downloads/windows/).
> [!IMPORTANT]
> During installation, check the box: **"Add Python to PATH"**.

#### Option A: Using PowerShell (Recommended)
Open PowerShell, navigate to the folder, and run:
```powershell
git clone https://github.com/musicOverdose/xray-config-bench.git
cd xray-config-bench
.\launch.ps1
```
*If script execution is restricted on your system, enable it for the current process:*
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\launch.ps1
```

#### Option B: Using Command Prompt / Batch
Double-click `launch.bat` or run:
```cmd
launch.bat
```
The script will automatically create a `.venv`, install requirements, and start the GUI.

#### Option C: Building a Standalone Windows Executable
You can package a single standalone `.exe` using PyInstaller:
```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller xray-config-bench.spec
```
The resulting executable will be in `dist\xray-config-bench.exe`.

> [!NOTE]
> **Windows Defender & SmartScreen Notice**: Unsigned executables built from source or downloaded from GitHub Actions may trigger Windows SmartScreen ("Windows protected your PC"). Click **"More info"** and then **"Run anyway"**.

---

### Linux (Debian 13 Trixie, Ubuntu 22.04+, Arch, Fedora)

#### System Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl
```

#### Launching with `launch.sh`
```bash
git clone https://github.com/musicOverdose/xray-config-bench.git
cd xray-config-bench
./launch.sh
```

#### Desktop Launcher
To integrate with your desktop menu (KDE Plasma, GNOME, etc.):
```bash
cp xray-config-bench.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

---

## Operating System Paths

| Platform | Configuration & SQLite Database | Managed Binaries & Temp Configs |
| :--- | :--- | :--- |
| **Windows** | `%APPDATA%\xray-config-bench\` | `%LOCALAPPDATA%\xray-config-bench\` |
| **Linux** | `~/.config/xray-config-bench/` | `~/.config/xray-config-bench/` or `~/.local/share/` |

---

## Managing Configuration Sources

You can add and manage multiple configuration feeds directly from the GUI without writing code:

### 1. Instant Setup (Recommended Sources)
In the **Sources** tab, click **"Load Recommended"**. This immediately populates vetted, active community sources covering VLESS Reality, Trojan, VMess, and Shadowsocks.

### 2. Adding Custom Sources
1. Click on the **Sources** tab.
2. Click **"+ Add Source"**.
3. Choose the source type:
   - **Subscription URL**: Enter any public subscription feed (plain-text or Base64).
   - **GitHub Repository**: Enter a repository URL (e.g. `https://github.com/freefq/free` or `https://github.com/owner/repo/tree/branch/subfolder`). The application inspects the repository's tree via the GitHub API, retrieves eligible text files, and parses proxy links across nested subdirectories.
   - **Raw GitHub File**: Direct link to a raw file (e.g. `https://raw.githubusercontent.com/.../nodes.txt`).
   - **Local File**: Click "Browse..." to select any text file on your local machine.
4. Enter an optional display name and click **OK**.
5. Click **"Refresh Selected"** or **"Refresh All Enabled"**. Discovered configurations are automatically validated, deduplicated, and displayed in the Results tab.

### Popular Community Sources

| Source Name | Type | URL |
| :--- | :--- | :--- |
| **Barry-Far All Protocols** | Subscription | `https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt` |
| **Barry-Far VLESS Reality** | Subscription | `https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vless.txt` |
| **Barry-Far Trojan** | Subscription | `https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/trojan.txt` |
| **Barry-Far VMess** | Subscription | `https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vmess.txt` |
| **FreeFQ Community Nodes** | Subscription | `https://raw.githubusercontent.com/freefq/free/master/v2` |
| **Pawdroid Free Servers** | Subscription | `https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub` |
| **Yebekhe Telegram Collector** | Subscription | `https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix` |
| **Mahdi0024 ProxyCollector** | Subscription | `https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/master/sub/proxies.txt` |
| **FreeFQ Repository** | GitHub Repo | `https://github.com/freefq/free` |

---

## Benchmarking & Ranking Workflow

1. In the top toolbar, toggle:
   - **"Test Untested Only"** (recommended for quick incremental updates) or uncheck to retest all candidates.
   - **"Enable Speed Test"** (uncheck for fast latency-only scans).
2. Click **"Start Benchmark"**.
3. The application runs tests with configurable concurrency (default: 3 parallel workers).
4. Results appear in real-time in the **Results** table with:
   - Protocol badge
   - Connection status (Working / Failed)
   - Median latency (ms) and latency variance/jitter (ms)
   - Download speed (Mbps)
   - Reliability / success rate (%)
   - Composite ranking score (0 - 100)
5. **Exporting**:
   - Select rows and click **"Export Selected"**.
   - Click **"Export All Working"** or **"Export Top N..."** to save winners to a text file or copy directly to your clipboard.

---

## Automated Tests

Run the test suite across both platforms:

```bash
source .venv/bin/activate  # Linux
# or .venv\Scripts\activate on Windows

QT_QPA_PLATFORM=offscreen pytest -v
```

The test suite covers:
- Protocol parsers (`vless`, `vmess`, `trojan`, `shadowsocks`, edge cases, Base64 padding).
- OS-aware asset discovery and binary naming (`xray.exe` on Windows, `xray` on Linux).
- Cross-platform paths and temporary directory handling (`platformdirs`).
- Ephemeral port reservation and subprocess creation flags (`CREATE_NO_WINDOW`).
- Mocked GitHub tree crawling and rate-limit backoff.
- Credential scrubbing and privacy enforcement.
- PySide6 GUI window and widget initialization.

---

## License

This project is licensed under the [MIT License](LICENSE).
