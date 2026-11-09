"""Pure display adapters for the Norunja final dashboard.

The UI reads supplied simulation JSON; it never invents predictions.
Missing final-stage fields remain missing until the engine supplies them.
"""
from __future__ import annotations

import math
from typing import Any, Mapping
import pandas as pd


def number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def metric(result: Mapping[str, Any], field: str) -> str:
    value = number(result.get(field))
    if value is None:
        return "자료 대기"
    if field == "daytime_share" and 0 <= value <= 1:
        return f"{value * 100:.1f}%"
    return f"{int(value):,}" if value.is_integer() else f"{value:,.4f}".rstrip("0").rstrip(".")


def weekly_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    values = result.get("weekly_visitors")
    if not isinstance(values, list):
        return pd.DataFrame(columns=["week", "visitors"])
    rows = []
    for i, value in enumerate(values[:12], 1):
        val = number(value)
        if val is not None and val >= 0:
            rows.append({"week": i, "visitors": val})
    return pd.DataFrame(rows, columns=["week", "visitors"])


def repromo_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    record = result.get("repromo")
    if not isinstance(record, dict):
        return pd.DataFrame(columns=["week", "with_promo", "without_promo"])
    yes, no = record.get("with"), record.get("without")
    if not isinstance(yes, list) or not isinstance(no, list):
        return pd.DataFrame(columns=["week", "with_promo", "without_promo"])
    rows = []
    for i, (y, n) in enumerate(zip(yes[:12], no[:12]), 1):
        a, b = number(y), number(n)
        if a is not None and b is not None and a >= 0 and b >= 0:
            rows.append({"week": i, "with_promo": a, "without_promo": b})
    return pd.DataFrame(rows, columns=["week", "with_promo", "without_promo"])


def channel_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    shares = result.get("channel_share")
    if not isinstance(shares, dict):
        return pd.DataFrame(columns=["group", "channel", "percent"])
    if shares and all(number(v) is not None for v in shares.values()):
        shares = {"전체": shares}
    rows = []
    for group, channels in shares.items():
        if isinstance(channels, dict):
            for channel, value in channels.items():
                ratio = number(value)
                if ratio is not None and 0 <= ratio <= 1:
                    rows.append({"group": str(group), "channel": str(channel), "percent": ratio * 100})
    return pd.DataFrame(rows, columns=["group", "channel", "percent"])


def scenarios_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    scenarios = result.get("scenarios")
    if not isinstance(scenarios, list):
        return pd.DataFrame(columns=["name", "cost", "visitors_gain"])
    rows = []
    for entry in scenarios:
        if not isinstance(entry, dict):
            continue
        cost, gain = number(entry.get("cost")), number(entry.get("visitors_gain"))
        if cost is not None and gain is not None and cost >= 0:
            rows.append({"name": str(entry.get("name", "미상")), "cost": cost, "visitors_gain": gain})
    return pd.DataFrame(rows, columns=["name", "cost", "visitors_gain"])


def budget_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    plan = result.get("budget_plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("split"), dict):
        return pd.DataFrame(columns=["channel", "amount"])
    rows = []
    for channel, value in plan["split"].items():
        amount = number(value)
        if amount is not None and amount >= 0:
            rows.append({"channel": str(channel), "amount": amount})
    return pd.DataFrame(rows, columns=["channel", "amount"])


def hubs_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    hubs = result.get("hubs")
    if not isinstance(hubs, list):
        return pd.DataFrame(columns=["id", "group", "dong", "reach"])
    rows = []
    for hub in hubs:
        if isinstance(hub, dict):
            rows.append({"id": str(hub.get("id", "-")), "group": str(hub.get("group", "미상")),
                         "dong": str(hub.get("dong", "미상")), "reach": number(hub.get("reach"))})
    return pd.DataFrame(rows, columns=["id", "group", "dong", "reach"])


def input_payload(*, idea: str, regions: list[str], business_hours: dict | None,
                  rent: int | None, avg_price: int | None, budget: int | None) -> dict:
    """Export inputs only; no server execution, and no modification of model results.

    business_hours is a *proposed* key pending the engine team's agreement.
    """
    return {"business_idea": idea, "candidate_dongs": list(regions),
            "rent": rent, "avg_price": avg_price, "budget": budget,
            "business_hours": business_hours}


def preview_fields() -> dict:
    """UI-only illustrative values, never written to exports or data files."""
    weekly = [7, 9, 12, 15, 17, 19, 18, 17, 16, 15, 14, 13]
    return {
        "visitors_demand": 42, "competition_factor": 0.82, "daytime_share": 0.47,
        "weekly_visitors": weekly, "breakeven_week": 9,
        "repromo": {"week": 7, "with": [7, 9, 12, 15, 17, 19, 22, 25, 27, 28, 26, 25], "without": weekly},
        "channel_share": {
            "20대이하_학생": {"인스타": .50, "검색": .25, "지인": .15, "동네": .10},
            "30대_직장인": {"인스타": .22, "검색": .41, "지인": .24, "동네": .13},
        },
        "scenarios": [
            {"name": "인스타 광고", "cost": 400000, "visitors_gain": 18},
            {"name": "체험단", "cost": 600000, "visitors_gain": 23},
        ],
        "budget_plan": {"budget": 1000000, "split": {"인스타": 400000, "체험단": 600000},
                        "visitors_gain": 41},
        "hubs": [
            {"id": "PREVIEW-01", "group": "30대_주부", "dong": "망원1동", "reach": 14},
            {"id": "PREVIEW-02", "group": "20대이하_학생", "dong": "서교동", "reach": 11},
        ],
    }
