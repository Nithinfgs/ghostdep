"""Terminal UI and JSON output formatters."""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, Any

from ghostdep.models import ScanReport, Status

# Terminal color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

STATUS_STYLES: Dict[Status, Dict[str, str]] = {
    Status.PHANTOM: {"color": RED, "badge": "👻 PHANTOM", "icon": "✖"},
    Status.SUSPICIOUS: {"color": YELLOW, "badge": "⚠️ SUSPICIOUS", "icon": "!"},
    Status.NEWBORN: {"color": MAGENTA, "badge": "🐣 NEWBORN", "icon": "▲"},
    Status.VERIFIED: {"color": GREEN, "badge": "✓ VERIFIED", "icon": "✓"},
    Status.STDLIB: {"color": CYAN, "badge": "📦 STDLIB", "icon": "•"},
    Status.LOCAL: {"color": BLUE, "badge": "🏠 LOCAL", "icon": "•"},
    Status.SKIPPED: {"color": DIM, "badge": "○ SKIPPED", "icon": "-"},
    Status.ERROR: {"color": RED, "badge": "✖ ERROR", "icon": "✖"},
}


def should_colorize() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


def format_table(report: ScanReport, verbose: bool = False) -> str:
    use_color = should_colorize()
    lines = []

    def c(code: str, text: str) -> str:
        return f"{code}{text}{RESET}" if use_color else text

    # Header banner
    lines.append("")
    lines.append(c(BOLD + CYAN, "👻 ghostdep") + c(DIM, f" — AI Hallucination & Slopsquatting Detector"))
    lines.append(c(DIM, f"Target: {report.target} | Scanned in {report.scan_duration_ms:.1f}ms"))
    lines.append("")

    if not report.dependencies:
        lines.append(c(GREEN, "✓ No external dependencies or imports detected."))
        lines.append("")
        return "\n".join(lines)

    # Columns: Status, Package, Eco, Source, Details
    # Filter: if not verbose, display all except verified/stdlib if there are phantoms
    deps_to_show = report.dependencies
    if not verbose and (report.phantom_count + report.suspicious_count > 0):
        # Highlight problematic ones first
        deps_to_show = sorted(
            report.dependencies,
            key=lambda d: (
                0 if d.status == Status.PHANTOM else
                1 if d.status == Status.SUSPICIOUS else
                2 if d.status == Status.NEWBORN else
                3 if d.status == Status.ERROR else 4
            )
        )

    # Calculate column widths
    max_pkg_len = max(len(d.name) for d in deps_to_show)
    max_pkg_len = max(max_pkg_len, 7)
    max_eco_len = max(len(d.ecosystem) for d in deps_to_show)
    max_eco_len = max(max_eco_len, 9)

    header = f"{'STATUS':<14} {'PACKAGE':<{max_pkg_len}} {'ECOSYSTEM':<{max_eco_len}} {'LOCATION':<24} {'DETAILS'}"
    separator = "─" * min(len(header) + 30, 110)

    lines.append(c(BOLD, header))
    lines.append(c(DIM, separator))

    for d in deps_to_show:
        style = STATUS_STYLES.get(d.status, {"color": WHITE, "badge": d.status.value, "icon": "?"})
        badge_colored = c(style["color"] + BOLD, f"{style['badge']:<14}")

        location = f"{d.source_file}:{d.line_number}" if d.line_number else d.source_file
        if len(location) > 24:
            location = "…" + location[-23:]

        details_str = d.details
        if d.similar_to:
            details_str = c(YELLOW + BOLD, f"TYPO OF '{d.similar_to}'! ") + details_str

        pkg_colored = c(BOLD, f"{d.name:<{max_pkg_len}}")
        eco_str = f"{d.ecosystem:<{max_eco_len}}"
        loc_str = f"{location:<24}"

        lines.append(f"{badge_colored} {pkg_colored} {c(DIM, eco_str)} {loc_str} {details_str}")

    lines.append(c(DIM, separator))

    # Summary bar
    summary_parts = []
    if report.phantom_count > 0:
        summary_parts.append(c(RED + BOLD, f"👻 {report.phantom_count} phantom (NOT on registry)"))
    if report.suspicious_count > 0:
        summary_parts.append(c(YELLOW + BOLD, f"⚠️ {report.suspicious_count} suspicious"))
    if report.newborn_count > 0:
        summary_parts.append(c(MAGENTA, f"🐣 {report.newborn_count} newborn"))
    if report.verified_count > 0:
        summary_parts.append(c(GREEN, f"✓ {report.verified_count} verified"))
    if report.stdlib_count > 0:
        summary_parts.append(c(CYAN, f"📦 {report.stdlib_count} stdlib"))
    if report.local_count > 0:
        summary_parts.append(c(BLUE, f"🏠 {report.local_count} local"))

    lines.append(f"Summary: {', '.join(summary_parts)}")

    # Verdict
    if report.phantom_count > 0:
        lines.append(c(RED + BOLD, "\n✖ FAILED: Hallucinated dependencies detected! Registering or installing these could lead to RCE or slopsquatting attacks.\n"))
    elif report.suspicious_count > 0:
        lines.append(c(YELLOW + BOLD, "\n⚠️ WARNING: Suspicious package dependencies detected. Review age and maintainers before running install.\n"))
    else:
        lines.append(c(GREEN + BOLD, "\n✓ PASSED: All dependencies verified or recognized as standard/local libraries.\n"))

    return "\n".join(lines)


def format_json(report: ScanReport) -> str:
    """Format report as clean, pretty-printed JSON."""
    return json.dumps(report.to_dict(), indent=2)


def format_quiet(report: ScanReport) -> str:
    """Minimal output printing only phantom/suspicious packages, one per line."""
    lines = []
    for d in report.dependencies:
        if d.status in (Status.PHANTOM, Status.SUSPICIOUS):
            lines.append(f"{d.status.value.upper()}: {d.ecosystem} {d.name} ({d.source_file}) - {d.details}")
    return "\n".join(lines)
