"""Bounded RAG context from MiniLM hits plus a few graph edges."""

from __future__ import annotations

from typing import Any

from config import (
    RAG_MAX_CODE_CHARS,
    RAG_MAX_CONTEXT_CHARS,
    RAG_MAX_DEPS_PER_SYMBOL,
)

SYSTEM_PROMPT = """You answer questions about a Python repository using only the supplied context.

Rules:
- Use only the context. Do not invent files, functions, or behavior.
- If the context is insufficient, say so clearly.
- Cite sources with [path/file.py:L12-L40] using the provided line ranges.
- Keep the answer concise and technical.
"""


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 18)].rstrip() + "\n# ... truncated ..."


def _edges_for_file(
    file_path: str,
    dependencies: list[dict[str, str]],
) -> tuple[list[str], list[str]]:
    depends_on: list[str] = []
    imported_by: list[str] = []
    seen_on: set[str] = set()
    seen_by: set[str] = set()
    for edge in dependencies:
        if (
            edge["source"] == file_path
            and edge["target"] not in seen_on
            and len(depends_on) < RAG_MAX_DEPS_PER_SYMBOL
        ):
            seen_on.add(edge["target"])
            depends_on.append(edge["target"])
        if (
            edge["target"] == file_path
            and edge["source"] not in seen_by
            and len(imported_by) < RAG_MAX_DEPS_PER_SYMBOL
        ):
            seen_by.add(edge["source"])
            imported_by.append(edge["source"])
    return depends_on, imported_by


def source_from_hit(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "file": hit["file"],
        "qualified_name": hit["qualified_name"],
        "start_line": hit["start_line"],
        "end_line": hit["end_line"],
    }


def render_symbol_block(
    hit: dict[str, Any],
    depends_on: list[str],
    imported_by: list[str],
) -> str:
    code = _clip(hit.get("code") or "", RAG_MAX_CODE_CHARS)
    lines = [
        f"{hit['file']} :: {hit['qualified_name']} ({hit['type']}) "
        f"L{hit['start_line']}-L{hit['end_line']}",
    ]
    if depends_on:
        lines.append("Depends on: " + ", ".join(depends_on))
    if imported_by:
        lines.append("Imported by: " + ", ".join(imported_by))
    lines.append("Code:")
    lines.append(code)
    return "\n".join(lines)


def build_context(
    question: str,
    hits: list[dict[str, Any]],
    dependencies: list[dict[str, str]],
) -> dict[str, Any]:
    blocks: list[str] = []
    sources: list[dict[str, Any]] = []
    used = 0
    for hit in hits:
        depends_on, imported_by = _edges_for_file(hit["file"], dependencies)
        block = render_symbol_block(hit, depends_on, imported_by)
        extra = len(block) + (2 if blocks else 0)
        if blocks and used + extra > RAG_MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        sources.append(source_from_hit(hit))
        used += extra

    context = "\n\n".join(blocks)
    user_prompt = (
        f"Question: {question.strip()}\n\n"
        f"Repository context:\n{context if context else '(no matching symbols)'}"
    )
    return {
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "context": context,
        "sources": sources,
        "char_count": len(context),
    }
