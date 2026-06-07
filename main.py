from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from src.config import load_config
from src.pipeline import run_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tạo báo cáo thị trường Việt Nam hằng ngày theo phong cách IBD.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="Tạo báo cáo cho phiên giao dịch đã hoàn tất gần nhất.")
    group.add_argument("--date", type=str, help="Ngày yêu cầu theo định dạng YYYY-MM-DD.")
    return parser.parse_args()


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    args = parse_args()
    requested_date = date.today() if args.latest else date.fromisoformat(args.date)
    config = load_config()
    output = run_report(requested_date=requested_date, cfg=config, latest=args.latest)
    print(f"Đã tạo báo cáo: {output}")


if __name__ == "__main__":
    main()
