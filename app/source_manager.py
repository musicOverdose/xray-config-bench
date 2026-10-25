"""Source collector and polling manager for subscriptions, GitHub, and local files."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests

from .config_parser.models import ProxyConfig
from .database import Database
from .github_source import fetch_github_repo_files, is_github_repo_url
from .security import redact_credentials
from .subscription_parser import decode_subscription_feed


class SourceManager:
    """Manages fetching, parsing, and storing proxy sources."""

    def __init__(self, db: Database):
        self.db = db

    def fetch_source(
        self,
        source: Dict[str, any],
        github_token: Optional[str] = None,
        timeout: int = 20,
    ) -> Tuple[int, int, Optional[str], List[ProxyConfig]]:
        """
        Fetch configurations from a single source definition.
        Returns: (discovered_count, valid_count, error_message, list_of_valid_configs)
        """
        source_id = source["id"]
        source_type = source.get("source_type", "subscription")
        url_or_path = source["url_or_path"].strip()

        discovered = 0
        valid_configs: List[ProxyConfig] = []
        error_msg: Optional[str] = None

        try:
            is_local = (source_type == "local_file") or (
                not url_or_path.startswith(("http://", "https://")) and os.path.exists(url_or_path)
            )
            if is_local:
                file_path = Path(url_or_path)
                if not file_path.is_file():
                    raise FileNotFoundError(f"Local file does not exist: {url_or_path}")
                content = file_path.read_text(encoding="utf-8", errors="replace")
                items = decode_subscription_feed(content)
                discovered = len(items)
                for raw, cfg, err in items:
                    if cfg:
                        cfg.source_id = source_id
                        valid_configs.append(cfg)

            elif is_github_repo_url(url_or_path) or source_type == "github_repo":
                files = fetch_github_repo_files(
                    url_or_path, github_token=github_token, timeout=timeout
                )
                for file_path, file_content in files:
                    items = decode_subscription_feed(file_content)
                    discovered += len(items)
                    for raw, cfg, err in items:
                        if cfg:
                            cfg.source_id = source_id
                            valid_configs.append(cfg)

            else:
                # Subscription URL / raw file / HTTP feed
                headers = {
                    "User-Agent": "XrayConfigBench/1.0 (v2ray/xray subscription client)",
                    "Accept": "text/plain, application/json, */*",
                }
                resp = requests.get(url_or_path, headers=headers, timeout=timeout)
                if resp.status_code != 200:
                    raise requests.RequestException(
                        f"HTTP request returned status {resp.status_code}"
                    )

                items = decode_subscription_feed(resp.content)
                discovered = len(items)
                for raw, cfg, err in items:
                    if cfg:
                        cfg.source_id = source_id
                        valid_configs.append(cfg)

        except Exception as exc:
            error_msg = redact_credentials(str(exc))

        # Upsert valid configurations into database
        saved_count = 0
        for cfg in valid_configs:
            is_new = self.db.upsert_config(cfg, source_id=source_id)
            if is_new:
                saved_count += 1

        self.db.update_source_stats(
            source_id=source_id,
            discovered=discovered,
            valid=len(valid_configs),
            error_message=error_msg,
        )

        return discovered, len(valid_configs), error_msg, valid_configs

    def refresh_all_enabled(
        self,
        github_token: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[int, int, List[str]]:
        """
        Refresh all enabled sources.
        Returns: (total_discovered, total_valid, list_of_errors)
        """
        sources = [s for s in self.db.get_sources() if s["enabled"]]
        total_discovered = 0
        total_valid = 0
        errors: List[str] = []

        for idx, src in enumerate(sources):
            if progress_callback:
                progress_callback(idx + 1, len(sources), f"Fetching {src['name']}...")
            disc, val, err, _ = self.fetch_source(src, github_token=github_token)
            total_discovered += disc
            total_valid += val
            if err:
                errors.append(f"{src['name']}: {err}")

        return total_discovered, total_valid, errors


RECOMMENDED_SOURCES = [
    {
        "name": "Barry-Far All Protocols",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt",
    },
    {
        "name": "Barry-Far VLESS Reality & TLS",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vless.txt",
    },
    {
        "name": "Barry-Far Trojan",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/trojan.txt",
    },
    {
        "name": "Barry-Far VMess",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vmess.txt",
    },
    {
        "name": "FreeFQ Community Multi-Protocol",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/freefq/free/master/v2",
    },
    {
        "name": "Pawdroid Free Servers",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    },
    {
        "name": "Yebekhe Collector Mix",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix",
    },
    {
        "name": "Mahdi0024 ProxyCollector",
        "source_type": "subscription",
        "url_or_path": "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/master/sub/proxies.txt",
    },
    {
        "name": "FreeFQ GitHub Repository",
        "source_type": "github_repo",
        "url_or_path": "https://github.com/freefq/free",
    },
]


def populate_recommended_sources(db: Database) -> int:
    """Add recommended community sources to database if not already present. Returns count of added sources."""
    import uuid

    existing_urls = {s["url_or_path"].strip().lower() for s in db.get_sources()}
    added = 0
    for item in RECOMMENDED_SOURCES:
        url = item["url_or_path"].strip()
        if url.lower() not in existing_urls:
            db.add_source(
                source_id=str(uuid.uuid4()),
                name=item["name"],
                source_type=item["source_type"],
                url_or_path=url,
                enabled=True,
            )
            existing_urls.add(url.lower())
            added += 1
    return added
