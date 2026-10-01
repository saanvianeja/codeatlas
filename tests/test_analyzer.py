from pathlib import Path

import pytest

from analyzer import (
    AnalysisLimitError,
    EmptyRepositoryError,
    analyze_repo,
    discover_python_files,
)
from config import is_github_repo_url

FIXTURES = Path(__file__).parent / "fixtures"
GRAPH_REPO = FIXTURES / "graph_repo"
SRC_LAYOUT = FIXTURES / "src_layout"


def file_map(analysis):
    return {item["file"]: item for item in analysis["files"]}


def edge_set(analysis):
    return {(item["source"], item["target"]) for item in analysis["dependencies"]}


def test_github_url_validation():
    assert is_github_repo_url("https://github.com/pallets/flask")
    assert is_github_repo_url("https://github.com/pallets/flask.git")
    assert is_github_repo_url("https://www.github.com/pallets/flask/")
    assert not is_github_repo_url("https://github.com/pallets/flask/tree/main")
    assert not is_github_repo_url("git@github.com:pallets/flask.git")
    assert not is_github_repo_url("/tmp/local-repo")
    assert not is_github_repo_url("https://gitlab.com/pallets/flask")


def test_module_async_class_and_method_extraction():
    analysis = analyze_repo(GRAPH_REPO)
    symbols_file = file_map(analysis)["symbols.py"]

    assert "module_fn" in symbols_file["functions"]
    assert "module_async" in symbols_file["async_functions"]
    assert "Greeter" in symbols_file["classes"]
    assert "Outer" in symbols_file["classes"]
    assert "greet" in symbols_file["methods"]
    assert "agreet" in symbols_file["methods"]
    assert "inner_method" in symbols_file["methods"]
    assert "nested_should_not_appear" not in symbols_file["functions"]
    assert "nested_should_not_appear" not in symbols_file["methods"]

    by_qname = {item["qualified_name"]: item for item in symbols_file["symbols"]}
    assert by_qname["module_fn"]["type"] == "function"
    assert by_qname["module_async"]["type"] == "async_function"
    assert by_qname["Greeter"]["type"] == "class"
    assert by_qname["Greeter.greet"]["type"] == "method"
    assert by_qname["Greeter.agreet"]["type"] == "async_method"
    assert by_qname["Outer.Inner"]["type"] == "class"
    assert by_qname["Outer.Inner.inner_method"]["type"] == "method"

    assert by_qname["module_fn"]["arguments"] == ["x", "y"]
    assert by_qname["module_fn"]["docstring"] == "A module-level function."
    assert by_qname["module_fn"]["lineno"] == 4
    assert by_qname["module_fn"]["end_lineno"] >= 10
    assert "def module_fn" in by_qname["module_fn"]["code"]
    assert by_qname["module_fn"]["file"] == "symbols.py"


def test_duplicate_file_stems_are_distinct_nodes():
    analysis = analyze_repo(GRAPH_REPO)
    files = {item["file"] for item in analysis["files"]}
    assert "package_a/utils.py" in files
    assert "package_b/utils.py" in files
    assert "utils" not in files


def test_absolute_internal_imports():
    analysis = analyze_repo(GRAPH_REPO)
    edges = edge_set(analysis)
    assert ("app.py", "package_a/utils.py") in edges
    assert ("app.py", "package_b/utils.py") in edges
    assert ("app.py", "package_a/mod.py") in edges


def test_relative_imports():
    analysis = analyze_repo(GRAPH_REPO)
    edges = edge_set(analysis)
    assert ("package_a/nested/rel.py", "package_a/utils.py") in edges
    assert ("package_a/nested/rel.py", "package_a/nested/other.py") in edges


def test_src_layout_absolute_import():
    analysis = analyze_repo(SRC_LAYOUT)
    edges = edge_set(analysis)
    assert ("scripts/run.py", "src/mylib/core.py") in edges
    assert ("src/mylib/core.py", "src/mylib/helpers.py") in edges


def test_unresolved_and_external_imports_are_not_edges():
    analysis = analyze_repo(GRAPH_REPO)
    files = file_map(analysis)
    edges = edge_set(analysis)

    stdlib_kinds = {item["kind"] for item in files["stdlib_user.py"]["imports"]}
    assert stdlib_kinds == {"stdlib"}

    third_kinds = {item["kind"] for item in files["third_party_user.py"]["imports"]}
    assert third_kinds == {"third_party"}

    unresolved_kinds = {item["kind"] for item in files["unresolved_rel.py"]["imports"]}
    assert unresolved_kinds == {"unresolved"}

    assert all(target != "requests" for _, target in edges)
    assert all(not target.endswith("does_not_exist") for _, target in edges)
    assert ("stdlib_user.py", "json") not in edges
    assert ("unresolved_rel.py", "does_not_exist") not in edges


def test_isolated_files_remain_graph_nodes():
    analysis = analyze_repo(GRAPH_REPO)
    files = {item["file"] for item in analysis["files"]}
    assert "package_b/isolated.py" in files
    edges = edge_set(analysis)
    assert all("package_b/isolated.py" not in pair for pair in edges)


def test_syntax_error_does_not_crash_repo_analysis():
    analysis = analyze_repo(GRAPH_REPO)
    broken = file_map(analysis)["broken.py"]
    assert broken["error"] == "SyntaxError"
    assert "app.py" in file_map(analysis)


def test_encoding_error_is_per_file(tmp_path):
    (tmp_path / "ok.py").write_text("def fine():\n    return 1\n", encoding="utf-8")
    (tmp_path / "bad.py").write_bytes(b"\xff\xfe not utf-8")
    analysis = analyze_repo(tmp_path)
    files = file_map(analysis)
    assert files["bad.py"]["error"] == "EncodingError"
    assert "fine" in files["ok.py"]["functions"]


def test_ignored_directories_are_skipped():
    discovered = {
        path.relative_to(GRAPH_REPO).as_posix()
        for path in discover_python_files(GRAPH_REPO)
    }
    assert "package_a/utils.py" in discovered
    assert ".venv/lib/hidden.py" not in discovered
    assert "venv/lib/hidden.py" not in discovered
    assert "site-packages/foo.py" not in discovered
    assert "__pycache__/cached.py" not in discovered
    assert "node_modules/pkg/index.py" not in discovered
    assert ".git/hooks.py" not in discovered

    analysis = analyze_repo(GRAPH_REPO)
    files = {item["file"] for item in analysis["files"]}
    assert ".venv/lib/hidden.py" not in files
    assert "node_modules/pkg/index.py" not in files


def test_dependencies_are_deduped_and_deterministic():
    first = analyze_repo(GRAPH_REPO)
    second = analyze_repo(GRAPH_REPO)
    assert first["dependencies"] == second["dependencies"]
    assert first["dependencies"] == sorted(
        first["dependencies"],
        key=lambda item: (item["source"], item["target"]),
    )
    assert len(first["dependencies"]) == len(edge_set(first))


def test_no_absolute_paths_in_analysis():
    analysis = analyze_repo(GRAPH_REPO)
    for item in analysis["files"]:
        assert not Path(item["file"]).is_absolute()
        for imported in item["imports"]:
            resolved = imported["resolved_file"]
            if resolved:
                assert not Path(resolved).is_absolute()
    for edge in analysis["dependencies"]:
        assert not Path(edge["source"]).is_absolute()
        assert not Path(edge["target"]).is_absolute()


def test_sample_repo_path_identity():
    analysis = analyze_repo(Path(__file__).resolve().parents[1] / "sample_repo")
    edges = edge_set(analysis)
    assert ("main.py", "utils.py") in edges
    assert ("utils.py", "data.py") in edges


def test_empty_repository_raises(tmp_path):
    (tmp_path / "README.md").write_text("no python here\n")
    with pytest.raises(EmptyRepositoryError):
        analyze_repo(tmp_path)


def test_python_file_limit(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 1\n")
    with pytest.raises(AnalysisLimitError):
        analyze_repo(tmp_path, max_python_files=1)
