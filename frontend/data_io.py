"""Shared data contract for the 2026 AI hackathon LocalSim frontend.

User-provided spec: personas.csv, reactions.json, result_{dong_code}.json,
validation_log.json, all with UTF-8 and lowercase English field names.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import pandas as pd

PERSONA_COLUMNS = {"id", "dong_code", "dong", "age", "gender", "job", "lat", "lng", "group"}
REACTION_FIELDS = {"group", "interest", "share", "reason_type", "reason_text", "community"}
RESULT_FIELDS = {"dong_code", "dong", "seed", "steps", "visitors", "stopped_at"}
VALID_JOBS = {"학생", "직장인", "주부", "자영업", "기타"}
VALID_AGES = {"20대이하", "30대", "40대", "50대이상"}
VALID_REASONS = {"가격", "거리", "분위기", "메뉴", "관심없음", "기타", "시간"}
VALID_COMMUNITIES = {"에타", "맘카페", "당근", "인스타", "없음"}
VALID_PATHS = VALID_COMMUNITIES - {"없음"} | {"동네"}
VALIDATION_FIELDS = {"round", "date", "target", "rank_corr", "seed_runs", "weights", "mismatch", "next"}
FIELD_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")


def check_lowercase_keys(keys, description: str):
    invalid = sorted(k for k in keys if not isinstance(k, str) or not FIELD_NAME_PATTERN.fullmatch(k))
    if invalid:
        raise DataContractError(f"{description}: 필드명은 영문 소문자/숫자/밑줄이어야 합니다: {invalid}")


class DataContractError(ValueError):
    pass


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise DataContractError(f"{path.name}: JSON을 읽을 수 없습니다 — {e}") from e


def read_personas(folder: Path) -> pd.DataFrame:
    path = folder / "personas.csv"
    if not path.exists():
        raise DataContractError(f"{path} 파일이 없습니다.")
    try:
        df = pd.read_csv(path, dtype={"dong_code": str}, encoding="utf-8")
    except Exception as e:
        raise DataContractError(f"personas.csv 읽기 오류: {e}") from e
    check_lowercase_keys(df.columns, "personas.csv")
    missing = PERSONA_COLUMNS - set(df.columns)
    if missing:
        raise DataContractError(f"personas.csv 필수 열 누락: {', '.join(sorted(missing))}")
    df = df.copy()
    for field in ("id", "lat", "lng"):
        df[field] = pd.to_numeric(df[field], errors="coerce")
    if df[["id", "lat", "lng"]].isna().any().any():
        raise DataContractError("personas.csv의 id/lat/lng는 유효한 숫자여야 합니다.")
    if not (df["id"] % 1 == 0).all():
        raise DataContractError("personas.csv의 id는 정수여야 합니다.")
    df["id"] = df["id"].astype(int)
    if df["id"].duplicated().any():
        raise DataContractError("personas.csv에서 시민 id가 중복되었습니다.")
    if not df["lat"].between(-90, 90).all() or not df["lng"].between(-180, 180).all():
        raise DataContractError("personas.csv 위도/경도 범위 오류")
    df["dong_code"] = df["dong_code"].astype(str)
    if df[["dong_code", "group", "dong", "job"]].isna().any().any():
        raise DataContractError("personas.csv의 dong_code/group/dong/job은 비어 있을 수 없습니다.")
    if (df[["dong_code", "group", "dong", "job"]].astype(str).apply(lambda c: c.str.strip() == "")).any().any():
        raise DataContractError("personas.csv의 dong_code/group/dong/job에 빈 문자열이 있습니다.")
    if not df["job"].isin(VALID_JOBS).all():
        raise DataContractError("personas.csv의 job에는 학생/직장인/주부/자영업/기타만 사용합니다.")
    expected_groups = {f"{age}_{job}" for age in VALID_AGES for job in VALID_JOBS}
    invalid_groups = set(df["group"].astype(str)) - expected_groups
    if invalid_groups:
        raise DataContractError(f"personas.csv의 group 형식이 팀 규약과 다릅니다: {sorted(invalid_groups)}")
    if path.parent.name == "real":
        invalid_codes = sorted(c for c in df["dong_code"].unique() if not re.fullmatch(r"[0-9]{10}", c))
        if invalid_codes:
            raise DataContractError(f"실데이터 dong_code는 10자리 행정동 코드여야 합니다: {invalid_codes[:8]}")
    return df


def read_reactions(folder: Path, person_df: pd.DataFrame) -> list[dict]:
    path = folder / "reactions.json"
    if not path.exists():
        return []  # C frontend should still render without A's results
    obj = load_json(path)
    if not isinstance(obj, list):
        raise DataContractError("reactions.json 최상위 항목은 배열이어야 합니다.")
    for i, r in enumerate(obj):
        if not isinstance(r, dict) or not REACTION_FIELDS.issubset(r):
            raise DataContractError(f"reactions.json {i}번째 요소의 필수 필드를 확인하세요.")
        check_lowercase_keys(r.keys(), f"reactions.json {i}번째 요소")
        try:
            interest = float(r["interest"])
            share = float(r["share"])
        except (ValueError, TypeError) as exc:
            raise DataContractError(f"reactions.json {i}번째 interest/share는 숫자 1~5여야 합니다.") from exc
        if not (1 <= interest <= 5 and 1 <= share <= 5):
            raise DataContractError(f"reactions.json {i}번째 interest/share 값은 1~5입니다.")
        if r["reason_type"] not in VALID_REASONS:
            raise DataContractError(f"reactions.json {i}번째 reason_type에 팀 규약 외 값이 있습니다.")
        if not isinstance(r["community"], list):
            raise DataContractError(f"reactions.json {i}번째 community는 배열입니다.")
        if any(v not in VALID_COMMUNITIES for v in r["community"]):
            raise DataContractError(f"reactions.json {i}번째 community 값이 팀 규약과 다릅니다.")
    groups = [str(r["group"]) for r in obj]
    if len(groups) != len(set(groups)):
        raise DataContractError("reactions.json의 group이 중복되었습니다.")
    absent = set(person_df["group"].unique()) - set(groups)
    if absent:
        raise DataContractError(f"reactions.json에 없는 집단: {', '.join(sorted(absent))}")
    return obj


def read_results(folder: Path, person_df: pd.DataFrame) -> list[dict]:
    files = sorted(folder.glob("result_*.json"))
    if not files:
        raise DataContractError(f"{folder}에 result_{{동코드}}.json 파일이 없습니다.")
    person_ids = set(person_df["id"].tolist())
    result = []
    seen_dongs = set()
    for path in files:
        obj = load_json(path)
        if not isinstance(obj, dict) or not RESULT_FIELDS.issubset(obj):
            raise DataContractError(f"{path.name}: 필수 필드 누락")
        check_lowercase_keys(obj.keys(), path.name)
        if not isinstance(obj["dong_code"], str):
            raise DataContractError(f"{path.name}: dong_code는 문자열이어야 합니다.")
        dong_code = obj["dong_code"]
        if path.stem != f"result_{dong_code}":
            raise DataContractError(f"{path.name}: 파일명의 동 코드와 JSON dong_code가 다릅니다.")
        if dong_code in seen_dongs:
            raise DataContractError(f"{path.name}: 중복 동 코드")
        seen_dongs.add(dong_code)
        steps = obj["steps"]
        if not isinstance(steps, list) or any(not isinstance(s, list) for s in steps):
            raise DataContractError(f"{path.name}: steps는 [[시민 ID, ...], ...] 형식입니다.")
        flat_ids = [pid for step in steps for pid in step]
        if any(type(pid) is not int for pid in flat_ids):
            raise DataContractError(f"{path.name}: 시민 ID는 정수여야 합니다.")
        if len(flat_ids) != len(set(flat_ids)):
            raise DataContractError(f"{path.name}: steps에 동일 시민 ID가 중복 등장합니다(새 노출만 기록).")
        invalid = set(flat_ids) - person_ids
        if invalid:
            raise DataContractError(f"{path.name}: personas.csv에 없는 시민 ID: {sorted(invalid)[:8]}")
        if not isinstance(obj["stopped_at"], list):
            raise DataContractError(f"{path.name}: stopped_at은 배열이어야 합니다.")
        for i, stop in enumerate(obj["stopped_at"]):
            if not isinstance(stop, dict) or not {"group", "path"}.issubset(stop):
                raise DataContractError(f"{path.name}: stopped_at[{i}]에는 group/path가 있어야 합니다.")
            check_lowercase_keys(stop.keys(), f"{path.name} stopped_at[{i}]")
            if stop["group"] not in set(person_df["group"]):
                raise DataContractError(f"{path.name}: 존재하지 않는 정체 집단: {stop['group']}")
            if stop["path"] not in VALID_PATHS:
                raise DataContractError(f"{path.name}: 팀 규약에 없는 정체 경로: {stop['path']}")
        if not isinstance(obj["visitors"], int) or obj["visitors"] < 0:
            raise DataContractError(f"{path.name}: visitors는 0 이상 정수여야 합니다.")
        result.append(obj)
    return result


def load_dataset(folder: Path):
    persons = read_personas(folder)
    reactions = read_reactions(folder, persons)
    results = read_results(folder, persons)
    geo = None
    geopath = folder / "dongs.geojson"
    if geopath.exists():
        geo = load_json(geopath)
        if not isinstance(geo, dict) or geo.get("type") not in ("FeatureCollection", "Feature"):
            raise DataContractError("dongs.geojson이 올바른 GeoJSON이 아닙니다.")
    validations = []
    vpath = folder / "validation_log.json"
    if vpath.exists():
        validations = load_json(vpath)
        if not isinstance(validations, list):
            raise DataContractError("validation_log.json 최상위 항목은 배열이어야 합니다.")
        for i, log in enumerate(validations):
            if not isinstance(log, dict) or not VALIDATION_FIELDS.issubset(log):
                raise DataContractError(f"validation_log.json {i}번째 기록 필드가 부족합니다.")
            check_lowercase_keys(log.keys(), f"validation_log.json {i}번째 기록")
    edgepath = folder / "edges.json"
    if edgepath.exists():
        edges = load_json(edgepath)
        if not isinstance(edges, list):
            raise DataContractError("edges.json 최상위 항목은 배열이어야 합니다.")
        person_ids = set(persons["id"].tolist())
        for i, edge in enumerate(edges):
            if not isinstance(edge, dict) or not {"from", "to", "type"}.issubset(edge):
                raise DataContractError(f"edges.json {i}번째 관계의 필수 필드가 없습니다.")
            check_lowercase_keys(edge.keys(), f"edges.json {i}번째 관계")
            if edge["type"] not in VALID_PATHS:
                raise DataContractError(f"edges.json {i}번째 type에 팀 규약 외 값이 있습니다: {edge['type']}")
            if type(edge["from"]) is not int or type(edge["to"]) is not int or edge["from"] not in person_ids or edge["to"] not in person_ids:
                raise DataContractError(f"edges.json {i}번째 관계에 없는 시민 ID가 있습니다.")
    return {"persons": persons, "reactions": reactions, "results": results,
            "geo": geo, "validations": validations}


def exposed_until(steps: list[list[int]], current_step: int) -> tuple[set[int], set[int]]:
    """Return (cumulative exposed, newly exposed) for 0-based step.

    -1 is the baseline before any diffusion event.
    """
    if current_step < 0:
        return set(), set()
    upto = steps[:current_step+1]
    cumulative = {pid for part in upto for pid in part}
    latest = set(steps[current_step]) if current_step < len(steps) else set()
    return cumulative, latest
