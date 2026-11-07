"""Syntitan 설문 결과 CSV들 -> reactions.json
실행 (저장소 맨 위에서):
    python reactions/convert_reactions.py
    python reactions/convert_reactions.py --region 서울   (마포구 응답이 너무 적을 때)
입력: reactions/syntitan_output/*.csv   출력: frontend/data/real/reactions.json
"""
import argparse, json, re
from collections import Counter
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
# Syntitan 설문 q4 보기 순서와 반드시 같게!
COMMUNITY_ORDER = ["에타", "맘카페", "당근", "인스타", "없음"]
# 거절 이유 분류 (위에서부터 먼저 걸리는 것)
REASON_KEYWORDS = [
    ("가격", ["가격", "비싸", "비용", "지출", "돈", "소득", "용돈", "부담돼", "외식비", "가성비"]),
    ("시간", ["시간", "퇴근", "바쁘", "바빠", "일정", "영업시간", "불규칙", "여유가 없"]),
    ("거리", ["멀", "거리", "교통", "주차", "이동", "버스", "걸음", "걷"]),
    ("분위기", ["분위기", "혼자", "좌석", "대기", "시끄", "낯선"]),
    ("메뉴", ["메뉴", "맛", "양이", "디저트", "음료"]),
    ("관심없음", ["관심", "필요 없", "굳이", "동기"]),
]
AGES = ["20대이하", "30대", "40대", "50대이상"]


def classify(text):
    t = str(text)
    for label, keys in REASON_KEYWORDS:
        if any(k in t for k in keys):
            return label
    return "기타"


def to_group(r):
    a = int(r["age"])
    band = "20대이하" if a < 30 else "30대" if a < 40 else "40대" if a < 50 else "50대이상"
    unemployed = str(r.get("economic_activity", "")).strip() in ("일하지 않았음", "", "nan")
    if unemployed:
        if a <= 29: job = "학생"
        elif a <= 64 and str(r.get("marital_status", "")) == "배우자 있음": job = "주부"
        else: job = "기타"
    else:
        job = "자영업" if "자영" in str(r.get("employment_position", "")) else "직장인"
    return f"{band}_{job}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="reactions/syntitan_output")
    ap.add_argument("--out", default="frontend/data/real/reactions.json")
    ap.add_argument("--region", default="마포구", help="마포구 / 서울 / 전체")
    args = ap.parse_args()

    files = sorted((ROOT / args.input).glob("*.csv"))
    df = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in files], ignore_index=True)
    print(f"결과 파일 {len(files)}개, 응답 {len(df)}명")
    print("지역 분포(상위):", df["region_sigungu"].value_counts().head(5).to_dict())

    if args.region == "마포구":
        df = df[df["region_sigungu"] == "마포구"]
    elif args.region == "서울":
        df = df[df["region_sido"].astype(str) == "11"]
    print(f"지역 필터({args.region}) 후 {len(df)}명")

    df["group"] = df.apply(to_group, axis=1)
    df["reason_type"] = df["q3"].apply(classify)
    def to_comm(v):
        t = str(v).strip()
        for c in COMMUNITY_ORDER:          # 보기 이름 그대로 온 경우
            if c in t:
                return c
        m = re.search(r"(\d+)", t)          # answer-3 같은 번호로 온 경우
        if m and 1 <= int(m.group(1)) <= len(COMMUNITY_ORDER):
            return COMMUNITY_ORDER[int(m.group(1)) - 1]
        return None

    def picked(v):
        t = str(v).strip().lower()
        return t not in ("", "nan", "none", "0", "0.0", "false", "n", "no")

    multi_cols = [c for c in df.columns if c.startswith("q4.answer-")]

    def row_comms(r):
        out = []
        # 복수 선택형 (q4.answer-1 ~ 5 열로 나뉜 경우)
        for c in multi_cols:
            n = int(c.split("-")[-1])
            if 1 <= n <= len(COMMUNITY_ORDER) and picked(r[c]):
                out.append(COMMUNITY_ORDER[n - 1])
        # 단일 선택형 (q4 한 열)
        if not out and "q4" in df.columns:
            c = to_comm(r["q4"])
            if c:
                out.append(c)
        return out

    if multi_cols:
        vals = pd.unique(df[multi_cols].astype(str).values.ravel())[:8]
        print("복수선택 열에 들어 있는 값 예시:", list(vals))
    df["community"] = df.apply(row_comms, axis=1)
    no_comm = (df["community"].str.len() == 0).sum()
    print(f"커뮤니티 형식: 복수선택 열 {len(multi_cols)}개 / 단일 q4 열 {'있음' if 'q4' in df.columns else '없음'}")
    if no_comm:
        print(f"[참고] 커뮤니티 답이 없는 응답 {no_comm}개 -> 커뮤니티 계산에서 제외")
    for q in ("q1", "q2"):
        df[q] = pd.to_numeric(df[q], errors="coerce")
    df = df.dropna(subset=["q1", "q2"])

    rows = {}
    for g, sub in df.groupby("group"):
        top_reason = sub["reason_type"].value_counts().idxmax()
        has = sub[sub["community"].str.len() > 0]
        if len(has):
            rate = {c: has["community"].apply(lambda l: c in l).mean() for c in COMMUNITY_ORDER}
            chosen = [c for c in COMMUNITY_ORDER if rate[c] >= 0.25] or [max(rate, key=rate.get)]
        else:
            chosen = ["없음"]
        rows[g] = {"group": g,
                   "interest": round(float(sub["q1"].mean()), 2),
                   "share": round(float(sub["q2"].mean()), 2),
                   "reason_type": top_reason,
                   "reason_text": str(sub.loc[sub["reason_type"] == top_reason, "q3"].iloc[0]),
                   "community": chosen,
                   "_n": len(sub)}

    # 페르소나의 15개 집단 전부 채우기 (응답 없는 집단은 같은 나이대 평균, 그것도 없으면 전체 평균)
    need = sorted(pd.read_csv(ROOT / "frontend/data/real/personas.csv")["group"].unique())
    out = []
    for g in need:
        if g in rows:
            r = rows[g]
        else:
            band = g.split("_")[0]
            pool = [v for k, v in rows.items() if k.startswith(band + "_")] or list(rows.values())
            r = {"group": g,
                 "interest": round(sum(v["interest"] for v in pool) / len(pool), 2),
                 "share": round(sum(v["share"] for v in pool) / len(pool), 2),
                 "reason_type": Counter(v["reason_type"] for v in pool).most_common(1)[0][0],
                 "reason_text": pool[0]["reason_text"],
                 "community": pool[0]["community"], "_n": 0}
            print(f"[채움] {g}: 응답 없음 -> {band if pool is not list(rows.values()) else '전체'} 평균으로")
        out.append(r)

    print("\n집단 | 응답수 | 관심 | 전달 | 이유 | 커뮤니티")
    for r in out:
        print(f"{r['group']} | {r['_n']} | {r['interest']} | {r['share']} | {r['reason_type']} | {r['community']}")
    with open(ROOT / args.out, "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in r.items() if k != "_n"} for r in out], f, ensure_ascii=False, indent=2)
    print(f"\n저장: {args.out} ({len(out)}개 집단)")


if __name__ == "__main__":
    main()
