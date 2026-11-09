"""Regression tests for the read-only Norunja final UI adapters."""
from frontend.final_features import (
    metric, weekly_frame, repromo_frame, channel_frame, scenarios_frame,
    budget_frame, hubs_frame, input_payload, preview_fields,
)


def test_missing_fields_do_not_invent_results():
    result = {"visitors": 61}
    assert metric(result, "visitors_demand") == "자료 대기"
    assert metric(result, "competition_factor") == "자료 대기"
    assert metric(result, "daytime_share") == "자료 대기"
    assert weekly_frame(result).empty
    assert channel_frame(result).empty
    assert scenarios_frame(result).empty
    assert budget_frame(result).empty
    assert hubs_frame(result).empty


def test_new_metrics_are_read_without_recalculation():
    r = {"visitors_demand": 81, "competition_factor": .83, "daytime_share": .47}
    assert metric(r, "visitors_demand") == "81"
    assert metric(r, "competition_factor") == "0.83"
    assert metric(r, "daytime_share") == "47.0%"


def test_weekly_only_reads_provided_weeks():
    x = {"weekly_visitors": [2, 4, 6],
         "repromo": {"with": [2, 5, 8], "without": [2, 4, 6]}}
    assert weekly_frame(x)["visitors"].tolist() == [2, 4, 6]
    assert repromo_frame(x)["with_promo"].tolist() == [2, 5, 8]


def test_ratios_keep_original_valid_values():
    x = {"channel_share": {"20대이하_학생": {"인스타": .55, "검색": .30, "invalid": 200}}}
    chart = channel_frame(x)
    assert chart["channel"].tolist() == ["인스타", "검색"]
    assert chart["percent"].tolist() == [55, 30]


def test_budget_scenarios_and_hubs_are_only_source_values():
    x = {
        "scenarios": [{"name":"체험단", "cost":600000,"visitors_gain":23}],
        "budget_plan": {"split":{"인스타":400000,"체험단":600000}},
        "hubs": [{"id":373,"group":"30대_주부","dong":"망원1동","reach":14}],
    }
    assert scenarios_frame(x).iloc[0]["visitors_gain"] == 23
    assert int(budget_frame(x)["amount"].sum()) == 1000000
    assert hubs_frame(x).iloc[0]["group"] == "30대_주부"


def test_scenario_input_is_not_a_model_result():
    x = input_payload(idea="디저트 카페", regions=["연남동"],
                      business_hours={"open":"10:00","close":"22:00"},
                      rent=3000000, avg_price=8000, budget=None)
    assert x["budget"] is None
    assert x["business_hours"]["open"] == "10:00"
    assert "visitors" not in x


def test_preview_is_separated_from_real_data():
    example = preview_fields()
    assert len(example["weekly_visitors"]) == 12
    assert example["hubs"][0]["id"].startswith("PREVIEW")
    assert example["daytime_share"] == .47


def test_final_path_names_allowed():
    from frontend.data_io import VALID_PATHS
    assert {"동네", "동선", "지인", "검색", "인스타", "맘카페", "당근", "에타"}.issubset(VALID_PATHS)
