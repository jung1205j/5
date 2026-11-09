from frontend.final_features import (raw_metric, weekly_frame, repromo_frame, channel_frame,
                                     scenarios_frame, budget_split, hubs_frame, scenario_payload)


def test_missing_values_are_not_generated():
    result = {"visitors": 61}
    assert raw_metric(result, "visitors_demand") == "자료 대기"
    assert raw_metric(result, "competition_factor") == "자료 대기"
    assert weekly_frame(result).empty
    assert repromo_frame(result).empty
    assert channel_frame(result).empty
    assert scenarios_frame(result).empty
    assert budget_split(result)[0].empty
    assert hubs_frame(result).empty


def test_new_raw_metrics_are_preserved():
    sample = {"visitors_demand": 123, "competition_factor": .88, "daytime_share": .355}
    assert raw_metric(sample, "visitors_demand") == "123"
    assert raw_metric(sample, "competition_factor") == "0.88"
    assert raw_metric(sample, "daytime_share") == "0.355"
    assert raw_metric({"daytime_share": None}, "daytime_share") == "자료 대기"


def test_weekly_and_repromo_keep_actual_rows_only():
    result = {"weekly_visitors": [3, 7, 9],
              "repromo": {"week": 4, "with": [3, 7, 9, 12], "without": [3, 7, 9, 8]}}
    assert weekly_frame(result).visitors.tolist() == [3, 7, 9]
    frame = repromo_frame(result)
    assert frame["with_promo"].tolist() == [3, 7, 9, 12]
    assert frame["without_promo"].tolist() == [3, 7, 9, 8]


def test_channel_and_budget_do_not_normalize_missing_proportions():
    sample = {"channel_share": {"20대이하_학생": {"인스타": .55, "검색": .30, "오류": 150}},
              "scenarios": [{"name": "체험단", "cost": 600000, "visitors_gain": 23}],
              "budget_plan": {"budget": 1000000, "split": {"인스타": 400000, "체험단": 600000}, "visitors_gain": 41},
              "hubs": [{"id": 373, "group": "30대_주부", "dong": "망원2동", "reach": 14}]}
    channels = channel_frame(sample)
    assert set(channels.channel) == {"인스타", "검색"}
    assert [round(x, 4) for x in channels.percent.tolist()] == [55, 30]
    assert scenarios_frame(sample).iloc[0]["visitors_gain"] == 23
    split, plan = budget_split(sample)
    assert split.amount.sum() == 1000000
    assert plan["visitors_gain"] == 41
    assert hubs_frame(sample).iloc[0]["group"] == "30대_주부"


def test_scenario_payload_has_new_hours_but_no_auto_simulation():
    obj = scenario_payload(idea="가게", selected=["연남동"], hours={"open":"10:00", "close":"22:00"},
                           rent=3000000, avg_price=8000, budget=None)
    assert obj["rent"] == 3000000 and obj["budget"] is None
    assert obj["business_hours"]["close"] == "22:00"


def test_final_graph_path_contract():
    from frontend.data_io import VALID_PATHS
    assert {"동네", "동선", "지인", "검색", "인스타", "맘카페", "당근", "에타"}.issubset(VALID_PATHS)
