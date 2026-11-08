# 📖 Case técnico | AI Reliability Lab
### Como projetar um laboratório reproduzível para avaliar confiabilidade de LLMs em perguntas bancárias

[🏠 Início](../README.md) · [🏗️ Arquitetura](ARCHITECTURE.md) · [📏 Métricas](EVALUATION.md) · [📊 Resultados](RESULTS.md)

![Ilustração do laboratório: dados sintéticos, modelo e evidências](assets/pipeline.svg)

> **Resumo executivo:** desenvolvemos um laboratório público de avaliação de respostas bancárias, com **100 cenários sintéticos, 16 políticas, seis módulos de interface, testes automatizados e inferência real por Ollama**. O projeto transforma erros de modelos em evidências inspecionáveis, com relatórios por caso, métricas, regressões e documentação das limitações.

**[Abrir aplicação](https://ai-reliability-lab.streamlit.app/)** · **[Consultar código](https://github.com/yhenriux/ai-reliability-lab)** · **[Ver pipelines](https://github.com/yhenriux/ai-reliability-lab/actions)**

## 1. 🎯 Contexto e problema

Um chatbot bancário pode responder de maneira convincente e ainda assim informar um procedimento inexistente, deixar de citar a política, ignorar ausência de evidência ou atender a uma instrução maliciosa.

A engenharia de confiabilidade precisa tornar essas falhas **observáveis, comparáveis e reproduzíveis**. Para isso, criamos o Aurora Bank, instituição fictícia, e um conjunto controlado de políticas sobre Pix, cartões, contas, segurança, crédito, tarifas, atendimento e investimentos.

**Pergunta orientadora:** como avaliar sistematicamente a qualidade, a fundamentação, a segurança e a latência de um assistente com LLM, com infraestrutura acessível e critérios auditáveis?

## 2. 🧭 Objetivos e critérios de sucesso

| Objetivo | Implementação | Evidência |
|---|---|---|
| Avaliar respostas bancárias | Dataset v2.0 com 100 casos distintos | [Dataset](../data/golden_v2.json) |
| Rastrear respostas e fontes | JSON com respostas, citações e hashes | [Metodologia](EVALUATION.md) |
| Medir falhas de segurança | 20 cenários adversariais e 20 sem evidência | [Safety Lab](../app.py) |
| Identificar regressões | Comparador por caso + quality gates | [CI](../.github/workflows/ci.yml) |
| Validar interface e backend | Streamlit AppTest, pytest e QA | [Relatório de QA](UX_QA.md) |
| Observar modelo real | Ollama em CPU com relatório por caso | [Experimentos](RESULTS.md) |
| Permitir auditoria | README, Mermaid, SVG, artefatos e código aberto | [Arquitetura](ARCHITECTURE.md) |

## 3. 🏗️ Solução e arquitetura

```mermaid
flowchart LR
    A["📚 100 cenários<br/>16 políticas"] --> B["⚙️ Executor Python"]
    B --> C{"🧠 Provedor"}
    C --> D["Demo oráculo"]
    C --> E["Ollama Qwen3 4B"]
    D --> F["📏 Avaliador heurístico"]
    E --> F
    F --> G["📦 JSON e SQLite"]
    G --> H["🖥️ Streamlit"]
    F --> I["🧪 CI e regressões"]
```

**Stack:** Python, Streamlit, pandas, Ollama, Qwen3 4B, SQLite, pytest, Streamlit AppTest, GitHub Actions, Docker opcional, Mermaid e SVG.

A interface foi dividida em seis módulos, preservando a jornada de exploração, execução, análise, regressão, segurança e exportação. A implementação evita serviços pagos obrigatórios e facilita a reprodução local.

A arquitetura e seus trade-offs estão detalhados em [ARCHITECTURE.md](ARCHITECTURE.md).

## 4. 🧪 Metodologia

O dataset contém **48 casos respondíveis, 20 sem evidência, 20 adversariais e 12 ambíguos**. Os testes respondíveis fornecem a política correta ao modelo. Isso isola a geração condicionada à evidência e mantém a avaliação de recuperação fora do escopo inicial.

O motor combina Token-F1, cobertura de conceitos, sobreposição lexical com evidência, citações geradas pelo modelo, padrões de recusa, sinais sensíveis, latência e tokens. Cada falha preserva uma razão específica, como `citation_mismatch` ou `missing_required_concepts`.

### Exemplo de avaliação

**Pergunta:** “Como faço para bloquear meu cartão?”

**Política sintética:** `POL-005`, que descreve o procedimento autorizado no aplicativo.

**Resposta esperada:** orientação coerente com a política, incluindo a citação `[POL-005]`.

**Possíveis falhas:** afirmar que o bloqueio já foi executado, indicar uma etapa inexistente, citar uma política diferente ou omitir a fonte.

O avaliador registra a resposta integral, critérios e metadados. A [metodologia completa](EVALUATION.md) explica fórmulas, limiares e riscos de falsos positivos.

## 5. 📊 Evidências e resultados

| Experimento | Escopo | Evidência |
|---|---|---|
| Baseline determinístico | 100 casos, gabarito conhecido | CI e quality gates |
| SmolLM2 135M real | 8 casos, **0/8 aprovações heurísticas** | [JSON observado](../data/real_smoke_smollm2_135m.json) |
| Qwen3 4B real | 100 casos, execução integral em CPU | [Workflow e status](https://github.com/yhenriux/ai-reliability-lab/actions/workflows/full-model-benchmark.yml) |

No primeiro experimento real, o modelo de 135M parâmetros apresentou repetição de prompt e respostas irrelevantes. O resultado motivou a seleção do Qwen3 4B, modelo multilíngue de aproximadamente 2,5 GB quantizado, compatível com o runner CPU. A [análise da escolha](MODEL_SELECTION.md) documenta alternativas, critérios e restrições.

**O modo demo usa o gabarito** e sua aprovação não mede capacidade do modelo. Os resultados reais são reportados somente após conferência dos artefatos. Consulte [RESULTS.md](RESULTS.md) para valores verificados.

## 6. 🔍 Qualidade, UX e segurança

A implementação contempla testes unitários, integração dos seis módulos com Streamlit AppTest, verificação de regressões e publicação no Streamlit Cloud. O [relatório de QA](UX_QA.md) distingue evidência automatizada, validação do responsável e inspeções visuais ainda pendentes.

O sistema usa dados inteiramente fictícios, evita endpoints de inferência configuráveis por visitantes e desabilita importação de JSON na hospedagem pública. As verificações de segurança baseadas em expressões regulares têm cobertura parcial; o case documenta essa limitação.

## 7. ⚖️ Decisões e aprendizados

| Decisão | Justificativa | Trade-off |
|---|---|---|
| Streamlit em vez de front-end customizado | Velocidade de entrega e foco no motor | Menor controle de UX e responsividade |
| SQLite + exportação JSON | Simplicidade e auditabilidade | Histórico efêmero no deploy gratuito |
| Baseline determinístico | CI estável e reproduzível | Mede consistência do pipeline |
| LLM real em CPU | Sem custo de API e com logs verificáveis | Latência elevada e modelos menores |
| Métricas heurísticas | Interpretabilidade e baixo custo | Exigem calibração por revisão humana |
| Dataset sintético | Compartilhamento público seguro | Generalização para bancos reais não demonstrada |

### O que o case demonstra

**Engenharia:** implementação e teste de um motor de avaliação, integração de inferência, persistência, CI/CD, automação e artefatos reproduzíveis.

**Avaliação de IA:** desenho de casos adversariais, tratamento de ausência de evidência, grounding lexical, citação gerada, análise de regressões e interpretação crítica das métricas.

**Arquitetura:** decisões explícitas sobre custo, complexidade, segurança, observabilidade e separação entre harness e modelo.

## 8. 🗺️ Limitações e evolução

A [revisão humana independente de 20 respostas](HUMAN_REVIEW.md) permanece **PENDENTE**, com rubrica e critérios de aceite definidos. Também estão planejadas calibração de métricas, comparação entre modelos adicionais, auditoria de acessibilidade e eventual recuperação RAG.

O laboratório é um **case experimental de engenharia de confiabilidade**. As evidências apresentadas não equivalem a certificação de segurança bancária ou conformidade regulatória.

---

**Como avaliar este projeto:** execute a aplicação, examine [o dataset](../data/golden_v2.json), consulte [os resultados brutos](RESULTS.md), verifique [os testes](../tests) e reproduza o benchmark com as instruções de [MODEL_SELECTION.md](MODEL_SELECTION.md).
