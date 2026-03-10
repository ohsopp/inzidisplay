#!/usr/bin/env python3
"""
Update mc_fake_values.json for D330 on a fixed interval.

Behavior:
- Uses absolute range starting from 0.
- Increments by +1 every interval (default: 50ms).
- When value exceeds max (default: 100), resets to 0.
"""

from __future__ import annotations

import argparse
import json
import signal
import tempfile
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MC_FAKE_VALUES_PATH = SCRIPT_DIR / "mc_fake_values.json"
TARGET_KEY = "D330"

_running = True


def _stop_handler(signum, frame):  # noqa: ARG001
    global _running
    _running = False


def load_config() -> dict:
    with open(MC_FAKE_VALUES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write_config(data: dict) -> None:
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(MC_FAKE_VALUES_PATH.parent),
    ) as tf:
        json.dump(data, tf, ensure_ascii=False, indent=2)
        tf.write("\n")
        temp_path = Path(tf.name)
    temp_path.replace(MC_FAKE_VALUES_PATH)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate D330 value changes")
    parser.add_argument("--interval-ms", type=float, default=50.0, help="Update interval in milliseconds")
    parser.add_argument("--max", dest="max_value", type=int, default=100, help="Reset threshold max value")
    args = parser.parse_args()

    if not MC_FAKE_VALUES_PATH.exists():
        print(f"Error: file not found: {MC_FAKE_VALUES_PATH}")
        return 1

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    data = load_config()
    entry = data.get(TARGET_KEY)
    if not isinstance(entry, dict):
        print(f"Error: key not found: {TARGET_KEY}")
        return 1

    interval_sec = max(0.001, args.interval_ms / 1000.0)
    current = 0
    entry["value"] = current
    atomic_write_config(data)
    print(
        f"Simulating {TARGET_KEY}: range=0..{args.max_value}, "
        f"interval={args.interval_ms}ms (Ctrl+C to stop)"
    )

    while _running:
        next_value = current + 1
        if next_value > args.max_value:
            next_value = 0
        entry["value"] = next_value
        atomic_write_config(data)
        current = next_value
        time.sleep(interval_sec)

    print("Stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
