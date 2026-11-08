# 🗺️ Roadmap e dívida técnica priorizada

[← Início](../README.md) · [📊 Resultados](RESULTS.md) · [👤 Revisão humana](HUMAN_REVIEW.md)

| Prioridade | Entrega | Estado | Evidência / critério de aceite |
|---|---|---|---|
| P0 | Dataset sintético versionado (100 casos) | ✅ Concluído | `data/golden_v2.json` |
| P0 | Harness determinístico e CI | ✅ Concluído | Testes pytest e quality gates |
| P0 | Inferência real inicial (135M, 8 casos) | ✅ Concluído | JSON versionado e GitHub Actions |
| P0 | Inferência real Qwen3 4B, 100 casos | ✅ Execução, verificação e versionamento concluídos | [Run 42430639080](https://github.com/yhenriux/ai-reliability-lab/actions/runs/42430639080): 100 IDs únicos, `real_local_llm`, `qwen3:4b`; 0% aprovação heurística. [JSON integral](../data/real_full_qwen3_4b_v2.json) e [planilha de revisão](../data/review_20_qwen3_4b_v2.csv) versionados |
| P0 | Revisão **humana independente** de 20 respostas | ⏳ Pendente | Rubrica preenchida, justificativas, matriz de concordância |
| P1 | Testes dos seis módulos e jornadas principais | ✅ Automatizados | Streamlit AppTest e testes do motor |
| P1 | Inspeção visual multi-dispositivo | ⏳ Pendente | Capturas e verificação de responsividade |
| P1 | Acessibilidade WCAG 2.2 AA | ⏳ Pendente | Checklist, teclado e leitor de tela |
| P1 | Quality gates calibrados para LLM real | ⏳ Pendente | Limiar justificado por revisão humana |
| P2 | Persistência em banco durável | 📌 Opcional | Somente se histórico multiusuário for requisito |
| P2 | Recuperação RAG e métricas de retrieval | 📌 Evolução | Dataset de recuperação e métricas específicas |
| P2 | Benchmark comparativo de segundo modelo real | 📌 Evolução | Mesmo conjunto de 100 casos e mesmo protocolo |

## Critérios de priorização

**P0:** evidências necessárias para sustentar afirmações sobre desempenho de modelos.  
**P1:** qualidade operacional, experiência e redução de ambiguidades de interpretação.  
**P2:** capacidade adicional que depende de uma necessidade validada.

### Resultado do benchmark integral

O Qwen3 4B foi executado em 100 casos reais, com média de 9,98 s por resposta e 0% de aprovação heurística. A próxima investigação deve inspecionar separação de raciocínio e resposta final, formatação de citações e prompts, preservando o artefato original e sem recalibrar métricas retrospectivamente. A Issue #9 continua aberta para revisão humana independente.

### Próxima decisão após o benchmark integral

1. Se o Qwen3 4B falhar de forma sistemática, inspecionar prompts e exemplos antes de trocar novamente de modelo.
2. Se a taxa heurística for alta, priorizar revisão qualitativa para identificar falsos positivos.
3. Se houver divergências relevantes, calibrar critérios, preservar resultados originais e versionar a nova metodologia.
4. Se o desempenho for suficiente para demonstração, publicar os limites junto aos indicadores, sem reivindicar conformidade bancária.

**Definição de pronto para publicação:** aplicação acessível, código e CI funcionais, pelo menos um experimento real com dados versionados, metodologia e limitações explícitas. **Definição de pronto para alegações robustas de confiabilidade:** amostra revisada por humanos, métricas calibradas e comparações reproduzíveis.
