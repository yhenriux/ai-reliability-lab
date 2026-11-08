"""CLI runner for CI quality gates and real local-model experiments."""
import argparse
import json
from pathlib import Path

from engine import execute_suite, evaluate_gates, load_data


def main():
    parser = argparse.ArgumentParser(description="Aurora Bank evaluation runner")
    parser.add_argument("--provider", choices=["demo", "ollama"], default="demo")
    parser.add_argument("--model", default=None)
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--dataset-version", choices=["1.0", "2.0"], default="2.0")
    parser.add_argument("--balanced-per-category", type=int, default=0)
    parser.add_argument("--gates", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    parser.add_argument("--db", type=Path, default=Path("artifacts/cli-runs.db"))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--print-json", action="store_true", help="Print full synthetic report in CI logs")
    args = parser.parse_args()

    _, dataset = load_data(args.dataset_version)
    cases = dataset["cases"]
    if args.balanced_per_category:
        if args.balanced_per_category < 1:
            parser.error("balanced-per-category must be positive")
        selected = []
        for category in ("answerable", "unanswerable", "adversarial", "ambiguous"):
            selected.extend([c for c in cases if c["category"] == category][:args.balanced_per_category])
        cases = selected
    model = args.model or ("deterministic-baseline-v1" if args.provider == "demo" else "smollm2:135m")
    run = execute_suite(cases=cases, provider=args.provider, model=model, url=args.url,
                        db=args.db, dataset_version=args.dataset_version)
    gates = None
    if args.gates:
        thresholds = json.loads(args.gates.read_text(encoding="utf-8"))
        baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
        gates = evaluate_gates(run, thresholds, baseline)
        run["quality_gates"] = gates
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"mode": run["mode"], "model": run["model"],
                      "dataset": run["dataset_version"], "metrics": run["metrics"],
                      "gates": gates, "artifact": str(args.output)}, ensure_ascii=False, indent=2))
    if args.print_json:
        print("BEGIN_AURORA_REPORT_JSON")
        print(json.dumps(run, ensure_ascii=False))
        print("END_AURORA_REPORT_JSON")
    if args.strict and gates is not None and not gates["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
