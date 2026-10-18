"""Multi-stage benchmark pipeline: connectivity, latency, download speed, and stability."""

from dataclasses import dataclass
import statistics
import time
from typing import Callable, List, Optional
import requests

from .security import redact_credentials

DEFAULT_TEST_ENDPOINTS = [
    "https://cp.cloudflare.com/generate_204",
    "https://www.google.com/generate_204",
    "https://www.gstatic.com/generate_204",
]

DEFAULT_DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes=2097152"  # 2 MB
DEFAULT_DOWNLOAD_BYTES = 2 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024


@dataclass
class BenchmarkResult:
    status: str  # 'working' or 'failed'
    error_category: Optional[str] = None
    error_detail: Optional[str] = None
    latency_ms: Optional[float] = None
    latency_variance: Optional[float] = None
    download_speed_mbps: Optional[float] = None
    success_rate: float = 0.0
    score: float = 0.0


def classify_network_error(exc: Exception) -> str:
    """Categorize network exceptions into standard descriptive categories."""
    msg = str(exc).lower()

    if "timeout" in msg or "timed out" in msg:
        return "Connection timeout"
    if "ssl" in msg or "tls" in msg or "handshake" in msg or "certificate" in msg:
        return "TLS handshake failure"
    if "dns" in msg or "getaddrinfo" in msg or "nameresolution" in msg:
        return "DNS resolution failure"
    if "connection refused" in msg or "unreachable" in msg or "refused" in msg:
        return "Remote server unreachable"
    if "auth" in msg or "password" in msg or "401" in msg or "407" in msg:
        return "Authentication or protocol error"
    if "bad response" in msg or "empty response" in msg or "502" in msg or "504" in msg:
        return "HTTP probe failure"

    return "HTTP probe failure"


def make_proxies(socks_port: int) -> dict:
    """Return requests proxies dictionary routing DNS and traffic through SOCKS5."""
    proxy_url = f"socks5h://127.0.0.1:{socks_port}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def measure_single_probe(
    socks_port: int,
    endpoint: str,
    timeout: float = 5.0,
) -> float:
    """
    Execute a single HTTP/HTTPS probe and return response latency in milliseconds.
    Raises exception on connection or HTTP failure.
    """
    proxies = make_proxies(socks_port)
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) XrayConfigBench/1.0"}

    start = time.perf_counter()
    resp = requests.get(
        endpoint,
        proxies=proxies,
        headers=headers,
        timeout=timeout,
        allow_redirects=True,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    if resp.status_code not in (200, 204, 301, 302, 307):
        raise requests.RequestException(f"HTTP probe returned status {resp.status_code}")

    return elapsed_ms


def test_latency_and_stability(
    socks_port: int,
    endpoints: List[str],
    attempts: int = 3,
    timeout: float = 5.0,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> tuple[float, float, float]:
    """
    Measure latency across multiple attempts and endpoints.
    Returns (median_latency_ms, latency_variance, success_rate).
    """
    if not endpoints:
        endpoints = DEFAULT_TEST_ENDPOINTS

    latencies: List[float] = []
    total_attempts = 0
    success_count = 0

    for i in range(attempts):
        if cancel_check and cancel_check():
            break

        # Pick endpoint round-robin
        ep = endpoints[i % len(endpoints)]
        total_attempts += 1
        try:
            lat = measure_single_probe(socks_port, ep, timeout=timeout)
            latencies.append(lat)
            success_count += 1
        except Exception:
            # Failed attempt
            pass

    if not latencies:
        return 0.0, 0.0, 0.0

    median_lat = float(statistics.median(latencies))
    lat_var = float(statistics.stdev(latencies)) if len(latencies) > 1 else 0.0
    success_rate = (success_count / max(1, total_attempts)) * 100.0

    return median_lat, lat_var, success_rate


def measure_download_speed(
    socks_port: int,
    download_url: str = DEFAULT_DOWNLOAD_URL,
    max_bytes: int = DEFAULT_DOWNLOAD_BYTES,
    timeout: float = 15.0,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> float:
    """
    Download a bounded transfer through SOCKS5 and calculate throughput in Mbps.
    Returns download speed in Mbps (0.0 on failure).
    """
    max_bytes = min(max_bytes, MAX_DOWNLOAD_BYTES)
    proxies = make_proxies(socks_port)
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) XrayConfigBench/1.0"}

    total_bytes = 0
    start_time = time.perf_counter()

    try:
        with requests.get(
            download_url,
            proxies=proxies,
            headers=headers,
            stream=True,
            timeout=timeout,
        ) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=16384):
                if cancel_check and cancel_check():
                    break
                if chunk:
                    total_bytes += len(chunk)
                    if total_bytes >= max_bytes:
                        break

        elapsed = time.perf_counter() - start_time
        if elapsed > 0.05 and total_bytes > 4096:
            # Mbps = (bytes * 8) / (seconds * 1,000,000)
            mbps = (total_bytes * 8.0) / (elapsed * 1_000_000.0)
            return round(mbps, 2)
        return 0.0
    except Exception:
        return 0.0


def benchmark_candidate(
    socks_port: int,
    endpoints: Optional[List[str]] = None,
    latency_attempts: int = 3,
    timeout: float = 5.0,
    enable_speed_test: bool = True,
    download_url: str = DEFAULT_DOWNLOAD_URL,
    download_bytes: int = DEFAULT_DOWNLOAD_BYTES,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> BenchmarkResult:
    """
    Run full benchmarking pipeline on an active candidate.
    """
    if not endpoints:
        endpoints = DEFAULT_TEST_ENDPOINTS

    # Stage 1 & 2: Latency and Stability
    # Initial connectivity probe
    first_err: Optional[Exception] = None
    initial_probe_ok = False
    for ep in endpoints:
        if cancel_check and cancel_check():
            return BenchmarkResult(status="failed", error_category="Cancelled")
        try:
            measure_single_probe(socks_port, ep, timeout=timeout)
            initial_probe_ok = True
            break
        except Exception as e:
            if not first_err:
                first_err = e

    if not initial_probe_ok:
        cat = classify_network_error(first_err) if first_err else "Connection timeout"
        err_msg = redact_credentials(str(first_err)) if first_err else "All probe endpoints failed"
        return BenchmarkResult(
            status="failed",
            error_category=cat,
            error_detail=err_msg,
            success_rate=0.0,
            score=0.0,
        )

    # Full latency attempts
    median_lat, lat_var, success_rate = test_latency_and_stability(
        socks_port=socks_port,
        endpoints=endpoints,
        attempts=latency_attempts,
        timeout=timeout,
        cancel_check=cancel_check,
    )

    if success_rate == 0.0:
        return BenchmarkResult(
            status="failed",
            error_category="Connection timeout",
            error_detail="No probe attempts succeeded",
            success_rate=0.0,
            score=0.0,
        )

    # Stage 3: Speed test (if enabled)
    speed_mbps: Optional[float] = None
    if enable_speed_test and success_rate >= 50.0:
        if not (cancel_check and cancel_check()):
            speed_mbps = measure_download_speed(
                socks_port=socks_port,
                download_url=download_url,
                max_bytes=download_bytes,
                timeout=12.0,
                cancel_check=cancel_check,
            )

    return BenchmarkResult(
        status="working",
        latency_ms=round(median_lat, 1),
        latency_variance=round(lat_var, 1),
        download_speed_mbps=speed_mbps,
        success_rate=round(success_rate, 1),
    )
