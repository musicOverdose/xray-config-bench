"""Qt worker threads for non-blocking source fetching, benchmarking, and core downloads."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, QThread, Signal

from .benchmark import benchmark_candidate
from .config_parser.models import ProxyConfig
from .core_manager import download_official_xray
from .database import Database
from .proxy_runner import ProxyRunner
from .ranking import ScoringWeights, calculate_score
from .security import redact_credentials
from .source_manager import SourceManager


class SourceFetchWorker(QThread):
    """Worker thread for fetching sources asynchronously without freezing the UI."""

    progress = Signal(int, int, str)
    source_finished = Signal(str, int, int, str)
    all_finished = Signal(int, int, list)
    log_message = Signal(str)

    def __init__(
        self,
        db: Database,
        source_id: Optional[str] = None,
        github_token: Optional[str] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.source_id = source_id
        self.github_token = github_token
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        sm = SourceManager(self.db)
        if self.source_id:
            src = self.db.get_source(self.source_id)
            if not src:
                self.all_finished.emit(0, 0, [f"Source not found: {self.source_id}"])
                return
            sources = [src]
        else:
            sources = [s for s in self.db.get_sources() if s["enabled"]]

        total_discovered = 0
        total_valid = 0
        errors = []

        total_count = len(sources)
        for idx, src in enumerate(sources):
            if self._is_cancelled:
                self.log_message.emit("Source fetching was cancelled.")
                break

            name = src["name"]
            self.progress.emit(idx + 1, total_count, f"Fetching {name}...")
            self.log_message.emit(f"Fetching source '{name}' ({src['url_or_path']})...")

            disc, val, err, _ = sm.fetch_source(src, github_token=self.github_token)
            total_discovered += disc
            total_valid += val

            err_str = err or ""
            if err:
                errors.append(f"{name}: {err}")
                self.log_message.emit(f"Error fetching '{name}': {err}")
            else:
                self.log_message.emit(f"Source '{name}': Discovered {disc}, valid {val} configs.")

            self.source_finished.emit(src["id"], disc, val, err_str)

        self.progress.emit(total_count, total_count, "Done fetching.")
        self.all_finished.emit(total_discovered, total_valid, errors)


class BenchmarkWorker(QThread):
    """Worker thread running concurrent candidate connectivity and speed tests."""

    progress = Signal(int, int, str)
    candidate_tested = Signal(dict)
    finished = Signal(int, int)
    log_message = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        db: Database,
        xray_path: Path,
        configs: List[ProxyConfig],
        max_parallel: int = 3,
        latency_attempts: int = 3,
        timeout: float = 5.0,
        enable_speed_test: bool = True,
        download_url: str = "https://speed.cloudflare.com/__down?bytes=2097152",
        download_bytes: int = 2 * 1024 * 1024,
        max_speed_candidates: int = 10,
        weights: Optional[ScoringWeights] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.xray_path = xray_path
        self.configs = configs
        self.max_parallel = max(1, min(max_parallel, 10))
        self.latency_attempts = latency_attempts
        self.timeout = timeout
        self.enable_speed_test = enable_speed_test
        self.download_url = download_url
        self.download_bytes = download_bytes
        self.max_speed_candidates = max_speed_candidates
        self.weights = weights or ScoringWeights()

        self._is_cancelled = False
        self._lock = threading.Lock()
        self._completed_count = 0
        self._working_count = 0
        self._failed_count = 0
        self._speed_tested_count = 0

    def cancel(self):
        self._is_cancelled = True

    def _test_single_candidate(self, config: ProxyConfig) -> Dict[str, Any]:
        """Test a single configuration through an isolated Xray process."""
        if self._is_cancelled:
            return {"config": config, "status": "failed", "error": "Cancelled"}

        # Determine if this candidate should get speed tested
        with self._lock:
            allow_speed = self.enable_speed_test and (self._speed_tested_count < self.max_speed_candidates)

        runner = ProxyRunner(self.xray_path, config)
        try:
            with runner as port:
                bench = benchmark_candidate(
                    socks_port=port,
                    latency_attempts=self.latency_attempts,
                    timeout=self.timeout,
                    enable_speed_test=allow_speed,
                    download_url=self.download_url,
                    download_bytes=self.download_bytes,
                    cancel_check=lambda: self._is_cancelled,
                )

                if bench.download_speed_mbps is not None and bench.download_speed_mbps > 0:
                    with self._lock:
                        self._speed_tested_count += 1

                score = calculate_score(
                    status=bench.status,
                    latency_ms=bench.latency_ms,
                    latency_variance=bench.latency_variance,
                    download_speed_mbps=bench.download_speed_mbps,
                    success_rate=bench.success_rate,
                    weights=self.weights,
                )
                bench.score = score

                # Save result to DB
                self.db.record_benchmark_result(
                    config_hash=config.unique_hash,
                    status=bench.status,
                    error_category=bench.error_category,
                    error_detail=bench.error_detail,
                    latency_ms=bench.latency_ms,
                    latency_variance=bench.latency_variance,
                    download_speed_mbps=bench.download_speed_mbps,
                    success_rate=bench.success_rate,
                    score=bench.score,
                )

                return {
                    "config": config,
                    "status": bench.status,
                    "latency_ms": bench.latency_ms,
                    "latency_variance": bench.latency_variance,
                    "download_speed_mbps": bench.download_speed_mbps,
                    "success_rate": bench.success_rate,
                    "score": bench.score,
                    "error_category": bench.error_category,
                    "error_detail": bench.error_detail,
                }

        except Exception as exc:
            err_detail = redact_credentials(str(exc))
            err_cat = "Backend startup failure" if "startup" in err_detail.lower() else "Connection timeout"
            self.db.record_benchmark_result(
                config_hash=config.unique_hash,
                status="failed",
                error_category=err_cat,
                error_detail=err_detail,
                latency_ms=None,
                download_speed_mbps=None,
                success_rate=0.0,
                score=0.0,
            )
            return {
                "config": config,
                "status": "failed",
                "latency_ms": None,
                "download_speed_mbps": None,
                "success_rate": 0.0,
                "score": 0.0,
                "error_category": err_cat,
                "error_detail": err_detail,
            }

    def run(self):
        if not self.xray_path or not self.xray_path.is_file():
            self.error.emit(f"Xray binary not found at '{self.xray_path}'")
            return

        total_configs = len(self.configs)
        if total_configs == 0:
            self.finished.emit(0, 0)
            return

        self.log_message.emit(
            f"Starting scan on {total_configs} configurations with {self.max_parallel} concurrent workers..."
        )

        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = {
                executor.submit(self._test_single_candidate, cfg): cfg
                for cfg in self.configs
            }

            for future in as_completed(futures):
                if self._is_cancelled:
                    self.log_message.emit("Scan cancelled by user.")
                    break

                try:
                    res = future.result()
                    cfg: ProxyConfig = res["config"]
                    status = res.get("status", "failed")

                    with self._lock:
                        self._completed_count += 1
                        if status == "working":
                            self._working_count += 1
                        else:
                            self._failed_count += 1
                        completed = self._completed_count

                    # Emit candidate tested signal for UI update
                    self.candidate_tested.emit(res)

                    speed_txt = f" | {res['download_speed_mbps']} Mbps" if res.get("download_speed_mbps") else ""
                    lat_txt = f"{res['latency_ms']} ms" if res.get("latency_ms") else res.get("error_category", "failed")

                    self.log_message.emit(
                        f"[{completed}/{total_configs}] {cfg.protocol.upper()} {cfg.server}:{cfg.port} -> "
                        f"{status.upper()} ({lat_txt}{speed_txt}) Score: {res.get('score', 0)}"
                    )

                    self.progress.emit(
                        completed,
                        total_configs,
                        f"Tested {completed}/{total_configs} ({self._working_count} working)",
                    )
                except Exception as e:
                    self.log_message.emit(f"Worker exception: {redact_credentials(str(e))}")

        self.finished.emit(self._working_count, self._failed_count)


class XrayDownloadWorker(QThread):
    """Worker thread downloading the official Xray release."""

    progress = Signal(int, int, str)
    finished = Signal(bool, str)

    def run(self):
        try:
            installed_path = download_official_xray(
                progress_callback=lambda cur, tot, msg: self.progress.emit(cur, tot, msg)
            )
            self.finished.emit(True, f"Xray installed successfully at {installed_path}")
        except Exception as exc:
            self.finished.emit(False, redact_credentials(str(exc)))
