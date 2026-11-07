
import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")


# 1. JSON 파일 읽기
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# 2. 진단 결과 JSON Schema
DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "dong_code": {"type": "string"},
        "dong": {"type": "string"},
        "seed": {"type": "integer"},
        "visitors": {"type": "integer"},
        "overall_status": {
            "type": "string",
            "enum": ["원활", "확산 정체", "확산 저조", "판단 불가"]
        },
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
                "required": [
                    "group", "path", "reason", "evidence"
                ],
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
        "dong_code",
        "dong",
        "seed",
        "visitors",
        "overall_status",
        "diagnosis",
        "main_causes",
        "affected_groups",
        "recommendations",
        "data_limitations"
    ],
    "additionalProperties": False
}


# 3. AI 진단 함수
def diagnose(result_file):

    # 입력 데이터 불러오기
    simulation = load_json(DATA_DIR / result_file)
    reactions = load_json(DATA_DIR / "reactions.json")

    # 진단 지침
    instructions = """
당신은 지역 상권과 소비자 행동을 분석하는 전문가입니다.

제공된 시뮬레이션 결과와 집단별 반응 데이터를
종합적으로 분석하여 입소문 확산을 진단하세요.

[분석 기준]

1. steps를 분석하여 단계별 확산 현황을 파악합니다.
2. stopped_at을 분석하여 확산이 막힌 집단과 경로를 파악합니다.
3. reactions에서 해당 집단의 관심도, 공유 의향,
   거절 이유를 찾아 분석합니다.
4. 여러 집단에서 반복되는 문제를 주요 원인으로 파악합니다.
5. 각 문제에 적합한 개선 방안을 제안합니다.

[주의사항]

- 반드시 입력 데이터에 근거하여 분석합니다.
- 데이터에 없는 사실은 추측하지 않습니다.
- 확산 경로와 방문 거절 이유를 동일한 원인으로
  단정하지 않습니다.
- 근거가 부족하면 판단 불가 또는 데이터 부족으로 표시합니다.
- visitors는 방문 가능 고객 수이며 실제 방문객 수로
  단정하지 않습니다.
- 모든 결과는 한국어로 작성합니다.
- diagnosis는 3~4문장 이내로 작성합니다.
- main_causes는 주요 원인만 최대 3개 작성합니다.
- recommendations는 실행 가능한 방안을 최대 3개 작성합니다.
"""

    # 입력 데이터 구성
    input_data = {
        "simulation_result": simulation,
        "reactions": reactions
    }

    # OpenAI API 호출
    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=json.dumps(input_data, ensure_ascii=False),
        text={
            "format": {
                "type": "json_schema",
                "name": "business_diagnosis",
                "strict": True,
                "schema": DIAGNOSIS_SCHEMA
            }
        }
    )

    # 응답 상태 확인
    if response.status != "completed":
        raise RuntimeError(
            f"진단 생성이 완료되지 않았습니다: {response.status}"
        )

    # JSON 문자열을 Python 딕셔너리로 변환
    diagnosis = json.loads(response.output_text)

    return diagnosis


# 4. 실행 및 결과 저장
if __name__ == "__main__":

    OUTPUT_DIR.mkdir(exist_ok=True)

    result = diagnose("result_1144068000.json")

    output_path = OUTPUT_DIR / "diagnosis.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

