from __future__ import annotations

import argparse
import re
from pathlib import Path


def normalize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def calculate_wer(reference: list[str], hypothesis: list[str]) -> tuple[float, int, int, int]:
    rows = len(reference) + 1
    columns = len(hypothesis) + 1
    costs = [[0] * columns for _ in range(rows)]
    operations = [[None] * columns for _ in range(rows)]

    for row in range(1, rows):
        costs[row][0] = row
        operations[row][0] = "deletion"
    for column in range(1, columns):
        costs[0][column] = column
        operations[0][column] = "insertion"

    for row in range(1, rows):
        for column in range(1, columns):
            same = reference[row - 1] == hypothesis[column - 1]
            choices = (
                (costs[row - 1][column - 1] + (not same), "match" if same else "substitution"),
                (costs[row - 1][column] + 1, "deletion"),
                (costs[row][column - 1] + 1, "insertion"),
            )
            costs[row][column], operations[row][column] = min(
                choices, key=lambda choice: choice[0]
            )

    substitutions = insertions = deletions = 0
    row, column = len(reference), len(hypothesis)
    while row or column:
        operation = operations[row][column]
        if operation in {"match", "substitution"}:
            substitutions += operation == "substitution"
            row -= 1
            column -= 1
        elif operation == "deletion":
            deletions += 1
            row -= 1
        else:
            insertions += 1
            column -= 1

    wer = costs[-1][-1] / len(reference) if reference else float(bool(hypothesis))
    return wer, substitutions, insertions, deletions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a manual reference transcript with a transcription hypothesis."
    )
    parser.add_argument("reference", type=Path)
    parser.add_argument("hypothesis", type=Path)
    arguments = parser.parse_args()
    reference = normalize(arguments.reference.read_text(encoding="utf-8"))
    hypothesis = normalize(arguments.hypothesis.read_text(encoding="utf-8"))
    wer, substitutions, insertions, deletions = calculate_wer(reference, hypothesis)
    print(f"Reference words: {len(reference)}")
    print(f"Hypothesis words: {len(hypothesis)}")
    print(f"WER: {wer:.3%}")
    print(f"Substitutions: {substitutions}")
    print(f"Insertions: {insertions}")
    print(f"Deletions: {deletions}")


if __name__ == "__main__":
    main()
