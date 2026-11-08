# Case técnico: AI Reliability Lab

**Domínio:** FAQ bancária sintética (Aurora Bank)  
**Aplicação:** https://ai-reliability-lab.streamlit.app/  
**Repositório:** https://github.com/yhenriux/ai-reliability-lab

## Problema

Assistentes bancários baseados em LLM podem apresentar respostas imprecisas, falta de evidência, recusas inadequadas, comportamentos inseguros e regressões entre versões. Para comparar mudanças, é necessário registrar entradas, evidências, saídas, critérios, configurações e resultados de forma reproduzível.

## Objetivo de engenharia

Criar um laboratório interativo que execute cenários bancários sintéticos, compare respostas, explicite as limitações das métricas e produza artefatos auditáveis, sem serviços pagos obrigatórios.

## Decisões e trade-offs

1. **Streamlit + Python:** implementação de seis fluxos com poucas dependências e publicação gratuita.
2. **SQLite + JSON:** histórico local simples e relatórios portáteis. Em hospedagem gratuita, o banco pode ser efêmero.
3. **Dataset versionado:** v1.0 preservado; v2.0 tem 100 perguntas distintas, com maior diversidade semântica e adversarial.
4. **Dois modos de execução:** demo determinístico, usado para testar o harness, e Ollama opcional, usado para inferência real.
5. **Heurísticas interpretáveis:** F1, cobertura de conceitos, sobreposição lexical com evidência, citações geradas e padrões de recusa. Nenhuma dessas medidas substitui avaliação humana de correção factual.
6. **Evidence oracle:** em casos respondíveis, a política correta é fornecida. O foco experimental é a resposta condicionada à evidência, enquanto recuperação de informação fica fora do escopo do MVP.
7. **CI com quality gates:** um baseline determinístico versionado identifica regressões críticas no pipeline. Os limites de modelos reais exigem calibração própria.

## Fluxo

```mermaid
flowchart LR
    A[Dataset v2 + políticas] --> B[Executor]
    B --> C{Provedor}
    C --> D[Demo oracle]
    C --> E[Ollama real]
    D --> F[Avaliador heurístico]
    E --> F
    F --> G[SQLite e JSON]
    G --> H[Dashboard e regressões]
    F --> I[Quality gates CI]
```

## Protocolo experimental

- Selecionar versão e conjunto de casos.
- Registrar modelo, modo, hashes de políticas/dataset, evidência e timestamp.
- Executar as mesmas perguntas com o mesmo conjunto de evidências.
- Armazenar resposta gerada, citações presentes no texto, tokens observados, latência e falhas.
- Calcular métricas e comparar execuções compatíveis.
- Exportar JSON e CSV; revisar manualmente respostas com falso positivo/falso negativo heurístico.

## Evidências e resultados

| Evidência | Situação |
|---|---|
| Dataset sintético v2.0, 100 casos | Implementado |
| Suite determinística com baseline e quality gates | Implementado; confirmar resultado no CI |
| Integração Streamlit por testes automatizados | Implementado; confirmar resultado no CI |
| Execução com Ollama SmolLM2 135M, 8 casos | **Concluída** em GitHub Actions; relatório JSON versionado |
| Experimento com dois modelos reais em 100 casos | Ainda não executado |
| Validação manual de qualidade factual | Ainda não realizada |
| Aplicação pública | Publicada; dashboard inclui relatório real versionado após deploy |

### Primeira inferência real observada (8 casos)

O workflow [Real local LLM smoke benchmark](https://github.com/yhenriux/ai-reliability-lab/actions/runs/42429513000) executou **SmolLM2 135M** em CPU via Ollama em 08/11/2026 (UTC). O relatório bruto está em [data/real_smoke_smollm2_135m.json](../data/real_smoke_smollm2_135m.json).

| Indicador observado | Resultado |
|---|---:|
| Casos avaliados | 8 (2 por categoria) |
| Aprovação heurística | 0/8 (0%) |
| Falhas críticas | 2 |
| Correspondência de citações nas perguntas respondíveis | 50% |
| Latência média | 1.053,829 ms |
| Latência p95 | 2.030,392 ms |
| Tokens | Registrados por caso no JSON |
| Preço de API configurado | US$ 0 (CPU do runner não contabilizada) |

**Diagnóstico:** o modelo de 135M parâmetros repetiu o prompt e gerou sequências irrelevantes, como "VERDE" repetido. A avaliação sinalizou falhas de recusa, citações e aderência à referência. A amostra de oito casos é deliberadamente pequena; estes valores descrevem apenas o experimento, sem generalização para os 100 cenários nem para modelos maiores. As métricas de sobreposição lexical também podem penalizar paráfrases corretas.

**Importante:** a aprovação do modo demo apenas comprova a consistência do pipeline com um gabarito conhecido. O relatório real contém as respostas geradas, metadados e limitações.

## Segurança e privacidade

Todos os conteúdos são sintéticos. A hospedagem pública mantém a inferência local desativada por padrão e impede a configuração de URLs de rede por visitantes. Importação de relatórios no banco compartilhado também é opt-in local. A aplicação não contém credenciais ou dados de clientes.

## Próximos experimentos

1. Avaliar dois modelos reais sob o mesmo conjunto de casos, com amostras suficientes para comparação.
2. Adicionar avaliação humana de factualidade e checagem semântica calibrada.
3. Avaliar recuperação de evidências separadamente do gerador, caso o escopo avance para RAG.
