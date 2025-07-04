"""
LLM Output Scrub - macOS app that replaces smart/typographic characters with plain ASCII.
"""

__version__ = "0.0.1"
__author__ = "nisc"
__description__ = "A simple macOS app that replaces smart/typographic characters with plain ASCII"

from .llm_output_scrub import LLMOutputScrub  # pylint: disable=import-error

__all__ = ["LLMOutputScrub"]
