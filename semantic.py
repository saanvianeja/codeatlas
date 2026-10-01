"""MiniLM semantic retrieval over AST symbols.

What is embedded
----------------
Each searchable symbol is converted to a deterministic text block:

    File: <repository-relative path>
    Symbol: <unqualified name>
    Qualified name: <qualified_name>
    Type: <function|async_function|class|method|async_method>
    Arguments: <comma-separated args, or (none)>
    Docstring: <docstring or (none)>
    Code:
    <AST source for that symbol>

The corpus is encoded once per analysis with all-MiniLM-L6-v2. Queries
are encoded at search time and ranked by cosine similarity. The stored
embedding matrix is L2-normalized so search is a matrix-vector product.

This module does not re-embed the repository on each query.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from config import (
    DEFAULT_SEARCH_TOP_K,
    EMBEDDING_MODEL_NAME,
    MAX_SEARCH_TOP_K,
    SEARCHABLE_SYMBOL_TYPES,
)

_model = None


def get_model():
    """Lazy-load MiniLM so unit tests can inject embeddings instead."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def symbol_embedding_text(symbol: dict[str, Any]) -> str:
    arguments = symbol.get("arguments") or []
    args_text = ", ".join(arguments) if arguments else "(none)"
    docstring = (symbol.get("docstring") or "").strip() or "(none)"
    code = symbol.get("code") or ""
    return (
        f"File: {symbol.get('file', '')}\n"
        f"Symbol: {symbol.get('name', '')}\n"
        f"Qualified name: {symbol.get('qualified_name', symbol.get('name', ''))}\n"
        f"Type: {symbol.get('type', '')}\n"
        f"Arguments: {args_text}\n"
        f"Docstring: {docstring}\n"
        f"Code:\n{code}"
    )


def _l2_normalize(matrix: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    if matrix.size == 0:
        return matrix.astype(np.float32, copy=False)
    if matrix.ndim == 1:
        norm = float(np.linalg.norm(matrix))
        return (matrix / max(norm, eps)).astype(np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return (matrix / np.maximum(norms, eps)).astype(np.float32)


def _default_encode_texts(texts: list[str]) -> np.ndarray:
    encoded = get_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )
    return np.asarray(encoded, dtype=np.float32)


def build_index(
    symbols: list[dict[str, Any]],
    *,
    embeddings: np.ndarray | None = None,
    encode_texts: Callable[[list[str]], np.ndarray] | None = None,
) -> dict[str, Any]:
    """Encode searchable symbols once. Inject embeddings/encode_texts in tests.

    If ``embeddings`` is provided, rows must align with ``symbols`` (same
    length and order, including any non-searchable entries that will be
    dropped) or with the searchable-and-sorted symbol list.
    """
    paired: list[tuple[dict[str, Any], int]] = [
        (symbol, index)
        for index, symbol in enumerate(symbols)
        if symbol.get("type") in SEARCHABLE_SYMBOL_TYPES
    ]
    paired.sort(
        key=lambda item: (
            item[0].get("file", ""),
            int(item[0].get("lineno") or 0),
            item[0].get("qualified_name", ""),
        )
    )
    ordered = [symbol for symbol, _ in paired]
    texts = [symbol_embedding_text(symbol) for symbol in ordered]
    if not ordered:
        return {
            "model_name": EMBEDDING_MODEL_NAME,
            "symbols": [],
            "texts": [],
            "embeddings": np.zeros((0, 0), dtype=np.float32),
        }

    if embeddings is not None:
        source = np.asarray(embeddings, dtype=np.float32)
        if source.ndim != 2:
            raise ValueError("Embedding matrix must be 2-dimensional.")
        if source.shape[0] == len(symbols):
            matrix = np.stack([source[index] for _, index in paired], axis=0)
        elif source.shape[0] == len(ordered):
            matrix = source
        else:
            raise ValueError("Embedding matrix must have one row per symbol.")
    else:
        encoder = encode_texts or _default_encode_texts
        matrix = np.asarray(encoder(texts), dtype=np.float32)

    if matrix.ndim != 2 or matrix.shape[0] != len(ordered):
        raise ValueError("Embedding matrix must have one row per searchable symbol.")

    return {
        "model_name": EMBEDDING_MODEL_NAME,
        "symbols": ordered,
        "texts": texts,
        "embeddings": _l2_normalize(matrix),
    }


def semantic_search(
    query: str,
    index: dict[str, Any] | None,
    top_k: int = DEFAULT_SEARCH_TOP_K,
    *,
    query_embedding: np.ndarray | None = None,
    encode_query: Callable[[str], np.ndarray] | None = None,
) -> list[dict[str, Any]] | None:
    if query is None or not isinstance(query, str):
        return None
    query = query.strip()
    if not query:
        return None

    top_k = max(1, min(int(top_k), MAX_SEARCH_TOP_K))
    if not index or not index.get("symbols"):
        return []

    symbols = index["symbols"]
    matrix = np.asarray(index["embeddings"], dtype=np.float32)
    if matrix.size == 0:
        return []

    if query_embedding is not None:
        qvec = _l2_normalize(np.asarray(query_embedding, dtype=np.float32))
    elif encode_query is not None:
        qvec = _l2_normalize(np.asarray(encode_query(query), dtype=np.float32))
    else:
        qvec = _l2_normalize(
            np.asarray(
                get_model().encode(
                    [query],
                    convert_to_numpy=True,
                    normalize_embeddings=False,
                )[0],
                dtype=np.float32,
            )
        )

    scores = matrix @ qvec
    ranked = sorted(
        range(len(symbols)),
        key=lambda i: (
            -float(scores[i]),
            symbols[i].get("file", ""),
            symbols[i].get("qualified_name", ""),
            int(symbols[i].get("lineno") or 0),
            i,
        ),
    )
    limit = min(top_k, len(ranked))
    results: list[dict[str, Any]] = []
    for rank, index_i in enumerate(ranked[:limit], start=1):
        symbol = symbols[index_i]
        results.append(
            {
                "rank": rank,
                "name": symbol["name"],
                "qualified_name": symbol["qualified_name"],
                "type": symbol["type"],
                "file": symbol["file"],
                "start_line": symbol["lineno"],
                "end_line": symbol["end_lineno"],
                "similarity": float(scores[index_i]),
                "code": symbol.get("code") or "",
            }
        )
    return results


def get_similarity(query, code):
    """Pairwise cosine on raw query/code text. Used by the untrained reranker."""
    query_embedding = get_model().encode(query, convert_to_tensor=True)
    code_embedding = get_model().encode(code, convert_to_tensor=True)
    from sentence_transformers import util

    return util.cos_sim(query_embedding, code_embedding).item()
