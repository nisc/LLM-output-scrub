#!/usr/bin/env python3
"""Setup script for LLM Output Scrub macOS app."""

import os
import shutil
from typing import List, Tuple
from setuptools import setup  # type: ignore

MODEL_ASSET_DIR = os.path.join("assets", "en_core_web_sm")
MODEL_DATA_SUBDIR = "en_core_web_sm-3.8.0"


# Copy spaCy model from venv to assets/en_core_web_sm/ if needed
def ensure_spacy_model_asset() -> None:
    """Copy spaCy en_core_web_sm model from venv to assets for bundling."""
    try:
        import en_core_web_sm  # type: ignore[import-untyped]  # pylint: disable=import-outside-toplevel

        venv_model_dir = os.path.dirname(en_core_web_sm.__file__)
        venv_model_data_dir = os.path.join(venv_model_dir, MODEL_DATA_SUBDIR)
        asset_model_data_dir = os.path.join(MODEL_ASSET_DIR, MODEL_DATA_SUBDIR)
        if not os.path.exists(asset_model_data_dir) or not os.listdir(asset_model_data_dir):
            src = venv_model_data_dir
            dst = asset_model_data_dir
            print(f"Copying spaCy model from {src} to {dst}")
            os.makedirs(MODEL_ASSET_DIR, exist_ok=True)
            if os.path.exists(asset_model_data_dir):
                shutil.rmtree(asset_model_data_dir)
            shutil.copytree(venv_model_data_dir, asset_model_data_dir)
        else:
            print(f"spaCy model already present in {asset_model_data_dir}")
    except ImportError:
        print("Warning: en_core_web_sm not found in venv, model will not be bundled!")


# Always call this before setup()
ensure_spacy_model_asset()


def get_spacy_model_data() -> List[Tuple[str, List[str]]]:
    """Return (destination, [file]) tuples for spaCy model files."""
    model_data_dir = os.path.join(MODEL_ASSET_DIR, MODEL_DATA_SUBDIR)
    if not os.path.exists(model_data_dir):
        print(f"Warning: spaCy model data not found at {model_data_dir}")
        return []
    data_files = []
    for root, _, files in os.walk(model_data_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, model_data_dir)
            dest_dir = os.path.join("en_core_web_sm", os.path.dirname(rel_path))
            data_files.append((dest_dir, [file_path]))
    mdir = model_data_dir
    print(f"Including spaCy model data from: {mdir}")
    return data_files


# py2app configuration
APP = ["src/llm_output_scrub/app.py"]
DATA_FILES: List[Tuple[str, List[str]]] = get_spacy_model_data()
OPTIONS = {
    "iconfile": "assets/icon.icns",
    "plist": {
        "CFBundleName": "LLM Output Scrub",
        "CFBundleDisplayName": "LLM Output Scrub",
        "CFBundleGetInfoString": ("Converts typographic characters to ASCII using spaCy NLP"),
        "CFBundleIdentifier": "com.llmoutputscrub.app",
        "CFBundleVersion": "0.2.0",
        "CFBundleShortVersionString": "0.2.0",
        "NSHumanReadableCopyright": "Copyright © 2025 MIT License",
        "LSUIElement": True,  # Makes it a background app (no dock icon)
    },
    "excludes": ["pygments", "smart_open"],
    "packages": [
        "rumps",
        "llm_output_scrub",
        "spacy",
        "thinc",
        "blis",
        "preshed",
        "cymem",
        "murmurhash",
        "wasabi",
        "srsly",
        "catalogue",
        "packaging",
        "setuptools",
        "numpy",
    ],
    "includes": [
        "jaraco.text",
        "spacy.lang.en",
        "spacy.lang.en.syntax_iterators",
        "spacy.lang.en.tag_map",
        "spacy.lang.en.stop_words",
        "spacy.lang.en.lemmatizer",
        "spacy.lang.en.tokenizer_exceptions",
        "spacy.lang.en.punctuation",
        "spacy.lang.en.norm_exceptions",
        "spacy.lang.en.lex_attrs",
    ],
    "site_packages": False,
    "resources": [],
    "frameworks": [],
    "dylib_excludes": [],
}

if __name__ == "__main__":
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={"py2app": OPTIONS},
        setup_requires=["py2app"],
        extras_require={
            "dev": [
                "isort>=5.0.0",
            ],
        },
    )
