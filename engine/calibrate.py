"""실제 손님 수 보정 (customer_scale 계산)

'평범한 동네에 새 카페를 내면, 3달째에는 그 동네 평범한 카페의 calibration_target_ratio 수준 손님이 온다'를 기준으로
모델 단위 방문 수를 실제 월 손님 수로 바꾸는 배율을 구해 config/weights.json의 customer_scale에 저장한다.

실행 (먼저 전체 동 결과가 있어야 함):
    python engine/simulate.py --all-dongs --out outputs/validation_run
    python engine/calibrate.py
"""
import csv
import glob
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W = ROOT / "config" / "weights.json"

w = json.load(open(W, encoding="utf-8"))
with open(ROOT / "frontend/data/real/dong_stats.csv", encoding="utf-8-sig") as f:
    stats = {r["dong_code"]: r for r in csv.DictReader(f)}

per_store, model_month = [], []
for path in glob.glob(str(ROOT / "outputs/validation_run/result_*.json")):
    r = json.load(open(path, encoding="utf-8"))
    st = stats.get(r["dong_code"])
    if not st or r.get("is_estimated") or not r.get("weekly_visits_model"):
        continue
    try:
        tx, stores = float(st["cafe_monthly_transactions_avg"]), float(st["store_count"])
    except (KeyError, ValueError):
        continue
    if stores < 3 or tx < 1000:  # 표본이 너무 작은 동 제외
        continue
    per_store.append(tx / stores)
    model_month.append(sum(r["weekly_visits_model"][-4:]))

if not per_store:
    raise SystemExit("보정할 결과가 없습니다. 먼저 --all-dongs 결과를 만들어 주세요.")
target = statistics.median(per_store) * w.get("calibration_target_ratio", 0.7)
scale = target / statistics.median(model_month)
w["customer_scale"] = round(scale, 2)
json.dump(w, open(W, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"{len(per_store)}개 동 기준 / 카페 한 곳 월 결제 중앙값 {statistics.median(per_store):,.0f}건 "
      f"x {w.get('calibration_target_ratio', 0.7)} = 목표 {target:,.0f}건")
print(f"모델 3달째 월 방문 중앙값 {statistics.median(model_month):.1f} -> customer_scale = {scale:.2f} (weights.json에 저장)")
