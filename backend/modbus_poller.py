"""
Modbus TCP 폴링: 매핑/옵션/블록 그룹핑/범용 디코더(modbus_mapping) 사용.
Boolean(Coil) 3초, Holding 등 1초. io_variables.json + modbus_options.json.
"""
import threading
import time

from modbus_mapping import (
    load_io_variables,
    load_options,
    build_full_map,
    build_read_blocks,
    decode_value,
)

ALARM_POLL_INTERVAL = 3
DATA_POLL_INTERVAL = 1


def run_poller(host, port, slave_id, on_parsed, on_error, stop_event):
    """
    폴링 스레드: modbus_mapping 매핑/블록/디코더 사용.
    Coil 3초, Holding/InputReg 1초. on_parsed({ name: value }).
    """
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        on_error("pymodbus가 설치되지 않았습니다. pip install pymodbus")
        return

    options = load_options()
    entries = load_io_variables()
    full_map = build_full_map(entries, options)
    blocks = build_read_blocks(full_map)

    port = port or 502
    parsed = {}
    last_coil_time = [0]
    last_reg_time = [0]

    def connect_client():
        c = ModbusTcpClient(host=host, port=port, timeout=3)
        if not c.connect():
            return None
        return c

    def do_coils():
        for start, count, tags in blocks.get("coil", []):
            client = connect_client()
            if not client:
                on_error("Modbus TCP 연결 실패")
                return
            try:
                rr = client.read_coils(start, count=count, device_id=slave_id)
                if rr.isError():
                    continue
                bits = rr.bits[:count]
                for name, info, addr, tag_count in tags:
                    off = addr - start
                    sl = bits[off : off + tag_count] if off + tag_count <= len(bits) else []
                    parsed[name] = decode_value(info, raw_bits=sl)
            except Exception as e:
                on_error(str(e))
            finally:
                try:
                    client.close()
                except Exception:
                    pass

    def do_discrete():
        for start, count, tags in blocks.get("discrete", []):
            client = connect_client()
            if not client:
                continue
            try:
                rr = client.read_discrete_inputs(start, count=count, device_id=slave_id)
                if rr.isError():
                    continue
                bits = rr.bits[:count]
                for name, info, addr, tag_count in tags:
                    off = addr - start
                    sl = bits[off : off + tag_count] if off + tag_count <= len(bits) else []
                    parsed[name] = decode_value(info, raw_bits=sl)
            finally:
                try:
                    client.close()
                except Exception:
                    pass

    def do_holding():
        for start, count, tags in blocks.get("holding", []):
            client = connect_client()
            if not client:
                on_error("Modbus TCP 연결 실패")
                return
            try:
                rr = client.read_holding_registers(start, count=count, device_id=slave_id)
                if rr.isError():
                    continue
                regs = rr.registers[:count]
                for name, info, addr, tag_count in tags:
                    off = addr - start
                    chunk = regs[off : off + tag_count] if off + tag_count <= len(regs) else []
                    parsed[name] = decode_value(info, raw_regs=chunk)
            except Exception as e:
                on_error(str(e))
            finally:
                try:
                    client.close()
                except Exception:
                    pass

    def do_input_reg():
        for start, count, tags in blocks.get("input_reg", []):
            client = connect_client()
            if not client:
                continue
            try:
                rr = client.read_input_registers(start, count=count, device_id=slave_id)
                if rr.isError():
                    continue
                regs = rr.registers[:count]
                for name, info, addr, tag_count in tags:
                    off = addr - start
                    chunk = regs[off : off + tag_count] if off + tag_count <= len(regs) else []
                    parsed[name] = decode_value(info, raw_regs=chunk)
            finally:
                try:
                    client.close()
                except Exception:
                    pass

    try:
        do_coils()
        do_discrete()
        do_holding()
        do_input_reg()
        on_parsed(dict(parsed))
    except Exception as e:
        on_error(str(e))

    while not stop_event.is_set():
        now = time.monotonic()
        if now - last_coil_time[0] >= ALARM_POLL_INTERVAL:
            last_coil_time[0] = now
            do_coils()
            do_discrete()
            on_parsed(dict(parsed))
        if now - last_reg_time[0] >= DATA_POLL_INTERVAL:
            last_reg_time[0] = now
            do_holding()
            do_input_reg()
            on_parsed(dict(parsed))
        time.sleep(0.2)
