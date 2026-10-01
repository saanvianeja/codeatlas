from fastapi.testclient import TestClient

from config import RAG_MAX_CODE_CHARS, RAG_MAX_CONTEXT_CHARS
from llm import LLMNotConfigured, complete_chat
from main import app
from rag import build_context
from semantic import build_index
from services import ask_analysis
from store import AnalysisRecord, save


def _hit(**kwargs):
    base = {
        "rank": 1,
        "name": "clone_repository",
        "qualified_name": "clone_repository",
        "type": "function",
        "file": "services.py",
        "start_line": 10,
        "end_line": 25,
        "similarity": 0.8,
        "code": "def clone_repository(url, destination):\n    return destination\n",
    }
    base.update(kwargs)
    return base


def test_context_contains_retrieved_symbols_and_deps():
    hits = [
        _hit(),
        _hit(
            name="analyze_repo",
            qualified_name="analyze_repo",
            file="analyzer.py",
            start_line=40,
            end_line=60,
            code="def analyze_repo(folder):\n    return {}\n",
        ),
    ]
    packed = build_context(
        "How does cloning work?",
        hits,
        [{"source": "services.py", "target": "analyzer.py"}],
    )
    assert "clone_repository" in packed["context"]
    assert "services.py" in packed["context"]
    assert "L10-L25" in packed["context"]
    assert "Depends on: analyzer.py" in packed["context"]
    assert packed["sources"][0]["file"] == "services.py"
    assert packed["sources"][0]["start_line"] == 10
    assert packed["sources"][0]["end_line"] == 25
    assert packed["sources"][0]["qualified_name"] == "clone_repository"


def test_context_is_bounded():
    huge = "x" * (RAG_MAX_CODE_CHARS * 4)
    packed = build_context(
        "q",
        [_hit(code=huge), _hit(file="other.py", qualified_name="other", code=huge)],
        [],
    )
    assert packed["char_count"] <= RAG_MAX_CONTEXT_CHARS
    assert "# ... truncated ..." in packed["context"]


def test_mocked_grounded_answer_and_sources(monkeypatch):
    hit = _hit(
        name="helper",
        qualified_name="helper",
        file="utils.py",
        start_line=1,
        end_line=3,
        code="def helper():\n    return 1\n",
    )
    monkeypatch.setattr(
        "services.search_analysis",
        lambda analysis_id, query, top_k=5: [hit],
    )
    save(
        AnalysisRecord(
            analysis_id="33333333-3333-3333-3333-333333333333",
            repo_url="https://github.com/example/repo",
            files=[],
            dependencies=[],
            index=None,
        )
    )

    def fake_llm(system_prompt: str, user_prompt: str) -> str:
        assert "only the supplied" in system_prompt
        assert "helper" in user_prompt
        return "helper returns 1 [utils.py:L1-L3]"

    payload = ask_analysis(
        "33333333-3333-3333-3333-333333333333",
        "What does helper do?",
        complete=fake_llm,
    )
    assert payload["answer"].startswith("helper returns 1")
    assert payload["sources"][0]["file"] == "utils.py"
    assert payload["sources"][0]["start_line"] == 1


def test_api_unknown_analysis_and_empty_question():
    client = TestClient(app)
    missing = client.post(
        "/analyses/00000000-0000-0000-0000-000000000000/ask",
        json={"question": "How does cloning work?"},
    )
    assert missing.status_code == 404

    save(
        AnalysisRecord(
            analysis_id="44444444-4444-4444-4444-444444444444",
            repo_url="https://github.com/example/repo",
            files=[],
            dependencies=[],
            index=build_index([]),
        )
    )
    blank = client.post(
        "/analyses/44444444-4444-4444-4444-444444444444/ask",
        json={"question": "   "},
    )
    assert blank.status_code == 422


def test_no_api_key_is_a_clean_configuration_error(monkeypatch):
    monkeypatch.delenv("CODEATLAS_LLM_API_KEY", raising=False)
    try:
        complete_chat("sys", "user")
        raise AssertionError("expected LLMNotConfigured")
    except LLMNotConfigured as exc:
        assert "CODEATLAS_LLM_API_KEY" in str(exc)

    hit = _hit(name="run", qualified_name="run", file="app.py", start_line=1, end_line=2)
    monkeypatch.setattr(
        "services.search_analysis",
        lambda analysis_id, query, top_k=5: [hit],
    )
    save(
        AnalysisRecord(
            analysis_id="55555555-5555-5555-5555-555555555555",
            repo_url="https://github.com/example/repo",
            files=[],
            dependencies=[],
            index=None,
        )
    )
    client = TestClient(app)
    response = client.post(
        "/analyses/55555555-5555-5555-5555-555555555555/ask",
        json={"question": "What does run do?"},
    )
    assert response.status_code == 503
    assert "CODEATLAS_LLM_API_KEY" in response.json()["detail"]
