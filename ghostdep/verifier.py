"""Registry verification, hallucination detection, and slopsquatting checks."""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set

from ghostdep.models import Dependency, Status, Ecosystem
from ghostdep.stdlib import (
    is_stdlib,
    TOP_POPULAR_PYTHON,
    TOP_POPULAR_NPM,
)
from ghostdep.cache import RegistryCache

USER_AGENT = "ghostdep/0.1.0 (+https://github.com/Nithinfgs/ghostdep)"
REQUEST_TIMEOUT = 3.5  # seconds


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def check_typosquatting(name: str, ecosystem: str) -> Optional[str]:
    """Check if name is dangerously close to a top popular package (slopsquatting)."""
    name_lower = name.lower()
    targets: Set[str] = TOP_POPULAR_PYTHON if ecosystem == Ecosystem.PYTHON.value else TOP_POPULAR_NPM if ecosystem == Ecosystem.NPM.value else set()
    
    # Exact match in target popular list
    if name_lower in targets or name_lower.replace("_", "-") in targets or name_lower.replace("-", "_") in targets:
        return None

    normalized_name = name_lower.replace("_", "-")

    for target in targets:
        normalized_target = target.replace("_", "-")

        # Prefix or suffix addition (e.g. pydantic-auth, requests-helper, pydantic_core_ext)
        if normalized_name.startswith(f"{normalized_target}-") or normalized_name.endswith(f"-{normalized_target}"):
            # Often used by AI hallucinations
            return target
        
        # Levenshtein distance 1 or 2 for similar length
        if len(normalized_name) >= 4 and abs(len(normalized_name) - len(normalized_target)) <= 2:
            dist = levenshtein_distance(normalized_name, normalized_target)
            if dist == 1 or (dist == 2 and len(normalized_name) >= 7):
                return target
    return None


class DependencyVerifier:
    def __init__(self, cache: Optional[RegistryCache] = None, offline: bool = False, max_workers: int = 8):
        self.cache = cache or RegistryCache()
        self.offline = offline
        self.max_workers = max_workers

    def verify_all(self, dependencies: List[Dependency], root_dir: Optional[Path] = None) -> List[Dependency]:
        """Verify a list of dependencies concurrently and populate status/risk scores."""
        # Step 1: Detect stdlib & local packages first
        pending_check: List[Dependency] = []
        for dep in dependencies:
            if is_stdlib(dep.name, dep.ecosystem):
                dep.status = Status.STDLIB
                dep.risk_score = 0
                dep.details = f"Built-in {dep.ecosystem} standard library"
                continue

            if root_dir and self._is_local_module(dep.name, dep.ecosystem, root_dir):
                dep.status = Status.LOCAL
                dep.risk_score = 0
                dep.details = "Local workspace module / relative package"
                continue

            # Check cached results
            cached = self.cache.get(dep.ecosystem, dep.name)
            if cached:
                self._apply_metadata(dep, cached)
                continue

            pending_check.append(dep)

        if not pending_check:
            return dependencies

        # Step 2: Handle offline mode
        if self.offline:
            for dep in pending_check:
                self._verify_offline(dep)
            return dependencies

        # Step 3: Run concurrent online checks for unique packages
        unique_tasks: Dict[Tuple[str, str], List[Dependency]] = {}
        for dep in pending_check:
            key = (dep.ecosystem, dep.name.lower())
            unique_tasks.setdefault(key, []).append(dep)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_key = {
                executor.submit(self._fetch_registry_info, eco, name): (eco, name)
                for (eco, name) in unique_tasks.keys()
            }
            for future in as_completed(future_to_key):
                eco, name = future_to_key[future]
                deps_group = unique_tasks[(eco, name)]
                try:
                    info = future.result()
                    if info:
                        self.cache.set(eco, name, info)
                        for dep in deps_group:
                            self._apply_metadata(dep, info)
                except Exception as ex:
                    for dep in deps_group:
                        dep.status = Status.ERROR
                        dep.details = f"Check failed: {str(ex)}"
                        dep.risk_score = 30

        return dependencies

    def _is_local_module(self, name: str, ecosystem: str, root_dir: Path) -> bool:
        """Check if package name corresponds to a local file or directory."""
        clean_name = name.split(".")[0].replace("-", "_")
        if ecosystem == Ecosystem.PYTHON.value:
            if (root_dir / f"{clean_name}.py").exists():
                return True
            if (root_dir / clean_name).is_dir() and ((root_dir / clean_name / "__init__.py").exists() or (root_dir / clean_name / "py.typed").exists()):
                return True
            if (root_dir / "src" / clean_name).is_dir():
                return True
            if (root_dir / "src" / f"{clean_name}.py").exists():
                return True
        elif ecosystem == Ecosystem.NPM.value:
            if (root_dir / "packages" / name).is_dir() or (root_dir / clean_name).is_dir():
                return True
        return False

    def _verify_offline(self, dep: Dependency) -> None:
        """Verify against known top packages offline."""
        typo = check_typosquatting(dep.name, dep.ecosystem)
        if typo:
            dep.status = Status.SUSPICIOUS
            dep.similar_to = typo
            dep.risk_score = 75
            dep.details = f"Offline check: potential slopsquatting / typo of '{typo}'"
            return

        if dep.ecosystem == Ecosystem.PYTHON.value and dep.name.lower() in TOP_POPULAR_PYTHON:
            dep.status = Status.VERIFIED
            dep.risk_score = 0
            dep.details = "Verified via offline known package database"
            return
        elif dep.ecosystem == Ecosystem.NPM.value and dep.name.lower() in TOP_POPULAR_NPM:
            dep.status = Status.VERIFIED
            dep.risk_score = 0
            dep.details = "Verified via offline known package database"
            return

        dep.status = Status.SKIPPED
        dep.risk_score = 40
        dep.details = "Offline mode: unverified (not in top known packages or stdlib)"

    def _fetch_registry_info(self, ecosystem: str, name: str) -> Dict[str, Any]:
        """Fetch package metadata from public registries."""
        if ecosystem == Ecosystem.PYTHON.value:
            return self._query_pypi(name)
        elif ecosystem == Ecosystem.NPM.value:
            return self._query_npm(name)
        elif ecosystem == Ecosystem.CARGO.value:
            return self._query_crates(name)
        elif ecosystem == Ecosystem.GO.value:
            return self._query_go(name)
        return {
            "status": Status.SKIPPED.value,
            "details": f"Registry lookup not supported for {ecosystem}",
            "risk_score": 10
        }

    def _query_pypi(self, name: str) -> Dict[str, Any]:
        url = f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    info = data.get("info", {})
                    releases = data.get("releases", {})
                    latest_ver = info.get("version", "unknown")

                    # Calculate age
                    age_days = None
                    pub_date = None
                    if releases and latest_ver in releases and releases[latest_ver]:
                        upload_str = releases[latest_ver][0].get("upload_time_iso_8601")
                        if upload_str:
                            try:
                                dt = datetime.fromisoformat(upload_str.replace("Z", "+00:00"))
                                age_days = (datetime.now(timezone.utc) - dt).days
                                pub_date = dt.strftime("%Y-%m-%d")
                            except Exception:
                                pass

                    typo = check_typosquatting(name, Ecosystem.PYTHON.value)
                    status = Status.VERIFIED.value
                    risk_score = 5
                    details = f"Active PyPI package (v{latest_ver})"

                    if age_days is not None and age_days < 14:
                        status = Status.NEWBORN.value
                        risk_score = 65
                        details = f"Registered {age_days}d ago ({pub_date})"
                    elif len(releases) <= 1 and (not info.get("summary") or len(info.get("summary", "")) < 10):
                        status = Status.SUSPICIOUS.value
                        risk_score = 70
                        details = "Single release with minimal/empty metadata"

                    if typo:
                        status = Status.SUSPICIOUS.value
                        risk_score = max(risk_score, 80)
                        details += f" (Warning: suspiciously similar to '{typo}')"

                    return {
                        "status": status,
                        "details": details,
                        "registry_url": f"https://pypi.org/project/{name}/",
                        "latest_version": latest_ver,
                        "age_days": age_days,
                        "published_date": pub_date,
                        "similar_to": typo,
                        "risk_score": risk_score
                    }
        except urllib.error.HTTPError as e:
            e.close()
            if e.code == 404:
                typo = check_typosquatting(name, Ecosystem.PYTHON.value)
                return {
                    "status": Status.PHANTOM.value,
                    "details": f"Not found on PyPI! Hallucination risk." + (f" Did you mean '{typo}'?" if typo else ""),
                    "registry_url": f"https://pypi.org/project/{name}/",
                    "similar_to": typo,
                    "risk_score": 95
                }
            return {
                "status": Status.ERROR.value,
                "details": f"PyPI HTTP {e.code}",
                "risk_score": 25
            }
        except Exception as e:
            return {
                "status": Status.ERROR.value,
                "details": f"PyPI request error: {str(e)}",
                "risk_score": 25
            }

    def _query_npm(self, name: str) -> Dict[str, Any]:
        # Handle scoped package URL encoding (@org/pkg -> @org%2Fpkg)
        encoded_name = name.replace("/", "%2F")
        url = f"https://registry.npmjs.org/{encoded_name}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    dist_tags = data.get("dist-tags", {})
                    latest_ver = dist_tags.get("latest", "unknown")
                    time_data = data.get("time", {})
                    
                    age_days = None
                    pub_date = None
                    if "created" in time_data:
                        try:
                            dt = datetime.fromisoformat(time_data["created"].replace("Z", "+00:00"))
                            age_days = (datetime.now(timezone.utc) - dt).days
                            pub_date = dt.strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    typo = check_typosquatting(name, Ecosystem.NPM.value)
                    status = Status.VERIFIED.value
                    risk_score = 5
                    details = f"Active npm package (v{latest_ver})"

                    if age_days is not None and age_days < 14:
                        status = Status.NEWBORN.value
                        risk_score = 65
                        details = f"Published {age_days}d ago ({pub_date})"

                    if typo:
                        status = Status.SUSPICIOUS.value
                        risk_score = max(risk_score, 80)
                        details += f" (Warning: suspiciously similar to '{typo}')"

                    return {
                        "status": status,
                        "details": details,
                        "registry_url": f"https://www.npmjs.com/package/{name}",
                        "latest_version": latest_ver,
                        "age_days": age_days,
                        "published_date": pub_date,
                        "similar_to": typo,
                        "risk_score": risk_score
                    }
        except urllib.error.HTTPError as e:
            e.close()
            if e.code == 404:
                typo = check_typosquatting(name, Ecosystem.NPM.value)
                return {
                    "status": Status.PHANTOM.value,
                    "details": f"Not found on npm registry! Hallucination risk." + (f" Did you mean '{typo}'?" if typo else ""),
                    "registry_url": f"https://www.npmjs.com/package/{name}",
                    "similar_to": typo,
                    "risk_score": 95
                }
            return {
                "status": Status.ERROR.value,
                "details": f"npm HTTP {e.code}",
                "risk_score": 25
            }
        except Exception as e:
            return {
                "status": Status.ERROR.value,
                "details": f"npm request error: {str(e)}",
                "risk_score": 25
            }

    def _query_crates(self, name: str) -> Dict[str, Any]:
        url = f"https://crates.io/api/v1/crates/{urllib.parse.quote(name)}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    crate = data.get("crate", {})
                    latest_ver = crate.get("max_version", "unknown")
                    return {
                        "status": Status.VERIFIED.value,
                        "details": f"Active Crates.io package (v{latest_ver})",
                        "registry_url": f"https://crates.io/crates/{name}",
                        "latest_version": latest_ver,
                        "risk_score": 5
                    }
        except urllib.error.HTTPError as e:
            e.close()
            if e.code == 404:
                return {
                    "status": Status.PHANTOM.value,
                    "details": "Not found on Crates.io! Hallucination risk.",
                    "registry_url": f"https://crates.io/crates/{name}",
                    "risk_score": 95
                }
            return {
                "status": Status.ERROR.value,
                "details": f"Crates.io HTTP {e.code}",
                "risk_score": 25
            }
        except Exception as e:
            return {
                "status": Status.ERROR.value,
                "details": f"Crates.io error: {str(e)}",
                "risk_score": 25
            }

    def _query_go(self, name: str) -> Dict[str, Any]:
        # Go proxy: https://proxy.golang.org/{name}/@v/list
        url = f"https://proxy.golang.org/{urllib.parse.quote(name)}/@v/list"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    versions = response.read().decode("utf-8").strip().splitlines()
                    latest = versions[-1] if versions else "latest"
                    return {
                        "status": Status.VERIFIED.value,
                        "details": f"Verified on Go proxy (v{latest})",
                        "registry_url": f"https://pkg.go.dev/{name}",
                        "latest_version": latest,
                        "risk_score": 5
                    }
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return {
                    "status": Status.PHANTOM.value,
                    "details": "Module not found on Go proxy! Hallucination risk.",
                    "registry_url": f"https://pkg.go.dev/{name}",
                    "risk_score": 95
                }
            return {
                "status": Status.ERROR.value,
                "details": f"Go proxy HTTP {e.code}",
                "risk_score": 25
            }
        except Exception as e:
            return {
                "status": Status.ERROR.value,
                "details": f"Go proxy error: {str(e)}",
                "risk_score": 25
            }

    def _apply_metadata(self, dep: Dependency, meta: Dict[str, Any]) -> None:
        """Apply fetched metadata to Dependency object."""
        status_val = meta.get("status")
        if status_val:
            try:
                dep.status = Status(status_val)
            except ValueError:
                dep.status = Status.ERROR
        dep.details = meta.get("details", dep.details)
        dep.registry_url = meta.get("registry_url", dep.registry_url)
        dep.latest_version = meta.get("latest_version", dep.latest_version)
        dep.published_date = meta.get("published_date", dep.published_date)
        dep.age_days = meta.get("age_days", dep.age_days)
        dep.similar_to = meta.get("similar_to", dep.similar_to)
        dep.risk_score = meta.get("risk_score", dep.risk_score)
