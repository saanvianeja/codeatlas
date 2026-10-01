from dataclasses import dataclass
from typing import Any


@dataclass
class AnalysisRecord:
    analysis_id: str
    repo_url: str
    files: list[dict[str, Any]]
    dependencies: list[dict[str, str]]
    index: dict[str, Any] | None


_analyses: dict[str, AnalysisRecord] = {}


def save(record: AnalysisRecord) -> None:
    _analyses[record.analysis_id] = record


def get(analysis_id: str) -> AnalysisRecord | None:
    return _analyses.get(analysis_id)
