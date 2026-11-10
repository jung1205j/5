"""Tests for Nov 10 engine v6 output schema and UI-only fallbacks."""
import json
from pathlib import Path
import pytest
from frontend.v6_display import (
    DAYS, V6_KEYS, series_for_regions, channel_total_frame, visits_range,
    assumptions_frame, open_scenario, load_results_without_links,
    ad_costs_frame, notes_payload,
)
from frontend.final_features import hubs_frame


def test_three_regions_overlay_weekly():
    rows = series_for_regions([
        {'dong':'서교동','weekly_visitors':[54,129,220]},
        {'dong':'망원1동','weekly_visitors':[43,82,136]},
        {'dong':'연남동','weekly_visitors':[28,78,127]},
    ])
    assert len(rows) == 9
    assert rows['dong'].unique().tolist() == ['서교동','망원1동','연남동']
    assert rows[rows.dong == '서교동'].visitors.tolist() == [54,129,220]


def test_null_does_not_create_projections():
    assert series_for_regions([{'dong':'망원1동','weekly_visitors': None}]).empty
    assert channel_total_frame({'channel_total':None}).empty
    assert assumptions_frame({'assumptions':None}).empty
    assert visits_range({'visitors_range':None}) is None


def test_channel_total_percent_distinct_from_group_share():
    table = channel_total_frame({'channel_total':{'동네':.42,'검색':.30,'인스타':.28}})
    assert table.percent.tolist() == [42.0,30.0,28.0]


def test_range_and_assumptions():
    obj={'visitors_range':[60,66], 'assumptions':{'rent':None,'avg_price':9099}}
    assert visits_range(obj) == (60,66)
    assert assumptions_frame(obj).loc[0,'value'] == '입력되지 않음'
    assert visits_range({'visitors_range':[66,60]}) is None


def test_open_scenario_matches_engine_schema():
    obj=open_scenario(idea='카페',codes=['1144066000'],
                      open_hours=(10,22),open_days=['월','화','토'],
                      rent=3000000,avg_price=9000,budget=1000000)
    assert obj['open_hours']==[10,22]
    assert obj['open_days']==['월','화','토']
    assert obj['rent']==3000000 and obj['avg_price']==9000
    assert 'budget' not in obj and 'business_hours' not in obj
    assert len(DAYS)==7
    with pytest.raises(ValueError):
        open_scenario(idea='',codes=[],open_hours=(22,2),open_days=['월'],
                      rent=None,avg_price=None,budget=None)
    with pytest.raises(ValueError):
        open_scenario(idea='',codes=[],open_hours=(10,22),open_days=[],
                      rent=None,avg_price=None,budget=None)


def test_hubs_include_all_v6_metadata():
    hubs = hubs_frame({'hubs':[{'id':15902,'group':'40대_직장인','dong':'염리동',
                                   'reach':9,'direct':4,'week':2,
                                   'community':['맘카페','당근','인스타']}]})
    assert hubs.iloc[0]['direct'] == 4
    assert hubs.iloc[0]['week'] == 2
    assert hubs.iloc[0]['community'] == ['맘카페','당근','인스타']


def test_load_result_only_does_not_invent_persona_links(tmp_path):
    file=tmp_path/'result_1144066000.json'
    file.write_text(json.dumps({'dong_code':'1144066000','dong':'서교동',
                                'steps':[[1,2]],'visitors':62,'weekly_visitors':[20]}),encoding='utf-8')
    rows=load_results_without_links(tmp_path)
    assert rows[0]['weekly_visitors']==[20]
    assert rows[0]['steps']==[[1,2]]


def test_ad_costs_nullable_and_notes(tmp_path):
    (tmp_path/'ad_costs.json').write_text(json.dumps([
        {'channel':'당근','tier':'클릭 1회','unit':'클릭', 'cost_per_unit':300,
         'cost_min':100,'cost_max':500,'is_estimated':False,'default':True},
        {'channel':'오픈이벤트', 'cost_per_unit':None, 'is_estimated':True}]),encoding='utf-8')
    frame=ad_costs_frame(tmp_path)
    assert len(frame)==2
    assert frame.iloc[0]['기준 단가(원)']==300
    assert frame.iloc[1]['기준 단가(원)']!=frame.iloc[1]['기준 단가(원)'] # NaN
    meta=notes_payload(idea='카페',codes=['123'],budget=1000,target='학생',price_band='5000')
    assert 'open_hours' not in meta


def test_required_fields_all_supported_by_ui_read_only():
    expected={'monthly_customers','channel_total','visitors_range','assumptions','open_hours','open_days'}
    assert expected.issubset(V6_KEYS)
    s=Path(__file__).resolve().parents[2].joinpath('app.py').read_text(encoding='utf-8')
    for keyword in ['series_for_regions(', 'channel_total_frame(', 'open_scenario(', 'visits_range(', 'assumptions_frame(']:
        assert keyword in s
