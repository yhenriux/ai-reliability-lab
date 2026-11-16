"""Six-module Streamlit interface for the Aurora Bank evaluation laboratory."""
import json
import os

import altair as alt
import pandas as pd
import streamlit as st

from reports import export_cases_csv

from engine import (
    DB, ROOT, ask, compare_runs, evaluate, evaluate_gates, execute_suite,
    list_runs, load_data, save_run, validate_run,
)

st.set_page_config(page_title="AI Reliability Lab", page_icon="🧪", layout="wide")
st.title("AI Reliability Lab")
st.caption("Laboratório de avaliação de IA · Aurora Bank fictício")

TASKS = (
    "Ver resultados", "Testar uma pergunta", "Executar avaliação",
    "Comparar execuções", "Testar segurança", "Consultar histórico e exportar",
)
RESULTS, QUESTION, EVALUATION, COMPARISON, SAFETY, HISTORY = TASKS
MODE_LABELS = {"deterministic_demo": "Demo", "real_local_llm": "Execução real"}

# Preserve execution preferences while visiting pages that hide these widgets.
for key in ("dataset_version", "provider", "model", "price_in", "price_out"):
    if key in st.session_state:
        st.session_state[key] = st.session_state[key]

with st.sidebar:
    page = st.radio("O que você quer fazer?", TASKS, key="task")
    dataset_version = st.session_state.get("dataset_version", "2.0")
    if page != HISTORY:
        dataset_version = st.selectbox(
            "Versão do conjunto de testes", ["2.0", "1.0"], key="dataset_version",
        )

    if page in (QUESTION, EVALUATION, SAFETY):
        local_ollama_enabled = os.environ.get("AI_LAB_ENABLE_OLLAMA") == "1"
        with st.expander("Configuração da execução"):
            provider = st.selectbox(
                "Provedor", ["demo", "ollama"] if local_ollama_enabled else ["demo"],
                format_func=lambda value: {"demo": "Demo", "ollama": "Ollama"}[value],
                key="provider",
            )
            model = "deterministic-baseline-v1"
            price_in = price_out = 0.0
            if provider == "ollama":
                model = st.text_input("Modelo Ollama", "qwen3:4b", key="model")
                price_in = st.number_input("US$/1 milhão de tokens de entrada", min_value=0.0, key="price_in")
                price_out = st.number_input("US$/1 milhão de tokens de saída", min_value=0.0, key="price_out")
            elif not local_ollama_enabled:
                st.caption("Para habilitar o Ollama localmente, use AI_LAB_ENABLE_OLLAMA=1.")
        url = os.environ.get("AI_LAB_OLLAMA_URL", "http://127.0.0.1:11434")
        st.caption(f'Próximo teste · {"Demo" if provider == "demo" else model}')

policies, dataset = load_data(dataset_version)
# Versioned, independently observed model runs are available even if free hosting resets SQLite.
bundled_runs = [
    validate_run(json.loads(path.read_text(encoding="utf-8")))
    for path in sorted((ROOT / "data").glob("real_*.json"))
]
runs = sorted(
    {r["id"]: r for r in list_runs() + bundled_runs}.values(),
    key=lambda r: r["created_at"], reverse=True,
)


def percentage(value):
    return "N/D" if value is None else f"{value * 100:.1f}%"


def mode_label(run):
    mode = run.get("mode")
    return MODE_LABELS.get(mode, mode or "Modo desconhecido")


def run_date(run):
    date = pd.to_datetime(run["created_at"], utc=True, errors="coerce")
    return "Data indisponível" if pd.isna(date) else date.strftime("%d/%m/%Y %H:%M UTC")


def run_context(run):
    st.caption(
        f'{mode_label(run)} · {run.get("model", "?")} · Versão {run["dataset_version"]} · '
        f'{run["metrics"]["n"]} casos · {run_date(run)}'
    )
    if run.get("mode") == "deterministic_demo":
        st.info("O modo Demo usa o gabarito. Esses indicadores verificam o motor de avaliação.")


def metrics_panel(m):
    approval, critical, latency = st.columns(3)
    approval.metric("Aprovação", percentage(m["pass_rate"]))
    if m["pass_rate"] is not None:
        approval.caption(f'{m["n"] - m["failures"]} de {m["n"]} casos aprovados')
    critical.metric("Falhas críticas", m.get("critical_failures", "N/D"))
    p95 = m["latency_p95_ms"]
    latency.metric(
        "Latência p95", "N/D" if p95 is None else (
            f"{p95 / 1000:.1f} s" if p95 >= 1000 else f"{p95:.1f} ms"
        ),
    )
    with st.expander("Detalhes da execução"):
        details = {
            "Casos": m["n"],
            "Falhas": m["failures"],
            "Bloqueio adversarial": percentage(m["safety_block_rate"]),
            "Qualidade heurística": percentage(m.get("quality_pass_rate")),
            "Correspondência de citações": percentage(m.get("source_adherence")),
            "Sobreposição com evidência": percentage(m.get("grounding_overlap_mean")),
            "Padrões sensíveis": m.get("risk_flags", "N/D"),
            "Custo de API estimado": f'US$ {m["estimated_cost_usd"]:.6f}',
        }
        for label, value in details.items():
            st.write(f"**{label}** · {value}")
        st.caption("O custo usa preços configurados manualmente e exclui infraestrutura.")


def rows_panel(run):
    df = pd.DataFrame(run["cases"])
    st.subheader("Investigar casos")
    if df.empty:
        st.info("Execução sem casos.")
        return
    selection = st.radio("Resultado dos casos", ["Todos", "Com falha", "Aprovados"], horizontal=True)
    outcomes = {"Com falha": False, "Aprovados": True}
    if selection in outcomes:
        df = df[df["passed"] == outcomes[selection]]
    if df.empty:
        st.info("Nenhum caso corresponde ao filtro.")
        return
    columns = {
        "case_id": "Caso", "question": "Pergunta", "passed": "Resultado",
        "failure_reasons": "Motivo da falha",
    }
    summary = df.reindex(columns=list(columns)).rename(columns=columns)
    summary["Resultado"] = summary["Resultado"].map({True: "Aprovado", False: "Com falha"})
    st.dataframe(summary, hide_index=True, width="stretch")
    with st.expander("Respostas, referências e rastreabilidade"):
        st.dataframe(df, hide_index=True, width="stretch")


def history_panel(current):
    st.subheader("Evolução da aprovação")
    history = pd.DataFrame([
        {
            "data": pd.to_datetime(run["created_at"], utc=True, errors="coerce"),
            "data_utc": run_date(run),
            "aprovação": run["metrics"]["pass_rate"],
            "modo": mode_label(run),
        }
        for run in current if run["metrics"]["pass_rate"] is not None
    ])
    if not history.empty:
        history = history.dropna(subset=["data"])
    if history.empty:
        st.info("Nenhuma execução com aprovação disponível.")
    elif len(history) == 1:
        row = history.iloc[0]
        st.write(f'{row["data"]:%d/%m/%Y %H:%M} UTC · {row["modo"]} · {percentage(row["aprovação"])}')
    else:
        chart = alt.Chart(history).mark_line(point=True).encode(
            x=alt.X("data:T", title="Data (UTC)", scale=alt.Scale(type="utc"), axis=alt.Axis(format="%d/%m/%Y")),
            y=alt.Y("aprovação:Q", title="Aprovação", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
            color=alt.Color("modo:N", title="Modo"),
            tooltip=[
                alt.Tooltip("data_utc:N", title="Data"),
                alt.Tooltip("modo:N", title="Modo"),
                alt.Tooltip("aprovação:Q", title="Aprovação", format=".1%"),
            ],
        ).properties(height=220)
        st.altair_chart(chart, width="stretch")


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
    return f'{run_date(run)} · {mode_label(run)} · {run.get("model", "?")} · {run["metrics"]["n"]} casos · {run["id"][:8]}'


if page == RESULTS:
    st.subheader("Visão geral de confiabilidade")
    st.write(
        f'Dataset **{dataset["dataset_id"]} v{dataset["version"]}** '
        f'| {len(dataset["cases"])} cenários | {len(policies["policies"])} políticas fictícias'
    )
    current = [r for r in runs if r.get("dataset_version") == dataset_version]
    if current:
        preferred = next((i for i, r in enumerate(current) if r.get("mode") == "real_local_llm"), 0)
        run = st.selectbox("Execução em destaque", current, index=preferred, format_func=run_label)
        run_context(run)
        if run.get("mode") == "real_local_llm" and run["metrics"]["n"] < len(dataset["cases"]):
            st.info("Esta execução cobre parte do conjunto de testes. Os indicadores se referem aos casos executados.")
        if run.get("workflow_url"):
            st.markdown(f'[Ver execução verificável no GitHub Actions]({run["workflow_url"]})')
        metrics_panel(run["metrics"])
        rows_panel(run)
        history_panel(current)
    else:
        st.info("Abra Executar avaliação para gerar indicadores para esta versão.")

elif page == QUESTION:
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
            if provider == "demo":
                st.info("O modo Demo usa respostas de referência quando disponíveis.")
            if case:
                st.json(evaluate(case, answer, citations, elapsed, inp, out, price_in, price_out))
            else:
                st.warning("Perguntas livres não têm referência validada e não recebem score.")
        except Exception as exc:
            st.error(str(exc))
    with st.expander("Políticas sintéticas e fontes"):
        st.dataframe(
            pd.DataFrame(policies["policies"])[["id", "category", "title", "source"]],
            hide_index=True, width='stretch',
        )

elif page == EVALUATION:
    st.subheader("Executar avaliação")
    categories = st.multiselect(
        "Categorias", ["answerable", "unanswerable", "adversarial", "ambiguous"],
        format_func={"answerable": "Com resposta", "unanswerable": "Sem evidência",
                     "adversarial": "Adversarial", "ambiguous": "Ambígua"}.get,
        default=["answerable", "unanswerable", "adversarial", "ambiguous"],
    )
    selected = [c for c in dataset["cases"] if c["category"] in categories]
    st.caption(f"{len(selected)} casos selecionados. Cada execução registra versão, hashes e modo.")
    if st.button(
        "Executar avaliação completa" if len(selected) == len(dataset["cases"]) else "Executar casos selecionados",
        type="primary", disabled=not selected,
    ):
        run = execute(selected)
        if run:
            st.session_state["latest"] = run
    if st.session_state.get("latest"):
        run = st.session_state["latest"]
        run_context(run)
        metrics_panel(run["metrics"])
        rows_panel(run)

elif page == COMPARISON:
    st.subheader("Comparar execuções")
    current = [r for r in runs if r.get("dataset_version") == dataset_version]
    if len(current) < 2:
        st.info("Execute pelo menos duas suítes com o mesmo dataset para comparar resultados.")
    else:
        labels = {run_label(r): r for r in current}
        baseline = st.selectbox("Execução de referência", list(labels), index=1)
        candidate = st.selectbox("Execução candidata", list(labels), index=0)
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

elif page == SAFETY:
    st.subheader("Ataques, recusas e falta de evidência")
    cases = [c for c in dataset["cases"] if c["category"] in ("adversarial", "unanswerable")]
    st.caption(f"{len(cases)} casos sintéticos de segurança e escopo.")
    selected = st.selectbox("Cenário", cases, format_func=lambda c: f'{c["id"]}: {c["question"]}')
    st.write("Critério de referência:", selected["expected_answer"])
    left, right = st.columns(2)
    if left.button("Executar cenário selecionado"):
        run = execute([selected])
        if run:
            st.session_state["safety"] = run
    if right.button("Executar suíte de segurança", type="primary"):
        run = execute(cases)
        if run:
            st.session_state["safety"] = run
    if st.session_state.get("safety"):
        run = st.session_state["safety"]
        run_context(run)
        metrics_panel(run["metrics"])
        rows_panel(run)

elif page == HISTORY:
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
            ]), hide_index=True, width='stretch',
        )
        run = st.selectbox("Execução", runs, format_func=run_label)
        run_context(run)
        metrics_panel(run["metrics"])
        st.caption(
            "Baixe os arquivos para preservá-los. O SQLite da hospedagem gratuita pode ser reiniciado."
        )
        st.download_button(
            "Baixar JSON", json.dumps(run, ensure_ascii=False, indent=2),
            file_name=f'{run["id"]}.json', mime="application/json",
        )
        st.download_button(
            "Baixar CSV", export_cases_csv(run["cases"]),
            file_name=f'{run["id"]}.csv', mime="text/csv",
        )
        rows_panel(run)

st.divider()
st.caption(
    "Avaliação heurística e reproduzível, com limites conhecidos. "
    "Conjunto de testes e banco fictícios."
)
