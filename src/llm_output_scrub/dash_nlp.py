"""
Context-aware EM/EN dash replacement logic for LLM Output Scrub.
"""

import re


def get_dash_replacement(text: str, position: int) -> str:
    """Determine the appropriate replacement for an EM dash based on advanced NLP context analysis.
    Always replaces the EM dash; never preserves it, regardless of context.
    """
    before = text[:position].strip()
    after = text[position + 1 :].strip()

    # 1. MATHEMATICAL AND TECHNICAL CONTEXTS
    if _is_mathematical_context(before, after):
        return " - "

    # 2. RANGE DETECTION (Enhanced)
    if _is_range_context(before, after):
        return "-"

    # 3. SENTENCE INTERRUPTION (e.g., 'He stopped—what was that?')
    if _is_sentence_boundary_or_interruption(before, after):
        return "... "

    # 4. PARENTHETICAL AND APPOSITIVE
    # If previous dash was a range, treat this as parenthetical
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

    # 5. LIST/ENUMERATION WITH COMPOUND WORDS (e.g., 1—self—driving cars)
    if before and before[-1].isdigit() and after and after[0].isalpha():
        # First dash after a numeral gets colon and space
        return ": "

    # Handle compound words in numeral-list contexts (e.g., "1: self—driving cars")
    if before and after and before[-1].isalpha() and after[0].isalpha():
        # Check if this is part of a numeral-list context by looking for previous colon
        prev_colon = text.rfind(":", 0, position)
        if prev_colon != -1:
            # Check if there's a numeral before the colon
            before_colon = text[:prev_colon].strip()
            if before_colon and before_colon[-1].isdigit():
                # This is a compound word in a numeral-list context
                return "-"

    # If dash is between short words (compound), use '-' only if both sides are <4 chars and not parenthetical
    if _is_compound_word_context(before):
        if len(before.split()[-1]) <= 3:
            return "-"
        else:
            return " - "

    # 6. SENTENCE BOUNDARY (e.g., 'He stopped—what was that?')
    if before and after and before[-1].isalpha() and after[0].isupper():
        if len(before.split()[-1]) > 1 and len(after.split()[0]) > 1:
            return ". "

    # 7. DIALOGUE AND ATTRIBUTION
    if _is_dialogue_context(before, after):
        return " - "

    # 8. EMPHASIS AND FOCUS
    if _is_emphasis_context(before, after):
        return " - "

    # 9. LIST AND ENUMERATION
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
    math_patterns = [
        r"\d+\s*[+\-*/=<>≤≥≠≈±]\s*$",
        r"[+\-*/=<>≤≥≠≈±]\s*\d+$",
        r"[a-zA-Z]\s*[+\-*/=<>≤≥≠≈±]\s*$",
        r"[+\-*/=<>≤≥≠≈±]\s*[a-zA-Z]$",
    ]
    for pattern in math_patterns:
        if re.search(pattern, before) or re.search(pattern, after):
            return True
    return False


def _is_range_context(before: str, after: str) -> bool:
    if not before or not after:
        return False
    if (before[-1].isdigit() or before[-1] == ".") and (after[0].isdigit() or after[0] == "."):
        return True
    if (
        before[-1].isalpha()
        and after[0].isalpha()
        and len(before.split()[-1]) == 1
        and len(after.split()[0]) == 1
    ):
        return True
    date_patterns = [r"\d{4}$", r"\d{1,2}/\d{1,2}$", r"\d{1,2}-\d{1,2}$"]
    for pattern in date_patterns:
        if re.search(pattern, before) and re.search(pattern, after):
            return True
    if re.search(r"\d+\.\d+$", before) and re.search(r"^\d+\.\d+", after):
        return True
    return False


def _is_dialogue_context(before: str, after: str) -> bool:
    dialogue_patterns = [r'["\']\s*$', r'^\s*["\']', r"^\s*[A-Z][a-z]+"]
    for pattern in dialogue_patterns:
        if re.search(pattern, before) or re.search(pattern, after):
            return True
    return False


def _is_sentence_boundary_or_interruption(before: str, after: str) -> bool:
    if after and after[0] in ".!?":
        return True
    interruption_phrases = [
        "never mind",
        "forget it",
        "whatever",
        "anyway",
        "actually",
        "well",
        "oh",
        "um",
        "uh",
        "er",
        "hmm",
        "so",
        "but",
        "however",
        "nevertheless",
        "meanwhile",
        "suddenly",
        "unexpectedly",
        "fortunately",
        "unfortunately",
        "interestingly",
        "surprisingly",
        "obviously",
        "clearly",
        "apparently",
        "evidently",
        "what",
    ]
    after_lower = after.lower()
    for phrase in interruption_phrases:
        if after_lower.startswith(phrase):
            return True
    if len(after) > 0 and after[0].isupper() and len(before) > 0 and before[-1].isalpha():
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
    if (not before or before[-1] in " \n\t") and (not after or after[0] in " \n\t"):
        return True
    return False


def _is_list_context(before: str) -> bool:
    if before and before[-1].isdigit():
        return True
    if before and before[-1] in "•·":
        return True
    return False


def _is_compound_word_context(before: str) -> bool:
    if not before:
        return False
    if before[-1].isalpha() and len(before.split()[-1]) <= 3:
        return True
    compound_patterns = [
        "self-",
        "pre-",
        "post-",
        "anti-",
        "pro-",
        "co-",
        "non-",
        "re-",
        "un-",
        "-based",
        "-oriented",
        "-friendly",
        "-free",
        "-less",
        "-like",
        "-wise",
    ]
    for pattern in compound_patterns:
        if before.endswith(pattern):
            return True
    return False
