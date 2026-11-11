"""홍보 시나리오 · 예산 배분 (LocalSim)

simulate.py가 후보 동마다 plan(model)을 부른다. 하는 일:
1) 채널별 시나리오: 인스타 / 당근 / 맘카페 / 체험단 / 허브 쿠폰 / 오픈 할인을 각각 넣고 12주 손님이 얼마나 느는지
2) 시점: 채널마다 오픈 2주 전 / 오픈 주 / 소식이 멈추는 주 중 가장 효과 좋은 때를 고름
3) 예산 배분: 채널별 '돈을 늘릴수록 효과가 줄어드는' 곡선을 만들고 입력 예산 안에서 손님이 가장 많은 배분을 찾음
4) 허브 vs 넓게: 같은 돈으로 입소문 허브에게 쿠폰을 줬을 때와 인스타로 넓게 뿌렸을 때 비교
5) 막힌 집단 처방: 관심은 있는데 소식이 덜 닿은 집단에 맞는 채널과 제안 (설문의 홍보 반응·거절 이유 기준)
6) 돈 얘기: 만 원당 손님, 광고비 회수 주차, 손익분기 변화, 단가 범위가 바뀌어도 추천이 유지되는지

광고비 -> 소식을 직접 들은 가상 시민 수 변환은 customer_scale(모델 1명 = 실제 손님 환산 배율)을 그대로 써서
결과 화면의 실제 손님 수와 같은 단위로 맞춘다. 노출당 주목률 같은 효과 숫자는 가정값(weights.json의 promo)이다.
"""
import itertools
import math
from collections import Counter

AD_COSTS = []  # simulate.py가 ad_costs.json을 넣어줌

CHANNELS = ["인스타", "당근", "맘카페", "체험단", "허브쿠폰"]
TIMINGS = ["오픈전", "오픈주", "정체기"]
RESPONSE_KEY = {"인스타": "인스타광고", "당근": "당근광고", "맘카페": "지인추천", "체험단": "체험단후기",
                "허브쿠폰": "지인추천", "오픈이벤트": "오픈할인"}
CHANNEL_CODE = {"인스타": 101, "당근": 102, "맘카페": 103, "체험단": 104, "허브쿠폰": 105}
FALLBACK_COST = {"인스타": 18000, "당근": 300, "맘카페": 200000, "체험단": 100000}


def ad_item(channel):
    items = [a for a in AD_COSTS if a.get("channel") == channel]
    item = next((a for a in items if a.get("default")), items[0] if items else None)
    if not item or not item.get("cost_per_unit"):
        return {"cost_per_unit": FALLBACK_COST.get(channel), "cost_min": None, "cost_max": None,
                "unit": "기본값", "tier": None}
    return item


def cost_range(channel):
    """단가 최소/최대 배수 (기준 단가 대비). 모르면 1"""
    it = ad_item(channel)
    base = it.get("cost_per_unit") or 1
    lo = (it.get("cost_min") or base) / base
    hi = (it.get("cost_max") or base) / base
    return lo, hi


def members_of(tier, default):
    try:
        return float(str(tier).replace(",", "").replace("명", ""))
    except (TypeError, ValueError):
        return default


# ---------- 시나리오 실행 ----------
def build_promo(m, actions, seed):
    """actions: [{"channel", "budget", "timing"}] -> spread()에 넣을 promo dict, 할인 boost, 실제 비용(할인 제외)"""
    w, P = m["w"], max(m["cscale"], 1e-9)
    pw = w["promo"]
    spw = w.get("steps_per_week", 1)
    coin = m["coin"]
    react = m["reactions"]
    promo = {"pre": [], "pre_steps": pw["pre_open_weeks"] * spw, "at": {}, "share": {}, "reviews": {}}
    boost = None
    base_seeds = set(m["main"]["seeds"])

    def resp(i, ch):
        g = m["by_id"][i]["group"]
        return react.get(g, {}).get("promo_response", {}).get(RESPONSE_KEY[ch], pw["response_default"])

    def comm(i):
        return react.get(m["by_id"][i]["group"], {}).get("community", [])

    def step_of(timing, k=0):
        if timing == "오픈전":
            return None
        if timing == "오픈주":
            return 1 + k * 4 * spw
        return max(1, m["stall_week"] * spw) + k * 4 * spw

    def add(ids, ch, timing, k=0):
        st = step_of(timing, k)
        if st is None:
            promo["pre"].extend((i, ch) for i in ids)
        else:
            promo["at"].setdefault(st, []).extend((i, ch) for i in ids)

    def pick(cands, n_expected, ch, weight, salt=0):
        """기댓값 n_expected명이 되도록 사람마다 확률을 주고 고정 난수로 뽑음"""
        if not cands or n_expected <= 0:
            return []
        tot = sum(weight(i) for i in cands) or 1.0
        out = []
        for i in cands:
            p = min(1.0, n_expected * weight(i) / tot)
            if coin(seed, i, 50_000_000 + CHANNEL_CODE.get(ch, 1) * 1000 + salt) < p:
                out.append(i)
        return out

    alive = [i for i in m["by_id"] if m["interest"][i] > 0 and i not in base_seeds]
    for a in actions:
        ch, b, timing = a["channel"], a["budget"], a["timing"]
        if b <= 0 and ch != "오픈이벤트":
            continue
        it = ad_item(ch) if ch != "오픈이벤트" else None
        cost = (it or {}).get("cost_per_unit") or 1
        if ch == "인스타":
            cands = [i for i in alive if "인스타" in comm(i)]
            exposed = (b / cost) * 1000 / P / pw["insta_frequency"]
            n = exposed * pw["notice"]["인스타"] * pw["response_mean"] * pw["effect_scale"]
            add(pick(cands, n, ch, lambda i: resp(i, ch)), "인스타광고", timing)
        elif ch == "당근":
            cands = [i for i in alive if "당근" in comm(i) and m["dist"][i] <= pw["dangn_radius_m"]]
            n = (b / cost) / P * pw["notice"]["당근"] * pw["effect_scale"]
            add(pick(cands, n, ch, lambda i: resp(i, ch)), "당근광고", timing)
        elif ch == "맘카페":
            cands = [i for i in alive if "맘카페" in comm(i)]
            months = min(int(b // cost), pw["max_months"])
            members = members_of(it.get("tier"), pw["cafe_members"])
            for k in range(months):
                n = members * pw["banner_view_rate"] / P * pw["notice"]["맘카페"] * pw["response_mean"] * pw["effect_scale"]
                add(pick(cands, n, ch, lambda i: resp(i, ch), salt=k), "맘카페광고", timing, k)
        elif ch == "체험단":
            posts = b / cost
            st = step_of(timing) if step_of(timing) is not None else 0
            promo["reviews"][max(st, 1)] = promo["reviews"].get(max(st, 1), 0) + posts * pw["review_per_post"] * pw["effect_scale"]
            n = posts * pw["post_reach"] / P * pw["notice"]["체험단"] * pw["response_mean"] * pw["effect_scale"]
            add(pick(alive, n, ch, lambda i: resp(i, ch)), "체험단후기", timing)
        elif ch == "허브쿠폰":
            # 쿠폰 1장 = 실제 1명 -> 가상 시민 1명(=P명)에게 닿으려면 P장. 대상은 영향력 순
            n_pers = b / (pw["coupon_cost"] * P)
            order = [i for i in m["hub_order"] if i not in base_seeds]
            k_full = int(n_pers)
            chosen = order[:k_full]
            frac = n_pers - k_full
            if frac > 0 and k_full < len(order) and coin(seed, order[k_full], 60_000_000) < frac:
                chosen.append(order[k_full])
            add(chosen, "허브쿠폰", timing)
            for i in chosen:
                promo["share"][i] = min(1.0, m["share"][i] + pw["hub_share_boost"])
        elif ch == "오픈이벤트":
            weeks = set(range(pw["discount_weeks"]))
            mult = {i: 1 + pw["discount_boost"] * resp(i, "오픈이벤트") for i in m["by_id"]}
            boost = (weeks, mult)
    return promo, boost


def run_plan(m, actions):
    """actions를 넣고 promo runs개 시드로 돌린 12주 실제 손님(평균)과 할인 비용"""
    w = m["w"]
    rows = m["rows"][: w["promo"]["runs"]]
    H = w["horizon_weeks"]
    total = [0.0] * H
    for r in rows:
        promo, boost = build_promo(m, actions, r["seed"])
        _, heard, _, _, _ = m["spread"](m["people"], m["adj"], r["seeds"], m["share"], m["interest"], w,
                                        r["seed"], m["by_id"], ctx=m["ctx"], promo=promo)
        wv, _ = m["weekly_visits"](heard, m["visit_prob"], m["revisit"], w, boost=boost)
        total = [a + b / len(rows) for a, b in zip(total, wv)]
    real = [x * m["cscale"] for x in total]
    disc_cost = 0.0
    if any(a["channel"] == "오픈이벤트" for a in actions):
        pw = w["promo"]
        disc_cost = pw["discount_rate"] * m["price"] * sum(real[: pw["discount_weeks"]])
    return real, disc_cost


def gain_of(m, real):
    return sum(real) - sum(m["base_promo"])


# ---------- 예산 배분 ----------
def concave_curve(points):
    """[(예산, 효과)] -> 0에서 시작, 효과 감소(오목) 보정된 구간별 기울기 [(구간 끝 예산, 기울기)]"""
    pts = sorted([(0.0, 0.0)] + [(b, max(g, 0.0)) for b, g in points])
    segs, last_slope = [], float("inf")
    for (b0, g0), (b1, g1) in zip(pts, pts[1:]):
        slope = (g1 - g0) / (b1 - b0) if b1 > b0 else 0.0
        slope = max(0.0, min(slope, last_slope))
        segs.append((b1, slope))
        last_slope = slope
    return segs


def marginal(segs, b, mult=1.0):
    """예산 b 지점의 한계 효과. mult = 단가 배수 (단가가 2배면 같은 돈으로 효과는 절반 지점)"""
    x = b / mult
    for end, slope in segs:
        if x < end:
            return slope / mult
    return 0.0


def allocate(curves, budget, step, mults=None):
    mults = mults or {}
    alloc = {c: 0.0 for c in curves}
    left = budget
    while left >= step - 1e-6:
        best = max(curves, key=lambda c: marginal(curves[c], alloc[c], mults.get(c, 1.0)))
        if marginal(curves[best], alloc[best], mults.get(best, 1.0)) <= 0:
            break
        alloc[best] += step
        left -= step
    return alloc


def payback_week(m, real, cost):
    """추가 손님이 남긴 이익(객단가 x 마진율) 누적이 광고비를 넘는 주 (1주차부터)"""
    if cost <= 0:
        return 0
    cum = 0.0
    for t, (a, b) in enumerate(zip(real, m["base_promo"])):
        cum += (a - b) * m["price"] * m["w"]["gross_margin"]
        if cum >= cost:
            return t + 1
    return None


# ---------- 막힌 집단 처방 ----------
OFFER = {"가격": "오픈 할인이나 가격대 조정", "시간": "영업시간을 이 집단이 주로 오는 시간에 맞추기",
         "분위기": "체험단 사진 후기로 분위기 보여주기", "메뉴": "체험단 후기로 대표 메뉴 보여주기",
         "거리": "가게 앞을 지나는 사람에게 보이게 (간판·당근 동네 광고)", "관심없음": "타깃에서 빼는 것도 검토",
         "기타": "반응 좋은 채널로 먼저 알리기"}


def prescriptions(m, top=3):
    react, by_id = m["reactions"], m["by_id"]
    heard = m["main"]["heard_week"]
    total, got = Counter(), Counter()
    for i, p in by_id.items():
        total[p["group"]] += 1
        got[p["group"]] += i in heard
    overall = sum(got.values()) / max(sum(total.values()), 1)
    out = []
    for g, n in total.items():
        r = react.get(g)
        if not r or n < 5:
            continue
        interest01 = (float(r["interest"]) - 1) / 4
        aware = got[g] / n
        if interest01 < m["w"]["promo"]["presc_interest_min"] or aware >= overall * m["w"]["promo"]["presc_aware_ratio"]:
            continue
        comm = r.get("community", [])
        pr = r.get("promo_response", {})
        options = [("체험단", pr.get("체험단후기", 0)), ("오픈이벤트", pr.get("오픈할인", 0))]
        if "인스타" in comm:
            options.append(("인스타", pr.get("인스타광고", 0)))
        if "당근" in comm:
            options.append(("당근", pr.get("당근광고", 0)))
        if "맘카페" in comm:
            options.append(("맘카페", pr.get("지인추천", 0)))
        ch, rv = max(options, key=lambda x: x[1])
        offer = OFFER.get(r.get("reason_type"), OFFER["기타"])
        if r.get("reason_type") == "시간" and r.get("visit_time"):
            offer += f" (주로 {max(r['visit_time'], key=r['visit_time'].get)})"
        if r.get("reason_type") == "가격" and r.get("price_max"):
            offer += f" (가장 많이 고른 가격대: {max(r['price_max'], key=r['price_max'].get)})"
        out.append({"group": g, "awareness": round(aware, 3), "overall_awareness": round(overall, 3),
                    "interest": r["interest"], "reason_type": r.get("reason_type"),
                    "channel": ch, "response": round(rv, 3), "offer": offer})
    return sorted(out, key=lambda x: x["awareness"])[:top]


# ---------- 전체 계획 ----------
def plan(m):
    from simulate import coin  # 같은 고정 난수
    w = m["w"]
    pw = w["promo"]
    m["coin"] = coin
    B = float(m["budget"])
    # 허브 순서: 대표 실행에서 영향력(reach) 큰 순
    m["hub_order"] = [h["id"] for h in m["find_hubs"](m["main"]["heard_week"], m["main"]["parent"],
                                                       m["by_id"], m["reactions"], pw["hub_pool"])]
    m["base_promo"], _ = run_plan(m, [])
    children = {}
    for c, p in m["main"]["parent"].items():
        children.setdefault(p, []).append(c)
    reach = {}
    for i in sorted(m["main"]["heard_week"], key=lambda i: -m["main"]["heard_week"][i]):
        reach[i] = sum(1 + reach.get(c, 0) for c in children.get(i, []))
    m["reach"] = reach

    # 1) 채널별 최적 시점 (예산 절반 기준)
    best_timing, timing_table = {}, {}
    for ch in CHANNELS:
        res = {}
        for t in TIMINGS:
            real, _ = run_plan(m, [{"channel": ch, "budget": B / 2, "timing": t}])
            res[t] = gain_of(m, real)
        best_timing[ch] = max(res, key=res.get)
        timing_table[ch] = {t: max(0, round(v)) for t, v in res.items()}  # 효과가 거의 없는 경우 운 차이로 생기는 음수는 0

    # 2) 채널별 예산-효과 곡선 (1/4, 1/2, 전체)
    curves, scen = {}, []
    for ch in CHANNELS:
        pts = []
        for f in (0.25, 0.5, 1.0):
            if f == 0.5:
                g = timing_table[ch][best_timing[ch]]
            else:
                real, _ = run_plan(m, [{"channel": ch, "budget": B * f, "timing": best_timing[ch]}])
                g = gain_of(m, real)
            pts.append((B * f, g))
        curves[ch] = concave_curve(pts)
        g_full = pts[-1][1]
        scen.append({"name": ch, "timing": best_timing[ch], "cost": int(B), "visitors_gain": int(round(g_full)),
                     "per_10k": round(g_full / (B / 10000), 2) if B else None,
                     "roas": round(g_full * m["price"] / B, 2) if B else None,
                     "by_timing": timing_table[ch], "curve": [[int(b), int(round(g))] for b, g in pts]})

    # 오픈 할인 (예산과 별개로 할인한 만큼 비용이 듦)
    disc_real, disc_cost = run_plan(m, [{"channel": "오픈이벤트", "budget": 0, "timing": "오픈주"}])
    disc_gain = gain_of(m, disc_real)
    scen.append({"name": "오픈이벤트", "timing": "오픈주", "cost": int(disc_cost), "visitors_gain": int(round(disc_gain)),
                 "per_10k": round(disc_gain / (disc_cost / 10000), 2) if disc_cost else None,
                 "note": f"첫 {pw['discount_weeks']}주 {int(pw['discount_rate'] * 100)}% 할인, 비용 = 할인해준 금액"})

    # 3) 예산 배분 (할인 포함/미포함 중 손님이 더 많은 쪽)
    step = max(B * pw["step_frac"], 1.0)

    def finish(alloc, with_disc):
        acts = [{"channel": c, "budget": b, "timing": best_timing[c]} for c, b in alloc.items() if b > 0]
        if with_disc:
            acts.append({"channel": "오픈이벤트", "budget": 0, "timing": "오픈주"})
        real, dc = run_plan(m, acts)
        return acts, real, dc

    alloc_a = allocate(curves, B, step)
    acts_a, real_a, dc_a = finish(alloc_a, False)
    candidates = [(gain_of(m, real_a), alloc_a, acts_a, real_a, dc_a, False)]
    # 할인 포함안: 할인 비용은 손님 수에 따라 커지므로, 할인 비용을 뺀 나머지로 배분 -> 다시 계산을 두 번 반복해 예산 안에 맞춤
    dc_est = disc_cost
    for _ in range(2):
        if dc_est >= B:
            break
        alloc_b = allocate(curves, B - dc_est, step)
        acts_b, real_b, dc_b = finish(alloc_b, True)
        if sum(alloc_b.values()) + dc_b <= B * 1.02:
            candidates.append((gain_of(m, real_b), alloc_b, acts_b, real_b, dc_b, True))
            break
        dc_est = dc_b
    # 한 채널에 다 쓰는 게 더 나은 경우도 비교 (배분 곡선이 겹치는 효과를 다 못 담을 수 있어서)
    best_single = max(CHANNELS, key=lambda c: next(s["visitors_gain"] for s in scen if s["name"] == c))
    single_alloc = {c: (B if c == best_single else 0.0) for c in CHANNELS}
    acts_s, real_s, dc_s = finish(single_alloc, False)
    candidates.append((gain_of(m, real_s), single_alloc, acts_s, real_s, dc_s, False))
    gain, alloc, acts, real, dc, with_disc = max(candidates, key=lambda x: x[0])
    spent = sum(alloc.values()) + dc

    base_be = m["breakeven"]([int(round(x)) for x in m["baseline_real"]], m["price"], m["rent"], w)
    with_be = m["breakeven"]([int(round(x)) for x in real], m["price"], m["rent"], w)

    # 4) 견고성: 채널별 단가가 최소/최대로 바뀌어도 1순위 채널이 그대로인지
    top = max(alloc, key=alloc.get) if any(alloc.values()) else None
    ranges = {c: cost_range(c) for c in CHANNELS}
    same, total = 0, 0
    for combo in itertools.product(*[(ranges[c][0], ranges[c][1]) for c in CHANNELS]):
        mults = dict(zip(CHANNELS, combo))
        a2 = allocate(curves, B, step, mults)
        total += 1
        same += (max(a2, key=a2.get) if any(a2.values()) else None) == top
    robust_share = same / total if total else 1.0

    budget_plan = {
        "budget": int(B), "spent": int(round(spent)),
        "split": {c: int(round(b)) for c, b in alloc.items() if b > 0},
        "timing": {c: best_timing[c] for c, b in alloc.items() if b > 0},
        "open_discount": with_disc, "discount_cost": int(round(dc)),
        "visitors_gain": int(round(gain)),
        "per_10k": round(gain / (spent / 10000), 2) if spent else None,
        "roas": round(gain * m["price"] / spent, 2) if spent else None,
        "payback_week": payback_week(m, real, spent),
        "breakeven_without": base_be, "breakeven_with": with_be,
        "weekly_with": [int(round(x)) for x in real],
        "weekly_without": [int(round(x)) for x in m["base_promo"]],
        "robust": {"top_channel": top, "same_top_share": round(robust_share, 2),
                   "stable": robust_share >= pw["robust_threshold"]},
        "assumption_note": "노출당 주목률·쿠폰 효과·할인 효과는 가정값 (weights.json promo)",
    }

    # 5) 허브 vs 넓게 (같은 돈)
    X = min(B, pw["hub_compare_budget"])
    hub_real, _ = run_plan(m, [{"channel": "허브쿠폰", "budget": X, "timing": best_timing["허브쿠폰"]}])
    ins_real, _ = run_plan(m, [{"channel": "인스타", "budget": X, "timing": best_timing["인스타"]}])
    hg, ig = gain_of(m, hub_real), gain_of(m, ins_real)
    # 한 명이 몇 명에게 퍼뜨리나: 대표 실행의 입소문 경로에서 직접 계산 (운에 덜 흔들림)
    reach = m["reach"]
    hub_people = X / pw["coupon_cost"]
    n_hub = max(1, min(len(m["hub_order"]), int(round(hub_people / max(m["cscale"], 1e-9))) or 1))
    hub_ids = m["hub_order"][: max(n_hub, pw["hub_compare_min"])]
    insta_users = [i for i in m["main"]["heard_week"]
                   if "인스타" in m["reactions"].get(m["by_id"][i]["group"], {}).get("community", [])]
    per_hub = sum(reach.get(i, 0) for i in hub_ids) / len(hub_ids) if hub_ids else 0
    per_ins = sum(reach.get(i, 0) for i in insta_users) / len(insta_users) if insta_users else 0
    ins_people = (X / (ad_item("인스타").get("cost_per_unit") or 1)) * 1000 / pw["insta_frequency"] \
        * pw["notice"]["인스타"] * pw["response_mean"] * pw["effect_scale"]
    hub_vs_broad = {"budget": int(X), "hub_coupons": int(hub_people),
                    "hub_gain": int(round(hg)), "broad_channel": "인스타", "broad_gain": int(round(ig)),
                    "ratio": round(hg / ig, 2) if ig > 0 else None,
                    "broad_people": int(round(ins_people)),
                    "reach_hub": round(per_hub, 2), "reach_broad": round(per_ins, 2),
                    "per_person_ratio": round(per_hub / per_ins, 2) if per_ins > 0 else None,
                    "per_person_note": "한 명이 소식을 퍼뜨린 평균 인원 (허브 상위 vs 인스타 이용자 평균)",
                    "hub_examples": m["find_hubs"](m["main"]["heard_week"], m["main"]["parent"], m["by_id"],
                                                   m["reactions"], 3)}

    return {"scenarios": scen, "budget_plan": budget_plan, "hub_vs_broad": hub_vs_broad,
            "prescriptions": prescriptions(m)}
