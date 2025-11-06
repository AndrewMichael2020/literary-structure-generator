"""
Universal profanity handling with structural [bleep] replacement.

Provides consistent profanity filtering across all outputs, replacing
detected profanity with [bleep] while preserving rhythm and tone.
"""

import re

# Comprehensive profanity list for filtering
PROFANITY_LIST = [
    "fuck",
    "fucking",
    "fucked",
    "fucker",
    "shit",
    "shitting",
    "shitty",
    "bitch",
    "bitching",
    "asshole",
    "bastard",
    "cunt",
    "damn",
    "damned",
    "hell",
    "ass",
    "crap",
]


def structural_bleep(text: str, substitution: str = "[bleep]") -> str:
    """
    Replace profanity with structural bleeps while preserving rhythm.

    Applies case-sensitive replacement with word boundaries to ensure
    accurate filtering without affecting non-profane words containing
    profane substrings.

    Args:
        text: Input text to filter
        substitution: Replacement string (default: "[bleep]")

    Returns:
        Filtered text with profanity replaced

    Examples:
        >>> structural_bleep("This is fucking great!")
        'This is [bleep] great!'
        >>> structural_bleep("What the hell is this?")
        'What the [bleep] is this?'
        >>> structural_bleep("assessment", "[bleep]")
        'assessment'  # Not affected - contains "ass" but not as word
    """
    if not text:
        return text

    # Build regex pattern with word boundaries
    # Case-insensitive matching to catch all variations
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(word) for word in PROFANITY_LIST) + r")\b",
        re.IGNORECASE,
    )

    # Replace with substitution
    return pattern.sub(substitution, text)


def count_bleeps(text: str) -> int:
    """
    Count profanity instances in text.

    Args:
        text: Input text to analyze

    Returns:
        Number of profanity instances found
    """
    if not text:
        return 0

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(word) for word in PROFANITY_LIST) + r")\b",
        re.IGNORECASE,
    )
    matches = pattern.findall(text)
    return len(matches)


def apply_profanity_filter(
    text: str,
    enabled: bool = True,
    substitution: str = "[bleep]",
    log_replacements: bool = False,
) -> tuple[str, int | None]:
    """
    Apply profanity filter with optional logging.

    Args:
        text: Input text to filter
        enabled: Whether filtering is enabled (default: True)
        substitution: Replacement string (default: "[bleep]")
        log_replacements: Whether to return count of replacements

    Returns:
        Tuple of (filtered_text, num_replacements)
        num_replacements is None if log_replacements is False
    """
    if not enabled:
        return text, None

    count = count_bleeps(text) if log_replacements else None
    filtered = structural_bleep(text, substitution)

    return filtered, count
