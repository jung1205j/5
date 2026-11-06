"""LocalSim 확산 엔진 (동네 + 커뮤니티 관계망, 확산, 방문 계산, 랜덤 시드)

실행 (저장소 맨 위에서):
    python engine/simulate.py
    python engine/simulate.py --seed 7 --data frontend/data/real

입력: {data}/personas.csv, {data}/reactions.json, (있으면) {data}/dongs.geojson
출력: {data}/edges.json, {data}/result_{동코드}.json
가중치: config/weights.json  (검증 때 여기 숫자만 바꾸면 됨)
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


def to01(score):
    """1~5점 -> 0~1"""
    return max(0.0, min(1.0, (float(score) - 1) / 4))


def distance_m(lat1, lng1, lat2, lng2):
    """서울 범위에서는 평면 근사로 충분"""
    dy = (lat1 - lat2) * 111_000
    dx = (lng1 - lng2) * 111_000 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


# ---------- 관계망 ----------
def build_neighbor_edges(people, radius_m, max_neighbors):
    """서로 radius_m 안에 사는 사람끼리 연결 (사람당 가까운 순 최대 max_neighbors명)"""
    cell = radius_m / 111_000  # 위경도 격자 크기
    grid = defaultdict(list)
    for p in people:
        grid[(int(p["lat"] // cell), int(p["lng"] // cell))].append(p)

    edges = set()
    for p in people:
        ci, cj = int(p["lat"] // cell), int(p["lng"] // cell)
        near = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for q in grid[(ci + di, cj + dj)]:
                    if q["id"] == p["id"]:
                        continue
                    d = distance_m(p["lat"], p["lng"], q["lat"], q["lng"])
                    if d <= radius_m:
                        near.append((d, q["id"]))
        for _, qid in sorted(near)[:max_neighbors]:
            edges.add((min(p["id"], qid), max(p["id"], qid)))
    return [{"from": a, "to": b, "type": "동네"} for a, b in sorted(edges)]


def build_community_edges(people, reactions, links_per_person, radius_by_community, seed):
    """같은 커뮤니티 이용자끼리 연결.
    글 하나가 회원 여럿에게 보이는 효과를 사람당 무작위 links_per_person명 연결로 근사.
    설득력은 weights의 path_weight로 동네보다 약하게.
    radius_by_community에 반경이 있는 커뮤니티(예: 당근)는 그 거리 안 회원끼리만 연결."""
    rng = random.Random(f"community-{seed}")
    members = defaultdict(list)
    for p in people:
        for c in reactions.get(p["group"], {}).get("community", []):
            if c != "없음":
                members[c].append(p)

    edges = set()
    for c in sorted(members):
        pool = members[c]
        radius = radius_by_community.get(c)
        for p in pool:
            cand = [q for q in pool if q["id"] != p["id"]]
            if radius:
                cand = [q for q in cand if distance_m(p["lat"], p["lng"], q["lat"], q["lng"]) <= radius]
            for q in rng.sample(cand, min(links_per_person, len(cand))):
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


# ---------- 확산 ----------
def simulate(dong_code, dong, people, edges, reactions, geo, w, seed):
    rng = random.Random(seed)
    by_id = {p["id"]: p for p in people}

    # 반응 없는 집단은 무관심(0) -> 결과가 낙관적으로 안 나오게
    interest = {p["id"]: to01(reactions[p["group"]]["interest"]) if p["group"] in reactions else 0.0 for p in people}
    share = {p["id"]: to01(reactions[p["group"]]["share"]) if p["group"] in reactions else 0.0 for p in people}

    adj = defaultdict(list)
    for e in edges:
        adj[e["from"]].append((e["to"], e["type"]))
        adj[e["to"]].append((e["from"], e["type"]))

    # 출발점: 가게와 가장 가까운 그 동 주민
    slat, slng = store_point(dong_code, people, geo)
    dist = {p["id"]: distance_m(p["lat"], p["lng"], slat, slng) for p in people}
    local = sorted((p["id"] for p in people if p["dong_code"] == dong_code), key=lambda i: (dist[i], i))
    seeds = local[: w["seed_count"]] or sorted(dist, key=lambda i: (dist[i], i))[: w["seed_count"]]

    informed = set(seeds)
    steps = [sorted(seeds)]
    fails = Counter()
    frontier = sorted(seeds)
    while frontier and len(steps) < w["max_steps"]:
        new = []
        for s in frontier:  # 새로 들은 사람은 연결된 사람마다 한 번씩 전할 기회
            for r, path in sorted(adj[s]):
                if r in informed:
                    continue
                p = share[s] * interest[r] * w["path_weight"][path]
                if rng.random() < p:
                    informed.add(r)
                    new.append(r)
                else:
                    fails[(by_id[r]["group"], path)] += 1
        if not new:
            break
        steps.append(sorted(new))
        frontier = sorted(new)

    # 방문 가능 고객: 관심도 일정 이상 + 가까울수록 높은 확률
    visitors = sum(interest[i] * math.exp(-dist[i] / w["visit_distance_scale_m"])
                   for i in informed if interest[i] >= w["visit_interest_min"])

    # 확산이 멈춘 집단: 인지율 10% 미만 + 가장 많이 실패한 경로
    total, heard = Counter(), Counter()
    for p in people:
        total[p["group"]] += 1
        heard[p["group"]] += p["id"] in informed
    stopped_at = []
    for g in sorted(total):
        if heard[g] / total[g] < w["stop_awareness_threshold"]:
            tried = [(n, path) for (grp, path), n in fails.items() if grp == g]
            stopped_at.append({"group": g, "path": max(tried)[1] if tried else "동네"})

    return {"dong_code": dong_code, "dong": dong, "seed": seed, "steps": steps,
            "visitors": int(round(visitors)), "stopped_at": stopped_at}


# ---------- 실행 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="frontend/data/real")
    ap.add_argument("--weights", default="config/weights.json")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    folder = ROOT / args.data
    w = load_json(ROOT / args.weights)
    people = load_personas(folder)
    reactions = load_reactions(folder)
    geo = load_json(folder / "dongs.geojson") if (folder / "dongs.geojson").exists() else None

    missing = sorted({p["group"] for p in people} - set(reactions))
    if missing:
        print(f"[경고] reactions.json에 없는 집단 {len(missing)}개 -> 무관심(0)으로 처리: {missing[:5]}")

    edges = build_neighbor_edges(people, w["neighbor_radius_m"], w["neighbor_max"])
    edges += build_community_edges(people, reactions, w["community_links_per_person"],
                                   w.get("community_radius_m", {}), args.seed)
    with open(folder / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False)
    by_type = Counter(e["type"] for e in edges)
    print(f"관계망: 시민 {len(people)}명, 연결 {len(edges)}개 {dict(by_type)} -> edges.json")

    for code, name in DEFAULT_CANDIDATES.items():
        res = simulate(code, name, people, edges, reactions, geo, w, args.seed)
        with open(folder / f"result_{code}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        heard = sum(len(s) for s in res["steps"])
        print(f"{name}: 소식 들은 시민 {heard}명 / {len(res['steps'])}단계 / 방문 가능 {res['visitors']}명 / 멈춘 집단 {len(res['stopped_at'])}개")


if __name__ == "__main__":
    main()
