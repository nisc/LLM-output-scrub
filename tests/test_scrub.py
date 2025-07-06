#!/usr/bin/env python3
"""
Comprehensive tests for LLM Output Scrub functionality.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from typing import TYPE_CHECKING, List, Tuple, cast

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if TYPE_CHECKING:
    from llm_output_scrub import LLMOutputScrub
    from llm_output_scrub.config_manager import ScrubConfig
else:
    LLMOutputScrub = None  # pylint: disable=invalid-name
    ScrubConfig = None  # pylint: disable=invalid-name

try:
    from llm_output_scrub import LLMOutputScrub
    from llm_output_scrub.config_manager import ScrubConfig
except ImportError:
    pass


class TestScrubConfig(unittest.TestCase):
    """Test cases for ScrubConfig class."""

    config: "ScrubConfig"

    def setUp(self) -> None:
        """Set up test fixtures."""
        if ScrubConfig is None:
            self.skipTest("ScrubConfig module not available")

        # Create a temporary config file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.config = ScrubConfig(self.config_file)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_config_structure(self) -> None:
        """Test that default config has expected structure."""
        self.assertIn("character_replacements", self.config.config)
        self.assertIn("general", self.config.config)

        # Check that all expected categories exist
        expected_categories = [
            "smart_quotes",
            "em_dashes",
            "en_dashes",
            "ellipsis",
            "angle_quotes",
            "trademarks",
            "mathematical",
            "fractions",
            "footnotes",
            "units",
            "currency",
        ]
        for category in expected_categories:
            self.assertIn(category, self.config.config["character_replacements"])

    def test_en_dashes_category_exists(self) -> None:
        """Test that en_dashes category exists and is enabled by default."""
        self.assertIn("en_dashes", self.config.config["character_replacements"])
        self.assertTrue(self.config.is_category_enabled("en_dashes"))
        # EN dash uses simple replacement
        self.assertIn("–", self.config.config["character_replacements"]["en_dashes"]["replacements"])

    def test_em_dashes_category_exists(self) -> None:
        """Test that em_dashes category exists and is enabled by default."""
        self.assertIn("em_dashes", self.config.config["character_replacements"])
        self.assertTrue(self.config.is_category_enabled("em_dashes"))
        self.assertTrue(self.config.is_em_dash_contextual())  # Should be contextual by default

    def test_get_all_replacements(self) -> None:
        """Test getting all enabled replacements."""
        replacements = self.config.get_all_replacements()
        self.assertIsInstance(replacements, dict)
        self.assertIn("\u201c", replacements)  # Left double quote
        self.assertIn("\u201d", replacements)  # Right double quote
        self.assertIn("–", replacements)  # EN dash
        self.assertIn("…", replacements)  # Ellipsis
        # EM dashes are in replacements when contextual mode is off, but handled specially when on
        # This test checks the default state (contextual mode on), so EM dash should not be in simple
        # replacements
        self.assertNotIn("—", replacements)  # EM dash

    def test_set_category_enabled(self) -> None:
        """Test enabling and disabling categories."""
        # Disable smart_quotes
        self.config.set_category_enabled("smart_quotes", False)
        self.assertFalse(self.config.is_category_enabled("smart_quotes"))

        # Re-enable smart_quotes
        self.config.set_category_enabled("smart_quotes", True)
        self.assertTrue(self.config.is_category_enabled("smart_quotes"))

    def test_get_categories(self) -> None:
        """Test getting list of all categories."""
        categories = self.config.get_categories()
        self.assertIsInstance(categories, list)
        self.assertIn("smart_quotes", categories)
        self.assertIn("en_dashes", categories)
        self.assertIn("em_dashes", categories)

    def test_config_persistence(self) -> None:
        """Test that config changes are saved to file."""
        # Modify config
        self.config.set_category_enabled("smart_quotes", False)

        # Create new config instance with same file
        new_config = ScrubConfig(self.config_file)

        # Check that change persisted
        self.assertFalse(new_config.is_category_enabled("smart_quotes"))

    def test_config_merge(self) -> None:
        """Test that partial config files merge correctly with defaults."""
        # Create partial config file
        partial_config = {"character_replacements": {"smart_quotes": {"enabled": False}}}

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(partial_config, f)

        # Load config
        config = ScrubConfig(self.config_file)

        # Check that smart_quotes is disabled but other defaults remain
        self.assertFalse(config.is_category_enabled("smart_quotes"))
        self.assertTrue(config.is_category_enabled("en_dashes"))

    def test_config_load_error_handling(self) -> None:
        """Test error handling when loading corrupted config files."""
        # Create a corrupted config file
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write('{"invalid": json}')

        # Should not raise exception, should use defaults
        config = ScrubConfig(self.config_file)
        self.assertTrue(config.is_category_enabled("smart_quotes"))  # Should use defaults

    def test_config_save_error_handling(self) -> None:
        """Test error handling when saving to read-only location."""
        # Create config with read-only file
        config = ScrubConfig(self.config_file)

        # Make file read-only (this might not work on all systems, but worth testing)
        try:
            os.chmod(self.config_file, 0o444)  # Read-only
            # This should not raise an exception, just print error
            config.set_category_enabled("smart_quotes", False)
        except PermissionError:
            # Expected on some systems
            pass
        finally:
            # Restore permissions
            try:
                os.chmod(self.config_file, 0o644)
            except PermissionError:
                pass

    def test_config_merge_edge_cases(self) -> None:
        """Test edge cases for config merging."""
        # Test with deeply nested config
        deep_config = {
            "character_replacements": {
                "smart_quotes": {"enabled": False, "replacements": {"\u201c": "CUSTOM_QUOTE"}}
            }
        }

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(deep_config, f)

        config = ScrubConfig(self.config_file)

        # Should merge correctly
        self.assertFalse(config.is_category_enabled("smart_quotes"))
        # Other categories should still have defaults
        self.assertTrue(config.is_category_enabled("en_dashes"))

    def test_category_validation(self) -> None:
        """Test validation of category names and operations."""
        # Test with non-existent category (should return False as default)
        self.assertFalse(self.config.is_category_enabled("non_existent_category"))

        # Test setting non-existent category (should not crash)
        self.config.set_category_enabled("non_existent_category", True)

        # Test with empty category name (should return False as default)
        self.assertFalse(self.config.is_category_enabled(""))

        # Test with None category name (should return False as default)
        self.assertFalse(self.config.is_category_enabled(None))  # type: ignore

    def test_debug_mode_setting(self) -> None:
        """Test that debug_mode setting works correctly."""
        # Debug mode should be False by default
        self.assertFalse(self.config.get_general_setting("debug_mode"))

        # Enable debug mode
        self.config.set_general_setting("debug_mode", True)
        self.assertTrue(self.config.get_general_setting("debug_mode"))

        # Disable debug mode
        self.config.set_general_setting("debug_mode", False)
        self.assertFalse(self.config.get_general_setting("debug_mode"))

        # Test persistence
        self.config.set_general_setting("debug_mode", True)
        new_config = ScrubConfig(self.config_file)
        self.assertTrue(new_config.get_general_setting("debug_mode"))

    def test_get_menu_items(self) -> None:
        """Test that get_menu_items returns correct menu items based on debug mode."""
        # Debug mode off by default
        menu_items = self.config.get_menu_items()
        self.assertEqual(menu_items, ["Scrub Clipboard", "Configuration"])

        # Enable debug mode
        self.config.set_general_setting("debug_mode", True)
        menu_items = self.config.get_menu_items()
        self.assertEqual(menu_items, ["Scrub Clipboard", "Configuration", "NLP Stats"])

        # Disable debug mode
        self.config.set_general_setting("debug_mode", False)
        menu_items = self.config.get_menu_items()
        self.assertEqual(menu_items, ["Scrub Clipboard", "Configuration"])


class TestLLMOutputScrub(unittest.TestCase):
    """Test cases for LLMOutputScrub class."""

    scrubber: "LLMOutputScrub"

    def setUp(self) -> None:
        """Set up test fixtures."""
        if LLMOutputScrub is None:
            self.skipTest("LLMOutputScrub module not available")

        # Create temporary config for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.scrubber = LLMOutputScrub()
        self.scrubber.config = cast(  # type: ignore[redundant-cast]
            ScrubConfig, ScrubConfig(self.config_file)
        )

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_smart_quotes_replacement(self) -> None:
        """Test smart quotes replacement."""
        test_cases = [
            ("\u201cHello\u201d", '"Hello"'),
            ("\u2018World\u2019", "'World'"),
            ("\u201cHello\u201d and \u2018World\u2019", "\"Hello\" and 'World'"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_dashes_replacement(self) -> None:
        """Test dashes replacement (EN dash simple, EM dash context-aware)."""
        test_cases = [
            ("1–5", "1-5"),  # EN dash
            ("A–Z", "A-Z"),  # EN dash
            ("2020–2023", "2020-2023"),  # EN dash
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_em_dash_context_aware_replacement(self) -> None:
        """Test EM dash replacement with context awareness within dashes category."""
        test_cases = [
            # Parenthetical usage
            (
                "The weather—it was terrible—ruined our picnic.",
                "The weather, it was terrible, ruined our picnic.",
            ),
            ("The cat—a fluffy Persian—was sleeping.", "The cat, a fluffy Persian, was sleeping."),
            # Default usage (these use default replacement)
            ("The range is 1—5.", "The range is 1-5."),
            ("The A—Z guide.", "The A-Z guide."),
            ("The years 2020—2023 were challenging.", "The years 2020-2023 were challenging."),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_em_dash_context_aware_replacement_hard_cases(self) -> None:
        """Hard/ambiguous cases for EM dash context-aware replacement."""
        test_cases: List[Tuple[str, str]] = []
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_em_dash_disabled(self) -> None:
        """Test that EM dashes are not replaced when em_dashes category is disabled."""
        cast(ScrubConfig, self.scrubber.config).set_em_dash_enabled(False)  # type: ignore[redundant-cast]

        test_text = "The weather—it was terrible—ruined our picnic."
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, test_text)  # Should remain unchanged

    def test_em_dash_dumb_replacement(self) -> None:
        """Test that EM dashes use simple replacement when contextual mode is disabled."""
        cast(ScrubConfig, self.scrubber.config).set_em_dash_enabled(True)  # type: ignore[redundant-cast]
        cast(ScrubConfig, self.scrubber.config).set_em_dash_contextual(False)  # type: ignore[redundant-cast]

        test_cases = [
            (
                "The weather—it was terrible—ruined our picnic.",
                "The weather-it was terrible-ruined our picnic.",
            ),
            ("The cat—a fluffy Persian—was sleeping.", "The cat-a fluffy Persian-was sleeping."),
            ("The range is 1—5.", "The range is 1-5."),
            ("self—driving car", "self-driving car"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_ellipsis_replacement(self) -> None:
        """Test ellipsis replacement."""
        test_cases = [
            ("This is an ellipsis…", "This is an ellipsis..."),
            ("Wait… what?", "Wait... what?"),
            ("The story continues…", "The story continues..."),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_mathematical_symbols_replacement(self) -> None:
        """Test mathematical symbols replacement."""
        # Enable mathematical category
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "mathematical", True
        )  # type: ignore[redundant-cast]

        test_cases = [
            ("5 ≤ 10", "5 <= 10"),
            ("15 ≥ 5", "15 >= 5"),
            ("3 ≠ 4", "3 != 4"),
            ("5 ≈ 5", "5 ~ 5"),
            ("10 ± 2", "10 +/- 2"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_currency_replacement(self) -> None:
        """Test currency symbols replacement."""
        # Enable currency category
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "currency", True
        )  # type: ignore[redundant-cast]

        test_cases = [
            ("€50", "EUR50"),
            ("£30", "GBP30"),
            ("¥1000", "JPY1000"),
            ("¢25", "cents25"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_fractions_replacement(self) -> None:
        """Test fractions replacement."""
        # Enable fractions category
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "fractions", True
        )  # type: ignore[redundant-cast]

        test_cases = [
            ("¼ cup", "1/4 cup"),
            ("½ pound", "1/2 pound"),
            ("¾ inch", "3/4 inch"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_trademarks_replacement(self) -> None:
        """Test trademark symbols replacement."""
        # Enable trademarks category
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "trademarks", True
        )  # type: ignore[redundant-cast]

        test_cases = [
            ("Apple™", "Apple(TM)"),
            ("Microsoft®", "Microsoft(R)"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_angle_quotes_replacement(self) -> None:
        """Test angle quotes replacement."""
        # Enable angle_quotes category
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "angle_quotes", True
        )  # type: ignore[redundant-cast]

        test_cases = [
            ("‹text›", "<text>"),
            ("«text»", "<<text>>"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_footnotes_replacement(self) -> None:
        """Test footnote symbols replacement."""
        # Enable footnotes category
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "footnotes", True
        )  # type: ignore[redundant-cast]

        test_cases = [
            ("Text†", "Text*"),
            ("Text‡", "Text**"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_units_replacement(self) -> None:
        """Test units symbols replacement."""
        # Enable units category
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "units", True
        )  # type: ignore[redundant-cast]

        test_cases = [
            ("5 × 3", "5 * 3"),
            ("10 ÷ 2", "10 / 2"),
            ("5‰", "5 per thousand"),
            ("1‱", "1 per ten thousand"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_unicode_normalization(self) -> None:
        """Test Unicode normalization."""
        # Enable remove_combining_chars for this test
        cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
            "remove_combining_chars"
        ] = True

        # Test with combining characters
        test_text = "e\u0301"  # e + combining acute accent
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, "e")  # Should normalize to 'é' then remove accent

    def test_whitespace_normalization(self) -> None:
        """Test whitespace normalization."""
        # Enable normalize_whitespace
        cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
            "normalize_whitespace"
        ] = True
        test_cases = [
            ("  multiple   spaces  ", "multiple spaces"),
            ("\t\ttabs\t\t", "tabs"),
            ("\n\nnewlines\n\n", "newlines"),
            ("\u00a0non-breaking\u00a0space\u00a0", "non-breaking space"),  # Non-breaking space
            ("a\n\n\n\nb", "a\n\nb"),  # Multiple empty lines → single empty line
            ("a\n\n\n\n\n\nb", "a\n\nb"),  # Multiple empty lines → single empty line
            ("a\n\n\n\nb\n\n\nc", "a\n\nb\n\nc"),  # Multiple empty lines → single empty lines
            ("a\n\n\n\n\n\n\nb\n\n\nc\n\n\n", "a\n\nb\n\nc"),  # Multiple empty lines → single empty lines
            ("\n\n\n\n", ""),  # All empty lines → empty string
            ("a\n\n\n\n", "a"),  # Empty lines at end → removed
            ("\n\n\n\na", "a"),  # Empty lines at start → removed
            ("a\n\n\n\n\n\n", "a"),  # Empty lines at end → removed
            ("\n\n\n\na\n\n\n\n", "a"),  # Empty lines at start/end → removed
            ("a\n\n\n\nb\n\n\n\nc\n\n\n\n", "a\n\nb\n\nc"),  # Multiple empty lines → single empty lines
        ]
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_whitespace_normalization_conversation_example(self) -> None:
        """Test whitespace normalization with a realistic conversation example."""
        # Enable normalize_whitespace
        cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
            "normalize_whitespace"
        ] = True

        input_text = """This is a test of whitespace normalization.

Multiple    spaces    should    be    normalized    to    single    spaces.

Tabs		should		also		be		normalized.

Multiple empty lines should be preserved but excessive ones trimmed:


This line should have one empty line above it.

This line should also have one empty line above it.


And this line should have one empty line above it too.

The end."""

        result = self.scrubber.scrub_text(input_text)

        # Check that empty lines are preserved (not all stripped)
        empty_line_count = result.count("\n\n")
        self.assertGreater(empty_line_count, 0, "Empty lines should be preserved")

        # Check that multiple consecutive empty lines are trimmed to single empty lines
        # Should not have more than 2 consecutive newlines anywhere
        self.assertNotIn("\n\n\n", result, "Multiple consecutive empty lines should be trimmed")

        # Check that whitespace within lines is normalized
        lines = result.split("\n")
        for line in lines:
            if line.strip():  # Non-empty lines
                # Should not have multiple consecutive spaces
                self.assertNotIn("  ", line, "Multiple spaces should be normalized to single spaces")

        # Check that the structure is preserved
        self.assertIn("This is a test", result, "Content should be preserved")
        self.assertIn("The end", result, "End content should be preserved")

    def test_remove_non_ascii(self) -> None:
        """Test removal of non-ASCII characters."""
        # Enable remove_non_ascii
        cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
            "remove_non_ascii"
        ] = True

        test_text = "Hello 世界"  # Contains Chinese characters
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, "Hello ")  # Chinese characters should be removed, space preserved

    def test_remove_combining_chars(self) -> None:
        """Test removal of combining characters."""
        # Enable remove_combining_chars
        cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
            "remove_combining_chars"
        ] = True

        test_text = "e\u0301"  # e + combining acute accent
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, "e")  # Combining character should be removed

    def test_complex_text_scrubbing(self) -> None:
        """Test scrubbing of complex text with multiple character types."""
        # Enable all categories for comprehensive testing
        for category in cast(
            ScrubConfig, self.scrubber.config
        ).get_categories():  # type: ignore[redundant-cast]
            cast(ScrubConfig, self.scrubber.config).set_category_enabled(
                category, True
            )  # type: ignore[redundant-cast]

        test_text = "The price is €50 and £30™. It's 5 ≤ 10 and ½ cup of 5 × 3 = 15‰. Text†‡"
        expected = (
            "The price is EUR50 and GBP30(TM). It's 5 <= 10 and 1/2 cup of 5 * 3 = 15 per thousand. Text***"
        )
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, expected)

    def test_complex_text_scrubbing_hard_cases(self) -> None:
        """Hard/ambiguous cases for complex text scrubbing."""
        for category in cast(
            ScrubConfig, self.scrubber.config
        ).get_categories():  # type: ignore[redundant-cast]
            cast(ScrubConfig, self.scrubber.config).set_category_enabled(
                category, True
            )  # type: ignore[redundant-cast]
        test_text = "The price is €50—or £30™. It's 5 ≤ 10 and ½ cup of 5 × 3 = 15‰. Text†‡"
        expected = (
            "The price is EUR50, or GBP30(TM). It's 5 <= 10 and 1/2 cup of 5 * 3 = 15 per thousand. Text***"
        )
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, expected)

    def test_empty_and_whitespace_only_text(self) -> None:
        """Test handling of empty and whitespace-only text."""
        # Enable normalize_whitespace
        cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
            "normalize_whitespace"
        ] = True

        test_cases = [
            ("", ""),
            ("   ", ""),
            ("\n\t", ""),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=repr(input_text)):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_no_replacements_needed(self) -> None:
        """Test text that doesn't need any replacements."""
        test_text = "This is plain ASCII text with no special characters."
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, test_text)

    def test_mixed_unicode_and_ascii(self) -> None:
        """Test text with mixed Unicode and ASCII characters."""
        test_text = "Hello 世界—this is a test™ with 5 ≤ 10"
        # Enable relevant categories
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "dashes", True
        )  # type: ignore[redundant-cast]
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "trademarks", True
        )  # type: ignore[redundant-cast]
        cast(ScrubConfig, self.scrubber.config).set_category_enabled(
            "mathematical", True
        )  # type: ignore[redundant-cast]

        result = self.scrubber.scrub_text(test_text)
        # Should handle the replacements but keep the Chinese characters
        self.assertIn("Hello", result)
        self.assertIn("世界", result)
        self.assertIn("this is a test(TM)", result)
        self.assertIn("5 <= 10", result)

    def test_enhanced_em_dash_nlp_contexts(self) -> None:
        """Test the enhanced spaCy-first NLP dash replacement with realistic 100-500 character contexts."""
        # Enable em_dashes category
        cast(ScrubConfig, self.scrubber.config).set_em_dash_enabled(True)  # type: ignore[redundant-cast]

        test_cases = [
            # 1. DEFAULT REPLACEMENT CONTEXTS (use simple hyphen)
            (
                "In advanced calculus, the function f(x) = 2x—3 represents a linear transformation that "
                "maps input values to output values in a predictable mathematical relationship.",
                "In advanced calculus, the function f(x) = 2x-3 represents a linear transformation that "
                "maps input values to output values in a predictable mathematical relationship.",
            ),
            (
                "The algorithm compares variables x—y to determine the mathematical difference between "
                "two data points, which is crucial for statistical analysis and machine learning models.",
                "The algorithm compares variables x-y to determine the mathematical difference between "
                "two data points, which is crucial for statistical analysis and machine learning models.",
            ),
            (
                "During the software engineering conference, we discussed the performance metrics comparing "
                "Algorithm A—B processing speeds when handling large datasets efficiently.",
                "During the software engineering conference, we discussed the performance metrics comparing "
                "Algorithm A-B processing speeds when handling large datasets efficiently.",
            ),
            (
                "The comprehensive research study covered Pages 15—87 of the technical manual, providing "
                "detailed analysis of the implementation strategies used in modern software development "
                "practices.",
                "The comprehensive research study covered Pages 15-87 of the technical manual, providing "
                "detailed analysis of the implementation strategies used in modern software development "
                "practices.",
            ),
            (
                "The economic analysis examined the challenging period from Years 2020—2023, during which "
                "global markets experienced unprecedented volatility due to various international "
                "factors.",
                "The economic analysis examined the challenging period from Years 2020-2023, during which "
                "global markets experienced unprecedented volatility due to various international "
                "factors.",
            ),
            (
                "The software update roadmap shows that Version 2.1—3.0 will include revolutionary new "
                "features that enhance user experience and improve system performance "
                "significantly.",
                "The software update roadmap shows that Version 2.1-3.0 will include revolutionary new "
                "features that enhance user experience and improve system performance "
                "significantly.",
            ),
            # 3. DIALOGUE AND ATTRIBUTION WITH CONTEXT (120-250 chars)
            (
                "After the lengthy presentation concluded, the distinguished professor looked at his "
                'students and said, "Your final assignment will be challenging"—Dr. Johnson explained '
                "with a warm smile.",
                "After the lengthy presentation concluded, the distinguished professor looked at his "
                'students and said, "Your final assignment will be challenging", Dr. Johnson explained '
                "with a warm smile.",
            ),
            (
                '"I believe we can solve this complex problem if we work together as a team," the project '
                "manager stated confidently—Sarah replied to the concerned stakeholders during the meeting.",
                '"I believe we can solve this complex problem if we work together as a team," the project '
                "manager stated confidently, Sarah replied to the concerned stakeholders during the meeting.",
            ),
            (
                'The detailed financial report revealed significant growth in the third quarter. "These '
                'numbers exceed our expectations," the CEO announced—Maria explained to the board of '
                "directors.",
                'The detailed financial report revealed significant growth in the third quarter. "These '
                'numbers exceed our expectations," the CEO announced, Maria explained to the board of '
                "directors.",
            ),
            # 5. PARENTHETICAL AND APPOSITIVE CONTEXTS (150-300 chars)
            (
                "The innovative startup company—founded by two brilliant MIT graduates who specialized in "
                "artificial intelligence—successfully launched their revolutionary product in the "
                "competitive tech market.",
                "The innovative startup company, founded by two brilliant MIT graduates who specialized in "
                "artificial intelligence, successfully launched their revolutionary product in the "
                "competitive tech market.",
            ),
            (
                "Our distinguished guest speaker—Dr. Elizabeth Chen, the renowned expert in quantum "
                "computing—will present her groundbreaking research findings at tomorrow's scientific "
                "symposium.",
                "Our distinguished guest speaker, Dr. Elizabeth Chen, the renowned expert in quantum "
                "computing, will present her groundbreaking research findings at tomorrow's scientific "
                "symposium.",
            ),
            (
                "The comprehensive solution to our technical challenges—that is, the approach that "
                "addresses both performance and security concerns—requires careful implementation and "
                "thorough testing procedures.",
                "The comprehensive solution to our technical challenges, that is, the approach that "
                "addresses both performance and security concerns, requires careful implementation and "
                "thorough testing procedures.",
            ),
            # 6. EMPHASIS AND FOCUS WITH CONTEXT (120-250 chars)
            (
                "The long-awaited experimental results were finally available after months of careful "
                "research and analysis—amazingly—the findings exceeded all our initial expectations and "
                "assumptions.",
                "The long-awaited experimental results were finally available after months of careful "
                "research and analysis, amazingly, the findings exceeded all our initial expectations and "
                "assumptions.",
            ),
            (
                "After years of struggling with the complex problem, the research team made a "
                "breakthrough discovery—incredibly—that completely revolutionized our understanding of "
                "the subject matter.",
                "After years of struggling with the complex problem, the research team made a "
                "breakthrough discovery, incredibly, that completely revolutionized our understanding of "
                "the subject matter.",
            ),
            (
                "The difficult negotiation process took several months to complete, but finally—at "
                "long last—all parties reached a mutually beneficial agreement that satisfied "
                "everyone's requirements.",
                "The difficult negotiation process took several months to complete, but finally, at "
                "long last, all parties reached a mutually beneficial agreement that satisfied "
                "everyone's requirements.",
            ),
            # 7. MORE DEFAULT REPLACEMENT CONTEXTS (compound words)
            (
                "The automotive industry is rapidly developing self—driving vehicles that utilize advanced "
                "artificial intelligence and sophisticated sensor technology for autonomous navigation.",
                "The automotive industry is rapidly developing self-driving vehicles that utilize advanced "
                "artificial intelligence and sophisticated sensor technology for autonomous navigation.",
            ),
            (
                "Modern software applications require user—friendly interfaces that provide intuitive "
                "navigation and accessibility features for diverse user populations and varying technical "
                "expertise levels.",
                "Modern software applications require user-friendly interfaces that provide intuitive "
                "navigation and accessibility features for diverse user populations and varying technical "
                "expertise levels.",
            ),
            (
                "The company implemented a pre—existing security framework that had been thoroughly tested "
                "and validated by cybersecurity experts in multiple enterprise environments.",
                "The company implemented a pre-existing security framework that had been thoroughly tested "
                "and validated by cybersecurity experts in multiple enterprise environments.",
            ),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_em_dash_edge_cases(self) -> None:
        """Test edge cases for EM dash replacement with realistic 100-500 character contexts."""
        test_cases = [
            # Multiple EM dashes in sequence with full context
            (
                "The research project involved multiple phases of development—design, implementation, "
                "testing—each requiring careful coordination and extensive documentation throughout the "
                "entire process.",
                "The research project involved multiple phases of development, design, implementation, "
                "testing, each requiring careful coordination and extensive documentation throughout the "
                "entire process.",
            ),
            # EM dash with spacing variations in professional context
            (
                "The quarterly business report highlighted several key performance indicators—  revenue "
                "growth, customer satisfaction, market expansion—that exceeded our initial projections "
                "significantly.",
                "The quarterly business report highlighted several key performance indicators, revenue "
                "growth, customer satisfaction, market expansion, that exceeded our initial projections "
                "significantly.",
            ),
            # EM dash with whitespace characters in technical documentation
            (
                "The software architecture diagram illustrates the complex relationships between different "
                "system components—\tuser interface, database layer, business logic—and their "
                "interconnections.",
                "The software architecture diagram illustrates the complex relationships between different "
                "system components, user interface, database layer, business logic, and their "
                "interconnections.",
            ),
        ]
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_large_text_processing(self) -> None:
        """Test processing of large text to ensure performance and correctness."""
        # Create large text with many special characters (optimized for reasonable test time)
        large_text = "Hello " + "—" * 50 + " World " + "…" * 50 + " Test"
        result = self.scrubber.scrub_text(large_text)

        # Should not crash and should process all characters
        self.assertIn("Hello", result)
        self.assertIn("World", result)
        self.assertIn("Test", result)
        # Should have processed EM dashes and ellipsis
        self.assertNotIn("—", result)
        self.assertNotIn("…", result)

    def test_unicode_normalization_edge_cases(self) -> None:
        """Test edge cases for Unicode normalization."""
        # Test with various combining characters
        test_cases = [
            ("e\u0301\u0302", "e"),  # Multiple combining characters
            ("a\u0300\u0301", "a"),  # Multiple accents
            ("o\u0308\u0301", "o"),  # Umlaut + acute
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                # Enable remove_combining_chars
                cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
                    "remove_combining_chars"
                ] = True
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_whitespace_normalization_edge_cases(self) -> None:
        """Test edge cases for whitespace normalization."""
        # Enable normalize_whitespace
        cast(ScrubConfig, self.scrubber.config).config["general"][  # type: ignore[redundant-cast]
            "normalize_whitespace"
        ] = True

        test_cases = [
            (
                "\u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a",
                "",
            ),  # Various Unicode spaces
            ("\t\n\r\f\v", ""),  # Various whitespace characters
            ("  \t\n  \r  \f  \v  ", ""),  # Mixed whitespace
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=repr(input_text)):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_em_dash_never_preserved_when_enabled(self) -> None:
        """Assert that EM dashes are never preserved in any context when em_dashes category is enabled."""
        cast(ScrubConfig, self.scrubber.config).set_em_dash_enabled(True)  # type: ignore[redundant-cast]
        test_cases = [
            '"Hello"—John said',
            "The result—amazingly—was perfect",
            "The cat—a fluffy Persian—was sleeping.",
            "The range is 1—5.",
            "Suddenly—everything changed",
            "self—driving car",
            "The solution—that is, the correct approach—is simple",
            "The weather—it was terrible—ruined our picnic.",
        ]
        for input_text in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertNotIn("—", result, f"EM dash was preserved in: {result}")

    def test_dialogue_context_preservation(self) -> None:
        """Test that dialogue contexts replace EM dashes (no longer preserve)."""
        cast(ScrubConfig, self.scrubber.config).set_em_dash_enabled(True)  # type: ignore[redundant-cast]

        test_cases = [
            ('"Hello"—John said', '"Hello", John said'),
            ("'How are you?'—she asked", "'How are you?', she asked"),
            ("The answer—Mary replied", "The answer, Mary replied"),
            ("'I don't know'—he mumbled", "'I don't know', he mumbled"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_emphasis_context_preservation(self) -> None:
        """Test that emphasis contexts replace EM dashes (no longer preserve)."""
        cast(ScrubConfig, self.scrubber.config).set_em_dash_enabled(True)  # type: ignore[redundant-cast]

        test_cases = [
            ("The result—amazingly—was perfect", "The result, amazingly, was perfect"),
            ("Finally—at last—we succeeded", "Finally, at last, we succeeded"),
            ("The truth—however painful—must be told", "The truth, however painful, must be told"),
            ("Suddenly—unexpectedly—everything changed", "Suddenly, unexpectedly, everything changed"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
