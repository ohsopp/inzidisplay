#!/usr/bin/env python3
"""
TOLE(True Order Little-Endian) UDP 테스트 송신기.

io_variables.json의 변수별 길이(bit) 합만큼 UDP 패킷을 1초 간격으로 전송한다.
String 타입은 16비트 워드 단위 리틀엔디안 바이트 순서로 전송한다.
수신 측을 little-endian 파싱으로 볼 때 hello 문자열이 정상으로 보이도록 맞춘다.
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


def load_variables():
    """io_variables.json을 순서대로 로드. 반환: [(name, length_bits, data_type), ...]"""
    with open(IO_VARIABLES_PATH, "r", encoding="utf-8") as f:
        obj = json.load(f)
    out = []
    for name, val in obj.items():
        if isinstance(val, dict) and "length" in val:
            length = int(val["length"])
            data_type = (val.get("dataType") or "").strip().lower()
        else:
            length = int(val) if isinstance(val, (int, float)) else 0
            data_type = ""
        out.append((name, length, data_type))
    return out


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
    """16비트 워드 단위로 바이트 스왑 (AB CD EF -> BA DC FE)."""
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
    total_bits = sum(length for _, length, _ in variables)
    total_bytes = (total_bits + 7) // 8
    print(f"io_variables.json: 총 비트 = {total_bits}, 바이트 = {total_bytes}")

    total_var_bits = total_bits
    total_bytes = (total_var_bits + 7) // 8
    wire_bits = total_bytes * 8
    padding_bits = wire_bits - total_var_bits

    bits = [0] * padding_bits
    string_index = 0
    for _name, length_bits, data_type in variables:
        if data_type == "string":
            string_index += 1
            text = f"hello{string_index}"
            byte_count = (length_bits + 7) // 8
            ascii_bytes = text.encode("ascii").ljust(byte_count, b"\x00")
            tole_bytes = swap_16bit_word_bytes(ascii_bytes)
            bits.extend(bytes_to_bits_be(tole_bytes))
        else:
            for _ in range(length_bits):
                byte_idx = (len(bits) - padding_bits) // 8
                bit_idx = (len(bits) - padding_bits) % 8
                b = byte_idx % 256
                bits.append((b >> (7 - bit_idx)) & 1)
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
