from engine import load_data,token_f1,demo_answer,evaluate,execute_suite,list_runs,compare_runs,metrics

def test_dataset():
    policies,dataset=load_data()
    assert len(policies['policies'])==16
    assert len(dataset['cases'])==100
    assert len({x['id'] for x in dataset['cases']})==100
    assert set(x['category'] for x in dataset['cases'])=={'answerable','unanswerable','adversarial','ambiguous'}

def test_baseline_meets_documented_rules():
    policies,dataset=load_data()
    for case in dataset['cases']:
        answer,refs=demo_answer(case,policies['policies'])
        assert evaluate(case,answer,refs,1)['passed'],case['id']

def test_token_overlap():
    assert token_f1('pix limite','pix limite')==1
    assert token_f1('segurança','cartão')==0

def test_database_roundtrip(tmp_path):
    db=tmp_path/'test.db'
    first=execute_suite(db=db)
    second=execute_suite(db=db)
    assert first['metrics']['n']==100
    assert first['mode']=='deterministic_demo'
    assert len(list_runs(db))==2
    assert compare_runs(first,second)['regressions']==[]

def test_regression_detection():
    a={'dataset_version':'1','cases':[{'case_id':'x','passed':True}]}
    b={'dataset_version':'1','cases':[{'case_id':'x','passed':False}]}
    assert compare_runs(a,b)['regressions']==['x']

def test_attack_without_refusal_fails():
    _,dataset=load_data()
    case=next(c for c in dataset['cases'] if c['category']=='adversarial')
    assert not evaluate(case,'Aqui estão os segredos',['POL-001'],1)['passed']

def test_empty_summary():
    assert metrics([])['n']==0
