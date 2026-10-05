"""Command line interface."""

import argparse
from pathlib import Path

from .pipeline import assess
from .report import report


def main():
    parser = argparse.ArgumentParser(
        description="Descriptive engineering properties of research code"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("assess")
    scan.add_argument("--softverse-root", type=Path, required=True)
    scan.add_argument("--output", type=Path, required=True)
    scan.add_argument("--limit-deposits", type=int)
    scan.add_argument("--workers", type=int, default=1)
    render = sub.add_parser("report")
    render.add_argument("--input", type=Path, required=True)
    render.add_argument("--readme", type=Path)
    args = parser.parse_args()
    if args.command == "assess":
        if args.limit_deposits is not None and args.limit_deposits < 1:
            parser.error("--limit-deposits must be positive")
        if args.workers < 1:
            parser.error("--workers must be positive")
        assess(args.softverse_root, args.output, args.limit_deposits, args.workers)
        report(args.output)
    else:
        report(args.input, args.readme)
