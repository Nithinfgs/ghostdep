"""Unit tests for dependency extractors."""

import unittest
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


class TestExtractors(unittest.TestCase):
    def test_requirements_extraction(self):
        content = """
        # Core requirements
        requests==2.31.0
        pydantic>=2.0.0; sys_platform == 'linux'
        celery[redis]<=5.3.0
        # Comment line
        -e .
        --extra-index-url https://custom.repo
        langchain-community~=0.0.10
        """
        deps = extract_from_requirements(content)
        names = [d.name for d in deps]
        self.assertIn("requests", names)
        self.assertIn("pydantic", names)
        self.assertIn("celery", names)
        self.assertIn("langchain-community", names)
        self.assertNotIn("-e", names)
        self.assertNotIn("--extra-index-url", names)

    def test_package_json_extraction(self):
        content = """{
            "name": "my-app",
            "dependencies": {
                "react": "^18.2.0",
                "@tanstack/react-query": "^5.0.0"
            },
            "devDependencies": {
                "typescript": "^5.0.0",
                "vitest": "^1.0.0"
            }
        }"""
        deps = extract_from_package_json(content)
        names = [d.name for d in deps]
        self.assertIn("react", names)
        self.assertIn("@tanstack/react-query", names)
        self.assertIn("typescript", names)
        self.assertIn("vitest", names)

    def test_pyproject_toml_extraction(self):
        content = """
        [project]
        name = "demo"
        dependencies = [
            "fastapi>=0.100.0",
            "uvicorn[standard]==0.22.0",
        ]

        [tool.poetry.dependencies]
        python = "^3.10"
        httpx = "^0.24.0"
        """
        deps = extract_from_pyproject_toml(content)
        names = [d.name for d in deps]
        self.assertIn("fastapi", names)
        self.assertIn("uvicorn", names)
        self.assertIn("httpx", names)
        self.assertNotIn("python", names)

    def test_cargo_toml_extraction(self):
        content = """
        [package]
        name = "agent-core"
        version = "0.1.0"

        [dependencies]
        tokio = { version = "1", features = ["full"] }
        serde = "1.0"

        [dev-dependencies]
        tempfile = "3"
        """
        deps = extract_from_cargo_toml(content)
        names = [d.name for d in deps]
        self.assertIn("tokio", names)
        self.assertIn("serde", names)
        self.assertIn("tempfile", names)

    def test_go_mod_extraction(self):
        content = """
        module example.com/demo

        go 1.22

        require (
            github.com/gin-gonic/gin v1.9.1
            go.uber.org/zap v1.26.0
        )
        """
        deps = extract_from_go_mod(content)
        names = [d.name for d in deps]
        self.assertIn("github.com/gin-gonic/gin", names)
        self.assertIn("go.uber.org/zap", names)

    def test_python_code_extraction(self):
        code = """
import os
import sys
import numpy as np
from pydantic import BaseModel
from .local_module import helper
from ..parent_module import util
import requests.auth
"""
        deps = extract_from_python_code(code)
        names = [d.name for d in deps]
        self.assertIn("os", names)
        self.assertIn("numpy", names)
        self.assertIn("pydantic", names)
        self.assertIn("requests", names)
        # Relative imports must not be treated as third-party packages
        self.assertNotIn("local_module", names)
        self.assertNotIn("parent_module", names)

    def test_js_code_extraction(self):
        code = """
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { helper } from './utils';
import config from '../config';
const fs = require('fs');
const lodash = require('lodash');
"""
        deps = extract_from_js_code(code)
        names = [d.name for d in deps]
        self.assertIn("react", names)
        self.assertIn("@tanstack/react-query", names)
        self.assertIn("fs", names)
        self.assertIn("lodash", names)
        self.assertNotIn("./utils", names)
        self.assertNotIn("../config", names)

    def test_rust_code_extraction(self):
        code = """
use std::collections::HashMap;
use tokio::sync::Mutex;
use crate::utils::logger;
use super::parent_helper;
extern crate serde_json;
"""
        deps = extract_from_rust_code(code)
        names = [d.name for d in deps]
        self.assertIn("std", names)
        self.assertIn("tokio", names)
        self.assertIn("serde_json", names)
        self.assertNotIn("crate", names)
        self.assertNotIn("super", names)

    def test_go_code_extraction(self):
        code = """
package main

import (
    "fmt"
    "net/http"
    "github.com/stretchr/testify/assert"
)
"""
        deps = extract_from_go_code(code)
        names = [d.name for d in deps]
        self.assertIn("fmt", names)
        self.assertIn("net/http", names)
        self.assertIn("github.com/stretchr/testify/assert", names)


if __name__ == "__main__":
    unittest.main()
