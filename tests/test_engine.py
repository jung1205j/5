"""확산 엔진 동작 검증 테스트 (상식 테스트 4개)

실행 (저장소 맨 위에서):  python tests/test_engine.py
pytest가 있으면:          pytest tests/test_engine.py

실제 데이터 대신 테스트용 가상 동네(시민 400명)를 만들어 엔진 규칙만 확인한다.
"""
import copy
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import simulate as eng  # noqa: E402

DONG = "9999999999"
CENTER = (37.5550, 126.9100)
SEEDS = [1, 2, 3, 4, 5]


def load_weights():
    with open(ROOT / "config" / "weights.json", encoding="utf-8") as f:
        return json.load(f)


def make_people(n=400, spread=0.004, center=CENTER):
    """중심 주변 약 400m 안에 시민 n명, 전원 같은 동, 같은 집단"""
    rng = random.Random(0)
    return [{"id": i, "dong_code": DONG, "dong": "테스트동", "group": "20대이하_학생",
             "lat": center[0] + rng.uniform(-spread, spread),
             "lng": center[1] + rng.uniform(-spread, spread)} for i in range(1, n + 1)]


def make_reactions(interest, share=5):
    return {"20대이하_학생": {"group": "20대이하_학생", "interest": interest, "share": share,
                            "reason_type": "기타", "reason_text": "테스트", "community": ["인스타"]}}


def make_geo(center):
    """가게 위치(동 중심점)를 center로 두는 작은 정사각형 경계"""
    lat, lng = center
    ring = [[lng - 0.001, lat - 0.001], [lng + 0.001, lat - 0.001], [lng + 0.001, lat + 0.001],
            [lng - 0.001, lat + 0.001], [lng - 0.001, lat - 0.001]]
    return {"type": "FeatureCollection", "features": [{"type": "Feature",
            "properties": {"adm_cd2": DONG}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def run(people, reactions, w, seed, geo=None):
    edges = eng.build_neighbor_edges(people, w["neighbor_radius_m"], w["neighbor_max"])
    edges += eng.build_community_edges(people, reactions, w["community_links_per_person"],
                                       w.get("community_radius_m", {}), seed)
    res = eng.simulate(DONG, "테스트동", people, edges, reactions, geo or make_geo(CENTER), w, seed)
    heard = sum(len(s) for s in res["steps"])
    return res, heard, edges


def test_no_interest_no_spread():
    """1) 관심도 최저(1점=0)면 출발점 외에는 거의 퍼지지 않는다"""
    w, people = load_weights(), make_people()
    for seed in SEEDS:
        _, heard, _ = run(people, make_reactions(interest=1), w, seed)
        assert heard <= w["seed_count"], f"seed {seed}: 관심도 0인데 {heard}명에게 퍼짐"


def test_more_interest_more_spread():
    """2) 관심도를 올리면 확산이 늘어난다 (시드 5개 평균)"""
    w, people = load_weights(), make_people()
    low = sum(run(people, make_reactions(interest=2), w, s)[1] for s in SEEDS) / len(SEEDS)
    high = sum(run(people, make_reactions(interest=5), w, s)[1] for s in SEEDS) / len(SEEDS)
    assert high > low, f"관심도 5({high:.1f}명)가 관심도 2({low:.1f}명)보다 많이 퍼져야 함"


def test_farther_store_fewer_visitors():
    """3) 같은 사람들이 소식을 들어도 가게가 멀수록 방문 가능 고객이 줄어든다"""
    w, people = load_weights(), make_people()
    w = copy.deepcopy(w)
    w["transmission_scale"] = 10.0  # 전원이 듣게 해서 확산 차이를 없애고 거리 효과만 본다
    reactions = make_reactions(interest=5)
    near, heard_near, _ = run(people, reactions, w, 42, geo=make_geo(CENTER))
    far_center = (CENTER[0] + 0.02, CENTER[1])  # 약 2.2km 북쪽
    far, heard_far, _ = run(people, reactions, w, 42, geo=make_geo(far_center))
    assert heard_near == heard_far == len(people), "테스트 전제(전원 인지)가 깨짐"
    assert near["visitors"] > far["visitors"], f"가까울 때 {near['visitors']}명, 멀 때 {far['visitors']}명"


def test_same_seed_same_result():
    """4) 같은 시드면 관계망과 결과가 완전히 같다"""
    w, people, reactions = load_weights(), make_people(), make_reactions(interest=4)
    a, _, edges_a = run(people, reactions, w, 7)
    b, _, edges_b = run(people, reactions, w, 7)
    assert edges_a == edges_b, "같은 시드인데 관계망이 다름"
    assert a == b, "같은 시드인데 결과가 다름"


if __name__ == "__main__":
    tests = [test_no_interest_no_spread, test_more_interest_more_spread,
             test_farther_store_fewer_visitors, test_same_seed_same_result]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"통과  {t.__doc__.strip()}")
        except AssertionError as e:
            failed += 1
            print(f"실패  {t.__doc__.strip()}\n      -> {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} 통과")
    sys.exit(1 if failed else 0)
