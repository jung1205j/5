"""Strictly UI-only demonstration data; NEVER persist or merge into model files."""
from __future__ import annotations


def preview_only_keys() -> set[str]:
    return {
        'visitors_demand', 'competition_factor', 'daytime_share',
        'weekly_visitors', 'breakeven_week', 'repromo', 'channel_share',
        'scenarios', 'budget_plan', 'hubs', 'diagnosis',
    }


def preview_fields() -> dict:
    """Example values for visual inspection, not a prediction or user record."""
    original = [5, 8, 13, 18, 23, 25, 24, 22, 20, 18, 16, 15]
    return {
        'visitors_demand': 58,
        'competition_factor': 0.83,
        'daytime_share': .47,
        'weekly_visitors': original,
        'breakeven_week': 10,
        'repromo': {
            'week': 7,
            'without': original,
            'with': [5, 8, 13, 18, 23, 25, 28, 32, 35, 36, 35, 33],
        },
        'channel_share': {
            '20대이하_학생': {'인스타': .46, '검색': .27, '지인': .17, '동네': .10},
            '30대_직장인': {'인스타': .25, '검색': .40, '지인': .25, '동네': .10},
            '40대_주부': {'맘카페': .40, '검색': .30, '지인': .20, '동네': .10},
        },
        'scenarios': [
            {'name': '인스타 광고', 'cost': 400000, 'visitors_gain': 18},
            {'name': '체험단', 'cost': 600000, 'visitors_gain': 23},
            {'name': '당근 동네 광고', 'cost': 300000, 'visitors_gain': 12},
            {'name': '오픈 할인', 'cost': 200000, 'visitors_gain': 9},
        ],
        'budget_plan': {
            'budget': 1000000,
            'split': {'인스타': 400000, '체험단': 600000},
            'visitors_gain': 41,
        },
        'hubs': [
            {'id': 'PREVIEW-001', 'group': '30대_주부', 'dong': '망원1동', 'reach': 14},
            {'id': 'PREVIEW-002', 'group': '20대이하_학생', 'dong': '서교동', 'reach': 11},
            {'id': 'PREVIEW-003', 'group': '30대_직장인', 'dong': '연남동', 'reach': 8},
        ],
    }
