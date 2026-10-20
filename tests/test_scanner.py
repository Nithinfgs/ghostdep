"""Unit tests for scanner and git diff parsing."""

import tempfile
import unittest
from pathlib import Path

from ghostdep.scanner import Scanner
from ghostdep.verifier import DependencyVerifier
from ghostdep.models import Status


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_path(self):
        # Create a sample python file and package.json
        py_file = self.root / "app.py"
        py_file.write_text("import sys\nimport requests\nfrom .local_mod import bar\n", encoding="utf-8")

        pkg_json = self.root / "package.json"
        pkg_json.write_text('{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8")

        verifier = DependencyVerifier(offline=True)
        scanner = Scanner(verifier=verifier)
        report = scanner.scan_path(self.root)

        dep_names = [d.name for d in report.dependencies]
        self.assertIn("sys", dep_names)
        self.assertIn("requests", dep_names)
        self.assertIn("react", dep_names)

        # Check metrics
        report.compute_metrics()
        self.assertEqual(report.stdlib_count, 1) # sys
        self.assertEqual(report.verified_count, 2) # requests, react

    def test_parse_git_diff_content(self):
        sample_diff = """
diff --git a/requirements.txt b/requirements.txt
index 123456..789abc 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,2 +1,4 @@
 requests==2.31.0
+langchain-community==0.0.10
+completely_fake_hallucinated_package_xyz==1.0.0
diff --git a/src/index.ts b/src/index.ts
index abc..def 100644
--- a/src/index.ts
+++ b/src/index.ts
@@ -10 +10,2 @@
 import { query } from './db';
+import { hallucinatedHelper } from 'phantom-npm-package-99';
"""
        verifier = DependencyVerifier(offline=True)
        scanner = Scanner(verifier=verifier)
        deps = scanner._parse_git_diff_content(sample_diff)

        names = [d.name for d in deps]
        self.assertIn("langchain-community", names)
        self.assertIn("completely_fake_hallucinated_package_xyz", names)
        self.assertIn("phantom-npm-package-99", names)
        self.assertNotIn("requests", names) # was unchanged, not added


if __name__ == "__main__":
    unittest.main()
