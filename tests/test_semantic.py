import numpy as np
from fastapi.testclient import TestClient

from main import app
from semantic import build_index, semantic_search, symbol_embedding_text
from store import AnalysisRecord, save


def _symbol(
    name,
    *,
    file,
    symbol_type="function",
    qualified_name=None,
    lineno=1,
    end_lineno=5,
    arguments=None,
    docstring=None,
    code=None,
):
    qname = qualified_name or name
    return {
        "name": name,
        "qualified_name": qname,
        "type": symbol_type,
        "file": file,
        "lineno": lineno,
        "end_lineno": end_lineno,
        "arguments": arguments or [],
        "docstring": docstring,
        "code": code or f"def {name}():\n    return None",
    }


def test_embedding_text_is_deterministic():
    symbol = _symbol(
        "clone_repository",
        file="services/repository.py",
        arguments=["url", "destination"],
        docstring="Clone a GitHub repository.",
        code="def clone_repository(url, destination):\n    pass",
        lineno=15,
        end_lineno=42,
    )
    text = symbol_embedding_text(symbol)
    assert text == symbol_embedding_text(symbol)
    assert "File: services/repository.py" in text
    assert "Symbol: clone_repository" in text
    assert "Qualified name: clone_repository" in text
    assert "Type: function" in text
    assert "Arguments: url, destination" in text
    assert "Docstring: Clone a GitHub repository." in text
    assert "def clone_repository" in text


def test_deterministic_ranking_with_injected_embeddings():
    symbols = [
        _symbol("alpha", file="b.py", lineno=2),
        _symbol("beta", file="a.py", lineno=1),
        _symbol("gamma", file="c.py", lineno=3),
    ]
    embeddings = np.array(
        [
            [0.2, 0.8, 0.0],
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
        ],
        dtype=np.float32,
    )
    index = build_index(symbols, embeddings=embeddings)
    query_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    first = semantic_search("anything", index, query_embedding=query_embedding)
    second = semantic_search("anything", index, query_embedding=query_embedding)
    assert first == second
    assert [item["name"] for item in first] == ["beta", "gamma", "alpha"]
    assert first[0]["similarity"] >= first[1]["similarity"] >= first[2]["similarity"]


def test_top_k_and_larger_than_corpus():
    symbols = [
        _symbol("a", file="a.py", lineno=1),
        _symbol("b", file="b.py", lineno=1),
        _symbol("c", file="c.py", lineno=1),
    ]
    embeddings = np.eye(3, dtype=np.float32)
    index = build_index(symbols, embeddings=embeddings)
    query_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    top_two = semantic_search(
        "q", index, top_k=2, query_embedding=query_embedding
    )
    assert len(top_two) == 2
    assert [item["rank"] for item in top_two] == [1, 2]
    oversized = semantic_search(
        "q", index, top_k=50, query_embedding=query_embedding
    )
    assert len(oversized) == 3


def test_duplicate_symbol_names_remain_distinct():
    symbols = [
        _symbol(
            "process",
            file="package_a/utils.py",
            qualified_name="process",
            lineno=4,
        ),
        _symbol(
            "process",
            file="package_b/utils.py",
            qualified_name="Worker.process",
            symbol_type="method",
            lineno=10,
        ),
    ]
    embeddings = np.array([[1.0, 0.0], [0.99, 0.1]], dtype=np.float32)
    index = build_index(symbols, embeddings=embeddings)
    results = semantic_search(
        "process handler",
        index,
        query_embedding=np.array([1.0, 0.0], dtype=np.float32),
    )
    assert len(results) == 2
    identities = {
        (item["file"], item["qualified_name"], item["start_line"])
        for item in results
    }
    assert identities == {
        ("package_a/utils.py", "process", 4),
        ("package_b/utils.py", "Worker.process", 10),
    }


def test_file_and_line_metadata():
    symbols = [
        _symbol(
            "helper",
            file="package_a/mod.py",
            lineno=12,
            end_lineno=20,
            arguments=["x"],
        )
    ]
    index = build_index(
        symbols, embeddings=np.array([[1.0, 0.0]], dtype=np.float32)
    )
    result = semantic_search(
        "helper", index, query_embedding=np.array([1.0, 0.0], dtype=np.float32)
    )[0]
    assert result["file"] == "package_a/mod.py"
    assert result["start_line"] == 12
    assert result["end_line"] == 20
    assert result["qualified_name"] == "helper"
    assert result["type"] == "function"


def test_empty_query_returns_none():
    symbols = [_symbol("a", file="a.py")]
    index = build_index(
        symbols, embeddings=np.array([[1.0, 0.0]], dtype=np.float32)
    )
    assert semantic_search("   ", index) is None
    assert semantic_search("", index) is None
    assert semantic_search(None, index) is None


def test_no_searchable_symbols():
    index = build_index([])
    assert semantic_search("where is login", index) == []


def test_index_is_reused_across_queries():
    calls = {"corpus": 0}

    def encode_texts(texts):
        calls["corpus"] += 1
        return np.eye(len(texts), 4, dtype=np.float32)

    symbols = [
        _symbol("a", file="a.py", lineno=1),
        _symbol("b", file="b.py", lineno=1),
    ]
    index = build_index(symbols, encode_texts=encode_texts)
    assert calls["corpus"] == 1
    semantic_search(
        "first", index, query_embedding=np.array([1.0, 0.0, 0.0, 0.0])
    )
    semantic_search(
        "second", index, query_embedding=np.array([0.0, 1.0, 0.0, 0.0])
    )
    assert calls["corpus"] == 1
    assert index["embeddings"].shape[0] == 2


def test_api_unknown_analysis_and_empty_index():
    client = TestClient(app)
    missing = client.post(
        "/analyses/00000000-0000-0000-0000-000000000000/search",
        json={"query": "where is login handled"},
    )
    assert missing.status_code == 404

    save(
        AnalysisRecord(
            analysis_id="22222222-2222-2222-2222-222222222222",
            repo_url="https://github.com/example/repo",
            files=[],
            dependencies=[],
            index=build_index([]),
        )
    )
    empty = client.post(
        "/analyses/22222222-2222-2222-2222-222222222222/search",
        json={"query": "where is login handled"},
    )
    assert empty.status_code == 200
    assert empty.json()["results"] == []

    blank = client.post(
        "/analyses/22222222-2222-2222-2222-222222222222/search",
        json={"query": "   "},
    )
    assert blank.status_code == 422
