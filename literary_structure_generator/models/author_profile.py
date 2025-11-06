"""
AuthorProfile Pydantic model

User voice preferences, lexicon constraints, and style settings.
Can be learned from user's own writing or manually configured.

Schema version: AuthorProfile@1

Used to blend exemplar style with user's personal voice.
"""

from pydantic import BaseModel, Field


class Lexicon(BaseModel):
    """Lexical preferences."""

    prefer: list[str] = Field(default_factory=list, description="Preferred word types or patterns")
    avoid: list[str] = Field(default_factory=list, description="Words or patterns to avoid")


class Syntax(BaseModel):
    """Syntactic preferences."""

    avg_sentence_len: int = Field(default=14, description="Average sentence length in words")
    variance: float = Field(default=0.55, description="Sentence length variance")
    em_dash: str = Field(default="rare", description="Em-dash usage: rare|moderate|frequent")


class Register(BaseModel):
    """Register and tone sliders."""

    deadpan: float = Field(default=0.7, description="Deadpan vs expressive (0-1)")
    tender: float = Field(default=0.6, description="Tender vs harsh (0-1)")
    irony: float = Field(default=0.4, description="Ironic vs sincere (0-1)")


class Profanity(BaseModel):
    """Profanity policy."""

    allowed: bool = Field(default=False, description="Whether profanity is allowed")
    frequency: float = Field(default=0.0, description="Target profanity frequency (0-1)")


class AuthorProfile(BaseModel):
    """
    AuthorProfile@1 schema

    User voice preferences and style constraints.
    Can be manually configured or learned from user's writing samples.
    Blended with exemplar style to create personalized StorySpec.
    """

    schema_version: str = Field(
        default="AuthorProfile@1", description="Schema version identifier", alias="schema"
    )
    lexicon: Lexicon = Field(default_factory=Lexicon, description="Lexical preferences")
    syntax: Syntax = Field(default_factory=Syntax, description="Syntactic preferences")
    register_sliders: Register = Field(
        default_factory=Register, description="Register and tone", alias="register"
    )
    profanity: Profanity = Field(default_factory=Profanity, description="Profanity policy")

    class Config:
        """Pydantic config."""

        populate_by_name = True

        json_schema_extra = {
            "example": {
                "schema": "AuthorProfile@1",
                "lexicon": {
                    "prefer": ["plain nouns", "everyday verbs"],
                    "avoid": ["generally", "very"],
                },
                "syntax": {"avg_sentence_len": 14, "variance": 0.55, "em_dash": "rare"},
                "register": {"deadpan": 0.7, "tender": 0.6, "irony": 0.4},
                "profanity": {"allowed": False, "frequency": 0.0},
            }
        }
