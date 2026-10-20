"""Unit tests for verifier and typosquatting detection."""

import unittest
from ghostdep.models import Dependency, Status, Ecosystem
from ghostdep.verifier import levenshtein_distance, check_typosquatting, DependencyVerifier
from ghostdep.cache import RegistryCache


class TestVerifier(unittest.TestCase):
    def test_levenshtein_distance(self):
        self.assertEqual(levenshtein_distance("requests", "requests"), 0)
        self.assertEqual(levenshtein_distance("requests", "reqeusts"), 2)
        self.assertEqual(levenshtein_distance("pydantic", "pydanticc"), 1)
        self.assertEqual(levenshtein_distance("numpy", "scipy"), 3)

    def test_typosquatting_detection(self):
        # Close typos should be flagged
        flagged_python = check_typosquatting("reqeusts", "python")
        self.assertEqual(flagged_python, "requests")

        # Prefix/suffix addition of popular package
        flagged_suffix = check_typosquatting("pydantic-auth-helpers", "python")
        self.assertEqual(flagged_suffix, "pydantic")

        # Legitimate popular package should not flag itself
        self.assertIsNone(check_typosquatting("requests", "python"))
        self.assertIsNone(check_typosquatting("react", "npm"))

    def test_offline_verification(self):
        verifier = DependencyVerifier(offline=True)

        dep_stdlib = Dependency(name="os", ecosystem="python", source_file="main.py")
        dep_known = Dependency(name="requests", ecosystem="python", source_file="main.py")
        dep_unknown = Dependency(name="non_existent_super_lib_12345", ecosystem="python", source_file="main.py")
        dep_typo = Dependency(name="pydantic-secret-sauce", ecosystem="python", source_file="main.py")

        results = verifier.verify_all([dep_stdlib, dep_known, dep_unknown, dep_typo])

        self.assertEqual(results[0].status, Status.STDLIB)
        self.assertEqual(results[1].status, Status.VERIFIED)
        self.assertEqual(results[2].status, Status.SKIPPED)
        self.assertEqual(results[3].status, Status.SUSPICIOUS)
        self.assertEqual(results[3].similar_to, "pydantic")

    def test_cache_operations(self):
        cache = RegistryCache(ttl_seconds=10)
        cache.clear()
        self.assertIsNone(cache.get("python", "fake_pkg"))

        cache.set("python", "fake_pkg", {"status": "verified", "latest_version": "1.0.0"})
        cached = cache.get("python", "fake_pkg")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["status"], "verified")
        self.assertEqual(cached["latest_version"], "1.0.0")

        cache.clear()
        self.assertIsNone(cache.get("python", "fake_pkg"))


if __name__ == "__main__":
    unittest.main()
