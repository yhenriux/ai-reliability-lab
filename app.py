"""Six-module Streamlit interface for the Aurora Bank evaluation laboratory."""
import json
import os

import pandas as pd
import streamlit as st

from engine import (
    DB, ROOT, ask, compare_runs, evaluate, evaluate_gates, execute_suite,
    list_runs, load_data, save_run, validate_run,
)

st.set_page_config(page_title="AI Reliability Lab", page_icon="🧪", layout="wide")
st.title("AI Reliability Lab")
st.caption("Banking FAQ Reliability Engineering | Aurora Bank é uma instituição inteiramente fictícia")

with st.sidebar:
    st.header("Configuração")
    dataset_version = st.selectbox("Dataset versionado", ["2.0", "1.0"])
    local_ollama_enabled = os.environ.get("AI_LAB_ENABLE_OLLAMA") == "1"
    provider = st.selectbox("Provedor", ["demo", "ollama"] if local_ollama_enabled else ["demo"])
    model = (
        "deterministic-baseline-v1" if provider == "demo"
        else st.text_input("Modelo Ollama", "smollm2:135m")
    )
    url = os.environ.get("AI_LAB_OLLAMA_URL", "http://127.0.0.1:11434")
    price_in = price_out = 0.0
    if provider == "ollama":
        price_in = st.number_input("USD/1M tokens input", min_value=0.0, value=0.0)
        price_out = st.number_input("USD/1M tokens output", min_value=0.0, value=0.0)
    st.info(
        "Demo: usa o gabarito para testar o pipeline. "
        "Aprovação de 100% não significa qualidade de um LLM."
        if provider == "demo" else
        "Ollama: inferência real. Evidências dos casos rotulados são fornecidas pelo gabarito."
    )
    if not local_ollama_enabled:
        st.caption("Ollama local: execute com AI_LAB_ENABLE_OLLAMA=1.")
    page = st.radio(
        "Navegação",
        ["Dashboard", "Banking FAQ Playground", "Evaluation Studio",
         "Regression Testing", "Safety Lab", "Reports & History"],
    )

policies, dataset = load_data(dataset_version)
# Versioned, independently observed model runs are available even if free hosting resets SQLite.
bundled_runs = [
    validate_run(json.loads(path.read_text(encoding="utf-8")))
    for path in sorted((ROOT / "data").glob("real_smoke_*.json"))
]
runs = sorted(
    {r["id"]: r for r in list_runs() + bundled_runs}.values(),
    key=lambda r: r["created_at"], reverse=True,
)


def percentage(value):
    return "N/D" if value is None else f"{value * 100:.1f}%"


def metrics_panel(m):
    a, b, c, d = st.columns(4)
    a.metric("Casos", m["n"])
    b.metric("Aprovação", percentage(m["pass_rate"]))
    c.metric("Bloqueio adversarial", percentage(m["safety_block_rate"]))
    d.metric(
        "Latência p95 observada",
        "N/D" if m["latency_p95_ms"] is None else f'{m["latency_p95_ms"]:.1f} ms',
    )
    a, b, c, d = st.columns(4)
    a.metric("Qualidade heurística", percentage(m.get("quality_pass_rate")))
    b.metric("Correspondência de citações", percentage(m.get("source_adherence")))
    c.metric("Sobreposição com evidência", percentage(m.get("grounding_overlap_mean")))
    d.metric("Falhas críticas", m.get("critical_failures", 0))
    st.caption(
        f'Falhas: {m["failures"]} | Padrões sensíveis: {m.get("risk_flags", 0)} | '
        f'Custo de API estimado: US$ {m["estimated_cost_usd"]:.6f} '
        "(preço configurado manualmente; custo de infraestrutura excluído)"
    )


def rows_panel(run):
    df = pd.DataFrame(run["cases"])
    if df.empty:
        st.info("Execução sem casos.")
        return
    cols = [
        "case_id", "category", "scenario", "question", "passed",
        "failure_reasons", "token_f1", "term_coverage",
        "grounding_overlap", "source_ok", "latency_ms",
    ]
    st.dataframe(df[[c for c in cols if c in df.columns]], hide_index=True, use_container_width=True)
    with st.expander("Respostas, referências e rastreabilidade"):
        st.dataframe(df, hide_index=True, use_container_width=True)


def execute(cases):
    try:
        with st.spinner("Executando a avaliação..."):
            return execute_suite(
                cases=cases, provider=provider, model=model, url=url,
                price_input=price_in, price_output=price_out,
                dataset_version=dataset_version,
            )
    except Exception as exc:
        st.error(f"Falha na execução: {exc}")
        return None


def run_label(run):
    return f'{run["created_at"]} | {run.get("mode", "?")} | {run["id"][:8]}'


if page == "Dashboard":
    st.subheader("Visão geral de confiabilidade")
    st.write(
        f'Dataset **{dataset["dataset_id"]} v{dataset["version"]}** '
        f'| {len(dataset["cases"])} cenários | {len(policies["policies"])} políticas fictícias'
    )
    current = [r for r in runs if r.get("dataset_version") == dataset_version]
    if current:
        preferred = next((i for i, r in enumerate(current) if r.get("mode") == "real_local_llm"), 0)
        run = st.selectbox("Execução em destaque", current, index=preferred, format_func=run_label)
        st.caption(f'Modelo: {run.get("model", "?")} | Amostra: {run["metrics"]["n"]} casos')
        if run.get("mode") == "deterministic_demo":
            st.warning("Indicadores do modo demo são verificações do pipeline, não resultados de LLM.")
        elif run["metrics"]["n"] < 100:
            st.info("Execução real em amostra pequena. Os resultados não representam a taxa de aprovação dos 100 casos.")
        if run.get("workflow_url"):
            st.markdown(f'[Ver execução verificável no GitHub Actions]({run["workflow_url"]})')
        metrics_panel(run["metrics"])
        history = pd.DataFrame([
            {"data": r["created_at"], "aprovação": r["metrics"]["pass_rate"]}
            for r in reversed(current) if r["metrics"]["pass_rate"] is not None
        ])
        if not history.empty:
            st.line_chart(history.set_index("data"))
        rows_panel(run)
    else:
        st.info("Execute uma suíte em Evaluation Studio para gerar indicadores.")

elif page == "Banking FAQ Playground":
    st.subheader("Perguntas bancárias")
    options = {f'{c["id"]} | {c["question"]}': c for c in dataset["cases"]}
    selection = st.selectbox("Caso de referência", ["Pergunta livre"] + list(options))
    case = options.get(selection)
    question = st.text_input(
        "Pergunta", value=case["question"] if case else "Como faço para bloquear cartão?"
    )
    if case and question != case["question"]:
        st.info("Pergunta alterada: avaliação livre, sem acesso ao gabarito do caso selecionado.")
        case = None
    if st.button("Gerar resposta", type="primary"):
        try:
            answer, citations, elapsed, inp, out = ask(
                question, policies["policies"], provider, model, url, case
            )
            st.markdown("#### Resposta")
            st.write(answer)
            st.caption(
                f'Fontes geradas/selecionadas: {", ".join(citations) if citations else "nenhuma"} '
                f'| Latência observada {elapsed:.2f} ms | Tokens: {inp} entrada, {out} saída'
            )
            if case:
                st.json(evaluate(case, answer, citations, elapsed, inp, out, price_in, price_out))
            else:
                st.warning("Perguntas livres não têm referência validada e não recebem score.")
        except Exception as exc:
            st.error(str(exc))
    with st.expander("Políticas sintéticas e fontes"):
        st.dataframe(
            pd.DataFrame(policies["policies"])[["id", "category", "title", "source"]],
            hide_index=True, use_container_width=True,
        )

elif page == "Evaluation Studio":
    st.subheader("Evaluation Studio")
    categories = st.multiselect(
        "Categorias", ["answerable", "unanswerable", "adversarial", "ambiguous"],
        default=["answerable", "unanswerable", "adversarial", "ambiguous"],
    )
    selected = [c for c in dataset["cases"] if c["category"] in categories]
    st.caption(f"{len(selected)} casos selecionados. Cada execução registra versão, hashes e modo.")
    if st.button(
        "Run Full Evaluation" if len(selected) == 100 else "Run Selected Evaluation",
        type="primary", disabled=not selected,
    ):
        run = execute(selected)
        if run:
            st.session_state["latest"] = run
    if st.session_state.get("latest"):
        run = st.session_state["latest"]
        st.caption(run_label(run))
        if run.get("mode") == "deterministic_demo":
            st.warning("Demo: respostas obtidas do gabarito. Interprete os scores como testes do motor.")
        metrics_panel(run["metrics"])
        rows_panel(run)

elif page == "Regression Testing":
    st.subheader("Regressões e quality gates")
    current = [r for r in runs if r.get("dataset_version") == dataset_version]
    if len(current) < 2:
        st.info("Execute pelo menos duas suítes com o mesmo dataset para comparar resultados.")
    else:
        labels = {run_label(r): r for r in current}
        baseline = st.selectbox("Baseline", list(labels), index=1)
        candidate = st.selectbox("Candidata", list(labels), index=0)
        if st.button("Comparar execuções", type="primary"):
            try:
                if labels[baseline]["id"] == labels[candidate]["id"]:
                    st.warning("Selecione duas execuções distintas para uma comparação útil.")
                comparison = compare_runs(labels[baseline], labels[candidate])
                if comparison["baseline_only"] or comparison["candidate_only"]:
                    st.warning(
                        "As execuções têm coberturas diferentes. Os deltas usam apenas "
                        f'{comparison["common_cases"]} casos em comum; '
                        f'{comparison["baseline_only"]} exclusivos da baseline e '
                        f'{comparison["candidate_only"]} exclusivos da candidata.'
                    )
                st.metric("Novas regressões", len(comparison["regressions"]))
                st.metric("Regressões críticas", len(comparison["critical_regressions"]))
                st.json(comparison)
                if labels[candidate].get("mode") == "deterministic_demo":
                    thresholds = json.loads(
                        (ROOT / "config/quality_gates.json").read_text(encoding="utf-8")
                    )
                    st.markdown("#### Quality gates do pipeline demonstrativo")
                    st.json(evaluate_gates(labels[candidate], thresholds, labels[baseline]))
                else:
                    st.caption("Gates de qualidade para modelos reais exigem calibração por modelo.")
            except ValueError as exc:
                st.error(str(exc))

elif page == "Safety Lab":
    st.subheader("Ataques, recusas e falta de evidência")
    cases = [c for c in dataset["cases"] if c["category"] in ("adversarial", "unanswerable")]
    st.caption(f"{len(cases)} casos sintéticos de segurança e escopo.")
    selected = st.selectbox("Cenário", cases, format_func=lambda c: f'{c["id"]}: {c["question"]}')
    st.write("Critério de referência:", selected["expected_answer"])
    left, right = st.columns(2)
    if left.button("Run Selected Safety Case"):
        run = execute([selected])
        if run:
            st.session_state["safety"] = run
    if right.button("Run Safety Suite", type="primary"):
        run = execute(cases)
        if run:
            st.session_state["safety"] = run
    if st.session_state.get("safety"):
        metrics_panel(st.session_state["safety"]["metrics"])
        rows_panel(st.session_state["safety"])

elif page == "Reports & History":
    st.subheader("Histórico, exportação e importação")
    if os.environ.get("AI_LAB_ENABLE_IMPORT") == "1":
        uploaded = st.file_uploader("Importar relatório JSON exportado", type=["json"])
        if uploaded is not None and st.button("Importar relatório"):
            try:
                if uploaded.size > 3_000_000:
                    raise ValueError("Arquivo excede 3 MB")
                imported = validate_run(json.loads(uploaded.getvalue().decode("utf-8")))
                save_run(imported)
                st.success("Relatório importado. Recarregue a página para vê-lo no histórico.")
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                st.error(f"Arquivo inválido: {exc}")
    else:
        st.caption("Importação desabilitada na hospedagem pública. Para habilitar localmente: AI_LAB_ENABLE_IMPORT=1.")
    if not runs:
        st.info("Nenhuma execução registrada.")
    else:
        st.dataframe(
            pd.DataFrame([
                {
                    "id": r["id"], "data": r["created_at"],
                    "modo": r.get("mode"), "dataset": r["dataset_version"],
                    "modelo": r.get("model"), "casos": r["metrics"]["n"],
                    "aprovação": r["metrics"]["pass_rate"],
                } for r in runs
            ]), hide_index=True, use_container_width=True,
        )
        run = st.selectbox("Execução", runs, format_func=run_label)
        metrics_panel(run["metrics"])
        st.caption(
            "Baixe os arquivos para preservá-los. O SQLite da hospedagem gratuita pode ser reiniciado."
        )
        st.download_button(
            "Export JSON", json.dumps(run, ensure_ascii=False, indent=2),
            file_name=f'{run["id"]}.json', mime="application/json",
        )
        st.download_button(
            "Export CSV", pd.DataFrame(run["cases"]).to_csv(index=False),
            file_name=f'{run["id"]}.csv', mime="text/csv",
        )
        rows_panel(run)

st.divider()
st.caption(
    "Avaliação heurística e reproduzível, com limites conhecidos. "
    "Dataset e banco fictícios. No modo demo, a resposta conhece o gabarito. "
    "Histórico SQLite na hospedagem gratuita pode ser perdido após reinicialização. "
    "Exporte os relatórios para preservá-los."
)
