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


RERANKER_ENABLED = False
RERANKER_CHECKPOINT = "outputs/reranker/best.pt"
RERANKER_SEED = 42
RERANKER_LEARNING_RATE = 0.01
RERANKER_MAX_EPOCHS = 300
RERANKER_PATIENCE = 25
RERANKER_INPUT_SIZE = 4
RERANKER_HIDDEN_SIZE = 8

RERANKER_SOURCE_PINS = {
    "pallets/flask": {
        "url": "https://github.com/pallets/flask.git",
        "tag": "3.1.1",
        "commit": "7fff56f5172c48b6f3aedf17ee14ef5c2533dfd1",
    },
    "pallets/click": {
        "url": "https://github.com/pallets/click.git",
        "tag": "8.1.8",
        "commit": "934813e4d421071a1b3db3973c02fe2721359a6e",
    },
    "fastapi/fastapi": {
        "url": "https://github.com/fastapi/fastapi.git",
        "tag": "0.136.3",
        "commit": "82064857539e6286522c347b4b11331b48dd2378",
    },
}

RAG_TOP_K = 5
RAG_MAX_CODE_CHARS = 1200
RAG_MAX_CONTEXT_CHARS = 8000
RAG_MAX_DEPS_PER_SYMBOL = 3

LLM_API_KEY_ENV = "CODEATLAS_LLM_API_KEY"
LLM_BASE_URL_ENV = "CODEATLAS_LLM_BASE_URL"
LLM_MODEL_ENV = "CODEATLAS_LLM_MODEL"
LLM_DEFAULT_BASE_URL = "https://api.openai.com/v1"
LLM_DEFAULT_MODEL = "gpt-4o-mini"
LLM_TIMEOUT_SECONDS = 30
