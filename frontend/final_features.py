"""Display-only adapters for the Norunja final UI.

Never fabricate missing engine values or derive real-world forecasts from input
fields. All analytical numbers displayed by these functions are read from the
team's result JSON as supplied. Pure helpers can be tested without Streamlit.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd


def finite_number(value: Any) -> float | None:
    """Return a finite numeric value, excluding bool and missing values."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def raw_metric(result: Mapping[str, Any], name: str) -> str:
    """Show raw engine value, or clearly state it has not arrived."""
    number = finite_number(result.get(name))
    if number is None:
        return "자료 대기"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.4f}".rstrip("0").rstrip(".")


def weekly_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    """Keep exactly the weeks supplied; do not fill future weeks."""
    values = result.get("weekly_visitors")
    if not isinstance(values, list):
        return pd.DataFrame(columns=["week", "visitors"])
    rows = []
    for i, value in enumerate(values[:12], 1):
        num = finite_number(value)
        if num is not None and num >= 0:
            rows.append({"week": i, "visitors": num})
    return pd.DataFrame(rows, columns=["week", "visitors"])


def repromo_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    info = result.get("repromo")
    if not isinstance(info, dict):
        return pd.DataFrame(columns=["week", "with_promo", "without_promo"])
    with_data, without_data = info.get("with"), info.get("without")
    if not isinstance(with_data, list) or not isinstance(without_data, list):
        return pd.DataFrame(columns=["week", "with_promo", "without_promo"])
    rows = []
    for i in range(min(len(with_data), len(without_data), 12)):
        a, b = finite_number(with_data[i]), finite_number(without_data[i])
        if a is not None and b is not None and a >= 0 and b >= 0:
            rows.append({"week": i+1, "with_promo": a, "without_promo": b})
    return pd.DataFrame(rows, columns=["week", "with_promo", "without_promo"])


def channel_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    """Return group × channel percentages, preserving original ratios.

    Fractions outside [0,1] are excluded rather than scaled or normalized.
    """
    obj = result.get("channel_share")
    if not isinstance(obj, dict):
        return pd.DataFrame(columns=["group", "channel", "percent"])
    if obj and all(finite_number(x) is not None for x in obj.values()):
        obj = {"전체": obj}
    rows = []
    for group, entries in obj.items():
        if not isinstance(entries, dict):
            continue
        for channel, share in entries.items():
            number = finite_number(share)
            if number is not None and 0 <= number <= 1:
                rows.append({"group": str(group), "channel": str(channel), "percent": number * 100})
    return pd.DataFrame(rows, columns=["group", "channel", "percent"])


def scenarios_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    obj = result.get("scenarios")
    if not isinstance(obj, list):
        return pd.DataFrame(columns=["name", "cost", "visitors_gain"])
    rows = []
    for entry in obj:
        if not isinstance(entry, dict):
            continue
        cost = finite_number(entry.get("cost"))
        gain = finite_number(entry.get("visitors_gain"))
        if cost is not None and gain is not None and cost >= 0:
            rows.append({"name": str(entry.get("name", "이름 없음")), "cost": cost, "visitors_gain": gain})
    return pd.DataFrame(rows, columns=["name", "cost", "visitors_gain"])


def budget_split(result: Mapping[str, Any]) -> tuple[pd.DataFrame, dict]:
    obj = result.get("budget_plan")
    if not isinstance(obj, dict):
        return pd.DataFrame(columns=["channel", "amount"]), {}
    rows = []
    raw = obj.get("split")
    if isinstance(raw, dict):
        for channel, amount in raw.items():
            num = finite_number(amount)
            if num is not None and num >= 0:
                rows.append({"channel": str(channel), "amount": num})
    return pd.DataFrame(rows, columns=["channel", "amount"]), obj


def hubs_frame(result: Mapping[str, Any]) -> pd.DataFrame:
    obj = result.get("hubs")
    if not isinstance(obj, list):
        return pd.DataFrame(columns=["id", "group", "dong", "reach"])
    rows = []
    for hub in obj:
        if not isinstance(hub, dict):
            continue
        reach = finite_number(hub.get("reach"))
        rows.append({"id": str(hub.get("id", "-")), "group": str(hub.get("group", "미상")),
                     "dong": str(hub.get("dong", "미상")), "reach": reach})
    return pd.DataFrame(rows, columns=["id", "group", "dong", "reach"])


def scenario_payload(*, idea: str, selected: list[str], hours: dict | None,
                     rent: int | None, avg_price: int | None, budget: int | None) -> dict:
    """Create a file for human handoff; app does not execute the simulation.

    `business_hours` is a proposed frontend-only field pending team schema
    approval; existing agreed fields are otherwise unchanged.
    """
    return {"business_idea": idea, "candidate_dongs": list(selected),
            "rent": rent, "avg_price": avg_price, "budget": budget,
            "business_hours": hours}
