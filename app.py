"""Norunja / Team 05 — frontend and visual-report deliverable.

The app DOES NOT itself perform Syntitan surveying, graph diffusion,
or real-customer prediction. It reads the team's fixed artifacts and makes
an honest, interactive map/reports experience.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from datetime import time

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

from frontend.data_io import DataContractError, exposed_until, load_dataset, read_personas, read_reactions
from frontend.v6_display import (DAYS, V6_KEYS, series_for_regions, channel_total_frame,
    visits_range, assumptions_frame, open_scenario, notes_payload,
    load_results_without_links, ad_costs_frame)
from frontend.animated_map import build_map_html
from frontend.ui_theme import get_css
from frontend.final_preview import preview_fields, preview_only_keys
from frontend.data_diagnostics import inspect_data_contract, inspect_dong_stats
from frontend.final_features import (raw_metric, weekly_frame, repromo_frame,
                                     channel_frame, scenarios_frame, budget_split,
                                     hubs_frame, scenario_payload, finite_number)
from frontend.analysis_helpers import (total_exposed, exposure_by_step, summaries,
                              summary_export, scenario_options, get_reason, html_report)

ROOT = Path(__file__).resolve().parent
st.set_page_config(
    page_title="노른자 · 입소문 상권 시뮬레이터",
    page_icon="🟡", layout="wide", initial_sidebar_state="expanded",
)

with st.sidebar:
    theme_choice = st.selectbox(
        "화면 디자인", ["노른자 크림(추천)", "노른자 옐로", "기존 다크·민트"],
        help="노른자 크림은 새 디자인입니다. 기존 다크·민트 및 노른자 옐로를 언제든 선택할 수 있고, 원본 코드는 frontend/design_backups 에 보관했습니다.",
    )
st.markdown(get_css(theme_choice), unsafe_allow_html=True)
cream_theme = theme_choice == "노른자 크림(추천)"
chart_ink = "#33404A" if cream_theme else "#DCE9F1"
chart_grid = "#EBE8E1" if cream_theme else "#29485D"
chart_alt = "#96A6B0" if cream_theme else "#7DAADA"


def safe(x: object) -> str:
    return html.escape(str(x), quote=True)


def heading(num: str, name: str, hint: str = "") -> None:
    st.markdown(f'<div class="ls-section"><span class="ls-number">{safe(num)}</span>{safe(name)}</div>', unsafe_allow_html=True)
    if hint:
        st.markdown(f'<div class="ls-copy">{safe(hint)}</div>', unsafe_allow_html=True)


def card(label: str, value: str, detail: str, *, best: bool = False) -> None:
    klass = "ls-card best" if best else "ls-card"
    st.markdown(f'<div class="{klass}"><div class="ls-kpi-label">{safe(label)}</div>'
                f'<div class="ls-kpi-value">{safe(value)}</div>'
                f'<div class="ls-kpi-detail">{safe(detail)}</div></div>', unsafe_allow_html=True)


def note(value: str, warning: bool = False):
    klass = "ls-note orange" if warning else "ls-note"
    st.markdown(f'<div class="{klass}">{safe(value)}</div>', unsafe_allow_html=True)


def map_fallback(persons: pd.DataFrame, geo: dict | None, item: dict, step: int = -1, view_mode: str = "selected") -> pdk.Deck:
    reached, latest = exposed_until(item["steps"], step)
    df = persons[["id", "lat", "lng", "dong", "group"]].copy()
    df["state"] = df["id"].map(lambda pid: "이번 단계" if pid in latest else "기존 노출" if pid in reached else "미노출")
    df["fill"] = df["id"].map(lambda pid: [255, 192, 120, 225] if pid in latest else [57, 223, 190, 217] if pid in reached else [123, 149, 178, 130])
    layers = []
    if geo:
        layers.append(pdk.Layer("GeoJsonLayer", data=geo, filled=True, stroked=True,
                                get_fill_color=[45, 150, 157, 25], get_line_color=[76, 176, 180, 195],
                                line_width_min_pixels=1.5, pickable=False))
    layers.append(pdk.Layer("ScatterplotLayer", data=df.to_dict("records"),
                            get_position="[lng, lat]", get_fill_color="fill", get_radius=37,
                            radius_min_pixels=2.8, radius_max_pixels=7, pickable=True))
    selected_people = persons[persons["dong_code"].astype(str) == str(item["dong_code"])]
    target = selected_people if view_mode == "selected" and not selected_people.empty else persons
    span = max(float(target["lat"].max()-target["lat"].min()), float(target["lng"].max()-target["lng"].min()))
    zoom = 14.5 if view_mode == "selected" and span < .025 else 13 if span < .05 else 11.4
    return pdk.Deck(layers=layers, map_style="https://tiles.openfreemap.org/styles/dark",
                    initial_view_state=pdk.ViewState(latitude=float(target["lat"].mean()),
                    longitude=float(target["lng"].mean()), zoom=zoom),
                    tooltip={"html":"<b>시민 {id}</b><br>{dong}<br>{group}<br>{state}",
                             "style":{"backgroundColor":"#0a2435","color":"#eefaff"}})


def curve_chart(item: dict) -> go.Figure:
    rows = exposure_by_step(item)
    xs = [x["step"] for x in rows]
    ys = [x["exposed"] for x in rows]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name="누적 도달",
                             line={"color": "#E4AF30" if cream_theme else "#FFD048", "width": 3, "shape": "spline"},
                             marker={"size": 8, "color": "#E4AF30" if cream_theme else "#FFD048"},
                             fill="tozeroy", fillcolor="rgba(60,224,197,.11)",
                             hovertemplate="%{x}단계 / 누적 %{y}명<extra></extra>"))
    fig.update_layout(height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin={"l": 8, "r": 12, "t": 12, "b": 20},
                      font={"color": chart_ink, "size": 12}, showlegend=False,
                      xaxis={"title": "확산 단계", "showgrid": False, "dtick": 1, "zeroline": False},
                      yaxis={"title": "고유 노출 시민 수", "gridcolor": chart_grid, "zeroline": False})
    return fig


# SIDE PANEL
with st.sidebar:
    st.markdown('<div class="ls-side-name">🟡 노른자 / Team 05</div>'
                '<div class="ls-side-sub">NORUNJA · LOCATION & WORD-OF-MOUTH LAB</div>',
                unsafe_allow_html=True)
    source = st.radio("데이터 소스", ["샘플 데이터", "팀 실데이터"], index=0,
                      help="팀 실데이터는 frontend/data/real 폴더에 PM과 B 담당 파일을 넣어야 활성화됩니다.")
    demo = source == "샘플 데이터"
    fallback_demo = False
    if not demo:
        fallback_demo = st.checkbox("실데이터가 오류여도 샘플 UI 표시", value=False,
                                    help="실데이터 결과를 대신 계산하지 않습니다. 화면만 샘플로 확인합니다.")
    preview_new_sections = st.checkbox("최종 기능 예시 차트 표시", value=False,
                                       disabled=not (demo or fallback_demo),
                                       help="12주 곡선·채널별 유입·홍보 비교·허브의 예시를 화면에서만 표시합니다. 원본 데이터와 다운로드 결과는 유지합니다.")
    supplied_result_files = st.file_uploader(
        "최신 엔진 v6 결과 JSON 임시 확인 (선택·복수)", type=["json"],
        accept_multiple_files=True,
        help="지역별 result_*.json 3개를 함께 선택해 새 결과 지표·곡선을 확인할 수 있습니다. 원본 지도/다운로드 결과는 바꾸지 않습니다.")
    folder = ROOT / "frontend" / "data" / ("demo" if demo else "real")
    if demo:
        st.warning("DEMO · 결과 수치·시민·경계는 시연을 위한 가상 데이터입니다.")
    else:
        st.info("TEAM DATA · 시뮬레이션 결과이며 실제 방문객 예측의 정확성을 보장하지 않습니다.")
    st.divider()
    st.markdown("**연동 상태**")
    file_names = [
        ("personas.csv", (folder / "personas.csv").exists()),
        ("result_*.json", bool(list(folder.glob("result_*.json")))),
        ("dongs.geojson", (folder / "dongs.geojson").exists()),
        ("reactions.json", (folder / "reactions.json").exists()),
        ("validation_log.json", (folder / "validation_log.json").exists()),
    ]
    st.markdown("".join(f'<div class="ls-file"><span class="ls-dot {"" if found else "missing"}"></span>{safe(n)}</div>' for n, found in file_names), unsafe_allow_html=True)
    st.divider()
    st.caption("파일을 추가하거나 변경했다면 앱을 새로고침하세요. 비밀키나 개인정보를 GitHub에 올리지 마세요.")

map_links_valid = True
try:
    dataset = load_dataset(folder)
except DataContractError as exc:
    st.error(f"실데이터 연결 검사: {exc}")
    map_links_valid = False
    if not demo:
        with st.expander("현재 실데이터 진단 보기", expanded=True):
            details = inspect_data_contract(folder)
            for message in details:
                st.write("• " + message)
        st.warning("기존 결과와 서울 전체 페르소나 ID를 임의로 연결하지 않습니다. 엔진에서 동일 ID 체계로 결과를 재생성해야 합니다.")
    if not demo and fallback_demo:
        folder = ROOT / "frontend" / "data" / "demo"
        dataset = load_dataset(folder)
        demo = True
        map_links_valid = True
        st.warning("⚠ 샘플 UI로 대체 표시 중입니다. 아래 지도·결과는 서울 실데이터가 아닌 데모입니다.")
    elif not demo:
        # Preserve read-only model result graphs without making up a map ID mapping.
        result_only = load_results_without_links(folder)
        if not result_only:
            st.info("실데이터 결과 파일이 없습니다. 왼쪽에서 샘플 데이터를 선택해 주세요.")
            st.stop()
        try:
            people_only = read_personas(folder)
        except DataContractError:
            people_only = pd.DataFrame(columns=["id","dong_code","lat","lng","dong","group"])
        try:
            reactions_only = read_reactions(folder, people_only)
        except DataContractError:
            reactions_only = []
        dataset = {"persons": people_only, "reactions": reactions_only, "results": result_only,
                   "geo": None, "validations": []}
        st.warning("확산 지도만 비활성화하고 엔진 결과의 분석 화면은 읽기 전용으로 표시합니다. 시민 ID 대응 관계가 검증되기 전에는 지도 점과 결과를 연결하지 않습니다.")
    else:
        st.stop()

people = dataset["persons"]
base_results = {str(x["dong_code"]): x for x in dataset["results"]}
dong_codes = list(base_results.keys())
scenarios = scenario_options(folder, people)

if cream_theme:
    st.markdown('''<div class="nj-hero">
      <div class="nj-hero-body">
        <div class="nj-hero-kicker">PICK THE RIGHT SPOT · LOCATION INTELLIGENCE</div>
        <h1>좋은 가게의 시작,<br>가능성이 모이는 자리를 찾다.</h1>
        <p>아이디어 한 줄에서 출발해 후보 지역의 입소문, 방문 수요,<br>
        홍보 전략까지 비교해 보세요.</p>
        <span class="nj-pill">✦ 후보 입지 비교</span>
        <span class="nj-pill">◎ 입소문 확산</span>
        <span class="nj-pill">▣ 홍보 전략</span>
      </div>
      <div class="nj-hero-egg" aria-hidden="true">
        <div class="nj-hero-ring"></div><div class="nj-hero-ring two"></div>
        <div class="nj-hero-yolk"></div>
      </div>
    </div>''', unsafe_allow_html=True)
else:
    st.markdown('<div class="ls-kicker">LOCATION INTELLIGENCE / WOM SIMULATION / 2026</div>'
                '<div class="ls-head"><div class="ls-mark">●</div><div class="ls-title">노른자</div></div>'
                '<div class="ls-sub">어디에 가게를 내고, 누구에게 먼저 알려야 할까? 동네별 입소문 흐름을 비교해 보세요.</div>'
                '<span class="ls-pill">TEAM 05 · 노른자 시뮬레이터</span>'
                + ('<span class="ls-pill warn">데모 / 가상 결과</span>' if demo else '<span class="ls-pill warn">팀 계산 결과 / 검증 별도</span>'),
                unsafe_allow_html=True)

heading("01", "어떤 가게를 생각하고 있나요?", "창업 아이디어와 비교 지역을 선택하세요. 현재 입력값은 이미 계산된 시뮬레이션을 재실행하지 않습니다.")
if cream_theme:
    primary_col, helper_col = st.columns([1.75, .85], gap="medium")
else:
    primary_col, helper_col = st.container(), None
with primary_col:
    with st.container(border=cream_theme):
        form_left, form_right = st.columns([1.35, 1], gap="large")
        with form_left:
            idea = st.text_area("창업 아이디어", value="20대 대학생 대상 합리적인 가격의 디저트 카페", height=120,
                                help="현재 입력한 문장은 표시·보고서용입니다. 연결된 엔진 없이 결과를 다시 계산하지 않습니다.")
        with form_right:
            selected = st.multiselect("비교 후보 지역 (1~3개)", dong_codes, default=dong_codes[:3], max_selections=3,
                                      format_func=lambda c: f"{base_results[c]['dong']} · {c}")
            target = st.text_input("타깃 고객 (선택)", placeholder="예: 대학생·20대 직장인")
            price = st.text_input("가격대 (선택)", placeholder="예: 디저트 5천~9천 원")

        with st.expander("선택 입력 · 영업시간 / 영업 요일 / 월세 / 객단가 / 홍보 예산", expanded=True):
            st.caption("입력하지 않아도 기존 시뮬레이션 결과를 확인할 수 있습니다. 값을 바꿔도 엔진이 다시 실행되지는 않습니다.")
            hours_enabled = st.checkbox("영업시간 입력 (open_hours)", value=False,
                                        help="엔진 규격: [시작 시각, 종료 시각] 정수 쌍. 자정 넘기는 영업은 현재 지원되지 않습니다.")
            hours_col1, hours_col2 = st.columns(2)
            with hours_col1:
                opened_at = st.time_input("영업 시작", value=time(10, 0), disabled=not hours_enabled, step=1800)
            with hours_col2:
                closed_at = st.time_input("영업 종료", value=time(22, 0), disabled=not hours_enabled, step=1800)
            money_col1, money_col2, money_col3 = st.columns(3)
            with money_col1:
                rent = st.number_input("월세 (원)", min_value=0, value=None, step=100_000,
                                       placeholder="선택 입력", help="월세만으로 손익분기점을 정확히 추정할 수는 없습니다.")
            with money_col2:
                avg_price = st.number_input("객단가 (원)", min_value=0, value=None, step=1_000,
                                            placeholder="선택 입력")
            with money_col3:
                budget = st.number_input("홍보 예산 (원)", min_value=0, value=None, step=100_000,
                                         placeholder="선택 입력")
            days_enabled = st.checkbox("영업 요일 입력 (open_days)", value=False,
                                      help="체크한 요일만 여는 설정입니다. 엔진은 월·화·수·목·금·토·일을 읽습니다.")
            open_days = st.multiselect("영업 요일", options=list(DAYS), default=list(DAYS),
                                       disabled=not days_enabled)
            engine_hours = None
            if hours_enabled:
                if opened_at.minute or closed_at.minute:
                    st.error("엔진 v6은 시간 단위 [10, 22]를 받습니다. 분 단위 설정은 현재 적용되지 않습니다.")
                elif opened_at.hour >= closed_at.hour:
                    st.error("엔진 v6은 종료 시각이 시작 시각보다 뒤인 당일 영업만 지원합니다.")
                else:
                    engine_hours = (opened_at.hour, closed_at.hour)
            if days_enabled and not open_days:
                st.warning("영업 요일을 하나 이상 선택해야 합니다.")
            st.caption("엔진에서 계산하려면 scenario.json을 반영하고 결과를 다시 생성해야 합니다. 현재는 이미 계산된 파일을 보여줍니다.")
if cream_theme and helper_col is not None:
    with helper_col:
        st.markdown('''<div class="nj-overview">
            <div>
              <div class="nj-light">WHAT YOU WILL DISCOVER</div>
              <div class="nj-heading">어디에 열고,<br>어떻게 알려야 할까요?</div>
              <p>① 동네별 입소문과 방문 수요를 비교하고<br>
                 ② 유입 경로와 홍보 전략을 살펴보고<br>
                 ③ 개선 방향과 리포트를 확인합니다.</p>
            </div>
        </div>''', unsafe_allow_html=True)
        st.caption("결과는 합성 시민과 모델 가정에 기반합니다. 실제 매출을 예측하거나 보장하지 않습니다.")

if not selected:
    st.info("후보 지역을 하나 이상 선택해 주세요.")
    st.stop()

left_button, right_notice = st.columns([1, 2.5], vertical_alignment="center")
with left_button:
    if st.button("◈  시뮬레이션 결과 보기", type="primary", use_container_width=True):
        st.session_state["opened"] = True
with right_notice:
    st.caption("현재는 계산된 결과를 여는 동작입니다. 입력값을 바꾸어도 재계산하지 않습니다.")
    if (not hours_enabled or engine_hours is not None) and (not days_enabled or bool(open_days)):
        engine_scenario = open_scenario(
            idea=idea, codes=selected, open_hours=engine_hours,
            open_days=open_days if days_enabled else None,
            rent=rent, avg_price=avg_price, budget=budget)
        st.download_button("엔진용 scenario.json 내려받기",
                           data=json.dumps(engine_scenario, ensure_ascii=False, indent=2),
                           file_name="scenario.json", mime="application/json",
                           help="엔진이 실제로 읽는 키 open_hours/open_days/avg_price/rent를 사용합니다. 적용 및 재계산은 팀장이 결정합니다.")
    memo = notes_payload(idea=idea, codes=selected, budget=budget, target=target, price_band=price)
    st.download_button("아이디어·홍보예산 메모 JSON",
                       data=json.dumps(memo, ensure_ascii=False, indent=2),
                       file_name="norunja_input_notes.json", mime="application/json",
                       help="엔진이 이 메모를 자동으로 읽지는 않습니다.")

if cream_theme and not st.session_state.get("opened", False):
    st.markdown('''<div class="nj-mini-grid">
        <div class="nj-mini"><div class="nj-mini-top">01 · WHERE</div>
           <div class="nj-mini-title">어느 동네가 좋을까?</div>
           <div class="nj-mini-description">후보 동별 확산·방문 수요 비교</div></div>
        <div class="nj-mini"><div class="nj-mini-top">02 · WHEN</div>
           <div class="nj-mini-title">언제 자리 잡을까?</div>
           <div class="nj-mini-description">12주 전망과 손익분기 정보</div></div>
        <div class="nj-mini"><div class="nj-mini-top">03 · HOW</div>
           <div class="nj-mini-title">어떻게 알릴까?</div>
           <div class="nj-mini-description">채널 분석과 홍보 예산 비교</div></div>
      </div>''', unsafe_allow_html=True)

if not st.session_state.get("opened", False):
    note("버튼을 누르면 지도와 지역별 비교·진단 결과가 표시됩니다. 샘플 모드에서는 모두 가상 수치입니다.")
    st.stop()

scenario_choice = "baseline"
scenario_label = "기준 시나리오"
active_results = base_results
if scenarios:
    scenario_lookup = {x["code"]: x for x in scenarios if x.get("results")}
    heading("02", "실험 시나리오", "PM이 제공한 수정안 결과가 있을 때만 수정 전·후 비교를 할 수 있습니다.")
    options = ["baseline"] + list(scenario_lookup)
    labels = {"baseline": "기준 시나리오"} | {x["code"]: x["label"] for x in scenarios}
    scenario_choice = st.selectbox("지도 및 분석에 표시할 시나리오", options,
                                   format_func=lambda x: labels.get(x, x))
    if scenario_choice != "baseline":
        active_results = {str(x["dong_code"]): x for x in scenario_lookup[scenario_choice]["results"]}
        scenario_label = labels[scenario_choice]
    else:
        scenario_label = "기준 시나리오"
    not_in_scenario = set(selected)-set(active_results)
    if not_in_scenario:
        st.warning("선택한 수정 시나리오에 일부 지역의 결과가 없습니다. 해당 지역은 제외됩니다.")
        selected = [x for x in selected if x in active_results]
    if not selected:
        st.stop()
else:
    st.markdown('<div class="ls-note">변경 전·후 비교는 아직 미연동입니다. PM이 수정안을 다시 계산한 결과를 <code>frontend/data/real/scenarios/</code>에 넣으면 비교 기능이 나타납니다.</div>', unsafe_allow_html=True)

preview_uploaded_by_code = {}
for uploaded in supplied_result_files or []:
    if uploaded.size > 2_000_000:
        st.warning(f"{uploaded.name}: 2MB보다 커서 미리보기에 사용하지 않습니다.")
        continue
    try:
        obj = json.loads(uploaded.getvalue().decode('utf-8-sig'))
        if isinstance(obj, dict) and obj.get('dong_code') is not None:
            preview_uploaded_by_code[str(obj['dong_code'])] = obj
    except (UnicodeDecodeError, ValueError):
        st.warning(f"{uploaded.name}: JSON 읽기 오류")

def show_result(code):
    original = active_results[code]
    item = original
    if demo and preview_new_sections:
        item = {**item, **preview_fields()}
    incoming = preview_uploaded_by_code.get(str(code))
    if incoming is not None:
        item = {**item, **{key: incoming[key] for key in V6_KEYS if key in incoming}}
    return item

items = [active_results[x] for x in selected]
view_items = [show_result(x) for x in selected]
summary = summaries(items, len(people))
leader = summary.iloc[0].to_dict()

tab_map, tab_forecast, tab_marketing, tab_report = st.tabs([
    "🗺️ 입지·지도", "📈 12주·유동인구", "📣 유입·홍보·허브", "📋 진단·리포트",
])

with tab_map:
    heading("02" if not scenarios else "03", "후보 입지 인사이트", "후보별 확산 결과는 서로 독립적인 시뮬레이션이며, 합산해서는 안 됩니다.")
    row_cols = st.columns(4, gap="small")
    with row_cols[0]:
        card("이번 시뮬레이션의 1위 후보", str(leader["dong"]), "잠재 방문 고객 계산값 기준", best=True)
    with row_cols[1]:
        card("1위 · 잠재 방문 고객", f'{int(leader["visitors"]):,}명', "모델 계산값 · 실측 방문 아님")
    with row_cols[2]:
        card("1위 · 소식 도달 시민", f'{int(leader["exposed"]):,}명', "중복 제외, 가상 시민 기준")
    with row_cols[3]:
        card("1위 · 가상 시민 도달률", f'{leader["exposure_ratio"]:.1f}%' if map_links_valid else "연결 확인 필요",
             f'전체 {len(people):,}명 기준' if map_links_valid else "ID 연결 전 비율 표시 제한")

    heading("03" if not scenarios else "04", "입소문 확산 시각화", "회색 = 미노출 · 민트 = 이전 단계 노출 · 주황 = 이번 단계 새로 소식을 들은 시민")
    region_col, mode_col, view_col = st.columns([1.3, 1, 1.0], gap="medium")
    with region_col:
        region = st.selectbox("지도에 표시할 행정동", selected, format_func=lambda x: f"{active_results[x]['dong']} · {x}")
    with mode_col:
        map_mode = st.selectbox("지도 표시 방식", ["인터랙티브 애니메이션", "호환 지도"],
                                help="인터랙티브 애니메이션은 OpenStreetMap 타일과 Leaflet을 사용합니다. 차단되면 호환 지도를 선택하세요.")
    with view_col:
        focus_choice = st.selectbox("지도 범위", ["선택 동 확대", "전체 동 보기"],
                                    help="동을 바꾸면 선택한 동 중심으로 이동합니다. 전체 동 보기에서는 모든 시민의 위치가 한 화면에 보입니다.")
    focus_mode = "selected" if focus_choice == "선택 동 확대" else "all"
    result = active_results[region]
    display_result = show_result(region)
    if demo and preview_new_sections:
        st.warning("시각화용 예시 수치입니다. 실제 팀의 엔진 계산 결과가 아니며 원본 다운로드에 반영되지 않습니다.")
    if region in preview_uploaded_by_code:
        st.info("이 지역의 엔진 v6 새 필드를 임시 확인 중입니다. 원본 지도·순위·다운로드 결과와 구분하세요.")
    if not map_links_valid:
        st.warning("지도 표시 중지: 페르소나와 확산 단계 시민 ID 연결이 검증되지 않았습니다. 분석 탭의 그래프와 수치는 확인할 수 있습니다.")
    elif not result["steps"]:
        st.warning("확산 단계 데이터가 비어 있습니다. PM의 JSON을 확인하세요.")
    else:
        if map_mode == "인터랙티브 애니메이션":
            anim_result = {**result, "_is_demo": demo}
            components.html(build_map_html(people, anim_result, dataset["geo"], result["dong"], focus_mode=focus_mode),
                            height=670, scrolling=False)
            st.caption("지도 안에서 재생·일시정지·속도 조절·단계 이동을 할 수 있습니다. 지도 로딩은 인터넷 연결이 필요합니다.")
        else:
            max_frame = len(result["steps"]) - 1
            frame = st.slider("표시 단계", min_value=-1, max_value=max_frame, value=max_frame,
                              help="-1은 확산 시작 이전입니다.")
            st.pydeck_chart(map_fallback(people, dataset["geo"], result, frame, view_mode=focus_mode), height=475,
                            use_container_width=True)
            reached, latest = exposed_until(result["steps"], frame)
            st.caption(f"누적 노출 {len(reached):,}명 · 이번 단계 {len(latest):,}명 · 전체 가상 시민 {len(people):,}명")

    if demo:
        st.markdown('<div class="ls-note orange">데모에서는 각 동의 대략적인 위치에 가상 시민을 배치했습니다. 선택 동 확대 기능은 작동하지만, 경계는 임의 직사각형이며 실제 행정동 경계가 아닙니다. B 담당의 실제 CSV와 GeoJSON으로 교체해야 정확한 지리 시각화가 됩니다.</div>', unsafe_allow_html=True)
    elif dataset["geo"] is None:
        st.warning("dongs.geojson이 없습니다. 점은 표시할 수 있지만 실제 행정동 경계는 아직 없습니다.")

    heading("04" if not scenarios else "05", "후보 지역 비교", "상대 막대의 길이는 후보 중 최댓값을 100%로 둔 값으로, 실제 방문 확률이 아닙니다.")
    compare_left, compare_right = st.columns([1.15, 1], gap="large")
    with compare_left:
        st.markdown("**잠재 방문 고객(모델 계산값)**")
        fig = go.Figure(go.Bar(
            y=summary["dong"][::-1], x=summary["visitors"][::-1], orientation="h",
            marker={"color": [("#E6B437" if cream_theme else "#FFCA39") if str(x)==str(leader["dong"]) else chart_alt for x in summary["dong"][::-1]],
                    "line": {"width": 0}},
            text=summary["visitors"][::-1].astype(str)+"명", textposition="outside",
            hovertemplate="%{y}: %{x}명<extra></extra>"
        ))
        fig.update_layout(height=260, margin={"l": 0, "r": 55, "t": 10, "b": 20},
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font={"color": chart_ink, "size": 13},
                          xaxis={"showgrid": True, "gridcolor": chart_grid, "zeroline": False, "title": "모델 계산 인원"},
                          yaxis={"showgrid": False})
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with compare_right:
        st.markdown(f"**{result['dong']} · 단계별 누적 도달**")
        st.plotly_chart(curve_chart(result), use_container_width=True,
                        config={"displayModeBar": False})

    if scenario_choice != "baseline":
        st.markdown("**수정 전·후 비교 (두 파일의 모델 계산값)**")
        diff_rows=[]
        for code in selected:
            original = base_results.get(code)
            revised = active_results.get(code)
            if original is not None and revised is not None:
                diff_rows.append({"행정동":revised["dong"],"기준 방문 고객":original["visitors"],
                                  "수정안 방문 고객":revised["visitors"],"차이":revised["visitors"]-original["visitors"],
                                  "기준 노출":total_exposed(original),"수정안 노출":total_exposed(revised)})
        if diff_rows:
            st.dataframe(pd.DataFrame(diff_rows), hide_index=True, use_container_width=True)
            st.caption("차이는 시나리오 간 모델 계산 결과 차이이며, 실제 개선 효과를 입증하지 않습니다.")

with tab_forecast:
    # Final flow fields are optional in the current MVP JSON. Do not invent values
    # when engine output is absent; new keys render automatically after integration.
    heading("05", "방문 수요 · 경쟁 · 낮 시간대 비중", "팀장님이 추가한 결과 필드 3개를 원본값 그대로 표시합니다.")
    field_cols = st.columns(3, gap="small")
    for column, label, field, info in zip(
        field_cols,
        ("방문 수요", "경쟁 보정 계수", "낮 시간대 비중"),
        ("visitors_demand", "competition_factor", "daytime_share"),
        ("visitors_demand 원본값", "competition_factor 원본값", "daytime_share 원본값"),
    ):
        with column:
            card(label, raw_metric(display_result, field), f"{result['dong']} · {info}")
    if any(finite_number(display_result.get(k)) is None for k in ("visitors_demand", "competition_factor", "daytime_share")):
        st.caption("현재 ZIP의 결과 파일에는 일부 신규 지표가 아직 없습니다. 팀장님이 해당 값을 넣으면 자동 표시됩니다.")
    st.caption("세 지표의 단위와 계산식은 엔진 담당자와 확정 후 표시합니다. 특히 낮 시간대 비중은 단위 확정 전까지 임의로 % 변환하지 않았습니다.")

    # Public-data estimates should not be presented as observed data.
    stats_path = folder / "dong_stats.csv"
    if stats_path.exists():
        try:
            stats_df = pd.read_csv(stats_path, dtype={"dong_code": str}, encoding="utf-8-sig",
                                   usecols=["dong_code", "is_estimated"])
            estimate_row = stats_df.loc[stats_df["dong_code"] == str(result["dong_code"])]
            if not estimate_row.empty and str(estimate_row.iloc[0]["is_estimated"]).strip() in ("1", "1.0", "True", "true"):
                st.warning("이 행정동의 공공데이터 일부에는 추정·보완한 값이 포함됩니다. 실측 자료로 해석하지 마세요.")
        except (OSError, ValueError, KeyError):
            st.caption("동별 공공데이터의 추정 여부를 아직 확인할 수 없습니다.")

    with st.expander("공공데이터 · 시간대별 / 연령대별 유동인구 (선택 지역)", expanded=False):
        local_stats = inspect_dong_stats(folder, result["dong_code"])
        if local_stats.get("warning"):
            st.info(local_stats["warning"])
        elif local_stats.get("periods"):
            a, b = st.columns(2)
            with a:
                st.markdown("**시간대별 유동인구**")
                st.bar_chart(pd.DataFrame(local_stats["periods"]), x="구간", y="유동인구")
            with b:
                st.markdown("**연령대별 유동인구**")
                st.bar_chart(pd.DataFrame(local_stats["ages"]), x="연령대", y="유동인구")
            if local_stats.get("weekday") is not None and local_stats.get("weekend") is not None:
                st.caption(f"평일 {local_stats['weekday']:,.0f} / 주말 {local_stats['weekend']:,.0f} (원본 자료 단위)")
            st.caption("공공데이터 기반 유동인구이며, 우리 가게의 실제 방문객이나 추가 방문 수요를 뜻하지 않습니다.")
        else:
            st.info("선택 지역의 공공데이터가 아직 없습니다.")

    heading("06", "12주 방문객 곡선 · 손익분기",
            "후보 지역 1~3개의 주별 방문 곡선을 겹쳐 비교합니다. 원본 엔진 수치이며 지역별 예측은 독립적입니다.")
    combined_df = series_for_regions(view_items)
    if combined_df.empty:
        st.info("세 후보 지역 12주 방문객 데이터 대기 중 · weekly_visitors를 확인하세요.")
    else:
        st.markdown("**후보 지역별 12주 방문 고객 추이 (같은 그래프)**")
        fig_regions = go.Figure()
        region_colors = ['#D49B16' if cream_theme else '#F6C543', '#667D90', '#AAB5BD']
        for i, name in enumerate(combined_df['dong'].unique()):
            subset = combined_df[combined_df['dong'] == name]
            fig_regions.add_trace(go.Scatter(
                x=subset['week'], y=subset['visitors'], mode='lines+markers',
                name=str(name), line={'width':3,'color':region_colors[i % len(region_colors)]},
                hovertemplate='%{x}주차 · %{y:,.0f}명<extra>' + safe(name) + '</extra>'))
        fig_regions.update_layout(
            height=350, margin={'l':6,'r':12,'t':20,'b':25},
            font={'color':chart_ink},
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            legend={'orientation':'h','y':1.14},
            xaxis={'title':'오픈 후 주차','dtick':1,'gridcolor':chart_grid},
            yaxis={'title':'주별 모델 방문 고객 수','gridcolor':chart_grid})
        st.plotly_chart(fig_regions, use_container_width=True, config={'displayModeBar':False})
    monthly_cards = st.columns(len(view_items))
    for col, item in zip(monthly_cards, view_items):
        with col:
            n = finite_number(item.get('monthly_customers'))
            card(f"{item['dong']} · 3달째 월 고객", f"{n:,.0f}명" if n is not None else "자료 대기",
                 "최근 4주 고객 합계 · 엔진 계산값")

    week_df = weekly_frame(display_result)
    re_df = repromo_frame(display_result)
    weekly_left, weekly_right = st.columns([1.65, 1], gap="large")
    with weekly_left:
        if week_df.empty:
            st.info("12주 방문객 데이터 대기 중 · result JSON에 weekly_visitors가 추가되면 곡선이 표시됩니다.")
        else:
            fig_week = go.Figure()
            fig_week.add_trace(go.Scatter(x=week_df["week"], y=week_df["visitors"], mode="lines+markers",
                                          name="주별 방문 가능 고객", line={"color": "#E6B437" if cream_theme else "#FFCA39", "width": 3},
                                          marker={"size": 7}))
            if not re_df.empty:
                fig_week.add_trace(go.Scatter(x=re_df["week"], y=re_df["with_promo"],
                                              mode="lines+markers", name="추가 홍보", line={"color": "#64D9E7", "width": 2, "dash": "dash"}))
                fig_week.add_trace(go.Scatter(x=re_df["week"], y=re_df["without_promo"],
                                              mode="lines+markers", name="추가 홍보 없음", line={"color": "#A7B5C6", "width": 2, "dash": "dot"}))
            fig_week.update_layout(height=330, margin={"l": 8, "r": 8, "t": 12, "b": 32},
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                   font={"color": chart_ink}, legend={"orientation": "h", "y": -0.25},
                                   xaxis={"title": "오픈 후 주차", "dtick": 1, "range": [0.5, 12.5], "showgrid": False},
                                   yaxis={"title": "모델 계산 인원", "gridcolor": chart_grid})
            st.plotly_chart(fig_week, use_container_width=True, config={"displayModeBar": False})
            if len(week_df) < 12:
                st.caption(f"현재 {len(week_df)}주치만 전달됐습니다. 나머지 주차는 임의로 채우지 않았습니다.")
    with weekly_right:
        if "breakeven_week" not in display_result:
            card("손익분기 주차", "자료 대기", "breakeven_week 필드 미도착")
        elif display_result["breakeven_week"] is None:
            card("손익분기 주차", "판정 정보 없음", "월세·객단가 미입력 또는 분석 기간 내 미도달일 수 있습니다.")
        else:
            week = finite_number(display_result["breakeven_week"])
            card("손익분기 주차", f"{int(week)}주 차" if week is not None and 0 < week <= 12 else "값 확인 필요",
                 "모델의 손익 가정값에 따른 결과 · 실제 수익 보장 아님")
        note("월세와 객단가만으로는 정확한 손익분기를 계산할 수 없습니다. 인건비·원가·기타 고정비 등의 가정과 산식은 엔진 팀의 확인이 필요합니다.", warning=True)

with tab_marketing:
    heading("07", "채널별 유입 비율", "전체 유입 경로와 집단별 경로를 분리해서 보여줍니다.")
    total_channel_df = channel_total_frame(display_result)
    if total_channel_df.empty:
        st.info("전체 유입 경로 자료 대기 중 · channel_total 필드가 필요합니다.")
    else:
        st.markdown("**전체 유입 경로 비율 (channel_total)**")
        fig_all_channels = go.Figure(go.Bar(
            x=total_channel_df['percent'], y=total_channel_df['channel'], orientation='h',
            marker_color='#D49B16' if cream_theme else '#FFCA39',
            hovertemplate='%{y}: %{x:.1f}%<extra></extra>'))
        fig_all_channels.update_layout(height=max(240, len(total_channel_df)*45+60),
            margin={'l':5,'r':12,'t':10,'b':25},
            paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
            font={'color':chart_ink},xaxis={'range':[0,100], 'gridcolor':chart_grid,
                'title':'유입 경로 비율 (%)'},yaxis={'title':''})
        st.plotly_chart(fig_all_channels, use_container_width=True,
                        config={'displayModeBar':False})
        st.caption('전체 경로 비율은 계산된 집단별 평균이 아니라 엔진 channel_total 원본입니다.')
    st.markdown("**집단별 유입 경로 (channel_share)**")
    channel_df = channel_frame(display_result)
    if channel_df.empty:
        st.info("채널별 유입 데이터 대기 중 · channel_share가 추가되면 집단별 비교 그래프가 표시됩니다.")
    else:
        pv = channel_df.pivot_table(index="group", columns="channel", values="percent", aggfunc="sum", fill_value=0)
        fig_ch = go.Figure()
        palette = ["#E4B43A" if cream_theme else "#FFCB45", "#4ABFC9", "#91A7CE", "#B69AE5", "#F09479", "#B9CC8B", "#CFB0A2"]
        for i, channel in enumerate(pv.columns):
            fig_ch.add_trace(go.Bar(y=pv.index.tolist(), x=pv[channel].tolist(), name=str(channel),
                                    orientation="h", marker_color=palette[i % len(palette)],
                                    hovertemplate="%{y} / %{x:.1f}%<extra>" + safe(channel) + "</extra>"))
        fig_ch.update_layout(barmode="stack", height=max(285, 55 * len(pv) + 120),
                             margin={"l": 0, "r": 8, "t": 12, "b": 22},
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             font={"color": chart_ink}, legend={"orientation": "h", "y": -0.15},
                             xaxis={"title": "경로별 인지 비율 (%)", "range": [0, 100], "gridcolor": chart_grid},
                             yaxis={"title": ""})
        st.plotly_chart(fig_ch, use_container_width=True, config={"displayModeBar": False})
        st.caption("그래프는 엔진이 제공한 경로별 비중만 표시합니다. 집단별 합계가 100%가 아니면 원본 데이터 확인이 필요합니다.")

    heading("08", "홍보 시나리오 · 예산 배분", "홍보 방식별 결과와 예산 배분안을 비교합니다. 화면 입력만으로 효과를 새로 계산하지는 않습니다.")
    scenario_df = scenarios_frame(display_result)
    split_df, plan = budget_split(display_result)
    marketing_left, marketing_right = st.columns([1.15, 1], gap="large")
    with marketing_left:
        st.markdown("**홍보 방식별 방문 가능 고객 증가량 (시뮬레이션)**")
        if scenario_df.empty:
            st.info("시나리오 비교 결과 대기 중 · scenarios가 들어오면 비교 차트가 표시됩니다.")
        else:
            fig_scen = go.Figure(go.Bar(x=scenario_df["visitors_gain"], y=scenario_df["name"],
                                       orientation="h", marker_color="#E6B437" if cream_theme else "#FFCA39",
                                       text=scenario_df["visitors_gain"], textposition="auto"))
            fig_scen.update_layout(height=max(260, len(scenario_df) * 52 + 100),
                                   margin={"l": 5, "r": 12, "t": 12, "b": 22},
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                   font={"color": chart_ink}, xaxis={"title": "모델 계산 인원 증가", "gridcolor": chart_grid},
                                   yaxis={"title": ""})
            st.plotly_chart(fig_scen, use_container_width=True, config={"displayModeBar": False})
            st.dataframe(scenario_df.rename(columns={"name": "홍보 방식", "cost": "가정 비용 (원)", "visitors_gain": "방문 가능 고객 증가 (모델)"}),
                         hide_index=True, use_container_width=True)
    with marketing_right:
        st.markdown("**홍보 예산 추천 배분안 (모델 결과)**")
        if split_df.empty:
            st.info("예산 배분안 대기 중 · budget_plan.split이 들어오면 표시됩니다.")
        else:
            st.dataframe(split_df.rename(columns={"channel": "홍보 채널", "amount": "배분 금액 (원)"}),
                         hide_index=True, use_container_width=True)
            planned = finite_number(plan.get("budget"))
            gain = finite_number(plan.get("visitors_gain"))
            if planned is not None:
                st.metric("엔진이 분석한 홍보 예산", f"{planned:,.0f}원")
            if gain is not None:
                st.metric("방문 가능 고객 증가량 (모델)", f"{gain:,.0f}명")
            if budget is not None and planned is not None and float(budget) != planned:
                st.warning("현재 입력한 홍보 예산과 저장된 엔진 결과의 예산이 다릅니다. 재시뮬레이션 전에는 추천안이 바뀌지 않습니다.")
    st.caption("광고 비용은 수집한 단가, 광고 효과는 가정값일 수 있습니다. 실제 광고 효율·매출 보장을 의미하지 않습니다.")
    with st.expander("광고 단가 원본 확인 · ad_costs.json (선택)", expanded=False):
        ad_rows = ad_costs_frame(folder)
        if ad_rows.empty:
            st.info("ad_costs.json 파일이 아직 없습니다. 팀원이 업데이트한 최신 파일을 가져오면 표시됩니다.")
        else:
            only_default = st.checkbox("기본 상품만 보기", value=True)
            table_rows = ad_rows[ad_rows['기본 상품']] if only_default else ad_rows
            st.dataframe(table_rows, hide_index=True, use_container_width=True)
            st.caption("단가 기준값은 cost_per_unit, 불확실한 범위는 cost_min/cost_max, 추정 여부는 is_estimated입니다. 단가만으로 실제 광고 효과를 계산하지 않습니다.")

    heading("09", "입소문 허브 페르소나", "가게 소식을 널리 전달할 가능성이 높은 가상 시민을 카드로 보여줍니다.")
    hubs_df = hubs_frame(display_result)
    if hubs_df.empty:
        st.info("입소문 허브 데이터 대기 중 · hubs가 들어오면 페르소나 카드가 표시됩니다.")
    else:
        hubs_columns = st.columns(min(3, len(hubs_df)))
        for i, (_, hub) in enumerate(hubs_df.head(5).iterrows()):
            with hubs_columns[i % len(hubs_columns)]:
                reach = finite_number(hub["reach"])
                card(f"가상 시민 #{hub['id']}", hub['group'],
                     f"{hub['dong']} · 입소문 전달 " +
                     (f"{int(reach):,}명" if reach is not None else "집계 대기"))
                extra = []
                if finite_number(hub.get('direct')) is not None:
                    extra.append(f"직접 전달 {int(hub['direct'])}명")
                if finite_number(hub.get('week')) is not None:
                    extra.append(f"최초 활동 {int(hub['week'])}주차")
                if isinstance(hub.get('community'), list):
                    extra.append('채널 ' + ', '.join(str(x) for x in hub['community'][:3]))
                if extra:
                    st.caption(' · '.join(extra))
        st.caption("허브는 가상 관계망에 기반한 시뮬레이션 결과로, 실제 개인이나 실제 고객을 지칭하지 않습니다.")

with tab_report:
    heading("10", "정체 지점과 반응 근거", "확산 엔진이 기록한 정체 집단·경로와 A 담당의 집단별 거절 이유를 함께 확인합니다.")
    reason_col, raw_col = st.columns([1, 1], gap="large")
    with reason_col:
        st.markdown(f"**{result['dong']} · 정체 구간**")
        stops = result.get("stopped_at", [])
        if not stops:
            st.info("현재 정체 집단이 기록되지 않았습니다.")
        else:
            for stop in stops[:5]:
                group = str(stop.get("group", "미상"))
                path = str(stop.get("path", "미상"))
                reason_type, reason_text = get_reason(group, dataset["reactions"])
                # A group-level objection is a hypothesis, not necessarily the cause of an edge failing.
                detail = f"정체 경로: {path}"
                if reason_type:
                    detail += f" | 같은 집단의 합성 설문 응답: {reason_type}"
                st.markdown(f'<div class="ls-diagnosis"><div class="title">{safe(group)}</div>'
                            f'<div class="detail">{safe(detail)}</div>'
                            + (f'<div class="detail">{safe(reason_text)}</div>' if reason_text else "")
                            + '</div>', unsafe_allow_html=True)
        diagnosis = display_result.get("diagnosis")
        if not isinstance(diagnosis, str) or not diagnosis.strip():
            # The teammate previously delivered diagnosis_{dong_code}.json separately.
            diag_path = folder / f"diagnosis_{result['dong_code']}.json"
            if diag_path.exists():
                try:
                    diag_data = json.loads(diag_path.read_text(encoding="utf-8-sig"))
                    if isinstance(diag_data, dict):
                        diagnosis = diag_data.get("diagnosis") or diag_data.get("summary")
                except (OSError, ValueError):
                    st.caption("별도 진단 JSON을 읽지 못했습니다. 파일 구조를 확인해 주세요.")
        if isinstance(diagnosis, str) and diagnosis.strip():
            st.info(f"**A 담당 AI 진단 요약:** {diagnosis}")
        else:
            st.caption("AI 진단은 result JSON의 diagnosis 또는 별도 diagnosis_{동코드}.json에 문장이 있으면 표시됩니다.")
    with raw_col:
        st.markdown("**집단별 Syntitan / LLM 반응**")
        if dataset["reactions"]:
            reactions_df = pd.DataFrame(dataset["reactions"])
            view_cols = [c for c in ("group","interest","share","reason_type","community") if c in reactions_df.columns]
            st.dataframe(reactions_df[view_cols], hide_index=True, use_container_width=True, height=260)
            st.caption("관심도·전달 의향은 1~5점 응답입니다. 시민들의 실제 설문이나 실측 반응이 아닙니다.")
        else:
            st.info("reactions.json 파일이 아직 없습니다.")

    heading("11", "결과 리포트와 검증 이력", "수치 범위·계산 가정·시드 수와 데이터 출처를 함께 제시합니다.")
    st.markdown("**현재 지역 결과의 범위·가정**")
    mnmx = visits_range(display_result)
    if mnmx:
        st.metric("방문 가능 고객 결과 범위 (시드 반복)", f"{mnmx[0]:,.0f} ~ {mnmx[1]:,.0f}명")
    else:
        st.info("visitors_range 자료 대기 중")
    if finite_number(display_result.get('runs')) is not None:
        st.caption(f"시드 반복 횟수: {int(display_result['runs'])}회")
    assumptions_df = assumptions_frame(display_result)
    if assumptions_df.empty:
        st.info("assumptions 자료 대기 중")
    else:
        st.markdown("**엔진 계산 가정(원본)**")
        st.dataframe(assumptions_df.rename(columns={'key':'필드','value':'원본 값'}),
                     hide_index=True, use_container_width=True)
        st.caption("rent가 null이면 임대료 미반영 가능성이 있습니다. 손익분기 null은 임의의 주차로 대체하지 않습니다.")
    applied_hours = display_result.get('open_hours')
    applied_days = display_result.get('open_days')
    st.caption(f"결과에 적용된 영업시간: {applied_hours if applied_hours is not None else '미설정'} · "
               f"영업 요일: {', '.join(applied_days) if isinstance(applied_days, list) else '미설정'}")
    report_df = summary_export(items, len(people))
    with st.expander("지역별 상세 수치", expanded=True):
        st.dataframe(report_df, hide_index=True, use_container_width=True)
    with st.expander("검증 기록 · 신뢰성 상태"):
        validations = dataset["validations"]
        if isinstance(validations, list) and validations:
            st.dataframe(pd.DataFrame(validations), hide_index=True, use_container_width=True)
            st.caption("검증 기록은 B 담당이 제공한 자료를 그대로 표시합니다. 표의 수치를 독립적으로 검증한 결과는 아닙니다.")
        else:
            st.info("B 담당 검증 기록이 아직 없습니다. 결과가 현실과 부합한다고 주장할 수 없습니다.")
        st.markdown("**해석 시 주의사항**")
        st.caption("실제 상권 매출과 시뮬레이션 순위의 상관관계가 높더라도 새로운 가게의 실제 방문객 수를 검증한 것은 아닙니다. 검증 데이터와 가중치 조정 데이터도 분리해야 합니다.")

    export1, export2, export3 = st.columns(3, gap="small")
    with export1:
        # Machine-readable exports follow the team's lowercase-English-column UTF-8 contract.
        machine_export = summaries(items, len(people))
        st.download_button("↓ 지역 비교 CSV", machine_export.to_csv(index=False).encode("utf-8"),
                           "norunja_comparison.csv", "text/csv", use_container_width=True)
    with export2:
        st.download_button("↓ 결과 JSON", json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"),
                           "norunja_results.json", "application/json", use_container_width=True)
    with export3:
        st.download_button("↓ 보고서 HTML", html_report(items, len(people), idea, demo, scenario_label),
                           "norunja_report.html", "text/html", use_container_width=True,
                           help="브라우저에서 열어 인쇄/파일로 저장할 수 있는 간단 리포트입니다.")

st.markdown('<div class="ls-footer">노른자 · TEAM 05 · 2026 해커톤<br>'
            '현재 프론트엔드는 계산 결과의 시각화 및 비교 도구입니다. 가상 시민 수·합성 설문·모델 계산값을 실제 유동인구, 방문객 수 또는 매출 예측치로 해석해서는 안 됩니다.</div>',
            unsafe_allow_html=True)
