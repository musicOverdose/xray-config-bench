"""Unit tests for GitHub source tree discovery, filtering, and error handling."""

from unittest.mock import MagicMock, patch
import pytest

from app.github_source import (
    fetch_github_repo_files,
    is_github_repo_url,
    parse_github_repo_url,
)


def test_parse_github_repo_url():
    owner, repo, branch, subpath = parse_github_repo_url("https://github.com/v2fly/v2ray-examples")
    assert owner == "v2fly"
    assert repo == "v2ray-examples"
    assert branch is None
    assert subpath is None

    owner2, repo2, branch2, subpath2 = parse_github_repo_url(
        "https://github.com/freefq/free/tree/master/v2"
    )
    assert owner2 == "freefq"
    assert repo2 == "free"
    assert branch2 == "master"
    assert subpath2 == "v2"


def test_is_github_repo_url():
    assert is_github_repo_url("https://github.com/owner/repo") is True
    assert is_github_repo_url("https://github.com/owner/repo/tree/main") is True
    assert is_github_repo_url("https://raw.githubusercontent.com/owner/repo/main/file.txt") is False
    assert is_github_repo_url("https://github.com/owner/repo/raw/main/file.txt") is False


@patch("requests.get")
def test_fetch_github_repo_files_success(mock_get):
    # Mock repo info call (default branch)
    repo_resp = MagicMock()
    repo_resp.status_code = 200
    repo_resp.json.return_value = {"default_branch": "main"}

    # Mock tree call
    tree_resp = MagicMock()
    tree_resp.status_code = 200
    tree_resp.json.return_value = {
        "tree": [
            {"path": "configs/nodes.txt", "type": "blob", "size": 1024},
            {"path": "images/screenshot.png", "type": "blob", "size": 50000},  # should be ignored
            {"path": "large_archive.zip", "type": "blob", "size": 9999999},  # should be ignored
            {"path": "subs.sub", "type": "blob", "size": 2048},
        ]
    }

    # Mock raw file downloads
    raw1_resp = MagicMock()
    raw1_resp.status_code = 200
    raw1_resp.text = "vless://uuid@node1.com:443#Node1"

    raw2_resp = MagicMock()
    raw2_resp.status_code = 200
    raw2_resp.text = "trojan://pass@node2.com:443#Node2"

    mock_get.side_effect = [repo_resp, tree_resp, raw1_resp, raw2_resp]

    files = fetch_github_repo_files("https://github.com/owner/repo")
    assert len(files) == 2
    assert files[0][0] == "configs/nodes.txt"
    assert "vless://" in files[0][1]
    assert files[1][0] == "subs.sub"
    assert "trojan://" in files[1][1]


@patch("requests.get")
def test_fetch_github_repo_rate_limit(mock_get):
    rate_resp = MagicMock()
    rate_resp.status_code = 403
    rate_resp.text = "API rate limit exceeded for 1.2.3.4"
    mock_get.return_value = rate_resp

    with pytest.raises(ValueError, match="rate limit exceeded"):
        fetch_github_repo_files("https://github.com/owner/repo")


@patch("requests.get")
def test_fetch_github_repo_not_found(mock_get):
    not_found_resp = MagicMock()
    not_found_resp.status_code = 404
    mock_get.return_value = not_found_resp

    with pytest.raises(ValueError, match="not found"):
        fetch_github_repo_files("https://github.com/owner/missing-repo")
