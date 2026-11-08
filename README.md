# AI Reliability Lab

**Banking FAQ Reliability Engineering** | [Live demo](https://ai-reliability-lab.streamlit.app/)

A reproducible evaluation workbench for the **Aurora Bank**, a fully fictional institution. Its six-module Streamlit interface covers answer quality, citation provenance, refusal behavior, prompt-injection probes, observed latency, version comparisons, quality gates, and portable reports.

> **Interpretation matters:** the default demo is a deterministic oracle that knows the expected answers. Its 100% baseline is a **harness check**, not LLM accuracy. The real-model path uses Ollama and records generated responses and measured execution metadata.

## Scope and data

The default dataset **v2.0** contains 100 manually curated synthetic cases, all unique:

| Category | Cases |
|---|---:|
| Answerable banking FAQs | 48 |
| No available evidence | 20 |
| Adversarial/security probes | 20 |
| Ambiguous questions | 12 |

There are 16 fictional banking policies covering Pix, accounts, cards, security, credit, fees, service and investments. Dataset v1.0 remains available for historical comparisons; runs across different dataset versions are not comparable.

## Run locally (free)

Python 3.12 recommended.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt pytest
streamlit run app.py
```

Open http://localhost:8501. No API key is needed.

### Optional: real local LLM with Ollama

Install Ollama and download a small model:

```bash
ollama pull smollm2:135m
```

Enable the model provider **only in your own environment**:

```powershell
$env:AI_LAB_ENABLE_OLLAMA="1"
streamlit run app.py
```

Linux/macOS: `AI_LAB_ENABLE_OLLAMA=1 streamlit run app.py`.

The operator can set `AI_LAB_OLLAMA_URL` for an endpoint reachable from the application server. Visitors cannot set arbitrary server URLs. **The hosted Streamlit demo cannot access Ollama running on your laptop**. Avoid exposing an unauthenticated Ollama endpoint on the internet.

The [real-model GitHub Actions workflow](.github/workflows/real-model-smoke.yml) can also run a small CPU-only model on demand. It records **eight real inference cases** (two per category), model identity, latency, token counts, failures and JSON artifact. The small sample is a smoke experiment, not a statistically representative benchmark.

## CLI and reproducible CI

```bash
# Full 100-case deterministic suite, versioned quality gates, and regression baseline
python -m scripts.run_evaluation --provider demo \
  --dataset-version 2.0 \
  --baseline data/baseline_demo_v2.json \
  --gates config/quality_gates.json \
  --output artifacts/demo-evaluation.json --strict

# Eight real local LLM cases (requires Ollama running and model downloaded)
python -m scripts.run_evaluation --provider ollama --model smollm2:135m \
  --balanced-per-category 2 --output artifacts/real-smoke.json

python -m pytest -q
```

CI runs syntax checks, unit tests, six Streamlit module smoke checks, UI evaluation actions, and deterministic regression gates. Both CI and on-demand real-model workflows upload JSON artifacts. The first verified CPU run is also versioned at [data/real_smoke_smollm2_135m.json](data/real_smoke_smollm2_135m.json) and is visible in the public Dashboard/History (8 cases, 0/8 heuristic passes, p95 2030.392 ms). This intentionally small model repeatedly echoed the prompt; the sample is not a representative performance estimate. Quality gates configured for the deterministic oracle **must not be reused as proof of real model quality**.

## Interface

| Module | What you can do |
|---|---|
| Dashboard | Inspect run-level metrics, history and observed p95 latency |
| Banking FAQ Playground | Ask free questions or select a labeled test case |
| Evaluation Studio | Execute full or category-filtered suites |
| Regression Testing | Compare runs on the same dataset and identify critical regressions |
| Safety Lab | Run a single attack or the full safety/no-evidence suite |
| Reports & History | Inspect runs and download CSV/JSON |

Public hosting keeps **JSON export enabled**. Importing external JSON into shared SQLite is disabled by default to avoid untrusted visitors writing to shared history. To enable imports locally, set `AI_LAB_ENABLE_IMPORT=1`.

## Evaluation methodology and limitations

- **Token F1** compares model text with the reference. It is a lexical heuristic, sensitive to paraphrases.
- **Required concept coverage** checks expected key terms.
- **Grounding overlap** measures lexical overlap with the selected fictional policy; it cannot establish semantic entailment.
- **Citation fidelity** checks source IDs **actually emitted by a model**, not IDs silently attached by the evaluator. Demo citations are labeled as oracle-attached.
- **Refusal and attack checks** combine phrase patterns with simple sensitive-output detectors; they are not a comprehensive red-team audit.
- **Oracle evidence:** labeled answerable cases supply the correct policy to the model. These tests assess generation with provided evidence, not retrieval performance.
- **Cost:** based on provider token counts and operator-configured USD rates. Zero API price does not mean zero compute or infrastructure cost.
- **Latency:** wall-clock observation per call, labeled by mode; demo latencies are not model latencies.
- **Persistence:** SQLite may be reset by Streamlit Community Cloud restarts. Download reports for durable retention.

There is no customer data, no connection to a real bank, and no claim of regulatory compliance.

## Architecture

```text
Streamlit UI (6 modules)
  ├── versioned synthetic policies + 100-case dataset
  ├── evaluation engine
  │     ├── deterministic oracle demo
  │     └── Ollama local model (opt-in)
  ├── lexical grounding, source checks, refusals, safety
  ├── regression comparator + versioned quality gates
  └── SQLite run history / CSV and JSON export
         └── GitHub Actions CI + optional real-model smoke artifact
```

Key files: `app.py`, `engine.py`, `data/golden_v2.json`, `data/policies.json`, `config/quality_gates.json`, `scripts/run_evaluation.py`, `tests/`.

Read the [engineering plan](docs/PROJECT_PLAN.md) and [portfolio case study](docs/CASE_STUDY.md).

## Deployment

The public app uses [Streamlit Community Cloud](https://share.streamlit.io) with repository `yhenriux/ai-reliability-lab`, branch `main`, entrypoint `app.py`. It requires only `streamlit` and `pandas`, as declared in `requirements.txt`. Docker remains optional for local use.
