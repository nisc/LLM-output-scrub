#!/usr/bin/env python3
"""
Configuration for LLM Output Scrub character replacements.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ScrubConfig:
    """Configuration manager for character replacements."""

    def __init__(self, config_file: Optional[str] = None):
        if config_file is None:
            # Default to user's home directory
            config_dir = Path.home() / ".llm_output_scrub"
            config_dir.mkdir(exist_ok=True)
            config_file = str(config_dir / "config.json")

        self.config_file = Path(config_file)
        self.config = self._load_default_config()
        self.load_config()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load the default configuration with all replacements enabled."""
        return {
            "general": {
                "normalize_unicode": True,
                "normalize_whitespace": True,
                "remove_combining_chars": False,
                "remove_non_ascii": False,
            },
            "character_replacements": {
                "smart_quotes": {
                    "enabled": True,
                    "replacements": {
                        "\u201c": '"',
                        "\u201d": '"',
                        "\u2018": "'",
                        "\u2019": "'",
                    },
                },
                "dashes": {
                    "enabled": True,
                    "replacements": {
                        "–": "-",  # EN dash: simple replacement
                    },
                    # EM dash (—) uses context-aware replacement logic, not simple substitution
                },
                "ellipsis": {
                    "enabled": True,
                    "replacements": {
                        "…": "...",
                    },
                },
                "angle_quotes": {
                    "enabled": False,
                    "replacements": {
                        "‹": "<",
                        "›": ">",
                        "«": "<<",
                        "»": ">>",
                    },
                },
                "trademarks": {
                    "enabled": False,
                    "replacements": {
                        "™": "(TM)",
                        "®": "(R)",
                    },
                },
                "mathematical": {
                    "enabled": False,
                    "replacements": {
                        "≤": "<=",
                        "≥": ">=",
                        "≠": "!=",
                        "≈": "~",
                        "±": "+/-",
                    },
                },
                "fractions": {
                    "enabled": False,
                    "replacements": {
                        "¼": "1/4",
                        "½": "1/2",
                        "¾": "3/4",
                    },
                },
                "footnotes": {
                    "enabled": False,
                    "replacements": {
                        "†": "*",
                        "‡": "**",
                    },
                },
                "units": {
                    "enabled": False,
                    "replacements": {
                        "×": "*",
                        "÷": "/",
                        "‰": "per thousand",
                        "‱": "per ten thousand",
                    },
                },
                "currency": {
                    "enabled": False,
                    "replacements": {
                        "€": "EUR",
                        "£": "GBP",
                        "¥": "JPY",
                        "¢": "cents",
                    },
                },
            },
        }

    def load_config(self) -> None:
        """Load configuration from file, creating default if it doesn't exist."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to handle missing keys
                    self._merge_config(self.config, loaded_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
        else:
            self.save_config()

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> None:
        """Recursively merge loaded config with defaults."""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value

    def get_all_replacements(self) -> Dict[str, str]:
        """Get all enabled character replacements as a flat dictionary."""
        replacements = {}

        for _, category in self.config["character_replacements"].items():
            if category.get("enabled", True):
                replacements.update(category.get("replacements", {}))

        return replacements

    def set_category_enabled(self, category: str, enabled: bool) -> None:
        """Enable or disable a category of replacements."""
        if category in self.config["character_replacements"]:
            self.config["character_replacements"][category]["enabled"] = enabled
            self.save_config()

    def is_category_enabled(self, category: str) -> bool:
        """Check if a category is enabled."""
        value = self.config["character_replacements"].get(category, {}).get("enabled", True)
        if isinstance(value, bool):
            return value
        return True

    def get_categories(self) -> list:
        """Get list of all available categories."""
        return list(self.config["character_replacements"].keys())

    def get_config_path(self) -> str:
        """Get the path to the configuration file."""
        return str(self.config_file)
