"""Python static analysis and internal-import resolution.

Limitations (by design; we do not pretend to resolve these):
- Dynamic imports (importlib, __import__, exec) are ignored.
- sys.path changes and runtime-generated modules are invisible.
- Unusual packaging (namespace packages without __init__.py, editable
  installs, multiple roots besides repo root / src/) may not resolve.
- Import aliases and ``from x import *`` cannot bind names at runtime.
- Definitions nested inside functions are not treated as top-level symbols.
- We never execute repository code.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

from config import (
    MAX_FILE_BYTES,
    MAX_PYTHON_FILES,
    MAX_TOTAL_SOURCE_BYTES,
    SKIP_DIR_NAMES,
)

STDLIB_TOP_LEVEL = set(sys.stdlib_module_names)


class AnalysisLimitError(Exception):
    pass


class EmptyRepositoryError(Exception):
    pass


def posix_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_skip_path(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return any(part in SKIP_DIR_NAMES for part in parts)


def discover_python_files(root: Path) -> list[Path]:
    files = [
        path
        for path in root.rglob("*.py")
        if path.is_file() and not should_skip_path(path, root)
    ]
    files.sort(key=lambda path: posix_relative(path, root))
    return files


def _empty_file_result(rel: str, error: str) -> dict[str, Any]:
    return {
        "file": rel,
        "imports": [],
        "functions": [],
        "async_functions": [],
        "classes": [],
        "methods": [],
        "symbols": [],
        "error": error,
    }


def _function_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    names: list[str] = []
    args = node.args
    for arg in list(args.posonlyargs) + list(args.args):
        names.append(arg.arg)
    if args.vararg:
        names.append(f"*{args.vararg.arg}")
    for arg in args.kwonlyargs:
        names.append(arg.arg)
    if args.kwarg:
        names.append(f"**{args.kwarg.arg}")
    return names


def _source_for_node(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment is not None:
        return segment
    lines = source.splitlines()
    start = getattr(node, "lineno", 1) - 1
    end = getattr(node, "end_lineno", start + 1)
    return "\n".join(lines[start:end])


def _symbol(
    *,
    name: str,
    qualified_name: str,
    symbol_type: str,
    rel: str,
    node: ast.AST,
    source: str,
    arguments: list[str],
) -> dict[str, Any]:
    docstring = ast.get_docstring(node) if isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    ) else None
    return {
        "name": name,
        "qualified_name": qualified_name,
        "type": symbol_type,
        "file": rel,
        "lineno": getattr(node, "lineno", 1),
        "end_lineno": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
        "arguments": arguments,
        "docstring": docstring,
        "code": _source_for_node(source, node),
    }


def _iter_body(nodes: Iterable[ast.stmt]) -> Iterator[ast.stmt]:
    """Yield statements, flattening module-level control flow but not functions."""
    for node in nodes:
        yield node
        if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            yield from _iter_body(node.body)
            yield from _iter_body(node.orelse)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            yield from _iter_body(node.body)
        elif isinstance(node, ast.Try):
            yield from _iter_body(node.body)
            yield from _iter_body(node.orelse)
            yield from _iter_body(node.finalbody)
            for handler in node.handlers:
                yield from _iter_body(handler.body)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                yield from _iter_body(case.body)


def _extract_symbols(tree: ast.Module, source: str, rel: str) -> dict[str, Any]:
    functions: list[str] = []
    async_functions: list[str] = []
    classes: list[str] = []
    methods: list[str] = []
    symbols: list[dict[str, Any]] = []

    def visit_class(class_node: ast.ClassDef, parent_qname: str | None) -> None:
        qname = (
            f"{parent_qname}.{class_node.name}"
            if parent_qname
            else class_node.name
        )
        classes.append(class_node.name)
        symbols.append(
            _symbol(
                name=class_node.name,
                qualified_name=qname,
                symbol_type="class",
                rel=rel,
                node=class_node,
                source=source,
                arguments=[],
            )
        )
        for child in _iter_body(class_node.body):
            if isinstance(child, ast.FunctionDef):
                methods.append(child.name)
                symbols.append(
                    _symbol(
                        name=child.name,
                        qualified_name=f"{qname}.{child.name}",
                        symbol_type="method",
                        rel=rel,
                        node=child,
                        source=source,
                        arguments=_function_arguments(child),
                    )
                )
            elif isinstance(child, ast.AsyncFunctionDef):
                methods.append(child.name)
                symbols.append(
                    _symbol(
                        name=child.name,
                        qualified_name=f"{qname}.{child.name}",
                        symbol_type="async_method",
                        rel=rel,
                        node=child,
                        source=source,
                        arguments=_function_arguments(child),
                    )
                )
            elif isinstance(child, ast.ClassDef):
                visit_class(child, qname)

    for node in _iter_body(tree.body):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
            symbols.append(
                _symbol(
                    name=node.name,
                    qualified_name=node.name,
                    symbol_type="function",
                    rel=rel,
                    node=node,
                    source=source,
                    arguments=_function_arguments(node),
                )
            )
        elif isinstance(node, ast.AsyncFunctionDef):
            async_functions.append(node.name)
            symbols.append(
                _symbol(
                    name=node.name,
                    qualified_name=node.name,
                    symbol_type="async_function",
                    rel=rel,
                    node=node,
                    source=source,
                    arguments=_function_arguments(node),
                )
            )
        elif isinstance(node, ast.ClassDef):
            visit_class(node, None)

    return {
        "functions": functions,
        "async_functions": async_functions,
        "classes": classes,
        "methods": methods,
        "symbols": symbols,
    }


def _module_names_for_relative_path(rel: str) -> list[str]:
    parts = rel.split("/")
    last = parts[-1]
    if last.endswith(".py"):
        parts[-1] = last[:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    names: list[str] = []
    if parts:
        names.append(".".join(parts))
    if len(parts) > 1 and parts[0] == "src":
        names.append(".".join(parts[1:]))
    return names


def _package_parts(rel: str) -> list[str]:
    parts = rel.split("/")
    last = parts[-1]
    if last.endswith(".py"):
        parts[-1] = last[:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    else:
        parts = parts[:-1]
    return [part for part in parts if part]


def build_module_index(relative_files: list[str]) -> dict[str, str]:
    index: dict[str, str] = {}
    for rel in relative_files:
        for name in _module_names_for_relative_path(rel):
            existing = index.get(name)
            if existing is None:
                index[name] = rel
            elif rel.endswith("/__init__.py") and not existing.endswith(
                "/__init__.py"
            ):
                index[name] = rel
    return index


def _resolve_module(index: dict[str, str], dotted: str | None) -> str | None:
    if not dotted:
        return None
    return index.get(dotted)


def _longest_prefix_resolve(index: dict[str, str], dotted: str) -> str | None:
    parts = dotted.split(".")
    for end in range(len(parts), 0, -1):
        resolved = _resolve_module(index, ".".join(parts[:end]))
        if resolved:
            return resolved
    return None


def _relative_anchor(rel: str, level: int) -> list[str] | None:
    pkg_parts = _package_parts(rel)
    if level > len(pkg_parts):
        return None
    drop = level - 1
    if drop == 0:
        return pkg_parts
    return pkg_parts[: len(pkg_parts) - drop]


def _raw_from_import(module: str | None, level: int, names: list[str]) -> str:
    dots = "." * level
    imported = ", ".join(names)
    if module:
        return f"from {dots}{module} import {imported}"
    return f"from {dots} import {imported}"


def _internal_top_levels(index: dict[str, str]) -> set[str]:
    return {name.split(".", 1)[0] for name in index}


def classify_import(
    *,
    resolved: str | None,
    top_level: str | None,
    relative: bool,
    index: dict[str, str] | None = None,
) -> str:
    if resolved:
        return "internal"
    if relative:
        return "unresolved"
    if top_level and top_level in STDLIB_TOP_LEVEL:
        return "stdlib"
    if top_level and index and top_level in _internal_top_levels(index):
        return "unresolved"
    if top_level:
        return "third_party"
    return "unresolved"


def resolve_import_statement(
    *,
    index: dict[str, str],
    current_rel: str,
    node: ast.Import | ast.ImportFrom,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if isinstance(node, ast.Import):
        for alias in node.names:
            dotted = alias.name
            resolved = _resolve_module(index, dotted)
            top = dotted.split(".", 1)[0]
            kind = classify_import(
                resolved=resolved,
                top_level=top,
                relative=False,
                index=index,
            )
            results.append(
                {
                    "raw": f"import {dotted}",
                    "kind": kind,
                    "resolved_file": resolved if kind == "internal" else None,
                }
            )
        return results

    names = [alias.name for alias in node.names]
    level = node.level
    module = node.module
    raw = _raw_from_import(module, level, names)
    relative = level > 0

    bases: list[str] = []
    if relative:
        anchor = _relative_anchor(current_rel, level)
        if anchor is None or (not anchor and not module):
            results.append(
                {
                    "raw": raw,
                    "kind": "unresolved",
                    "resolved_file": None,
                }
            )
            return results
        if module:
            bases.append(".".join(anchor + module.split(".")))
        else:
            bases.append(".".join(anchor) if anchor else "")
    else:
        if module:
            bases.append(module)

    resolved_files: list[str] = []
    top_level: str | None = None

    for base in bases:
        if not base:
            for name in names:
                candidate = name
                resolved = _resolve_module(index, candidate)
                if resolved:
                    resolved_files.append(resolved)
            continue
        top_level = base.split(".", 1)[0]
        for name in names:
            as_submodule = f"{base}.{name}"
            resolved = _resolve_module(index, as_submodule)
            if resolved:
                resolved_files.append(resolved)
                continue
            resolved = _resolve_module(index, base)
            if resolved:
                resolved_files.append(resolved)
                continue
            prefix = _longest_prefix_resolve(index, as_submodule)
            if prefix:
                resolved_files.append(prefix)

        if not names:
            resolved = _resolve_module(index, base) or _longest_prefix_resolve(
                index, base
            )
            if resolved:
                resolved_files.append(resolved)

    unique_resolved = list(dict.fromkeys(resolved_files))
    if unique_resolved:
        for resolved in unique_resolved:
            results.append(
                {
                    "raw": raw,
                    "kind": "internal",
                    "resolved_file": resolved,
                }
            )
        return results

    kind = classify_import(
        resolved=None,
        top_level=top_level,
        relative=relative,
        index=index,
    )
    results.append(
        {
            "raw": raw,
            "kind": kind,
            "resolved_file": None,
        }
    )
    return results


def _collect_import_nodes(tree: ast.AST) -> list[ast.Import | ast.ImportFrom]:
    found: list[ast.Import | ast.ImportFrom] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            found.append(node)
    return found


def analyze_file(
    path: Path,
    root: Path,
    *,
    module_index: dict[str, str] | None = None,
) -> dict[str, Any]:
    rel = posix_relative(path, root)
    try:
        size = path.stat().st_size
    except OSError as exc:
        return _empty_file_result(rel, f"Could not read file: {exc}")

    if size > MAX_FILE_BYTES:
        return _empty_file_result(rel, "File too large")

    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _empty_file_result(rel, "EncodingError")
    except OSError as exc:
        return _empty_file_result(rel, f"Could not read file: {exc}")

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _empty_file_result(rel, "SyntaxError")

    extracted = _extract_symbols(tree, source, rel)
    index = module_index or {}
    imports: list[dict[str, Any]] = []
    for import_node in _collect_import_nodes(tree):
        imports.extend(
            resolve_import_statement(
                index=index,
                current_rel=rel,
                node=import_node,
            )
        )

    return {
        "file": rel,
        "imports": imports,
        **extracted,
        "error": None,
    }


def _build_dependencies(files: list[dict[str, Any]]) -> list[dict[str, str]]:
    edges: set[tuple[str, str]] = set()
    for file_info in files:
        source = file_info["file"]
        for imported in file_info["imports"]:
            if imported["kind"] != "internal":
                continue
            target = imported["resolved_file"]
            if not target or target == source:
                continue
            edges.add((source, target))
    return [
        {"source": source, "target": target}
        for source, target in sorted(edges)
    ]


def analyze_repo(
    folder: str | Path,
    *,
    max_python_files: int = MAX_PYTHON_FILES,
    max_total_bytes: int = MAX_TOTAL_SOURCE_BYTES,
) -> dict[str, Any]:
    root = Path(folder)
    python_files = discover_python_files(root)
    if not python_files:
        raise EmptyRepositoryError("Repository contains no Python files.")
    if len(python_files) > max_python_files:
        raise AnalysisLimitError(
            f"Repository has {len(python_files)} Python files; "
            f"limit is {max_python_files}."
        )

    total_bytes = 0
    sized_files: list[Path] = []
    for path in python_files:
        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue
        sized_files.append(path)
        if total_bytes > max_total_bytes:
            raise AnalysisLimitError(
                f"Repository Python sources exceed {max_total_bytes} bytes."
            )

    relative_files = [posix_relative(path, root) for path in python_files]
    module_index = build_module_index(relative_files)

    results = [
        analyze_file(path, root, module_index=module_index)
        for path in python_files
    ]
    dependencies = _build_dependencies(results)
    return {
        "files": results,
        "dependencies": dependencies,
    }


def chunks_from_analysis(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for file_info in analysis["files"]:
        for symbol in file_info.get("symbols", []):
            chunks.append(
                {
                    "name": symbol["name"],
                    "qualified_name": symbol["qualified_name"],
                    "type": symbol["type"],
                    "file": symbol["file"],
                    "code": symbol["code"],
                    "lineno": symbol["lineno"],
                    "end_lineno": symbol["end_lineno"],
                    "docstring": symbol["docstring"],
                    "arguments": symbol["arguments"],
                }
            )
    return chunks


def extract_repo_chunks(folder: str | Path) -> list[dict[str, Any]]:
    analysis = analyze_repo(folder)
    return chunks_from_analysis(analysis)


if __name__ == "__main__":
    print(analyze_repo("sample_repo"))
