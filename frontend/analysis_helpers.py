"""Pure read-only analytics for LocalSim UI (no new model predictions)."""
from __future__ import annotations
import html
import json
from pathlib import Path

import pandas as pd
from .data_io import exposed_until, read_results


def total_exposed(item: dict) -> int:
    return len({int(pid) for part in item.get("steps", []) for pid in part})


def exposure_by_step(item: dict) -> list[dict]:
    rows = [{"step": 0, "exposed": 0, "new": 0}]
    total = 0
    for i, part in enumerate(item.get("steps", []), 1):
        total += len(part)
        rows.append({"step": i, "exposed": total, "new": len(part)})
    return rows


def summaries(items: list[dict], population: int) -> pd.DataFrame:
    rows = []
    for r in items:
        exposed = total_exposed(r)
        rows.append({
            "dong_code": str(r["dong_code"]), "dong": r["dong"],
            "visitors": int(r["visitors"]), "exposed": exposed,
            "exposure_ratio": round(100 * exposed / max(1, population), 1),
            "steps": len(r["steps"]), "seed": r["seed"],
        })
    return pd.DataFrame(rows).sort_values("visitors", ascending=False).reset_index(drop=True)


def summary_export(items: list[dict], population: int) -> pd.DataFrame:
    df = summaries(items, population).rename(columns={
        "dong_code": "행정동 코드", "dong": "행정동", "visitors": "잠재 방문 고객(모델값)",
        "exposed": "도달 시민 수", "exposure_ratio": "도달 비율(%)",
        "steps": "확산 단계 수", "seed": "랜덤 시드",
    })
    return df


def get_reason(group: str, reactions: list[dict]) -> tuple[str, str]:
    for r in reactions:
        if str(r.get("group")) == str(group):
            return str(r.get("reason_type", "")), str(r.get("reason_text", ""))
    return "", ""


def scenario_options(folder: Path, persons: pd.DataFrame) -> list[dict]:
    """Optional precomputed revised scenario results; no automatic re-simulation."""
    root = folder / "scenarios"
    if not root.exists():
        return []
    items = []
    for subfolder in sorted(root.iterdir()):
        if not subfolder.is_dir() or not list(subfolder.glob("result_*.json")):
            continue
        info = {}
        meta = subfolder / "scenario.json"
        if meta.exists():
            try:
                info = json.loads(meta.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                info = {}
        try:
            data = read_results(subfolder, persons)
        except Exception as exc:
            items.append({"code": subfolder.name, "label": subfolder.name,
                          "error": str(exc), "results": []})
            continue
        items.append({"code": subfolder.name, "label": info.get("label", subfolder.name),
                      "idea": info.get("idea", ""), "note": info.get("note", ""), "results": data})
    return items


def html_report(items: list[dict], population: int, idea: str, is_demo: bool,
                scenario_label: str = "기준 시나리오") -> bytes:
    df = summary_export(items, population)
    headers = "".join(f"<th>{html.escape(str(col))}</th>" for col in df.columns)
    rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
                   for row in df.itertuples(index=False, name=None))
    note = "화면 시험을 위한 가상 데이터입니다. 실제 시장 예측이 아닙니다." if is_demo else "팀 확산 엔진 계산 결과입니다. 예측 정확도는 별도 검증이 필요합니다."
    content = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>LocalSim 결과 리포트</title>
<style>body{{font-family:'Malgun Gothic',sans-serif;color:#14314a;max-width:980px;margin:45px auto;line-height:1.65}}
h1{{font-size:32px;letter-spacing:-1px}}.label{{color:#147e76;font-weight:bold;letter-spacing:.1em}}
.alert{{background:#eaf7f5;border-left:4px solid #30b9a3;padding:14px;margin:18px 0}}
.tag{{padding:4px 9px;background:#f6eee1;border-radius:12px;font-size:12px}}table{{border-collapse:collapse;width:100%;margin-top:16px}}th,td{{text-align:left;border:1px solid #dae3eb;padding:12px}}th{{background:#edf4f7}}.sub{{color:#66798b}}
@media print{{body{{margin:20px}}}}</style></head><body>
<div class='label'>LOCALSIM • TEAM 05</div><h1>창업 후보 입지 분석 리포트</h1><p class='sub'>시나리오: {html.escape(scenario_label)}</p>
<h3>창업 아이디어</h3><p>{html.escape(idea)}</p><div class='alert'>{html.escape(note)}</div>
<h3>후보 동별 비교</h3><table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>
<p class='sub'>방문 가능 고객 수는 모델의 계산값이며 실제 방문객 수나 매출 예측을 의미하지 않습니다. 후보별 결과는 독립적인 시뮬레이션이며 합산하지 않습니다.</p>
<h3>정체 집단 · 경로</h3><ul>"""
    for r in items:
        stops = r.get("stopped_at", [])
        if stops:
            for s in stops[:4]:
                content += f"<li>{html.escape(r['dong'])} — {html.escape(str(s.get('group','미상')))} / {html.escape(str(s.get('path','미상')))}</li>"
        else:
            content += f"<li>{html.escape(r['dong'])} — 정체 기록 없음</li>"
    content += "</ul><p class='sub'>데이터 출처 및 검증 로그는 개발팀 원본 파일을 확인해 주세요.</p></body></html>"
    return content.encode("utf-8")
