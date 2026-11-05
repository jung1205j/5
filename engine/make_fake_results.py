import csv, json, random
from pathlib import Path

FOLDER = Path("data/fake")
SEED = 42
rng = random.Random(SEED)
PATHS = ["동네", "에타", "맘카페", "당근", "인스타"]
CANDIDATES = {"1144069000": "망원1동", "1144071000": "연남동", "1144066000": "서교동"}

with open(FOLDER / "personas.csv", encoding="utf-8") as f:
    personas = list(csv.DictReader(f))
groups = sorted({p["group"] for p in personas})

for dong_code, dong in CANDIDATES.items():
    local = [int(p["id"]) for p in personas if p["dong_code"] == dong_code]
    others = [int(p["id"]) for p in personas if p["dong_code"] != dong_code]
    rng.shuffle(local); rng.shuffle(others)
    print(f"{dong}: 동 안 시민 {len(local)}명")  # 0명이면 페르소나 dong_code 확인 필요

    steps = [local[:3], local[3:8] + others[:3], others[3:10]]
    result = {
        "dong_code": dong_code,
        "dong": dong,
        "seed": SEED,
        "steps": [s for s in steps if s],
        "visitors": rng.randint(50, 200),
        "stopped_at": [{"group": g, "path": rng.choice(PATHS)}
                       for g in rng.sample(groups, min(2, len(groups)))],
    }
    with open(FOLDER / f"result_{dong_code}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("저장:", f"result_{dong_code}.json")