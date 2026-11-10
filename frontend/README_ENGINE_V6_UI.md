# 노른자 프론트엔드 ↔ 팀 엔진 v6 인수인계

기준: 팀 저장소 `user24345/5`, 2026-11-10 확인. **프로젝트 원본 `engine/`, `config/`, `frontend/data/`는 수정하지 않음.**

## 화면과 결과 필드 연결표

| 화면 / 항목 | 읽는 값 | 처리 방식 |
|---|---|---|
| 창업 입력 | `scenario.json` 입력 규격: `open_hours`, `open_days`, `avg_price`, `rent` | 화면 입력값을 별도 **엔진용** `scenario.json`으로 다운로드. 앱 자체는 엔진을 재실행하지 않음 |
| 입력 메모 | 아이디어, 타깃, 가격대, 홍보 예산, 후보 동 | **메모 JSON**으로 별도 다운로드. `budget`은 현재 엔진 v6 `scenario.json`에서 계산에 사용하지 않음 |
| 후보 지역 비교 / 지도 | `steps`, `visitors`, `dong_code`, `population_in_radius`, `is_estimated` | 기존 지도와 지역 비교 유지. 페르소나 ID와 결과 ID가 불일치하면 지도만 중단하고 숫자 결과는 읽기 전용으로 표시 |
| 3개 지역의 12주 곡선 | 각 `result_*.json`의 `weekly_visitors` | 세 후보 지역을 **하나의 선 그래프**에 표시. 각 지역은 독립 모델 계산값이며 합산하지 않음 |
| 3달째 월 고객 수 | `monthly_customers` | `최근 4주 손님 합계`로 표시. 엔진 원본 결과 |
| 손익분기 주차 | `breakeven_week` | `null`은 `판정 정보 없음`으로 표시. 임의 계산 금지 |
| 홍보 전/후 재실험 | `repromo.week`, `repromo.with`, `repromo.without`, `repromo.gain` | 선택 지역의 12주 두 곡선 겹쳐서 표시 |
| 전체 유입 경로 | `channel_total` | 전체 경로 비율 그래프 (분율 ×100%) |
| 집단별 경로 | `channel_share` | 연령×직업 집단별 누적 막대 그래프. 전체 유입 비율과 혼동하지 않음 |
| 입소문 허브 5명 | `hubs[].id`, `group`, `dong`, `reach`, `direct`, `week`, `community` | 5개 카드. 실제 사람이 아니라 가상 시민 |
| 방문 수요·경쟁·낮 비중 | `visitors_demand`, `competition_factor`, `daytime_share` | 엔진 원본값 표시. 경쟁 계수는 경쟁 강도가 아니라 **방문 수요에 곱하는 보정 계수** |
| 모델 수치 범위 | `visitors_range`, `runs` | 반복 시드 결과 범위 및 반복 횟수 표시 |
| 가정값 | `assumptions.avg_price`, `rent`, `gross_margin`, `other_fixed_monthly`, `customer_scale` | 원본 숫자와 `null`을 구분하여 표시 |
| 유동인구 | `dong_stats.csv`: `flow_06_11` 등, `flow_age_*`, `flow_weekday`, `flow_weekend`, `is_estimated` | 기존 공공데이터 읽기 / 추정 데이터 안내 |
| 홍보 단가 원본 | `ad_costs.json`: `channel`, `tier`, `unit`, `cost_per_unit`, `cost_min`, `cost_max`, `is_estimated`, `default`, `note` | 원본 조회 표. **효과·ROI는 단가만으로 계산하지 않음** |
| 미래 홍보 예산 시뮬레이션 | `scenarios`, `budget_plan` | v6 결과가 `null`이면 준비 중. 값이 들어오면 기존 차트 표시 |
| AI 진단 | `diagnosis` 또는 `diagnosis_{dong_code}.json` | 없으면 준비 중, 기존과 동일 |

## 엔진 입력 규격 — 반드시 구분

v6의 `engine/simulate.py`는 `frontend/data/real/scenario.json`에서 다음 키를 실제로 읽음:

```json
{
  "open_hours": [10, 22],
  "open_days": ["월", "화", "수", "목", "금", "토"],
  "avg_price": 9000,
  "rent": 2800000
}
```

- `open_hours`: **정수 시** `[시작, 끝]`, 24시간 단위. 예를 들어 오전 10시~오후 10시는 `[10,22]`. 현재 엔진 `overlap` 계산상 **자정을 넘기는 시간**과 30분 단위 입력은 별도 개발 필요.
- `open_days`: `월`, `화`, `수`, `목`, `금`, `토`, `일`의 목록. 선택하지 않으면 미설정(`null`) → 엔진 기본 설정 동작.
- `rent`: 월 임대료 **총액(원)**을 가정하는 엔진 입력. 지은님이 답한 `3.3㎡당 임대료` 자료는 매장 면적과 환산 전에는 그대로 **월세 총액으로 넣으면 안 됨**.
- `avg_price`: 고객 1명당 가정 객단가(원).
- **홍보 예산 `budget`**: 현재 엔진 v6에서 직접 사용하지 않으므로 별도 메모 JSON에 저장. 추후 PM 규격 확정 후 연결.
- 위 파일을 다운로드하더라도 **기존 결과는 자동 재계산되지 않음.** PM이 엔진을 실행해야 결과에 반영됨.

## 실제 데이터와 기존 ZIP 차이

- 이 ZIP은 `2026-11-09`의 크림 UI 프로젝트를 바탕으로 새 프론트엔드 화면을 추가한 것이므로 **내장된 `frontend/data/real/`은 최신 v6 결과가 아님**.
- **가장 권장하는 실행**: 함께 제공한 `START_LATEST_WITH_V6_UI.cmd`로 팀 GitHub 최신 `main`을 별도 폴더에 **새로 내려받고 프론트엔드 변경만 복사하여 로컬 실행**. GitHub 업로드는 일어나지 않음.
- 엔진 결과가 실제로 존재하면 `샘플 데이터`가 아닌 **팀 실데이터** 선택.
- `personas.csv`의 UUID와 과거 결과의 정수 ID 불일치가 남아 있으면 **지도는 비활성화**하고 분석 결과만 읽기 전용으로 표시. 서로 다른 시민 ID를 임의로 연결하지 않음.
- `result_*.json` 세 개만 먼저 확인하려면 **파일 업로드(복수)**로 가져와 새 지표와 세 지역 주별 곡선을 임시 확인 가능. 업로드한 값은 기존 지도/CSV/다운로드 결과에 합치지 않음.

## 테스트

```
py -m pip install -r requirements.txt
py -m pip install pytest
py -m pytest -q frontend/tests
py -m streamlit run app.py
```

## 배포/검토

검토 후 GitHub Desktop의 `Changes`에서 **`app.py`, `frontend/final_features.py`, `frontend/v6_display.py`, `frontend/tests/`, `frontend/README_ENGINE_V6_UI.md`만 비교**할 것. 팀원 엔진/설문/공공데이터/설정 파일은 이번 패치 대상이 아님. 승인 전에는 커밋·푸시하지 않아도 됨.
