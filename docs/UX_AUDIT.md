# Auditoria de experiência para avaliadores

**Data:** 16/11/2026  
**Escopo:** seis tarefas da aplicação pública em desktop, com revisão de clareza, hierarquia, confiança, acessibilidade observável e interpretação dos resultados.

## Objetivo do usuário

Uma pessoa avaliadora deve entender, sem conhecimento prévio do projeto, o que o laboratório demonstra, como usar cada tarefa e quais conclusões os resultados permitem.

## Evidências observadas

1. **Ver resultados — atenção necessária.** Os indicadores eram visíveis, mas a tela não explicava o que a execução comprovava nem que os percentuais valiam apenas para casos fictícios.
2. **Testar uma pergunta — atenção necessária.** O fluxo era direto, porém “políticas sintéticas”, “gabarito” e o papel do modo Demo exigiam conhecimento técnico.
3. **Executar avaliação — atenção necessária.** Categorias e botão eram acessíveis, mas termos como “adversarial”, “hashes” e “modo” não explicavam o valor da tarefa.
4. **Comparar execuções — correção prioritária.** A seleção inicial comparava uma execução real com o modo Demo, embora os dois tenham objetivos diferentes.
5. **Testar segurança — atenção necessária.** A tela listava casos, mas não esclarecia que eles cobrem exemplos conhecidos e não certificam segurança completa.
6. **Consultar histórico e exportar — atenção necessária.** A tabela expunha nomes internos, datas técnicas e identificadores completos antes de explicar o propósito de auditoria e retenção.

## Melhorias implementadas

- Hero contextual em todas as tarefas com propósito, evidência demonstrada e limite de interpretação.
- Explicação permanente de que o projeto usa tecnologias open source e dados inteiramente fictícios.
- Tradução de termos técnicos e códigos de falha na visão executiva, preservando os dados originais em áreas expansíveis.
- Comparação inicial entre duas execuções reais quando ambas estão disponíveis.
- Histórico com data, modo, versão, modelo e aprovação em formato legível.
- Linguagem explícita sobre o modo Demo, retenção da hospedagem pública, revisão humana e limites de segurança.

## Acessibilidade observada

- A navegação tem rótulo e controles de seleção identificáveis por tecnologia assistiva.
- Títulos seguem uma hierarquia previsível e as tarefas funcionam por teclado.
- Os componentes nativos do Streamlit preservam foco, rótulos e reflow básico.
- A auditoria visual não comprova contraste em todos os estados, leitura completa por leitor de tela nem conformidade WCAG 2.2 AA. Esses itens exigem testes especializados adicionais.

## Critérios de aceite

- Cada tarefa explica o que faz, para que serve, o que demonstra e sua principal limitação.
- “Fictício” é explicado como proteção contra uso de dados reais e como base controlada para comparação.
- O modo Demo nunca é apresentado como prova da qualidade de um modelo.
- A visão principal evita códigos técnicos sem tradução.
- Comparações reais são priorizadas quando existem duas execuções de modelo disponíveis.
- Os fluxos, cálculos, arquivos exportados e resultados versionados permanecem compatíveis.

