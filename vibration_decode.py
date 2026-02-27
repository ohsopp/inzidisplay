# backend/services/vibration_decode.py - VVB001 진동센서·온도 디코딩
import traceback


def parse_hex_to_temperature(hex_data):
    """16진수 데이터를 온도로 변환 (예: '0110' -> 27.2°C)"""
    try:
        hex_int = int(hex_data, 16)
        temperature = hex_int / 10.0
        return temperature
    except Exception as e:
        print(f"❌ Error parsing hex to temperature: {e}")
        return None

PDIN_PATHS = [
    '/iolinkmaster/port[4]/iolinkdevice/pdin',
    '/iolinkmaster/port[3]/iolinkdevice/pdin',
    '/iolinkmaster/port[2]/iolinkdevice/pdin',
    '/iolinkmaster/port[1]/iolinkdevice/pdin'
]

DEVICE_STATUS_MAP = {
    0: "Device is OK",
    1: "Maintenance required",
    2: "Out of specification",
    3: "Function check",
    4: "Offline",
    5: "Device not available",
    6: "No data available",
    7: "Cyclic data not available"
}

SPECIAL_VALUES = {
    32760: "OL",
    -32760: "UL",
    32764: "NoData",
    -32768: "Invalid"
}

def hex_to_bytes(hex_string):
    """16진수 문자열을 바이트 배열로 변환"""
    try:
        return bytes.fromhex(hex_string)
    except Exception as e:
        print(f"❌ Error converting hex to bytes: {e}")
        return None

def check_special(value):
    """특수 값 체크"""
    if value in SPECIAL_VALUES:
        return SPECIAL_VALUES[value]
    return None

def decode_vvb001(hex_data):
    """VVB001 진동센서 데이터 디코딩 (빅 엔디안, 20바이트)"""
    try:
        if len(hex_data) != 40:
            print(f"⚠️ Invalid hex data length: {len(hex_data)}, expected 40")
            return None

        bytes_data = hex_to_bytes(hex_data)
        if bytes_data is None or len(bytes_data) != 20:
            return None

        v_rms_raw = int.from_bytes(bytes_data[0:2], byteorder='big', signed=True)
        v_rms = v_rms_raw * 0.0001

        a_peak_raw = int.from_bytes(bytes_data[4:6], byteorder='big', signed=True)
        a_peak = a_peak_raw * 0.1

        a_rms_raw = int.from_bytes(bytes_data[8:10], byteorder='big', signed=True)
        a_rms = a_rms_raw * 0.1

        status_byte = bytes_data[10]
        device_status_code = (status_byte >> 4) & 0x07
        device_status = DEVICE_STATUS_MAP.get(device_status_code, f"Unknown({device_status_code})")
        out1 = bool(status_byte & 0x01)
        out2 = bool(status_byte & 0x02)

        temp_raw = int.from_bytes(bytes_data[12:14], byteorder='big', signed=True)
        temperature = temp_raw * 0.1

        crest_raw = int.from_bytes(bytes_data[16:18], byteorder='big', signed=True)
        crest = crest_raw * 0.1

        v_rms_special = check_special(v_rms_raw)
        a_peak_special = check_special(a_peak_raw)
        a_rms_special = check_special(a_rms_raw)
        temp_special = check_special(temp_raw)
        crest_special = check_special(crest_raw)

        return {
            'v_rms': v_rms if not v_rms_special else None,
            'a_peak': a_peak if not a_peak_special else None,
            'a_rms': a_rms if not a_rms_special else None,
            'temperature': temperature if not temp_special else None,
            'crest': crest if not crest_special else None,
            'device_status': device_status,
            'out1': out1,
            'out2': out2,
            'raw_values': {
                'v_rms': v_rms_raw, 'a_peak': a_peak_raw, 'a_rms': a_rms_raw,
                'temperature': temp_raw, 'crest': crest_raw, 'status_byte': status_byte
            },
            'special_values': {
                'v_rms': v_rms_special, 'a_peak': a_peak_special, 'a_rms': a_rms_special,
                'temperature': temp_special, 'crest': crest_special
            }
        }
    except Exception as e:
        print(f"❌ Error decoding VVB001 data: {e}")
        traceback.print_exc()
        return None
