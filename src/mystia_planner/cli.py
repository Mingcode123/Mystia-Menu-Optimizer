"""Non-interactive command line entry point."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .io import load_dataset, write_csv_report, write_json_report
from .models import Settings
from .planner import plan_dataset


def _tokens(values: list[str] | None) -> frozenset[str]:
    return frozenset(token for value in (values or []) for token in re.split(r"[\s,，;；、|/]+", value.strip()) if token)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan one recipe per guest and select a cookware combination.")
    parser.add_argument("--input", type=Path, required=True, help="mystia-planner-data/v1 JSON file")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON report")
    parser.add_argument("--csv", type=Path, help="Also export a UTF-8 CSV table")
    parser.add_argument("--min-score", type=int, default=3, help="Minimum preferred-tag score (default: 3)")
    parser.add_argument("--orders-per-day", type=int, default=5, help="Expected orders for each guest (default: 5)")
    parser.add_argument("--trend-like", action="append", help="Trend-like anchor tags; repeat or separate by comma/space")
    parser.add_argument("--trend-hate", action="append", help="Trend-hate anchor tags; repeat or separate by comma/space")
    parser.add_argument("--guest", action="append", help="Exact guest name; repeat to select several (default: all)")
    parser.add_argument("--cookware-count", type=int, help="Number of cookware types to select (default: all available)")
    parser.add_argument("--exclude-cookware", action="append", help="Cookware to exclude; repeat or separate by comma/space")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        destinations = [args.output] + ([args.csv] if args.csv else [])
        resolved = [path.resolve() for path in destinations]
        if args.input.resolve() in resolved or len(set(resolved)) != len(resolved):
            raise ValueError("Input, JSON output, and CSV output must have different paths")
        settings = Settings(
            min_score=args.min_score,
            orders_per_day=args.orders_per_day,
            trend_like=_tokens(args.trend_like),
            trend_hate=_tokens(args.trend_hate),
            cookware_count=args.cookware_count,
            exclude_cookware=_tokens(args.exclude_cookware),
        )
        dataset = load_dataset(args.input)
        report = plan_dataset(dataset, settings, tuple(args.guest) if args.guest else None)
        write_json_report(report, args.output)
        if args.csv:
            write_csv_report(report, args.csv)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    summary = report["summary"]
    print(f"Planned {summary['planned_count']}/{summary['guest_count']} guests; cookware: {', '.join(report['selected_cookware']) or '(none)'}")
    print(f"JSON: {args.output}")
    if args.csv:
        print(f"CSV: {args.csv}")
    return 0
