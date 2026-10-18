"""Unit tests for subscription feeds and unified link extraction."""

import base64
from app.config_parser import extract_links_from_text, parse_share_link
from app.subscription_parser import decode_subscription_feed


def test_decode_plaintext_feed():
    content = """
    # Community Free Subscription
    vless://uuid-1@node1.com:443?security=tls#Node1
    // Some comment line
    trojan://pass-2@node2.com:443#Node2

    # Malformed line that should be reported as error
    vless://malformed_no_at_symbol
    """
    results = decode_subscription_feed(content)
    # Total extracted items should include the 2 valid links and 1 malformed
    valid_configs = [cfg for raw, cfg, err in results if cfg]
    assert len(valid_configs) == 2
    assert valid_configs[0].server == "node1.com"
    assert valid_configs[1].server == "node2.com"


def test_decode_base64_feed():
    plain_links = (
        "vless://uuid-a@server-a.com:443#ServerA\n"
        "trojan://pass-b@server-b.com:443#ServerB\n"
    )
    b64_feed = base64.b64encode(plain_links.encode("utf-8")).decode("utf-8")

    results = decode_subscription_feed(b64_feed)
    valid_configs = [cfg for raw, cfg, err in results if cfg]
    assert len(valid_configs) == 2
    assert valid_configs[0].server == "server-a.com"
    assert valid_configs[1].server == "server-b.com"


def test_duplicate_detection(temp_db):
    link1 = "vless://same-uuid@same-host.com:443?security=tls#OriginalName"
    link2 = "vless://same-uuid@same-host.com:443?security=tls#RenamedInOtherFeed"

    cfg1 = parse_share_link(link1)
    cfg2 = parse_share_link(link2)

    # Identical server, port, credentials, transport must have identical hash
    assert cfg1.unique_hash == cfg2.unique_hash

    # Database insertion of second duplicate should return False (not new)
    is_new_1 = temp_db.upsert_config(cfg1)
    is_new_2 = temp_db.upsert_config(cfg2)

    assert is_new_1 is True
    assert is_new_2 is False
    assert temp_db.get_configs_count() == 1
