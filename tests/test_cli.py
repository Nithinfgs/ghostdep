"""Integration tests for CLI entrypoint."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from ghostdep.cli import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_clean_cache(self):
        f = io.StringIO()
        with redirect_stdout(f):
            code = main(["clean-cache", "--cache-dir", str(self.root / "cache")])
        self.assertEqual(code, 0)
        self.assertIn("cleared successfully", f.getvalue())

    def test_cli_scan_json_output(self):
        # Create a sample python file
        test_file = self.root / "sample.py"
        test_file.write_text("import os\nimport sys\n", encoding="utf-8")

        f = io.StringIO()
        with redirect_stdout(f):
            code = main(["scan", str(test_file), "--json", "--offline"])
        self.assertEqual(code, 0)

        output = f.getvalue()
        data = json.loads(output)
        self.assertIn("dependencies", data)
        self.assertIn("metrics", data)
        self.assertEqual(data["metrics"]["stdlib"], 2)

    def test_cli_scan_fail_on(self):
        # Create a file with a suspicious / phantom-like package
        test_file = self.root / "suspicious.py"
        test_file.write_text("import pydantic_core_super_fake_ext\n", encoding="utf-8")

        f = io.StringIO()
        with redirect_stdout(f):
            # In offline mode, pydantic_core_super_fake_ext triggers typosquatting of pydantic -> status suspicious
            code = main(["scan", str(test_file), "--offline", "--strict"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
