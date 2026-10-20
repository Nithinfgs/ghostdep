"""Command Line Interface for ghostdep."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ghostdep import __version__
from ghostdep.cache import RegistryCache
from ghostdep.verifier import DependencyVerifier
from ghostdep.scanner import Scanner
from ghostdep.formatters import format_table, format_json, format_quiet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghostdep",
        description="👻 ghostdep - Catch AI package hallucinations and slopsquatting traps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ghostdep scan .                      # Scan entire project manifests and source files
  ghostdep scan requirements.txt       # Scan a specific file
  ghostdep diff                        # Scan git diff (staged + unstaged additions)
  ghostdep diff --staged               # Scan only staged git diff before commit
  ghostdep diff HEAD~1..HEAD           # Scan commit or PR branch diff
  ghostdep diff --fail-on phantom      # Exit code 1 if any hallucinated package found
  ghostdep scan --offline              # Scan without hitting external registry APIs
  ghostdep scan --json                 # Output JSON for CI / agent integration
        """
    )
    parser.add_argument("-v", "--version", action="version", version=f"ghostdep {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan a file or directory for dependencies")
    scan_parser.add_argument("path", nargs="?", default=".", help="Path to file or directory to scan (default: current directory)")
    _add_common_flags(scan_parser)

    # Command: diff
    diff_parser = subparsers.add_parser("diff", help="Scan git diff for newly introduced dependencies")
    diff_parser.add_argument("revision", nargs="?", default=None, help="Git revision or commit range (e.g. HEAD~1, main..feature)")
    diff_parser.add_argument("--staged", action="store_true", help="Scan only staged git changes (ideal for pre-commit hooks)")
    diff_parser.add_argument("--working-tree", action="store_true", help="Scan working tree unstaged changes")
    _add_common_flags(diff_parser)

    # Command: clean-cache
    clean_parser = subparsers.add_parser("clean-cache", help="Clear local registry cache")
    clean_parser.add_argument("--cache-dir", type=str, default=None, help="Custom cache directory")

    return parser


def _add_common_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    p.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (only print problematic packages)")
    p.add_argument("--verbose", action="store_true", help="Show all verified and stdlib packages in table")
    p.add_argument("--offline", action="store_true", help="Run offline without querying package registries")
    p.add_argument(
        "--fail-on",
        choices=["phantom", "suspicious", "newborn", "any"],
        default="phantom",
        help="Exit with error code 1 if matching status is found (default: phantom)"
    )
    p.add_argument("--strict", action="store_true", help="Fail on both phantom and suspicious dependencies")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()

    # If no arguments provided, default to 'diff' if in git repo, otherwise 'scan .'
    raw_args = argv if argv is not None else sys.argv[1:]
    if not raw_args:
        # Default behavior: scan current directory
        raw_args = ["scan", "."]

    # If first argument looks like a path or flag, route to scan
    if raw_args and raw_args[0] not in ("scan", "diff", "clean-cache", "-h", "--help", "-v", "--version"):
        if raw_args[0].startswith("-"):
            raw_args = ["scan", "."] + raw_args
        else:
            raw_args = ["scan"] + raw_args

    args = parser.parse_args(raw_args)

    if args.command == "clean-cache":
        cache_dir = Path(args.cache_dir) if args.cache_dir else None
        cache = RegistryCache(cache_dir=cache_dir)
        cache.clear()
        print("✓ ghostdep registry cache cleared successfully.")
        return 0

    fail_on = "suspicious" if getattr(args, "strict", False) else getattr(args, "fail_on", "phantom")
    offline = getattr(args, "offline", False)
    cache = RegistryCache()
    verifier = DependencyVerifier(cache=cache, offline=offline)
    scanner = Scanner(verifier=verifier)

    if args.command == "diff":
        report = scanner.scan_diff(
            rev_or_range=args.revision,
            staged=args.staged,
            working_tree=args.working_tree
        )
    else:  # scan
        target_path = Path(args.path)
        if not target_path.exists():
            print(f"Error: Target path '{args.path}' does not exist.", file=sys.stderr)
            return 2
        report = scanner.scan_path(target_path)

    # Output formatting
    if getattr(args, "json", False):
        print(format_json(report))
    elif getattr(args, "quiet", False):
        out = format_quiet(report)
        if out:
            print(out)
    else:
        print(format_table(report, verbose=getattr(args, "verbose", False)))

    # Exit code
    if report.has_issues(fail_on=fail_on):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
