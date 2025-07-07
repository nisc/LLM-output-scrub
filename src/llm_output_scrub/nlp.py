"""
SpaCy-first NLP processor for EM dash replacement.
Uses linguistic features and POS tagging instead of hardcoded patterns.
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import spacy

__all__ = ["get_dash_replacement_nlp", "get_nlp_processor", "get_nlp_stats", "cleanup_nlp_processor"]


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
    """Dummy token for when we need to create tokens from text fragments."""

    def __init__(self, text: str, pos_: str):
        self.text = text
        self.pos_ = pos_
        self.is_alpha = text.isalpha()
        self.is_punct = not text.isalnum() and not text.isspace()
        self.like_num = text.replace(".", "").replace(",", "").isdigit()
        self.idx = 0  # Default index


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
        self._model_last_used: float = 0.0  # Track when model was last accessed
        self._cleanup_timer: Optional[threading.Timer] = None  # Timer for auto-cleanup
        self._model_lock = threading.Lock()  # Thread safety for model access

        # Set up stats file paths in user's config directory
        config_dir = Path.home() / ".llm_output_scrub"
        config_dir.mkdir(exist_ok=True)
        self.stats_file = config_dir / "nlp_stats.json"
        self.history_file = config_dir / "nlp_history.json"  # Detailed historical data

        # Initialize default stats (keep only counters in memory, no historical data)
        self.stats: Dict[str, Any] = {
            "total_dashes": 0,
            "context_types": {},  # Keep counts for quick access
            "spacy_decisions": 0,
            "fallback_decisions": 0,
            # Memory optimization tracking
            "model_loads": 0,
            "model_unloads": 0,
        }

        # Load existing stats from disk
        self._load_stats()

    def _load_stats(self) -> None:
        """Load statistics from disk if they exist."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    loaded_stats = json.load(f)
                    # Merge with defaults to handle missing keys
                    for key, value in loaded_stats.items():
                        if key in self.stats:
                            self.stats[key] = value

            except (json.JSONDecodeError, IOError):
                # If file is corrupted or unreadable, keep defaults
                pass

    def get_spacy_model(self) -> spacy.language.Language:
        """Get the spaCy model, loading it if necessary."""
        with self._model_lock:
            if self._nlp is None:
                self._nlp = get_nlp_model()
                self.stats["model_loads"] += 1  # Track model loads

            # Update last used time and schedule cleanup
            self._model_last_used = time.time()
            self._schedule_cleanup()

            return self._nlp

    def _schedule_cleanup(self) -> None:
        """Schedule model cleanup after 5 minutes of inactivity."""
        # Cancel existing timer if any
        if self._cleanup_timer is not None:
            self._cleanup_timer.cancel()

        # Schedule new cleanup in 5 minutes (300 seconds)
        self._cleanup_timer = threading.Timer(300.0, self._cleanup_model)
        self._cleanup_timer.daemon = True  # Don't block app shutdown
        self._cleanup_timer.start()

    def _cleanup_model(self) -> None:
        """Unload the spaCy model to free memory after inactivity."""
        with self._model_lock:
            # Check if model is still inactive (hasn't been used in last 5 minutes)
            if self._nlp is not None and time.time() - self._model_last_used >= 300:
                self._nlp = None  # Unload model, will be garbage collected
                self.stats["model_unloads"] += 1  # Track model unloads
                # Force garbage collection to free memory immediately
                import gc

                gc.collect()

    def cleanup(self) -> None:
        """Clean up resources before shutdown."""
        if self._cleanup_timer is not None:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None

        with self._model_lock:
            self._nlp = None

    def get_dash_replacement(self, text: str, position: int) -> str:
        """Get context-aware replacement for EM dash at given position."""
        self.stats["total_dashes"] += 1
        dash_char = "—"

        # Extract a reasonable context window around the dash (500 chars each side)
        # This reduces memory usage compared to processing the entire document
        context_start = max(0, position - 500)
        context_end = min(len(text), position + 500)
        context_text = text[context_start:context_end]
        dash_pos_in_context = position - context_start
        context_size = len(context_text)  # Track for historical logging only

        # Process only the context window instead of the full text
        context_doc = self.get_spacy_model()(context_text)
        sent, sent_start_in_context = self._find_sentence_containing_dash(context_doc, dash_pos_in_context)
        sent_text = sent.text
        dash_pos_in_sent = dash_pos_in_context - sent_start_in_context
        dashes_in_sent = [i for i, c in enumerate(sent_text) if c == dash_char]

        # Check for compound dash (single dash in sentence) - reuse sent doc
        compound_result = self._check_compound_dash(
            sent, sent_text, dashes_in_sent, dash_pos_in_sent, dash_char
        )
        if compound_result is not None:
            self._log_decision(compound_result[1], compound_result[2], context_size)
            return compound_result[0]

        # Check for parenthetical dash (multiple dashes in sentence) - reuse sent doc
        parenthetical_result = self._check_parenthetical_dash(
            sent, sent_text, dashes_in_sent, dash_pos_in_sent, dash_char
        )
        if parenthetical_result is not None:
            self._log_decision(parenthetical_result[1], parenthetical_result[2], context_size)
            return parenthetical_result[0]

        # Final contextual analysis using the smaller context
        final_result = self._get_final_replacement_optimized(
            context_doc, dash_pos_in_context, text, position, context_size
        )
        return final_result

    def _find_sentence_containing_dash(self, doc: Any, position: int) -> Tuple[Any, int]:
        """Find the sentence containing the dash at the given position."""
        for s in doc.sents:
            sent_start = doc[s.start].idx
            sent_end = doc[s.end - 1].idx + len(doc[s.end - 1])
            if sent_start <= position < sent_end:
                return s, sent_start
        # If not found in any sentence, return the whole document
        return doc, 0

    def _check_compound_dash(
        self, sent: Any, sent_text: str, dashes_in_sent: List[int], dash_pos_in_sent: int, dash_char: str
    ) -> Optional[Tuple[str, str, float]]:
        """Check if this is a compound dash case. Returns (replacement, context_type, confidence) or None."""
        # Compound dash: only if both sides are a single token, not proper nouns,
        # not surrounded by whitespace or punctuation
        # AND only if there's exactly one dash in the sentence (not a parenthetical pair)
        if len(dashes_in_sent) != 1:
            return None

        sent_doc = sent
        dash_token_idx = None
        for i, token in enumerate(sent_doc):
            if token.text == dash_char:
                dash_token_idx = i
                break

        if dash_token_idx is None or dash_token_idx == 0 or dash_token_idx >= len(sent_doc) - 1:
            return None

        before_token = sent_doc[dash_token_idx - 1]
        after_token = sent_doc[dash_token_idx + 1]

        # If after_token is a CCONJ or PROPN, treat as parenthetical/attribution (comma)
        if after_token.pos_ == "CCONJ" or after_token.pos_ == "PROPN":
            return (", ", "conjunction_or_attribution", 0.85)

        # Accept as compound if both tokens are alphabetic and <= 3 chars (regardless of POS)
        if (
            before_token.is_alpha
            and after_token.is_alpha
            and len(before_token.text) <= 3
            and len(after_token.text) <= 3
        ):
            return ("-", "compound", 0.95)

        # Accept as compound if one side is a prefix/suffix (e.g., 'pre—existing', 'self—driving')
        if (
            before_token.is_alpha
            and after_token.is_alpha
            and (len(before_token.text) <= 5 or len(after_token.text) <= 5)
        ):
            if before_token.pos_ not in ["PROPN", "ADV", "CCONJ"] and after_token.pos_ not in [
                "PROPN",
                "ADV",
                "CCONJ",
            ]:
                return ("-", "compound", 0.93)

        return None

    def _check_parenthetical_dash(
        self, sent: Any, sent_text: str, dashes_in_sent: List[int], dash_pos_in_sent: int, dash_char: str
    ) -> Optional[Tuple[str, str, float]]:
        """Check if this is a parenthetical dash case.

        Returns (replacement, context_type, confidence) or None.
        """
        # Parenthetical/emphasis: if there is a matching dash in the sentence and the tokens between are not
        # just single words
        if len(dashes_in_sent) < 2:
            return None

        # Check right dashes
        right_dashes = [i for i in dashes_in_sent if i > dash_pos_in_sent]
        if right_dashes:
            closing_dash_pos = right_dashes[0]
            between_text = sent_text[dash_pos_in_sent + 1 : closing_dash_pos]
            if self._is_parenthetical_content_optimized(sent, between_text):
                return (", ", "parenthetical_pair", 0.85)

        # Check left dashes
        left_dashes = [i for i in dashes_in_sent if i < dash_pos_in_sent]
        if left_dashes:
            opening_dash_pos = left_dashes[-1]
            between_text = sent_text[opening_dash_pos + 1 : dash_pos_in_sent]
            if self._is_parenthetical_content_optimized(sent, between_text):
                return (", ", "parenthetical_pair", 0.85)

        return None

    def _is_parenthetical_content_optimized(self, sent_doc: Any, between_text: str) -> bool:
        """Check if the text between dashes is parenthetical content using existing doc."""
        # Strip whitespace for robust matching
        between_text_stripped = between_text.strip()
        between_start = sent_doc.text.find(between_text_stripped)

        if between_start == -1:
            # Fallback: create new doc only if we can't find the text in the sentence
            return self._is_parenthetical_content(between_text_stripped)

        between_end = between_start + len(between_text_stripped)

        # Get the sentence offset within the full document
        sentence_offset = sent_doc[0].idx if len(sent_doc) > 0 else 0

        # Adjust the between_start and between_end to be relative to the full document
        adjusted_between_start = sentence_offset + between_start
        adjusted_between_end = sentence_offset + between_end

        between_tokens = [
            t
            for t in sent_doc
            if t.idx >= adjusted_between_start and t.idx + len(t.text) <= adjusted_between_end
        ]

        # Filter out punctuation tokens
        non_punct_tokens = [t for t in between_tokens if not t.is_punct and t.text.strip()]

        # Parenthetical/emphasis: more than one token, or single adverb/adjective
        result = len(non_punct_tokens) > 1 or (
            len(non_punct_tokens) == 1
            and non_punct_tokens[0].pos_ in ["ADV", "ADJ"]
            and len(non_punct_tokens[0].text) > 2
        )
        return result

    def _is_parenthetical_content(self, text: str) -> bool:
        """Check if the text between dashes is parenthetical content (fallback method)."""
        between_doc = self.get_spacy_model()(text)
        non_punct_tokens = [t for t in between_doc if not t.is_punct and t.text.strip()]

        # Parenthetical/emphasis: more than one token, or single adverb/adjective
        result = len(non_punct_tokens) > 1 or (
            len(non_punct_tokens) == 1
            and non_punct_tokens[0].pos_ in ["ADV", "ADJ"]
            and len(non_punct_tokens[0].text) > 2
        )
        return result

    def _get_final_replacement_optimized(
        self, doc: Any, dash_pos_in_doc: int, full_text: str, original_position: int, context_size: int
    ) -> str:
        """Get final replacement using optimized context analysis."""
        # Use the helper method to find dash token and context
        dash_token, dash_token_idx, before_token, after_token = self._find_dash_token_and_context(doc)

        if dash_token is None:
            return "-"

        # Robust fallback: if sentence contains >1 EM dash, treat as parenthetical
        sent_text = doc.text
        dash_indices = []
        for i, c in enumerate(sent_text):
            if c == "—":
                dash_indices.append(i)

        # If there are multiple dashes, any dash that has another dash before or after it is parenthetical
        if len(dash_indices) > 1:
            # Find the character position of this dash in the sentence text
            if dash_token and dash_token.text == "—" and dash_token_idx is not None:
                # Get the character position of this token in the sentence
                char_pos_in_sent = dash_token.idx

                # Check if this dash has another dash before or after it
                has_other_dash_before = any(idx < char_pos_in_sent for idx in dash_indices)
                has_other_dash_after = any(idx > char_pos_in_sent for idx in dash_indices)

                if has_other_dash_before or has_other_dash_after:
                    self._log_decision(
                        "parenthetical_fallback",
                        0.70,
                        context_size,
                    )
                    return ", "

        # Dialogue attribution: quote before dash and proper noun after dash
        if self._is_dialogue_context(doc, dash_pos_in_doc, full_text, original_position):
            self._log_decision("dialogue_attribution", 0.80, context_size)
            return ", "

        # Range/connection: two numbers or dates
        if before_token and after_token:
            if before_token.like_num and after_token.like_num:
                self._log_decision("numeric_range", 0.90, context_size)
                return "-"

        # Emphasis: single word or short phrase
        if before_token and after_token:
            if (
                before_token.is_alpha
                and after_token.is_alpha
                and len(before_token.text) <= 3
                and len(after_token.text) <= 3
            ):
                self._log_decision("emphasis", 0.75, context_size)
                return ", "

        # Default to hyphen for unknown cases
        self._log_decision("unknown", 0.50, context_size)
        return "-"

    def _find_dash_token_and_context(
        self, doc: Any
    ) -> Tuple[Optional[Any], Optional[int], Optional[Any], Optional[Any]]:
        """Find the dash token and its surrounding context in a document.

        Returns (dash_token, dash_token_idx, before_token, after_token)
        """
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
            return None, None, None, None

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

        return dash_token, dash_token_idx, before_token, after_token

    def _is_dialogue_context(self, doc: Any, _dash_pos: int, full_text: str, position: int) -> bool:
        """Use SpaCy patterns to detect dialogue attribution."""
        dash_token, dash_token_idx, before_token, after_token = self._find_dash_token_and_context(doc)

        if dash_token is None:
            return False

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

    def _log_decision(self, context_type: str, confidence: float, context_size: int) -> None:
        """Log the decision for analysis."""
        context_types = self.stats["context_types"]
        context_types[context_type] = context_types.get(context_type, 0) + 1

        if confidence > 0.7:
            spacy_decisions = self.stats.get("spacy_decisions", 0)
            self.stats["spacy_decisions"] = spacy_decisions + 1
        else:
            fallback_decisions = self.stats.get("fallback_decisions", 0)
            self.stats["fallback_decisions"] = fallback_decisions + 1

        # Save to historical file for comprehensive data
        self._save_historical_entry(context_type, confidence, context_size)

    def _save_historical_entry(self, context_type: str, confidence: float, context_size: int = 0) -> None:
        """Save detailed historical entry to disk."""
        try:
            # Load existing history
            history = []
            if self.history_file.exists():
                try:
                    with open(self.history_file, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except (json.JSONDecodeError, IOError):
                    history = []

            # Add new entry with timestamp
            entry = {
                "timestamp": time.time(),
                "context_type": context_type,
                "confidence": confidence,
                "context_size": context_size,  # Track context window size here instead of in memory
            }
            history.append(entry)

            # Keep ALL historical entries (no limit) - preserve complete history from first launch
            # Only limit would be disk space, but these entries are tiny (~100 bytes each)

            # Save back to file
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)

        except Exception:  # pylint: disable=broad-except
            pass  # Ignore file write errors

    def _save_stats(self) -> None:
        """Save statistics to file."""
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2)
        except Exception:  # pylint: disable=broad-except
            pass  # Ignore file write errors

    def print_stats(self) -> None:
        """Print comprehensive statistics loaded from disk."""
        # Load comprehensive stats from disk
        comprehensive_stats = self._load_comprehensive_stats()

        total = comprehensive_stats.get("total_dashes", 0)
        if total == 0:
            print("No statistics available yet.")
            return

        print("\n📊 SpaCy-First NLP Statistics (Comprehensive):")
        print(f"Total dashes processed: {total}")

        # Historical data info
        total_historical = comprehensive_stats.get("total_historical_entries", 0)
        if total_historical > 0:
            print(f"Historical entries: {total_historical}")
            timespan = comprehensive_stats.get("data_timespan_days", 0)
            if timespan > 0:
                print(f"Data spans: {timespan:.1f} days")

        spacy_decisions = comprehensive_stats.get("spacy_decisions", 0)
        spacy_pct = spacy_decisions / total * 100
        print(f"High-confidence decisions: {spacy_decisions} ({spacy_pct:.1f}%)")

        fallback_decisions = comprehensive_stats.get("fallback_decisions", 0)
        fallback_pct = fallback_decisions / total * 100
        print(f"Fallback decisions: {fallback_decisions} ({fallback_pct:.1f}%)")

        print("\nContext types (comprehensive):")
        context_types = comprehensive_stats.get("context_types", {})
        for context_type, count in context_types.items():
            pct = count / total * 100
            print(f"  {context_type}: {count} ({pct:.1f}%)")

        confidence_scores = comprehensive_stats.get("confidence_scores", [1])
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            print(f"\nAverage confidence: {avg_confidence:.2f}")
            print(f"Total confidence entries: {len(confidence_scores)}")

        # Memory optimization metrics
        print("\n🧠 Memory Optimization:")
        model_loads = comprehensive_stats.get("model_loads", 0)
        model_unloads = comprehensive_stats.get("model_unloads", 0)
        print(f"Model loads: {model_loads}")
        print(f"Model unloads: {model_unloads}")

        # Context window analysis from historical data
        context_sizes = comprehensive_stats.get("context_window_sizes", [])
        if context_sizes:
            avg_context_size = sum(context_sizes) / len(context_sizes)
            max_context_size = max(context_sizes)
            print(f"Avg context window size: {avg_context_size:.0f} chars")
            print(f"Max context window size: {max_context_size} chars")
            memory_saved_pct = (10000 - avg_context_size) / 10000 * 100
            print(f"Memory saved vs. full document processing: ~{memory_saved_pct:.1f}%*")
            print("  * Estimated based on 10KB average document size")

        print("\n💾 Memory Usage:")
        print("In-memory data: Only counters (context_types, totals)")
        print("Historical data: All stored on disk")
        print(f"Total historical entries on disk: {total_historical}")

    def _load_comprehensive_stats(self) -> Dict[str, Any]:
        """Load comprehensive statistics from disk for display purposes."""
        comprehensive_stats = self.stats.copy()

        # Load historical data
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)

                # Build comprehensive statistics from history
                all_confidence_scores = [entry["confidence"] for entry in history]
                all_context_types: Dict[str, int] = {}
                all_context_sizes = []

                for entry in history:
                    context_type = entry["context_type"]
                    all_context_types[context_type] = all_context_types.get(context_type, 0) + 1

                    # Extract context sizes (may not exist in older entries)
                    if "context_size" in entry and entry["context_size"] > 0:
                        all_context_sizes.append(entry["context_size"])

                # Update comprehensive stats
                comprehensive_stats["confidence_scores"] = all_confidence_scores
                comprehensive_stats["context_types"] = all_context_types
                comprehensive_stats["context_window_sizes"] = all_context_sizes
                comprehensive_stats["total_historical_entries"] = len(history)

                # Add time-based analysis
                if history:
                    first_entry = min(entry["timestamp"] for entry in history)
                    last_entry = max(entry["timestamp"] for entry in history)
                    comprehensive_stats["data_timespan_days"] = (last_entry - first_entry) / (24 * 3600)

            except (json.JSONDecodeError, IOError):
                pass  # Use current stats if historical data unavailable

        return comprehensive_stats


class _ProcessorSingleton:
    """Singleton pattern for NLP processor."""

    _instance: Optional[SpacyNLPProcessor] = None

    @classmethod
    def get_instance(cls) -> SpacyNLPProcessor:
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = SpacyNLPProcessor()
        return cls._instance

    @classmethod
    def cleanup(cls) -> None:
        """Clean up the singleton instance."""
        if cls._instance is not None:
            cls._instance.cleanup()
            cls._instance = None


def get_nlp_processor() -> SpacyNLPProcessor:
    """Get the NLP processor instance."""
    return _ProcessorSingleton.get_instance()


def cleanup_nlp_processor() -> None:
    """Clean up the NLP processor to free memory."""
    _ProcessorSingleton.cleanup()


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
