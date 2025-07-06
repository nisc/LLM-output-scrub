# flake8: noqa
# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument,unnecessary-ellipsis

"""Stub file for rumps (minimal docstrings for linter compliance)."""

from typing import Any, Callable

def clicked(title: str) -> Callable[[Any], Any]:
    """Decorator for menu item click handlers."""
    ...

class App:
    """Stub for rumps.App."""

    def __init__(self, name: str, **kwargs: Any) -> None: ...
    def run(self) -> None: ...
    def quit(self) -> None: ...

class Window:
    """Stub for rumps.Window."""

    def __init__(
        self, message: str, title: str, ok: str = "OK", cancel: str = "Cancel", default_text: str = ""
    ) -> None: ...
    def run(self) -> Any: ...

def notification(title: str, subtitle: str, message: str) -> None:
    """Stub for rumps.notification."""
    ...

def alert(title: str, message: str, ok: str = "OK", cancel: str = "Cancel") -> bool:
    """Stub for rumps.alert."""
    ...

def application_support(name: str) -> str:
    """Stub for rumps.application_support."""
    ...
