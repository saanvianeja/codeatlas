import os
import subprocess
import tempfile
import uuid

from fastapi import HTTPException, status

import analyzer
import store
from analyzer import AnalysisLimitError, EmptyRepositoryError
from config import (
    CLONE_TIMEOUT_SECONDS,
    MAX_PYTHON_FILES,
    MAX_TOTAL_SOURCE_BYTES,
    RAG_TOP_K,
    RERANKER_ENABLED,
    is_github_repo_url,
)
from store import AnalysisRecord


def create_analysis(repo_url: str) -> AnalysisRecord:
    repo_url = repo_url.strip()
    if not repo_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A repository URL is required.",
        )
    if not is_github_repo_url(repo_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a public GitHub repository URL such as https://github.com/owner/repo.",
        )

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            subprocess.run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "clone",
                    "--depth",
                    "1",
                    "--single-branch",
                    repo_url,
                    temp_dir,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=CLONE_TIMEOUT_SECONDS,
                env=env,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="git is not available on the server.",
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cloning the repository timed out.",
            )
        except subprocess.CalledProcessError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not clone the repository. Check that the URL is valid and the repo is public.",
            )

        try:
            analysis = analyzer.analyze_repo(
                temp_dir,
                max_python_files=MAX_PYTHON_FILES,
                max_total_bytes=MAX_TOTAL_SOURCE_BYTES,
            )
        except EmptyRepositoryError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except AnalysisLimitError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        chunks = analyzer.chunks_from_analysis(analysis)
        import semantic

        index = semantic.build_index(chunks)

    record = AnalysisRecord(
        analysis_id=str(uuid.uuid4()),
        repo_url=repo_url,
        files=analysis["files"],
        dependencies=analysis["dependencies"],
        index=index,
    )
    store.save(record)
    return record


def get_analysis(analysis_id: str) -> AnalysisRecord:
    record = store.get(analysis_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )
    return record


def search_analysis(
    analysis_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    import semantic

    record = get_analysis(analysis_id)
    results = semantic.semantic_search(query, record.index, top_k=top_k)
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A search query is required.",
        )
    if RERANKER_ENABLED and results:
        from reranker import get_production_model, rerank_search_results

        model = get_production_model()
        if model is not None:
            results = rerank_search_results(query, results, record.index, model)
    return results


def ask_analysis(analysis_id: str, question: str, complete=None) -> dict:
    from llm import LLMError, LLMNotConfigured, complete_chat
    from rag import build_context

    record = get_analysis(analysis_id)
    hits = search_analysis(analysis_id, question, top_k=RAG_TOP_K)
    packed = build_context(question, hits, record.dependencies)
    if not packed["sources"]:
        return {
            "answer": "I don't have enough repository context to answer that question.",
            "sources": [],
        }
    llm = complete or complete_chat
    try:
        answer = llm(packed["system_prompt"], packed["user_prompt"])
    except LLMNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return {
        "answer": answer,
        "sources": packed["sources"],
    }


def get_impact(analysis_id: str, selected_file: str) -> dict:
    from impact import UnknownFileError, compute_potential_impact

    record = get_analysis(analysis_id)
    try:
        return compute_potential_impact(
            record.files,
            record.dependencies,
            selected_file,
        )
    except UnknownFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
