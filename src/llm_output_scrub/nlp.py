"""
SpaCy-first NLP processor for EM dash replacement.
Uses linguistic features and POS tagging instead of hardcoded patterns.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import spacy

__all__ = ["get_dash_replacement_nlp", "get_nlp_processor", "get_nlp_stats"]


def load_spacy_model() -> spacy.language.Language:
    """Load spaCy model, trying bundled path first for standalone app."""
    # Try to load from bundled path first (for standalone app)
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        bundled_model_path = os.path.join(app_dir, "en_core_web_sm")
        if os.path.exists(bundled_model_path):
            return spacy.load(bundled_model_path)
    except (OSError, ImportError):
        pass

    try:
        return spacy.load("en_core_web_sm")
    except OSError as e:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' could not be loaded. "
            "Ensure it is bundled with the app or installed in the environment."
        ) from e


def get_nlp_model() -> spacy.language.Language:
    """Get the spaCy model, loading it if necessary."""
    return load_spacy_model()


class DummyToken:
    """Dummy token for fallback when spaCy tokenization fails."""

    def __init__(self, text: str, pos_: str):
        self.text = text
        self.pos_ = pos_


class AnalysisResult:
    """Result of linguistic analysis."""

    def __init__(self, replacement: str, context_type: str, confidence: float):
        self.replacement = replacement
        self.context_type = context_type
        self.confidence = confidence


class SpacyNLPProcessor:
    """SpaCy-based NLP processor for context-aware EM dash replacement."""

    def __init__(self) -> None:
        """Initialize the processor."""
        self._nlp: Optional[spacy.language.Language] = None  # Lazy-load the model
        self.stats: Dict[str, Any] = {
            "total_dashes": 0,
            "context_types": {},
            "confidence_scores": [],
            "spacy_decisions": 0,
            "fallback_decisions": 0,
        }
        self.stats_file = Path("nlp_stats.json")

    def get_spacy_model(self) -> spacy.language.Language:
        """Get the spaCy model, loading it if necessary."""
        if self._nlp is None:
            self._nlp = get_nlp_model()
        return self._nlp

    def get_dash_replacement(self, text: str, position: int) -> str:
        """Get context-aware replacement for EM dash at given position."""
        self.stats["total_dashes"] += 1
        dash_char = "—"

        # Find the sentence containing the dash
        doc = self.get_spacy_model()(text)
        sent: Any = None
        sent_start = 0
        for s in doc.sents:
            sent_start = doc[s.start].idx
            sent_end = doc[s.end - 1].idx + len(doc[s.end - 1])
            if sent_start <= position < sent_end:
                sent = s
                break
        if sent is None:
            sent = doc
            sent_start = 0
        sent_text = sent.text
        dash_pos_in_sent = position - sent_start
        dashes_in_sent = [i for i, c in enumerate(sent_text) if c == dash_char]
        # Compound dash: only if both sides are a single token, not proper nouns,
        # not surrounded by whitespace or punctuation
        # AND only if there's exactly one dash in the sentence (not a parenthetical pair)
        if len(dashes_in_sent) == 1:
            sent_doc = self.get_spacy_model()(sent_text)
            dash_token_idx = None
            for i, token in enumerate(sent_doc):
                if token.text == dash_char:
                    dash_token_idx = i
                    break
            if dash_token_idx is not None and dash_token_idx > 0 and dash_token_idx < len(sent_doc) - 1:
                before_token = sent_doc[dash_token_idx - 1]
                after_token = sent_doc[dash_token_idx + 1]

                # Special case: conjunction after dash (e.g., "€50—or") should be parenthetical
                if after_token.pos_ == "CCONJ":
                    self._log_decision("conjunction_parenthetical", 0.85)
                    return ", "

                # Only treat as compound if both tokens are short (1-2 chars) or form a true compound pattern
                # Special case: single-letter mathematical variables (like x) should be treated as compounds
                # even if classified as PROPN, but only if they appear in mathematical contexts
                is_single_letter_variable = (
                    len(before_token.text) == 1
                    and len(after_token.text) == 1
                    and before_token.text.isalpha()
                    and after_token.text.isalpha()
                    and before_token.text.islower()
                    and after_token.text.islower()
                )

                is_compound = (
                    before_token.is_alpha
                    and after_token.is_alpha
                    and (
                        (
                            before_token.pos_ not in ["PROPN", "ADV", "CCONJ"]
                            and after_token.pos_ not in ["PROPN", "ADV", "CCONJ"]
                        )
                        or is_single_letter_variable
                    )
                    and (len(before_token.text) <= 8 and len(after_token.text) <= 8)
                    and (
                        sent_text[
                            before_token.idx
                            + len(before_token.text) : before_token.idx
                            + len(before_token.text)
                            + 1
                        ]
                        == dash_char
                    )
                    and sent_text[after_token.idx - 1 : after_token.idx] == dash_char
                )
                if is_compound:
                    self._log_decision("compound", 0.95)
                    return "-"
        # Parenthetical/emphasis: if there is a matching dash in the sentence and the tokens between are not
        # just single words
        if len(dashes_in_sent) >= 2:
            right_dashes = [i for i in dashes_in_sent if i > dash_pos_in_sent]
            if right_dashes:
                closing_dash_pos = right_dashes[0]
                between_text = sent_text[dash_pos_in_sent + 1 : closing_dash_pos]
                between_doc = self.get_spacy_model()(between_text)
                non_punct_tokens = [t for t in between_doc if not t.is_punct and t.text.strip()]
                # Parenthetical/emphasis: more than one token, or single adverb/adjective
                if len(non_punct_tokens) > 1 or (
                    len(non_punct_tokens) == 1
                    and non_punct_tokens[0].pos_ in ["ADV", "ADJ"]
                    and len(non_punct_tokens[0].text) > 2
                ):
                    self._log_decision("parenthetical_pair", 0.85)
                    return ", "
            left_dashes = [i for i in dashes_in_sent if i < dash_pos_in_sent]
            if left_dashes:
                opening_dash_pos = left_dashes[-1]
                between_text = sent_text[opening_dash_pos + 1 : dash_pos_in_sent]
                between_doc = self.get_spacy_model()(between_text)
                non_punct_tokens = [t for t in between_doc if not t.is_punct and t.text.strip()]
                # Parenthetical/emphasis: more than one token, or single adverb/adjective
                if len(non_punct_tokens) > 1 or (
                    len(non_punct_tokens) == 1
                    and non_punct_tokens[0].pos_ in ["ADV", "ADJ"]
                    and len(non_punct_tokens[0].text) > 2
                ):
                    self._log_decision("parenthetical_pair", 0.85)
                    return ", "
        context_start = max(0, position - 150)
        context_end = min(len(text), position + 150)
        context_text = text[context_start:context_end]
        dash_pos_in_context = position - context_start
        context_doc = self.get_spacy_model()(context_text)
        result = self._analyze_linguistic_context(context_doc, dash_pos_in_context, text, position)
        self._log_decision(result.context_type, result.confidence)
        if self.stats["total_dashes"] % 50 == 0:
            self._save_stats()
        # Always normalize whitespace around comma replacements (", ") regardless of setting
        if result.replacement.strip() == ",":
            return ", "
        return result.replacement

    def _analyze_linguistic_context(
        self, doc: Any, dash_pos: int, full_text: str, position: int
    ) -> AnalysisResult:
        """Analyze context using SpaCy linguistic features based on pattern analysis."""

        # 1. Dialogue attribution - High confidence: quotes_before + verb_after
        if self._is_dialogue_context(doc, dash_pos, full_text, position):
            return AnalysisResult(", ", "dialogue", 0.85)

        # 2. Parenthetical - High confidence: verb_after + determiner_after + second dash
        if self._is_parenthetical_context(doc, dash_pos, full_text, position):
            return AnalysisResult(", ", "parenthetical", 0.80)

        # 3. Emphasis - High confidence: adverb_after (ending in -ly) + adjective_after
        if self._is_emphasis_context(doc, dash_pos, full_text, position):
            return AnalysisResult(", ", "emphasis", 0.75)

        # 4. List context - High confidence: noun_after + punctuation_after
        if self._is_list_context(doc, dash_pos, full_text, position):
            return AnalysisResult(", ", "list", 0.70)

        # Default: simple hyphen replacement (no whitespace changes)
        return AnalysisResult("-", "general", 0.60)

    def _is_dialogue_context(self, doc: Any, _dash_pos: int, full_text: str, position: int) -> bool:
        """Use SpaCy patterns to detect dialogue attribution."""
        # Find the dash token in the document
        dash_token = None
        dash_token_idx = None
        for i, token in enumerate(doc):
            if token.text == "—":
                dash_token = token
                dash_token_idx = i
                break

        # Fallback: look for a token containing the dash as a substring
        if dash_token is None:
            for i, token in enumerate(doc):
                if "—" in token.text:
                    dash_token = token
                    dash_token_idx = i
                    break

        if dash_token is None:
            return False

        # Get tokens before and after dash (or inside the merged token)
        before_token = None
        after_token = None
        if dash_token_idx is not None:
            if dash_token.text == "—":
                if dash_token_idx > 0:
                    before_token = doc[dash_token_idx - 1]
                if dash_token_idx < len(doc) - 1:
                    after_token = doc[dash_token_idx + 1]
            else:
                # Dash is inside a merged token, e.g. 'challenging"—Dr'
                # Try to split at the dash
                dash_in_token_idx = dash_token.text.find("—")
                # For before_token, use the same token but up to the dash, or previous token if available
                if dash_in_token_idx > 0:
                    before_token = DummyToken(dash_token.text[:dash_in_token_idx], dash_token.pos_)
                elif dash_token_idx > 0:
                    before_token = doc[dash_token_idx - 1]
                # For after_token, use the same token after the dash, or next token if available
                if dash_in_token_idx < len(dash_token.text) - 1:
                    after_token = DummyToken(dash_token.text[dash_in_token_idx + 1 :], dash_token.pos_)
                elif dash_token_idx < len(doc) - 1:
                    after_token = doc[dash_token_idx + 1]

        # Dialogue attribution: quote before dash and proper noun after dash
        if before_token and after_token:
            if (
                before_token.text in ['"', "'"]
                or before_token.text.endswith('"')
                or before_token.text.endswith("'")
            ):
                if after_token.pos_ == "PROPN":
                    return True

        # Additional check: look at raw text around the dash position
        if position > 0:
            char_before_dash = full_text[position - 1]
            if char_before_dash in ['"', "'"] and after_token and after_token.pos_ == "PROPN":
                return True

        # Dialogue attribution without quotes: noun before dash and proper noun after dash
        if before_token and after_token:
            if before_token.pos_ == "NOUN" and after_token.pos_ == "PROPN":
                return True

        # Fallback: original logic for high-confidence patterns
        before_tokens = [t for t in doc if t.i < (dash_token_idx if dash_token_idx is not None else 0)][-5:]
        after_tokens = [t for t in doc if t.i > (dash_token_idx if dash_token_idx is not None else 0)][:5]

        has_quotes_before = any(t.text in ['"', "'"] for t in before_tokens)
        has_verb_after = any(t.pos_ == "VERB" for t in after_tokens)
        has_noun_after = any(t.pos_ == "NOUN" for t in after_tokens)
        has_pronoun_after = any(t.pos_ == "PRON" for t in after_tokens)

        if has_quotes_before and has_verb_after:
            return True
        if has_quotes_before and (has_noun_after or has_pronoun_after):
            return True

        return False

    def _is_parenthetical_context(self, doc: Any, _dash_pos: int, full_text: str, position: int) -> bool:
        """Use SpaCy patterns to identify parenthetical information."""
        # Find the dash token in the document
        dash_token = None
        for token in doc:
            if token.text == "—":
                dash_token = token
                break

        if not dash_token:
            return False

        # Get tokens after dash
        after_tokens = [t for t in doc if t.i > dash_token.i][:10]

        # High confidence signals from pattern analysis
        has_verb_after = any(t.pos_ == "VERB" for t in after_tokens)
        has_determiner_after = any(t.pos_ == "DET" for t in after_tokens)
        has_noun_after = any(t.pos_ == "NOUN" for t in after_tokens)

        # Parenthetical pattern: verb + determiner + noun (high confidence)
        if has_verb_after and has_determiner_after and has_noun_after:
            return True

        # Also detect parenthetical for the second dash in a pair
        if has_verb_after and has_noun_after:
            # Check if this is the second dash in a pair
            before_dash = full_text[max(0, position - 100) : position]
            has_first_dash = "—" in before_dash
            if has_first_dash:
                return True

        return False

    def _is_emphasis_context(self, doc: Any, _dash_pos: int, _full_text: str, _position: int) -> bool:
        """Use SpaCy patterns to detect emphasis."""
        # Find the dash token in the document
        dash_token = None
        for token in doc:
            if token.text == "—":
                dash_token = token
                break

        if not dash_token:
            return False

        # Get tokens before and after dash
        before_token = None
        after_token = None
        for i, token in enumerate(doc):
            if token == dash_token:
                if i > 0:
                    before_token = doc[i - 1]
                if i < len(doc) - 1:
                    after_token = doc[i + 1]
                break

        # Heuristic: If dash is between two single-letter tokens (likely variables), do not treat as emphasis
        if before_token and after_token:
            if len(before_token.text) == 1 and len(after_token.text) == 1:
                # Also check that both are alpha or both are noun/proper noun/symbol
                if (before_token.text.isalpha() and after_token.text.isalpha()) or (
                    before_token.pos_ in ["NOUN", "PROPN", "SYM", "X"]
                    and after_token.pos_ in ["NOUN", "PROPN", "SYM", "X"]
                ):
                    return False

        # Get tokens after dash
        after_tokens = [t for t in doc if t.i > dash_token.i][:5]

        # High confidence signals from pattern analysis
        # Only trigger if the FIRST token after dash is an adverb ending in -ly or an adjective
        if after_tokens:
            first_after = after_tokens[0]
            if first_after.pos_ == "ADV" and first_after.text.lower().endswith("ly"):
                return True
            if first_after.pos_ == "ADJ":
                return True

        # Secondary pattern: if the 2nd token after dash is an adverb ending in -ly or adjective,
        # but only if the first is a comma or punctuation
        if len(after_tokens) > 1:
            if after_tokens[0].pos_ == "PUNCT":
                second = after_tokens[1]
                if second.pos_ == "ADV" and second.text.lower().endswith("ly"):
                    return True
                if second.pos_ == "ADJ":
                    return True

        # Emphasis pattern: preposition + adverb (like "at last")
        if len(after_tokens) > 1:
            if after_tokens[0].pos_ == "ADP" and after_tokens[1].pos_ == "ADV":
                return True

        return False

    def _is_list_context(self, doc: Any, _dash_pos: int, _full_text: str, _position: int) -> bool:
        """Use SpaCy patterns to detect list contexts."""
        # Find the dash token in the document
        dash_token = None
        for token in doc:
            if token.text == "—":
                dash_token = token
                break

        if not dash_token:
            return False

        # Get tokens before and after dash
        before_token = None
        after_token = None
        for i, token in enumerate(doc):
            if token == dash_token:
                if i > 0:
                    before_token = doc[i - 1]
                if i < len(doc) - 1:
                    after_token = doc[i + 1]
                break

        # Heuristic: If dash is between two single-letter tokens (likely variables or abbreviations),
        # do not treat as list
        if before_token and after_token:
            if len(before_token.text) == 1 and len(after_token.text) == 1:
                # Also check that both are alpha or both are noun/proper noun/symbol
                if (before_token.text.isalpha() and after_token.text.isalpha()) or (
                    before_token.pos_ in ["NOUN", "PROPN", "SYM", "X"]
                    and after_token.pos_ in ["NOUN", "PROPN", "SYM", "X"]
                ):
                    return False
            # Also, if both are proper nouns (e.g., names or abbreviations)
            if before_token.pos_ == "PROPN" and after_token.pos_ == "PROPN":
                return False

        # Get tokens after dash
        after_tokens = [t for t in doc if t.i > dash_token.i][:10]

        # High confidence signals from pattern analysis
        has_noun_after = any(t.pos_ == "NOUN" for t in after_tokens)
        has_punctuation_after = any(t.pos_ == "PUNCT" for t in after_tokens)
        has_adjective_after = any(t.pos_ == "ADJ" for t in after_tokens)

        # Count commas (list separators)
        comma_count = sum(1 for t in after_tokens if t.text == ",")

        # List detection: noun after + multiple commas (high confidence)
        if has_noun_after and comma_count >= 2:
            return True

        # Secondary pattern: noun + adjective + punctuation
        if has_noun_after and has_adjective_after and has_punctuation_after:
            return True

        return False

    def _log_decision(self, context_type: str, confidence: float) -> None:
        """Log the decision for analysis."""
        context_types = self.stats["context_types"]
        context_types[context_type] = context_types.get(context_type, 0) + 1
        confidence_scores = self.stats["confidence_scores"]
        confidence_scores.append(confidence)

        if confidence > 0.7:
            spacy_decisions = self.stats.get("spacy_decisions", 0)
            self.stats["spacy_decisions"] = spacy_decisions + 1
        else:
            fallback_decisions = self.stats.get("fallback_decisions", 0)
            self.stats["fallback_decisions"] = fallback_decisions + 1

    def _save_stats(self) -> None:
        """Save statistics to file."""
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2)
        except Exception:  # pylint: disable=broad-except
            pass  # Ignore file write errors

    def print_stats(self) -> None:
        """Print current statistics."""
        total = self.stats.get("total_dashes", 0)
        if total == 0:
            print("No statistics available yet.")
            return

        print("\n📊 SpaCy-First NLP Statistics:")
        print(f"Total dashes processed: {total}")
        spacy_decisions = self.stats.get("spacy_decisions", 0)
        spacy_pct = spacy_decisions / total * 100
        print(f"High-confidence decisions: {spacy_decisions} ({spacy_pct:.1f}%)")

        fallback_decisions = self.stats.get("fallback_decisions", 0)
        fallback_pct = fallback_decisions / total * 100
        print(f"Fallback decisions: {fallback_decisions} ({fallback_pct:.1f}%)")

        print("\nContext types:")
        context_types = self.stats.get("context_types", {})
        for context_type, count in context_types.items():
            pct = count / total * 100
            print(f"  {context_type}: {count} ({pct:.1f}%)")

        confidence_scores = self.stats.get("confidence_scores", [1])
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        print(f"\nAverage confidence: {avg_confidence:.2f}")


class _ProcessorSingleton:
    """Singleton pattern for NLP processor."""

    _instance: Optional[SpacyNLPProcessor] = None

    @classmethod
    def get_instance(cls) -> SpacyNLPProcessor:
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = SpacyNLPProcessor()
        return cls._instance


def get_nlp_processor() -> SpacyNLPProcessor:
    """Get the NLP processor instance."""
    return _ProcessorSingleton.get_instance()


def get_dash_replacement_nlp(text: str, position: int) -> Tuple[str, int]:
    """
    Get EM dash replacement using spaCy-first NLP analysis.
    Handles all whitespace normalization/stripping for contextual replacements.
    Returns:
        Tuple[str, int]: (replacement_text, new_position)
        - replacement_text: The text to append to output (whitespace handled)
        - new_position: The position to continue processing from
    """
    processor = get_nlp_processor()
    replacement = processor.get_dash_replacement(text, position)

    if replacement == ", ":
        # Find end of whitespace after dash
        end = position + 1
        while end < len(text) and text[end].isspace():
            end += 1
        # Always return ', ' (comma + single space), never a space before the comma
        return ", ", end
    return replacement, position + 1


def get_nlp_stats() -> Dict[str, Any]:
    """Get NLP processing statistics."""
    processor = get_nlp_processor()
    return processor.stats.copy()
