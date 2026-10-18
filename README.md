# Xray Config Bench

A modern, high-performance desktop application for discovering, testing, speed benchmarking, and ranking V2Ray/Xray configurations. Built with **Python 3** and **PySide6 (Qt for Python)**, designed natively for Linux desktop environments (Debian, Ubuntu, KDE Plasma, GNOME).

---

## Features

- **Multi-Source Configuration Discovery**:
  - Direct subscription URLs (plain text or Base64-encoded).
  - GitHub repositories: traverses git trees via GitHub API, downloads eligible text files recursively across nested directories, with automatic rate-limit and pagination handling.
  - Raw GitHub file URLs and arbitrary HTTP/HTTPS proxy feeds.
  - Local text files with real-time file browser integration.
- **Extensible Protocol Parsers**:
  - Full support for `vless://`, `vmess://`, `trojan://`, and `ss://` (Shadowsocks SIP002 & legacy).
  - Retains all security-critical transport options: TLS, SNI, ALPN, Reality public keys (`pbk`), short IDs (`sid`), spiderX (`spx`), uTLS fingerprints (`fp`), WebSocket paths/hosts, and gRPC services/modes.
- **Isolated Real-World Xray Testing Backend**:
  - Real end-to-end HTTP/HTTPS probes through genuine isolated Xray Core processes.
  - Each candidate runs with a dedicated local SOCKS5 inbound bound exclusively to `127.0.0.1` on unique ephemeral ports.
  - Dynamic port allocation and guaranteed child process & temporary file cleanup.
  - Automatically identifies failure categories: *TLS handshake failure*, *Connection timeout*, *DNS resolution failure*, *Remote server unreachable*, *Authentication or protocol error*, and *Backend startup failure*.
- **Multi-Stage Benchmarking Pipeline**:
  - **Latency**: End-to-end response time measurement over multiple attempts with median latency and variance calculation.
  - **Download Speed**: Bounded streaming throughput measurement (Mbps) over HTTPS (default 2 MB, hard limit 10 MB). Can be restricted to top candidates or toggled off for latency-only scans.
  - **Stability**: Measures candidate reliability and packet success rates across repeated probes.
- **Fair Composite Ranking**:
  - Normalized multi-factor scoring formula balancing connectivity (35%), latency (30%), download speed (25%), and stability (10%).
  - Configurable scoring weights and penalty rules (failed nodes always score 0).
- **Security & Privacy First**:
  - Original share links and benchmark history stay strictly local in `~/.config/xray-config-bench/xray_bench.db`.
  - Automatic credential redaction: UUIDs, passwords, and tokens are masked before logging or displaying in UI tables.
  - Zero telemetry and no external analytics.
- **Desktop Usability & Exports**:
  - Native dark theme optimized for readability and dark desktop themes.
  - Export top N configurations, all working configurations, or copy sanitized summaries without credentials.

---

## Interface Overview

<!-- Screenshots Section -->
```
+-------------------------------------------------------------------------------------------------+
|  Xray Config Bench                               [Fetch Sources] [Start Benchmark] [Cancel Scan]|
+-------------------------------------------------------------------------------------------------+
| [ Dashboard ] [ Sources ] [ Results ] [ Settings ] [ Logs ]                                     |
|                                                                                                 |
|   +---------------+  +---------------+  +---------------+  +---------------+  +---------------+ |
|   |  DISCOVERED   |  |    TESTED     |  |    WORKING    |  |    FAILED     |  |    PENDING    | |
|   |      142      |  |      85       |  |      47       |  |      38       |  |      57       | |
|   +---------------+  +---------------+  +---------------+  +---------------+  +---------------+ |
|                                                                                                 |
|   Active Scan Progress: [===================================>--------] 65% (47 working)        |
|                                                                                                 |
|   Top-Performing Configuration:                                                                 |
|   +-----------------------------------------------------------------------------------------+   |
|   | [VLESS] Fast-US-Node-Reality                                                 SCORE: 96  |   |
|   | Server: 104.21.42.1:443  |  Latency: 68.2 ms  |  Speed: 18.4 Mbps                       |   |
|   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```
*(Screenshot placeholder: Rendered above using ASCII wireframe. The GUI runs natively using PySide6.)*

---

## Installation & Setup

### 1. System Requirements

- **Operating System**: Debian 13 (Trixie), Debian 12 (Bookworm), Ubuntu 22.04+, or any modern Linux distribution.
- **Desktop**: KDE Plasma, GNOME, XFCE, or any desktop session.
- **Python**: Python 3.10 or newer (tested on Python 3.13).

### 2. Debian / Ubuntu System Dependencies

Install Python 3, venv, and Git:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl
```

### 3. Clone and Setup Environment

```bash
git clone https://github.com/musicOverdose/xray-config-bench.git
cd xray-config-bench
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Launching the Application

You can launch the application in several ways:

### Option A: Using the Launch Script (Recommended)

```bash
./launch.sh
```

### Option B: Running with Python Directly

```bash
source .venv/bin/activate
python3 main.py
```

### Option C: Desktop Launcher

Install the `.desktop` launcher into your local user applications directory:

```bash
cp xray-config-bench.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

---

## Xray Core Backend

Xray Config Bench requires the **Xray Core** binary to run candidate proxies in an isolated sandbox.

### Managed Automatic Download

1. Open the application.
2. Go to the **Settings** tab.
3. Click **"Download Official Xray"**.
4. The application will securely download the latest official release (`Xray-linux-64.zip`) from [XTLS/Xray-core](https://github.com/XTLS/Xray-core), verify its checksum, extract the binary into `~/.config/xray-config-bench/bin/xray`, and set executable permissions.

### Using an Existing Installation

If you already have Xray installed (e.g. via package manager in `/usr/local/bin/xray` or `~/.local/bin/xray`), click **"Auto-Detect"** or enter its absolute path in Settings.

---

## Usage Guide

### 1. Adding Sources

Navigate to the **Sources** tab and click **"+ Add Source"**:

- **Subscription URL**: Enter any public subscription feed (plain-text or Base64).
- **GitHub Repository**: Enter a repository URL such as `https://github.com/freefq/free`. The application uses the GitHub API to discover files like `.txt`, `.sub`, and `.yaml`, downloading candidate files safely without touching binaries.
- **Raw GitHub File**: Direct link to a raw file, e.g. `https://raw.githubusercontent.com/.../nodes.txt`.
- **Local File**: Click "Browse..." to select a local text file containing configuration links.

Click **"Refresh Selected"** or **"Refresh All Enabled"** to parse and import configurations into your local database. Duplicates across multiple feeds are automatically deduplicated.

### 2. Running a Benchmark Scan

From the top toolbar or Dashboard:

1. Choose whether to **"Test Untested Only"** or retest existing nodes.
2. Choose whether to **"Enable Speed Test"** (uncheck for fast, latency-only scans).
3. Click **"Start Benchmark"**.
4. Watch real-time progress on the Dashboard, detailed metrics in Results, and sanitized events in Logs.
5. Click **"Cancel Scan"** at any time to halt testing immediately.

### 3. Understanding Metrics & Ranking

Configurations are evaluated through a real SOCKS5 socket to test actual internet connectivity:

- **Latency (ms)**: End-to-end response time for HTTP/HTTPS requests through the proxy.
- **Speed (Mbps)**: Real download throughput measured by streaming a bounded block of data (default 2 MB) through the proxy.
- **Success Rate (%)**: Reliability percentage over repeated probe attempts.
- **Variance (ms)**: Latency jitter between attempts. Lower jitter indicates a more stable connection.
- **Composite Score (0 - 100)**: Multi-factor score combining all measurements using normalized weights:
  $$\text{Score} = w_{\text{conn}} \cdot S_{\text{conn}} + w_{\text{lat}} \cdot S_{\text{lat}} + w_{\text{spd}} \cdot S_{\text{spd}} + w_{\text{stab}} \cdot S_{\text{stab}}$$

### 4. Exporting Configurations

In the **Results** tab:

- **Copy Share Link**: Copies the raw share link of the selected row.
- **Copy Safe Summary**: Copies a human-readable summary without leaking passwords or UUIDs.
- **Export Selected**: Saves selected configurations to a `.txt` file or copies them to clipboard.
- **Export All Working**: Exports all configurations that passed connectivity tests.
- **Export Top N**: Exports the top *N* highest-ranked configurations.

---

## Supported Protocols

| Protocol | Transport Networks | Security | Key Parameters Supported |
| :--- | :--- | :--- | :--- |
| **VLESS** | TCP, WebSocket, gRPC, HTTP | None, TLS, Reality | `pbk`, `sid`, `spx`, `fp`, `sni`, `flow` (`xtls-rprx-vision`), `alpn`, `path`, `host`, `serviceName` |
| **VMess** | TCP, WebSocket, gRPC, HTTP | None, TLS | Base64 JSON & URI formats, `alterId`, `cipher`, `path`, `host`, `sni`, `fp` |
| **Trojan** | TCP, WebSocket, gRPC | TLS | `sni`, `alpn`, `fp`, `path`, `host`, `serviceName` |
| **Shadowsocks** | TCP | Stream / AEAD | SIP002 & legacy formats, `aes-128-gcm`, `aes-256-gcm`, `chacha20-ietf-poly1305` |

> [!NOTE]
> *Hysteria2* and *TUIC* require the sing-box core backend and are not natively supported by standard Xray Core. They are planned for a future update with a modular backend driver.

---

## Security & Privacy Considerations

- **Local Storage Only**: Configurations, links, and benchmarks are saved exclusively in your user directory (`~/.config/xray-config-bench/`).
- **Local Inbound Isolation**: Temporary test SOCKS5 inbounds listen strictly on `127.0.0.1` and are never exposed to your local network or public interfaces.
- **Safe Sandboxing**: Source files are parsed only as text feeds. No downloaded shell scripts or arbitrary code are ever executed.
- **Automatic Redaction**: UUIDs, passwords, and tokens are scrubbed from diagnostic logs and UI views.

---

## Running the Automated Test Suite

Run pytest inside the virtual environment:

```bash
source .venv/bin/activate
QT_QPA_PLATFORM=offscreen pytest -v
```

All 39 unit and GUI integration tests mock network requests and child processes to verify:
- Parsing and parameter retention across all supported protocols.
- Base64 padding and corruption tolerance.
- Duplicate detection and database transactions.
- Credential redaction in logs and share links.
- Isolated process lifecycle and dynamic port assignment.
- Metric normalization and ranking scores.
- PySide6 GUI window and tab initialization.

---

## License

This project is licensed under the [MIT License](LICENSE).
