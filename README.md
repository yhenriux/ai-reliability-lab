# AI Reliability Lab

## Banking FAQ Reliability Engineering

Interactive, reproducible evaluation workbench for the **Aurora Bank**, a wholly fictional bank. Includes **100 synthetic evaluation cases** (64 answerable, 12 unanswerable, 16 adversarial, 8 ambiguous) grounded in 16 fictional policies.

### Run locally

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install 'streamlit>=1.38,<2' 'pandas>=2.1,<3' pytest
streamlit run app.py
```

Open http://localhost:8501. No API key or paid service required.

### Six interactive modules

1. Dashboard: historical KPIs and runs.
2. Banking FAQ Playground: case-based and ad-hoc questions with evidence.
3. Evaluation Studio: full 100-case suite or category subsets.
4. Regression Testing: compare two recorded executions by case ID.
5. Safety Lab: 16 synthetic adversarial and 12 out-of-knowledge cases.
6. Reports & History: SQLite persistence with JSON and CSV downloads.

### Optional: evaluate a genuine local LLM

Install Ollama, download a model (e.g. `ollama pull llama3.2:1b`) and choose **ollama** in the sidebar. Supply the local model name and Ollama URL. Calls use the provider's observed input/output token counts. Pricing is user-configured and defaults to zero.

### Engineering notes

- `engine.py`: independent evaluation, provider adapters, SQLite, comparisons.
- `data/policies.json`: versioned, fictional FAQ knowledge base.
- `data/golden_v1.json`: versioned 100-case gold dataset.
- `app.py`: Streamlit single-app user interface.
- `tests/test_engine.py`: deterministic tests.
- `.github/workflows/ci.yml`: tests on Python 3.12.
- `Dockerfile`: optional self-hosted run.

```bash
pip install pytest
pytest -q
docker build -t ai-reliability-lab .
docker run --rm -p 8501:8501 ai-reliability-lab
```

### Interpreting results

**Critical:** demo mode reads the gold case classification and policy mapping to produce deterministic reference replies. Thus its expected 100% pass rate only confirms the test harness; it **is not model accuracy**. In Ollama mode the app provides ground-truth policy evidence for answerable cases, so it assesses answer behavior under supplied evidence, not retrieval quality. Token-F1, keyword coverage and exact refusal checks are **heuristic metrics**; passing the adversarial set does not demonstrate broad prompt-injection resistance. The pipeline attaches citation IDs when evidence is selected, which is a measure of source routing, not verified factual entailment. Review outputs manually for substantive correctness.

Measured latency is local observation of each invocation. Demo latency is **not LLM latency**; cost is calculated only from actual provider token counters and manually configured prices. JSON metadata distinguishes `deterministic_demo` from `real_local_llm`.

For public free hosting, SQLite may be temporary; persisted runs can disappear if container storage resets. Export JSON/CSV for lasting evidence. This app uses **no actual bank data, PII, live bank integrations or paid API calls**.

### Project decisions

See [engineering plan](docs/PROJECT_PLAN.md).
