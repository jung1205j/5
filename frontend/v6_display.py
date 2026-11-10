"""Read-only adapters for the Nov 10 Team 05 engine v6 result contract.

Never infer missing predictions, rescale a model quantity, or connect
incompatible person IDs to a geographical animation.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

DAYS = ('월', '화', '수', '목', '금', '토', '일')
V6_KEYS = frozenset((
    'visitors_demand', 'competition_factor', 'daytime_share', 'visitors_range',
    'weekly_visitors', 'monthly_customers', 'breakeven_week', 'repromo',
    'channel_total', 'channel_share', 'hubs', 'assumptions',
    'open_hours', 'open_days', 'hours_factor', 'days_factor', 'weekend_share',
    'day_age_mix', 'weekly_visits_model', 'runs', 'population_in_radius',
    'is_estimated', 'scenarios', 'budget_plan', 'diagnosis',
))


def number(obj: Any) -> float | None:
    if obj is None or isinstance(obj, bool):
        return None
    try:
        v = float(obj)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def series_for_regions(items: list[dict]) -> pd.DataFrame:
    """One trace for each named neighborhood, only its supplied weeks."""
    rows = []
    for item in items:
        values = item.get('weekly_visitors')
        if not isinstance(values, list):
            continue
        for i, v in enumerate(values[:12], 1):
            n = number(v)
            if n is not None and n >= 0:
                rows.append({'week': i, 'dong': str(item.get('dong', '미상')), 'visitors': n})
    return pd.DataFrame(rows, columns=['week', 'dong', 'visitors'])


def channel_total_frame(result: dict) -> pd.DataFrame:
    source = result.get('channel_total')
    if not isinstance(source, dict):
        return pd.DataFrame(columns=['channel', 'percent'])
    rows = []
    for name, frac in source.items():
        n = number(frac)
        if n is not None and 0 <= n <= 1:
            rows.append({'channel': str(name), 'percent': round(n * 100, 1)})
    return pd.DataFrame(rows, columns=['channel', 'percent'])


def visits_range(result: dict) -> tuple[float, float] | None:
    pair = result.get('visitors_range')
    if not isinstance(pair, list) or len(pair) != 2:
        return None
    a, b = number(pair[0]), number(pair[1])
    if a is None or b is None or a < 0 or b < a:
        return None
    return a, b


def assumptions_frame(result: dict) -> pd.DataFrame:
    source = result.get('assumptions')
    if not isinstance(source, dict):
        return pd.DataFrame(columns=['key', 'value'])
    return pd.DataFrame([{'key': k, 'value': '입력되지 않음' if v is None else v}
                         for k, v in source.items()], columns=['key', 'value'])


def open_scenario(*, idea: str, codes: list[str], open_hours: tuple[int, int] | None,
                  open_days: list[str] | None, rent: int | None,
                  avg_price: int | None, budget: int | None) -> dict:
    """Engine-compatible subset is open_hours, open_days, avg_price, rent.

    The engine currently reads scenario.json; UI never runs it implicitly.
    Other inputs remain as metadata and do not change saved results.
    """
    if open_hours is not None:
        if len(open_hours) != 2 or any(not isinstance(x, int) for x in open_hours):
            raise ValueError('영업시간은 [시작시각, 종료시각] 정수 쌍이어야 합니다')
        if not (0 <= open_hours[0] < open_hours[1] <= 24):
            raise ValueError('종료 시간은 시작 시간보다 뒤여야 합니다 (자정 이후 영업은 현재 엔진 미지원)')
    if open_days is not None and (not open_days or any(d not in DAYS for d in open_days)):
        raise ValueError('영업 요일은 월~일 중 한 개 이상이어야 합니다')
    obj = {
        'open_hours': list(open_hours) if open_hours is not None else None,
        'open_days': list(open_days) if open_days is not None else None,
        'avg_price': avg_price,
        'rent': rent,
    }
    # The engine ignores these metadata fields. Keep them clearly separated.
    return obj


def notes_payload(*, idea: str, codes: list[str], budget: int | None, target: str,
                  price_band: str) -> dict:
    return {'business_idea': idea, 'candidate_dong_codes': list(codes),
            'budget': budget, 'target_customer': target, 'price_band': price_band,
            'note': '프론트엔드 입력 메모. 엔진 시나리오와 별개이며 자동 재계산되지 않습니다.'}


def load_results_without_links(folder: Path) -> list[dict]:
    """Display-only recovery when personas and steps IDs are incompatible.

    Do NOT use these results with the map: ID linking remains unverified.
    """
    rows = []
    for path in sorted(folder.glob('result_*.json')):
        try:
            item = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            continue
        if not isinstance(item, dict) or not {'dong_code', 'dong', 'steps', 'visitors'} <= item.keys():
            continue
        if str(item['dong_code']) != path.stem.removeprefix('result_'):
            continue
        rows.append(item)
    return rows


def ad_costs_frame(folder: Path) -> pd.DataFrame:
    path = folder / 'ad_costs.json'
    if not path.exists():
        return pd.DataFrame()
    try:
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError):
        return pd.DataFrame()
    if not isinstance(raw, list):
        return pd.DataFrame()
    rows = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rows.append({
            '채널': str(item.get('channel', '미상')),
            '상품·등급': str(item.get('tier') or ''),
            '단위': str(item.get('unit') or ''),
            '기준 단가(원)': number(item.get('cost_per_unit')),
            '최소(원)': number(item.get('cost_min')),
            '최대(원)': number(item.get('cost_max')),
            '추정 여부': bool(item.get('is_estimated', False)),
            '기본 상품': bool(item.get('default', False)),
            '설명': str(item.get('note') or ''),
        })
    return pd.DataFrame(rows)
