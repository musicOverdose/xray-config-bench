"""GitHub repository and raw file source collector using the GitHub API."""

import re
import urllib.parse
from typing import Dict, List, Optional, Tuple
import requests

from .security import redact_credentials

GITHUB_API_BASE = "https://api.github.com"
MAX_FILE_SIZE_BYTES = 512 * 1024  # 512 KB
MAX_FILES_PER_REPO = 60  # Avoid scanning massive repositories

# Extensions that might contain proxy share links or subscription text
ELIGIBLE_EXTENSIONS = {
    ".txt", ".sub", ".yaml", ".yml", ".json", ".conf", ".list", ".md", ""
}

# Binary and irrelevant extensions to skip
IGNORED_EXTENSIONS = {
    ".exe", ".zip", ".tar", ".gz", ".7z", ".rar", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".svg", ".pdf", ".deb", ".rpm", ".iso", ".pyc", ".so",
    ".dll", ".bin", ".mp3", ".mp4", ".woff", ".woff2", ".ttf"
}


def is_github_repo_url(url: str) -> bool:
    """Check if URL points to a GitHub repository page rather than a raw file."""
    u = url.strip().lower()
    if not (u.startswith("http://") or u.startswith("https://")):
        return False
    return "github.com/" in u and "raw.githubusercontent.com" not in u and not u.endswith(".txt")


def parse_github_repo_url(url: str) -> Tuple[str, str, Optional[str], Optional[str]]:
    """
    Parse a GitHub repository URL into (owner, repo, branch_or_tree, subpath).
    Examples:
      https://github.com/owner/repo -> ('owner', 'repo', None, None)
      https://github.com/owner/repo/tree/dev/configs -> ('owner', 'repo', 'dev', 'configs')
    """
    parsed = urllib.parse.urlparse(url.strip())
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repository URL: {url}")

    owner = parts[0]
    repo = parts[1].replace(".git", "")
    branch = None
    subpath = None

    if len(parts) >= 4 and parts[2] == "tree":
        branch = parts[3]
        if len(parts) > 4:
            subpath = "/".join(parts[4:])

    return owner, repo, branch, subpath


def fetch_github_repo_files(
    repo_url: str,
    github_token: Optional[str] = None,
    timeout: int = 15,
) -> List[Tuple[str, str]]:
    """
    Traverse a GitHub repository's tree using the GitHub API, find eligible text files,
    and download their contents. Returns list of (file_path, content_text).
    """
    owner, repo, branch, subpath = parse_github_repo_url(repo_url)

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "XrayConfigBench/1.0",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token.strip()}"

    # 1. Get default branch if not specified
    if not branch:
        repo_info_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        try:
            resp = requests.get(repo_info_url, headers=headers, timeout=timeout)
            if resp.status_code == 404:
                raise ValueError(f"GitHub repository '{owner}/{repo}' not found or is private")
            elif resp.status_code == 403 and "rate limit" in resp.text.lower():
                raise ValueError("GitHub API rate limit exceeded. Add an API token in Settings.")
            elif resp.status_code != 200:
                raise ValueError(f"GitHub API error ({resp.status_code}): {redact_credentials(resp.text[:200])}")
            repo_data = resp.json()
            branch = repo_data.get("default_branch", "main")
        except requests.RequestException as e:
            raise ValueError(f"Network error accessing GitHub API: {redact_credentials(str(e))}")

    # 2. Get repository tree recursively
    tree_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    try:
        tree_resp = requests.get(tree_url, headers=headers, timeout=timeout)
        if tree_resp.status_code == 404:
            raise ValueError(f"Branch or tree '{branch}' not found in '{owner}/{repo}'")
        elif tree_resp.status_code == 403 and "rate limit" in tree_resp.text.lower():
            raise ValueError("GitHub API rate limit exceeded. Add an API token in Settings.")
        elif tree_resp.status_code != 200:
            raise ValueError(f"Failed to fetch tree from GitHub ({tree_resp.status_code})")
        tree_data = tree_resp.json()
    except requests.RequestException as e:
        raise ValueError(f"Network error fetching tree from GitHub: {redact_credentials(str(e))}")

    tree_items = tree_data.get("tree", [])

    # 3. Filter eligible files
    eligible_items = []
    for item in tree_items:
        if item.get("type") != "blob":
            continue

        item_path = item.get("path", "")
        # If user specified a subpath, only include items under it
        if subpath and not item_path.startswith(subpath):
            continue

        size = item.get("size", 0)
        if size > MAX_FILE_SIZE_BYTES or size <= 0:
            continue

        # Check extension
        dot_idx = item_path.rfind(".")
        ext = item_path[dot_idx:].lower() if dot_idx != -1 else ""

        if ext in IGNORED_EXTENSIONS:
            continue
        if ext in ELIGIBLE_EXTENSIONS or "." not in item_path:
            eligible_items.append(item)

        if len(eligible_items) >= MAX_FILES_PER_REPO:
            break

    # 4. Download content of eligible files
    downloaded_files: List[Tuple[str, str]] = []
    for item in eligible_items:
        file_path = item.get("path", "")
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
        try:
            raw_resp = requests.get(raw_url, headers=headers, timeout=timeout)
            if raw_resp.status_code == 200:
                downloaded_files.append((file_path, raw_resp.text))
        except Exception:
            # Continue scanning other files if one fails
            continue

    return downloaded_files
