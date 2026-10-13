"""Repeatable whole-file raw inspection without changing the CSV or using Spark."""

import argparse
import json
from pathlib import Path

from database.raw_vietjobs import DEFAULT_RAW, RawIndex


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Report exists: choose a new name to preserve the previous inspection")
    report = RawIndex(args.input).profile
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("rows", "column_count", "exact_duplicate_rows", "source_sha256")
            }
        )
    )


if __name__ == "__main__":
    main()
