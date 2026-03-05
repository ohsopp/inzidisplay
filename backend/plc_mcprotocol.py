#!/usr/bin/env python3
"""
plc_tcp_send.py와 동일한 CLI로, pymcprotocol(MC 프로토콜) 라이브러리를 사용해
3E 요청 전송 및 응답 파싱을 수행합니다. 요청/응답 패킷을 콘솔에 덤프합니다.

의존성: pip install pymcprotocol

- 실행 예시 -
python3 backend/plc_mcprotocol.py --device D --address 140 --type word --length 1
python3 backend/plc_mcprotocol.py --device Y --address 107 --type boolean --length 1
python3 backend/plc_mcprotocol.py --device D --address 1810 --type dword --length 1
python3 backend/plc_mcprotocol.py --device D --address 1560 --type string --length 16
"""
import argparse
import sys

try:
    import pymcprotocol
except ImportError:
    print("오류: pymcprotocol이 필요합니다. pip install pymcprotocol", file=sys.stderr)
    sys.exit(1)

PLC_HOST = "192.168.0.5"
PLC_PORT = 5002
TIMEOUT = 5.0

# 응답 파싱용 상수 (plc_tcp_send.py와 동일)
RESPONSE_HEADER_LEN = 9
END_CODE_LEN = 2


def parse_address(s: str) -> int:
    """주소 문자열 해석. 0x 접두사 있으면 16진수, 없으면 10진수."""
    s = (s or "").strip()
    if not s:
        raise ValueError("주소가 비어 있음")
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)


def num_words_from_type(data_type: str, length: int) -> int:
    """데이터 타입과 length로 요청할 워드 수 계산."""
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


def device_to_headdevice(device: str, address: int) -> str:
    """(device, address) → pymcprotocol 헤드 디바이스 문자열. 예: D140, Y107, M0."""
    return f"{device.upper()}{address}"


def wireshark_hex_dump(data: bytes, bytes_per_line: int = 16) -> str:
    """와이어샤크 스타일 HEX 덤프."""
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


def hex_line(data: bytes) -> str:
    return " ".join(data.hex().upper()[i : i + 2] for i in range(0, len(data.hex()), 2))


def parse_3e_response(data: bytes) -> tuple[bytes, bytes, bytes] | None:
    """3E 응답 패킷을 (헤더, End code, Read data)로 파싱."""
    if len(data) < RESPONSE_HEADER_LEN + END_CODE_LEN:
        return None
    header = data[:RESPONSE_HEADER_LEN]
    end_code = data[RESPONSE_HEADER_LEN : RESPONSE_HEADER_LEN + END_CODE_LEN]
    read_data = data[RESPONSE_HEADER_LEN + END_CODE_LEN :]
    return header, end_code, read_data


def format_read_data_value(read_data: bytes, data_type: str, length: int) -> str:
    """Read data 바이트를 요청한 타입에 맞게 해석해 설명 문자열 반환 (plc_tcp_send와 동일 형식)."""
    t = (data_type or "").strip().lower()
    lines = []

    if t == "boolean":
        n = min(length, len(read_data) * 8)
        if len(read_data) == 1 and n >= 1:
            byte_val = read_data[0]
            lines.append(f"  byte = 0x{byte_val:02X} ({byte_val})  (수신 1바이트)")
            lines.append(f"  bit[0] = {byte_val & 1}")
        else:
            for i in range(n):
                word_ix = i // 16
                byte_base = word_ix * 2
                if byte_base + 2 <= len(read_data):
                    word_be = (read_data[byte_base] << 8) | read_data[byte_base + 1]
                    val = (word_be >> (i % 16)) & 1
                    lines.append(f"  bit[{i}] = {val}")
        if not lines:
            lines.append(f"  (raw) {hex_line(read_data)}")
    elif t == "word":
        for i in range(0, min(length * 2, len(read_data)), 2):
            if i + 2 <= len(read_data):
                w = (read_data[i] << 8) | read_data[i + 1]
                if w >= 0x8000:
                    w -= 0x10000
                lines.append(f"  word[{i//2}] = {w} (0x{read_data[i]:02X}{read_data[i+1]:02X})")
        if not lines:
            lines.append(f"  (raw) {hex_line(read_data)}")
    elif t == "dword":
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


class PacketCaptureSocket:
    """send/recv 시 패킷을 저장하는 socket 래퍼. _real_socket_class로 진짜 소켓 생성(재귀 방지)."""

    _real_socket_class = None  # main()에서 패치 전에 설정

    def __init__(self, family, type_, proto=-1):
        cls = PacketCaptureSocket._real_socket_class or __import__("socket").socket
        self._sock = cls(family, type_, proto)
        self._last_sent = b""
        self._last_received = b""

    def __getattr__(self, name):
        return getattr(self._sock, name)

    def sendall(self, data, *args, **kwargs):
        self._last_sent = data
        return self._sock.sendall(data, *args, **kwargs)

    def send(self, data, *args, **kwargs):
        self._last_sent = data if isinstance(data, bytes) else self._last_sent + (data or b"")
        return self._sock.send(data, *args, **kwargs)

    def recv(self, bufsize, *args, **kwargs):
        data = self._sock.recv(bufsize, *args, **kwargs)
        if data:
            self._last_received += data
        return data


def main():
    parser = argparse.ArgumentParser(
        description="pymcprotocol으로 3E 읽기 수행, 요청/응답 패킷 덤프"
    )
    parser.add_argument("--device", required=True, choices=["Y", "M", "D"], help="디바이스 (Y, M, D)")
    parser.add_argument(
        "--address",
        type=parse_address,
        required=True,
        metavar="ADDR",
        help="시작 주소. 10진수(예: 140) 또는 0x 접두사 시 16진(예: 0x8C)",
    )
    parser.add_argument(
        "--type",
        dest="data_type",
        required=True,
        choices=["boolean", "word", "dword", "string"],
        help="데이터 타입",
    )
    parser.add_argument(
        "--length",
        type=int,
        required=True,
        metavar="N",
        help="boolean: 비트 수. word: 워드 개수. dword: Dword 개수. string: 바이트 수",
    )
    parser.add_argument("--host", default=PLC_HOST, help=f"PLC IP (기본 {PLC_HOST})")
    parser.add_argument("--port", type=int, default=PLC_PORT, help=f"PLC 포트 (기본 {PLC_PORT})")
    args = parser.parse_args()

    num_words = num_words_from_type(args.data_type, args.length)
    headdevice = device_to_headdevice(args.device, args.address)

    # 패킷 캡처: 래퍼가 내부에서 진짜 socket만 쓰도록 해서 재귀 방지
    socket_module = __import__("socket")
    real_socket = socket_module.socket
    PacketCaptureSocket._real_socket_class = real_socket
    capture_sock = None

    def capturing_socket(family, type_, proto=-1):
        nonlocal capture_sock
        capture_sock = PacketCaptureSocket(family, type_, proto)
        return capture_sock

    socket_module.socket = capturing_socket

    pymc3e = pymcprotocol.Type3E()
    try:
        pymc3e.connect(args.host, args.port)
    except Exception as e:
        print(f"오류: 연결 실패 {args.host}:{args.port} - {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        socket_module.socket = real_socket

    request_packet = b""
    response_packet = b""
    values = None

    try:
        t = (args.data_type or "").strip().lower()
        if t == "boolean":
            if hasattr(pymc3e, "batchread_bitunits"):
                values = pymc3e.batchread_bitunits(headdevice=headdevice, readsize=args.length)
            else:
                values = pymc3e.batchread_wordunits(headdevice=headdevice, readsize=num_words)
        elif t == "word":
            values = pymc3e.batchread_wordunits(headdevice=headdevice, readsize=args.length)
        elif t == "dword":
            values = pymc3e.batchread_wordunits(headdevice=headdevice, readsize=args.length * 2)
        elif t == "string":
            values = pymc3e.batchread_wordunits(headdevice=headdevice, readsize=num_words)
        else:
            values = pymc3e.batchread_wordunits(headdevice=headdevice, readsize=num_words)
    except Exception as e:
        print(f"오류: 읽기 실패 - {e}", file=sys.stderr)
        if capture_sock:
            response_packet = capture_sock._last_received
        try:
            pymc3e.close()
        except Exception:
            pass
        sys.exit(1)
    finally:
        if capture_sock:
            request_packet = capture_sock._last_sent
            response_packet = capture_sock._last_received
        try:
            pymc3e.close()
        except Exception:
            pass

    print(f"[요청 패킷] ({len(request_packet)} bytes)")
    print(wireshark_hex_dump(request_packet) if request_packet else "(캡처 없음)")

    print(f"[응답 패킷] ({len(response_packet)} bytes)")
    print(wireshark_hex_dump(response_packet) if response_packet else "(캡처 없음)")

    parsed = parse_3e_response(response_packet) if response_packet else None
    if parsed:
        header, end_code, read_data = parsed
        expected_bytes = num_words * 2
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
        print("\n[파싱] 응답 길이 부족으로 raw 파싱 불가")
        if values is not None:
            print("[라이브러리 반환값]", f"  {args.data_type} = {values}")


if __name__ == "__main__":
    main()
