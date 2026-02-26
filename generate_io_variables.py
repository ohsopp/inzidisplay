#!/usr/bin/env python3
"""
PLC IO List 기반 변수 정보 매핑 생성 스크립트.

iolist.csv에서 변수명, Length, DataType, scale, Description을 읽어
io_variables.json을 생성한다. (UDP 파싱용 length 포함)
"""

import csv
import re
import json
from pathlib import Path


def parameter_to_camel_case(text: str) -> str:
    """
    Parameter (English) 문자열을 camelCase로 변환한다.
    - 공백, 괄호, 슬래시, 하이픈 등으로 단어 분리
    - 첫 단어는 소문자, 이후 각 단어의 첫 글자는 대문자
    - 영숫자만 유지
    """
    if not text or not str(text).strip():
        return ""
    text = str(text).strip()
    # 영문자, 숫자, 공백만 남기고 나머지는 공백으로 치환 후 단어 분리
    words = re.sub(r"[^\w\s]", " ", text, flags=re.ASCII)
    words = re.sub(r"_+", " ", words)
    words = words.split()
    if not words:
        return ""
    result = [words[0].lower()]
    for w in words[1:]:
        if w:
            result.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
    return "".join(result)


def make_variable_name(parameter_en: str, address: str, none_counter: list) -> str:
    """
    변수명 생성: {camelCaseParameter}_{address}
    Parameter(English)가 비어 있으면 None1_{address}, None2_{address}, ... 형태로 사용.
    """
    address = str(address).strip() if address else ""
    if not address:
        return ""

    base = parameter_to_camel_case(parameter_en) if parameter_en else ""
    if not base:
        none_counter[0] += 1
        base = f"None{none_counter[0]}"
    # 변수명에 허용되지 않는 문자 정리 (주소는 그대로 두기)
    base = re.sub(r"[^a-zA-Z0-9_]", "", base)
    if not base:
        none_counter[0] += 1
        base = f"None{none_counter[0]}"
    return f"{base}_{address}"


def load_iolist_csv(csv_path: str | Path) -> list[dict]:
    """
    iolist.csv를 로드하여 최소 컬럼 Parameter(English), Address, Length 를 가진 행 목록 반환.
    빈 행, Address/Length 없는 행은 제외하지 않고 반환 (호출 쪽에서 필터링 가능).
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return rows
        for row in reader:
            rows.append(row)
    return rows


def get_cell(row: dict, *keys: str) -> str:
    """컬럼명 정규화: 공백/괄호 등 포함 가능."""
    for k in keys:
        if k in row:
            return (row[k] or "").strip()
        for header in row:
            if header.strip().lower().replace(" ", "") == k.lower().replace(" ", ""):
                return (row[header] or "").strip()
    return ""


def build_variable_info_list(csv_path: str | Path) -> list[dict]:
    """
    CSV를 읽어 변수별 정보 리스트를 반환.
    각 항목: variableName, length(비트), dataType, scale, description
    CSV 정의 순서대로 연속된 바이너리 스트림 순서를 유지한다.
    """
    rows = load_iolist_csv(csv_path)
    result = []
    none_counter = [0]

    for row in rows:
        param_en = get_cell(row, "Parameter(English)", "Parameter (English)")
        address = get_cell(row, "Address")
        data_type_raw = get_cell(row, "DataType")
        scale_str = get_cell(row, "scale")
        description = get_cell(row, "Description")

        if not address:
            continue
        type_lengths = {"boolean": 1, "word": 16, "dword": 32, "string": 128}
        length = type_lengths.get(data_type_raw.strip().lower(), 16)
        data_type = data_type_raw.strip() or ""
        scale = scale_str if scale_str else ""

        var_name = make_variable_name(param_en, address, none_counter)
        if var_name:
            result.append({
                "variableName": var_name,
                "length": length,
                "dataType": data_type,
                "scale": scale,
                "description": description,
            })

    return result


def main():
    base = Path(__file__).resolve().parent
    csv_path = base / "iolist.csv"
    info_list = build_variable_info_list(csv_path)

    # io_variables.json: 변수명 -> { length, dataType, scale, description } (순서 유지)
    obj = {
        item["variableName"]: {
            "length": item["length"],
            "dataType": item["dataType"],
            "scale": item["scale"],
            "description": item["description"],
        }
        for item in info_list
    }
    out_json = base / "io_variables.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"Written: {out_json} ({len(obj)} variables)")

if __name__ == "__main__":
    main()
