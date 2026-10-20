"""Dependency extractors for manifests and source code files."""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional, Set

from ghostdep.models import Dependency, Ecosystem
from ghostdep.stdlib import is_stdlib

# Try tomllib for Python 3.11+, fallback to lightweight regex parser
try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore


# Regular expressions for manifests and code
REQUIREMENTS_LINE_RE = re.compile(r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]*\])?(?:\s*(?:==|>=|<=|~=|!=|<|>|===)\s*([^;,\s]+))?")
JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:(?:[\w*\s{},]*)\s+from\s+)?['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\)|import\s*\(\s*['"]([^'"]+)['"]\s*\)|export\s+(?:(?:[\w*\s{},]*)\s+from\s+)?['"]([^'"]+)['"])"""
)
RUST_USE_RE = re.compile(r"(?:use\s+([a-zA-Z0-9_]+)::|extern\s+crate\s+([a-zA-Z0-9_]+);)")
GO_IMPORT_RE = re.compile(r"""(?:import\s+['"]([^'"]+)['"]|import\s*\(\s*([^)]+)\))""")


def extract_from_requirements(content: str, file_path: str = "requirements.txt") -> List[Dependency]:
    deps: List[Dependency] = []
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        # Skip empty lines, comments, and flags like -r, -e, -i
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip trailing comments
        line = line.split("#")[0].strip()
        match = REQUIREMENTS_LINE_RE.match(line)
        if match:
            pkg_name = match.group(1).strip()
            version_spec = match.group(2) if match.group(2) else None
            # Skip local directory paths or file references
            if pkg_name.startswith((".", "/")):
                continue
            deps.append(Dependency(
                name=pkg_name,
                ecosystem=Ecosystem.PYTHON.value,
                source_file=file_path,
                line_number=line_no,
                version_spec=version_spec,
                source_type="manifest",
            ))
    return deps


def extract_from_package_json(content: str, file_path: str = "package.json") -> List[Dependency]:
    deps: List[Dependency] = []
    try:
        data = json.loads(content)
    except Exception:
        return deps

    sections = ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]
    for section in sections:
        sec_dict = data.get(section, {})
        if isinstance(sec_dict, dict):
            for pkg_name, version in sec_dict.items():
                deps.append(Dependency(
                    name=pkg_name,
                    ecosystem=Ecosystem.NPM.value,
                    source_file=file_path,
                    line_number=None,
                    version_spec=str(version) if version else None,
                    source_type="manifest",
                    details=f"Declared in {section}"
                ))
    return deps


def extract_from_pyproject_toml(content: str, file_path: str = "pyproject.toml") -> List[Dependency]:
    deps: List[Dependency] = []
    if tomllib:
        try:
            data = tomllib.loads(content)
            # standard project.dependencies
            project = data.get("project", {})
            for req in project.get("dependencies", []):
                match = REQUIREMENTS_LINE_RE.match(req.strip())
                if match:
                    deps.append(Dependency(
                        name=match.group(1).strip(),
                        ecosystem=Ecosystem.PYTHON.value,
                        source_file=file_path,
                        version_spec=match.group(2) if match.group(2) else None,
                        source_type="manifest",
                        details="project.dependencies"
                    ))
            # poetry dependencies
            tool = data.get("tool", {})
            poetry = tool.get("poetry", {})
            poetry_deps = poetry.get("dependencies", {})
            if isinstance(poetry_deps, dict):
                for pkg_name, ver in poetry_deps.items():
                    if pkg_name.lower() == "python":
                        continue
                    v_str = ver if isinstance(ver, str) else ver.get("version") if isinstance(ver, dict) else None
                    deps.append(Dependency(
                        name=pkg_name,
                        ecosystem=Ecosystem.PYTHON.value,
                        source_file=file_path,
                        version_spec=v_str,
                        source_type="manifest",
                        details="tool.poetry.dependencies"
                    ))
            return deps
        except Exception:
            pass

    # Fallback regex parser for TOML dependencies
    in_deps_section = False
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if line.startswith("["):
            sec = line.strip("[] \t").lower()
            in_deps_section = sec in ("project.dependencies", "tool.poetry.dependencies")
            continue
        if in_deps_section:
            if "=" in line:
                key, val = line.split("=", 1)
                pkg = key.strip().strip('"\'')
                if pkg and pkg.lower() != "python":
                    deps.append(Dependency(
                        name=pkg,
                        ecosystem=Ecosystem.PYTHON.value,
                        source_file=file_path,
                        line_number=line_no,
                        source_type="manifest",
                    ))
            elif line.startswith('"') or line.startswith("'"):
                pkg_val = line.strip(',"\' ')
                match = REQUIREMENTS_LINE_RE.match(pkg_val)
                if match:
                    deps.append(Dependency(
                        name=match.group(1).strip(),
                        ecosystem=Ecosystem.PYTHON.value,
                        source_file=file_path,
                        line_number=line_no,
                        version_spec=match.group(2) if match.group(2) else None,
                        source_type="manifest",
                    ))
    return deps


def extract_from_cargo_toml(content: str, file_path: str = "Cargo.toml") -> List[Dependency]:
    deps: List[Dependency] = []
    in_dep_section = False
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.split("#")[0].strip()
        if not line:
            continue
        if line.startswith("["):
            sec = line.strip("[] \t").lower()
            in_dep_section = any(k in sec for k in ["dependencies", "dev-dependencies", "build-dependencies"])
            continue
        if in_dep_section and "=" in line:
            pkg_name = line.split("=", 1)[0].strip().strip('"\'')
            if pkg_name:
                deps.append(Dependency(
                    name=pkg_name,
                    ecosystem=Ecosystem.CARGO.value,
                    source_file=file_path,
                    line_number=line_no,
                    source_type="manifest",
                ))
    return deps


def extract_from_go_mod(content: str, file_path: str = "go.mod") -> List[Dependency]:
    deps: List[Dependency] = []
    in_require_block = False
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.split("//")[0].strip()
        if not line:
            continue
        if line.startswith("require ("):
            in_require_block = True
            continue
        elif in_require_block and line.startswith(")"):
            in_require_block = False
            continue
        elif line.startswith("require ") and not in_require_block:
            parts = line[8:].strip().split()
            if parts:
                deps.append(Dependency(
                    name=parts[0],
                    ecosystem=Ecosystem.GO.value,
                    source_file=file_path,
                    line_number=line_no,
                    version_spec=parts[1] if len(parts) > 1 else None,
                    source_type="manifest",
                ))
        elif in_require_block:
            parts = line.split()
            if parts:
                deps.append(Dependency(
                    name=parts[0],
                    ecosystem=Ecosystem.GO.value,
                    source_file=file_path,
                    line_number=line_no,
                    version_spec=parts[1] if len(parts) > 1 else None,
                    source_type="manifest",
                ))
    return deps


def extract_from_python_code(content: str, file_path: str = "") -> List[Dependency]:
    deps: List[Dependency] = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    deps.append(Dependency(
                        name=root,
                        ecosystem=Ecosystem.PYTHON.value,
                        source_file=file_path,
                        line_number=getattr(node, "lineno", None),
                        source_type="import",
                    ))
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    root = node.module.split(".")[0]
                    deps.append(Dependency(
                        name=root,
                        ecosystem=Ecosystem.PYTHON.value,
                        source_file=file_path,
                        line_number=getattr(node, "lineno", None),
                        source_type="import",
                    ))
        return deps
    except SyntaxError:
        # Fallback regex for snippets or diff additions that may not be valid full files
        for line_no, line in enumerate(content.splitlines(), start=1):
            line_str = line.strip()
            match_from = re.match(r"^from\s+([a-zA-Z0-9_\.]+)\s+import", line_str)
            if match_from and not match_from.group(1).startswith("."):
                root = match_from.group(1).split(".")[0]
                deps.append(Dependency(
                    name=root,
                    ecosystem=Ecosystem.PYTHON.value,
                    source_file=file_path,
                    line_number=line_no,
                    source_type="import",
                ))
            match_imp = re.match(r"^import\s+([a-zA-Z0-9_\.]+)", line_str)
            if match_imp:
                root = match_imp.group(1).split(".")[0]
                deps.append(Dependency(
                    name=root,
                    ecosystem=Ecosystem.PYTHON.value,
                    source_file=file_path,
                    line_number=line_no,
                    source_type="import",
                ))
        return deps


def extract_from_js_code(content: str, file_path: str = "") -> List[Dependency]:
    deps: List[Dependency] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in JS_IMPORT_RE.finditer(line):
            pkg_raw = next((g for g in match.groups() if g is not None), None)
            if not pkg_raw:
                continue
            pkg = pkg_raw.strip()
            # Ignore relative imports and path aliases
            if pkg.startswith((".", "/", "~/", "@/")):
                continue
            # Handle scoped packages (e.g. @org/package/sub -> @org/package)
            if pkg.startswith("@"):
                parts = pkg.split("/")
                pkg_name = f"{parts[0]}/{parts[1]}" if len(parts) > 1 else pkg
            else:
                pkg_name = pkg.split("/")[0]

            deps.append(Dependency(
                name=pkg_name,
                ecosystem=Ecosystem.NPM.value,
                source_file=file_path,
                line_number=line_no,
                source_type="import",
            ))
    return deps


def extract_from_rust_code(content: str, file_path: str = "") -> List[Dependency]:
    deps: List[Dependency] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in RUST_USE_RE.finditer(line):
            pkg = next((g for g in match.groups() if g is not None), None)
            if not pkg:
                continue
            pkg_clean = pkg.strip()
            if pkg_clean in ("crate", "super", "self"):
                continue
            deps.append(Dependency(
                name=pkg_clean,
                ecosystem=Ecosystem.CARGO.value,
                source_file=file_path,
                line_number=line_no,
                source_type="import",
            ))
    return deps


def extract_from_go_code(content: str, file_path: str = "") -> List[Dependency]:
    deps: List[Dependency] = []
    in_import_block = False

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.split("//")[0].strip()
        if not line:
            continue

        if line.startswith("import ("):
            in_import_block = True
            continue
        elif in_import_block and line.startswith(")"):
            in_import_block = False
            continue
        elif in_import_block:
            cleaned = line.strip().strip('"')
            if cleaned:
                deps.append(Dependency(
                    name=cleaned,
                    ecosystem=Ecosystem.GO.value,
                    source_file=file_path,
                    line_number=line_no,
                    source_type="import",
                ))
        elif line.startswith("import "):
            # Single line import, e.g. import "fmt" or import mypkg "github.com/..."
            match = re.search(r'import\s+(?:[a-zA-Z0-9_]+\s+)?["\']([^"\']+)["\']', line)
            if match:
                deps.append(Dependency(
                    name=match.group(1).strip(),
                    ecosystem=Ecosystem.GO.value,
                    source_file=file_path,
                    line_number=line_no,
                    source_type="import",
                ))
    return deps
