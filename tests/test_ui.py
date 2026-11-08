"""Integration smoke checks for all six Streamlit modules using AppTest."""
import pytest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'app.py'
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("page", [
    "Dashboard", "Banking FAQ Playground", "Evaluation Studio",
    "Regression Testing", "Safety Lab", "Reports & History",
])
def test_six_modules_render(page):
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.radio[0].set_value(page).run()
    assert not at.exception


def test_full_evaluation_from_interface():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value("Evaluation Studio").run()
    assert not at.exception
    assert any(b.label == "Run Full Evaluation" for b in at.button)
    next(b for b in at.button if b.label == "Run Full Evaluation").click().run()
    assert not at.exception
    assert at.session_state["latest"]["metrics"]["n"] == 100


def test_safety_single_case_from_interface():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value("Safety Lab").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Run Selected Safety Case").click().run()
    assert not at.exception
    assert at.session_state["safety"]["metrics"]["n"] == 1


def test_playground_generates_answer_without_browser_exception():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value("Banking FAQ Playground").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Gerar resposta").click().run()
    assert not at.exception
    assert any("Resposta" in m.value for m in at.markdown)


def test_regression_journey_from_two_ui_executions():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value("Evaluation Studio").run()
    for _ in range(2):
        next(b for b in at.button if b.label == "Run Full Evaluation").click().run()
        assert not at.exception
    at.radio[0].set_value("Regression Testing").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Comparar execuções").click().run()
    assert not at.exception
    assert any("Novas regressões" in metric.label for metric in at.metric)


def test_safety_suite_journey():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value("Safety Lab").run()
    next(b for b in at.button if b.label == "Run Safety Suite").click().run()
    assert not at.exception
    assert at.session_state["safety"]["metrics"]["n"] == 40


def test_dataset_switch_keeps_evaluation_working():
    at = AppTest.from_file(APP, default_timeout=30).run()
    next(s for s in at.selectbox if s.label == "Dataset versionado").set_value("1.0").run()
    at.radio[0].set_value("Evaluation Studio").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Run Full Evaluation").click().run()
    assert not at.exception
    assert at.session_state["latest"]["dataset_version"] == "1.0"


def test_report_serialization_round_trip(tmp_path):
    import json
    import pandas as pd
    from engine import execute_suite

    run = execute_suite(db=tmp_path / "runs.db")
    json_export = json.dumps(run, ensure_ascii=False, indent=2)
    csv_export = pd.DataFrame(run["cases"]).to_csv(index=False)
    assert json.loads(json_export)["metrics"]["n"] == 100
    assert len(pd.read_csv(__import__("io").StringIO(csv_export))) == 100
    assert "failure_reasons" in csv_export
