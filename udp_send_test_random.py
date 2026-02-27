#!/usr/bin/env python3
"""
UDP 테스트 송신기: udp_send_test_tobe.py와 동일한 length/주소 구조.
String은 제외하고 Boolean/Word/Dword만 매번 랜덤 값으로 전송. String은 고정(hello 등).
수신 측: PLC UDP Monitor (포트 5212)
"""
import json
import random
import socket
import time
from pathlib import Path

# 설정
HOST = "127.0.0.1"
PORT = 5212
INTERVAL_SEC = 1.0

SCRIPT_DIR = Path(__file__).resolve().parent
IO_VARIABLES_PATH = SCRIPT_DIR / "io_variables.json"


def load_variables():
    """io_variables.json을 순서대로 로드. 반환: [(name, length_bits, data_type, scale, description), ...]"""
    with open(IO_VARIABLES_PATH, "r", encoding="utf-8") as f:
        obj = json.load(f)
    out = []
    for name, val in obj.items():
        if isinstance(val, dict) and "length" in val:
            length = int(val["length"])
            data_type = (val.get("dataType") or "").strip().lower()
            scale = (val.get("scale") or "1").strip()
            description = (val.get("description") or "").strip()
        else:
            length = int(val) if isinstance(val, (int, float)) else 0
            data_type = ""
            scale = "1"
            description = ""
        out.append((name, length, data_type, scale, description))
    return out


def build_string_groups(variables):
    """연속된 String 변수를 같은 base로 묶음. 반환: { base: [(name, length_bits), ...] }"""
    groups = {}
    for name, length_bits, data_type, *_ in variables:
        if data_type != "string":
            continue
        base = name.rsplit("_", 1)[0] if "_" in name else name
        groups.setdefault(base, []).append((name, length_bits))
    return groups


def get_random_value(name, length_bits, data_type, scale, description):
    """String이면 None(별도 처리), Boolean은 0/1 랜덤, Word/Dword는 범위 내 랜덤."""
    if data_type == "string":
        return None
    if data_type == "boolean":
        return 1 if random.random() < 0.5 else 0
    if data_type == "word" and length_bits == 16:
        return random.randint(0, 0xFFFF)
    if data_type == "dword" and length_bits == 32:
        return random.randint(0, 0xFFFFFFFF)
    byte_count = (length_bits + 7) // 8
    max_v = (1 << length_bits) - 1 if length_bits <= 64 else 0xFFFFFFFF
    return random.randint(0, min(max_v, 0xFFFFFFFF))


def value_to_bytes(value, length_bits, data_type, big_endian=True, string_chunk=None):
    """값을 바이트로. string_chunk: String일 때 이 구간에 넣을 바이트."""
    if data_type == "string" and string_chunk is not None:
        byte_count = (length_bits + 7) // 8
        return string_chunk.ljust(byte_count, b"\x00")[:byte_count]
    if value is None:
        byte_count = (length_bits + 7) // 8
        return bytes(byte_count)
    if data_type == "boolean":
        return bytes([1 if value else 0])
    if length_bits == 16:
        v = int(value) & 0xFFFF
        if big_endian:
            return bytes([(v >> 8) & 0xFF, v & 0xFF])
        return bytes([v & 0xFF, (v >> 8) & 0xFF])
    if length_bits == 32:
        v = int(value) & 0xFFFFFFFF
        if big_endian:
            return bytes([(v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF])
        return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF])
    byte_count = (length_bits + 7) // 8
    v = int(value) & ((1 << length_bits) - 1)
    b = []
    for i in range(byte_count - 1, -1, -1):
        b.append((v >> (i * 8)) & 0xFF)
    return bytes(b) if big_endian else bytes(reversed(b))


def bytes_to_bits_be(b: bytes):
    """바이트를 비트 리스트로 (바이트당 MSB 먼저)."""
    bits = []
    for byte in b:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
    return bits


def bits_to_bytes(bits: list) -> bytes:
    """비트 리스트를 바이트로 패킹 (8비트=1바이트, MSB 먼저)."""
    out = []
    for i in range(0, len(bits), 8):
        chunk = bits[i : i + 8]
        byte = sum(b << (7 - j) for j, b in enumerate(chunk))
        out.append(byte)
    return bytes(out)


def build_payload(variables, group_full_strings, base_offset):
    """base_offset 기준으로 String 구간 채우고, Boolean/Word/Dword는 랜덤. tobe와 동일 비트/바이트 구조."""
    total_var_bits = sum(length for _, length, *_ in variables)
    total_bytes = (total_var_bits + 7) // 8
    wire_bits = total_bytes * 8
    padding_bits = wire_bits - total_var_bits

    bits = [0] * padding_bits
    offset = dict(base_offset)
    for name, length_bits, data_type, scale, description in variables:
        if data_type == "string":
            base = name.rsplit("_", 1)[0] if "_" in name else name
            off = offset.get(base, 0)
            chunk_len = length_bits // 8
            full = group_full_strings.get(base, b"")
            chunk = full[off : off + chunk_len] if off < len(full) else bytes(chunk_len)
            offset[base] = off + chunk_len
            raw = value_to_bytes(None, length_bits, data_type, big_endian=True, string_chunk=chunk)
            bits.extend(bytes_to_bits_be(raw))
        else:
            value = get_random_value(name, length_bits, data_type, scale, description)
            if data_type == "boolean" and length_bits == 1:
                bits.append(1 if value else 0)
            else:
                raw = value_to_bytes(value, length_bits, data_type, big_endian=True)
                bits.extend(bytes_to_bits_be(raw))
    return bits_to_bytes(bits)


def main():
    variables = load_variables()
    total_var_bits = sum(length for _, length, *_ in variables)
    total_bytes = (total_var_bits + 7) // 8
    print(f"io_variables.json: 총 비트 = {total_var_bits}, 바이트 = {total_bytes}")
    print("String 제외 Boolean/Word/Dword 매번 랜덤 전송. String은 고정(hello 등).")

    # String 그룹별 고정 문자열 (tobe와 동일)
    string_groups = build_string_groups(variables)
    group_full_strings = {}
    for base, items in string_groups.items():
        total_s = sum(length_bits // 8 for _, length_bits in items)
        group_full_strings[base] = "hello".encode("ascii").ljust(total_s, b"\x00")[:total_s]
    base_offset = {base: 0 for base in string_groups}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    counter = 0
    try:
        print(f"매 {INTERVAL_SEC}초마다 랜덤 데이터를 {HOST}:{PORT} 로 전송합니다. (Ctrl+C 종료)")
        while True:
            payload = build_payload(variables, group_full_strings, base_offset)
            sock.sendto(payload, (HOST, PORT))
            counter += 1
            print(f"  전송 #{counter} ({len(payload)} bytes)", end="\r")
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        print("\n종료.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
