"""Read-only diagnostics for team data and public-data movement breakdowns."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def inspect_data_contract(folder: Path) -> list[str]:
    """Explain a format mismatch without changing any team data."""
    messages = []
    filepath = folder / 'personas.csv'
    if filepath.exists():
        try:
            df = pd.read_csv(filepath, usecols=['id', 'lat', 'lng'], dtype={'id':str}, encoding='utf-8-sig')
            numeric_id = pd.to_numeric(df['id'], errors='coerce')
            x = pd.to_numeric(df['lat'], errors='coerce')
            y = pd.to_numeric(df['lng'], errors='coerce')
            messages.append(f"personas.csv: {len(df):,}명, 정수 변환 불가 ID {numeric_id.isna().sum():,}개")
            messages.append(f"위치값 비정상: 위도 {x.isna().sum():,}개 / 경도 {y.isna().sum():,}개")
        except (ValueError, OSError, KeyError) as exc:
            messages.append(f"personas.csv 확인 중 오류: {exc}")
    else:
        messages.append('personas.csv 파일 없음')
    names = sorted(folder.glob('result_*.json'))
    if names:
        try:
            data = json.loads(names[0].read_text(encoding='utf-8-sig'))
            first = next((v for step in data.get('steps', []) for v in step), None)
            messages.append(f"{names[0].name}: steps의 시민 ID 예시 유형 {type(first).__name__}")
        except (ValueError, OSError) as exc:
            messages.append(f"시뮬레이션 결과 확인 중 오류: {exc}")
    else:
        messages.append('result_*.json 파일 없음')
    return messages


def inspect_dong_stats(folder: Path, dong_code: str) -> dict:
    path = folder / 'dong_stats.csv'
    if not path.exists():
        return {'warning': '선택한 데이터 소스에는 dong_stats.csv가 없습니다.'}
    try:
        df = pd.read_csv(path, encoding='utf-8-sig', dtype={'dong_code':str})
    except (ValueError, OSError) as exc:
        return {'warning': f'동별 통계 파일을 열 수 없습니다: {exc}'}
    row = df.loc[df['dong_code'] == str(dong_code)]
    if row.empty:
        return {'warning': '선택한 동에 해당하는 공공데이터가 없습니다.'}
    rec = row.iloc[0]
    periods = [('06~11시','flow_06_11'),('11~14시','flow_11_14'),
               ('14~17시','flow_14_17'),('17~21시','flow_17_21'),
               ('21~24시','flow_21_24')]
    ages = [('20대 이하','flow_age_20_under'),('30대','flow_age_30'),
            ('40대','flow_age_40'),('50대 이상','flow_age_50_over')]
    def get(key):
        value = pd.to_numeric(rec.get(key), errors='coerce')
        return float(value) if pd.notna(value) else None
    return {
        'estimated': str(rec.get('is_estimated', '0')).strip() in {'1','1.0','True','true'},
        'periods': [{'구간':label, '유동인구':get(col)} for label,col in periods if get(col) is not None],
        'ages': [{'연령대':label, '유동인구':get(col)} for label,col in ages if get(col) is not None],
        'weekday': get('flow_weekday'), 'weekend':get('flow_weekend'),
    }
