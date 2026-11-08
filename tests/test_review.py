"""The review preparation must preserve human judgment fields as pending."""
import csv
import json

import pytest

from engine import execute_suite
from scripts.prepare_human_review import prepare_review


def test_review_sheet_prefill_keeps_judgments_blank(tmp_path):
    run = execute_suite(db=tmp_path / "run.db")
    run["mode"] = "real_local_llm"
    run["model"] = "fixture-model"
    source = tmp_path / "run.json"
    source.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
    result = prepare_review(source, "data/review_sample_v2.csv", tmp_path / "review.csv")
    with result.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 20
    assert all(row["model_answer"] for row in rows)
    assert all(row["factual_correctness"] == "" for row in rows)
    assert all(row["grounding"] == "" for row in rows)
    assert all(row["safety"] == "" for row in rows)
    assert all(row["status"] == "pending_human_review" for row in rows)


def test_review_sheet_rejects_demo_mode(tmp_path):
    run = execute_suite(db=tmp_path / "run.db")
    source = tmp_path / "run.json"
    source.write_text(json.dumps(run), encoding="utf-8")
    with pytest.raises(ValueError, match="real-model"):
        prepare_review(source, "data/review_sample_v2.csv", tmp_path / "review.csv")
