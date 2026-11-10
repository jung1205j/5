"""확산 엔진 동작 검증 테스트 (상식 테스트 13개)

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


def make_stats(floating=5e6, workers=3000, stores=50):
    return {DONG: {"floating_pop": floating, "worker_pop": workers, "store_count": stores, "is_estimated": 0}}


def run_with_stats(stats, seed=42):
    w, people, reactions = load_weights(), make_people(), make_reactions(interest=4)
    for p in people[::2]:  # 절반은 다른 동 주민 (낮 방문자 후보)
        p["dong_code"] = "8888888888"
    edges = eng.build_neighbor_edges(people, w["neighbor_radius_m"], w["neighbor_max"])
    return eng.simulate(DONG, "테스트동", people, edges, reactions, make_geo(CENTER), w, seed, stats)


def test_more_floating_more_day_visitors():
    """5) 유동인구·직장인구가 많은 동일수록 낮 출발점과 방문 수요가 늘어난다"""
    low = run_with_stats(make_stats(floating=2e6, workers=1000))
    high = run_with_stats(make_stats(floating=20e6, workers=30000))
    assert high["day_seeds"] > low["day_seeds"], f"낮 출발점 {low['day_seeds']} -> {high['day_seeds']}"
    assert high["daytime_share"] > low["daytime_share"], "낮 방문 비율이 늘지 않음"


def test_more_competition_fewer_visitors():
    """6) 같은 수요라도 근처 경쟁 점포가 많으면 방문 가능 고객이 줄어든다"""
    few = run_with_stats(make_stats(stores=20))
    many = run_with_stats(make_stats(stores=500))
    assert few["visitors_demand"] == many["visitors_demand"], "테스트 전제(같은 수요)가 깨짐"
    assert many["visitors"] < few["visitors"], f"경쟁 적음 {few['visitors']}명, 많음 {many['visitors']}명"


def test_interest_fades_over_time():
    """7) 같은 주에 소식을 들은 사람들의 첫 방문은 시간이 지날수록 줄어든다 (관심이 식음)"""
    w = load_weights()
    heard = {i: 0 for i in range(100)}
    prob = {i: 0.5 for i in range(100)}
    _, first = eng.weekly_visits(heard, prob, {i: 0.0 for i in range(100)}, w)
    assert all(first[t] > first[t + 1] for t in range(len(first) - 1)), f"첫 방문 {first}"


def test_repromo_never_hurts():
    """8) 소식이 멈출 때 추가 홍보를 하면 12주 전체 방문객이 줄지 않는다 (일찍 알게 된 만큼 주별로는 앞당겨질 수 있음)"""
    r = run_with_stats(make_stats())
    rp = r["repromo"]
    assert sum(rp["with"]) >= sum(rp["without"]), f"추가 홍보 {sum(rp['with'])} < 없음 {sum(rp['without'])}"


def test_higher_rent_later_breakeven():
    """9) 손님 흐름이 같으면 월세가 높을수록 손익분기가 늦어지거나 12주 안에 안 온다"""
    w = load_weights()
    weekly = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]
    low = eng.breakeven(weekly, 7000, 1_000_000, w)
    high = eng.breakeven(weekly, 7000, 6_000_000, w)
    assert low is not None and (high is None or high > low), f"월세 100만 {low}주차, 600만 {high}주차"


def test_evening_hours_favor_night_dong():
    """10) 저녁 영업(17~24시)이면 밤 유동인구 비중이 큰 동이, 낮 영업(9~17시)이면 낮 비중이 큰 동이 유리하다"""
    w = load_weights()
    night = {"flow": {"flow_06_11": 10, "flow_11_14": 10, "flow_14_17": 10, "flow_17_21": 40, "flow_21_24": 30}}
    day = {"flow": {"flow_06_11": 30, "flow_11_14": 30, "flow_14_17": 25, "flow_17_21": 10, "flow_21_24": 5}}
    ev_n, _ = eng.hours_factor(night, [17, 24], w)
    ev_d, _ = eng.hours_factor(day, [17, 24], w)
    lu_n, _ = eng.hours_factor(night, [9, 17], w)
    lu_d, _ = eng.hours_factor(day, [9, 17], w)
    assert ev_n > ev_d and lu_d > lu_n, f"저녁: 밤동 {ev_n:.2f} 낮동 {ev_d:.2f} / 낮: 밤동 {lu_n:.2f} 낮동 {lu_d:.2f}"


def test_closed_days_fewer_customers():
    """11) 쉬는 날이 있으면 일주일 손님이 줄고, 주말이 붐비는 동에서 주말에 쉬면 더 크게 준다"""
    weekend_heavy = {"flow": {"flow_weekday": 500, "flow_weekend": 400}}
    all_days, _ = eng.days_factor(weekend_heavy, None)
    no_sun, _ = eng.days_factor(weekend_heavy, ["월", "화", "수", "목", "금", "토"])
    no_mon, _ = eng.days_factor(weekend_heavy, ["화", "수", "목", "금", "토", "일"])
    assert all_days == 1.0 and no_sun < no_mon < all_days, f"전체 {all_days}, 일 휴무 {no_sun:.2f}, 월 휴무 {no_mon:.2f}"


def test_no_reviews_little_search():
    """12) 후기가 쌓이지 않으면(후기 작성률 0) 검색으로 알게 되는 사람이 거의 없다"""
    w, people, reactions = load_weights(), make_people(), make_reactions(interest=4)
    for g in reactions:
        reactions[g]["discovery"] = {"네이버검색": 0.6, "인스타": 0.1, "지인": 0.1, "지나가다": 0.1, "당근커뮤니티": 0.1}
    edges = eng.build_neighbor_edges(people, w["neighbor_radius_m"], w["neighbor_max"])

    def search_count(rate):
        w2 = dict(w, review_rate=rate)
        r = eng.simulate(DONG, "테스트동", people, edges, reactions, make_geo(CENTER), w2, 42)
        return r["channel_total"].get("검색", 0)
    none, some = search_count(0.0), search_count(0.5)
    assert none == 0 and some > 0, f"후기 없음 {none}, 후기 있음 {some}"


def test_hub_reach_consistent():
    """13) 입소문 허브는 전한 인원(reach) 순으로 정렬되고, 직접 전한 사람 수보다 reach가 작지 않다"""
    r = run_with_stats(make_stats())
    hubs = r["hubs"]
    assert hubs, "허브가 하나도 없음"
    assert all(a["reach"] >= b["reach"] for a, b in zip(hubs, hubs[1:])), "reach 순서가 아님"
    assert all(h["reach"] >= h["direct"] >= 1 for h in hubs), f"reach/direct 이상 {hubs}"


if __name__ == "__main__":
    tests = [test_no_interest_no_spread, test_more_interest_more_spread,
             test_farther_store_fewer_visitors, test_same_seed_same_result,
             test_more_floating_more_day_visitors, test_more_competition_fewer_visitors,
             test_interest_fades_over_time, test_repromo_never_hurts, test_higher_rent_later_breakeven,
             test_evening_hours_favor_night_dong, test_closed_days_fewer_customers,
             test_no_reviews_little_search, test_hub_reach_consistent]
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
