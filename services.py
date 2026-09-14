import subprocess
import tempfile
import uuid

from fastapi import HTTPException, status

import analyzer
import semantic
import store
from store import AnalysisRecord


def create_analysis(repo_url: str) -> AnalysisRecord:
    repo_url = repo_url.strip()
    if not repo_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A repository URL is required.",
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            subprocess.run(
                ["git", "clone", repo_url, temp_dir],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="git is not available on the server.",
            )
        except subprocess.CalledProcessError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not clone the repository. Check that the URL is valid and the repo is accessible.",
            )

        analysis = analyzer.analyze_repo(temp_dir)
        chunks = analyzer.extract_repo_chunks(temp_dir)
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
