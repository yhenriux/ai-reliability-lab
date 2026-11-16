"""Integration smoke checks for all six Streamlit modules using AppTest."""
import pytest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'app.py'
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("page", [
    "Ver resultados", "Testar uma pergunta", "Executar avaliação",
    "Comparar execuções", "Testar segurança", "Consultar histórico e exportar",
])
def test_six_modules_render(page):
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.sidebar.radio(key="task").set_value(page).run()
    assert not at.exception
    assert any(heading.value == page for heading in at.subheader)
    visible_text = " ".join(caption.value for caption in at.caption)
    assert "PARA QUE SERVE" in visible_text
    assert "O QUE ESTA TELA DEMONSTRA" in visible_text
    assert "LIMITE DESTA DEMONSTRAÇÃO" in visible_text


def test_full_evaluation_from_interface():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="task").set_value("Executar avaliação").run()
    assert not at.exception
    assert any(b.label == "Executar avaliação completa" for b in at.button)
    next(b for b in at.button if b.label == "Executar avaliação completa").click().run()
    assert not at.exception
    assert at.session_state["latest"]["metrics"]["n"] == 100


def test_safety_single_case_from_interface():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="task").set_value("Testar segurança").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Executar cenário selecionado").click().run()
    assert not at.exception
    assert at.session_state["safety"]["metrics"]["n"] == 1


def test_playground_generates_answer_without_browser_exception():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="task").set_value("Testar uma pergunta").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Gerar resposta").click().run()
    assert not at.exception
    assert any("Resposta" in m.value for m in at.markdown)
    assert any("não recebem nota" in warning.value for warning in at.warning)
    reference = at.selectbox[0]
    reference.set_value(reference.options[1]).run()
    next(b for b in at.button if b.label == "Gerar resposta").click().run()
    assert not at.exception
    assert at.json


def test_regression_journey_from_two_ui_executions():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="task").set_value("Executar avaliação").run()
    for _ in range(2):
        next(b for b in at.button if b.label == "Executar avaliação completa").click().run()
        assert not at.exception
    at.sidebar.radio(key="task").set_value("Comparar execuções").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Comparar execuções").click().run()
    assert not at.exception
    assert any("Casos que pioraram" in metric.label for metric in at.metric)


def test_safety_suite_journey():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="task").set_value("Testar segurança").run()
    next(b for b in at.button if b.label == "Executar suíte de segurança").click().run()
    assert not at.exception
    assert at.session_state["safety"]["metrics"]["n"] == 40


def test_dataset_switch_keeps_evaluation_working():
    at = AppTest.from_file(APP, default_timeout=30).run()
    next(s for s in at.selectbox if s.label == "Versão do conjunto de testes").set_value("1.0").run()
    at.sidebar.radio(key="task").set_value("Executar avaliação").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Executar avaliação completa").click().run()
    assert not at.exception
    assert at.session_state["latest"]["dataset_version"] == "1.0"


def test_report_serialization_round_trip(tmp_path):
    import json
    import pandas as pd
    from engine import execute_suite
    from reports import export_cases_csv

    run = execute_suite(db=tmp_path / "runs.db")
    json_export = json.dumps(run, ensure_ascii=False, indent=2)
    csv_export = export_cases_csv(run["cases"])
    assert json.loads(json_export)["metrics"]["n"] == 100
    assert len(pd.read_csv(__import__("io").StringIO(csv_export))) == 100
    assert "failure_reasons" in csv_export


def test_dashboard_distinguishes_real_run_and_filters_failures():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("Execução real" in caption.value for caption in at.caption)
    assert not any("resposta esperada" in info.value for info in at.info)
    assert [metric.label for metric in at.metric] == ["Aprovação", "Falhas críticas", "Latência p95"]
    at.radio[0].set_value("Com falha").run()
    assert not at.exception
    assert set(at.dataframe[0].value["Resultado"]) == {"Com falha"}
    reasons = " ".join(at.dataframe[0].value["Motivo da falha"])
    assert "citation_mismatch" not in reasons
    assert "fonte citada" in reasons.lower()


def test_execution_settings_survive_history_and_filtered_evaluation():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.selectbox(key="dataset_version").set_value("1.0").run()
    at.sidebar.radio(key="task").set_value("Consultar histórico e exportar").run()
    assert not at.exception
    assert len(at.sidebar.selectbox) == 0
    at.sidebar.radio(key="task").set_value("Executar avaliação").run()
    assert at.sidebar.selectbox(key="dataset_version").value == "1.0"
    at.multiselect[0].set_value(["answerable"]).run()
    next(b for b in at.button if b.label == "Executar casos selecionados").click().run()
    assert not at.exception
    assert 0 < at.session_state["latest"]["metrics"]["n"] < 100
    assert {case["category"] for case in at.session_state["latest"]["cases"]} == {"answerable"}


def test_history_import_and_export(tmp_path, monkeypatch):
    import json
    from functools import partial

    import engine

    db = tmp_path / "history.db"
    run = engine.execute_suite(db=tmp_path / "source.db")
    monkeypatch.setattr(engine, "list_runs", partial(engine.list_runs, db=db))
    monkeypatch.setattr(engine, "save_run", partial(engine.save_run, db=db))
    monkeypatch.setenv("AI_LAB_ENABLE_IMPORT", "1")
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="task").set_value("Consultar histórico e exportar").run()
    at.file_uploader[0].upload("run.json", json.dumps(run).encode(), "application/json").run()
    next(b for b in at.button if b.label == "Importar relatório").click().run()
    assert not at.exception
    assert at.success
    assert engine.list_runs()[0]["id"] == run["id"]
    at.run()
    assert run["id"][:8] in set(at.dataframe[0].value["Execução"])
    assert {button.proto.label for button in at.get("download_button")} == {"Baixar JSON", "Baixar CSV"}


def test_public_copy_explains_fictional_data_and_open_source_stack():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    copy = " ".join(markdown.value for markdown in at.markdown)
    captions = " ".join(caption.value for caption in at.caption)
    assert "assistentes de IA antes de confiar neles" in copy
    assert "tecnologias open source" in captions
    assert "nenhum dado de cliente" in captions


def test_comparison_prefers_two_real_model_runs():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio(key="task").set_value("Comparar execuções").run()
    assert not at.exception
    selectors = [box for box in at.selectbox if box.label.startswith("Execução")]
    assert len(selectors) == 2
    assert "Execução real" in selectors[0].value
    assert "Execução real" in selectors[1].value
