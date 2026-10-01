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


def search_analysis(analysis_id: str, query: str) -> list[dict]:
    import semantic

    record = get_analysis(analysis_id)
    if record.index is None:
        return []

    results = semantic.semantic_search(query, record.index)
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A search query is required.",
        )
    return results


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
