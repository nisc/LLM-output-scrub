#!/usr/bin/env python3
"""
LLM Output Scrub - macOS app that replaces smart/typographic characters with plain ASCII.
Run directly: python3 app.py
Or build with: python3 setup.py py2app
"""

import re
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

    # Get the shared application instance
    NS_APP = getattr(AppKit, "NSApplication").sharedApplication()
except ImportError:
    NS_APP = None

# Check if we're on macOS
if sys.platform != "darwin":
    raise ImportError("This app is designed for macOS only.")

try:
    import rumps  # pylint: disable=import-error
except ImportError as exc:
    raise ImportError(
        "rumps is required but not installed. Please install with: pip install -e .[macOS]"
    ) from exc


def bring_dialog_to_front() -> None:
    """Bring alert dialogs to the front without affecting notification state."""
    if NS_APP is not None:
        try:
            # Only activate for dialogs, not for notifications
            NS_APP.activateIgnoringOtherApps_(True)
        except Exception:  # pylint: disable=broad-except
            pass


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
        self.menu = ["Scrub Clipboard", "Configuration", "NLP Stats"]
        self.config = ScrubConfig(config_file)
        self._observer: Optional[Any] = None
        self._start_config_watcher()

        # Set app as background app (no dock icon) - this must be done early
        if NS_APP is not None:
            try:
                # NSApplicationActivationPolicyAccessory = 1 (background app, no dock icon)
                NS_APP.setActivationPolicy_(1)
            except Exception:  # pylint: disable=broad-except
                pass

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
                    title="LLM Output Scrub", subtitle="Empty clipboard", message="No text to process"
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
                    subtitle="Already clean",
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

    @rumps.clicked("Configuration")  # type: ignore[misc]
    def configure(self, _: Any) -> None:
        """Show configuration dialog."""
        self._show_config_dialog()

    def _show_config_dialog(self) -> None:
        """Show the toggle settings menu directly as the main configuration dialog."""
        self._toggle_single_setting()

    def _toggle_single_setting(self) -> None:
        """Show all settings in one dialog with option to toggle any of them."""
        bring_dialog_to_front()

        # Create numbered list for selection
        all_settings = []

        # Add general settings with intuitive descriptions
        general_settings = self.config.get_general_settings()
        setting_descriptions = {
            "normalize_unicode": "Decompose Unicode Characters (é→e + accent)",
            "remove_combining_chars": "Remove Accent Marks (e + accent→e)",
            "remove_non_ascii": "Remove All Non-ASCII",
            "normalize_whitespace": "Clean Up Extra Spacing",
        }

        for setting, value in general_settings.items():
            setting_name = setting_descriptions.get(setting, setting.replace("_", " ").title())
            all_settings.append(("general", setting, setting_name, value))

        # Add separator between general and category settings
        all_settings.append(("separator", "", "", False))

        # Add categories and their sub-settings
        categories = self.config.get_categories()

        for category in categories:
            enabled = self.config.is_category_enabled(category)
            category_name = self.config.get_category_display_name(category)
            all_settings.append(("category", category, category_name, enabled))

            # Add sub-settings if category is enabled
            if enabled:
                sub_settings = self.config.get_sub_settings(category)
                for setting_key, display_name, current_value in sub_settings:
                    all_settings.append(
                        ("sub_setting", f"{category}_{setting_key}", display_name, current_value)
                    )

        # Build settings display with numbered list

        # Add option 0 for Restore Defaults
        settings_text = "⚪ 0. Restore Defaults\n\n"

        # Track if we've shown the general settings title
        general_title_shown = False
        category_title_shown = False

        def get_status_symbol(value: bool) -> str:
            """Return the appropriate status symbol for a setting."""
            return "🟢" if value else "🔴"

        for i, (setting_type, setting_key, setting_name, current_value) in enumerate(all_settings, 1):
            if setting_type == "separator":
                settings_text += "\n"
            elif setting_type in ["general", "category", "sub_setting"]:
                # Show title for first occurrence of each type
                if setting_type == "general" and not general_title_shown:
                    settings_text += "GENERAL SETTINGS:\n"
                    general_title_shown = True
                elif setting_type == "category" and not category_title_shown:
                    settings_text += "REPLACEMENTS:\n"
                    category_title_shown = True

                # Add the setting line
                settings_text += f"{get_status_symbol(current_value)} {i}. {setting_name}\n"

        # Use rumps.Window for input
        window = rumps.Window(
            message=settings_text + '\nEnter numbers to toggle (e.g. "3 5 9"):',
            title="Configuration",
            ok="Toggle",
            cancel="Close",
            default_text="",
        )

        response = window.run()

        if response.clicked == 1:  # Toggle clicked
            try:
                # Parse comma-separated numbers with proper sanitization
                input_text = response.text.strip()
                if not input_text:
                    rumps.alert(title="Invalid Input", message="Please enter at least one number.")
                    self._toggle_single_setting()
                    return

                # Check for single "0" input (Restore Defaults) - must be standalone
                if input_text.strip() == "0":
                    self._restore_defaults()
                    return

                # Split by multiple separators and clean each number
                # Split by any non-digit character (allows any character as separator)
                number_strings = re.split(r"[^\d]+", input_text)
                selections = []

                for num_str in number_strings:
                    if not num_str:  # Skip empty strings
                        continue
                    try:
                        num = int(num_str)
                        if num == 0:
                            # 0 can only be used standalone
                            rumps.alert(
                                title="Invalid Input",
                                message="Option 0 (Restore Defaults) must be entered alone, "
                                "not with other numbers.",
                            )
                            self._toggle_single_setting()
                            return
                        elif 1 <= num <= len(all_settings):
                            selections.append(num)
                        else:
                            rumps.alert(
                                title="Invalid Number",
                                message=f"Number {num} is out of range (1-{len(all_settings)})",
                            )
                            self._toggle_single_setting()
                            return
                    except ValueError:
                        rumps.alert(title="Invalid Input", message=f"'{num_str}' is not a valid number")
                        self._toggle_single_setting()
                        return

                # Remove duplicates while preserving order
                unique_selections = []
                for num in selections:
                    if num not in unique_selections:
                        unique_selections.append(num)

                if not unique_selections:
                    rumps.alert(title="No Valid Selections", message="No valid settings were selected.")
                    self._toggle_single_setting()
                    return

                # Toggle all selected settings
                toggled_settings = []
                for selection in unique_selections:
                    setting_type, setting_key, setting_name, current_value = all_settings[selection - 1]

                    # Toggle the setting
                    if setting_type == "general":
                        self.config.set_general_setting(setting_key, not current_value)
                    elif setting_type == "sub_setting":
                        # For sub-settings, we need to find the category name in the setting_key
                        # The setting_key format is: "category_setting_name"
                        # We need to find the category by looking at the categories list
                        categories = self.config.get_categories()
                        category = ""
                        setting = ""

                        for cat in categories:
                            if setting_key.startswith(f"{cat}_"):
                                category = cat
                                setting = setting_key[len(cat) + 1 :]
                                break

                        if category and setting:
                            self.config.set_sub_setting(category, setting, not current_value)
                    else:  # category
                        self.config.set_category_enabled(setting_key, not current_value)

                    new_status = "ON" if not current_value else "OFF"
                    toggled_settings.append(f"{setting_name} ({new_status})")

                # Show notification for all toggled settings
                if len(toggled_settings) == 1:
                    rumps.notification(
                        title="Setting Updated",
                        subtitle=toggled_settings[0],
                        message="Configuration saved.",
                    )
                else:
                    rumps.notification(
                        title="Settings Updated",
                        subtitle=f"{len(toggled_settings)} settings toggled",
                        message="Configuration saved.",
                    )

                # Stay in the toggle menu by calling it again
                self._toggle_single_setting()

            except (ValueError, TypeError, OSError) as e:
                rumps.alert(title="Error", message=f"An error occurred: {str(e)}")
                self._toggle_single_setting()
        elif response.clicked == 0:  # Close clicked
            # Return to main menu (do nothing, just exit)
            pass
        # If window is closed (response.clicked == -1), return to main menu

    def _restore_defaults(self) -> None:
        """Restore all configuration settings to their default values."""
        bring_dialog_to_front()
        confirm = rumps.alert(
            title="Restore Defaults",
            message="Are you sure you want to restore all settings to their default values?",
            ok="Yes, Restore",
            cancel="Cancel",
        )
        if confirm == 1:
            # Reset to defaults using the config manager method
            self.config.reset_to_defaults()
            rumps.notification(
                title="LLM Output Scrub",
                subtitle="Defaults Restored",
                message="All settings have been reset to defaults.",
            )
            # Return to main configuration dialog
            self._toggle_single_setting()

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
                bring_dialog_to_front()
                rumps.alert(title="📊 NLP Statistics", message=message)
            else:
                bring_dialog_to_front()
                rumps.alert(title="NLP Stats", message="No dashes processed yet")
        except (ValueError, KeyError, TypeError) as e:
            bring_dialog_to_front()
            rumps.alert(title="NLP Stats Error", message=str(e))

    def scrub_text(self, text: str) -> str:
        """Replace smart/typographic characters with plain ASCII equivalents."""

        # Get enabled replacements from config
        replacements = self.config.get_all_replacements()

        scrubbed_text = ""
        i = 0
        while i < len(text):
            char = text[i]

            # Special handling for EM dash if em_dashes category is enabled
            if char == "—" and self.config.is_em_dash_enabled():
                if self.config.is_em_dash_contextual():
                    replacement, new_position = get_dash_replacement_nlp(text, i)
                    scrubbed_text += replacement
                    i = new_position
                    continue
                else:
                    # Use simple replacement from config
                    scrubbed_text += self.config.config["character_replacements"]["em_dashes"][
                        "replacements"
                    ]["—"]
            elif char in replacements:
                scrubbed_text += replacements[char]
            else:
                scrubbed_text += char

            i += 1

        # Handle Unicode normalization and cleanup
        if self.config.config["general"]["normalize_unicode"]:
            scrubbed_text = unicodedata.normalize("NFKD", scrubbed_text)

        if self.config.config["general"]["remove_combining_chars"]:
            scrubbed_text = "".join(char for char in scrubbed_text if not unicodedata.combining(char))

        if self.config.config["general"]["remove_non_ascii"]:
            scrubbed_text = "".join(char if ord(char) < 128 else "" for char in scrubbed_text)

        # Handle whitespace normalization (final formatting step)
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
