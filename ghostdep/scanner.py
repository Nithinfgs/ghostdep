"""Workspace and Git diff scanner."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Set

from ghostdep.models import Dependency, ScanReport, Status, Ecosystem
from ghostdep.verifier import DependencyVerifier
from ghostdep.cache import RegistryCache
from ghostdep.extractors import (
    extract_from_requirements,
    extract_from_package_json,
    extract_from_pyproject_toml,
    extract_from_cargo_toml,
    extract_from_go_mod,
    extract_from_python_code,
    extract_from_js_code,
    extract_from_rust_code,
    extract_from_go_code,
)

IGNORED_DIRS: Set[str] = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".tox", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "target", "dist", "build", ".next", ".nuxt", "vendor"
}


class Scanner:
    def __init__(self, verifier: Optional[DependencyVerifier] = None):
        self.verifier = verifier or DependencyVerifier()

    def scan_path(self, target_path: str | Path, root_dir: Optional[Path] = None) -> ScanReport:
        """Scan a file or directory for dependencies."""
        start_time = time.time()
        path = Path(target_path).resolve()
        effective_root = root_dir or (path if path.is_dir() else path.parent)

        deps: List[Dependency] = []
        if path.is_file():
            deps.extend(self._scan_single_file(path, str(path.relative_to(effective_root) if effective_root in path.parents else path)))
        elif path.is_dir():
            for root, dirs, files in os.walk(path):
                # Filter out ignored directories in-place
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
                for file_name in files:
                    file_path = Path(root) / file_name
                    try:
                        rel_path = str(file_path.relative_to(effective_root))
                    except ValueError:
                        rel_path = str(file_path)
                    deps.extend(self._scan_single_file(file_path, rel_path))

        # De-duplicate dependencies
        unique_deps = self._deduplicate(deps)

        # Run verification
        verified_deps = self.verifier.verify_all(unique_deps, root_dir=effective_root)

        report = ScanReport(
            target=str(target_path),
            dependencies=verified_deps,
            scan_duration_ms=(time.time() - start_time) * 1000,
        )
        report.compute_metrics()
        return report

    def scan_diff(
        self,
        rev_or_range: Optional[str] = None,
        staged: bool = False,
        working_tree: bool = False,
        repo_dir: Optional[Path] = None
    ) -> ScanReport:
        """Scan git diff for newly introduced dependencies and imports."""
        start_time = time.time()
        effective_repo = (repo_dir or Path.cwd()).resolve()

        # Build git diff command
        cmd = ["git", "diff", "--no-color", "-U0"]
        if staged:
            cmd.append("--cached")
        elif working_tree:
            pass  # default git diff covers working tree
        elif rev_or_range:
            cmd.append(rev_or_range)
        else:
            # Default to staged + unstaged changes against HEAD, fallback to HEAD~1
            # First check if git repo has commits
            try:
                res = subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD"],
                    cwd=str(effective_repo),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                if res.returncode == 0:
                    cmd.append("HEAD")
            except Exception:
                pass

        try:
            diff_proc = subprocess.run(
                cmd,
                cwd=str(effective_repo),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            diff_text = diff_proc.stdout
        except Exception as e:
            report = ScanReport(target=f"git diff ({' '.join(cmd)})")
            report.dependencies = [
                Dependency(
                    name="git-diff-failed",
                    ecosystem="unknown",
                    source_file="",
                    status=Status.ERROR,
                    details=f"Failed to execute git diff: {str(e)}"
                )
            ]
            report.compute_metrics()
            return report

        # Parse diff text into added lines per file
        deps = self._parse_git_diff_content(diff_text)
        unique_deps = self._deduplicate(deps)
        verified_deps = self.verifier.verify_all(unique_deps, root_dir=effective_repo)

        report = ScanReport(
            target=f"git diff {' '.join(cmd[2:]) or 'working tree'}",
            dependencies=verified_deps,
            scan_duration_ms=(time.time() - start_time) * 1000,
        )
        report.compute_metrics()
        return report

    def _parse_git_diff_content(self, diff_text: str) -> List[Dependency]:
        """Extract newly added imports and dependencies from git diff output."""
        deps: List[Dependency] = []
        current_file: Optional[str] = None
        added_lines: List[str] = []

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                # Flush previous file additions
                if current_file and added_lines:
                    deps.extend(self._extract_from_added_lines(current_file, "\n".join(added_lines)))
                current_file = line[6:].strip()
                added_lines = []
            elif line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])  # strip leading '+'

        # Flush final file
        if current_file and added_lines:
            deps.extend(self._extract_from_added_lines(current_file, "\n".join(added_lines)))

        return deps

    def _extract_from_added_lines(self, file_path: str, added_content: str) -> List[Dependency]:
        """Extract dependencies from the added lines of a single file in a diff."""
        file_name = Path(file_path).name.lower()
        extracted: List[Dependency] = []

        if "requirement" in file_name and file_name.endswith(".txt"):
            extracted = extract_from_requirements(added_content, file_path)
        elif file_name == "package.json":
            extracted = extract_from_package_json(added_content, file_path)
        elif file_name == "pyproject.toml":
            extracted = extract_from_pyproject_toml(added_content, file_path)
        elif file_name == "cargo.toml":
            extracted = extract_from_cargo_toml(added_content, file_path)
        elif file_name == "go.mod":
            extracted = extract_from_go_mod(added_content, file_path)
        elif file_name.endswith(".py"):
            extracted = extract_from_python_code(added_content, file_path)
        elif file_name.endswith((".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")):
            extracted = extract_from_js_code(added_content, file_path)
        elif file_name.endswith(".rs"):
            extracted = extract_from_rust_code(added_content, file_path)
        elif file_name.endswith(".go"):
            extracted = extract_from_go_code(added_content, file_path)

        for dep in extracted:
            dep.source_type = "diff_add"

        return extracted

    def _scan_single_file(self, file_path: Path, rel_path: str) -> List[Dependency]:
        """Scan a single physical file on disk."""
        name = file_path.name.lower()
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        if "requirement" in name and name.endswith(".txt"):
            return extract_from_requirements(content, rel_path)
        elif name == "package.json":
            return extract_from_package_json(content, rel_path)
        elif name == "pyproject.toml":
            return extract_from_pyproject_toml(content, rel_path)
        elif name == "cargo.toml":
            return extract_from_cargo_toml(content, rel_path)
        elif name == "go.mod":
            return extract_from_go_mod(content, rel_path)
        elif name.endswith(".py"):
            return extract_from_python_code(content, rel_path)
        elif name.endswith((".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")):
            return extract_from_js_code(content, rel_path)
        elif name.endswith(".rs"):
            return extract_from_rust_code(content, rel_path)
        elif name.endswith(".go"):
            return extract_from_go_code(content, rel_path)

        return []

    def _deduplicate(self, deps: List[Dependency]) -> List[Dependency]:
        """Deduplicate dependencies with same name and ecosystem."""
        seen: Set[str] = set()
        unique: List[Dependency] = []
        for dep in deps:
            key = f"{dep.ecosystem}:{dep.name.lower()}:{dep.source_file}:{dep.line_number or 0}"
            if key not in seen:
                seen.add(key)
                unique.append(dep)
        return unique
