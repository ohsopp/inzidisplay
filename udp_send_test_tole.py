#!/usr/bin/env python3
"""
TOLE(True Order Little-Endian) UDP 테스트 송신기.

io_variables.json의 변수별 길이(bit) 합만큼 UDP 패킷을 1초 간격으로 전송한다.
정순 리틀엔디안용: Boolean 0/1, Word/Dword는 칼럼 설명에 맞춘 유의미한 더미값(LE 바이트순), String은 hello 고정.
수신 측: PLC UDP Monitor (포트 5212)
"""
import json
import socket
import time
from pathlib import Path

# 설정
HOST = "127.0.0.1"
PORT = 5212
INTERVAL_SEC = 1.0

SCRIPT_DIR = Path(__file__).resolve().parent
IO_VARIABLES_PATH = SCRIPT_DIR / "io_variables.json"

# 칼럼 ID/설명에 맞춘 유의미한 더미값 (TOBE와 동일, Word/Dword는 scale 적용 전 raw 정수)
MEANINGFUL_WORD_DWORD = {
    "currentDieNumber_D140": 42,
    "nextDieNumber_D510": 43,
    "currentDieHeight_D711": 3505,   # 350.5 mm
    "nextDieHeight_D511": 3510,
    "currentBalanceAirPressure_D713": 550,   # 55.0
    "nextBalanceAirPressure_D513": 548,
    "pressAngle_D100": 180,
    "cPMCyclePerMinute_D104": 125,
    "strokePerMinute_D126": 120,
    "crankShaftTempRightFront_D340": 350,
    "crankShaftTempLeftFront_D341": 348,
    "crankShaftTempRightRear_D342": 352,
    "crankShaftTempLeftRear_D343": 345,
    "conrodTempLeft_D330": 340,
    "conrodTempRight_D331": 342,
    "oilSupplyCountSlide_D20": 20,
    "oilSupplyCountBalanceCylinder_D21": 3,
    "oilSupplyCountCrownLeft_D22": 50,
    "oilSupplyCountCrownRight_D23": 50,
    "totalCounter_D1820": 125000,
    "totalCounter_D1821": 125000,
    "productionCounter_D1810": 10000,
    "productionCounter_D1811": 10000,
    "currentProduction_D1812": 8500,
    "currentProduction_D1813": 8500,
    "defficiencyQuantity_D1814": (-1500) & 0xFFFFFFFF,  # 생산계획-현재
    "defficiencyQuantity_D1815": (-1500) & 0xFFFFFFFF,
    "presetCounter_D1816": 5000,       # 목표 일생산량
    "presetCounter_D1817": 5000,
    "production_D1818": 0,
    "production_D1819": 0,
    "todayStrokeCount_D1912": 3200,
    "todayStrokeCount_D1913": 3200,
    "todayRunningTime_D1914": 480,
}


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


def get_meaningful_value(name, length_bits, data_type, scale, description):
    """Boolean: 0/1, Word/Dword: 칼럼에 맞는 값, String: None(hello로 별도 처리)."""
    if data_type == "string":
        return None  # payload에서 "hello{N}" 로 채움
    if data_type == "boolean":
        if "운전준비" in description or "준비" in description or "Green" in name:
            return 1
        if "비상" in description or "알람" in description or "에러" in description or "오류" in description:
            return 0
        return 1 if "해제" in description or "진입" in description else 0
    if data_type == "word" and length_bits == 16:
        return MEANINGFUL_WORD_DWORD.get(name, 0)
    if data_type == "dword" and length_bits == 32:
        return MEANINGFUL_WORD_DWORD.get(name, 0)
    return 0


def value_to_bytes(value, length_bits, data_type, big_endian=False, string_index=0):
    """값을 바이트로 (LE 기본). String이면 hello{N} ASCII (TOLE는 16비트 워드 단위 LE 스왑은 호출처에서)."""
    if data_type == "string":
        byte_count = (length_bits + 7) // 8
        text = f"hello{string_index}" if string_index else "hello"
        ascii_bytes = text.encode("ascii").ljust(byte_count, b"\x00")
        return ascii_bytes
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
    return bytes(reversed(b)) if not big_endian else bytes(b)


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


def swap_16bit_word_bytes(data: bytes) -> bytes:
    """16비트 워드 단위로 바이트 스왑 (리틀엔디안으로 보이도록)."""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        if i + 1 < n:
            out.append(data[i + 1])
            out.append(data[i])
        else:
            out.append(data[i])
        i += 2
    return bytes(out)


def main():
    variables = load_variables()
    total_bits = sum(length for _, length, *_ in variables)
    total_bytes = (total_bits + 7) // 8
    print(f"io_variables.json: 총 비트 = {total_bits}, 바이트 = {total_bytes}")

    total_var_bits = total_bits
    total_bytes = (total_var_bits + 7) // 8
    wire_bits = total_bytes * 8
    padding_bits = wire_bits - total_var_bits

    bits = [0] * padding_bits
    string_index = 0
    for name, length_bits, data_type, scale, description in variables:
        value = get_meaningful_value(name, length_bits, data_type, scale, description)
        if data_type == "string":
            string_index += 1
            raw = value_to_bytes(None, length_bits, data_type, big_endian=False, string_index=string_index)
            raw = swap_16bit_word_bytes(raw)
        else:
            raw = value_to_bytes(value, length_bits, data_type, big_endian=False)
        if data_type == "boolean" and length_bits == 1:
            bits.append(1 if value else 0)
        else:
            bits.extend(bytes_to_bits_be(raw))
    payload = bits_to_bytes(bits)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    counter = 0
    try:
        print(f"매 {INTERVAL_SEC}초마다 같은 데이터를 {HOST}:{PORT} 로 전송합니다. (Ctrl+C 종료)")
        while True:
            sock.sendto(payload, (HOST, PORT))
            counter += 1
            print(f"  전송 #{counter} ({total_bytes} bytes)", end="\r")
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        print("\n종료.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
