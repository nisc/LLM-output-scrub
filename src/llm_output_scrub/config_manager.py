#!/usr/bin/env python3
"""
Configuration for LLM Output Scrub character replacements.
"""

import copy
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
                    "display_name": 'Smart Quotes ("" → "")',
                    "replacements": {
                        "\u201c": '"',
                        "\u201d": '"',
                        "\u2018": "'",
                        "\u2019": "'",
                    },
                },
                "em_dashes": {
                    "enabled": True,
                    "display_name": "Em Dashes (— → -)",
                    "enable_contextual_mode": True,  # Enable contextual mode (spaCy NLP)
                    "replacements": {  # Ignored in contextual mode
                        "—": "-",
                    },
                    "sub_settings": {
                        "enable_contextual_mode": {
                            "display_name": "Em Dashes — Contextual/NLP mode",
                        }
                    },
                },
                "en_dashes": {
                    "enabled": True,
                    "display_name": "En Dashes (– → -)",
                    "replacements": {
                        "–": "-",
                    },
                },
                "ellipsis": {
                    "enabled": True,
                    "display_name": "Ellipsis (… → ...)",
                    "replacements": {
                        "…": "...",
                    },
                },
                "angle_quotes": {
                    "enabled": False,
                    "display_name": "Angle Quotes («» → <<>>)",
                    "replacements": {
                        "‹": "<",
                        "›": ">",
                        "«": "<<",
                        "»": ">>",
                    },
                },
                "trademarks": {
                    "enabled": False,
                    "display_name": "Trademarks (™® → (TM)(R))",
                    "replacements": {
                        "™": "(TM)",
                        "®": "(R)",
                    },
                },
                "mathematical": {
                    "enabled": False,
                    "display_name": "Mathematical (≤≥ → <=>=)",
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
                    "display_name": "Fractions (½ → 1/2)",
                    "replacements": {
                        "¼": "1/4",
                        "½": "1/2",
                        "¾": "3/4",
                    },
                },
                "footnotes": {
                    "enabled": False,
                    "display_name": "Footnotes (†‡ → **)",
                    "replacements": {
                        "†": "*",
                        "‡": "**",
                    },
                },
                "units": {
                    "enabled": False,
                    "display_name": "Units (×÷ → */)",
                    "replacements": {
                        "×": "*",
                        "÷": "/",
                        "‰": " per thousand",
                        "‱": " per ten thousand",
                    },
                },
                "currency": {
                    "enabled": False,
                    "display_name": "Currency (€£¥ → EUR/GBP/JPY)",
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
            # Create a clean copy without display names for saving
            config_to_save = self._create_clean_config_for_saving()
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def _create_clean_config_for_saving(self) -> Dict[str, Any]:
        """Create a clean config copy without display names for saving."""
        clean_config = copy.deepcopy(self.config)

        # Remove display names from character replacements
        for category_config in clean_config["character_replacements"].values():
            category_config.pop("display_name", None)
            if "sub_settings" in category_config:
                for sub_setting_config in category_config["sub_settings"].values():
                    sub_setting_config.pop("display_name", None)

        return clean_config

    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> None:
        """Recursively merge loaded config with defaults."""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value

    def _get_default_value(self, category: str, setting: str) -> bool:
        """Get the default value for a setting from the default config."""
        default_config = self._load_default_config()
        return bool(default_config["character_replacements"].get(category, {}).get(setting, False))

    def get_all_replacements(self) -> Dict[str, str]:
        """Get all enabled character replacements as a flat dictionary."""
        replacements = {}

        for category_name, category in self.config["character_replacements"].items():
            default_enabled = self._get_default_value(category_name, "enabled")
            if category.get("enabled", default_enabled):
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
        default_enabled = self._get_default_value(category, "enabled")
        value = self.config["character_replacements"].get(category, {}).get("enabled", default_enabled)
        return bool(value)

    def is_em_dash_enabled(self) -> bool:
        """Check if EM dash replacement is enabled."""
        return self.is_category_enabled("em_dashes")

    def is_em_dash_contextual(self) -> bool:
        """Check if EM dash replacement should use contextual NLP processing."""
        if not self.is_em_dash_enabled():
            return False
        default_contextual = self._get_default_value("em_dashes", "enable_contextual_mode")
        return bool(
            self.config["character_replacements"]
            .get("em_dashes", {})
            .get("enable_contextual_mode", default_contextual)
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

    def get_category_display_name(self, category: str) -> str:
        """Get the display name for a category."""
        # Get from default config to avoid persisting display names to user config
        default_config = self._load_default_config()
        category_config = default_config["character_replacements"].get(category, {})
        return str(category_config.get("display_name", category.replace("_", " ").title()))

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
        # Get sub-settings from default config to avoid persisting display names to user config
        default_config = self._load_default_config()
        category_config = default_config["character_replacements"].get(category, {})
        sub_settings = category_config.get("sub_settings", {})

        result = []
        for setting_key, setting_info in sub_settings.items():
            display_name = setting_info.get("display_name", setting_key.replace("_", " ").title())
            current_value = self._get_sub_setting_value(category, setting_key)
            result.append((setting_key, display_name, current_value))

        return result

    def _get_sub_setting_value(self, category: str, setting: str) -> bool:
        """Get the current value of a sub-setting."""
        # Get the value from the actual config
        return bool(self.config["character_replacements"].get(category, {}).get(setting, False))

    def set_sub_setting(self, category: str, setting: str, value: bool) -> None:
        """Set a sub-setting for a category."""
        # Set the value in the actual config
        if category in self.config["character_replacements"]:
            self.config["character_replacements"][category][setting] = value
            self.save_config()
