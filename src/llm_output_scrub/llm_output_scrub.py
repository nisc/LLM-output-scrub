#!/usr/bin/env python3
"""
LLM Output Scrub - macOS app that replaces smart/typographic characters with plain ASCII.
Run directly: python3 llm_output_scrub.py
Or build with: python3 setup.py py2app
"""

import threading
import unicodedata
from pathlib import Path
from typing import Any, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import pyperclip
import rumps  # pylint: disable=import-error

from llm_output_scrub.config_manager import ScrubConfig  # pylint: disable=import-error
from llm_output_scrub.dash_nlp import get_dash_replacement  # pylint: disable=import-error

# If you get import errors, run with:
# python -m llm_output_scrub.llm_output_scrub
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

    def __init__(self) -> None:
        super().__init__("🧹", quit_button="")
        self.menu = ["Scrub LLM Output", "Configure", "About", "Quit"]
        self.config = ScrubConfig()
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

    @rumps.clicked("Quit")  # type: ignore[misc]
    def quit_app(self, _: Any) -> None:
        """Quit the application."""
        rumps.quit_application()

    @rumps.clicked("Scrub LLM Output")  # type: ignore[misc]
    def scrub_llm_output(self, _: Any) -> None:
        """Scrub the clipboard content by replacing smart quotes and other typographic characters."""
        try:
            # Get current clipboard content
            clipboard_text = pyperclip.paste()

            if not clipboard_text:
                rumps.notification(
                    title="LLM Output Scrub", subtitle="No content", message="Clipboard is empty"
                )  # fmt: off
                return

            # Scrub the text
            scrubbed_text = self.scrub_text(clipboard_text)

            # Put scrubbed text back to clipboard
            pyperclip.copy(scrubbed_text)

            # Show notification
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
        rumps.alert(title="LLM Output Scrub Configuration", message=message)

    @rumps.clicked("About")  # type: ignore[misc]
    def about(self, _: Any) -> None:
        """Show about dialog."""
        message = (
            "A simple macOS app that replaces smart/typographic characters with plain ASCII.\n\n"
            "Click 'Scrub LLM Output' to process the current clipboard content.\n"
            "Click 'Configure' to view current settings."
        )
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
                replacement = get_dash_replacement(text, i)
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

        if self.config.config["general"].get("normalize_whitespace", True):
            scrubbed_text = " ".join(scrubbed_text.split())

        return scrubbed_text


if __name__ == "__main__":
    LLMOutputScrub().run()
