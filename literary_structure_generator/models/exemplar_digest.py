"""
ExemplarDigest Pydantic model

Represents the extracted "DNA" from an exemplar text including:
- Stylometry (sentence patterns, POS, punctuation)
- Discourse structure (beats, dialogue, focalization)
- Pacing curves and paragraph distributions
- Coherence graphs, motif maps, imagery palettes

Schema version: ExemplarDigest@2

No verbatim text is stored to prevent plagiarism.
"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field


class MetaInfo(BaseModel):
    """Metadata about the exemplar source."""

    source: str = Field(..., description="Title or identifier of the exemplar text")
    tokens: int = Field(default=0, description="Total token count")
    paragraphs: int = Field(default=0, description="Total paragraph count")


class Stylometry(BaseModel):
    """Stylometric features extracted from the exemplar."""

    sentence_len_hist: list[int] = Field(
        default_factory=list, description="Histogram of sentence lengths"
    )
    type_token_ratio: float = Field(default=0.0, description="Lexical diversity metric")
    mtld: float = Field(default=0.0, description="Measure of Textual Lexical Diversity")
    function_word_profile: dict[str, float] = Field(
        default_factory=dict, description="Frequency of function words (and, but, the, etc.)"
    )
    pos_trigrams_top: list[list[str]] = Field(
        default_factory=list, description="Most common part-of-speech trigrams"
    )
    dep_arcs: dict[str, float] = Field(
        default_factory=dict, description="Dependency arc frequencies (parataxis, advcl, etc.)"
    )
    punctuation: dict[str, float] = Field(
        default_factory=dict, description="Punctuation density (comma_per_100, dash_per_100, etc.)"
    )
    figurative_density: dict[str, float] = Field(
        default_factory=dict, description="Density of figurative language (simile, metaphor, etc.)"
    )
    rhetorical_questions: int = Field(default=0, description="Count of rhetorical questions")


class Beat(BaseModel):
    """Structural beat in the story."""

    id: str = Field(..., description="Beat identifier (e.g., cold_open, setpiece_1)")
    span: list[int] = Field(..., description="Token span [start, end]")
    function: str = Field(..., description="Narrative function of this beat")


class Discourse(BaseModel):
    """Discourse-level features."""

    beats: list[Beat] = Field(default_factory=list, description="Structural beat map")
    scene_summary_switches: list[int] = Field(
        default_factory=list, description="Token positions where scene/summary mode switches"
    )
    dialogue_ratio: float = Field(default=0.0, description="Proportion of text that is dialogue")
    tense_distribution: dict[str, float] = Field(
        default_factory=dict, description="Distribution of tenses (past, present, etc.)"
    )
    focalization: str = Field(default="", description="Narrative focalization type")
    free_indirect_markers: float = Field(
        default=0.0, description="Density of free indirect discourse markers"
    )
    deictics: dict[str, float] = Field(
        default_factory=dict, description="Frequency of deictic expressions (now, here, etc.)"
    )
    anaphora_stats: dict[str, float] = Field(
        default_factory=dict, description="Anaphora chain statistics (avg_chain_len, max_chain)"
    )


class Pacing(BaseModel):
    """Pacing and rhythm features."""

    pacing_curve: list[float] = Field(
        default_factory=list, description="Pacing intensity over story progression"
    )
    pause_density: float = Field(default=0.0, description="Density of narrative pauses")
    paragraph_len_hist: list[int] = Field(
        default_factory=list, description="Histogram of paragraph lengths"
    )
    whitespace_ratio: float = Field(default=0.0, description="Ratio of whitespace to text")


class Entity(BaseModel):
    """Entity in the coherence graph."""

    id: str = Field(..., description="Entity ID (e.g., E1, E2)")
    canonical: str = Field(..., description="Canonical name for this entity")
    type: str = Field(..., description="Entity type: PERSON, PLACE, ORG, OBJECT, ANIMAL, VEHICLE")
    surface_forms: list[str] = Field(default_factory=list, description="Surface forms used in text")
    aliases: list[str] = Field(default_factory=list, description="Known aliases")
    mentions: int = Field(default=0, description="Total number of mentions")


class Edge(BaseModel):
    """Edge in the coherence graph."""

    source: str = Field(..., description="Source entity ID")
    target: str = Field(..., description="Target entity ID")
    relation: str = Field(..., description="Relation type: co_occurs, speaks_to, located_in")
    weight_sent: int = Field(default=0, description="Number of co-occurrences in same sentence")
    weight_para: int = Field(default=0, description="Number of co-occurrences in same paragraph")
    beats: list[str] = Field(default_factory=list, description="Beat IDs where this edge occurs")


class CoherenceGraph(BaseModel):
    """Entity coherence graph."""

    entities: list[Entity] = Field(default_factory=list, description="List of entities")
    edges: list[Edge] = Field(default_factory=list, description="Entity relationships")
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Graph statistics (num_entities, num_edges, avg_degree, largest_component)",
    )


class Motif(BaseModel):
    """Recurring motif or theme."""

    motif: str = Field(..., description="Motif name or description")
    anchors: list[int] = Field(
        default_factory=list, description="Token positions where motif appears"
    )
    co_occurs_with: list[str] = Field(
        default_factory=list, description="Other motifs this co-occurs with"
    )


class EventScript(BaseModel):
    """Common event script or schema."""

    script: str = Field(..., description="Script name (e.g., 'ER intake')")
    triples: list[list[str]] = Field(
        default_factory=list, description="Event triples [[subject, verb, object], ...]"
    )


class Safety(BaseModel):
    """Content safety analysis."""

    profanity_rate: float = Field(default=0.0, description="Rate of grit usage")
    taboo_topics: list[str] = Field(default_factory=list, description="Detected taboo topics")


class ExemplarDigest(BaseModel):
    """
    ExemplarDigest@2 schema

    Complete structural, stylistic, and thematic analysis of an exemplar text.
    Used to extract reusable "form" that can be applied to new content.
    """

    schema_version: str = Field(
        default="ExemplarDigest@2", description="Schema version identifier", alias="schema"
    )
    meta: MetaInfo = Field(..., description="Metadata about the exemplar")
    stylometry: Stylometry = Field(default_factory=Stylometry, description="Stylometric features")
    discourse: Discourse = Field(default_factory=Discourse, description="Discourse-level features")
    pacing: Pacing = Field(default_factory=Pacing, description="Pacing and rhythm features")
    coherence_graph: CoherenceGraph = Field(
        default_factory=CoherenceGraph, description="Entity coherence graph"
    )
    motif_map: list[Motif] = Field(default_factory=list, description="Recurring motifs and themes")
    imagery_palettes: dict[str, list[str]] = Field(
        default_factory=dict, description="Imagery palettes by category (hospital, road, etc.)"
    )
    event_scripts: list[EventScript] = Field(
        default_factory=list, description="Common event scripts"
    )
    lexical_domains: dict[str, list[str]] = Field(
        default_factory=dict, description="Lexical domains (medical, working_class, etc.)"
    )
    valence_arc: dict[str, Any] = Field(
        default_factory=dict, description="Emotional valence arc over story"
    )
    surprise_curve: list[float] = Field(
        default_factory=list, description="Information-theoretic surprise over story"
    )
    safety: Safety = Field(default_factory=Safety, description="Content safety analysis")

    class Config:
        """Pydantic config."""

        populate_by_name = True

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "schema": "ExemplarDigest@2",
                "meta": {"source": "Emergency", "tokens": 5234, "paragraphs": 127},
                "stylometry": {
                    "sentence_len_hist": [2, 5, 12, 23, 18, 9, 4, 2],
                    "type_token_ratio": 0.68,
                    "mtld": 78.5,
                },
                "discourse": {
                    "beats": [{"id": "cold_open", "span": [0, 180], "function": "tonal hook"}]
                },
            }
        }
