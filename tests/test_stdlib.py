"""Unit tests for stdlib and built-in detection."""

import unittest
from ghostdep.stdlib import is_stdlib


class TestStdlib(unittest.TestCase):
    def test_python_stdlib(self):
        self.assertTrue(is_stdlib("os", "python"))
        self.assertTrue(is_stdlib("sys", "python"))
        self.assertTrue(is_stdlib("urllib.parse", "python"))
        self.assertTrue(is_stdlib("asyncio", "python"))
        self.assertTrue(is_stdlib("json", "python"))
        self.assertFalse(is_stdlib("requests", "python"))
        self.assertFalse(is_stdlib("fastapi", "python"))
        self.assertFalse(is_stdlib("totally_fake_lib", "python"))

    def test_node_stdlib(self):
        self.assertTrue(is_stdlib("fs", "npm"))
        self.assertTrue(is_stdlib("path", "npm"))
        self.assertTrue(is_stdlib("node:child_process", "npm"))
        self.assertTrue(is_stdlib("crypto", "npm"))
        self.assertFalse(is_stdlib("react", "npm"))
        self.assertFalse(is_stdlib("express", "npm"))
        self.assertFalse(is_stdlib("fake_npm_package", "npm"))

    def test_rust_stdlib(self):
        self.assertTrue(is_stdlib("std", "cargo"))
        self.assertTrue(is_stdlib("core", "cargo"))
        self.assertFalse(is_stdlib("tokio", "cargo"))
        self.assertFalse(is_stdlib("serde", "cargo"))

    def test_go_stdlib(self):
        self.assertTrue(is_stdlib("fmt", "go"))
        self.assertTrue(is_stdlib("net/http", "go"))
        self.assertTrue(is_stdlib("encoding/json", "go"))
        self.assertFalse(is_stdlib("github.com/gin-gonic/gin", "go"))


if __name__ == "__main__":
    unittest.main()
