"""Subscription content parser handling Base64 and plain-text feeds."""

import base64
from typing import List, Optional, Tuple, Union
from .config_parser import extract_links_from_text, parse_share_link
from .config_parser.models import ProxyConfig
from .config_parser.vmess import safe_b64decode


def decode_subscription_feed(
    content: Union[str, bytes]
) -> List[Tuple[str, Optional[ProxyConfig], Optional[str]]]:
    """
    Parse a subscription response body (plain text or Base64 encoded).
    Returns list of (raw_link, parsed_config, error_message).
    """
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                text = ""
    else:
        text = str(content)

    text = text.strip()
    if not text:
        return []

    # Check if the whole text is Base64 encoded
    # Subscription base64 feeds usually do not start with a protocol scheme
    is_plain_links = any(
        text.startswith(scheme)
        for scheme in ("vless://", "vmess://", "trojan://", "ss://", "#", "//")
    )

    if not is_plain_links:
        try:
            decoded = safe_b64decode(text)
            # If decoded content contains recognized protocol markers, use it
            if any(k in decoded.lower() for k in ("vless://", "vmess://", "trojan://", "ss://")):
                return extract_links_from_text(decoded)
        except Exception:
            pass

    # Process as plain text
    return extract_links_from_text(text)
