import json
from pathlib import Path

import torch
import torch.nn as nn

import analyzer
import semantic


class CodeReranker(nn.Module):
    def __init__(self):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, 1)
        )

    def forward(self, x):
        return self.network(x)


def name_overlap(query, chunk_name):
    query = query.lower()
    chunk_name = chunk_name.lower()

    if chunk_name in query:
        return 1.0

    return 0.0


def path_overlap(query, file_path):
    query_words = query.lower().split()
    file_path = file_path.lower()

    for word in query_words:
        if word in file_path:
            return 1.0

    return 0.0


def is_test_file(file_path):
    file_path = file_path.lower()

    if "test" in file_path:
        return 1.0

    return 0.0


def extract_features(query, chunk):
    similarity = semantic.get_similarity(
        query,
        chunk["code"]
    )

    name_score = name_overlap(
        query,
        chunk["name"]
    )

    path_score = path_overlap(
        query,
        chunk["file"]
    )

    test_score = is_test_file(
        chunk["file"]
    )

    return [
        similarity,
        name_score,
        path_score,
        test_score
    ]


def find_chunk(chunks, file_path, chunk_name):
    for chunk in chunks:
        if (
            chunk["file"] == file_path
            and chunk["name"] == chunk_name
        ):
            return chunk

    return None


def build_training_tensors(repo_folder, examples):
    chunks = analyzer.extract_repo_chunks(repo_folder)

    feature_rows = []
    labels = []

    for example in examples:
        chunk = find_chunk(
            chunks,
            example["file"],
            example["chunk_name"]
        )

        if chunk is None:
            print(
                "Could not find:",
                example["file"],
                example["chunk_name"]
            )
            continue

        features = extract_features(
            example["query"],
            chunk
        )

        feature_rows.append(features)
        labels.append(example["label"])

    X = torch.tensor(
        feature_rows,
        dtype=torch.float32
    )

    y = torch.tensor(
        labels,
        dtype=torch.float32
    )

    return X, y


def train_model(X, y):
    model = CodeReranker()

    loss_fn = nn.BCEWithLogitsLoss()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.01
    )

    for epoch in range(100):
        optimizer.zero_grad()

        predictions = model(X).squeeze()

        loss = loss_fn(
            predictions,
            y
        )

        loss.backward()

        optimizer.step()

        if epoch % 10 == 0:
            print(
                f"Epoch {epoch}: "
                f"loss = {loss.item():.4f}"
            )

    return model


def load_training_data():
    with open("training_data.json") as file:
        data = json.load(file)

    return data["examples"]


if __name__ == "__main__":
    examples = load_training_data()

    print(
        f"Loaded {len(examples)} examples"
    )

    print(
        "Training data still needs "
        "local repository folders."
    )