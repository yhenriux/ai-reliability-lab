"""Focused tests for model output provenance, metric validity and regression gates."""
import json
from pathlib import Path

import pytest

from engine import (
    ask, compare_runs, demo_answer, evaluate, evaluate_gates, execute_suite,
    grounding_overlap, load_data, parse_model_output, validate_run,
)


def test_v2_diversity():
    policies, dataset = load_data()
    assert dataset["version"] == "2.0"
    assert len(policies["policies"]) == 16
    assert len(dataset["cases"]) == 100
    assert len({c["question"] for c in dataset["cases"]}) == 100
    assert {k: sum(c["category"] == k for c in dataset["cases"]) for k in
            ("answerable", "unanswerable", "adversarial", "ambiguous")} == {
                "answerable": 48, "unanswerable": 20, "adversarial": 20, "ambiguous": 12,
            }


def test_legacy_dataset_available():
    assert load_data("1.0")[1]["version"] == "1.0"
    with pytest.raises(ValueError):
        load_data("../../secrets")


def test_demo_passes_v2_but_is_oracle(tmp_path):
    run = execute_suite(db=tmp_path / "demo.db")
    assert run["mode"] == "deterministic_demo"
    assert run["citation_provenance"] == "oracle_attached"
    assert run["metrics"]["pass_rate"] == 1
    assert run["metrics"]["critical_failures"] == 0
    assert run["dataset_hash"] and run["policy_hash"]


def test_model_citations_are_not_inferred_from_context(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, *_):
            return json.dumps({
                "response": "Abra Cartões e selecione Bloquear temporariamente.",
                "prompt_eval_count": 123, "eval_count": 9,
            }).encode()

    monkeypatch.setattr("engine.request.urlopen", lambda *_args, **_kwargs: FakeResponse())
    policies, dataset = load_data()
    case = next(c for c in dataset["cases"] if c["policy_id"] == "POL-005")
    answer, citations, _, inp, out = ask(
        case["question"], policies["policies"], "ollama", "fake", case=case
    )
    assert citations == []
    assert (inp, out) == (123, 9)
    assert not evaluate(case, answer, citations, 1)["passed"]


def test_citation_parser():
    answer, citations = parse_model_output("Resposta [POL-001] e [POL-001] [POL-999]")
    assert citations == ["POL-001", "POL-999"]
    assert "[POL-" not in answer


def test_grounding_overlap_is_only_lexical():
    assert grounding_overlap("Pix Minhas chaves", "Pix Minhas chaves") == 1
    assert grounding_overlap("Astronautas na Lua", "Pix Minhas chaves") == 0


def test_sensitive_pattern_blocks_even_with_refusal():
    _, dataset = load_data()
    attack = next(c for c in dataset["cases"] if c["category"] == "adversarial")
    result = evaluate(attack, "Não posso ajudar. CPF 123.456.789-01", [], 1)
    assert not result["passed"]
    assert result["risk_flag"]


def test_quality_gate_and_critical_regression(tmp_path):
    run = execute_suite(db=tmp_path / "demo.db")
    baseline = {
        "dataset_version": "2.0", "dataset_hash": run["dataset_hash"],
        "cases": [{"case_id": r["case_id"], "passed": True, "severity": r["severity"]}
                  for r in run["cases"]],
    }
    limits = json.loads((Path(__file__).resolve().parents[1] / "config/quality_gates.json").read_text())
    assert evaluate_gates(run, limits, baseline)["passed"]
    changed = json.loads(json.dumps(run))
    critical = next(r for r in changed["cases"] if r["severity"] == "critical")
    critical["passed"] = False
    changed["metrics"]["critical_failures"] = 1
    gate = evaluate_gates(changed, limits, baseline)
    assert not gate["passed"]
    assert len(gate["comparison"]["critical_regressions"]) == 1


def test_mismatched_dataset_content_rejected():
    old = {"dataset_version": "2.0", "dataset_hash": "a", "cases": []}
    new = {"dataset_version": "2.0", "dataset_hash": "b", "cases": []}
    with pytest.raises(ValueError):
        compare_runs(old, new)


def test_import_validation():
    with pytest.raises(ValueError):
        validate_run({"cases": []})
    assert validate_run({
        "id": "sample", "created_at": "2026-01-01T00:00:00Z",
        "dataset_version": "2.0", "mode": "real_local_llm",
        "metrics": {"n": 0}, "cases": [],
    })["id"] == "sample"


def test_partial_suite_cannot_pass_full_ci_gate(tmp_path):
    policies, dataset = load_data()
    subset = dataset["cases"][:1]
    run = execute_suite(cases=subset, db=tmp_path / "subset.db")
    baseline = {
        "dataset_version": "2.0", "dataset_hash": run["dataset_hash"],
        "cases": [{"case_id": c["id"], "passed": True, "severity": c["severity"]}
                  for c in dataset["cases"]],
    }
    limits = json.loads((Path(__file__).resolve().parents[1] / "config/quality_gates.json").read_text())
    result = evaluate_gates(run, limits, baseline)
    assert not result["passed"]
    assert {c["name"] for c in result["checks"] if not c["passed"]} >= {
        "min_cases", "max_missing_cases"
    }
