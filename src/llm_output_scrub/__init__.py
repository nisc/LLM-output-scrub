"""
LLM Output Scrub - macOS app that replaces smart/typographic characters with plain ASCII.
"""

__version__ = "0.1.0-alpha"
__author__ = "nisc"
__description__ = "A simple macOS app that replaces smart/typographic characters with plain ASCII"

# Import core functionality that doesn't depend on macOS-specific modules
from .nlp import get_dash_replacement_nlp  # pylint: disable=import-error
from .nlp import SpacyNLPProcessor, get_nlp_processor


# Define NLPProcessor for backward compatibility
def get_nlp_processor_instance() -> SpacyNLPProcessor:
    """Get the NLP processor instance for backward compatibility."""
    return get_nlp_processor()


# Export for backward compatibility
NLPProcessor = get_nlp_processor_instance

# Conditionally import macOS-specific app functionality
try:
    from .app import LLMOutputScrub  # pylint: disable=import-error

    __all__ = ["LLMOutputScrub", "get_dash_replacement_nlp", "NLPProcessor"]
except ImportError:
    # rumps not available (e.g., during unit tests on non-macOS or without macOS deps)
    LLMOutputScrub = None  # type: ignore
    __all__ = ["get_dash_replacement_nlp", "NLPProcessor"]
