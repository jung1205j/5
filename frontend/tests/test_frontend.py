from pathlib import Path
import json
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from frontend.data_io import load_dataset
from frontend.analysis_helpers import (summaries, scenario_options, exposure_by_step,
                              total_exposed, html_report, get_reason)
from frontend.animated_map import build_map_html

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'data' / 'demo'

def test_load_demo_and_summaries():
    data=load_dataset(DEMO)
    assert len(data['persons'])==150
    assert len(data['results'])==3
    df=summaries(data['results'],len(data['persons']))
    assert df['visitors'].tolist() == sorted(df['visitors'], reverse=True)
    assert df['exposed'].gt(0).all()
    assert df['exposure_ratio'].le(100).all()


def test_scenario_contract_and_delta():
    data=load_dataset(DEMO)
    options=scenario_options(DEMO,data['persons'])
    assert len(options)==1
    assert len(options[0]['results'])==3
    before={x['dong_code']:x for x in data['results']}
    for revised in options[0]['results']:
        baseline=before[revised['dong_code']]
        assert revised['visitors'] > baseline['visitors']
        assert total_exposed(revised) > total_exposed(baseline)


def test_map_is_safe_for_embedded_text():
    data=load_dataset(DEMO)
    results=data['results'][0].copy()
    persons=data['persons'].copy()
    persons.loc[0,'dong'] = "</script><img src=x onerror=alert(1)>"
    html=build_map_html(persons, results, data['geo'], '시연용')
    assert '<img src=x onerror=alert(1)>' not in html
    assert '\\u003c/script\\u003e' in html
    assert '__PAYLOAD__' not in html
    assert 'id="play"' in html and 'id="timeline"' in html


def test_curve_and_report():
    data=load_dataset(DEMO)
    r=data['results'][0]
    curve=exposure_by_step(r)
    assert curve[0]['exposed']==0
    assert curve[-1]['exposed']==total_exposed(r)
    page=html_report(data['results'],150,'<script>test</script>',True)
    assert b'<script>test</script>' not in page
    assert b'<!doctype html>' in page


def test_reaction_reasons():
    data=load_dataset(DEMO)
    group=data['reactions'][0]['group']
    reason=get_reason(group,data['reactions'])
    assert reason[0]
