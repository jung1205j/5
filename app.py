"""LocalSim / Team 05 — C team's full frontend and visual-report deliverable.

The app DOES NOT itself perform Syntitan surveying, graph diffusion,
or real-customer prediction. It reads the team's fixed artifacts and makes
an honest, interactive map/reports experience.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

from frontend.data_io import DataContractError, exposed_until, load_dataset
from frontend.animated_map import build_map_html
from frontend.analysis_helpers import (total_exposed, exposure_by_step, summaries,
                              summary_export, scenario_options, get_reason, html_report)

ROOT = Path(__file__).resolve().parent
st.set_page_config(
    page_title="LocalSim · 로컬 창업 시뮬레이터",
    page_icon="🗺️", layout="wide", initial_sidebar_state="expanded",
)

CSS = """
<style>
:root {--ocean:#081725;--panel:#10283a;--panel2:#122c40;--line:#29465b;--ink:#f0f8fe;--muted:#a9bfce;--accent:#3ce0c5;--amber:#ffc078;}
html, body, [data-testid='stAppViewContainer']{background:#071724;color:#f0f8fe;}
[data-testid='stAppViewContainer']{background:radial-gradient(ellipse 800px 460px at 74% -6%,rgba(31,93,112,.22),transparent 74%),#071724;}
[data-testid='stHeader']{background:transparent;}
[data-testid='stSidebar']{background:#0a1e2e;border-right:1px solid #294257;}
[data-testid='stMainBlockContainer'],section.main .block-container{max-width:1440px!important;padding:2rem 2.1rem 4rem!important;}
[data-testid='stSidebar'] .block-container{padding:2rem 1.1rem!important;}
[data-testid='stTextArea'] textarea,[data-testid='stTextInput'] input,[data-testid='stMultiSelect'] div[data-baseweb='select']>div,[data-testid='stSelectbox'] div[data-baseweb='select']>div{background-color:#11283c!important;color:#f0f8fe!important;border-color:#36566b!important;border-radius:11px!important;}
[data-testid='stTextArea'] textarea{font-size:1.05rem!important;line-height:1.55!important;}
[data-testid='stTextArea'] textarea:focus{border-color:#3ce0c5!important;}
[data-testid='stWidgetLabel'] p{color:#d9e8f3;font-weight:700;font-size:.90rem;}
.stButton>button{background:#173349;border:1px solid #33566c;color:#e4f2fd;border-radius:11px;font-weight:750;min-height:43px;font-size:.91rem;}
.stButton>button:hover{border-color:#3ce0c5;background:#19475a;color:#fff;}
.stButton>button[kind='primary']{background:#3ce0c5!important;color:#092938!important;border:1px solid #3ce0c5!important;}
.stButton>button[kind='primary']:hover{background:#89f4e1!important;}
[data-testid='stDownloadButton'] button{border-radius:11px;background:#142c40;color:#e4f2fa;border:1px solid #365569;font-weight:650;}
[data-testid='stExpander']{border:1px solid #294458!important;border-radius:12px;background:#0e2435;}
[data-testid='stAlert']{border-radius:12px;}
[data-testid='stMetric']{background:#0e2739;border:1px solid #2e4c60;border-radius:14px;padding:15px;}
[data-testid='stMetricLabel'] p{color:#b9cbd9;font-size:.90rem;font-weight:650;}
[data-testid='stMetricValue']{font-size:1.60rem;color:#eff9ff;}
[data-testid='stDataFrame']{border:1px solid #2a4b5f;border-radius:12px;overflow:hidden;}
[data-testid='stSelectbox']{margin-bottom:0.3rem;}
[data-testid='stSidebar'] [data-testid='stMarkdownContainer'] p{line-height:1.65}
hr{border-color:#284359!important;}
header#streamlitHeader,footer{visibility:hidden;}
.ls-kicker{font-size:.78rem;color:#69e6d1;font-weight:850;letter-spacing:.18em;margin-bottom:12px;}
.ls-head{display:flex;gap:14px;align-items:center;margin-bottom:7px;}
.ls-mark{display:inline-flex;align-items:center;justify-content:center;width:52px;height:52px;background:linear-gradient(145deg,#3ce0c5,#87b4fb);border-radius:15px;color:#07314b;font-size:28px;font-weight:900;box-shadow:0 10px 25px #2fd2c02b;}
.ls-title{font-size:2.65rem;font-weight:900;line-height:1.13;letter-spacing:-.075em;color:#effaff;}
.ls-sub{font-size:1.05rem;color:#bbccdb;line-height:1.65;margin:4px 0 16px;}
.ls-pill{display:inline-block;border:1px solid #356777;border-radius:999px;padding:6px 12px;color:#8fefde;background:#12394266;font-size:.77rem;letter-spacing:.02em;font-weight:750;margin-right:8px;margin-bottom:8px;}
.ls-pill.warn{color:#ffcd8a;border-color:#695332;background:#4c3a1e44;}
.ls-section{display:flex;align-items:center;gap:12px;color:#f0f7ff;font-size:1.28rem;letter-spacing:-.035em;font-weight:830;margin:31px 0 9px;}
.ls-number{color:#69e6d1;font-size:.75rem;letter-spacing:.15em;font-weight:900;}
.ls-copy{font-size:.93rem;color:#a9bece;line-height:1.55;margin-bottom:15px;}
.ls-card{padding:19px 21px;background:linear-gradient(145deg,#142f43,#0e2436);border:1px solid #2e4d60;border-radius:16px;min-height:137px;}
.ls-card.best{background:linear-gradient(145deg,#124a4d,#112a3b);border-color:#3ad7bf;}
.ls-kpi-label{color:#bdd0dc;font-size:.85rem;font-weight:700;margin-bottom:9px;}
.ls-kpi-value{color:#f0faff;font-size:1.75rem;font-weight:870;line-height:1.2;letter-spacing:-.05em;word-break:keep-all;}
.ls-kpi-detail{font-size:.77rem;color:#9bb5c5;margin-top:9px;line-height:1.5;}
.ls-note{padding:13px 16px;border-radius:12px;border:1px solid #325367;background:#132f43;color:#b7cddc;font-size:.87rem;line-height:1.65;}
.ls-note.orange{border-color:#725e35;background:#3d33272b;color:#ecd1aa;}
.ls-diagnosis{padding:13px 15px;border:1px solid #345168;border-left:3px solid #ffc078;border-radius:10px;background:#102a3c;margin:11px 0;}
.ls-diagnosis .title{font-size:.96rem;color:#f4eedb;font-weight:760;}
.ls-diagnosis .detail{font-size:.81rem;color:#b3cad9;margin-top:5px;line-height:1.7;}
.ls-meta{font-size:.83rem;color:#b7ccd9;line-height:1.7;}
.ls-footer{font-size:.82rem;color:#9bb2c4;line-height:1.8;margin-top:20px;}
.ls-side-name{color:#eaf9ff;font-weight:900;letter-spacing:-.045em;font-size:1.35rem;}
.ls-side-sub{color:#8cb1c6;font-size:.77rem;margin:5px 0 18px;}
.ls-file{color:#bfd4df;font-size:.82rem;line-height:2.1;}
.ls-dot{display:inline-block;width:7px;height:7px;margin-right:8px;border-radius:100%;background:#31c5a4;}
.ls-dot.missing{background:#7a899c;}
@media(max-width:850px){[data-testid='stMainBlockContainer'],section.main .block-container{padding:1rem .8rem 3rem!important}.ls-title{font-size:2.05rem}.ls-kpi-value{font-size:1.4rem}.ls-card{min-height:auto;padding:14px}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


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
                             line={"color": "#3ce0c5", "width": 3, "shape": "spline"},
                             marker={"size": 8, "color": "#3ce0c5"},
                             fill="tozeroy", fillcolor="rgba(60,224,197,.11)",
                             hovertemplate="%{x}단계 / 누적 %{y}명<extra></extra>"))
    fig.update_layout(height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin={"l": 8, "r": 12, "t": 12, "b": 20},
                      font={"color": "#c7dae7", "size": 12}, showlegend=False,
                      xaxis={"title": "확산 단계", "showgrid": False, "dtick": 1, "zeroline": False},
                      yaxis={"title": "고유 노출 시민 수", "gridcolor": "#294357", "zeroline": False})
    return fig


# SIDE PANEL
with st.sidebar:
    st.markdown('<div class="ls-side-name">◈ LocalSim / Team 05</div>'
                '<div class="ls-side-sub">LOCAL WORD-OF-MOUTH LAB · 2026 AI HACKATHON</div>',
                unsafe_allow_html=True)
    source = st.radio("데이터 소스", ["샘플 데이터", "팀 실데이터"], index=0,
                      help="팀 실데이터는 frontend/data/real 폴더에 PM과 B 담당 파일을 넣어야 활성화됩니다.")
    demo = source == "샘플 데이터"
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

try:
    dataset = load_dataset(folder)
except DataContractError as exc:
    st.error(f"데이터를 불러올 수 없습니다: {exc}")
    st.info("현재 팀 자료가 없다면 왼쪽에서 '샘플 데이터'를 선택하세요. 실제 파일은 frontend/data/real/에 저장하면 됩니다.")
    st.stop()

people = dataset["persons"]
base_results = {str(x["dong_code"]): x for x in dataset["results"]}
dong_codes = list(base_results.keys())
scenarios = scenario_options(folder, people)

st.markdown('<div class="ls-kicker">LOCATION INTELLIGENCE / WOM SIMULATION / 2026</div>'
            '<div class="ls-head"><div class="ls-mark">◈</div><div class="ls-title">LocalSim</div></div>'
            '<div class="ls-sub">가게를 열기 전, 동네별 가상 시민의 반응과 입소문 확산을 비교하고 정체 지점을 진단하는 실험 공간.</div>'
            '<span class="ls-pill">TEAM 05 · 프론트엔드</span>'
            + ('<span class="ls-pill warn">데모 / 가상 결과</span>' if demo else '<span class="ls-pill warn">팀 계산 결과 / 검증 별도</span>'),
            unsafe_allow_html=True)

heading("01", "아이디어를 입력하고 입지를 비교하세요", "실제 분석은 PM의 확산 엔진에서 수행하며, 현재 화면은 전달받은 결과 파일을 시각화합니다.")
form_left, form_right = st.columns([1.35, 1], gap="large")
with form_left:
    idea = st.text_area("창업 아이디어", value="20대 대학생 대상 합리적인 가격의 디저트 카페", height=120,
                        help="현재 입력한 문장은 표시·보고서용입니다. 연결된 엔진 없이 결과를 다시 계산하지 않습니다.")
with form_right:
    selected = st.multiselect("비교 후보 지역 (1~3개)", dong_codes, default=dong_codes[:3], max_selections=3,
                              format_func=lambda c: f"{base_results[c]['dong']} · {c}")
    with st.expander("추가 정보 입력(향후 연동)"):
        target = st.text_input("타깃 고객", placeholder="예: 대학생·20대 직장인")
        price = st.text_input("가격대", placeholder="예: 디저트 5천~9천 원")
        st.caption("이 두 입력도 현재 계산 결과에는 영향을 주지 않습니다.")

if not selected:
    st.info("후보 지역을 하나 이상 선택해 주세요.")
    st.stop()

left_button, right_notice = st.columns([1, 2.5], vertical_alignment="center")
with left_button:
    if st.button("◈  시뮬레이션 결과 보기", type="primary", use_container_width=True):
        st.session_state["opened"] = True
with right_notice:
    st.caption("현재는 계산된 결과를 여는 동작입니다. 아이디어를 바꾸어도 재계산하지 않습니다.")

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

items = [active_results[x] for x in selected]
summary = summaries(items, len(people))
leader = summary.iloc[0].to_dict()

heading("02" if not scenarios else "03", "후보 입지 인사이트", "후보별 확산 결과는 서로 독립적인 시뮬레이션이며, 합산해서는 안 됩니다.")
row_cols = st.columns(4, gap="small")
with row_cols[0]:
    card("이번 시뮬레이션의 1위 후보", str(leader["dong"]), "잠재 방문 고객 계산값 기준", best=True)
with row_cols[1]:
    card("1위 · 잠재 방문 고객", f'{int(leader["visitors"]):,}명', "모델 계산값 · 실측 방문 아님")
with row_cols[2]:
    card("1위 · 소식 도달 시민", f'{int(leader["exposed"]):,}명', "중복 제외, 가상 시민 기준")
with row_cols[3]:
    card("1위 · 가상 시민 도달률", f'{leader["exposure_ratio"]:.1f}%', f'전체 {len(people):,}명 기준')

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
if not result["steps"]:
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
        marker={"color": ["#55e8cf" if str(x)==str(leader["dong"]) else "#7daada" for x in summary["dong"][::-1]],
                "line": {"width": 0}},
        text=summary["visitors"][::-1].astype(str)+"명", textposition="outside",
        hovertemplate="%{y}: %{x}명<extra></extra>"
    ))
    fig.update_layout(height=260, margin={"l": 0, "r": 55, "t": 10, "b": 20},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font={"color": "#d5e6f1", "size": 13},
                      xaxis={"showgrid": True, "gridcolor": "#29485d", "zeroline": False, "title": "모델 계산 인원"},
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

heading("05" if not scenarios else "06", "정체 지점과 반응 근거", "확산 엔진이 기록한 정체 집단·경로와 A 담당의 집단별 거절 이유를 함께 확인합니다.")
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
    diagnosis = result.get("diagnosis")
    if isinstance(diagnosis, str) and diagnosis.strip():
        st.info(f"**A 담당 AI 진단 요약:** {diagnosis}")
    else:
        st.caption("A 담당 AI 원인 진단 문장은 아직 미연동입니다. 선택 필드 diagnosis에 넣으면 표시됩니다.")
with raw_col:
    st.markdown("**집단별 Syntitan / LLM 반응**")
    if dataset["reactions"]:
        reactions_df = pd.DataFrame(dataset["reactions"])
        view_cols = [c for c in ("group","interest","share","reason_type","community") if c in reactions_df.columns]
        st.dataframe(reactions_df[view_cols], hide_index=True, use_container_width=True, height=260)
        st.caption("관심도·전달 의향은 1~5점 응답입니다. 시민들의 실제 설문이나 실측 반응이 아닙니다.")
    else:
        st.info("reactions.json 파일이 아직 없습니다.")

heading("06" if not scenarios else "07", "결과 리포트와 검증 이력", "보고서에 사용할 때는 반드시 데모 여부·데이터 출처·검증 한계를 함께 제시해 주세요.")
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
                       "localsim_comparison.csv", "text/csv", use_container_width=True)
with export2:
    st.download_button("↓ 결과 JSON", json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"),
                       "localsim_results.json", "application/json", use_container_width=True)
with export3:
    st.download_button("↓ 보고서 HTML", html_report(items, len(people), idea, demo, scenario_label),
                       "localsim_report.html", "text/html", use_container_width=True,
                       help="브라우저에서 열어 인쇄/파일로 저장할 수 있는 간단 리포트입니다.")

st.markdown('<div class="ls-footer">LOCAL SIMULATOR · TEAM 05 · 2026 해커톤<br>'
            '현재 프론트엔드는 계산 결과의 시각화 및 비교 도구입니다. 가상 시민 수·합성 설문·모델 계산값을 실제 유동인구, 방문객 수 또는 매출 예측치로 해석해서는 안 됩니다.</div>',
            unsafe_allow_html=True)
