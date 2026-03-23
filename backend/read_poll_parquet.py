#!/usr/bin/env python3
"""
poll_logs 아래 Parquet 파일 읽기·미리보기·CSV 내보내기.

  # ./venv/bin/python read_poll_parquet.py
  #  poll_logs/ 디렉토리에서 최근 Parquet 파일 목록을 보여줍니다.

  # ./venv/bin/python read_poll_parquet.py poll_logs/실시간_공정값/20260323.parquet
  #  지정한 Parquet 파일(예: 20260323.parquet)의 내용을 미리봅니다.

  # ./venv/bin/python read_poll_parquet.py poll_logs/실시간_공정값/20260323.parquet -n 5 --expand
  #  지정한 Parquet 파일에서 최대 5개 행을 펼쳐서(전체 데이터 내용 표시) 출력합니다.

  # ./venv/bin/python read_poll_parquet.py some.parquet --csv out.csv
  #  지정한 Parquet 파일을 읽어서 out.csv 파일로 내보냅니다.

"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq

# backend/poll_logs 기본 위치
_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_POLL_LOGS = _SCRIPT_DIR / "poll_logs"


def _list_parquet_files(base: Path, limit: int) -> list[Path]:
    if not base.is_dir():
        return []
    files = sorted(base.rglob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def _read_table(path: Path):
    return pq.read_table(path)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="poll_logs Parquet 읽기 (t_kst, interval_key, data_json)"
    )
    ap.add_argument(
        "path",
        nargs="?",
        help="*.parquet 파일 경로 (생략 시 poll_logs에서 최근 파일 목록)",
    )
    ap.add_argument(
        "-n",
        "--head",
        type=int,
        default=20,
        metavar="N",
        help="화면에 표시할 행 수 (기본 20)",
    )
    ap.add_argument(
        "--list",
        type=int,
        default=15,
        metavar="K",
        help="path 생략 시 나열할 최근 Parquet 개수 (기본 15)",
    )
    ap.add_argument(
        "--expand",
        action="store_true",
        help="data_json을 파싱해 변수별로 한 줄씩 출력",
    )
    ap.add_argument(
        "--csv",
        metavar="FILE",
        help="전체 행을 CSV로 저장 (data_json은 문자열 컬럼)",
    )
    ap.add_argument(
        "--base",
        type=Path,
        default=_DEFAULT_POLL_LOGS,
        help=f"목록 검색 기준 폴더 (기본: {_DEFAULT_POLL_LOGS})",
    )
    args = ap.parse_args()

    poll_base = Path(os.environ.get("POLL_LOGS_DIR", "").strip() or args.base)

    if not args.path:
        found = _list_parquet_files(poll_base, args.list)
        if not found:
            print(f"Parquet 파일이 없습니다: {poll_base}", file=sys.stderr)
            return 1
        print(f"최근 Parquet ({poll_base}):\n")
        for p in found:
            rel = p.relative_to(poll_base) if p.is_relative_to(poll_base) else p
            print(f"  {rel}")
        print("\n읽기: python read_poll_parquet.py <위 경로>")
        return 0

    path = Path(args.path)
    if not path.is_file():
        print(f"파일 없음: {path}", file=sys.stderr)
        return 1

    table = _read_table(path)
    n = table.num_rows

    if args.csv:
        out = Path(args.csv)
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_kst", "interval_key", "data_json"])
            col_t = table.column("t_kst")
            col_i = table.column("interval_key")
            col_d = table.column("data_json")
            for i in range(n):
                w.writerow([col_t[i].as_py(), col_i[i].as_py(), col_d[i].as_py()])
        print(f"CSV 저장: {out} ({n}행)")
        return 0

    show = min(args.head, n)
    if args.expand:
        col_t = table.column("t_kst")
        col_i = table.column("interval_key")
        col_d = table.column("data_json")
        for i in range(show):
            t_kst = col_t[i].as_py()
            iv = col_i[i].as_py()
            raw = col_d[i].as_py()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"_raw": raw}
            print(f"--- [{i}] {t_kst}  ({iv})")
            for k, v in sorted(data.items()):
                print(f"  {k}: {v}")
            print()
        if n > show:
            print(f"... 외 {n - show}행 생략 (-n 으로 조정)")
        return 0

    # 기본: 행 단위 (to_string()은 넓은 테이블에서 데이터가 잘 안 보일 수 있음)
    col_t = table.column("t_kst")
    col_i = table.column("interval_key")
    col_d = table.column("data_json")
    for i in range(show):
        dj = col_d[i].as_py()
        if len(dj) > 120:
            dj = dj[:117] + "..."
        print(f"{col_t[i].as_py()}\t{col_i[i].as_py()}\t{dj}")
    if n > show:
        print(f"\n... 총 {n}행 중 {show}행만 표시 (-n 으로 조정)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
