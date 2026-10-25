"""SQLite local storage for sources, configurations, benchmark results, and settings."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from .config_parser.models import ProxyConfig
from .security import redact_credentials

from .paths import get_app_config_dir, get_db_path

DEFAULT_CONFIG_DIR = get_app_config_dir()


def get_default_db_path() -> Path:
    return get_db_path()


class Database:
    """Thread-safe SQLite database manager."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    url_or_path TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_refresh TEXT,
                    discovered_count INTEGER DEFAULT 0,
                    valid_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS configs (
                    id TEXT PRIMARY KEY,
                    unique_hash TEXT UNIQUE NOT NULL,
                    protocol TEXT NOT NULL,
                    name TEXT,
                    server TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    raw_link TEXT NOT NULL,
                    source_id TEXT,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_category TEXT,
                    error_detail TEXT,
                    latency_ms REAL,
                    latency_variance REAL,
                    download_speed_mbps REAL,
                    success_rate REAL,
                    score REAL,
                    tested_at TEXT NOT NULL,
                    FOREIGN KEY(config_hash) REFERENCES configs(unique_hash) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_configs_hash ON configs(unique_hash);
                CREATE INDEX IF NOT EXISTS idx_bench_hash ON benchmark_results(config_hash);
                CREATE INDEX IF NOT EXISTS idx_bench_score ON benchmark_results(score);
                """
            )

    # --- Sources API ---

    def add_source(
        self,
        source_id: str,
        name: str,
        source_type: str,
        url_or_path: str,
        enabled: bool = True,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sources (id, name, source_type, url_or_path, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    source_type = excluded.source_type,
                    url_or_path = excluded.url_or_path,
                    enabled = excluded.enabled
                """,
                (source_id, name, source_type, url_or_path, 1 if enabled else 0, now),
            )

    def update_source_stats(
        self,
        source_id: str,
        discovered: int,
        valid: int,
        error_message: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sources
                SET last_refresh = ?, discovered_count = ?, valid_count = ?, error_message = ?
                WHERE id = ?
                """,
                (now, discovered, valid, error_message, source_id),
            )

    def set_source_enabled(self, source_id: str, enabled: bool) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sources SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, source_id),
            )

    def delete_source(self, source_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))

    def get_sources(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM sources ORDER BY created_at ASC")
            return [dict(r) for r in cur.fetchall()]

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    # --- Configs API ---

    def upsert_config(self, config: ProxyConfig, source_id: Optional[str] = None) -> bool:
        """
        Insert or update a parsed configuration by unique hash.
        Returns True if newly inserted, False if duplicate already existed.
        """
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(config.to_dict())
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT id FROM configs WHERE unique_hash = ?", (config.unique_hash,)
            )
            existing = cur.fetchone()
            if existing:
                # Update name if changed
                conn.execute(
                    "UPDATE configs SET name = ?, data_json = ? WHERE unique_hash = ?",
                    (config.name, data_json, config.unique_hash),
                )
                return False

            config_id = f"cfg_{config.unique_hash[:12]}"
            conn.execute(
                """
                INSERT INTO configs (id, unique_hash, protocol, name, server, port, raw_link, source_id, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    config_id,
                    config.unique_hash,
                    config.protocol,
                    config.name,
                    config.server,
                    config.port,
                    config.raw_link,
                    source_id or config.source_id,
                    data_json,
                    now,
                ),
            )
            return True

    def get_all_configs(self) -> List[ProxyConfig]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT data_json FROM configs ORDER BY created_at DESC")
            configs = []
            for row in cur.fetchall():
                try:
                    data = json.loads(row["data_json"])
                    configs.append(ProxyConfig.from_dict(data))
                except Exception:
                    continue
            return configs

    def get_config_by_hash(self, unique_hash: str) -> Optional[ProxyConfig]:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT data_json FROM configs WHERE unique_hash = ?", (unique_hash,)
            )
            row = cur.fetchone()
            if row:
                try:
                    return ProxyConfig.from_dict(json.loads(row["data_json"]))
                except Exception:
                    return None
            return None

    def get_configs_count(self) -> int:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) as count FROM configs")
            return cur.fetchone()["count"]

    # --- Benchmark Results API ---

    def record_benchmark_result(
        self,
        config_hash: str,
        status: str,
        error_category: Optional[str] = None,
        error_detail: Optional[str] = None,
        latency_ms: Optional[float] = None,
        latency_variance: Optional[float] = None,
        download_speed_mbps: Optional[float] = None,
        success_rate: Optional[float] = None,
        score: Optional[float] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            # Delete previous benchmark for this config to keep latest result active
            conn.execute("DELETE FROM benchmark_results WHERE config_hash = ?", (config_hash,))
            conn.execute(
                """
                INSERT INTO benchmark_results (
                    config_hash, status, error_category, error_detail,
                    latency_ms, latency_variance, download_speed_mbps,
                    success_rate, score, tested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    config_hash,
                    status,
                    error_category,
                    redact_credentials(error_detail or ""),
                    latency_ms,
                    latency_variance,
                    download_speed_mbps,
                    success_rate,
                    score,
                    now,
                ),
            )

    def get_latest_results(
        self,
        protocol: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get configs joined with their latest benchmark result.
        Returns rows sorted by score descending.
        """
        query = """
            SELECT
                c.unique_hash,
                c.protocol,
                c.name,
                c.server,
                c.port,
                c.raw_link,
                s.name as source_name,
                r.status,
                r.error_category,
                r.error_detail,
                r.latency_ms,
                r.latency_variance,
                r.download_speed_mbps,
                r.success_rate,
                r.score,
                r.tested_at
            FROM configs c
            LEFT JOIN sources s ON c.source_id = s.id
            LEFT JOIN benchmark_results r ON c.unique_hash = r.config_hash
            WHERE 1=1
        """
        params: List[Any] = []
        if protocol and protocol.lower() != "all":
            query += " AND LOWER(c.protocol) = ?"
            params.append(protocol.lower())
        if status and status.lower() != "all":
            if status.lower() == "untested":
                query += " AND r.status IS NULL"
            else:
                query += " AND LOWER(r.status) = ?"
                params.append(status.lower())

        query += " ORDER BY CASE WHEN r.score IS NULL THEN 0 ELSE r.score END DESC, r.latency_ms ASC"
        if limit:
            query += f" LIMIT {int(limit)}"

        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Return counts for dashboard cards."""
        with self._get_connection() as conn:
            total_configs = conn.execute("SELECT COUNT(*) as c FROM configs").fetchone()["c"]
            tested = conn.execute(
                "SELECT COUNT(DISTINCT config_hash) as c FROM benchmark_results"
            ).fetchone()["c"]
            working = conn.execute(
                "SELECT COUNT(DISTINCT config_hash) as c FROM benchmark_results WHERE status = 'working'"
            ).fetchone()["c"]
            failed = conn.execute(
                "SELECT COUNT(DISTINCT config_hash) as c FROM benchmark_results WHERE status = 'failed'"
            ).fetchone()["c"]

            best_cur = conn.execute(
                """
                SELECT c.name, c.protocol, c.server, c.port, r.latency_ms, r.download_speed_mbps, r.score
                FROM configs c
                JOIN benchmark_results r ON c.unique_hash = r.config_hash
                WHERE r.status = 'working'
                ORDER BY r.score DESC, r.latency_ms ASC
                LIMIT 1
                """
            )
            best_row = best_cur.fetchone()
            best_config = dict(best_row) if best_row else None

            return {
                "discovered": total_configs,
                "tested": tested,
                "working": working,
                "failed": failed,
                "untested": max(0, total_configs - tested),
                "best_config": best_config,
            }

    # --- Settings API ---

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def get_all_settings(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT key, value FROM settings")
            return {r["key"]: r["value"] for r in cur.fetchall()}
