"""
AuthorProfile Learner

Learn AuthorProfile from user's writing samples.
Analyzes user's texts to extract style preferences.

Blending modes:
    - Clean Mode: Blend exemplar with user style
    - Author-only: Extract profile from user texts only
    - Alpha blending: Weighted combination

Uses same analysis tools as ExemplarDigest.
"""

import re
from pathlib import Path

from literary_structure_generator.models.author_profile import (
    AuthorProfile,
    Profanity,
    Register,
    Syntax,
)
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.profiles.author_profile import save_profile


def _tokenize_sentences(text: str) -> list[str]:
    """Split text into sentences with a lightweight regex."""
    return [s.strip() for s in re.split(r"[.!?]+(?:\s+|$)", text) if s.strip()]


def _tokenize_words(text: str) -> list[str]:
    """Tokenize text into lowercase word tokens."""
    return re.findall(r"\b[\w']+\b", text.lower())


def _estimate_em_dash_usage(text: str, word_count: int) -> str:
    """Classify em-dash usage as rare, moderate, or frequent."""
    if word_count <= 0:
        return "rare"

    dash_count = text.count("—") + text.count("\u2013") + text.count("--")
    dashes_per_100 = (dash_count / word_count) * 100

    if dashes_per_100 >= 1.0:
        return "frequent"
    if dashes_per_100 >= 0.25:
        return "moderate"
    return "rare"


def analyze_user_texts(filepaths: list[str]) -> dict:
    """
    Analyze user's writing samples.

    Args:
        filepaths: List of paths to user's text files

    Returns:
        Dictionary with extracted style features
    """
    if not filepaths:
        raise ValueError("At least one user text filepath is required")

    combined_text_parts = []
    for filepath in filepaths:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"User text file not found: {filepath}")
        combined_text_parts.append(path.read_text(encoding="utf-8"))

    combined_text = "\n\n".join(combined_text_parts)
    sentences = _tokenize_sentences(combined_text)
    words = _tokenize_words(combined_text)

    sentence_lengths = [len(_tokenize_words(sentence)) for sentence in sentences]
    if sentence_lengths:
        avg_sentence_len = round(sum(sentence_lengths) / len(sentence_lengths))
        mean = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((length - mean) ** 2 for length in sentence_lengths) / len(sentence_lengths)
        normalized_variance = min(1.0, variance / 100.0)
    else:
        avg_sentence_len = 14
        normalized_variance = 0.55

    lower_text = combined_text.lower()
    irony_markers = ["sure", "obviously", "of course", "apparently"]
    tender_markers = ["gentle", "soft", "kind", "care", "held", "warm"]
    expressive_markers = ["!", "very", "really"]

    word_count = len(words)
    irony_score = (
        min(
            1.0, sum(lower_text.count(marker) for marker in irony_markers) / max(word_count, 1) * 20
        )
        if word_count
        else 0.4
    )
    tender_score = (
        min(
            1.0,
            sum(lower_text.count(marker) for marker in tender_markers) / max(word_count, 1) * 20,
        )
        if word_count
        else 0.6
    )
    expressive_score = (
        min(
            1.0,
            sum(lower_text.count(marker) for marker in expressive_markers)
            / max(word_count, 1)
            * 20,
        )
        if word_count
        else 0.3
    )

    return {
        "avg_sentence_len": avg_sentence_len,
        "sentence_variance": normalized_variance,
        "em_dash": _estimate_em_dash_usage(combined_text, word_count),
        "register": {
            "deadpan": max(0.0, min(1.0, 1.0 - expressive_score)),
            "tender": max(0.0, min(1.0, tender_score if tender_score > 0 else 0.6)),
            "irony": max(0.0, min(1.0, irony_score if irony_score > 0 else 0.4)),
        },
        "word_count": word_count,
        "file_count": len(filepaths),
    }


def extract_profile_from_analysis(analysis: dict) -> AuthorProfile:
    """
    Convert analysis results to AuthorProfile.

    Args:
        analysis: Style features from user texts

    Returns:
        AuthorProfile object
    """
    register = analysis.get("register", {})

    return AuthorProfile(
        syntax=Syntax(
            avg_sentence_len=int(analysis.get("avg_sentence_len", 14)),
            variance=float(analysis.get("sentence_variance", 0.55)),
            em_dash=str(analysis.get("em_dash", "rare")),
        ),
        register=Register(
            deadpan=float(register.get("deadpan", 0.7)),
            tender=float(register.get("tender", 0.6)),
            irony=float(register.get("irony", 0.4)),
        ),
        profanity=Profanity(allowed=False, frequency=0.0),
    )


def _average_sentence_length_from_digest(exemplar_digest: ExemplarDigest) -> int:
    """Estimate average sentence length from digest histogram."""
    histogram = exemplar_digest.stylometry.sentence_len_hist
    if not histogram or sum(histogram) == 0:
        return 14

    bucket_midpoints = [3, 8, 13, 18, 25, 35, 45, 63, 80]
    weighted_sum = sum(
        count * midpoint for count, midpoint in zip(histogram, bucket_midpoints, strict=False)
    )
    return round(weighted_sum / sum(histogram))


def blend_profiles(
    exemplar_digest: ExemplarDigest,
    user_profile: AuthorProfile,
    alpha_exemplar: float = 0.7,
) -> AuthorProfile:
    """
    Blend exemplar style with user profile.

    Args:
        exemplar_digest: Exemplar style features
        user_profile: User's profile
        alpha_exemplar: Weight for exemplar (0=all user, 1=all exemplar)

    Returns:
        Blended AuthorProfile
    """
    if not 0.0 <= alpha_exemplar <= 1.0:
        raise ValueError("alpha_exemplar must be between 0.0 and 1.0")

    exemplar_avg_sentence_len = _average_sentence_length_from_digest(exemplar_digest)
    blended_avg_sentence_len = round(
        alpha_exemplar * exemplar_avg_sentence_len
        + (1.0 - alpha_exemplar) * user_profile.syntax.avg_sentence_len
    )

    return AuthorProfile(
        lexicon=user_profile.lexicon,
        syntax=Syntax(
            avg_sentence_len=blended_avg_sentence_len,
            variance=user_profile.syntax.variance,
            em_dash=user_profile.syntax.em_dash,
        ),
        register=user_profile.register_sliders,
        profanity=user_profile.profanity,
    )


def learn_author_profile(
    user_filepaths: list[str],
    exemplar_digest: ExemplarDigest | None = None,
    alpha_exemplar: float = 0.7,
    output_path: str | None = None,
) -> AuthorProfile:
    """
    Main entry point: learn AuthorProfile from user's texts.

    Args:
        user_filepaths: List of paths to user's writing samples
        exemplar_digest: Optional ExemplarDigest to blend with
        alpha_exemplar: Blending weight (0=all user, 1=all exemplar)
        output_path: Optional path to save profile JSON

    Returns:
        Learned AuthorProfile
    """
    analysis = analyze_user_texts(user_filepaths)
    profile = extract_profile_from_analysis(analysis)

    if exemplar_digest is not None:
        profile = blend_profiles(exemplar_digest, profile, alpha_exemplar=alpha_exemplar)

    if output_path:
        save_profile(profile, output_path)

    return profile
