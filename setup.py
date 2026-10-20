#!/usr/bin/env python3
"""Setup script for ghostdep."""

from setuptools import setup, find_packages

setup(
    name="ghostdep",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "ghostdep = ghostdep.cli:main",
        ],
    },
    python_requires=">=3.8",
)
