"""오픈 후 보정 (LocalSim)

가게를 연 뒤 사장님이 처음 몇 주의 실제 손님 수를 넣으면, 시뮬레이션 12주 곡선을 그 숫자에 맞게 고쳐서
남은 주를 다시 예측하고 손익분기·추가 홍보 시점을 갱신한다.

보정 방법 (설명하기 쉬운 두 숫자만 맞춤)
- 크기(alpha): 손님이 예측보다 전체적으로 몇 배 많거나 적은지
- 속도(beta): 소식이 예측보다 빨리(>1) 또는 느리게(<1) 퍼지는지. 곡선을 시간 축으로 늘이거나 줄임
실제 주별 손님과 '보정된 곡선'의 차이(제곱 오차)가 가장 작은 alpha, beta를 격자 탐색으로 찾는다.

실행 (저장소 맨 위에서)
    python engine/open_calibrate.py --dong 1144071000 --actual 25 48 70 88
        -> 앞 4주 실제 손님으로 보정, frontend/data/real/calibration_1144071000.json 저장
    python engine/open_calibrate.py --demo
        -> 후보 동마다 가상 '실제 손님'을 여러 번 만들어 앞 4주로 보정했을 때
           뒤 8주 예측 오차가 얼마나 줄어드는지 확인 (검증 흐름: 보정 검증)
"""
import argparse
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "frontend/data/real"
CANDIDATES = ["1144069000", "1144071000", "1144066000"]
ALPHAS = [round(0.3 + 0.05 * i, 2) for i in range(55)]   # 0.30 ~ 3.00
BETAS = [round(0.5 + 0.05 * i, 2) for i in range(21)]    # 0.50 ~ 1.50


def curve_at(pred, t):
    """예측 곡선 pred를 실수 시점 t(주)에서 읽기. 범위 밖은 마지막 두 주의 증감 비율로 연장"""
    n = len(pred)
    if t <= 0:
        return pred[0] * max(t + 1, 0)  # 0주 이전은 0으로 줄어듦
    if t <= n - 1:
        i = int(t)
        f = t - i
        return pred[i] * (1 - f) + pred[min(i + 1, n - 1)] * f
    ratio = pred[-1] / pred[-2] if n >= 2 and pred[-2] > 0 else 1.0
    return pred[-1] * ratio ** (t - (n - 1))


def corrected(pred, alpha, beta, weeks=None):
    weeks = weeks or len(pred)
    return [alpha * curve_at(pred, beta * t) for t in range(weeks)]


def fit(pred, actual):
    """실제 앞 k주에 가장 잘 맞는 (alpha, beta)"""
    k = len(actual)
    best = (float("inf"), 1.0, 1.0)
    for b in BETAS:
        base = [curve_at(pred, b * t) for t in range(k)]
        for a in ALPHAS:
            err = sum((a * x - y) ** 2 for x, y in zip(base, actual))
            if err < best[0]:
                best = (err, a, b)
    return best[1], best[2]


def breakeven(weekly, price, rent, w):
    if not price or not rent:
        return None
    fixed_week = (rent + w.get("other_fixed_monthly", 0)) / 4.345
    for t, n in enumerate(weekly):
        if n * price * w["gross_margin"] >= fixed_week:
            return t + 1
    return None


def repromo_week(weekly):
    """보정된 곡선에서 손님이 정점을 찍고 줄기 시작하는 주 = 추가 홍보 추천 시점"""
    peak = max(range(len(weekly)), key=lambda i: weekly[i])
    for t in range(peak + 1, len(weekly)):
        if weekly[t] < weekly[t - 1]:
            return t + 1
    return None


def recalibrate(result, actual, w):
    """result 파일 하나 + 실제 앞 몇 주 손님 -> 보정 결과"""
    pred = result["weekly_visitors"]
    a, b = fit(pred, actual)
    corr = corrected(pred, a, b)
    actual = [int(round(x)) for x in actual]
    merged = actual + [round(x) for x in corr[len(actual):]]  # 이미 지난 주는 실제 값 그대로
    asm = result.get("assumptions", {})
    price, rent = asm.get("avg_price"), asm.get("rent")
    return {
        "dong_code": result["dong_code"], "dong": result["dong"],
        "observed_weeks": len(actual), "actual": list(actual),
        "predicted": pred, "corrected": merged,
        "alpha": a, "beta": b,
        "summary": (f"실제 손님이 예측의 {a:.2f}배, 소식이 퍼지는 속도는 예측의 {b:.2f}배로 보여 "
                    f"남은 주 예측을 고쳤어요"),
        "breakeven_before": breakeven(pred, price, rent, w),
        "breakeven_after": breakeven(merged, price, rent, w),
        "repromo_week_after": repromo_week(merged),
    }


def demo(result, w, trials=50, observe=4, seed=0):
    """가상 '실제 손님'을 만들어 앞 observe주로 보정 -> 뒤 주 예측 오차가 줄어드는지"""
    pred = result["weekly_visitors"]
    rng = random.Random(seed)
    before, after, examples = [], [], []
    for k in range(trials):
        true_a = rng.uniform(0.6, 1.6)
        true_b = rng.uniform(0.7, 1.3)
        truth = [max(0.0, x * rng.gauss(1, 0.08)) for x in corrected(pred, true_a, true_b)]
        obs = [round(x) for x in truth[:observe]]
        a, b = fit(pred, obs)
        fix = corrected(pred, a, b)
        rest = range(observe, len(pred))
        mae_b = statistics.mean(abs(pred[t] - truth[t]) for t in rest)
        mae_a = statistics.mean(abs(fix[t] - truth[t]) for t in rest)
        before.append(mae_b)
        after.append(mae_a)
        if k < 3:
            examples.append({"true_alpha": round(true_a, 2), "true_beta": round(true_b, 2),
                             "fit_alpha": a, "fit_beta": b, "actual": [round(x) for x in truth],
                             "predicted": pred, "corrected": [round(x) for x in fix],
                             "mae_before": round(mae_b, 1), "mae_after": round(mae_a, 1)})
    mb, ma = statistics.mean(before), statistics.mean(after)
    return {"dong_code": result["dong_code"], "dong": result["dong"], "trials": trials,
            "observed_weeks": observe, "mae_before": round(mb, 1), "mae_after": round(ma, 1),
            "error_reduction": round(1 - ma / mb, 3) if mb else None,
            "improved_share": round(sum(a < b for a, b in zip(after, before)) / trials, 3),
            "examples": examples}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dong", help="보정할 동 코드")
    ap.add_argument("--actual", nargs="*", type=float, help="오픈 후 1주차부터 실제 주별 손님 수")
    ap.add_argument("--demo", action="store_true", help="가상 실제 손님으로 보정 효과 확인")
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--observe", type=int, default=4)
    args = ap.parse_args()
    w = json.load(open(ROOT / "config/weights.json", encoding="utf-8"))

    if args.demo:
        rows = []
        for code in CANDIDATES:
            path = DATA / f"result_{code}.json"
            if not path.exists():
                continue
            res = demo(json.load(open(path, encoding="utf-8")), w, args.trials, args.observe)
            json.dump(res, open(DATA / f"calibration_demo_{code}.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            rows.append(res)
            print(f"{res['dong']}: 앞 {res['observed_weeks']}주로 보정 -> 뒤 주 평균 오차 "
                  f"{res['mae_before']}명 -> {res['mae_after']}명 ({res['error_reduction']:.0%} 감소, "
                  f"{res['trials']}번 중 {res['improved_share']:.0%} 개선)")
        return

    if not args.dong or not args.actual:
        raise SystemExit("--dong 과 --actual 을 넣거나 --demo 로 실행하세요")
    res = recalibrate(json.load(open(DATA / f"result_{args.dong}.json", encoding="utf-8")), args.actual, w)
    json.dump(res, open(DATA / f"calibration_{args.dong}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{res['dong']}: {res['summary']}")
    print(f"  예측 {res['predicted']}")
    print(f"  보정 {res['corrected']}")
    print(f"  손익분기 {res['breakeven_before'] or '-'} -> {res['breakeven_after'] or '-'}주차, "
          f"추가 홍보 추천 {res['repromo_week_after'] or '-'}주차")


if __name__ == "__main__":
    main()
