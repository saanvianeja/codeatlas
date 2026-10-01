from fastapi import HTTPException
from fastapi.testclient import TestClient

from impact import UnknownFileError, compute_potential_impact
from main import app
from store import AnalysisRecord, save


def files_from(*paths: str):
    return [
        {
            "file": path,
            "imports": [],
            "functions": [],
            "async_functions": [],
            "classes": [],
            "methods": [],
            "symbols": [],
            "error": None,
        }
        for path in paths
    ]


def edges(*pairs: tuple[str, str]):
    return [{"source": source, "target": target} for source, target in pairs]


def test_simple_chain():
    result = compute_potential_impact(
        files_from("A.py", "B.py", "C.py"),
        edges(("A.py", "B.py"), ("B.py", "C.py")),
        "C.py",
    )
    assert result["direct_dependents"] == ["B.py"]
    assert result["transitive_dependents"] == ["A.py"]
    assert result["distances"] == {"B.py": 1, "A.py": 2}
    assert result["total_impacted"] == 2
    assert "C.py" not in result["all_impacted_files"]


def test_branching_direct_dependents():
    result = compute_potential_impact(
        files_from("A.py", "B.py", "C.py"),
        edges(("A.py", "C.py"), ("B.py", "C.py")),
        "C.py",
    )
    assert result["direct_dependents"] == ["A.py", "B.py"]
    assert result["transitive_dependents"] == []
    assert result["distances"]["A.py"] == 1
    assert result["distances"]["B.py"] == 1


def test_multiple_levels():
    result = compute_potential_impact(
        files_from("A.py", "B.py", "C.py", "D.py"),
        edges(("A.py", "B.py"), ("B.py", "C.py"), ("D.py", "B.py")),
        "C.py",
    )
    assert result["direct_dependents"] == ["B.py"]
    assert result["transitive_dependents"] == ["A.py", "D.py"]
    assert result["distances"] == {"B.py": 1, "A.py": 2, "D.py": 2}


def test_cycle_terminates_and_excludes_selected():
    result = compute_potential_impact(
        files_from("A.py", "B.py", "C.py"),
        edges(("A.py", "B.py"), ("B.py", "C.py"), ("C.py", "A.py")),
        "A.py",
    )
    assert "A.py" not in result["all_impacted_files"]
    assert result["direct_dependents"] == ["C.py"]
    assert result["transitive_dependents"] == ["B.py"]
    assert result["distances"] == {"C.py": 1, "B.py": 2}
    assert result["total_impacted"] == 2


def test_shortest_distance_with_multiple_paths():
    result = compute_potential_impact(
        files_from("A.py", "B.py", "C.py"),
        edges(("A.py", "C.py"), ("A.py", "B.py"), ("B.py", "C.py")),
        "C.py",
    )
    assert result["distances"]["A.py"] == 1
    assert result["distances"]["B.py"] == 1
    assert result["direct_dependents"] == ["A.py", "B.py"]
    assert result["transitive_dependents"] == []


def test_isolated_file_has_zero_impact():
    result = compute_potential_impact(
        files_from("isolated.py", "other.py"),
        [],
        "isolated.py",
    )
    assert result["direct_dependents"] == []
    assert result["transitive_dependents"] == []
    assert result["all_impacted_files"] == []
    assert result["total_impacted"] == 0
    assert result["distances"] == {}


def test_nonexistent_file_raises():
    try:
        compute_potential_impact(files_from("A.py"), [], "missing.py")
        raise AssertionError("expected UnknownFileError")
    except UnknownFileError as exc:
        assert exc.selected_file == "missing.py"


def test_ordering_is_deterministic():
    first = compute_potential_impact(
        files_from("A.py", "B.py", "C.py"),
        edges(("A.py", "C.py"), ("B.py", "C.py")),
        "C.py",
    )
    second = compute_potential_impact(
        files_from("A.py", "B.py", "C.py"),
        edges(("B.py", "C.py"), ("A.py", "C.py")),
        "C.py",
    )
    assert first == second
    assert first["direct_dependents"] == ["A.py", "B.py"]


def test_api_missing_analysis_id():
    client = TestClient(app)
    response = client.get(
        "/analyses/00000000-0000-0000-0000-000000000000/impact",
        params={"file": "A.py"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found."


def test_api_missing_file_and_isolated_success():
    save(
        AnalysisRecord(
            analysis_id="11111111-1111-1111-1111-111111111111",
            repo_url="https://github.com/example/repo",
            files=files_from("isolated.py", "A.py", "B.py"),
            dependencies=edges(("A.py", "B.py")),
            index=None,
        )
    )
    client = TestClient(app)

    missing = client.get(
        "/analyses/11111111-1111-1111-1111-111111111111/impact",
        params={"file": "nope.py"},
    )
    assert missing.status_code == 404

    isolated = client.get(
        "/analyses/11111111-1111-1111-1111-111111111111/impact",
        params={"file": "isolated.py"},
    )
    assert isolated.status_code == 200
    body = isolated.json()
    assert body["total_impacted"] == 0
    assert body["direct_dependents"] == []

    chain = client.get(
        "/analyses/11111111-1111-1111-1111-111111111111/impact",
        params={"file": "B.py"},
    )
    assert chain.status_code == 200
    assert chain.json()["direct_dependents"] == ["A.py"]


def test_http_exception_for_missing_analysis():
    import services

    try:
        services.get_impact("00000000-0000-0000-0000-000000000000", "A.py")
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Analysis not found."
