# 노른자 최종 프론트엔드 — 통합 안내

이 브랜치는 2026-11-10 기준 `user24345/5` 원본 `main`의 Streamlit 앱을 바탕으로 **프론트엔드 변경만** 적용했습니다. 팀장님 엔진 및 팀원 데이터 파일은 변경하지 않았습니다.

## 변경 내용

- 서비스 화면 명칭 **노른자**, 노란색 주요 버튼/강조선
- 입력: 영업시간(선택 체크), 월세(원), 객단가(원), 홍보 예산(원), 기존 아이디어·후보 동 입력 유지
- 입력 조건 `norunja_scenario_input.json` 다운로드. 현 단계에서는 엔진을 호출하거나 결과를 재계산하지 않음
- 결과: `visitors_demand`, `competition_factor`, `daytime_share` 원본 필드 카드
- 결과: 12주 `weekly_visitors` 차트, `repromo` 비교, `breakeven_week`
- 결과: `channel_share` 집단별 비율, `scenarios` 홍보 채널 비교, `budget_plan.split` 예산 분배
- 결과: `hubs` 입소문 허브 카드
- 원본 파일에 신규 필드가 없으면 '자료 대기'. 임의 수치로 계산하지 않음
- 샘플 데이터에서만 체크할 수 있는 **최종 결과 화면 미리보기**. 예시 수치는 지도, 지역 순위, 결과 JSON, CSV, HTML 다운로드에 들어가지 않음
- `frontend/data_io.py`의 허용 확산 경로에 **동선·지인·검색** 추가

## 실행과 점검

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q frontend/tests
python -m streamlit run app.py
```

1. 사이드바에서 **샘플 데이터**를 선택합니다.
2. **최종 결과 화면 미리보기 · 예시 수치**를 체크합니다.
3. 시뮬레이션 결과 보기 버튼을 누르고 지도 아래쪽의 신규 차트와 카드를 확인합니다.
4. 미리보기 체크를 끄면 신규 결과 파일이 없는 차트가 '자료 대기' 상태가 되는지 확인합니다.
5. 실데이터는 엔진 결과·시민 ID 규격이 통합된 뒤에 점검합니다.

## 팀장님과 합의할 사항 / 미해결 사항

1. **실데이터 ID 불일치:** 2026-11-09에 제공된 서울 전체 `personas.csv`의 UUID ID와 과거 `edges.json` / `result_*.json`의 정수 ID는 일치하지 않습니다. 프론트에서 임의로 매핑하면 안 됩니다. 엔진 담당이 동일 ID 체계로 결과를 새로 생성하거나 명시적 매핑을 제공해야 합니다.
2. **영업시간 스키마:** 프론트는 입력 내보내기 JSON에 `business_hours: {"open":"10:00","close":"22:00"}`를 **제안 필드**로 내보냅니다. 엔진 측에서 정한 필드명과 의미를 확인해 주세요.
3. **엔진 호출 미연동:** '결과 보기'는 기존 JSON을 표시하는 동작입니다. 사용자 입력값을 바꾸어도 재시뮬레이션하지 않습니다. 엔진 실행/배포 흐름은 팀장님과 합의가 필요합니다.
4. **예산/손익 가정:** 시나리오 효과는 가정 기반 결과입니다. 월세와 객단가만으로 정확한 손익분기를 계산하지 못하므로 원가·고정비 가정이 추가로 필요합니다.
5. **새 결과 필드 공급:** `visitors_demand`, `competition_factor`, `daytime_share`, `weekly_visitors`, `channel_share`, `scenarios`, `budget_plan`, `hubs`, `breakeven_week`는 결과 JSON에 실제 들어오면 표시됩니다.
6. **공공데이터 추정값:** `dong_stats.csv`의 `is_estimated`는 자료 원본에서 추정된 동을 구분하는 신호입니다. 사용자의 판단에 영향을 주는 화면에는 향후 이를 별도 안내할 수 있습니다.

## 변경 파일

- `app.py`
- `frontend/final_features.py` (신규)
- `frontend/data_io.py` (허용 경로만 변경)
- `frontend/tests/test_final_features.py` (신규)

**주의:** 이 작업 브랜치를 기존 `main` 위에 덮어쓰기보다 Pull Request로 검토한 후 병합해 주세요.
