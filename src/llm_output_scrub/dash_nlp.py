"""
Context-aware EM/EN dash replacement logic for LLM Output Scrub.
"""

import re
from .wordlists import interruption_phrases, emphasis_words, compound_patterns


def get_dash_replacement(text: str, position: int) -> str:
    """Determine the appropriate replacement for an EM dash based on advanced NLP context analysis.
    Always replaces the EM dash; never preserves it, regardless of context.
    """
    before = text[:position].strip()
    after = text[position + 1 :].strip()

    # 1. DIALOGUE AND ATTRIBUTION (quote followed by name or attribution)
    if _is_dialogue_context(before, after):
        return ", "

    # 2. RANGE DETECTION (Enhanced) - check before mathematical
    if _is_range_context(before, after):
        return "-"

    # 3. MATHEMATICAL AND TECHNICAL CONTEXTS
    if _is_mathematical_context(before, after):
        return " - "

    # 4. EMPHASIS AND FOCUS (check before interruption)
    if _is_emphasis_context(before, after):
        return ", "

    # 5. SENTENCE INTERRUPTION (e.g., 'He stopped—what was that?')
    if _is_sentence_boundary_or_interruption(before, after):
        return "... "

    # 6. PARENTHETICAL AND APPOSITIVE (check before compound words)
    prev_dash = text.rfind("—", 0, position)
    if prev_dash != -1:
        before_prev = text[:prev_dash].strip()
        after_prev_start = prev_dash + 1
        after_prev = text[after_prev_start:position].strip()
        is_range = _is_range_context(before_prev, after_prev)
        if is_range:
            return ", "
    if _is_parenthetical_context(before, after):
        return ", "

    # 7. LIST/ENUMERATION WITH COMPOUND WORDS (e.g., 1—self—driving cars)
    if before and before[-1].isdigit() and after and after[0].isalpha():
        return ": "

    # Handle compound words in numeral-list contexts (e.g., "1: self—driving cars")
    if before and after and before[-1].isalpha() and after[0].isalpha():
        prev_colon = text.rfind(":", 0, position)
        if prev_colon != -1:
            before_colon = text[:prev_colon].strip()
            if before_colon and before_colon[-1].isdigit():
                return "-"

    # 8. COMPOUND WORDS AND HYPHENATION (more specific check)
    if _is_compound_word_context(before, after):
        if len(before.split()[-1]) <= 3:
            return "-"
        else:
            return " - "

    # 9. SENTENCE BOUNDARY (e.g., 'He stopped—what was that?')
    if before and after and before[-1].isalpha() and after[0].isupper():
        if len(before.split()[-1]) > 1 and len(after.split()[0]) > 1:
            return ". "

    # 10. LIST AND ENUMERATION
    if _is_list_context(before):
        return " - "

    # Default: treat as parenthetical
    return ", "


def _find_sentence_start(text: str, position: int) -> int:
    for i in range(position - 1, -1, -1):
        if text[i] in ".!?\n":
            return i + 1
    return 0


def _find_sentence_end(text: str, position: int) -> int:
    for i in range(position + 1, len(text)):
        if text[i] in ".!?\n":
            return i + 1
    return len(text)


def _is_mathematical_context(before: str, after: str) -> bool:
    # More precise mathematical patterns that exclude ranges
    math_patterns = [
        # Variable operations: x—y (but not single letters which are ranges)
        r"[a-zA-Z]\s*[+\-*/=<>≤≥≠≈±]\s*$",
        r"[+\-*/=<>≤≥≠≈±]\s*[a-zA-Z]$",
        # Function notation: f(x)—g(x)
        r"[a-zA-Z]\([^)]*\)\s*[+\-*/=<>≤≥≠≈±]\s*$",
        r"[+\-*/=<>≤≥≠≈±]\s*[a-zA-Z]\([^)]*\)$",
        # Complex expressions with operators
        r"\d+\s*[+\-*/=<>≤≥≠≈±]\s*$",
        r"[+\-*/=<>≤≥≠≈±]\s*\d+$",
    ]

    for pattern in math_patterns:
        if re.search(pattern, before) or re.search(pattern, after):
            return True

    # Special case: function notation like f(x)—g(x)
    if re.search(r"[a-zA-Z]\([^)]*\)\s*$", before) and re.search(r"^[a-zA-Z]\([^)]*\)", after):
        return True

    return False


def _is_range_context(before: str, after: str) -> bool:
    if not before or not after:
        return False

    # Simple numeric ranges: 1—5, 2.1—3.0
    if (before[-1].isdigit() or before[-1] == ".") and (after[0].isdigit() or after[0] == "."):
        return True

    # Single letter ranges: A—Z
    if (
        before[-1].isalpha()
        and after[0].isalpha()
        and len(before.split()[-1]) == 1
        and len(after.split()[0]) == 1
    ):
        return True

    # Date patterns
    date_patterns = [r"\d{4}$", r"\d{1,2}/\d{1,2}$", r"\d{1,2}-\d{1,2}$"]
    for pattern in date_patterns:
        if re.search(pattern, before) and re.search(pattern, after):
            return True

    # Version numbers: 2.1—3.0
    if re.search(r"\d+\.\d+$", before) and re.search(r"^\d+\.\d+", after):
        return True

    # Page numbers: Pages 1—10
    if re.search(r"Pages?\s+\d+$", before) and re.search(r"^\d+", after):
        return True

    # Years: 2020—2023
    if re.search(r"Years?\s+\d{4}$", before) and re.search(r"^\d{4}", after):
        return True

    return False


def _is_dialogue_context(before: str, after: str) -> bool:
    # Match if before ends with quote and after starts with a capitalized name/attribution
    if re.search(r'["\']\s*$', before) and re.match(r"^[A-Z][a-z]+", after):
        return True
    # Match attribution patterns like "The answer—Mary replied" (no quote)
    if re.search(r"\s+$", before) and re.match(r"^[A-Z][a-z]+", after):
        # Check if this looks like attribution by looking for common patterns
        # Capitalized name followed by lowercase word (likely a verb)
        if re.match(r"^[A-Z][a-z]+\s+[a-z]+", after):
            return True
    return False


def _is_sentence_boundary_or_interruption(before: str, after: str) -> bool:
    # Check for sentence-ending punctuation
    if after and after[0] in ".!?":
        return True

    # Check for specific interruption phrases that indicate abrupt breaks
    after_lower = after.lower()
    for phrase in interruption_phrases:
        if after_lower.startswith(phrase):
            return True

    # Check for sentence boundary (capitalized word after dash)
    if len(after) > 0 and after[0].isupper() and len(before) > 0 and before[-1].isalpha():
        # But exclude dialogue and emphasis contexts
        if not _is_dialogue_context(before, after) and not _is_emphasis_context(before, after):
            return True

    return False


def _is_parenthetical_context(before: str, after: str) -> bool:
    if after and after[0] == " ":
        return True
    if (
        before
        and after
        and before[-1].isalpha()
        and after[0].isalpha()
        and len(before.split()[-1]) > 1
        and len(after.split()[0]) > 1
    ):
        return True
    return False


def _is_emphasis_context(before: str, after: str) -> bool:
    # Emphasis typically involves short, impactful words or phrases
    # that are set off by dashes for dramatic effect
    after_lower = after.lower()
    for word in emphasis_words:
        if after_lower.startswith(word):
            return True

    # Also check for patterns like "The result—amazingly—was perfect"
    # where the emphasis word is between two dashes
    if before and after:
        before_words = before.split()
        after_words = after.split()
        if before_words and after_words and len(before_words[-1]) > 2 and len(after_words[0]) > 2:
            return True

    return False


def _is_list_context(before: str) -> bool:
    if before and before[-1].isdigit():
        return True
    if before and before[-1] in "•·":
        return True
    return False


def _is_compound_word_context(before: str, after: str) -> bool:
    if not before:
        return False

    # Only treat as compound word if it's clearly a compound pattern
    # Don't treat general alpha-alpha sequences as compound words
    for pattern in compound_patterns:
        if before.endswith(pattern):
            return True

    # Only treat short words as potential compound parts if they're clearly compound-like
    if before[-1].isalpha() and len(before.split()[-1]) <= 3:
        # Check if this looks like a compound word pattern
        if after and after[0].isalpha():
            # Only treat as compound if it's a very short word followed by a longer word
            # and it's not clearly parenthetical context
            if len(after.split()[0]) > 3 and not _is_parenthetical_context(before, after):
                return True

    return False
