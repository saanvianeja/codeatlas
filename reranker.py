"""Small PyTorch MLP reranker over MiniLM retrieval candidates.

Input features (length 4, all in [0, 1] aside from cosine which is ~[-1, 1]):
1. minilm_cosine — cosine similarity between the query and the same
   symbol embedding text used by retrieval
2. name_jaccard — token Jaccard of the query vs the symbol name
3. docstring_jaccard — token Jaccard of the query vs the docstring
4. identifier_jaccard — token Jaccard of the query vs name, qualified
   name, and file path tokens

Architecture: Linear(4, 8) → ReLU → Linear(8, 1) → relevance logit.
Target: binary relevance. Loss: BCEWithLogitsLoss.
This module does not load MiniLM; callers pass minilm_cosine.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from config import (
    RERANKER_CHECKPOINT,
    RERANKER_HIDDEN_SIZE,
    RERANKER_INPUT_SIZE,
)

FEATURE_NAMES = (
    "minilm_cosine",
    "name_jaccard",
    "docstring_jaccard",
    "identifier_jaccard",
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_CAMEL_RE = re.compile(r"([a-z])([A-Z])")
_QUERY_STOPWORDS = frozenset(
    "where is the a an are of and to for in on with by from how what does".split()
)

_loaded_model: nn.Module | None = None
_loaded_path: str | None = None


class CodeReranker(nn.Module):
    def __init__(
        self,
        input_size: int = RERANKER_INPUT_SIZE,
        hidden_size: int = RERANKER_HIDDEN_SIZE,
    ):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


def tokenize(text: str) -> set[str]:
    split = _CAMEL_RE.sub(r"\1 \2", text or "")
    split = split.replace("_", " ").replace("/", " ").replace(".", " ")
    return set(_TOKEN_RE.findall(split.lower()))


def token_jaccard(left: str, right: str, *, drop_stopwords: bool = False) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if drop_stopwords:
        left_tokens -= _QUERY_STOPWORDS
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def extract_features(
    query: str,
    symbol: dict[str, Any],
    minilm_cosine: float,
) -> list[float]:
    identifiers = " ".join(
        [
            symbol.get("name") or "",
            symbol.get("qualified_name") or "",
            (symbol.get("file") or "").replace(".py", ""),
        ]
    )
    return [
        float(minilm_cosine),
        token_jaccard(query, symbol.get("name") or "", drop_stopwords=True),
        token_jaccard(query, symbol.get("docstring") or "", drop_stopwords=True),
        token_jaccard(query, identifiers, drop_stopwords=True),
    ]


def save_checkpoint(model: CodeReranker, path: str | Path, extra: dict | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state_dict": model.state_dict(),
        "feature_names": list(FEATURE_NAMES),
        "input_size": RERANKER_INPUT_SIZE,
        "hidden_size": RERANKER_HIDDEN_SIZE,
        "extra": extra or {},
    }
    torch.save(payload, path)


def load_checkpoint(path: str | Path | None = None) -> CodeReranker:
    checkpoint_path = Path(path or RERANKER_CHECKPOINT)
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = CodeReranker(
        input_size=payload.get("input_size", RERANKER_INPUT_SIZE),
        hidden_size=payload.get("hidden_size", RERANKER_HIDDEN_SIZE),
    )
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model


def score_candidates(
    model: CodeReranker,
    query: str,
    candidates: list[dict[str, Any]],
) -> list[float]:
    rows = [
        extract_features(query, candidate, candidate["minilm_cosine"])
        for candidate in candidates
    ]
    with torch.no_grad():
        logits = model(torch.tensor(rows, dtype=torch.float32)).squeeze(-1)
    if logits.ndim == 0:
        return [float(logits.item())]
    return [float(value) for value in logits.tolist()]


def rerank_search_results(
    query: str,
    results: list[dict[str, Any]],
    index: dict[str, Any] | None,
    model: CodeReranker,
) -> list[dict[str, Any]]:
    """Reorder MiniLM results using the MLP. MiniLM similarity is unchanged."""
    if not results or not index:
        return results
    by_key = {
        (symbol["file"], symbol["qualified_name"], symbol["lineno"]): symbol
        for symbol in index.get("symbols", [])
    }
    candidates: list[dict[str, Any]] = []
    for result in results:
        symbol = by_key.get(
            (result["file"], result["qualified_name"], result["start_line"])
        )
        if symbol is None:
            return results
        candidates.append({**symbol, "minilm_cosine": result["similarity"]})
    scores = score_candidates(model, query, candidates)
    order = sorted(
        range(len(results)),
        key=lambda i: (
            -scores[i],
            -float(results[i]["similarity"]),
            results[i]["file"],
            results[i]["qualified_name"],
        ),
    )
    reranked = []
    for rank, i in enumerate(order, start=1):
        item = dict(results[i])
        item["rank"] = rank
        item["rerank_score"] = scores[i]
        reranked.append(item)
    return reranked


def get_production_model() -> CodeReranker | None:
    global _loaded_model, _loaded_path
    path = str(Path(RERANKER_CHECKPOINT))
    if _loaded_model is not None and _loaded_path == path:
        return _loaded_model
    if not Path(path).is_file():
        return None
    _loaded_model = load_checkpoint(path)
    _loaded_path = path
    return _loaded_model
