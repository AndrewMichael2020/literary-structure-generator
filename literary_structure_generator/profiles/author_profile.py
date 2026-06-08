"""
AuthorProfile utilities

Load, save, and validate AuthorProfile objects.
Provides helper functions for profile management.
"""

from literary_structure_generator.models.author_profile import AuthorProfile
from literary_structure_generator.utils.io_utils import load_json, save_json


def load_profile(filepath: str) -> AuthorProfile:
    """
    Load AuthorProfile from JSON file.

    Args:
        filepath: Path to profile JSON

    Returns:
        AuthorProfile object
    """
    profile = load_json(filepath, AuthorProfile)
    validate_profile(profile)
    return profile


def save_profile(profile: AuthorProfile, filepath: str) -> None:
    """
    Save AuthorProfile to JSON file.

    Args:
        profile: AuthorProfile object
        filepath: Path to save profile JSON
    """
    validate_profile(profile)
    save_json(profile, filepath)


def create_default_profile() -> AuthorProfile:
    """
    Create a default AuthorProfile with conservative settings.

    Returns:
        Default AuthorProfile object
    """
    return AuthorProfile()


def validate_profile(profile: AuthorProfile) -> bool:
    """
    Validate AuthorProfile for consistency.

    Args:
        profile: AuthorProfile to validate

    Returns:
        True if valid, raises exception otherwise
    """
    if profile.schema_version != "AuthorProfile@1":
        raise ValueError(f"Unsupported AuthorProfile schema: {profile.schema_version}")

    if profile.syntax.avg_sentence_len <= 0:
        raise ValueError("profile.syntax.avg_sentence_len must be positive")

    if profile.syntax.variance < 0:
        raise ValueError("profile.syntax.variance must be non-negative")

    allowed_dash_settings = {"rare", "moderate", "frequent"}
    if profile.syntax.em_dash not in allowed_dash_settings:
        raise ValueError(
            "profile.syntax.em_dash must be one of: "
            f"{', '.join(sorted(allowed_dash_settings))}"
        )

    sliders = profile.register_sliders.model_dump()
    for name, value in sliders.items():
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"profile.register.{name} must be between 0.0 and 1.0")

    if not 0.0 <= profile.profanity.frequency <= 1.0:
        raise ValueError("profile.profanity.frequency must be between 0.0 and 1.0")

    if not profile.profanity.allowed and profile.profanity.frequency > 0:
        raise ValueError(
            "profile.profanity.frequency must be 0.0 when profile.profanity.allowed is False"
        )

    return True
