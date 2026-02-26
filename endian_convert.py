#!/usr/bin/env python3
"""
리틀엔디안 ↔ 빅엔디안 변환 후 각각 10진수로 출력.

사용법:
  python3 endian_convert.py              # 무한 입력 모드 (한 줄씩 2진수 입력, 빈 줄 또는 Ctrl+C 종료)
  python3 endian_convert.py 01101100 01101101  # 인자 있으면 한 번만 변환 후 종료

입력: 2진수 (0/1만, 공백 허용). 길이는 8의 배수(1바이트 단위).
출력: 빅엔디안 10진수, 리틀엔디안 10진수
"""
import sys


def remove_whitespace(s: str) -> str:
    """문자열에서 모든 공백 문자(스페이스, 탭, 줄바꿈 등) 제거."""
    return "".join(s.split())


def binary_to_bytes(bin_str: str) -> bytes:
    s = remove_whitespace(bin_str)
    if not s:
        raise ValueError("2진수 입력이 비어 있습니다.")
    if len(s) % 8 != 0:
        raise ValueError("2진수 비트 수는 8의 배수여야 합니다 (1바이트 단위).")
    if not all(c in "01" for c in s):
        raise ValueError("2진수는 0과 1만 입력하세요.")
    return bytes(int(s[i : i + 8], 2) for i in range(0, len(s), 8))


def to_big_endian_decimal(b: bytes) -> int:
    """앞 바이트가 상위(MSB). 첫 바이트가 가장 큰 자리."""
    v = 0
    for byte in b:
        v = (v << 8) | byte
    return v


def to_little_endian_decimal(b: bytes) -> int:
    """앞 바이트가 하위(LSB). 첫 바이트가 가장 작은 자리."""
    v = 0
    for i, byte in enumerate(b):
        v |= byte << (8 * i)
    return v


def run_convert(bin_str: str) -> None:
    bin_str = remove_whitespace(bin_str)
    if not bin_str:
        return
    try:
        data = binary_to_bytes(bin_str)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        return
    if not data:
        print("입력된 바이트가 없습니다.", file=sys.stderr)
        return
    # 라벨과 값이 맞도록: 빅엔디안=앞바이트 상위, 리틀엔디안=앞바이트 하위
    be = to_big_endian_decimal(data)
    le = to_little_endian_decimal(data)
    print(f"입력 (2진수): {bin_str}")
    print(f"입력 (hex):   {data.hex()}")
    print(f"빅엔디안 (10진수): {be}")
    print(f"리틀엔디안 (10진수): {le}")


def main():
    if len(sys.argv) >= 2:
        # 인자로 한 번만 실행 (공백 제거 후 한 문자열로)
        run_convert(" ".join(sys.argv[1:]))
        return
    # 무한 입력 (빈 줄은 무시, 종료는 Ctrl+D 또는 Ctrl+C)
    print("2진수 입력 (종료: Ctrl+D 또는 Ctrl+C)")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            continue
        run_convert(line)
        print()


if __name__ == "__main__":
    main()
