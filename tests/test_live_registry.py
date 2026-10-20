"""Integration tests against live public registries (PyPI, npm)."""

import unittest
from ghostdep.models import Dependency, Status, Ecosystem
from ghostdep.verifier import DependencyVerifier


class TestLiveRegistry(unittest.TestCase):
    def setUp(self):
        self.verifier = DependencyVerifier(offline=False)

    def test_live_pypi_verified_and_phantom(self):
        dep_real = Dependency(name="requests", ecosystem=Ecosystem.PYTHON.value, source_file="demo.py")
        dep_fake = Dependency(name="phantom_never_registered_package_7a72269a", ecosystem=Ecosystem.PYTHON.value, source_file="demo.py")

        results = self.verifier.verify_all([dep_real, dep_fake])
        real_res = next(d for d in results if d.name == "requests")
        fake_res = next(d for d in results if d.name == "phantom_never_registered_package_7a72269a")

        self.assertEqual(real_res.status, Status.VERIFIED)
        self.assertIsNotNone(real_res.latest_version)

        self.assertEqual(fake_res.status, Status.PHANTOM)
        self.assertEqual(fake_res.risk_score, 95)
        self.assertIn("Not found on PyPI", fake_res.details)

    def test_live_npm_verified_and_phantom(self):
        dep_real = Dependency(name="react", ecosystem=Ecosystem.NPM.value, source_file="index.js")
        dep_fake = Dependency(name="@ghostdep-phantom-test/never-ever-registered-99999", ecosystem=Ecosystem.NPM.value, source_file="index.js")

        results = self.verifier.verify_all([dep_real, dep_fake])
        real_res = next(d for d in results if d.name == "react")
        fake_res = next(d for d in results if d.name == "@ghostdep-phantom-test/never-ever-registered-99999")

        self.assertEqual(real_res.status, Status.VERIFIED)
        self.assertEqual(fake_res.status, Status.PHANTOM)


if __name__ == "__main__":
    unittest.main()
