"""
Tests for ExemplarDigest pipeline (digest_exemplar module)

Validates the analyze_text function and text analysis components.
"""

from pathlib import Path

import pytest

from literary_structure_generator.ingest.digest_exemplar import (
    _calculate_profanity_rate,
    _calculate_type_token_ratio,
    _compute_paragraph_length_histogram,
    _compute_sentence_length_histogram,
    _detect_dialogue_ratio,
    _extract_function_word_profile,
    _split_paragraphs,
    _tokenize_sentences,
    _tokenize_words,
    analyze_text,
)
from literary_structure_generator.models.exemplar_digest import ExemplarDigest


class TestTextTokenization:
    """Test basic text tokenization functions."""

    def test_tokenize_sentences_basic(self):
        """Test basic sentence tokenization."""
        text = "This is a sentence. This is another one! Is this a third?"
        sentences = _tokenize_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "This is a sentence"
        assert sentences[1] == "This is another one"
        assert sentences[2] == "Is this a third"

    def test_tokenize_words_basic(self):
        """Test basic word tokenization."""
        text = "Hello world, this is a test!"
        words = _tokenize_words(text)
        assert "hello" in words
        assert "world" in words
        assert "test" in words
        assert len(words) == 6

    def test_tokenize_words_contractions(self):
        """Test that contractions are handled properly."""
        text = "I'm don't can't"
        words = _tokenize_words(text)
        assert "i'm" in words
        assert "don't" in words
        assert "can't" in words

    def test_split_paragraphs_basic(self):
        """Test paragraph splitting."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        paragraphs = _split_paragraphs(text)
        assert len(paragraphs) == 3
        assert "Paragraph one." in paragraphs[0]
        assert "Paragraph two." in paragraphs[1]

    def test_split_paragraphs_empty(self):
        """Test paragraph splitting with empty input."""
        paragraphs = _split_paragraphs("")
        assert len(paragraphs) == 0


class TestSentenceLengthHistogram:
    """Test sentence length histogram computation."""

    def test_compute_histogram_basic(self):
        """Test histogram computation with various sentence lengths."""
        sentences = [
            "Short.",  # ~1 word
            "A bit longer here.",  # ~4 words
            "This is a medium length sentence with more words.",  # ~9 words
            "This sentence has many more words in it to test the longer bins.",  # ~13 words
        ]
        histogram = _compute_sentence_length_histogram(sentences)
        assert len(histogram) == 9
        assert histogram[0] > 0  # Should have short sentences
        assert histogram[1] > 0  # Should have medium sentences
        assert sum(histogram) == len(sentences)

    def test_compute_histogram_empty(self):
        """Test histogram with empty input."""
        histogram = _compute_sentence_length_histogram([])
        assert len(histogram) == 9
        assert sum(histogram) == 0


class TestParagraphLengthHistogram:
    """Test paragraph length histogram computation."""

    def test_compute_paragraph_histogram_basic(self):
        """Test paragraph histogram with various lengths."""
        paragraphs = [
            "Short paragraph.",  # ~2 words
            "A medium length paragraph with several words here.",  # ~8 words
            " ".join(["word"] * 50),  # 50 words
            " ".join(["word"] * 100),  # 100 words
        ]
        histogram = _compute_paragraph_length_histogram(paragraphs)
        assert len(histogram) == 9
        assert sum(histogram) == len(paragraphs)

    def test_compute_paragraph_histogram_empty(self):
        """Test paragraph histogram with empty input."""
        histogram = _compute_paragraph_length_histogram([])
        assert len(histogram) == 9
        assert sum(histogram) == 0


class TestDialogueDetection:
    """Test dialogue ratio detection."""

    def test_detect_dialogue_straight_quotes(self):
        """Test dialogue detection with straight quotes."""
        text = 'He said "Hello there" and left.'
        ratio = _detect_dialogue_ratio(text)
        assert ratio > 0.0
        assert ratio < 1.0

    def test_detect_dialogue_curly_quotes(self):
        """Test dialogue detection with curly/smart quotes."""
        text = 'He said "Hello there" and left.'
        ratio = _detect_dialogue_ratio(text)
        assert ratio > 0.0
        assert ratio < 1.0

    def test_detect_dialogue_no_dialogue(self):
        """Test dialogue detection with no dialogue."""
        text = "This is a narrative paragraph with no dialogue at all."
        ratio = _detect_dialogue_ratio(text)
        assert ratio == 0.0

    def test_detect_dialogue_all_dialogue(self):
        """Test dialogue detection with mostly dialogue."""
        text = '"Hello" "Hi" "How are you" "Good"'
        ratio = _detect_dialogue_ratio(text)
        assert ratio > 0.5  # Should be high


class TestFunctionWordProfile:
    """Test function word profile extraction."""

    def test_extract_function_words_basic(self):
        """Test basic function word extraction."""
        words = ["the", "cat", "and", "the", "dog", "were", "in", "the", "house"]
        profile = _extract_function_word_profile(words, top_n=5)
        assert "the" in profile
        assert "and" in profile
        assert "in" in profile
        assert profile["the"] > profile["and"]  # "the" appears more

    def test_extract_function_words_empty(self):
        """Test function word extraction with empty input."""
        profile = _extract_function_word_profile([], top_n=5)
        assert len(profile) == 0

    def test_extract_function_words_frequency(self):
        """Test that frequencies are per 100 words."""
        words = ["the"] * 10 + ["cat"] * 90  # 10% function word
        profile = _extract_function_word_profile(words, top_n=5)
        assert "the" in profile
        # Should be approximately 10 per 100 words
        assert 9.0 < profile["the"] < 11.0


class TestTypeTokenRatio:
    """Test type-token ratio calculation."""

    def test_ttr_all_unique(self):
        """Test TTR with all unique words."""
        words = ["cat", "dog", "bird", "fish"]
        ratio = _calculate_type_token_ratio(words)
        assert ratio == 1.0

    def test_ttr_all_same(self):
        """Test TTR with all same words."""
        words = ["cat"] * 10
        ratio = _calculate_type_token_ratio(words)
        assert ratio == 0.1

    def test_ttr_empty(self):
        """Test TTR with empty input."""
        ratio = _calculate_type_token_ratio([])
        assert ratio == 0.0

    def test_ttr_mixed(self):
        """Test TTR with mixed repetition."""
        words = ["cat", "dog", "cat", "bird"]
        ratio = _calculate_type_token_ratio(words)
        assert ratio == 0.75  # 3 unique / 4 total


class TestProfanityRate:
    """Test profanity rate calculation."""

    def test_profanity_rate_clean_mode(self):
        """Test profanity rate in Clean Mode (always 0.0)."""
        rate = _calculate_profanity_rate()
        assert rate == 0.0


class TestAnalyzeTextIntegration:
    """Integration tests for analyze_text function."""

    def test_analyze_text_emergency_file(self):
        """Test analyze_text with the Emergency.txt file."""
        # Path to the Emergency.txt file
        file_path = "data/Emergency.txt"

        # Skip if file doesn't exist (for CI/CD environments)
        if not Path(file_path).exists():
            pytest.skip("Emergency.txt not found")

        digest = analyze_text(file_path)

        # Validate structure
        assert isinstance(digest, ExemplarDigest)
        assert digest.schema_version == "ExemplarDigest@2"

        # Validate metadata
        assert digest.meta.source == "Emergency"
        assert digest.meta.tokens > 0
        assert digest.meta.paragraphs > 0

        # Validate stylometry
        assert len(digest.stylometry.sentence_len_hist) == 9
        assert sum(digest.stylometry.sentence_len_hist) > 0
        assert 0.0 <= digest.stylometry.type_token_ratio <= 1.0
        assert len(digest.stylometry.function_word_profile) > 0
        assert len(digest.stylometry.punctuation) > 0

        # Validate discourse
        assert 0.0 <= digest.discourse.dialogue_ratio <= 1.0
        assert len(digest.discourse.beats) > 0

        # Validate pacing
        assert len(digest.pacing.paragraph_len_hist) == 9
        assert sum(digest.pacing.paragraph_len_hist) > 0

        # Validate safety
        assert digest.safety.profanity_rate == 0.0

    def test_analyze_text_output_structure(self, tmp_path):
        """Test that analyze_text produces valid ExemplarDigest structure."""
        # Create a temporary test file
        test_file = tmp_path / "test_story.txt"
        test_content = """Test Story

This is a test story. It has several sentences! Does it work?

"Hello," she said. "This is dialogue."

Another paragraph here with more content."""
        test_file.write_text(test_content, encoding="utf-8")

        digest = analyze_text(str(test_file))

        # Validate basic structure
        assert digest.meta.source == "test_story"
        assert digest.meta.tokens > 0
        assert digest.meta.paragraphs >= 3

        # Validate histogram structures
        assert len(digest.stylometry.sentence_len_hist) == 9
        assert len(digest.pacing.paragraph_len_hist) == 9

        # Validate dialogue detection
        assert digest.discourse.dialogue_ratio > 0.0

    def test_analyze_text_nonexistent_file(self):
        """Test analyze_text with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            analyze_text("nonexistent_file.txt")

    def test_analyze_text_json_serialization(self, tmp_path):
        """Test that ExemplarDigest can be serialized to JSON."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Simple test. Another sentence.", encoding="utf-8")

        digest = analyze_text(str(test_file))

        # Test JSON serialization
        json_str = digest.model_dump_json()
        assert isinstance(json_str, str)
        assert "ExemplarDigest@2" in json_str

        # Test deserialization
        loaded_digest = ExemplarDigest.model_validate_json(json_str)
        assert loaded_digest.meta.source == digest.meta.source
        assert loaded_digest.meta.tokens == digest.meta.tokens

    def test_analyze_text_beats_structure(self, tmp_path):
        """Test that beats are correctly structured."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content. " * 100, encoding="utf-8")

        digest = analyze_text(str(test_file))

        # Should have 3 beats (opening, middle, closing)
        assert len(digest.discourse.beats) == 3

        # Validate beat structure
        for beat in digest.discourse.beats:
            assert beat.id in ["opening", "middle", "closing"]
            assert len(beat.span) == 2
            assert beat.span[0] < beat.span[1]
            assert isinstance(beat.function, str)
            assert len(beat.function) > 0

        # Validate beat spans cover the full text
        assert digest.discourse.beats[0].span[0] == 0
        assert digest.discourse.beats[-1].span[1] == digest.meta.tokens
