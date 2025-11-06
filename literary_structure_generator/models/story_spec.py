"""
StorySpec Pydantic model

Represents a complete, portable specification for story generation.
Combines voice, form, and content parameters with anti-plagiarism constraints.

Schema version: StorySpec@2

Used by the generator to produce candidate stories.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MetaInfo(BaseModel):
    """Metadata about the story specification."""

    story_id: str = Field(..., description="Unique identifier for this story")
    seed: int = Field(..., description="Random seed for reproducibility")
    version: str = Field(default="2.0", description="Spec version")
    derived_from: Dict[str, Any] = Field(
        default_factory=dict, description="Source exemplar and digest version"
    )


class DialogueStyle(BaseModel):
    """Dialogue formatting preferences."""

    quote_marks: str = Field(default="double", description="Quote mark style")
    tag_verbs_allowed: List[str] = Field(
        default_factory=lambda: ["said", "asked"], description="Allowed dialogue tag verbs"
    )
    ban_adverbs_after_tags: bool = Field(
        default=True, description="Whether to ban adverbs after dialogue tags"
    )
    beats_per_dialogue: Dict[str, int] = Field(
        default_factory=lambda: {"min": 0, "max": 2},
        description="Min/max action beats per dialogue line",
    )


class Syntax(BaseModel):
    """Syntactic preferences."""

    avg_sentence_len: int = Field(default=15, description="Average sentence length in words")
    variance: float = Field(default=0.6, description="Sentence length variance")
    fragment_ok: bool = Field(default=True, description="Whether sentence fragments are allowed")
    parataxis_vs_hypotaxis: float = Field(
        default=0.7, description="Ratio of parataxis to hypotaxis (0=hypotactic, 1=paratactic)"
    )
    comma_density: float = Field(default=0.55, description="Comma frequency per sentence")
    em_dash: str = Field(default="rare", description="Em-dash usage: rare|moderate|frequent")
    semicolon_ok: bool = Field(default=False, description="Whether semicolons are allowed")


class Diction(BaseModel):
    """Lexical preferences."""

    concrete: float = Field(default=0.7, description="Concreteness ratio (0-1)")
    abstract: float = Field(default=0.3, description="Abstractness ratio (0-1)")
    slang: float = Field(default=0.2, description="Slang usage ratio (0-1)")
    medical: float = Field(default=0.0, description="Medical terminology ratio (0-1)")
    latinate: float = Field(default=0.2, description="Latinate vocabulary ratio (0-1)")
    anglo: float = Field(default=0.8, description="Anglo-Saxon vocabulary ratio (0-1)")


class Profanity(BaseModel):
    """Profanity policy."""

    allowed: bool = Field(default=False, description="Whether profanity is allowed")
    frequency: float = Field(default=0.0, description="Target profanity frequency (0-1)")


class TenseStrategy(BaseModel):
    """Tense and temporal strategy."""

    primary: str = Field(default="past", description="Primary tense")
    allows_flashback: bool = Field(default=True, description="Whether flashbacks are allowed")
    flashback_marker_style: str = Field(
        default="line-break+temporal cue", description="How flashbacks are marked"
    )


class Voice(BaseModel):
    """Voice and narrative style parameters."""

    person: str = Field(
        default="first", description="Narrative person: first|second|third-limited|omniscient"
    )
    tense_strategy: TenseStrategy = Field(
        default_factory=TenseStrategy, description="Tense strategy"
    )
    distance: str = Field(
        default="intimate", description="Narrative distance: intimate|close|medium|distant"
    )
    register_sliders: Dict[str, float] = Field(
        default_factory=lambda: {"lyric": 0.3, "deadpan": 0.7, "irony": 0.5, "tender": 0.6},
        description="Register sliders (0-1)",
        alias="register",
    )
    syntax: Syntax = Field(default_factory=Syntax, description="Syntactic preferences")
    diction: Diction = Field(default_factory=Diction, description="Lexical preferences")
    dialogue_style: DialogueStyle = Field(
        default_factory=DialogueStyle, description="Dialogue formatting"
    )
    profanity: Profanity = Field(default_factory=Profanity, description="Profanity policy")


class BeatSpec(BaseModel):
    """Specification for a single story beat."""

    id: str = Field(..., description="Beat identifier")
    target_words: int = Field(..., description="Target word count for this beat")
    function: str = Field(..., description="Narrative function")
    cadence: str = Field(..., description="Cadence: short|mixed|long")


class TimeWeave(BaseModel):
    """Temporal structure preferences."""

    chronology: str = Field(default="loose", description="Chronological structure")
    analepsis_budget: int = Field(default=2, description="Number of flashbacks allowed")
    prolepsis_budget: int = Field(default=0, description="Number of flash-forwards allowed")


class Viewpoint(BaseModel):
    """Viewpoint/POV preferences."""

    fixed: bool = Field(default=True, description="Whether POV is fixed")
    allowed_shifts: List[str] = Field(
        default_factory=list, description="Allowed POV shift points"
    )


class Paragraphing(BaseModel):
    """Paragraph structure preferences."""

    avg_len_tokens: int = Field(default=45, description="Average paragraph length in tokens")
    variance: float = Field(default=0.4, description="Paragraph length variance")


class Form(BaseModel):
    """Form and structure parameters."""

    structure: str = Field(default="episodic", description="Overall structure type")
    beat_map: List[BeatSpec] = Field(default_factory=list, description="Beat specifications")
    scene_ratio: Dict[str, float] = Field(
        default_factory=lambda: {"scene": 0.7, "summary": 0.3},
        description="Scene vs summary ratio",
    )
    dialogue_ratio: float = Field(default=0.25, description="Target dialogue ratio")
    time_weave: TimeWeave = Field(default_factory=TimeWeave, description="Temporal structure")
    viewpoint: Viewpoint = Field(default_factory=Viewpoint, description="Viewpoint preferences")
    paragraphing: Paragraphing = Field(
        default_factory=Paragraphing, description="Paragraph structure"
    )
    transitions: List[str] = Field(
        default_factory=list, description="Preferred transition types"
    )


class Character(BaseModel):
    """Character specification."""

    name: str = Field(..., description="Character name or role")
    role: str = Field(..., description="Narrative role")
    goal: str = Field(default="", description="Character goal")
    wound: str = Field(default="", description="Character wound or flaw")
    quirks: List[str] = Field(default_factory=list, description="Character quirks")
    diction_quirks: List[str] = Field(default_factory=list, description="Speech patterns")


class Setting(BaseModel):
    """Setting specification."""

    place: str = Field(..., description="Location")
    time: str = Field(..., description="Time period or seasonal marker")
    weather_budget: List[str] = Field(default_factory=list, description="Allowed weather elements")


class SensoryQuotas(BaseModel):
    """Sensory detail quotas."""

    visual: float = Field(default=0.4, description="Visual detail ratio")
    auditory: float = Field(default=0.2, description="Auditory detail ratio")
    tactile: float = Field(default=0.2, description="Tactile detail ratio")
    olfactory: float = Field(default=0.1, description="Olfactory detail ratio")
    gustatory: float = Field(default=0.1, description="Gustatory detail ratio")


class SymbolBudget(BaseModel):
    """Symbol usage constraints."""

    max_new_symbols: int = Field(default=2, description="Maximum number of new symbols")


class Content(BaseModel):
    """Content parameters: setting, characters, themes."""

    setting: Setting = Field(..., description="Setting specification")
    characters: List[Character] = Field(default_factory=list, description="Character list")
    motifs: List[str] = Field(default_factory=list, description="Key motifs and themes")
    imagery_palette: List[str] = Field(default_factory=list, description="Imagery palette")
    symbol_budget: SymbolBudget = Field(
        default_factory=SymbolBudget, description="Symbol constraints"
    )
    props: List[str] = Field(default_factory=list, description="Important props")
    sensory_quotas: SensoryQuotas = Field(
        default_factory=SensoryQuotas, description="Sensory detail quotas"
    )


class AntiPlagiarism(BaseModel):
    """Anti-plagiarism constraints."""

    max_ngram: int = Field(default=12, description="Maximum shared n-gram length")
    overlap_pct: float = Field(default=0.03, description="Maximum overlap percentage")
    simhash_hamming_min: int = Field(default=18, description="Minimum SimHash Hamming distance")


class LengthConstraints(BaseModel):
    """Length constraints."""

    min: int = Field(default=1200, description="Minimum word count")
    target: int = Field(default=2000, description="Target word count")
    max: int = Field(default=2800, description="Maximum word count")


class SafetyLexicon(BaseModel):
    """Safety and content filtering."""

    taboo: List[str] = Field(default_factory=list, description="Taboo words")
    ban_lists: List[str] = Field(default_factory=list, description="Ban lists to apply")


class ImageGrounding(BaseModel):
    """Image grounding options."""

    use: bool = Field(default=False, description="Whether to use image grounding")


class Constraints(BaseModel):
    """Constraints and guardrails."""

    anti_plagiarism: AntiPlagiarism = Field(
        default_factory=AntiPlagiarism, description="Anti-plagiarism constraints"
    )
    length_words: LengthConstraints = Field(
        default_factory=LengthConstraints, description="Length constraints"
    )
    forbidden: List[str] = Field(default_factory=list, description="Forbidden elements")
    must_include: List[str] = Field(default_factory=list, description="Required elements")
    safety_lexicon: SafetyLexicon = Field(
        default_factory=SafetyLexicon, description="Safety filtering"
    )
    external_knowledge: Dict[str, bool] = Field(
        default_factory=lambda: {"allowed": False}, description="External knowledge policy"
    )
    image_grounding: ImageGrounding = Field(
        default_factory=ImageGrounding, description="Image grounding options"
    )


class StorySpec(BaseModel):
    """
    StorySpec@2 schema

    Complete specification for generating a story.
    Combines voice, form, content, and constraints into a portable, serializable format.
    """

    schema_version: str = Field(default="StorySpec@2", description="Schema version identifier", alias="schema")
    meta: MetaInfo = Field(..., description="Metadata")
    voice: Voice = Field(default_factory=Voice, description="Voice and narrative style")
    form: Form = Field(default_factory=Form, description="Form and structure")
    content: Content = Field(..., description="Content parameters")
    constraints: Constraints = Field(default_factory=Constraints, description="Constraints")

    class Config:
        """Pydantic config."""
        
        populate_by_name = True

        json_schema_extra = {
            "example": {
                "schema": "StorySpec@2",
                "meta": {
                    "story_id": "story_001",
                    "seed": 137,
                    "version": "2.0",
                    "derived_from": {"exemplar": "Emergency", "digest_version": 2},
                },
                "voice": {"person": "first", "distance": "intimate"},
                "form": {"structure": "episodic", "dialogue_ratio": 0.25},
                "content": {
                    "setting": {"place": "Iowa City", "time": "1973", "weather_budget": ["fog"]},
                    "characters": [{"name": "protagonist", "role": "narrator"}],
                },
            }
        }
