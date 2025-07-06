#!/usr/bin/env python3
"""
Configuration for LLM Output Scrub character replacements.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple


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
                "remove_combining_chars": False,
                "remove_non_ascii": False,
                "normalize_whitespace": False,
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
                "em_dashes": {
                    "enabled": True,
                    "enable_contextual_mode": True,  # Enable contextual mode (spaCy NLP)
                    "replacements": {  # Ignored in contextual mode
                        "—": "-",
                    },
                },
                "en_dashes": {
                    "enabled": True,
                    "replacements": {
                        "–": "-",  # EN dash: simple replacement
                    },
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
                        "‰": " per thousand",
                        "‱": " per ten thousand",
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
                # Skip EM dash replacements when contextual mode is enabled
                if category.get("enable_contextual_mode", False):
                    # Don't include EM dash in simple replacements when using contextual mode
                    category_replacements = category.get("replacements", {}).copy()
                    category_replacements.pop("—", None)  # Remove EM dash
                    replacements.update(category_replacements)
                else:
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
        return bool(value)

    def is_em_dash_enabled(self) -> bool:
        """Check if EM dash replacement is enabled."""
        return self.is_category_enabled("em_dashes")

    def is_em_dash_contextual(self) -> bool:
        """Check if EM dash replacement should use contextual NLP processing."""
        if not self.is_em_dash_enabled():
            return False
        return bool(
            self.config["character_replacements"].get("em_dashes", {}).get("enable_contextual_mode", True)
        )

    def set_em_dash_enabled(self, enabled: bool) -> None:
        """Enable or disable EM dash replacement."""
        self.set_category_enabled("em_dashes", enabled)

    def set_em_dash_contextual(self, contextual: bool) -> None:
        """Set whether EM dash replacement should use contextual NLP processing."""
        if "em_dashes" in self.config["character_replacements"]:
            self.config["character_replacements"]["em_dashes"]["enable_contextual_mode"] = contextual
            self.save_config()

    def get_categories(self) -> list:
        """Get list of all available categories."""
        return list(self.config["character_replacements"].keys())

    def get_config_path(self) -> str:
        """Get the path to the configuration file."""
        return str(self.config_file)

    def set_general_setting(self, setting: str, value: bool) -> None:
        """Set a general setting value."""
        if setting in self.config["general"]:
            self.config["general"][setting] = value
            self.save_config()

    def get_general_setting(self, setting: str) -> bool:
        """Get a general setting value."""
        return bool(self.config["general"].get(setting, False))

    def get_general_settings(self) -> Dict[str, bool]:
        """Get all general settings."""
        return {key: bool(value) for key, value in self.config["general"].items()}

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values and save to file."""
        self.config = self._load_default_config()
        self.save_config()

    def get_sub_settings(self, category: str) -> List[Tuple[str, str, bool]]:
        """
        Get sub-settings for a category.
        Returns list of (setting_key, display_name, current_value) tuples.
        """
        if category == "em_dashes":
            return [
                ("enable_contextual_mode", "Contextual/NLP mode for Em Dashes", self.is_em_dash_contextual())
            ]
        return []

    def set_sub_setting(self, category: str, setting: str, value: bool) -> None:
        """Set a sub-setting for a category."""
        if category == "em_dashes" and setting == "enable_contextual_mode":
            self.set_em_dash_contextual(value)
        # Add more sub-settings here as needed
