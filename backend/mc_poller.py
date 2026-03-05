"""
MC 프로토콜(3E) 폴링. 웹 대시보드에서 폴링 시작 시 plc_mcprotocol.py(pymcprotocol)로
host:port(plc_tcp_fake_response 또는 실제 PLC)에 3E 요청을 보내고, 가짜 응답 서버가
응답한 패킷을 pymcprotocol이 파싱해 값을 받아 대시보드에 표시합니다.
"""
from mc_mapping import get_mc_entries
from plc_mcprotocol import read_mc_variables

POLL_INTERVAL_SEC = 1.0


def run_poller(host, port, on_parsed, on_error, stop_event):
    """
    폴링 스레드: plc_mcprotocol.read_mc_variables로 host:port에 3E 요청.
    가짜 응답 서버(plc_tcp_fake_response)가 응답하면 그 값을 대시보드에 전달.
    """
    def do_poll():
        try:
            # mc_fake_values.json 수정분(Y14C 등)을 재시작 없이 반영
            entries = get_mc_entries()
            if not entries:
                return
            parsed = read_mc_variables(host, port, entries)
            if parsed:
                on_parsed(parsed)
        except Exception as e:
            on_error(str(e))

    try:
        do_poll()
    except Exception as e:
        on_error(str(e))

    while not stop_event.is_set():
        if stop_event.wait(POLL_INTERVAL_SEC):
            break
        try:
            do_poll()
        except Exception as e:
            on_error(str(e))
