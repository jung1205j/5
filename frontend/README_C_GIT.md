# LocalSim C 담당 GitHub 제출본 — 2026-11-05

## 무엇이 포함되어 있나

- `app.py` : 팀 저장소 **최상위**에 복사하는 웹 앱 시작 파일 (C 담당)
- `frontend/data_io.py` : 합의된 CSV/JSON 형식을 읽는 코드
- `frontend/animated_map.py` : API 키 없는 OpenStreetMap 지도 및 확산 단계 애니메이션
- `frontend/analysis_helpers.py` : 후보지 비교, 진단/리포트 표시
- `frontend/data/demo/` : **시연용 가짜 데이터**, 실제 시민/상권 결과가 아님
- `frontend/data/real/` : 팀원 실데이터 로컬 테스트 위치. **공개 GitHub에 자동 업로드되지 않도록 .gitignore** 설정
- `frontend/CHECK_FRONTEND_FILES.py` : CSV/JSON 구조 점검
- `frontend/requirements_frontend.txt` : Streamlit 등 프론트 설치 의존성
- `frontend/START_C_WINDOWS.bat` : Windows에서 더블클릭해 앱 실행
- `frontend/tests/` : C 기능 단위 테스트

**주의**: C 담당의 제출물은 프론트 코드+데모이며, 실제 Syntitan/확산 엔진/검증 결과를 완료한 것이 아닙니다.

## 팀 저장소에 올리기 — 핵심 순서

1. 팀 GitHub 저장소를 내 PC에 clone 한 후 그 폴더로 이동한다. 이미 clone 했다면 먼저 `git pull`.
2. 이 ZIP을 압축 해제하고, 내용 중 **`app.py`와 `frontend/` 폴더만** 팀 저장소 최상위에 복사한다. `engine/`, `reactions/`, `data_prep/`, `validation/`, `config/`, `tests/`는 건드리지 않는다.
3. 팀 저장소 `app.py`가 팀장님 다른 코드로 이미 변경됐다면 덮어쓰지 말고 차이를 확인한 후 합의한다.
4. `git status`로 변경 대상 확인. `git add app.py frontend/`, `git commit -m "Add LocalSim frontend demo and map"`, `git push`.
5. 팀 저장소의 `requirements.txt`는 덮어쓰지 않는다. Streamlit/Pandas/PyDeck/Plotly 버전은 팀장과 합쳐야 한다.

## 실행

`frontend/START_C_WINDOWS.bat`를 더블클릭한 뒤 콘솔에 보이는 `http://localhost:8501` 등 Local URL 접속. 실행 중 콘솔 창을 닫지 않는다.

## 스키마 검사

```powershell
frontend\.venv\Scripts\python.exe frontend\CHECK_FRONTEND_FILES.py
```

이 검사에서 샘플은 통과해야 함. 실제 팀 데이터는 `frontend/data/real`에 **복사해서** 테스트할 수 있음. PM/B/A 폴더의 경로와 직접 자동 연동되는 것은 아님; 실데이터 경로·API는 최종 통합 전에 합의 필요.

## 팀 스키마

- `personas.csv`: `id,dong_code,dong,age,gender,job,lat,lng,group`
- `reactions.json`: `group,interest,share,reason_type,reason_text,community`
- `result_{dong_code}.json`: `dong_code,dong,seed,steps,visitors,stopped_at`
- `steps`: 각 단계에 **새로 노출된** 시민 ID들, 중복 없음
- 모든 컬럼/키는 영문 소문자 / underscore, UTF-8; `dong_code`는 문자열
- 샘플의 `DEMO_*` 코드는 정식 행정동 코드가 **아님**.
- API 키는 절대 코드, 예시 데이터, 공개 저장소에 넣지 말 것.
