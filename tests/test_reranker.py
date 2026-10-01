import json
from pathlib import Path

import torch

from config import RERANKER_ENABLED
from reranker import (
    CodeReranker,
    extract_features,
    load_checkpoint,
    rerank_search_results,
    save_checkpoint,
    score_candidates,
    tokenize,
)
from semantic import build_index
import numpy as np

SPLIT = json.loads(
    (Path(__file__).resolve().parents[1] / "outputs" / "retrieval_baseline.json").read_text()
)["phase5_query_split"]


def _symbol(**kwargs):
    base = {
        "name": "login",
        "qualified_name": "login",
        "type": "function",
        "file": "auth.py",
        "lineno": 10,
        "end_lineno": 20,
        "arguments": ["username"],
        "docstring": "Log the user in.",
        "code": "def login(username):\n    return username",
    }
    base.update(kwargs)
    return base


def _name_overlap_model() -> CodeReranker:
    model = CodeReranker()
    with torch.no_grad():
        for layer in model.network:
            if isinstance(layer, torch.nn.Linear):
                layer.weight.zero_()
                layer.bias.zero_()
        for index in range(4):
            model.network[0].weight[index, index] = 1.0
        model.network[2].weight[0, 1] = 10.0
    model.eval()
    return model


def test_feature_extraction_is_deterministic():
    symbol = _symbol()
    first = extract_features("where is user login handled", symbol, 0.42)
    second = extract_features("where is user login handled", symbol, 0.42)
    assert first == second
    assert len(first) == 4
    assert first[0] == 0.42
    assert first[1] > 0  # "login" overlaps the name


def test_tokenize_splits_identifiers():
    assert "logged" in tokenize("load_logged_in_user")
    assert "user" in tokenize("load_logged_in_user")


def test_forward_pass_shape():
    model = CodeReranker()
    model.eval()
    output = model(torch.zeros(5, 4))
    assert tuple(output.shape) == (5, 1)


def test_checkpoint_roundtrip(tmp_path):
    model = CodeReranker()
    path = tmp_path / "best.pt"
    save_checkpoint(model, path, extra={"seed": 42})
    loaded = load_checkpoint(path)
    x = torch.arange(8, dtype=torch.float32).reshape(2, 4)
    model.eval()
    with torch.no_grad():
        assert torch.allclose(model(x), loaded(x))


def test_candidate_ordering_by_scores():
    model = _name_overlap_model()
    weak = {
        **_symbol(name="index", qualified_name="index", file="blog.py"),
        "minilm_cosine": 0.9,
    }
    strong = {
        **_symbol(name="login", qualified_name="login", file="auth.py"),
        "minilm_cosine": 0.1,
    }
    scores = score_candidates(model, "where is user login handled", [weak, strong])
    assert scores[1] > scores[0]


def test_rerank_search_results_rewrites_ranks():
    symbols = [
        _symbol(name="index", qualified_name="index", file="blog.py", lineno=1),
        _symbol(name="login", qualified_name="login", file="auth.py", lineno=2),
    ]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    index = build_index(symbols, embeddings=embeddings)
    results = [
        {
            "rank": 1,
            "name": "index",
            "qualified_name": "index",
            "type": "function",
            "file": "blog.py",
            "start_line": 1,
            "end_line": 20,
            "similarity": 0.99,
            "code": "def index():\n    return 1",
        },
        {
            "rank": 2,
            "name": "login",
            "qualified_name": "login",
            "type": "function",
            "file": "auth.py",
            "start_line": 2,
            "end_line": 20,
            "similarity": 0.1,
            "code": "def login():\n    return 1",
        },
    ]
    model = _name_overlap_model()
    reranked = rerank_search_results(
        "where is user login handled", results, index, model
    )
    assert [item["qualified_name"] for item in reranked] == ["login", "index"]
    assert [item["rank"] for item in reranked] == [1, 2]
    assert reranked[0]["similarity"] == 0.1


def test_split_isolation_and_locked_test_queries():
    train = {q for qs in SPLIT["train"].values() for q in qs}
    val = {q for qs in SPLIT["validation"].values() for q in qs}
    test = {q for qs in SPLIT["test"].values() for q in qs}
    assert len(train) == 18
    assert len(val) == 6
    assert len(test) == 6
    assert train.isdisjoint(val)
    assert train.isdisjoint(test)
    assert val.isdisjoint(test)
    assert test == {
        "where is the query token checked for the expected value",
        "where is repository configuration updated",
        "where is the command line application initialized",
        "where is the database connection closed after a request",
        "where is the database connection created or retrieved",
        "where is user login handled",
    }


def test_training_metrics_do_not_include_test_queries():
    path = Path(__file__).resolve().parents[1] / "outputs" / "reranker" / "training_metrics.json"
    if not path.is_file():
        return
    payload = json.loads(path.read_text())
    assert payload["test_queries_used"] is False
    blob = json.dumps(payload)
    for query in SPLIT["test"]["pallets/flask"]:
        assert query not in blob


def test_production_reranker_disabled_by_default():
    assert RERANKER_ENABLED is False
