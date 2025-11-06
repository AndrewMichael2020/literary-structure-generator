"""
Tests for StorySpec synthesis (spec/synthesizer.py)

Validates the synthesis of StorySpec from ExemplarDigest.
"""

from pathlib import Path

import pytest

from literary_structure_generator.ingest.digest_exemplar import analyze_text
from literary_structure_generator.models.exemplar_digest import (
    Beat,
    Discourse,
    ExemplarDigest,
    MetaInfo,
    Pacing,
    Safety,
    Stylometry,
)
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.spec.synthesizer import (
    initialize_content_section,
    map_form_parameters,
    map_voice_parameters,
    synthesize_spec,
)


class TestVoiceMapping:
    """Test voice parameter mapping from digest."""

    def test_map_voice_basic(self):
        """Test basic voice parameter mapping."""
        digest = ExemplarDigest(
            meta=MetaInfo(source="test", tokens=1000, paragraphs=20),
            stylometry=Stylometry(
                sentence_len_hist=[10, 20, 15, 10, 5, 3, 2, 1, 0],
                punctuation={"comma_per_100": 50},
            ),
            discourse=Discourse(
                dialogue_ratio=0.3,
                focalization="first-person intimate",
            ),
        )

        voice_params = map_voice_parameters(digest)

        assert "person" in voice_params
        assert voice_params["person"] in ["first", "second", "third-limited", "omniscient"]
        assert "distance" in voice_params
        assert "syntax" in voice_params
        assert "avg_sentence_len" in voice_params["syntax"]

    def test_map_voice_first_person(self):
        """Test voice mapping for first-person narrative."""
        digest = ExemplarDigest(
            meta=MetaInfo(source="test", tokens=1000, paragraphs=20),
            stylometry=Stylometry(
                sentence_len_hist=[5, 10, 8, 5, 2, 1, 0, 0, 0],
                punctuation={"comma_per_100": 45},
            ),
            discourse=Discourse(
                dialogue_ratio=0.6,
                focalization="first-person",
            ),
        )

        voice_params = map_voice_parameters(digest)

        assert voice_params["person"] == "first"
        # Distance is "close" for avg_sentence_len around 12
        assert voice_params["distance"] in ["intimate", "close"]


class TestFormMapping:
    """Test form parameter mapping from digest."""

    def test_map_form_basic(self):
        """Test basic form parameter mapping."""
        digest = ExemplarDigest(
            meta=MetaInfo(source="test", tokens=1000, paragraphs=20),
            discourse=Discourse(
                beats=[
                    Beat(id="opening", span=[0, 300], function="establish setting"),
                    Beat(id="middle", span=[300, 700], function="develop conflict"),
                    Beat(id="closing", span=[700, 1000], function="resolution"),
                ],
                dialogue_ratio=0.25,
            ),
            pacing=Pacing(paragraph_len_hist=[5, 8, 10, 12, 8, 4, 2, 1, 0]),
        )

        form_params = map_form_parameters(digest)

        assert "beat_map" in form_params
        assert len(form_params["beat_map"]) == 3
        assert "dialogue_ratio" in form_params
        assert form_params["dialogue_ratio"] == 0.25
        assert "paragraphing" in form_params

    def test_beat_conversion(self):
        """Test beat conversion from digest to spec."""
        digest = ExemplarDigest(
            meta=MetaInfo(source="test", tokens=1300, paragraphs=20),
            discourse=Discourse(
                beats=[
                    Beat(id="opening", span=[0, 650], function="cold open"),
                    Beat(id="closing", span=[650, 1300], function="wrap up"),
                ],
                dialogue_ratio=0.2,
            ),
            pacing=Pacing(paragraph_len_hist=[10, 15, 12, 8, 5, 2, 1, 0, 0]),
        )

        form_params = map_form_parameters(digest)

        assert len(form_params["beat_map"]) == 2
        # Check token to word conversion (~1.3 ratio)
        assert form_params["beat_map"][0]["target_words"] == 500
        assert form_params["beat_map"][0]["id"] == "opening"
        assert form_params["beat_map"][0]["function"] == "cold open"


class TestContentInitialization:
    """Test content section initialization."""

    def test_initialize_content_empty(self):
        """Test content initialization with no prompts."""
        content = initialize_content_section()

        assert "setting" in content
        assert "characters" in content
        assert "motifs" in content
        assert content["setting"]["place"] == "[to be defined]"

    def test_initialize_content_with_setting(self):
        """Test content initialization with setting prompt."""
        content = initialize_content_section(setting_prompt="A busy hospital ER")

        assert content["setting"]["place"] == "A busy hospital ER"

    def test_initialize_content_with_characters(self):
        """Test content initialization with character prompts."""
        content = initialize_content_section(characters_prompt="Alice, Bob, Charlie")

        assert len(content["characters"]) == 3
        assert content["characters"][0]["name"] == "Alice"
        assert content["characters"][1]["name"] == "Bob"


class TestSpecSynthesis:
    """Test full StorySpec synthesis."""

    def test_synthesize_spec_basic(self, tmp_path):
        """Test basic spec synthesis from digest."""
        digest = ExemplarDigest(
            meta=MetaInfo(source="test_story", tokens=1300, paragraphs=25),
            stylometry=Stylometry(
                sentence_len_hist=[8, 15, 12, 10, 5, 3, 2, 1, 0],
                punctuation={"comma_per_100": 55},
            ),
            discourse=Discourse(
                beats=[
                    Beat(id="opening", span=[0, 400], function="setup"),
                    Beat(id="middle", span=[400, 900], function="conflict"),
                    Beat(id="closing", span=[900, 1300], function="resolution"),
                ],
                dialogue_ratio=0.35,
                focalization="first-person",
            ),
            pacing=Pacing(paragraph_len_hist=[6, 10, 12, 15, 8, 5, 2, 1, 0]),
        )

        spec = synthesize_spec(
            digest=digest,
            story_id="test_001",
            seed=42,
            run_id="test_run",
            iteration=0,
        )

        # Validate spec structure
        assert isinstance(spec, StorySpec)
        assert spec.meta.story_id == "test_001"
        assert spec.meta.seed == 42
        assert spec.meta.derived_from["exemplar"] == "test_story"

        # Validate voice
        assert spec.voice.person in ["first", "second", "third-limited", "omniscient"]
        assert spec.voice.syntax.avg_sentence_len > 0

        # Validate form
        assert len(spec.form.beat_map) == 3
        assert spec.form.dialogue_ratio == 0.35

        # Validate constraints
        assert spec.constraints.anti_plagiarism.max_ngram == 12
        assert spec.constraints.anti_plagiarism.overlap_pct == 0.03
        assert spec.constraints.length_words.target > 0

    def test_synthesize_spec_with_output(self, tmp_path):
        """Test spec synthesis with JSON output."""
        output_file = tmp_path / "test_spec.json"

        digest = ExemplarDigest(
            meta=MetaInfo(source="test", tokens=1000, paragraphs=20),
            stylometry=Stylometry(
                sentence_len_hist=[10, 15, 12, 8, 5, 3, 2, 1, 0],
                punctuation={"comma_per_100": 50},
            ),
            discourse=Discourse(
                beats=[
                    Beat(id="opening", span=[0, 500], function="intro"),
                    Beat(id="closing", span=[500, 1000], function="outro"),
                ],
                dialogue_ratio=0.2,
                focalization="third-person",
            ),
            pacing=Pacing(paragraph_len_hist=[8, 12, 10, 8, 5, 3, 2, 1, 0]),
        )

        spec = synthesize_spec(
            digest=digest,
            story_id="test_002",
            seed=137,
            output_path=str(output_file),
            run_id="test_run",
            iteration=0,
        )

        # Verify file was created
        assert output_file.exists()

        # Verify file can be loaded
        loaded_spec = StorySpec.model_validate_json(output_file.read_text())
        assert loaded_spec.meta.story_id == "test_002"
        assert loaded_spec.meta.seed == 137

    def test_synthesize_spec_from_emergency(self):
        """Test spec synthesis from actual Emergency.txt digest."""
        # Skip if Emergency.txt doesn't exist
        emergency_path = Path("data/Emergency.txt")
        if not emergency_path.exists():
            pytest.skip("Emergency.txt not found")

        # Generate digest
        digest = analyze_text(str(emergency_path), run_id="test_emergency", iteration=0)

        # Synthesize spec
        spec = synthesize_spec(
            digest=digest,
            story_id="emergency_spec_test",
            seed=137,
            run_id="test_emergency",
            iteration=0,
        )

        # Validate spec
        assert spec.meta.story_id == "emergency_spec_test"
        assert spec.meta.derived_from["exemplar"] == "Emergency"
        assert len(spec.form.beat_map) > 0
        assert spec.constraints.length_words.target > 0
        assert spec.voice.person in ["first", "second", "third-limited", "omniscient"]
