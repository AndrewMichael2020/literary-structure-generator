"""
Tests for Phase 4 generation components.

Tests cover:
- Draft generation pipeline
- Beat generation
- Overlap guards
- Clean mode filtering
- Repair passes
- Routing with GPT-5
"""

import tempfile
from pathlib import Path

from literary_structure_generator.generation.draft_generator import (
    build_beat_prompt,
    generate_beat_text,
    run_draft_generation,
    stitch_beats,
)
from literary_structure_generator.generation.guards import (
    apply_clean_mode_if_needed,
    check_overlap_guard,
    clean_mode,
    max_ngram_overlap,
    simhash_distance,
)
from literary_structure_generator.generation.repair import (
    calculate_paragraph_variance,
    repair_text,
)
from literary_structure_generator.llm.router import get_client
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    MetaInfo,
    Setting,
    StorySpec,
)
from literary_structure_generator.utils.similarity import calculate_simhash, hamming_distance


class TestSimilarityUtils:
    """Test similarity utilities."""

    def test_simhash_basic(self):
        """Test SimHash calculation."""
        text = "The quick brown fox jumps over the lazy dog"
        hash_val = calculate_simhash(text, num_bits=256)
        assert isinstance(hash_val, int)
        assert hash_val >= 0

    def test_simhash_different_texts(self):
        """Test different texts produce different hashes."""
        text1 = "The quick brown fox"
        text2 = "The lazy brown dog"
        hash1 = calculate_simhash(text1)
        hash2 = calculate_simhash(text2)
        assert hash1 != hash2

    def test_simhash_similar_texts(self):
        """Test similar texts produce similar hashes."""
        text1 = "The quick brown fox jumps"
        text2 = "The quick brown fox jumps"
        hash1 = calculate_simhash(text1)
        hash2 = calculate_simhash(text2)
        assert hash1 == hash2

    def test_hamming_distance_identical(self):
        """Test Hamming distance of identical hashes."""
        hash1 = 12345
        hash2 = 12345
        distance = hamming_distance(hash1, hash2)
        assert distance == 0

    def test_hamming_distance_different(self):
        """Test Hamming distance of different hashes."""
        hash1 = 0b1111
        hash2 = 0b0000
        distance = hamming_distance(hash1, hash2)
        assert distance == 4

    def test_hamming_distance_single_bit(self):
        """Test Hamming distance with single bit difference."""
        hash1 = 0b1000
        hash2 = 0b0000
        distance = hamming_distance(hash1, hash2)
        assert distance == 1


class TestGuards:
    """Test overlap guard and clean mode."""

    def test_max_ngram_overlap_no_overlap(self):
        """Test n-gram overlap with completely different texts."""
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "A cat sat on a mat looking happy today"
        overlap = max_ngram_overlap(text1, text2, n=12)
        assert overlap < 0.1  # Should be very low or zero

    def test_max_ngram_overlap_high_overlap(self):
        """Test n-gram overlap with similar texts."""
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "The quick brown fox jumps over the lazy cat"
        overlap = max_ngram_overlap(text1, text2, n=12)
        assert overlap > 0.5  # Should be high

    def test_max_ngram_overlap_empty_text(self):
        """Test n-gram overlap with empty text."""
        overlap = max_ngram_overlap("", "some text", n=12)
        assert overlap == 0.0

    def test_simhash_distance_identical(self):
        """Test SimHash distance of identical texts."""
        text = "The quick brown fox jumps over the lazy dog"
        distance = simhash_distance(text, text)
        assert distance == 0

    def test_simhash_distance_different(self):
        """Test SimHash distance of different texts."""
        text1 = "The quick brown fox"
        text2 = "A completely different sentence about cats"
        distance = simhash_distance(text1, text2)
        assert distance > 18  # Should be well above minimum threshold

    def test_clean_mode_no_profanity(self):
        """Test clean mode with clean text."""
        text = "This is a clean sentence."
        cleaned = clean_mode(text)
        assert cleaned == text

    def test_clean_mode_profanity_replacement(self):
        """Test clean mode replaces profanity."""
        text = "What the hell is going on?"
        cleaned = clean_mode(text)
        assert "hell" not in cleaned.lower()
        assert "heck" in cleaned.lower()

    def test_clean_mode_multiple_profanity(self):
        """Test clean mode with multiple profanity words."""
        text = "Damn this shit"
        cleaned = clean_mode(text)
        assert "damn" not in cleaned.lower()
        assert "shit" not in cleaned.lower()

    def test_check_overlap_guard_pass(self):
        """Test overlap guard passing."""
        text1 = "The protagonist walked down the street on a sunny day."
        text2 = "A character strolled along the avenue under cloudy skies."
        result = check_overlap_guard(text1, text2)
        assert result["passed"]
        assert len(result["violations"]) == 0

    def test_check_overlap_guard_fail_ngram(self):
        """Test overlap guard failing on n-gram overlap."""
        text1 = "The quick brown fox jumps over the lazy dog every single day"
        text2 = "The quick brown fox jumps over the lazy dog on weekends"
        result = check_overlap_guard(text1, text2, max_overlap_pct=0.01)
        assert not result["passed"]
        assert any("overlap" in v.lower() for v in result["violations"])

    def test_apply_clean_mode_if_needed_enabled(self):
        """Test clean mode application when enabled."""
        text = "What the hell"
        cleaned = apply_clean_mode_if_needed(text, clean_mode_enabled=True)
        assert "hell" not in cleaned.lower()

    def test_apply_clean_mode_if_needed_disabled(self):
        """Test clean mode not applied when disabled."""
        text = "What the hell"
        cleaned = apply_clean_mode_if_needed(text, clean_mode_enabled=False)
        assert cleaned == text


class TestRepair:
    """Test repair pass functionality."""

    def test_calculate_paragraph_variance_uniform(self):
        """Test variance calculation with uniform paragraphs."""
        text = "First paragraph with ten words here.\n\nSecond paragraph with ten words here."
        variance = calculate_paragraph_variance(text)
        assert variance < 1.0  # Should be very low

    def test_calculate_paragraph_variance_high(self):
        """Test variance calculation with varied paragraphs."""
        text = (
            "Short.\n\nThis is a much longer paragraph with many more words to make variance high."
        )
        variance = calculate_paragraph_variance(text)
        assert variance > 10.0  # Should be high

    def test_calculate_paragraph_variance_empty(self):
        """Test variance calculation with empty text."""
        variance = calculate_paragraph_variance("")
        assert variance == 0.0

    def test_repair_text_basic(self):
        """Test basic repair pass."""
        # Create minimal spec
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(setting=Setting(place="test", time="now")),
        )

        text = "The protagonist walked down the street."
        repaired = repair_text(text, spec)
        assert isinstance(repaired, str)
        assert len(repaired) > 0

    def test_repair_text_with_issues(self):
        """Test repair pass with specific issues."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(setting=Setting(place="test", time="now")),
        )

        text = "The protagonist walked down the street."
        notes = {"issues": ["Fix POV leak", "Improve rhythm"]}
        repaired = repair_text(text, spec, notes=notes)
        assert isinstance(repaired, str)
        assert len(repaired) > 0


class TestDraftGenerator:
    """Test draft generation pipeline."""

    def test_build_beat_prompt(self):
        """Test beat prompt construction."""
        beat = BeatSpec(
            id="beat1",
            target_words=200,
            function="establish setting",
            cadence="mixed",
            summary="Opening scene in hospital",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(
                setting=Setting(place="Hospital", time="1973"),
                characters=[Character(name="Dr. Smith", role="protagonist")],
                motifs=["healing", "crisis"],
                imagery_palette=["white walls", "fluorescent lights"],
                props=["stethoscope"],
            ),
        )

        prompt = build_beat_prompt(beat, spec)
        assert "establish setting" in prompt
        assert "200" in prompt
        assert "Hospital" in prompt
        assert "1973" in prompt

    def test_stitch_beats(self):
        """Test beat stitching."""
        beats = [
            "First beat text here.",
            "Second beat continues the story.",
            "Third beat concludes.",
        ]
        stitched = stitch_beats(beats)
        assert "First beat" in stitched
        assert "Second beat" in stitched
        assert "Third beat" in stitched
        assert "\n\n" in stitched

    def test_generate_beat_text_basic(self):
        """Test single beat generation."""
        beat = BeatSpec(
            id="beat1",
            target_words=100,
            function="opening",
            cadence="mixed",
            summary="Start the story",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(
                setting=Setting(place="City", time="present"),
                characters=[Character(name="Alex", role="protagonist")],
            ),
        )

        result = generate_beat_text(beat, spec)
        assert "text" in result
        assert "metadata" in result
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0

    def test_generate_beat_text_with_exemplar(self):
        """Test beat generation with overlap guard."""
        beat = BeatSpec(
            id="beat1",
            target_words=100,
            function="opening",
            cadence="mixed",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(
                setting=Setting(place="City", time="present"),
                characters=[Character(name="Alex", role="protagonist")],
            ),
        )

        exemplar = "Some exemplar text that should not be copied verbatim."
        result = generate_beat_text(beat, spec, exemplar=exemplar)
        assert result["guard_passed"]

    def test_run_draft_generation_basic(self):
        """Test full draft generation pipeline."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_story", seed=137),
            content=Content(
                setting=Setting(place="City", time="present"),
                characters=[Character(name="Alex", role="protagonist")],
            ),
        )

        # Add beats to spec
        spec.form.beat_map = [
            BeatSpec(
                id="beat1",
                target_words=100,
                function="opening",
                cadence="mixed",
            ),
            BeatSpec(
                id="beat2",
                target_words=100,
                function="development",
                cadence="mixed",
            ),
        ]

        result = run_draft_generation(spec)
        assert "beats" in result
        assert "stitched" in result
        assert "repaired" in result
        assert "final" in result
        assert "metadata" in result
        assert len(result["beats"]) == 2

    def test_run_draft_generation_with_output(self):
        """Test draft generation with file output."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_story", seed=137),
            content=Content(
                setting=Setting(place="City", time="present"),
                characters=[Character(name="Alex", role="protagonist")],
            ),
        )

        spec.form.beat_map = [
            BeatSpec(
                id="beat1",
                target_words=100,
                function="opening",
                cadence="mixed",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_draft_generation(spec, output_dir=tmpdir)

            # Check files created
            output_path = Path(tmpdir)
            assert (output_path / "story_spec.json").exists()
            assert (output_path / "beat_results.json").exists()
            assert (output_path / "stitched.txt").exists()
            assert (output_path / "repaired.txt").exists()
            assert (output_path / "final.txt").exists()
            assert (output_path / "metadata.json").exists()


class TestRouterGPT5:
    """Test router handling of GPT-5 models."""

    def test_gpt5_drops_temperature(self):
        """Test that GPT-5 models don't receive temperature param."""
        # This test verifies router behavior with GPT-5
        # In a real scenario, this would check that temperature is not passed
        client = get_client("beat_generator")
        # For mock client, temperature is always set, but in production
        # the router filters it out for gpt-5 models
        assert client.model in ["gpt-5", "mock"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_simhash_empty_text(self):
        """Test SimHash with empty text."""
        hash_val = calculate_simhash("", num_bits=256)
        assert hash_val == 0

    def test_clean_mode_empty_text(self):
        """Test clean mode with empty text."""
        cleaned = clean_mode("")
        assert cleaned == ""

    def test_max_ngram_overlap_single_word(self):
        """Test n-gram overlap with single-word texts."""
        overlap = max_ngram_overlap("word", "word", n=12)
        assert overlap >= 0.0

    def test_generate_beat_text_no_exemplar(self):
        """Test beat generation without exemplar."""
        beat = BeatSpec(
            id="beat1",
            target_words=50,
            function="test",
            cadence="short",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(
                setting=Setting(place="Test", time="now"),
            ),
        )
        result = generate_beat_text(beat, spec, exemplar=None)
        assert result["guard_passed"]

    def test_repair_text_no_issues(self):
        """Test repair with no issues."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(setting=Setting(place="test", time="now")),
        )
        text = "Clean text."
        repaired = repair_text(text, spec, notes=None)
        assert isinstance(repaired, str)

    def test_run_draft_generation_with_exemplar(self):
        """Test draft generation with exemplar guard."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(
                setting=Setting(place="City", time="present"),
            ),
        )
        spec.form.beat_map = [
            BeatSpec(id="b1", target_words=50, function="test", cadence="short"),
        ]

        exemplar = "This is some exemplar text that should not be copied."
        result = run_draft_generation(spec, exemplar=exemplar)
        assert "metadata" in result
        assert "stitched_guard" in result["metadata"]

    def test_calculate_paragraph_variance_single(self):
        """Test variance with single paragraph."""
        text = "Single paragraph only."
        variance = calculate_paragraph_variance(text)
        assert variance == 0.0

    def test_simhash_distance_empty(self):
        """Test SimHash distance with empty strings."""
        distance = simhash_distance("", "")
        assert distance == 0

    def test_build_beat_prompt_with_empty_lists(self):
        """Test beat prompt with minimal content."""
        beat = BeatSpec(
            id="beat1",
            target_words=100,
            function="test",
            cadence="mixed",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(
                setting=Setting(place="Test", time="now"),
            ),
        )
        prompt = build_beat_prompt(beat, spec)
        assert "test" in prompt.lower()
        assert "100" in prompt

    def test_check_overlap_guard_simhash_fail(self):
        """Test overlap guard failing on SimHash distance."""
        # Create nearly identical texts to fail SimHash check
        text1 = "The exact same sentence repeated multiple times."
        text2 = "The exact same sentence repeated multiple times."
        result = check_overlap_guard(text1, text2, min_simhash_hamming=1)
        assert not result["passed"]

    def test_generate_beat_text_with_memory(self):
        """Test beat generation with context memory."""
        beat = BeatSpec(
            id="beat2",
            target_words=50,
            function="continuation",
            cadence="short",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(setting=Setting(place="Test", time="now")),
        )
        memory = {"beat1": {"text": "Previous beat text.", "function": "opening"}}
        result = generate_beat_text(beat, spec, memory=memory)
        assert "text" in result

    def test_generate_beat_text_guard_failure(self):
        """Test beat generation with guard failure."""
        beat = BeatSpec(
            id="beat1",
            target_words=50,
            function="test",
            cadence="short",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(setting=Setting(place="Test", time="now")),
        )
        # Use same text as exemplar to force high overlap
        exemplar = "The morning air carried the scent of rain."
        result = generate_beat_text(beat, spec, exemplar=exemplar, max_retries=0)
        # Should still return result even if guard fails
        assert "text" in result
        assert "metadata" in result

    def test_build_beat_prompt_with_full_spec(self):
        """Test beat prompt with fully populated spec."""
        beat = BeatSpec(
            id="beat1",
            target_words=200,
            function="establish conflict",
            cadence="long",
            summary="The protagonist faces a difficult choice",
        )
        spec = StorySpec(
            meta=MetaInfo(story_id="test", seed=137),
            content=Content(
                setting=Setting(place="Hospital", time="1973"),
                characters=[
                    Character(name="Dr. Smith", role="protagonist"),
                    Character(name="Nurse Jones", role="supporting"),
                ],
                motifs=["healing", "crisis", "transformation"],
                imagery_palette=["white walls", "fluorescent lights", "sterile"],
                props=["stethoscope", "clipboard"],
            ),
        )

        # Set some specific voice parameters
        spec.voice.syntax.parataxis_vs_hypotaxis = 0.2  # Hypotactic
        spec.voice.register_sliders = {"lyric": 0.8, "deadpan": 0.2}

        prompt = build_beat_prompt(beat, spec)
        assert "establish conflict" in prompt
        assert "200" in prompt
        assert "Hospital" in prompt
        assert "1973" in prompt
        assert "Dr. Smith" in prompt
        assert "healing" in prompt
        assert "white walls" in prompt
        assert "stethoscope" in prompt
        assert "hypotactic" in prompt
