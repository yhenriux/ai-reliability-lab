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
st.write("Uma demonstração pública de como avaliar assistentes de IA antes de confiar neles.")
st.caption(
    "Construído com tecnologias open source: Python, Streamlit, Ollama e Qwen. "
    "O Aurora Bank, suas regras e todas as perguntas são fictícios; nenhum dado de cliente é usado."
)

TASKS = (
    "Ver resultados", "Testar uma pergunta", "Executar avaliação",
    "Comparar execuções", "Testar segurança", "Consultar histórico e exportar",
)
RESULTS, QUESTION, EVALUATION, COMPARISON, SAFETY, HISTORY = TASKS
MODE_LABELS = {"deterministic_demo": "Demo", "real_local_llm": "Execução real"}
TASK_GUIDANCE = {
    RESULTS: {
        "title": "Ver resultados",
        "summary": "Veja como uma execução do assistente se saiu e abra os casos que precisam de atenção.",
        "value": "Apoia uma leitura executiva de qualidade, segurança e velocidade.",
        "proof": "Mostra que cada resposta pode ser medida, rastreada e investigada.",
        "limit": "Os percentuais valem para este conjunto de testes fictícios; não representam clientes reais.",
    },
    QUESTION: {
        "title": "Testar uma pergunta",
        "summary": "Acompanhe o caminho entre uma pergunta, a regra usada como fonte e a resposta produzida.",
        "value": "Ajuda a inspecionar uma resposta individual com suas evidências.",
        "proof": "Demonstra resposta fundamentada, citação de fonte e avaliação por caso.",
        "limit": "Na versão pública, o modo Demo usa a resposta esperada. Resultados de modelo real ficam em Ver resultados.",
    },
    EVALUATION: {
        "title": "Executar avaliação",
        "summary": "Rode vários casos fictícios com o mesmo critério e gere um resultado comparável.",
        "value": "Automatiza uma bateria de testes que seria lenta e inconsistente se feita manualmente.",
        "proof": "Demonstra repetição, versionamento e registro das evidências de cada execução.",
        "limit": "O modo Demo verifica o funcionamento do laboratório; ele não mede a qualidade de um modelo de IA.",
    },
    COMPARISON: {
        "title": "Comparar execuções",
        "summary": "Compare duas versões nos mesmos casos para encontrar melhorias e regressões.",
        "value": "Ajuda a decidir se uma nova versão está pronta para avançar.",
        "proof": "Mostra quais casos melhoraram, pioraram ou deixaram de ser cobertos.",
        "limit": "A comparação identifica diferenças; ela não explica sozinha o que causou cada mudança.",
    },
    SAFETY: {
        "title": "Testar segurança",
        "summary": "Verifique como o assistente reage a tentativas de manipulação e pedidos sem informação disponível.",
        "value": "Ajuda a encontrar respostas indevidas antes que o sistema chegue a pessoas reais.",
        "proof": "Demonstra testes repetíveis de recusa, escopo e uso de evidências.",
        "limit": "Os testes cobrem exemplos conhecidos e não certificam segurança completa nem conformidade regulatória.",
    },
    HISTORY: {
        "title": "Consultar histórico e exportar",
        "summary": "Consulte execuções anteriores e baixe as evidências para análise ou auditoria.",
        "value": "Preserva a rastreabilidade das decisões e facilita o compartilhamento dos resultados.",
        "proof": "Mostra versão, modelo, data, métricas e casos de cada execução registrada.",
        "limit": "O armazenamento da demonstração pública pode ser reiniciado; baixe os arquivos que deseja preservar.",
    },
}

FAILURE_LABELS = {
    "citation_mismatch": "A fonte citada não corresponde à esperada",
    "low_reference_overlap": "A resposta se afastou da resposta de referência",
    "low_evidence_overlap": "A resposta tem pouco apoio na regra fornecida",
    "missing_required_concepts": "Faltam informações obrigatórias",
    "missing_expected_refusal_or_clarification": "Faltou recusar ou pedir esclarecimento",
    "sensitive_pattern": "A resposta contém um padrão sensível",
}

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


def task_hero(task):
    guide = TASK_GUIDANCE[task]
    st.subheader(guide["title"], anchor=False)
    st.write(guide["summary"])
    with st.container(border=True):
        value, proof, limit = st.columns(3)
        value.caption("PARA QUE SERVE")
        value.write(guide["value"])
        proof.caption("O QUE ESTA TELA DEMONSTRA")
        proof.write(guide["proof"])
        limit.caption("LIMITE DESTA DEMONSTRAÇÃO")
        limit.write(guide["limit"])


def format_failure_reasons(reasons):
    if not reasons:
        return "—"
    if isinstance(reasons, str):
        reasons = [part.strip() for part in reasons.split(",") if part.strip()]
    return "; ".join(FAILURE_LABELS.get(reason, reason.replace("_", " ")) for reason in reasons)


def run_context(run):
    st.caption(
        f'{mode_label(run)} · {run.get("model", "?")} · Versão {run["dataset_version"]} · '
        f'{run["metrics"]["n"]} casos · {run_date(run)}'
    )
    if run.get("mode") == "deterministic_demo":
        st.info(
            "O modo Demo usa a resposta esperada de cada caso. Ele verifica se o laboratório calcula e "
            "registra os resultados corretamente; não representa o desempenho de um modelo de IA."
        )


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
            "Tentativas de manipulação bloqueadas": percentage(m["safety_block_rate"]),
            "Respostas que passaram nos critérios automáticos": percentage(m.get("quality_pass_rate")),
            "Fontes citadas corretamente": percentage(m.get("source_adherence")),
            "Apoio encontrado nas regras fornecidas": percentage(m.get("grounding_overlap_mean")),
            "Alertas de conteúdo sensível": m.get("risk_flags", "N/D"),
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
    summary["Motivo da falha"] = summary["Motivo da falha"].map(format_failure_reasons)
    st.dataframe(summary, hide_index=True, width="stretch")
    with st.expander("Ver respostas, fontes e dados técnicos"):
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


task_hero(page)


if page == RESULTS:
    st.write(
        f'Conjunto de testes **{dataset["dataset_id"]} v{dataset["version"]}** · '
        f'{len(dataset["cases"])} situações fictícias · {len(policies["policies"])} regras fictícias'
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
    options = {f'{c["id"]} | {c["question"]}': c for c in dataset["cases"]}
    selection = st.selectbox("Caso de referência", ["Pergunta livre"] + list(options))
    case = options.get(selection)
    question = st.text_input(
        "Pergunta", value=case["question"] if case else "Como faço para bloquear cartão?"
    )
    if case and question != case["question"]:
        st.info("A pergunta foi alterada. Ela será respondida livremente, sem comparação com a resposta esperada.")
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
                st.info("O modo Demo usa a resposta esperada quando um caso de referência é selecionado.")
            if case:
                with st.expander("Ver avaliação técnica deste caso"):
                    st.json(evaluate(case, answer, citations, elapsed, inp, out, price_in, price_out))
            else:
                st.warning("Perguntas livres não têm uma resposta esperada para comparação e, por isso, não recebem nota.")
        except Exception as exc:
            st.error(str(exc))
    with st.expander("Ver regras fictícias usadas como fonte"):
        st.dataframe(
            pd.DataFrame(policies["policies"])[["id", "category", "title", "source"]],
            hide_index=True, width='stretch',
        )

elif page == EVALUATION:
    categories = st.multiselect(
        "Categorias", ["answerable", "unanswerable", "adversarial", "ambiguous"],
        format_func={"answerable": "Com resposta", "unanswerable": "Sem evidência",
                     "adversarial": "Tentativa de manipulação", "ambiguous": "Pergunta ambígua"}.get,
        default=["answerable", "unanswerable", "adversarial", "ambiguous"],
    )
    selected = [c for c in dataset["cases"] if c["category"] in categories]
    st.caption(
        f"{len(selected)} casos selecionados. Cada execução registra a versão do teste, o modo usado "
        "e os dados necessários para repetir a análise."
    )
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
    current = [r for r in runs if r.get("dataset_version") == dataset_version]
    if len(current) < 2:
        st.info("Execute pelo menos duas suítes com o mesmo dataset para comparar resultados.")
    else:
        real_runs = [r for r in current if r.get("mode") == "real_local_llm"]
        comparable = real_runs if len(real_runs) >= 2 else current
        labels = {run_label(r): r for r in comparable}
        baseline = st.selectbox("Execução de referência", list(labels), index=1)
        candidate = st.selectbox("Execução candidata", list(labels), index=0)
        if st.button("Comparar execuções", type="primary"):
            try:
                if labels[baseline]["id"] == labels[candidate]["id"]:
                    st.warning("Selecione duas execuções distintas para uma comparação útil.")
                comparison = compare_runs(labels[baseline], labels[candidate])
                if labels[baseline].get("mode") != labels[candidate].get("mode"):
                    st.warning(
                        "As execuções usam modos diferentes. Leia o resultado como uma comparação técnica, "
                        "sem concluir que um modo é melhor que o outro."
                    )
                if comparison["baseline_only"] or comparison["candidate_only"]:
                    st.warning(
                        "As execuções têm coberturas diferentes. Os deltas usam apenas "
                        f'{comparison["common_cases"]} casos em comum; '
                        f'{comparison["baseline_only"]} exclusivos da baseline e '
                        f'{comparison["candidate_only"]} exclusivos da candidata.'
                    )
                regressions, critical, improvements, common = st.columns(4)
                regressions.metric("Casos que pioraram", len(comparison["regressions"]))
                critical.metric("Pioras críticas", len(comparison["critical_regressions"]))
                improvements.metric("Casos que melhoraram", len(comparison["improvements"]))
                common.metric("Casos comparados", comparison["common_cases"])
                with st.expander("Ver dados técnicos da comparação"):
                    st.json(comparison)
                if labels[candidate].get("mode") == "deterministic_demo":
                    thresholds = json.loads(
                        (ROOT / "config/quality_gates.json").read_text(encoding="utf-8")
                    )
                    with st.expander("Ver critérios automáticos do modo Demo"):
                        st.json(evaluate_gates(labels[candidate], thresholds, labels[baseline]))
                else:
                    st.caption("Os limites de aprovação automática para modelos reais precisam ser calibrados por modelo.")
            except ValueError as exc:
                st.error(str(exc))

elif page == SAFETY:
    cases = [c for c in dataset["cases"] if c["category"] in ("adversarial", "unanswerable")]
    st.caption(f"{len(cases)} situações fictícias de segurança e pedidos sem informação disponível.")
    selected = st.selectbox("Cenário", cases, format_func=lambda c: f'{c["id"]}: {c["question"]}')
    st.write("**Resposta esperada:**", selected["expected_answer"].replace("políticas fictícias", "regras fictícias"))
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
        st.caption(
            "Por segurança, a demonstração pública permite baixar relatórios, mas não receber arquivos. "
            "A instalação local pode habilitar a importação."
        )
    if not runs:
        st.info("Nenhuma execução registrada.")
    else:
        history = pd.DataFrame([
                {
                    "Execução": r["id"][:8], "Data": run_date(r),
                    "Modo": mode_label(r), "Versão do teste": r["dataset_version"],
                    "Modelo": r.get("model"), "Casos": r["metrics"]["n"],
                    "Aprovação": percentage(r["metrics"]["pass_rate"]),
                } for r in runs
            ])
        st.dataframe(history, hide_index=True, width='stretch')
        run = st.selectbox("Execução", runs, format_func=run_label)
        run_context(run)
        metrics_panel(run["metrics"])
        st.caption(
            "Baixe os arquivos que deseja preservar. O histórico temporário desta página pode ser reiniciado."
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
    "Projeto experimental e reproduzível, criado com tecnologias open source. "
    "Os testes automáticos apoiam a análise e não substituem revisão humana especializada."
)
