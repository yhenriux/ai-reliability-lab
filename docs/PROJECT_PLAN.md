# AI Reliability Lab: Plano de engenharia

## Objetivo
Laboratório interativo de confiabilidade de IA para FAQ de um banco fictício, Aurora Bank. Um visitante executa avaliações e inspeciona qualidade, evidências, recusas, ataques, latência e custos.

## Princípios
- FAQ, políticas e clientes sempre sintéticos; jamais representar a documentação como política bancária real.
- Execuções reais de modelo explicitamente identificadas. Modo demo determinístico acessível sem credenciais.
- Avaliação reproduzível por dataset, versão, provedor, configuração e timestamp.
- Modelos configuráveis. Nenhuma chave de API incluída no repositório.
- Todas as operações acessíveis pela interface; CLI e testes são complementares.

## Stack MVP
Python 3.12, Streamlit, SQLite, JSON, pytest, Plotly, GitHub Actions. Adaptadores para modo demo e provedores externos opcionais.

## Interface
1. Overview: KPIs e histórico por execução.
2. Banking FAQ Playground: pergunta, resposta, política e avaliação.
3. Evaluation Studio: escolher dataset/modelo, executar uma suíte, inspecionar cada caso.
4. Regression Lab: comparar execuções pelo mesmo dataset e identificar regressões.
5. Safety Lab: ataques e recusas, com relatório por caso.
6. Reports: histórico, exportar JSON e CSV.

## Dados
- FAQ de políticas sintéticas com ids e versões, cobrindo Pix, contas, cartões, crédito, tarifas, segurança, atendimento e investimentos.
- Dataset gold v1 com 100 casos: perguntas respondíveis, sem evidência, adversariais e ambíguas.
- Cada caso tem id, categoria, questão, resposta ou padrão esperado, fontes autorizadas e tags.
- Conjuntos de teste reservados para detectar overfitting nas regras de avaliação.

## Contratos
- Provider.generate(question, evidence, settings) -> resposta, tokens/uso, latência, modelo, erro.
- EvaluationCase e EvaluationRun tipados e versionados.
- Database persiste execução, configuração, versão do dataset, métricas por caso e resultados agregados.

## Avaliações
- Determinísticas: taxa de recusa adequada, referências esperadas, termos obrigatórios, proibição de dados fictícios sensíveis, tempo.
- Heurísticas: similaridade token-F1, cobertura de conceitos, fundamentação; indicar limitações no UI.
- Opcional: LLM-as-judge com rubrica e rastreabilidade, nunca misturado com métricas determinísticas.
- Custo: estimativa baseada em preço versionado/configurado; distinguir medido de estimado.
- Segurança: suíte explícita de prompt injection, divulgação indevida e uso sem evidência.
- Regressão: comparar runs compatíveis e destacar delta, falhas novas e críticas.

## Critérios de aceitação
- Streamlit abre localmente sem API keys e navega em todos os módulos.
- Usuário executa caso unitário e suíte completa e vê resultados persistidos.
- Pelo menos 100 casos versionados, com fontes claras.
- Histórico e comparação de duas execuções operacionais.
- Exportação CSV e JSON com metadados.
- Testes de métricas, fontes, segurança e persistência; CI verde.
- Medidas simuladas e reais rotuladas corretamente; nenhum score inventado.
- Documentação de instalação, limites e arquitetura; tela orienta execução.
- Nenhuma conexão ou política de banco real.

## Fases
F0: inicialização, plano, contrato de dados e UX (atual).
F1: dataset e motor determinístico, SQLite, testes.
F2: UI end-to-end com demo sem credenciais.
F3: adaptador de modelo real, métricas de uso, regressão e hardening.
F4: documentação, CI, screenshots e publicação como case.

## Fora do escopo inicial
Produção bancária real, integração com contas, acesso a PII real, autenticação multiusuário, Kubernetes, GraphRAG e fornecedores pagos obrigatórios.
