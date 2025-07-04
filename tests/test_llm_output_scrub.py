#!/usr/bin/env python3
"""
Comprehensive tests for LLM Output Scrub functionality.
"""

import os
import sys
import unittest
import tempfile
import json
import shutil
from typing import TYPE_CHECKING

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
            "dashes",
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

    def test_dashes_category_exists(self) -> None:
        """Test that dashes category exists and is enabled by default."""
        self.assertIn("dashes", self.config.config["character_replacements"])
        self.assertTrue(self.config.is_category_enabled("dashes"))
        # EN dash uses simple replacement, EM dash uses context-aware logic
        self.assertIn("–", self.config.config["character_replacements"]["dashes"]["replacements"])

    def test_get_all_replacements(self) -> None:
        """Test getting all enabled replacements."""
        replacements = self.config.get_all_replacements()
        self.assertIsInstance(replacements, dict)
        self.assertIn("\u201c", replacements)  # Left double quote
        self.assertIn("\u201d", replacements)  # Right double quote
        self.assertIn("–", replacements)  # EN dash
        self.assertIn("…", replacements)  # Ellipsis
        # EM dashes use context-aware replacement, not simple config replacement
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
        self.assertIn("dashes", categories)

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
        self.assertTrue(config.is_category_enabled("dashes"))

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
        self.assertTrue(config.is_category_enabled("dashes"))

    def test_category_validation(self) -> None:
        """Test validation of category names and operations."""
        # Test with non-existent category (should return True as default)
        self.assertTrue(self.config.is_category_enabled("non_existent_category"))

        # Test setting non-existent category (should not crash)
        self.config.set_category_enabled("non_existent_category", True)

        # Test with empty category name (should return True as default)
        self.assertTrue(self.config.is_category_enabled(""))

        # Test with None category name (should return True as default)
        self.assertTrue(self.config.is_category_enabled(None))  # type: ignore


class TestLLMOutputScrub(unittest.TestCase):
    """Test cases for LLMOutputScrub class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        if LLMOutputScrub is None:
            self.skipTest("LLMOutputScrub module not available")

        # Create temporary config for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.scrubber = LLMOutputScrub()
        self.scrubber.config = ScrubConfig(self.config_file)

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
            ("He stopped—what was that?", "He stopped... what was that?"),
            ("The cat—a fluffy Persian—was sleeping.", "The cat, a fluffy Persian, was sleeping."),
            # Range usage
            ("The range is 1—5.", "The range is 1-5."),
            ("The A—Z guide.", "The A-Z guide."),
            ("The years 2020—2023 were challenging.", "The years 2020-2023 were challenging."),
            # Abrupt break
            ("I was going to—never mind.", "I was going to... never mind."),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_em_dash_disabled(self) -> None:
        """Test that EM dashes are not replaced when dashes category is disabled."""
        self.scrubber.config.set_category_enabled("dashes", False)

        test_text = "The weather—it was terrible—ruined our picnic."
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, test_text)  # Should remain unchanged

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
        self.scrubber.config.set_category_enabled("mathematical", True)

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
        self.scrubber.config.set_category_enabled("currency", True)

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
        self.scrubber.config.set_category_enabled("fractions", True)

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
        self.scrubber.config.set_category_enabled("trademarks", True)

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
        self.scrubber.config.set_category_enabled("angle_quotes", True)

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
        self.scrubber.config.set_category_enabled("footnotes", True)

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
        self.scrubber.config.set_category_enabled("units", True)

        test_cases = [
            ("5 × 3", "5 * 3"),
            ("10 ÷ 2", "10 / 2"),
            ("5‰", "5per thousand"),
            ("1‱", "1per ten thousand"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_unicode_normalization(self) -> None:
        """Test Unicode normalization."""
        # Enable remove_combining_chars for this test
        self.scrubber.config.config["general"]["remove_combining_chars"] = True

        # Test with combining characters
        test_text = "e\u0301"  # e + combining acute accent
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, "e")  # Should normalize to 'é' then remove accent

    def test_whitespace_normalization(self) -> None:
        """Test whitespace normalization."""
        test_cases = [
            ("  multiple   spaces  ", "multiple spaces"),
            ("\t\ttabs\t\t", "tabs"),
            ("\n\nnewlines\n\n", "newlines"),
            ("\u00A0non-breaking\u00A0space\u00A0", "non-breaking space"),  # Non-breaking space
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_remove_non_ascii(self) -> None:
        """Test removal of non-ASCII characters."""
        # Enable remove_non_ascii
        self.scrubber.config.config["general"]["remove_non_ascii"] = True

        test_text = "Hello 世界"  # Contains Chinese characters
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, "Hello")  # Chinese characters should be removed

    def test_remove_combining_chars(self) -> None:
        """Test removal of combining characters."""
        # Enable remove_combining_chars
        self.scrubber.config.config["general"]["remove_combining_chars"] = True

        test_text = "e\u0301"  # e + combining acute accent
        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, "e")  # Combining character should be removed

    def test_complex_text_scrubbing(self) -> None:
        """Test scrubbing of complex text with multiple character types."""
        # Enable all categories for comprehensive testing
        for category in self.scrubber.config.get_categories():
            self.scrubber.config.set_category_enabled(category, True)

        test_text = "The price is €50—or £30™. It's 5 ≤ 10 and ½ cup of 5 × 3 = 15‰. Text†‡"
        expected = (
            "The price is EUR50 - or GBP30(TM). It's 5 <= 10 and 1/2 cup of 5 * 3 = 15per thousand. Text***"
        )

        result = self.scrubber.scrub_text(test_text)
        self.assertEqual(result, expected)

    def test_empty_and_whitespace_only_text(self) -> None:
        """Test handling of empty and whitespace-only text."""
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
        self.scrubber.config.set_category_enabled("dashes", True)
        self.scrubber.config.set_category_enabled("trademarks", True)
        self.scrubber.config.set_category_enabled("mathematical", True)

        result = self.scrubber.scrub_text(test_text)
        # Should handle the replacements but keep the Chinese characters
        self.assertIn("Hello", result)
        self.assertIn("世界", result)
        self.assertIn("this is a test(TM)", result)
        self.assertIn("5 <= 10", result)

    def test_enhanced_em_dash_nlp_contexts(self) -> None:
        """Test the enhanced NLP-based EM dash replacement with various contexts."""
        # Enable dashes category
        self.scrubber.config.set_category_enabled("dashes", True)

        test_cases = [
            # 1. MATHEMATICAL AND TECHNICAL CONTEXTS
            ("The function f(x) = 2x—3 is linear", "The function f(x) = 2x - 3 is linear"),
            ("Variable x—y represents the difference", "Variable x - y represents the difference"),
            ("Algorithm A—B processes the data", "Algorithm A - B processes the data"),
            # 2. ENHANCED RANGE DETECTION
            ("Pages 1—10 contain the introduction", "Pages 1-10 contain the introduction"),
            ("Years 2020—2023 were challenging", "Years 2020-2023 were challenging"),
            ("Version 2.1—3.0 includes new features", "Version 2.1-3.0 includes new features"),
            ("Date range 01/01—12/31 covers the year", "Date range 01/01 - 12/31 covers the year"),
            # 3. DIALOGUE AND ATTRIBUTION (should now replace EM dash)
            ('"Hello"—John said', '"Hello", John said'),
            ("'How are you?'—she asked", "'How are you?', she asked"),
            ("The answer—Mary replied", "The answer, Mary replied"),
            # 4. SENTENCE BOUNDARY AND INTERRUPTION
            ("I was going to—never mind", "I was going to... never mind"),
            ("The weather—well, it's complicated", "The weather - well, it's complicated"),
            ("He stopped—what was that?", "He stopped... what was that?"),
            ("Suddenly—everything changed", "Suddenly... everything changed"),
            # 5. PARENTHETICAL AND APPOSITIVE
            ("The cat—a fluffy Persian—was sleeping.", "The cat, a fluffy Persian, was sleeping."),
            ("My friend—John Smith—arrived", "My friend, John Smith, arrived."),
            (
                "The solution—that is, the correct approach—is simple",
                "The solution, that is, the correct approach, is simple",
            ),
            # 6. EMPHASIS AND FOCUS (should now replace EM dash)
            ("The result—amazingly—was perfect", "The result, amazingly, was perfect"),
            ("Finally—at last—we succeeded", "Finally, at last, we succeeded"),
            ("The truth—however painful—must be told", "The truth, however painful, must be told"),
            # 7. LIST AND ENUMERATION
            ("1—First item", "1 - First item"),
            ("2—Second item", "2 - Second item"),
            ("•—Bullet point", "• - Bullet point"),
            # 8. COMPOUND WORDS AND HYPHENATION
            ("self—driving car", "self-driving car"),
            ("pre—existing condition", "pre-existing condition"),
            ("user—friendly interface", "user-friendly interface"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_dialogue_context_preservation(self) -> None:
        """Test that dialogue contexts replace EM dashes (no longer preserve)."""
        self.scrubber.config.set_category_enabled("dashes", True)

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
        self.scrubber.config.set_category_enabled("dashes", True)

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

    def test_complex_nlp_scenarios(self) -> None:
        """Test complex scenarios that combine multiple NLP contexts."""
        self.scrubber.config.set_category_enabled("dashes", True)

        test_cases = [
            # Complex mathematical with dialogue
            (
                "The equation f(x)—g(x) = 0—'solved it!'—John exclaimed",
                "The equation f(x) - g(x) = 0 - 'solved it!' - John exclaimed",
            ),
            # Range with parenthetical
            (
                "Pages 1—10—the introduction—contain the basics",
                "Pages 1-10, the introduction, contain the basics",
            ),
            # Interruption with emphasis
            ("I was going to—well, actually—never mind", "I was going to... well, actually... never mind"),
            # List with compound words
            ("1—self—driving cars", "1: self-driving cars"),
            ("2—user—friendly interfaces", "2: user-friendly interfaces"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_em_dash_edge_cases(self) -> None:
        """Test edge cases for EM dash replacement."""
        test_cases = [
            # Multiple EM dashes in sequence
            ("Word—word—word", "Word, word, word"),
            # EM dash at start of text
            ("—Start of sentence", "- Start of sentence"),
            # EM dash at end of text
            ("End of sentence—", "End of sentence. "),
            # EM dash with multiple spaces
            ("Word—  word", "Word, word"),
            # EM dash with tabs/newlines
            ("Word—\tword", "Word, word"),
            # Very long interruption phrases
            ("I was going to—never mind about that thing", "I was going to... never mind about that thing"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_large_text_processing(self) -> None:
        """Test processing of large text to ensure performance and correctness."""
        # Create large text with many special characters
        large_text = "Hello " + "—" * 1000 + " World " + "…" * 500 + " Test"
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
                self.scrubber.config.config["general"]["remove_combining_chars"] = True
                result = self.scrubber.scrub_text(input_text)
                self.assertEqual(result, expected)

    def test_whitespace_normalization_edge_cases(self) -> None:
        """Test edge cases for whitespace normalization."""
        test_cases = [
            (
                "\u00A0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A",
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
        """Assert that EM dashes are never preserved in any context when dashes category is enabled."""
        self.scrubber.config.set_category_enabled("dashes", True)
        test_cases = [
            '"Hello"—John said',
            "The result—amazingly—was perfect",
            "The cat—a fluffy Persian—was sleeping.",
            "The range is 1—5.",
            "I was going to—never mind.",
            "Suddenly—everything changed",
            "self—driving car",
            "The solution—that is, the correct approach—is simple",
            "The weather—it was terrible—ruined our picnic.",
        ]
        for input_text in test_cases:
            with self.subTest(input_text=input_text):
                result = self.scrubber.scrub_text(input_text)
                self.assertNotIn("—", result, f"EM dash was preserved in: {result}")


if __name__ == "__main__":
    unittest.main()
