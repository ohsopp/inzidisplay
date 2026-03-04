#!/usr/bin/env python3
"""
시작주소(디바이스+번호), 데이터 타입, length를 입력받아 3E 요청 패킷을 만들어
PLC(192.168.0.5:5002)로 전송하고, 요청/응답 패킷을 콘솔에 출력.
이 PC는 192.168.0.41:2025 로 나감.

- 실행 예시 -
# Y107 1비트 (기존과 동일)
python3 backend/plc_tcp_send.py --device Y --address 107 --type boolean --length 1

# D140 워드 1개
python3 backend/plc_tcp_send.py --device D --address 140 --type word --length 1

# D1810 Dword 1개 (2워드)
python3 backend/plc_tcp_send.py --device D --address 1810 --type dword --length 1

# D1560 문자열 16바이트(8워드)
python3 backend/plc_tcp_send.py --device D --address 1560 --type string --length 16
"""
import argparse
import socket
import sys

PLC_HOST = "192.168.0.5"
PLC_PORT = 5002
LOCAL_IP = "192.168.0.41"
LOCAL_PORT = 2025
TIMEOUT = 5.0

# 3E 디바이스 코드 (해당 PLC)
DEVICE_CODES = {"Y": 0x9D, "M": 0x90, "D": 0xA8}


def parse_address(s: str) -> int:
    """주소 문자열 해석. 0x 접두사 있으면 16진수, 없으면 10진수. D140 → 140(10진), 0x8C → 140."""
    s = (s or "").strip()
    if not s:
        raise ValueError("주소가 비어 있음")
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)


def num_words_from_type(data_type: str, length: int) -> int:
    """
    데이터 타입과 length로 요청할 워드 수 계산.
    boolean: length=비트 수 → 워드 수(최소 1).
    word: length=워드 개수.
    dword: length=Dword 개수 → 워드 수 = length*2.
    string: length=바이트 수(문자 수) → 워드 수 = ceil(length/2).
    """
    t = (data_type or "").strip().lower()
    if t == "boolean":
        return max(1, (length + 15) // 16)
    if t == "word":
        return max(1, length)
    if t == "dword":
        return max(1, length * 2)
    if t == "string":
        return max(1, (length + 1) // 2)
    return max(1, length)


def build_3e_0401_read(device: str, start_address: int, num_words: int) -> bytes:
    """3E 프레임 0401(워드 배치 읽기) 요청 패킷 생성. 헤더+바디."""
    device = (device or "D").upper()
    device_code = DEVICE_CODES.get(device, 0xA8)
    # Y/M/D 공통: 주소는 16진수로 받은 값을 24비트 그대로 사용. Y107(0x107=263) → 07 01 00
    addr24 = start_address & 0xFFFFFF
    addr3 = addr24.to_bytes(3, "little")
    points = num_words.to_bytes(2, "little")
    timer_value = 0x0010
    cmd = 0x0401
    subcmd = (0).to_bytes(2, "little")  # 0401 워드 배치 읽기 서브커맨드 0
    request_body = (
        timer_value.to_bytes(2, "little")
        + cmd.to_bytes(2, "little")
        + subcmd
        + addr3
        + bytes([device_code])
        + points
    )
    body_len = len(request_body)
    subheader = b"\x50\x00"
    header = (
        subheader
        + bytes([0x00, 0xFF])
        + (0x03FF).to_bytes(2, "little")
        + bytes([0x00])
        + body_len.to_bytes(2, "little")
    )
    return header + request_body


def hex_line(data: bytes) -> str:
    return " ".join(data.hex().upper()[i : i + 2] for i in range(0, len(data.hex()), 2))


def wireshark_hex_dump(data: bytes, bytes_per_line: int = 16) -> str:
    """와이어샤크와 동일: 왼쪽 오프셋(4자리 hex), 중간 hex(16바이트/줄), 오른쪽 ASCII."""
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i : i + bytes_per_line]
        offset = f"{i:04x}"
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        if len(chunk) < bytes_per_line:
            hex_part += "   " * (bytes_per_line - len(chunk))
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset}   {hex_part}   {ascii_part}")
    return "\n".join(lines)


# 3E 응답: 해당 PLC는 헤더 9바이트(Subheader+경로+데이터길이), 이후 End code(2)+Read data
# 패킷 센더와 동일한 응답을 받으려면 '헤더 9바이트 수신 → 길이 필드만큼만 추가 수신' (뒤에 오는 잔여 데이터 미수신)
RESPONSE_HEADER_LEN = 9
END_CODE_LEN = 2


def parse_3e_response(data: bytes) -> tuple[bytes, bytes, bytes] | None:
    """3E 응답 패킷을 (헤더, End code, Read data)로 파싱. 부족하면 None."""
    if len(data) < RESPONSE_HEADER_LEN + END_CODE_LEN:
        return None
    header = data[:RESPONSE_HEADER_LEN]
    end_code = data[RESPONSE_HEADER_LEN : RESPONSE_HEADER_LEN + END_CODE_LEN]
    # Read data = End code(2) 이후
    read_data = data[RESPONSE_HEADER_LEN + END_CODE_LEN :]
    return header, end_code, read_data


def format_read_data_value(read_data: bytes, data_type: str, length: int) -> str:
    """Read data 바이트를 요청한 타입에 맞게 해석해 설명 문자열 반환."""
    t = (data_type or "").strip().lower()
    lines = []

    if t == "boolean":
        # 1워드 = 2바이트. PLC는 워드를 빅엔디안(상위바이트 먼저)으로 보냄. 값 1 → 00 01 (LSB가 둘째 바이트).
        # 1바이트만 오면: 해당 바이트를 하위 바이트로 보고(상위=0) bit0 해석. 패킷 센더에서 "10"은 보통 0x10 바이트.
        n = min(length, len(read_data) * 8)
        if len(read_data) == 1 and n >= 1:
            byte_val = read_data[0]
            lines.append(f"  byte = 0x{byte_val:02X} ({byte_val})  (수신 1바이트)")
            lines.append(f"  bit[0] = {byte_val & 1}")
        else:
            for i in range(n):
                word_ix = i // 16
                bit_in_word = i % 16
                byte_base = word_ix * 2
                if byte_base + 2 <= len(read_data):
                    word_be = (read_data[byte_base] << 8) | read_data[byte_base + 1]
                    val = (word_be >> bit_in_word) & 1
                    lines.append(f"  bit[{i}] = {val}")
        if not lines:
            lines.append(f"  (raw) {hex_line(read_data)}")
    elif t == "word":
        # 워드 = 2바이트 빅엔디안
        for i in range(0, min(length * 2, len(read_data)), 2):
            if i + 2 <= len(read_data):
                w = (read_data[i] << 8) | read_data[i + 1]
                if w >= 0x8000:
                    w -= 0x10000
                lines.append(f"  word[{i//2}] = {w} (0x{read_data[i]:02X}{read_data[i+1]:02X})")
        if not lines:
            lines.append(f"  (raw) {hex_line(read_data)}")
    elif t == "dword":
        # Dword = 2워드, 상위워드(D1821) + 하위워드(D1820), 각 워드 빅엔디안
        for i in range(0, min(length * 4, len(read_data)), 4):
            if i + 4 <= len(read_data):
                low = (read_data[i] << 8) | read_data[i + 1]
                high = (read_data[i + 2] << 8) | read_data[i + 3]
                val32 = (high << 16) | low
                if val32 >= 0x80000000:
                    val32_signed = val32 - 0x100000000
                else:
                    val32_signed = val32
                lines.append(f"  dword[{i//4}] = {val32_signed} (unsigned {val32}, 0x{val32:08X})")
                lines.append(f"    → low word = {low} (0x{low:04X}), high word = {high} (0x{high:04X})")
        if not lines:
            lines.append(f"  (raw) {hex_line(read_data)}")
    elif t == "string":
        try:
            s = read_data.decode("ascii", errors="replace")
            lines.append(f"  (ascii) {repr(s)}")
        except Exception:
            pass
        lines.append(f"  (hex) {hex_line(read_data)}")
    else:
        lines.append(f"  (raw) {hex_line(read_data)}")

    return "\n".join(lines) if lines else hex_line(read_data)


def main():
    parser = argparse.ArgumentParser(
        description="3E 요청 패킷 생성 후 PLC로 전송, 요청/응답 패킷 출력"
    )
    parser.add_argument(
        "--device",
        required=True,
        choices=["Y", "M", "D"],
        help="디바이스 (Y, M, D)",
    )
    parser.add_argument(
        "--address",
        type=parse_address,
        required=True,
        metavar="ADDR",
        help="시작 주소. 10진수(예: 140) 또는 0x 접두사 시 16진(예: 0x8C). D140 → 140",
    )
    parser.add_argument(
        "--type",
        dest="data_type",
        required=True,
        choices=["boolean", "word", "dword", "string"],
        help="데이터 타입. string인 경우 length는 바이트(문자) 수",
    )
    parser.add_argument(
        "--length",
        type=int,
        required=True,
        metavar="N",
        help="boolean: 비트 수. word: 워드 개수. dword: Dword 개수. string: 바이트(문자) 수",
    )
    parser.add_argument("--host", default=PLC_HOST, help=f"PLC IP (기본 {PLC_HOST})")
    parser.add_argument("--port", type=int, default=PLC_PORT, help=f"PLC 포트 (기본 {PLC_PORT})")
    parser.add_argument("--local-ip", default=None, metavar="IP", help=f"로컬 바인드 IP. 지정 시에만 바인드 (이 PC에 해당 IP 없으면 생략). 기본 없음")
    parser.add_argument("--local-port", type=int, default=None, metavar="PORT", help=f"로컬 바인드 포트. 지정 시에만 바인드. 기본 없음")
    args = parser.parse_args()

    num_words = num_words_from_type(args.data_type, args.length)
    try:
        raw = build_3e_0401_read(args.device, args.address, num_words)
    except Exception as e:
        print(f"오류: 요청 패킷 생성 실패 - {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[요청 패킷] ({len(raw)} bytes)")
    print(wireshark_hex_dump(raw))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    if args.local_ip is not None or args.local_port is not None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((args.local_ip or "", args.local_port or 0))
        except OSError as e:
            print(f"오류: 바인드 실패 {args.local_ip or '0.0.0.0'}:{args.local_port or 0} - {e}", file=sys.stderr)
            sys.exit(1)

    try:
        sock.connect((args.host, args.port))
    except OSError as e:
        print(f"오류: 연결 실패 {args.host}:{args.port} - {e}", file=sys.stderr)
        sys.exit(1)

    try:
        sock.sendall(raw)
    except OSError as e:
        print(f"오류: 전송 실패 - {e}", file=sys.stderr)
        sys.exit(1)

    # 3E 응답: 헤더 9바이트 수신 후, 최소 End code(2)+요청 워드*2 바이트는 받도록 수신 (헤더 길이 필드가 작게 오는 PLC 대비)
    data = b""
    try:
        while len(data) < RESPONSE_HEADER_LEN:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            except OSError as e:
                print(f"오류: 수신 중 - {e}", file=sys.stderr)
                sys.exit(1)
            if not chunk:
                break
            data += chunk
        if len(data) >= RESPONSE_HEADER_LEN:
            resp_data_len = data[7] | (data[8] << 8)
            min_payload = END_CODE_LEN + num_words * 2
            need_total = RESPONSE_HEADER_LEN + max(resp_data_len, min_payload)
            while len(data) < need_total:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                except OSError as e:
                    print(f"오류: 수신 중 - {e}", file=sys.stderr)
                    sys.exit(1)
                if not chunk:
                    break
                data += chunk
            if len(data) < need_total:
                sock.settimeout(1.0)
                for _ in range(3):
                    try:
                        chunk = sock.recv(4096)
                    except (socket.timeout, OSError):
                        break
                    if not chunk:
                        break
                    data += chunk
                    if len(data) >= need_total:
                        break
            data = data[:need_total]
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()

    if not data:
        print("오류: 응답 없음 (타임아웃 또는 연결 종료)", file=sys.stderr)
        sys.exit(1)

    print(f"[응답 패킷] ({len(data)} bytes)")
    print(wireshark_hex_dump(data))

    parsed = parse_3e_response(data)
    if parsed:
        header, end_code, read_data = parsed
        expected_bytes = num_words_from_type(args.data_type, args.length) * 2
        read_use = read_data[:expected_bytes] if len(read_data) > expected_bytes else read_data
        print("\n[파싱]")
        print(f"  헤더 ({len(header)} bytes): {hex_line(header)}")
        print(f"  End code (2 bytes): {hex_line(end_code)}")
        print(f"  Read data (수신 {len(read_data)} bytes): {hex_line(read_data)}")
        if len(read_data) > expected_bytes:
            print(f"  → 요청한 {args.data_type} length={args.length} 이므로 앞 {expected_bytes} bytes만 사용: {hex_line(read_use)}")
        if read_use:
            print("\n[실제 데이터값] ({}{} (0x{:X})+ 요청한 개수만큼)".format(args.device, args.address, args.address))
            print(format_read_data_value(read_use, args.data_type, args.length))
    else:
        print("\n[파싱] 응답 길이 부족으로 파싱 불가", file=sys.stderr)


if __name__ == "__main__":
    main()
