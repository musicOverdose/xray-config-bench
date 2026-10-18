"""Unified parser entry point and link extraction registry."""

import re
from typing import Callable, Dict, List, Optional, Tuple

from .models import ProxyConfig
from .vless import parse_vless
from .vmess import parse_vmess
from .trojan import parse_trojan
from .shadowsocks import parse_shadowsocks

# Registry mapping URL scheme to parser function
_PARSERS: Dict[str, Callable[[str], ProxyConfig]] = {
    "vless": parse_vless,
    "vmess": parse_vmess,
    "trojan": parse_trojan,
    "ss": parse_shadowsocks,
}


def register_parser(scheme: str, parser_fn: Callable[[str], ProxyConfig]) -> None:
    """Register or extend support for additional protocols."""
    _PARSERS[scheme.lower().rstrip("://")] = parser_fn


def supported_protocols() -> List[str]:
    """Return list of supported protocol schemes."""
    return sorted(list(_PARSERS.keys()))


def parse_share_link(link: str) -> ProxyConfig:
    """
    Parse a single share link (vless://, vmess://, trojan://, ss://).
    Raises ValueError on unsupported protocol or malformed link.
    """
    link = link.strip()
    if not link:
        raise ValueError("Empty configuration link")

    scheme = link.split("://", 1)[0].lower() if "://" in link else ""
    if not scheme or scheme not in _PARSERS:
        supported = ", ".join(f"{s}://" for s in supported_protocols())
        raise ValueError(f"Unsupported protocol scheme '{scheme}'. Supported: {supported}")

    return _PARSERS[scheme](link)


# Regex pattern to match proxy links embedded in arbitrary text
LINK_REGEX = re.compile(
    r"\b(?:vless|vmess|trojan|ss)://[^\s<>\"'`]+",
    re.IGNORECASE
)


def extract_links_from_text(text: str) -> List[Tuple[str, Optional[ProxyConfig], Optional[str]]]:
    """
    Extract and parse all proxy configuration links from raw text.
    Returns list of tuples: (raw_link, parsed_config_or_none, error_message_or_none)
    """
    results: List[Tuple[str, Optional[ProxyConfig], Optional[str]]] = []
    if not text:
        return results

    # First find all explicit match patterns
    found_links = LINK_REGEX.findall(text)

    # Also check line-by-line in case links have trailing punctuation or whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidate_links = list(dict.fromkeys(found_links + [l for l in lines if any(l.startswith(f"{s}://") for s in _PARSERS)]))

    for raw_link in candidate_links:
        try:
            config = parse_share_link(raw_link)
            results.append((raw_link, config, None))
        except Exception as exc:
            results.append((raw_link, None, str(exc)))

    return results
