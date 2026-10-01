"""Potential downstream impact from reverse dependency traversal.

An edge source → target means source depends on target. Impact of a file is
the set of files that import it, directly or transitively. This is static
import structure only — not a proof that a change will break those files.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class UnknownFileError(Exception):
    def __init__(self, selected_file: str):
        self.selected_file = selected_file
        super().__init__(f"File not found in this analysis: {selected_file}")


def _known_files(
    files: list[dict[str, Any]],
    dependencies: list[dict[str, str]],
) -> set[str]:
    names = {item["file"] for item in files}
    for edge in dependencies:
        names.add(edge["source"])
        names.add(edge["target"])
    return names


def _reverse_adjacency(
    dependencies: list[dict[str, str]],
) -> dict[str, list[str]]:
    dependents: dict[str, set[str]] = defaultdict(set)
    for edge in dependencies:
        dependents[edge["target"]].add(edge["source"])
    return {
        target: sorted(sources) for target, sources in dependents.items()
    }


def compute_potential_impact(
    files: list[dict[str, Any]],
    dependencies: list[dict[str, str]],
    selected_file: str,
) -> dict[str, Any]:
    known = _known_files(files, dependencies)
    if selected_file not in known:
        raise UnknownFileError(selected_file)

    reverse = _reverse_adjacency(dependencies)
    visited = {selected_file}
    distances: dict[str, int] = {}
    queue: deque[str] = deque([selected_file])
    dist_from_selected = {selected_file: 0}

    while queue:
        current = queue.popleft()
        current_distance = dist_from_selected[current]
        for dependent in reverse.get(current, []):
            if dependent in visited:
                continue
            visited.add(dependent)
            hop = current_distance + 1
            dist_from_selected[dependent] = hop
            distances[dependent] = hop
            queue.append(dependent)

    ordered = sorted(distances, key=lambda path: (distances[path], path))
    direct = [path for path in ordered if distances[path] == 1]
    transitive = [path for path in ordered if distances[path] > 1]
    return {
        "selected_file": selected_file,
        "direct_dependents": direct,
        "transitive_dependents": transitive,
        "all_impacted_files": ordered,
        "total_impacted": len(ordered),
        "distances": {path: distances[path] for path in ordered},
    }
