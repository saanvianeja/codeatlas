"""Shared limits and ingestion rules for CodeAtlas.

Cloned repositories are untrusted. These constants exist so limits are
not scattered as magic numbers. The analyzer never executes repository code.
"""

import re

# Public GitHub HTTPS repo URLs only (no nested paths like /tree/main).
GITHUB_REPO_URL_RE = re.compile(
    r"^https://(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+?)"
    r"(?:\.git)?/?$"
)

CLONE_TIMEOUT_SECONDS = 60
MAX_PYTHON_FILES = 400
MAX_FILE_BYTES = 512_000
MAX_TOTAL_SOURCE_BYTES = 8_000_000

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "site-packages",
        "__pycache__",
        "node_modules",
    }
)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_SEARCH_TOP_K = 5
MAX_SEARCH_TOP_K = 25
SEARCHABLE_SYMBOL_TYPES = frozenset(
    {
        "function",
        "async_function",
        "class",
        "method",
        "async_method",
    }
)


def is_github_repo_url(repo_url: str) -> bool:
    return bool(GITHUB_REPO_URL_RE.match(repo_url.strip()))
