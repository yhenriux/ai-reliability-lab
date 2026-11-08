"""Prepare a human-review worksheet from a verified real-model benchmark.

This script NEVER auto-fills human judgments. It attaches model outputs,
heuristic verdicts and expected evidence to the fixed 20-case sample.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from engine import digest, load_data


def prepare_review(run_path, sample_path, output_path):
    run = json.loads(Path(run_path).read_text(encoding="utf-8"))
    _, dataset = load_data("2.0")
    if run.get("mode") != "real_local_llm":
        raise ValueError("Only real-model runs are accepted")
    if run.get("dataset_version") != "2.0" or run.get("dataset_hash") != digest(dataset):
        raise ValueError("Dataset version/hash mismatch")
    if run.get("metrics", {}).get("n") != 100:
        raise ValueError("Review requires a complete 100-case benchmark")
    results = {r["case_id"]: r for r in run["cases"]}
    if len(results) != 100:
        raise ValueError("Expected 100 unique case IDs")
    cases = {c["id"]: c for c in dataset["cases"]}
    with Path(sample_path).open(newline="", encoding="utf-8") as stream:
        sample = list(csv.DictReader(stream))
    if len(sample) != 20 or len({r["case_id"] for r in sample}) != 20:
        raise ValueError("Expected 20 unique review sample cases")
    fields = list(sample[0]) + [
        "model_name", "model_answer", "expected_answer",
        "model_citations", "heuristic_failure_reasons", "latency_ms",
    ]
    out = []
    for item in sample:
        case_id = item["case_id"]
        if case_id not in results or case_id not in cases:
            raise ValueError(f"Missing case: {case_id}")
        row = results[case_id]
        case = cases[case_id]
        item.update({
            "automated_pass": str(row["passed"]).lower(),
            "model_name": run["model"],
            "model_answer": row["answer"],
            "expected_answer": case["expected_answer"],
            "model_citations": ";".join(row["citations"]),
            "heuristic_failure_reasons": ";".join(row["failure_reasons"]),
            "latency_ms": row["latency_ms"],
        })
        out.append(item)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--sample", type=Path, default=Path("data/review_sample_v2.csv"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/review_20_prefilled.csv"))
    args = parser.parse_args()
    print(prepare_review(args.run, args.sample, args.output))


if __name__ == "__main__":
    main()
