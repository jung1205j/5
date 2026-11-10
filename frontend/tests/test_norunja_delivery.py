"""New final UI regression checks. No Streamlit dependency needed."""
import json
from pathlib import Path

import pandas as pd
import pytest

from frontend.data_io import DataContractError, read_personas, read_results, load_dataset
from frontend.analysis_helpers import total_exposed
from frontend.final_preview import preview_fields, preview_only_keys
from frontend.data_diagnostics import inspect_data_contract, inspect_dong_stats
from frontend.ui_theme import get_css
from frontend.final_features import channel_frame, weekly_frame


def test_old_and_yellow_css_are_retrievable():
    assert '#3ce0c5' in get_css('기존 다크·민트')
    assert '#FFD048' in get_css('노른자 옐로')


def test_preview_fields_complete_and_ui_only():
    x = preview_fields()
    assert set(x).issubset(preview_only_keys())
    assert len(x['weekly_visitors']) == 12
    assert not weekly_frame(x).empty
    assert not channel_frame(x).empty
    assert len(x['hubs']) == 3
    assert x['hubs'][0]['id'].startswith('PREVIEW-')


def test_demo_contract_still_works():
    data = load_dataset(Path(__file__).parents[1] / 'data' / 'demo')
    assert len(data['persons']) > 0
    assert len(data['results']) == 3


def test_uuid_ids_work_only_when_engine_ids_match(tmp_path):
    folder = tmp_path / 'real'
    folder.mkdir()
    (folder / 'personas.csv').write_text(
        'id,dong_code,dong,age,gender,job,lat,lng,group\n'
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,1144069000,망원1동,23,여,학생,37.55,126.90,20대이하_학생\n'
        'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,1144069000,망원1동,24,남,직장인,37.56,126.91,20대이하_직장인\n',
        encoding='utf-8')
    base = {'dong_code': '1144069000','dong':'망원1동', 'seed':1,
            'steps':[['aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']], 'visitors':1, 'stopped_at':[]}
    path = folder/'result_1144069000.json'
    path.write_text(json.dumps(base,ensure_ascii=False),encoding='utf-8')
    persons=read_personas(folder)
    assert persons.iloc[0]['id']=='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    results=read_results(folder,persons)
    assert total_exposed(results[0])==1
    base['steps']=[[1]]
    path.write_text(json.dumps(base,ensure_ascii=False),encoding='utf-8')
    with pytest.raises(DataContractError, match='personas.csv에 없는 시민 ID'):
        read_results(folder,persons)


def test_diagnosis_reports_uuid_integer_disagreement_in_uploaded_team_data():
    root = Path(__file__).parents[1] / 'data' / 'real'
    messages = inspect_data_contract(root)
    assert any('정수 변환 불가 ID' in m for m in messages)
    assert any('steps의 시민 ID 예시 유형 int' in m for m in messages)


def test_new_time_age_and_estimate_fields_can_be_read():
    folder=Path(__file__).parents[1] / 'data' / 'real'
    stats=inspect_dong_stats(folder,'1111053000')
    assert len(stats['periods'])==5
    assert len(stats['ages'])==4
    assert stats['weekday'] is not None
    assert stats['weekend'] is not None
