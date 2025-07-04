#!/usr/bin/env python3
"""
Setup script for LLM Output Scrub macOS app.
This file is kept for py2app compatibility but uses modern PEP 517 standards.
"""

from typing import List, Tuple
from setuptools import setup  # type: ignore

# py2app configuration
APP = ["main.py"]
DATA_FILES: List[Tuple[str, List[str]]] = []
OPTIONS = {
    "iconfile": "assets/icon.icns",  # Optional: add if you have an icon
    "plist": {
        "CFBundleName": "LLM Output Scrub",
        "CFBundleDisplayName": "LLM Output Scrub",
        "CFBundleGetInfoString": ("Scrubs smart/typographic characters from LLM output"),
        "CFBundleIdentifier": "com.llmoutputscrub.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHumanReadableCopyright": "Copyright © 2025 MIT License",
        "LSUIElement": True,  # Makes it a background app (no dock icon)
    },
    "excludes": [],
    "packages": ["rumps", "platformdirs"],
    "includes": ["jaraco.text"],
    "site_packages": False,
}

if __name__ == "__main__":
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={"py2app": OPTIONS},
        setup_requires=["py2app"],
    )
