#!/usr/bin/env python3
"""
LLM Output Scrub - macOS app that replaces smart/typographic characters with plain ASCII.
Run directly: python3 app.py
Or build with: python3 setup.py py2app
"""

import sys
import threading
import unicodedata
from pathlib import Path
from typing import Any, List, Optional

import pyperclip
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from llm_output_scrub.config_manager import ScrubConfig  # pylint: disable=import-error
from llm_output_scrub.nlp import get_dash_replacement_nlp, get_nlp_processor  # pylint: disable=import-error

# macOS-specific imports for window management
try:
    import AppKit  # type: ignore

    NSApp = AppKit.NSApplication.sharedApplication()
except ImportError:
    NSApp = None

# Check if we're on macOS
if sys.platform != "darwin":
    raise ImportError("This app is designed for macOS only.")

try:
    import rumps  # pylint: disable=import-error
except ImportError as exc:
    raise ImportError(
        "rumps is required but not installed. Please install with: pip install -e .[macOS]"
    ) from exc


def bring_app_to_foreground() -> None:
    """Bring the app to the foreground to ensure dialogs are visible."""
    if NSApp is not None:
        try:
            NSApp.activate(True)
        except Exception:  # pylint: disable=broad-except
            pass  # Ignore any errors with window management


# If you get import errors, run with:
# python -m llm_output_scrub.app
# from the src/ directory, or set your PYTHONPATH accordingly.


class ConfigFileChangeHandler(FileSystemEventHandler):
    """Handler for config file change events."""

    def __init__(self, app: "LLMOutputScrub", config_path: Path) -> None:
        super().__init__()
        self.app = app
        self.config_path = config_path

    def on_modified(self, event: Any) -> None:
        """Handle file modification events."""
        if event.src_path == str(self.config_path):
            self.app.reload_config()


class LLMOutputScrub(rumps.App):
    """macOS menu bar app that scrubs smart/typographic characters from LLM output."""

    def __init__(self, config_file: Optional[str] = None) -> None:
        super().__init__("📝")
        self.menu = ["Scrub Clipboard", "Configure", "NLP Stats", "About"]
        self.config = ScrubConfig(config_file)
        self._observer: Optional[Any] = None
        self._start_config_watcher()

    def _start_config_watcher(self) -> None:
        """Start watching the config file for changes."""
        if self._observer is not None:
            return  # Already watching

        config_path = self.config.config_file
        event_handler = ConfigFileChangeHandler(self, config_path)
        observer = Observer()
        observer.schedule(event_handler, str(config_path.parent), recursive=False)
        observer_thread = threading.Thread(target=observer.start, daemon=True)
        observer_thread.start()
        self._observer = observer

    def reload_config(self) -> None:
        """Reload configuration from file."""
        self.config.load_config()
        rumps.notification(
            title="LLM Output Scrub", subtitle="Config Reloaded", message="Configuration reloaded from file."
        )

    @rumps.clicked("Scrub Clipboard")  # type: ignore[misc]
    def scrub_llm_output(self, _: Any) -> None:
        """Scrub the clipboard content by replacing smart quotes and other typographic characters."""
        try:
            # Get current clipboard content
            clipboard_text = pyperclip.paste()

            # Always convert to a true Python str (handles objc.pyobjc_unicode and subclasses)
            clipboard_text = str(clipboard_text)

            if not clipboard_text:
                rumps.notification(
                    title="LLM Output Scrub", subtitle="No content", message="Clipboard is empty"
                )  # fmt: off
                return

            # Scrub the text
            scrubbed_text = self.scrub_text(clipboard_text)

            # Put scrubbed text back to clipboard
            pyperclip.copy(scrubbed_text)

            # Check if any changes were made
            if scrubbed_text == clipboard_text:
                # No changes were made
                rumps.notification(
                    title="LLM Output Scrub",
                    subtitle="No changes needed",
                    message=f"Text was already clean ({len(clipboard_text)} characters)",
                )
            else:
                # Changes were made
                rumps.notification(
                    title="LLM Output Scrub",
                    subtitle="Success",
                    message=f"Scrubbed {len(clipboard_text)} characters",
                )

        except (pyperclip.PyperclipException, OSError) as e:
            rumps.notification(title="LLM Output Scrub", subtitle="Error", message=str(e))

    @rumps.clicked("Configure")  # type: ignore[misc]
    def configure(self, _: Any) -> None:
        """Show configuration dialog."""
        categories = self.config.get_categories()
        enabled_categories = [cat for cat in categories if self.config.is_category_enabled(cat)]
        disabled_categories = [cat for cat in categories if not self.config.is_category_enabled(cat)]

        message = f"Configuration file: {self.config.get_config_path()}\n\n"
        message += "Enabled categories:\n"
        for cat in enabled_categories:
            message += f"  ✓ {cat.replace('_', ' ').title()}\n"

        if disabled_categories:
            message += "\nDisabled categories:\n"
            for cat in disabled_categories:
                message += f"  ✗ {cat.replace('_', ' ').title()}\n"

        message += "\nEdit the JSON config file to customize replacements."
        bring_app_to_foreground()
        rumps.alert(title="LLM Output Scrub Configuration", message=message)

    @rumps.clicked("NLP Stats")  # type: ignore[misc]
    def show_nlp_stats(self, _: Any) -> None:
        """Show NLP processing statistics."""
        try:
            processor = get_nlp_processor()
            processor.print_stats()

            # Get detailed statistics
            total_dashes = processor.stats.get("total_dashes", 0)

            if total_dashes > 0:
                spacy_decisions = processor.stats.get("spacy_decisions", 0)
                fallback_decisions = processor.stats.get("fallback_decisions", 0)
                spacy_pct = spacy_decisions / total_dashes * 100
                fallback_pct = fallback_decisions / total_dashes * 100

                # Calculate average confidence
                confidence_scores = processor.stats.get("confidence_scores", [1])
                avg_confidence = sum(confidence_scores) / len(confidence_scores)

                # Build detailed message for alert dialog
                message = f"Total dashes processed: {total_dashes}\n"
                message += f"High-confidence decisions: {spacy_decisions} ({spacy_pct:.1f}%)\n"
                message += f"Fallback decisions: {fallback_decisions} ({fallback_pct:.1f}%)\n\n"

                # Add context types
                context_types = processor.stats.get("context_types", {})
                if context_types:
                    message += "Context types:\n"
                    for context_type, count in context_types.items():
                        pct = count / total_dashes * 100
                        message += f"  {context_type}: {count} ({pct:.1f}%)\n"
                    message += "\n"

                message += f"Average confidence: {avg_confidence:.2f}"

                # Show detailed alert dialog instead of notification
                bring_app_to_foreground()
                rumps.alert(title="📊 NLP Statistics", message=message)
            else:
                bring_app_to_foreground()
                rumps.alert(title="NLP Stats", message="No dashes processed yet")
        except (ValueError, KeyError, TypeError) as e:
            bring_app_to_foreground()
            rumps.alert(title="NLP Stats Error", message=str(e))

    @rumps.clicked("About")  # type: ignore[misc]
    def about(self, _: Any) -> None:
        """Show about dialog."""
        message = (
            "A simple macOS app that replaces smart/typographic characters with plain ASCII.\n\n"
            "Click 'Scrub Clipboard' to process the current clipboard content.\n"
            "Click 'Configure' to view current settings."
        )
        bring_app_to_foreground()
        rumps.alert(title="LLM Output Scrub", message=message)

    def scrub_text(self, text: str) -> str:
        """Replace smart/typographic characters with plain ASCII equivalents."""

        # Get enabled replacements from config
        replacements = self.config.get_all_replacements()

        scrubbed_text = ""
        i = 0
        while i < len(text):
            char = text[i]

            # Special handling for EM dash if dashes category is enabled
            if char == "—" and self.config.is_category_enabled("dashes"):
                replacement = get_dash_replacement_nlp(text, i)
                scrubbed_text += replacement
            elif char in replacements:
                scrubbed_text += replacements[char]
            else:
                scrubbed_text += char

            i += 1

        # Handle other Unicode characters based on config
        if self.config.config["general"]["normalize_unicode"]:
            scrubbed_text = unicodedata.normalize("NFKD", scrubbed_text)

        if self.config.config["general"]["remove_combining_chars"]:
            scrubbed_text = "".join(char for char in scrubbed_text if not unicodedata.combining(char))

        if self.config.config["general"]["remove_non_ascii"]:
            scrubbed_text = "".join(char if ord(char) < 128 else "" for char in scrubbed_text)

        if self.config.config["general"].get("normalize_whitespace", False):
            # Normalize whitespace within each line, preserve empty lines, trim excessive empty lines
            lines = scrubbed_text.split("\n")
            normalized_lines = []
            for line in lines:
                if line.strip():
                    normalized_lines.append(" ".join(line.split()))
                else:
                    normalized_lines.append("")

            # Trim multiple consecutive empty lines to single empty lines
            trimmed_lines: List[str] = []
            prev_was_empty = False
            for line in normalized_lines:
                if line.strip():  # Non-empty line
                    trimmed_lines.append(line)
                    prev_was_empty = False
                else:  # Empty line
                    if not prev_was_empty:  # Only add if previous wasn't empty
                        trimmed_lines.append("")
                    prev_was_empty = True

            # Remove empty lines at the beginning and end
            while trimmed_lines and not trimmed_lines[0].strip():
                trimmed_lines.pop(0)
            while trimmed_lines and not trimmed_lines[-1].strip():
                trimmed_lines.pop()

            scrubbed_text = "\n".join(trimmed_lines)

        return scrubbed_text


def main() -> None:
    """Main entry point for the application."""
    LLMOutputScrub().run()


if __name__ == "__main__":
    main()
