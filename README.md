# 👻 ghostdep

> **Catch AI package hallucinations and slopsquatting traps before you `npm install`, `pip install`, or push to `main`.**

[![CI](https://github.com/Nithinfgs/ghostdep/actions/workflows/ci.yml/badge.svg)](https://github.com/Nithinfgs/ghostdep/actions/workflows/ci.yml)
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/ghostdep/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](https://github.com/Nithinfgs/ghostdep)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## The Problem: AI Package Hallucination & Slopsquatting

When AI coding agents (Claude Code, Cursor, Copilot, Codex, Antigravity) write code, they frequently invent dependencies:

```python
# LLM hallucination: this package does NOT exist on PyPI!
import fastapi_jwt_auth_helpers
from langchain_community_vector_cache import VectorCache
```

Or in `package.json`:
```json
{
  "dependencies": {
    "@tanstack/react-query-local-persist": "^5.0.0"
  }
}
```

Attackers actively monitor LLM hallucination benchmarks and common agent prompt patterns (the **AI Package Hallucination Attack** / **Slopsquatting** documented in USENIX Security). When an agent hallucinates a package name, attackers register it on public registries (PyPI, npm, crates.io).

The moment a developer or automated CI workflow runs `pip install` or `npm install`, the attacker's payload executes with full user permissions.

**`ghostdep` prevents this.** It inspects your files, manifests, or `git diff`, extracts newly introduced packages and imports, verifies them against live registries or offline databases, and flags phantom hallucinations and newborn squatting traps before damage is done.

---

## ✨ Features

- ⚡ **Zero Dependencies**: Pure Python standard library. Runs anywhere instantly.
- 🎯 **Git Diff Mode**: Inspects *only* newly added imports and dependencies in your uncommitted changes, PR branches, or agent edits (`ghostdep diff`).
- 🔍 **Multi-Ecosystem**:
  - **Python**: `requirements*.txt`, `pyproject.toml`, `setup.py`, AST imports (`import foo`, `from bar import baz`).
  - **JavaScript / TypeScript**: `package.json`, ESM/CJS imports (`import ... from 'pkg'`, `require('pkg')`, `@scope/pkg`).
  - **Rust**: `Cargo.toml`, `use pkg::...`, `extern crate pkg;`.
  - **Go**: `go.mod`, `import "pkg"` and block imports.
- 👻 **Hallucination Detection**: Pinpoints packages with HTTP 404 on official registries (high risk of attacker pre-registration).
- 🐣 **Newborn & Slopsquatting Heuristics**: Flags packages published < 14 days ago, single-version releases with empty metadata, or Levenshtein typos of top libraries (e.g. `pydantic-auth-ext` vs `pydantic`).
- 📦 **Standard Library & Local Awareness**: Instantly recognizes language built-ins (`os`, `sys`, `fs`, `path`, `fmt`, `std`) and relative workspace modules without network queries.
- 🚀 **Blazing Fast**: Non-blocking thread pool queries with automatic local disk caching (`~/.cache/ghostdep/`).
- 📴 **Offline Mode**: Operates fully disconnected with `--offline` using embedded standard library and top-tier package databases.
- 🤖 **Agent & CI Ready**: Structured `--json` output, configurable exit codes (`--fail-on phantom`), and sub-millisecond execution.

---

## 🚀 Quickstart

### Installation

```bash
# Clone and install
git clone https://github.com/Nithinfgs/ghostdep.git
cd ghostdep
pip install .
```

Or run directly without installing:

```bash
python3 -m ghostdep.cli scan .
```

---

## 💻 Usage

### 1. Scan Git Diff (Recommended for Pre-Commit & Coding Agents)

Inspect newly added imports or dependencies in your working tree:

```bash
ghostdep diff
```

Scan only staged changes right before committing:

```bash
ghostdep diff --staged
```

Scan a branch or commit range in CI:

```bash
ghostdep diff main..HEAD
```

### 2. Scan Project Files & Manifests

Scan the entire repository:

```bash
ghostdep scan .
```

Scan a single manifest:

```bash
ghostdep scan requirements.txt
ghostdep scan package.json
```

### 3. Terminal Output

```
👻 ghostdep — AI Hallucination & Slopsquatting Detector
Target: git diff (working tree) | Scanned in 420.5ms

STATUS         PACKAGE                          ECOSYSTEM LOCATION                 DETAILS
──────────────────────────────────────────────────────────────────────────────────────────────────────────
👻 PHANTOM     fastapi_jwt_auth_helpers         python    src/auth.py:4            Not found on PyPI! Hallucination risk. Did you mean 'fastapi'?
⚠️ SUSPICIOUS   pydantic-core-ext                python    requirements.txt:12      TYPO OF 'pydantic'! Single release with minimal metadata
🐣 NEWBORN     temp-eval-runner                 npm       package.json             Published 4d ago (2026-10-16)
✓ VERIFIED     requests                         python    src/client.py:2          Active PyPI package (v2.32.3)
📦 STDLIB       sys                              python    src/client.py:1          Built-in python standard library
──────────────────────────────────────────────────────────────────────────────────────────────────────────
Summary: 👻 1 phantom (NOT on registry), ⚠️ 1 suspicious, 🐣 1 newborn, ✓ 1 verified, 📦 1 stdlib

✖ FAILED: Hallucinated dependencies detected! Registering or installing these could lead to RCE or slopsquatting attacks.
```

---

## 🛠️ CLI Options

| Flag | Description |
|------|-------------|
| `ghostdep scan [path]` | Scan project directory or file (default: `.`) |
| `ghostdep diff [rev]` | Scan newly added dependencies in git diff |
| `--staged` | In diff mode, scan staged changes only |
| `--fail-on <level>` | Exit with code 1 if matching status found (`phantom`, `suspicious`, `newborn`, `any`) |
| `--strict` | Equivalent to `--fail-on suspicious` |
| `--offline` | Do not query registry APIs; verify against stdlib and local DB |
| `--json` | Output structured JSON for CI scripts and bots |
| `-q`, `--quiet` | Minimal output; prints only problematic packages |
| `-v`, `--verbose` | Display all verified and stdlib packages in the output table |
| `ghostdep clean-cache` | Clear cached registry responses |

---

## 🤖 AI Coding Agent Integration

### Claude Code / Cursor Post-Execution Hook

Add `ghostdep diff` to your agent verification checklist or shell hook so every file generated by an LLM is audited before install:

```bash
# In your agent task runner or script
ghostdep diff --fail-on phantom || {
    echo "Agent attempted to introduce hallucinated dependencies!"
    exit 1
}
```

### Git Pre-Commit Hook

Prevent accidentally committing phantom dependencies:

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
ghostdep diff --staged --fail-on phantom
```

### GitHub Actions CI Workflow

```yaml
name: Supply Chain Audit

on: [pull_request]

jobs:
  audit-dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install ghostdep
        run: pip install git+https://github.com/Nithinfgs/ghostdep.git

      - name: Audit PR dependencies
        run: ghostdep diff origin/${{ github.base_ref }}..HEAD --strict
```

---

## 🧪 Testing

Run the full test suite across unit and live registry tests:

```bash
python3 -m unittest discover tests -v
```

All 24 tests run in under 0.01 seconds.

---

## 📄 License

MIT © [Nithinfgs](https://github.com/Nithinfgs)
