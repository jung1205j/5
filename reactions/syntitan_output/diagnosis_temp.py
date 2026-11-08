import csv
import json
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
TARGET_CODES = ("1144069000", "1144071000", "1144066000")
TARGET_DONGS = ("망원1동", "연남동", "서교동")


def find_real_data_dir():
    roots = [SCRIPT_DIR, *SCRIPT_DIR.parents, Path.cwd(), *Path.cwd().parents]
    seen = set()
    for root in roots:
        root = root.resolve()
        if root in seen:
            continue
        seen.add(root)
        candidate = root / "frontend" / "data" / "real"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "frontend/data/real 폴더를 찾을 수 없습니다. "
        "diagnosis.py를 저장소 안에 두거나 저장소 루트에서 실행하세요."
    )


DATA_DIR = find_real_data_dir()


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_personas(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def key_name(value):
    return str(value or "").strip().lower().replace(" ", "_")


def build_persona_groups(personas):
    if not personas:
        raise ValueError("personas.csv에 시민 데이터가 없습니다.")

    columns = list(personas[0].keys())
    id_col = next((c for c in columns if key_name(c) in {
        "id", "persona_id", "citizen_id", "user_id"
    }), None)
    if id_col is None:
        raise ValueError("personas.csv에서 시민 ID 열을 찾지 못했습니다.")

    group_col = next((c for c in columns if key_name(c) in {
        "group", "segment", "persona_group", "집단", "그룹"
    }), None)
    if group_col:
        group_cols = [group_col]
    else:
        tokens = ("age", "gender", "job", "occupation", "주부", "직업", "연령", "성별")
        group_cols = [c for c in columns if any(t in key_name(c) for t in tokens)]
        if not group_cols:
            group_cols = [c for c in columns if c != id_col and personas[0].get(c)]

    id_to_group = {}
    populations = Counter()
    for row in personas:
        pid = str(row.get(id_col, "")).strip()
        if not pid:
            continue
        values = [str(row.get(c, "")).strip() for c in group_cols if str(row.get(c, "")).strip()]
        group = "_".join(values) if values else "분류 미상"
        id_to_group[pid] = group
        populations[group] += 1
    return id_to_group, populations, len(id_to_group)


def summarize_steps(steps, id_to_group, populations, total_population):
    step_summaries = []
    cumulative_ids = set()
    heard_ids_by_group = {}

    for step_index, ids in enumerate(steps, start=1):
        new_ids = {str(pid) for pid in ids}
        cumulative_ids.update(new_ids)
        step_counts = Counter()
        for pid in new_ids:
            group = id_to_group.get(pid, "페르소나 정보 없음")
            step_counts[group] += 1
            heard_ids_by_group.setdefault(group, set()).add(pid)
        step_summaries.append({
            "step": step_index,
            "newly_heard_count": len(new_ids),
            "newly_heard_by_group": dict(step_counts),
            "cumulative_heard_count": len(cumulative_ids),
            "overall_awareness_rate": round(len(cumulative_ids) / total_population, 4)
            if total_population else None,
        })

    group_awareness = []
    for group, population in populations.items():
        heard = len(heard_ids_by_group.get(group, set()))
        group_awareness.append({
            "group": group,
            "population": population,
            "heard_count": heard,
            "awareness_rate": round(heard / population, 4) if population else None,
        })

    return {
        "population_total": total_population,
        "unique_people_heard": len(cumulative_ids),
        "overall_awareness_rate": round(len(cumulative_ids) / total_population, 4)
        if total_population else None,
        "steps": step_summaries,
        "group_awareness": sorted(group_awareness, key=lambda x: x["group"]),
    }


DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "diagnosis": {"type": "string"},
        "main_causes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cause": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["cause", "description"],
                "additionalProperties": False
            }
        },
        "affected_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "group": {"type": "string"},
                    "path": {"type": "string"},
                    "reason": {"type": "string"},
                    "evidence": {"type": "string"}
                },
                "required": ["group", "path", "reason", "evidence"],
                "additionalProperties": False
            }
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"}
        },
        "data_limitations": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "diagnosis", "main_causes", "affected_groups",
        "recommendations", "data_limitations"
    ],
    "additionalProperties": False
}


def get_scenario(data_dir):
    scenario_path = data_dir / "scenario.json"
    scenario = load_json(scenario_path) if scenario_path.exists() else {}
    idea = os.getenv("BUSINESS_IDEA") or scenario.get("business_idea", "")
    raw_candidates = os.getenv("CANDIDATE_DONGS")
    if raw_candidates:
        try:
            candidates = json.loads(raw_candidates)
        except json.JSONDecodeError:
            candidates = [x.strip() for x in raw_candidates.split(",") if x.strip()]
    else:
        candidates = scenario.get("candidate_dongs", list(TARGET_DONGS))
    return idea, candidates


def overall_status(awareness_rate):
    if awareness_rate is None:
        return "판단 불가"
    if awareness_rate >= 0.40:
        return "원활"
    if awareness_rate >= 0.15:
        return "확산 정체"
    return "확산 저조"


def diagnose(result_path, data_dir):
    simulation = load_json(result_path)
    personas = load_personas(data_dir / "personas.csv")
    reactions = load_json(data_dir / "reactions.json")
    id_to_group, populations, total_population = build_persona_groups(personas)
    summary = summarize_steps(
        simulation.get("steps", []), id_to_group, populations, total_population
    )
    business_idea, candidates = get_scenario(data_dir)

    instructions = """
당신은 지역 상권 소비자 반응과 입소문 시뮬레이션을 진단하는 분석가입니다.
입력된 가게 아이디어, 후보 동네, 집단별 반응과 확산 요약을 종합하세요.

[시뮬레이션 규칙]
- interest와 share는 각 질문에 대한 1~5점 응답의 평균입니다. 점수가 높을수록 관심 또는 공유 의향이 높습니다.
- stopped_at은 인지율이 10% 미만인 집단과, 소식을 전달하려다 가장 많이 실패한 경로를 기록합니다.
- stopped_at의 path는 실패가 기록된 경로일 뿐, 그 경로 자체가 원인이라는 뜻은 아닙니다.
- 반응은 서울 시민에게 “집 근처에 생긴다면”이라는 조건으로 물었습니다. 거리나 이동 부담은 반응 원인이 아니므로 원인으로 제시하지 마세요.

[분석 순서]
1. 단계별 새로 들은 사람 수, 집단별 인지율, 전체 인지율로 확산 양상을 확인합니다.
2. 소식을 들은 집단 중 interest가 낮은 집단을 찾아 아이디어/가격/메뉴 반응 근거를 확인합니다.
3. interest는 높지만 인지율이 낮거나 share가 낮은 집단을 구분해 홍보 채널/전달 병목을 살핍니다.
4. stopped_at의 집단과 경로는 중단 위치로만 해석하고, 원인은 반응 점수와 수치로 별도 뒷받침합니다.
5. 근거가 부족한 내용은 단정하지 말고 데이터 한계로 표시합니다.

[주의사항]
- 입력에 없는 사실이나 시민 심리를 만들어내지 않습니다.
- visitors는 방문 가능 고객 수이며 실제 방문객/매출이 아닙니다.
- 전체 인지율 40% 이상은 원활, 15% 이상 40% 미만은 확산 정체, 15% 미만은 확산 저조로 코드에서 결정됩니다.
- 한국어로 작성하고 diagnosis는 3~4문장, 주요 원인과 추천은 각각 최대 3개로 제한합니다.
- path 또는 거리/이동 부담을 원인으로 단정하지 않습니다.
"""

    input_data = {
        "business_idea": business_idea,
        "candidate_dongs": candidates,
        "simulation_result": {
            "dong_code": simulation.get("dong_code"),
            "dong": simulation.get("dong"),
            "seed": simulation.get("seed"),
            "visitors": simulation.get("visitors"),
            "stopped_at": simulation.get("stopped_at", []),
            "step_summary": summary,
        },
        "reactions": reactions,
    }

    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=json.dumps(input_data, ensure_ascii=False),
        text={
            "format": {
                "type": "json_schema",
                "name": "business_diagnosis",
                "strict": True,
                "schema": DIAGNOSIS_SCHEMA,
            }
        },
    )
    if response.status != "completed":
        raise RuntimeError(f"진단 생성이 완료되지 않았습니다: {response.status}")

    result = json.loads(response.output_text)
    rate = summary["overall_awareness_rate"]
    return {
        "dong_code": str(simulation["dong_code"]),
        "dong": simulation["dong"],
        "seed": int(simulation["seed"]),
        "visitors": int(simulation["visitors"]),
        "overall_status": overall_status(rate),
        **result,
    }


def main():
    data_dir = find_real_data_dir()
    for filename in ("personas.csv", "reactions.json"):
        if not (data_dir / filename).exists():
            raise FileNotFoundError(f"필수 데이터 파일이 없습니다: {data_dir / filename}")

    paths = [data_dir / f"result_{code}.json" for code in TARGET_CODES]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("다음 시뮬레이션 결과 파일이 없습니다:\n" + "\n".join(missing))

    for result_path in paths:
        diagnosis = diagnose(result_path, data_dir)
        output_path = data_dir / f"diagnosis_{diagnosis['dong_code']}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(diagnosis, f, ensure_ascii=False, indent=2)
        print(f"저장 완료: {output_path}")


if __name__ == "__main__":
    main()