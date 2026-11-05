# 5팀 C 현재 진행 상황 (11/05 13시 샘플 제출용)

**현재 구현**: Streamlit 앱, 아이디어 입력/후보동 선택, 가상 시민 지도, 단계별 확산 재생, 후보 지역 비교, 정체 집단/경로 시각화, CSV/JSON/HTML 다운로드.

**13시 가짜 데이터 시연**: `frontend/data/demo/personas.csv`, `frontend/data/demo/result_*.json`, `frontend/data/demo/reactions.json` 으로 웹에서 화면 시연. 실데이터 및 실제 예측이 아님. 샘플 150명.

**실데이터/엔진 미연동**: ① B의 `personas.csv`, `dongs.geojson` ② A의 `reactions.json` ③ PM의 `result_{dong_code}.json`을 받아 **연결/검증 예정**. 현재 앱에서 창업 아이디어 문장을 변경해도 재시뮬레이션되지는 않음.

**기술 협의**: 팀장이 만든 폴더(reactions/, data_prep/, engine/)에서 실제 파일을 어떻게 프론트로 전달할지 결정 필요. 현재는 `frontend/data/real`로 복사하면 결과를 로딩할 수 있음.
