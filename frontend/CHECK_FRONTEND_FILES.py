"""Run `python CHECK_TEAM_FILES.py` after placing team files in data/real.
No API key and no Streamlit web server are needed to validate local files.
"""
from pathlib import Path
root = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(root.parent))
from frontend.data_io import load_dataset, DataContractError
for label in ("demo", "real"):
    folder = root / "data" / label
    if label == "real" and not (folder / "personas.csv").exists():
        print("[대기] 실데이터 파일이 아직 없습니다: frontend/data/real/personas.csv")
        continue
    try:
        data = load_dataset(folder)
        print(f"[통과] {label}: 시민 {len(data['persons'])}명 / 입지 결과 {len(data['results'])}개 / 반응 집단 {len(data['reactions'])}개")
        if label == "real":
            print("[참고] 스키마 검사 통과는 시뮬레이션 정확성이나 데이터의 실제 출처를 증명하지 않습니다.")
    except DataContractError as e:
        print(f"[오류] {label}: {e}")
        raise SystemExit(1)
print("확인 끝. 외부 API는 호출하지 않았습니다.")
