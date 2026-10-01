"""Train and evaluate the candidate-set PyTorch reranker.

Train queries: 18. Validation: 6 (early stopping / checkpoint selection).
Test queries: 6, evaluated once after the checkpoint is frozen.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyzer import analyze_file, build_module_index
from config import (
    EMBEDDING_MODEL_NAME,
    RERANKER_LEARNING_RATE,
    RERANKER_MAX_EPOCHS,
    RERANKER_PATIENCE,
    RERANKER_SEED,
    RERANKER_SOURCE_PINS,
)
from reranker import CodeReranker, extract_features, save_checkpoint
from semantic import get_model, symbol_embedding_text, _l2_normalize


OUTPUT_DIR = ROOT / "outputs" / "reranker"
SPLIT_SOURCE = ROOT / "outputs" / "retrieval_baseline.json"
TRAINING_DATA = ROOT / "training_data.json"


def set_seed(seed: int = RERANKER_SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_split() -> dict:
    payload = json.loads(SPLIT_SOURCE.read_text())
    split = payload["phase5_query_split"]
    return {
        "train": _flatten(split["train"]),
        "validation": _flatten(split["validation"]),
        "test": _flatten(split["test"]),
        "raw": split,
    }


def _flatten(grouped: dict[str, list[str]]) -> list[str]:
    queries: list[str] = []
    for repo in sorted(grouped):
        queries.extend(grouped[repo])
    return queries


def _assert_split_isolation(split: dict) -> None:
    train, val, test = set(split["train"]), set(split["validation"]), set(split["test"])
    assert train.isdisjoint(val)
    assert train.isdisjoint(test)
    assert val.isdisjoint(test)
    assert len(train) == 18 and len(val) == 6 and len(test) == 6


def pins_root() -> Path:
    return Path(os.environ.get("CODEATLAS_PINS_DIR", ROOT / ".cache" / "codeatlas_pins"))


def ensure_pinned_repos() -> dict[str, Path]:
    root = pins_root()
    root.mkdir(parents=True, exist_ok=True)
    paths = {}
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    folder = {
        "pallets/flask": "flask",
        "pallets/click": "click",
        "fastapi/fastapi": "fastapi",
    }
    for repo, pin in RERANKER_SOURCE_PINS.items():
        dest = root / folder[repo]
        if dest.is_dir() and (dest / ".git").exists():
            head = subprocess.check_output(
                ["git", "-C", str(dest), "rev-parse", "HEAD"], text=True
            ).strip()
            if head == pin["commit"]:
                paths[repo] = dest
                continue
        if dest.exists():
            subprocess.run(["rm", "-rf", str(dest)], check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "clone",
                "--depth",
                "1",
                "--branch",
                pin["tag"],
                pin["url"],
                str(dest),
            ],
            check=True,
            env=env,
        )
        head = subprocess.check_output(
            ["git", "-C", str(dest), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != pin["commit"]:
            raise RuntimeError(
                f"{repo} HEAD {head} does not match pinned commit {pin['commit']}"
            )
        paths[repo] = dest
    return paths


def resolve_examples(examples: list[dict], repos: dict[str, Path]) -> dict:
    needed: dict[str, set[str]] = defaultdict(set)
    for example in examples:
        needed[example["repo"]].add(example["file"])

    indexes: dict[str, dict[tuple[str, str], list[dict]]] = {}
    for repo, files in needed.items():
        root = repos[repo]
        rels = sorted(files)
        module_index = build_module_index(rels)
        by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for rel in rels:
            path = root / rel
            if not path.is_file():
                continue
            info = analyze_file(path, root, module_index=module_index)
            for symbol in info.get("symbols", []):
                by_key[(symbol["file"], symbol["name"])].append(symbol)
        indexes[repo] = by_key

    resolved = []
    unresolved = []
    ambiguous = []
    type_mismatches = []
    expected_type = {
        "FunctionDef": {"function", "method"},
        "AsyncFunctionDef": {"async_function", "async_method"},
        "ClassDef": {"class"},
    }
    for example in examples:
        matches = indexes.get(example["repo"], {}).get(
            (example["file"], example["chunk_name"]),
            [],
        )
        if not matches:
            unresolved.append(example)
        elif len(matches) > 1:
            ambiguous.append(
                {
                    "example": example,
                    "qualified_names": [item["qualified_name"] for item in matches],
                }
            )
        else:
            symbol = matches[0]
            allowed = expected_type.get(example["chunk_type"], set())
            if symbol["type"] not in allowed or (
                example["chunk_type"] == "FunctionDef" and symbol["type"] == "method"
            ):
                type_mismatches.append(
                    {
                        "file": example["file"],
                        "chunk_name": example["chunk_name"],
                        "labeled_type": example["chunk_type"],
                        "ast_type": symbol["type"],
                        "qualified_name": symbol["qualified_name"],
                        "still_resolved": True,
                    }
                )
            resolved.append({**example, "symbol": symbol})
    return {
        "resolved": resolved,
        "unresolved": unresolved,
        "ambiguous": ambiguous,
        "type_mismatches": type_mismatches,
    }


def encode_pairs(resolved: list[dict]) -> list[dict]:
    model = get_model()
    query_cache: dict[str, np.ndarray] = {}
    text_cache: dict[str, np.ndarray] = {}
    enriched = []
    for item in resolved:
        query = item["query"]
        symbol = item["symbol"]
        text = symbol_embedding_text(symbol)
        if query not in query_cache:
            query_cache[query] = _l2_normalize(
                np.asarray(
                    model.encode([query], convert_to_numpy=True)[0],
                    dtype=np.float32,
                )
            )
        if text not in text_cache:
            text_cache[text] = _l2_normalize(
                np.asarray(
                    model.encode([text], convert_to_numpy=True)[0],
                    dtype=np.float32,
                )
            )
        cosine = float(query_cache[query] @ text_cache[text])
        features = extract_features(query, symbol, cosine)
        enriched.append({**item, "minilm_cosine": cosine, "features": features})
    return enriched


def group_by_query(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["query"]].append(row)
    return grouped


def candidate_metrics(grouped: dict[str, list[dict]], score_key: str) -> dict:
    hit1 = 0
    mrr = 0.0
    ranks: list[int] = []
    queries = sorted(grouped)
    for query in queries:
        candidates = grouped[query]
        ordered = sorted(
            candidates,
            key=lambda row: (
                -float(row[score_key]),
                row["file"],
                row["chunk_name"],
            ),
        )
        rank = next(
            i
            for i, row in enumerate(ordered, start=1)
            if row["label"] == 1
        )
        ranks.append(rank)
        if rank == 1:
            hit1 += 1
        mrr += 1.0 / rank
    n = len(queries)
    return {
        "queries": n,
        "hit_at_1": hit1 / n if n else 0.0,
        "mrr": mrr / n if n else 0.0,
        "mean_positive_rank": sum(ranks) / n if n else 0.0,
        "positive_ranks": ranks,
    }


def tensors_for(rows: list[dict]) -> tuple[torch.Tensor, torch.Tensor]:
    x = torch.tensor([row["features"] for row in rows], dtype=torch.float32)
    y = torch.tensor([float(row["label"]) for row in rows], dtype=torch.float32)
    return x, y


def apply_model_scores(model: CodeReranker, rows: list[dict]) -> list[dict]:
    model.eval()
    x, _ = tensors_for(rows)
    with torch.no_grad():
        logits = model(x).squeeze(-1)
    scored = []
    values = [float(logits.item())] if logits.ndim == 0 else [float(v) for v in logits.tolist()]
    for row, score in zip(rows, values):
        scored.append({**row, "rerank_logit": score})
    return scored


def main() -> None:
    set_seed()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    split = load_split()
    _assert_split_isolation(split)
    examples = json.loads(TRAINING_DATA.read_text())["examples"]
    repos = ensure_pinned_repos()
    resolution = resolve_examples(examples, repos)
    if resolution["unresolved"] or resolution["ambiguous"]:
        (OUTPUT_DIR / "data_validation.json").write_text(
            json.dumps(
                {
                    "defensible": False,
                    "resolved": len(resolution["resolved"]),
                    "unresolved": len(resolution["unresolved"]),
                    "ambiguous": len(resolution["ambiguous"]),
                    "type_mismatches": resolution["type_mismatches"],
                    "pins": RERANKER_SOURCE_PINS,
                },
                indent=2,
            )
            + "\n"
        )
        raise SystemExit("Dataset is not fully resolvable; refusing to train.")

    enriched = encode_pairs(resolution["resolved"])
    by_query = group_by_query(enriched)
    train_rows = [row for query in split["train"] for row in by_query[query]]
    val_rows = [row for query in split["validation"] for row in by_query[query]]
    test_rows = [row for query in split["test"] for row in by_query[query]]
    assert {row["query"] for row in train_rows} == set(split["train"])
    assert {row["query"] for row in test_rows}.isdisjoint(split["train"])
    assert {row["query"] for row in test_rows}.isdisjoint(split["validation"])

    validation_report = {
        "defensible": True,
        "resolved": len(resolution["resolved"]),
        "unresolved": 0,
        "ambiguous": 0,
        "type_mismatches": resolution["type_mismatches"],
        "pins": RERANKER_SOURCE_PINS,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "note": "Labels were not edited. One labeled FunctionDef is an AST method (Click Repo.set_config).",
    }
    (OUTPUT_DIR / "data_validation.json").write_text(
        json.dumps(validation_report, indent=2) + "\n"
    )
    (OUTPUT_DIR / "split.json").write_text(
        json.dumps(
            {
                "method": split["raw"]["method"],
                "counts": split["raw"]["counts"],
                "train": split["train"],
                "validation": split["validation"],
                "test": split["test"],
                "pins": RERANKER_SOURCE_PINS,
            },
            indent=2,
        )
        + "\n"
    )

    model = CodeReranker()
    loss_fn = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=RERANKER_LEARNING_RATE)
    x_train, y_train = tensors_for(train_rows)

    best_state = None
    best_val_mrr = -1.0
    best_epoch = 0
    wait = 0
    history = []
    for epoch in range(1, RERANKER_MAX_EPOCHS + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(x_train).squeeze(-1)
        loss = loss_fn(logits, y_train)
        loss.backward()
        optimizer.step()

        val_scored = apply_model_scores(model, val_rows)
        val_metrics = candidate_metrics(group_by_query(val_scored), "rerank_logit")
        minilm_val = candidate_metrics(group_by_query(val_rows), "minilm_cosine")
        history.append(
            {
                "epoch": epoch,
                "train_bce": float(loss.item()),
                "val_mrr": val_metrics["mrr"],
                "val_hit_at_1": val_metrics["hit_at_1"],
                "val_minilm_mrr": minilm_val["mrr"],
            }
        )
        improved = val_metrics["mrr"] > best_val_mrr + 1e-12
        if improved:
            best_val_mrr = val_metrics["mrr"]
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= RERANKER_PATIENCE:
                break

    assert best_state is not None
    model.load_state_dict(best_state)
    save_checkpoint(
        model,
        OUTPUT_DIR / "best.pt",
        extra={
            "best_epoch": best_epoch,
            "best_val_mrr": best_val_mrr,
            "seed": RERANKER_SEED,
        },
    )

    val_final = candidate_metrics(
        group_by_query(apply_model_scores(model, val_rows)), "rerank_logit"
    )
    training_metrics = {
        "seed": RERANKER_SEED,
        "optimizer": "Adam",
        "learning_rate": RERANKER_LEARNING_RATE,
        "loss": "BCEWithLogitsLoss",
        "architecture": "Linear(4,8) ReLU Linear(8,1)",
        "features": [
            "minilm_cosine",
            "name_jaccard",
            "docstring_jaccard",
            "identifier_jaccard",
        ],
        "best_epoch": best_epoch,
        "epochs_ran": history[-1]["epoch"],
        "early_stopping_patience": RERANKER_PATIENCE,
        "train_queries": 18,
        "validation_queries": 6,
        "validation_minilm": candidate_metrics(group_by_query(val_rows), "minilm_cosine"),
        "validation_reranker": val_final,
        "history": history,
        "test_queries_used": False,
    }
    (OUTPUT_DIR / "training_metrics.json").write_text(
        json.dumps(training_metrics, indent=2) + "\n"
    )

    # Held-out test evaluation happens only after the checkpoint is frozen.
    test_minilm = candidate_metrics(group_by_query(test_rows), "minilm_cosine")
    test_rerank = candidate_metrics(
        group_by_query(apply_model_scores(model, test_rows)), "rerank_logit"
    )
    improved = (
        test_rerank["mrr"] > test_minilm["mrr"] + 1e-12
        or (
            abs(test_rerank["mrr"] - test_minilm["mrr"]) <= 1e-12
            and test_rerank["hit_at_1"] > test_minilm["hit_at_1"]
        )
    )
    test_metrics = {
        "setting": "candidate_set_ranking_not_full_corpus_retrieval",
        "test_queries": 6,
        "candidates_per_query": 4,
        "minilm": test_minilm,
        "minilm_plus_reranker": test_rerank,
        "reranker_improves_held_out": improved,
        "production_decision": (
            "enable_reranker" if improved else "keep_minilm_only"
        ),
    }
    (OUTPUT_DIR / "test_metrics.json").write_text(
        json.dumps(test_metrics, indent=2) + "\n"
    )
    print(json.dumps(test_metrics, indent=2))


if __name__ == "__main__":
    main()
