"""LocalSim 확산 엔진
동네 + 커뮤니티 관계망, 유동인구·직장인구(낮 방문자), 경쟁 점포 수, 확산(1단계=1주), 방문 계산,
12주 방문객 곡선(관심 식음 + 재방문), 추가 홍보 타이밍, 손익분기, 시드 여러 개 평균

실행 (저장소 맨 위에서):
    python engine/simulate.py                                   # 후보 3개 동 (프론트용)
    python engine/simulate.py --all-dongs --out outputs/validation_run   # 전체 동 (검증용)
    python engine/simulate.py --dongs 1144071000 1168064000      # 원하는 동만

입력: {data}/personas.csv, reactions.json, (있으면) dongs.geojson, dong_stats.csv
출력: {out}/result_{동코드}.json, (후보 모드일 때) {out}/edges.json
가중치: config/weights.json

서울 전체 시민 중 '가게 반경 sim_radius_m 안에 사는 사람'만 골라 동마다 따로 계산한다.
"""
import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CANDIDATES = {"1144069000": "망원1동", "1144071000": "연남동", "1144066000": "서교동"}


# ---------- 데이터 읽기 ----------
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_personas(folder):
    with open(folder / "personas.csv", encoding="utf-8-sig") as f:
        return [{"id": int(r["id"]), "dong_code": str(r["dong_code"]), "dong": r["dong"],
                 "group": r["group"], "lat": float(r["lat"]), "lng": float(r["lng"])}
                for r in csv.DictReader(f)]


def load_reactions(folder):
    path = folder / "reactions.json"
    return {r["group"]: r for r in load_json(path)} if path.exists() else {}


def load_dong_stats(folder):
    """동별 유동인구·직장인구·점포 수. 파일이 없으면 빈 dict (기존 방식으로 동작)"""
    path = folder / "dong_stats.csv"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig") as f:
        return {str(r["dong_code"]): {"floating_pop": float(r["floating_pop"]),
                                      "worker_pop": float(r["worker_pop"]),
                                      "store_count": float(r["store_count"]),
                                      "is_estimated": int(float(r.get("is_estimated", 0) or 0)),
                                      "avg_price": implied_price(r)}
                for r in csv.DictReader(f)}


def implied_price(r, min_tx=1000):
    """동 평균 객단가 = 카페 월매출 / 월 결제 건수 (결제가 너무 적은 동은 None)"""
    try:
        sales, tx = float(r["cafe_monthly_sales_avg_krw"]), float(r["cafe_monthly_transactions_avg"])
    except (KeyError, TypeError, ValueError):
        return None
    return sales / tx if tx >= min_tx else None


def to01(score):
    """1~5점 -> 0~1"""
    return max(0.0, min(1.0, (float(score) - 1) / 4))


def distance_m(lat1, lng1, lat2, lng2):
    """서울 범위에서는 평면 근사로 충분"""
    dy = (lat1 - lat2) * 111_000
    dx = (lng1 - lng2) * 111_000 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def make_grid(people, radius_m):
    cell = radius_m / 111_000
    grid = defaultdict(list)
    for p in people:
        grid[(int(p["lat"] // cell), int(p["lng"] // cell))].append(p)
    return grid, cell


def near(p, grid, cell, radius_m):
    """p 반경 radius_m 안 사람들 (자기 자신 제외) -> [(거리, 사람)]"""
    ci, cj = int(p["lat"] // cell), int(p["lng"] // cell)
    out = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for q in grid.get((ci + di, cj + dj), ()):
                if q["id"] != p["id"]:
                    d = distance_m(p["lat"], p["lng"], q["lat"], q["lng"])
                    if d <= radius_m:
                        out.append((d, q))
    return out


# ---------- 관계망 ----------
def build_neighbor_edges(people, radius_m, max_neighbors):
    """서로 radius_m 안에 사는 사람끼리 연결 (사람당 가까운 순 최대 max_neighbors명)"""
    grid, cell = make_grid(people, radius_m)
    edges = set()
    for p in people:
        cands = sorted(near(p, grid, cell, radius_m), key=lambda x: (x[0], x[1]["id"]))
        for _, q in cands[:max_neighbors]:
            edges.add((min(p["id"], q["id"]), max(p["id"], q["id"])))
    return [{"from": a, "to": b, "type": "동네"} for a, b in sorted(edges)]


def build_community_edges(people, reactions, links_per_person, radius_by_community, seed):
    """같은 커뮤니티 이용자끼리 사람당 무작위 links_per_person명과 연결.
    radius_by_community에 반경이 있는 커뮤니티(예: 당근)는 그 거리 안 회원끼리만."""
    rng = random.Random(f"community-{seed}")
    members = defaultdict(list)
    for p in people:
        for c in reactions.get(p["group"], {}).get("community", []):
            if c != "없음":
                members[c].append(p)

    edges = set()
    for c in sorted(members):
        pool = sorted(members[c], key=lambda p: p["id"])
        radius = radius_by_community.get(c)
        if radius:
            grid, cell = make_grid(pool, radius)
        for p in pool:
            if radius:
                cand = sorted((q for _, q in near(p, grid, cell, radius)), key=lambda q: q["id"])
                picks = rng.sample(cand, min(links_per_person, len(cand)))
            else:
                k = min(links_per_person, len(pool) - 1)
                picks, tried = [], set()
                while len(picks) < k:
                    q = pool[rng.randrange(len(pool))]
                    if q["id"] != p["id"] and q["id"] not in tried:
                        tried.add(q["id"])
                        picks.append(q)
            for q in picks:
                a, b = sorted((p["id"], q["id"]))
                edges.add((a, b, c))
    return [{"from": a, "to": b, "type": t} for a, b, t in sorted(edges)]


# ---------- 가게 위치 ----------
def store_point(dong_code, people, geo):
    """가게 위치 = 후보 동의 중심점 (경계 파일 우선, 없으면 그 동 주민 평균 좌표)"""
    if geo:
        for feat in geo.get("features", []):
            if str(feat["properties"].get("adm_cd2")) == dong_code:
                coords = feat["geometry"]["coordinates"]
                ring = coords[0][0] if feat["geometry"]["type"] == "MultiPolygon" else coords[0]
                return (sum(c[1] for c in ring) / len(ring), sum(c[0] for c in ring) / len(ring))
    local = [p for p in people if p["dong_code"] == dong_code] or people
    return (sum(p["lat"] for p in local) / len(local), sum(p["lng"] for p in local) / len(local))


def local_people(dong_code, people, geo, radius_m):
    """가게 반경 radius_m 안에 사는 시민 + 그 동 주민 전원"""
    slat, slng = store_point(dong_code, people, geo)
    return [p for p in people
            if p["dong_code"] == dong_code or distance_m(p["lat"], p["lng"], slat, slng) <= radius_m]


# ---------- 확산 ----------
def spread(people, adj, seeds, share, interest, w, rng, by_id, extra_at=None):
    """한 주에 steps_per_week 단계. 새로 들은 사람은 연결된 사람마다 한 번씩 전할 기회.
    extra_at={단계: [id,...]} 이면 그 단계에 추가 홍보로 소식을 직접 들은 사람을 더함.
    반환: steps(단계별 새로 들은 id), heard_week{id: 주차}, fails"""
    informed = set(seeds)
    heard_week = {i: 0 for i in seeds}
    steps = [sorted(seeds)]
    fails = Counter()
    frontier = sorted(seeds)
    scale = w.get("transmission_scale", 1.0)
    extra_at = extra_at or {}
    spw = w.get("steps_per_week", 1)
    max_steps = w["horizon_weeks"] * spw
    while len(steps) < max_steps:
        step = len(steps)
        new = []
        for s in frontier:
            for r, path in sorted(adj[s]):
                if r in informed:
                    continue
                if rng.random() < scale * share[s] * interest[r] * w["path_weight"][path]:
                    informed.add(r)
                    new.append(r)
                else:
                    fails[(by_id[r]["group"], path)] += 1
        for r in extra_at.get(step, []):
            if r not in informed:
                informed.add(r)
                new.append(r)
        if not new and not any(k > step for k in extra_at):
            break
        new = sorted(set(new))
        for r in new:
            heard_week[r] = step // spw
        steps.append(new)
        frontier = new
    return steps, heard_week, fails


def weekly_visits(heard_week, visit_prob, revisit, w):
    """주별 방문 (모델 단위, 기댓값)
    - 첫 방문: 소식을 들은 주부터 관심이 매주 interest_decay 비율로 식으며 나눠서 방문 (합 = visit_prob)
    - 재방문: 첫 방문한 사람이 이후 매주 revisit 확률로 다시 오고, 그 확률도 revisit_retention 비율로 줄어듦"""
    weeks = w["horizon_weeks"]
    d = w["interest_decay"]
    first = [0.0] * weeks
    repeat = [0.0] * weeks
    for i, h in heard_week.items():
        v = visit_prob.get(i, 0.0)
        if v <= 0 or h >= weeks:
            continue
        r0 = revisit.get(i, 0.0)
        for t in range(h, weeks):
            f = v * (1 - d) * d ** (t - h)
            first[t] += f
            for u in range(t + 1, weeks):  # 그 주에 처음 온 사람들의 이후 재방문
                repeat[u] += f * r0 * w["revisit_retention"] ** (u - t - 1)
    return [a + b for a, b in zip(first, repeat)], first


def breakeven(weekly_real, price, rent, w):
    """주간 공헌이익(매출 × 마진율) >= 주간 고정비(월세 + 기타 고정비)가 되는 첫 주 (1주차부터 셈)"""
    if not price or not rent:
        return None
    fixed_week = (rent + w.get("other_fixed_monthly", 0)) / 4.345
    for t, n in enumerate(weekly_real):
        if n * price * w["gross_margin"] >= fixed_week:
            return t + 1
    return None


def stall_week(heard_week, w):
    """주별 새로 듣는 사람 수가 정점 이후 정점의 repromo_trigger 비율 아래로 처음 떨어지는 주.
    12주 안에 안 떨어지면 정점 다음 주 (그래도 끝까지 가면 horizon의 절반)"""
    weeks = w["horizon_weeks"]
    counts = [0] * weeks
    for h in heard_week.values():
        if 0 < h < weeks:
            counts[h] += 1
    peak = max(range(1, weeks), key=lambda i: (counts[i], -i))
    for i in range(peak + 1, weeks):
        if counts[i] < w["repromo_trigger"] * counts[peak]:
            return i
    return min(peak + 1, weeks - 2) if counts[peak] else weeks // 2


def simulate(dong_code, dong, people, edges, reactions, geo, w, seed, stats=None, scenario=None, runs=1):
    by_id = {p["id"]: p for p in people}
    st = (stats or {}).get(dong_code)
    sc = scenario or {}

    # 반응 없는 집단은 무관심(0) -> 결과가 낙관적으로 안 나오게
    interest = {p["id"]: to01(reactions[p["group"]]["interest"]) if p["group"] in reactions else 0.0 for p in people}
    share = {p["id"]: to01(reactions[p["group"]]["share"]) if p["group"] in reactions else 0.0 for p in people}
    revisit = {p["id"]: to01(reactions[p["group"]].get("revisit", w["revisit_default"])) * w["revisit_rate_max"]
               if p["group"] in reactions else 0.0 for p in people}

    adj = defaultdict(list)
    for e in edges:
        adj[e["from"]].append((e["to"], e["type"]))
        adj[e["to"]].append((e["from"], e["type"]))

    slat, slng = store_point(dong_code, people, geo)
    dist = {p["id"]: distance_m(p["lat"], p["lng"], slat, slng) for p in people}
    local = sorted((p["id"] for p in people if p["dong_code"] == dong_code), key=lambda i: (dist[i], i))
    base_seeds = local[: w["seed_count"]] or sorted(dist, key=lambda i: (dist[i], i))[: w["seed_count"]]
    outsiders = sorted(p["id"] for p in people if p["dong_code"] != dong_code)

    # 낮 방문 비율·경쟁 계수 (동 단위, 시드와 무관)
    n_day, p_day, comp = 0, 0.0, 1.0
    if st:
        n_day = min(int(round(w.get("day_seeds_per_million_floating", 0) * st["floating_pop"] / 1e6
                              + w.get("day_seeds_per_1000_workers", 0) * st["worker_pop"] / 1000)),
                    w.get("day_seed_max", 0))
        p_day = min(w.get("day_visit_cap", 0.0),
                    w.get("day_visit_per_million_floating", 0) * st["floating_pop"] / 1e6
                    + w.get("day_visit_per_1000_workers", 0) * st["worker_pop"] / 1000)
        k = w.get("competition_k", 0)
        if k:
            comp = (k / (k + st["store_count"])) ** w.get("competition_alpha", 1.0)

    # 사람별 방문 확률 (경쟁 반영 전 수요 기준)
    scale_m = w["visit_distance_scale_m"]
    demand_prob = {}
    for p in people:
        i = p["id"]
        if interest[i] >= w["visit_interest_min"]:
            demand_prob[i] = interest[i] * ((1 - p_day) * math.exp(-dist[i] / scale_m) + p_day)
    visit_prob = {i: v * comp for i, v in demand_prob.items()}

    # 가격·월세 (입력 없으면 동 평균 객단가, 월세는 입력값만)
    price = sc.get("avg_price") or (st or {}).get("avg_price") or w["default_avg_price"]
    rent = sc.get("rent")
    cscale = w.get("customer_scale", 1.0)

    # 시드 여러 개 실행 -> 평균과 범위, 애니메이션은 중앙값에 가장 가까운 실행
    rows = []
    for k_run in range(runs):
        s = seed + k_run
        rng = random.Random(s)
        day_seeds = sorted(rng.sample(outsiders, min(n_day, len(outsiders)))) if n_day else []
        seeds = sorted(set(base_seeds) | set(day_seeds))
        steps, heard_week, fails = spread(people, adj, seeds, share, interest, w, rng, by_id)
        demand = sum(demand_prob.get(i, 0) for i in heard_week)
        weekly_model, _ = weekly_visits(heard_week, visit_prob, revisit, w)
        rows.append({"seed": s, "steps": steps, "heard_week": heard_week, "fails": fails,
                     "demand": demand, "visitors": demand * comp, "weekly_model": weekly_model,
                     "day_seeds": len(day_seeds)})
    vis = sorted(r["visitors"] for r in rows)
    median = vis[len(vis) // 2]
    main = min(rows, key=lambda r: (abs(r["visitors"] - median), r["seed"]))
    weekly_model = [sum(r["weekly_model"][t] for r in rows) / runs for t in range(w["horizon_weeks"])]
    weekly_real = [int(round(x * cscale)) for x in weekly_model]

    # 추가 홍보: 소식이 멈추는 주에 seed_count명에게 다시 직접 알림 (대표 실행 기준)
    rw = stall_week(main["heard_week"], w)
    spw = w.get("steps_per_week", 1)
    rng = random.Random(main["seed"])
    day_seeds = sorted(rng.sample(outsiders, min(n_day, len(outsiders)))) if n_day else []
    seeds = sorted(set(base_seeds) | set(day_seeds))
    not_yet = sorted(i for i in by_id if i not in main["heard_week"] or main["heard_week"][i] >= rw)
    # 추가 홍보 = 관심 있는 미인지 시민 중 가게 가까운 순으로 repromo_count명에게 직접 노출
    pick = sorted((i for i in not_yet if interest[i] >= w["visit_interest_min"]), key=lambda i: (dist[i], i))[: w["repromo_count"]]
    _, heard_with, _ = spread(people, adj, seeds, share, interest, w, rng, by_id, extra_at={rw * spw: pick})
    with_model, _ = weekly_visits(heard_with, visit_prob, revisit, w)
    without_real = [int(round(x * cscale)) for x in main["weekly_model"]]
    with_real = [int(round(x * cscale)) for x in with_model]

    # 확산이 멈춘 집단: 인지율 10% 미만 + 가장 많이 실패한 경로 (대표 실행 기준)
    total, heard = Counter(), Counter()
    for p in people:
        total[p["group"]] += 1
        heard[p["group"]] += p["id"] in main["heard_week"]
    stopped_at = []
    for g in sorted(total):
        if heard[g] / total[g] < w["stop_awareness_threshold"]:
            tried = [(n, path) for (grp, path), n in main["fails"].items() if grp == g]
            stopped_at.append({"group": g, "path": max(tried)[1] if tried else "동네"})

    mean = lambda xs: sum(xs) / len(xs)
    return {"dong_code": dong_code, "dong": dong, "seed": main["seed"], "steps": main["steps"],
            "visitors": int(round(mean([r["visitors"] for r in rows]))),
            "stopped_at": stopped_at,
            "visitors_demand": int(round(mean([r["demand"] for r in rows]))),
            "visitors_range": [int(round(vis[0])), int(round(vis[-1]))],
            "runs": runs,
            "competition_factor": round(comp, 3),
            "daytime_share": round(p_day, 3),
            "day_seeds": main["day_seeds"],
            "population_in_radius": len(people),
            "is_estimated": (st or {}).get("is_estimated", 0),
            # 시간 축 (실제 손님 수로 환산: customer_scale)
            "weekly_visitors": weekly_real,
            "weekly_visits_model": [round(x, 3) for x in weekly_model],
            "monthly_customers": sum(weekly_real[-4:]),
            "breakeven_week": breakeven(weekly_real, price, rent, w),
            "repromo": {"week": rw, "count": len(pick), "with": with_real, "without": without_real,
                        "gain": sum(with_real) - sum(without_real)},
            "assumptions": {"avg_price": int(price), "rent": rent, "gross_margin": w["gross_margin"],
                            "other_fixed_monthly": w.get("other_fixed_monthly", 0),
                            "customer_scale": cscale},
            "channel_share": None, "hubs": None, "scenarios": None, "budget_plan": None,
            "diagnosis": None}


# ---------- 실행 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="frontend/data/real")
    ap.add_argument("--weights", default="config/weights.json")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--all-dongs", action="store_true", help="페르소나에 있는 모든 동 계산 (검증용)")
    ap.add_argument("--dongs", nargs="*", help="계산할 동 코드 목록")
    ap.add_argument("--out", default=None, help="결과 저장 폴더 (기본: --data와 같은 폴더)")
    ap.add_argument("--runs", type=int, default=None, help="시드 몇 개를 돌려 평균낼지 (기본: 후보 5, 전체 동 1)")
    args = ap.parse_args()

    folder = ROOT / args.data
    w = load_json(ROOT / args.weights)
    people = load_personas(folder)
    reactions = load_reactions(folder)
    stats = load_dong_stats(folder)
    geo = load_json(folder / "dongs.geojson") if (folder / "dongs.geojson").exists() else None
    scenario = load_json(folder / "scenario.json") if (folder / "scenario.json").exists() else {}
    runs = args.runs or (1 if args.all_dongs else w.get("runs", 5))
    out_dir = ROOT / args.out if args.out else folder
    out_dir.mkdir(parents=True, exist_ok=True)

    missing = sorted({p["group"] for p in people} - set(reactions))
    if missing:
        print(f"[경고] reactions.json에 없는 집단 {len(missing)}개 -> 무관심(0)으로 처리: {missing[:5]}")
    print(f"시민 {len(people)}명, 동별 통계 {'있음 (' + str(len(stats)) + '개 동)' if stats else '없음 (유동인구·경쟁 미반영)'}, "
          f"가중치 {w.get('version')}")

    names = {}
    for p in people:
        names.setdefault(p["dong_code"], p["dong"])
    if args.all_dongs:
        dongs = dict(sorted(names.items()))
    elif args.dongs:
        dongs = {c: names.get(c, c) for c in args.dongs}
    else:
        dongs = DEFAULT_CANDIDATES

    radius = w.get("sim_radius_m")
    all_edges = set()
    for code, name in dongs.items():
        sub = local_people(code, people, geo, radius) if radius else people
        edges = build_neighbor_edges(sub, w["neighbor_radius_m"], w["neighbor_max"])
        edges += build_community_edges(sub, reactions, w["community_links_per_person"],
                                       w.get("community_radius_m", {}), f"{args.seed}-{code}")
        res = simulate(code, name, sub, edges, reactions, geo, w, args.seed, stats, scenario, runs)
        with open(out_dir / f"result_{code}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        if not args.all_dongs:
            all_edges.update((e["from"], e["to"], e["type"]) for e in edges)
        heard = sum(len(s) for s in res["steps"])
        print(f"{name}: 반경 내 {len(sub)}명 중 {heard}명 인지({heard / max(len(sub), 1):.0%}, 12주) / "
              f"방문 가능 {res['visitors']}명 (범위 {res['visitors_range'][0]}~{res['visitors_range'][1]}, 수요 {res['visitors_demand']}) / "
              f"3달째 월 손님 {res['monthly_customers']}명 / 손익분기 {res['breakeven_week'] or '-'}주차 / "
              f"{res['repromo']['week']}주차 추가 홍보 시 +{res['repromo']['gain']}명 / 멈춘 집단 {len(res['stopped_at'])}개")

    if all_edges:
        with open(out_dir / "edges.json", "w", encoding="utf-8") as f:
            json.dump([{"from": a, "to": b, "type": t} for a, b, t in sorted(all_edges)], f, ensure_ascii=False)


if __name__ == "__main__":
    main()
