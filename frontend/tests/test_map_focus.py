from pathlib import Path
import json, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from frontend.data_io import load_dataset
from frontend.animated_map import build_map_html

ROOT=Path(__file__).resolve().parents[1]

def test_each_candidate_has_own_coordinates_and_zoom():
    data=load_dataset(ROOT/'data'/'demo')
    df=data['persons']
    centers=[]
    for item in data['results']:
        group=df[df['dong_code']==str(item['dong_code'])]
        assert len(group)>0
        centers.append((round(float(group['lat'].mean()),4),round(float(group['lng'].mean()),4)))
        html=build_map_html(df,item,data['geo'],item['dong'])
        assert '\\"focus_mode\\":\\"selected\\"' in html or '"focus_mode":"selected"' in html
        assert 'selectedArea.pad' in html
        assert str(item['dong_code']) in html
    assert len(set(centers))==len(centers)


def test_can_switch_overview_mode():
    data=load_dataset(ROOT/'data'/'demo')
    item=data['results'][0]
    html=build_map_html(data['persons'],item,data['geo'],item['dong'],focus_mode='all')
    assert '"focus_mode":"all"' in html
