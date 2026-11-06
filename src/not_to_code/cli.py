"""Command line interface."""

import argparse
from pathlib import Path

from .languages import LANGUAGES
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
    scan.add_argument("--r-tools", type=Path)
    scan.add_argument("--language", choices=sorted(LANGUAGES))
    scan.add_argument("--recover-release", action="store_true")
    scan.add_argument(
        "--deposit-list",
        type=Path,
        help="JSON list of deposit-version IDs in the eligible frame",
    )
    render = sub.add_parser("report")
    render.add_argument("--input", type=Path, required=True)
    render.add_argument("--readme", type=Path)
    args = parser.parse_args()
    if args.command == "assess":
        if args.limit_deposits is not None and args.limit_deposits < 1:
            parser.error("--limit-deposits must be positive")
        if args.workers < 1:
            parser.error("--workers must be positive")
        assess(
            args.softverse_root,
            args.output,
            args.limit_deposits,
            args.workers,
            args.r_tools,
            args.language,
            args.recover_release,
            args.deposit_list,
        )
        report(args.output)
    else:
        report(args.input, args.readme)
