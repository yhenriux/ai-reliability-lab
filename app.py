"""Streamlit interface for the AI Reliability Lab."""
import json
import pandas as pd
import streamlit as st
from engine import load_data,ask,evaluate,execute_suite,list_runs,compare_runs

st.set_page_config(page_title='AI Reliability Lab',page_icon='🧪',layout='wide')
policies,dataset=load_data()
st.title('AI Reliability Lab')
st.caption('Banking FAQ Reliability Engineering | Aurora Bank é um banco inteiramente fictício')
with st.sidebar:
    st.header('Configuração')
    provider=st.selectbox('Provider',['demo','ollama'])
    model='deterministic-baseline-v1' if provider=='demo' else st.text_input('Modelo local Ollama','llama3.2:1b')
    url='http://localhost:11434' if provider=='demo' else st.text_input('Ollama URL','http://localhost:11434')
    price_in=price_out=0.0
    if provider=='ollama':
        price_in=st.number_input('USD/1M tokens input',value=0.0,min_value=0.0)
        price_out=st.number_input('USD/1M tokens output',value=0.0,min_value=0.0)
    st.info('Demo = respostas determinísticas com acesso ao gabarito. Nenhum modelo de IA executado. Ollama = modelo local real.')
    if provider=='ollama':
        st.warning('Ollama precisa estar acessível a partir do servidor Streamlit. Em hospedagem pública, localhost não aponta para seu computador.')
    page=st.radio('Navegação',['Dashboard','Banking FAQ Playground','Evaluation Studio','Regression Testing','Safety Lab','Reports & History'])

def metrics_panel(m):
    a,b,c,d=st.columns(4)
    a.metric('Casos',m['n'])
    b.metric('Aprovação',f"{m['pass_rate']*100:.1f}%" if m['pass_rate'] is not None else 'N/D')
    c.metric('Bloqueio adversarial',f"{m['safety_block_rate']*100:.1f}%" if m['safety_block_rate'] is not None else 'N/D')
    d.metric('Latência p95 observada',f"{m['latency_p95_ms']:.3f} ms" if m['latency_p95_ms'] is not None else 'N/D')
    st.caption(f"Custo estimado USD {m['estimated_cost_usd']:.6f} | Falhas {m['failures']}")

def rows_panel(run):
    df=pd.DataFrame(run['cases'])
    st.dataframe(df[['case_id','category','question','passed','token_f1','source_ok','latency_ms']],use_container_width=True,hide_index=True)
    with st.expander('Detalhes de todas as respostas'):st.dataframe(df,use_container_width=True,hide_index=True)

def execute(cases):
    try:
        with st.spinner('Executando testes...'):
            return execute_suite(cases,provider,model,url,price_in,price_out)
    except Exception as exc:
        st.error(f'Falha da execução: {exc}')
        return None

runs=list_runs()
if page=='Dashboard':
    st.subheader('Indicadores de confiabilidade')
    st.write(f"Dataset {dataset['dataset_id']} v{dataset['version']} | {len(dataset['cases'])} cenários")
    if runs:
        st.caption(f"Execução mais recente: {runs[0]['created_at']} | {runs[0]['mode']}")
        metrics_panel(runs[0]['metrics'])
        history=pd.DataFrame([{'data':r['created_at'],'aprovação':r['metrics']['pass_rate']} for r in reversed(runs)])
        st.line_chart(history.set_index('data'))
        rows_panel(runs[0])
    else:st.info('Execute a primeira suíte em Evaluation Studio.')

elif page=='Banking FAQ Playground':
    st.subheader('Perguntas bancárias')
    options={f"{c['id']} | {c['question']}":c for c in dataset['cases']}
    selection=st.selectbox('Caso de referência',['Pergunta livre']+list(options))
    case=options.get(selection)
    question=st.text_input('Pergunta',value=case['question'] if case else 'Como faço para bloquear cartão?')
    if st.button('Gerar resposta',type='primary'):
        try:
            answer,citations,elapsed,in_tok,out_tok=ask(question,policies['policies'],provider,model,url,case)
            st.write('### Resposta');st.write(answer)
            st.caption(f"Fontes: {', '.join(citations) if citations else 'nenhuma'} | Latência {elapsed:.3f} ms | tokens input {in_tok}, output {out_tok}")
            if case:
                st.json(evaluate(case,answer,citations,elapsed,in_tok,out_tok,price_in,price_out))
            else:st.warning('Perguntas livres não têm referência validada: não recebem score de qualidade.')
        except Exception as exc:st.error(str(exc))
    with st.expander('Base de conhecimento fictícia'):
        st.dataframe(pd.DataFrame(policies['policies'])[['id','category','title','source']],hide_index=True,use_container_width=True)

elif page=='Evaluation Studio':
    st.subheader('Evaluation Studio')
    categories=st.multiselect('Categorias',['answerable','unanswerable','adversarial','ambiguous'],default=['answerable','unanswerable','adversarial','ambiguous'])
    selected=[c for c in dataset['cases'] if c['category'] in categories]
    st.caption(f'{len(selected)} casos selecionados.')
    if st.button('Run Full Evaluation' if len(selected)==100 else 'Run Selected Evaluation',disabled=not selected,type='primary'):
        run=execute(selected)
        if run:st.session_state['latest']=run
    if st.session_state.get('latest'):
        run=st.session_state['latest']
        st.caption(f"{run['created_at']} | {run['mode']}")
        metrics_panel(run['metrics']);rows_panel(run)

elif page=='Regression Testing':
    st.subheader('Comparação entre versões e regressões')
    if len(runs)<2:st.info('Execute duas suítes para comparar resultados.')
    else:
        labels={f"{r['created_at']} · {r['id'][:8]}":r for r in runs}
        old=st.selectbox('Execução baseline',list(labels),index=1)
        new=st.selectbox('Execução candidata',list(labels),index=0)
        if st.button('Comparar'):st.json(compare_runs(labels[old],labels[new]))

elif page=='Safety Lab':
    st.subheader('Ataques e recusas')
    cases=[c for c in dataset['cases'] if c['category'] in ('adversarial','unanswerable')]
    st.caption(f'{len(cases)} casos: prompt injection e falta de evidência.')
    selected=st.selectbox('Exemplo',cases,format_func=lambda c:f"{c['id']}: {c['question']}")
    st.write('Resposta esperada:',selected['expected_answer'])
    if st.button('Run Safety Suite',type='primary'):
        run=execute(cases)
        if run:st.session_state['safety']=run
    if st.session_state.get('safety'):
        metrics_panel(st.session_state['safety']['metrics']);rows_panel(st.session_state['safety'])

elif page=='Reports & History':
    st.subheader('Execuções registradas')
    if not runs:st.info('Nenhuma execução registrada.')
    else:
        st.dataframe(pd.DataFrame([{'id':r['id'],'date':r['created_at'],'mode':r['mode'],'cases':r['metrics']['n'],'pass_rate':r['metrics']['pass_rate']} for r in runs]),use_container_width=True,hide_index=True)
        run=st.selectbox('Execução',runs,format_func=lambda r:f"{r['created_at']} · {r['id'][:8]}")
        metrics_panel(run['metrics'])
        st.download_button('Export JSON',json.dumps(run,ensure_ascii=False,indent=2),file_name=f"{run['id']}.json",mime='application/json')
        st.download_button('Export CSV',pd.DataFrame(run['cases']).to_csv(index=False),file_name=f"{run['id']}.csv",mime='text/csv')

st.divider()
st.caption('Aviso: dados e políticas fictícios. O modo demo verifica a execução do pipeline, sem medir qualidade de LLM. Scores de correção e segurança são heurísticos. Histórico SQLite pode ser efêmero em hospedagem gratuita.')
