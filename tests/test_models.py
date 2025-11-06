"""
Tests for Pydantic models

Validates schema definitions and serialization.
"""

import pytest
from pydantic import ValidationError

from literary_structure_generator.models import (
    ExemplarDigest,
    StorySpec,
    GenerationConfig,
    EvalReport,
    AuthorProfile,
)


class TestExemplarDigest:
    """Test ExemplarDigest model."""

    def test_create_minimal_digest(self):
        """Test creating digest with minimal required fields."""
        digest = ExemplarDigest(
            meta={"source": "Emergency", "tokens": 0, "paragraphs": 0}
        )
        assert digest.schema_version == "ExemplarDigest@2"
        assert digest.meta.source == "Emergency"

    def test_digest_serialization(self):
        """Test JSON serialization/deserialization."""
        digest = ExemplarDigest(
            meta={"source": "Test", "tokens": 100, "paragraphs": 10}
        )
        json_data = digest.model_dump_json()
        loaded = ExemplarDigest.model_validate_json(json_data)
        assert loaded.meta.source == "Test"


class TestStorySpec:
    """Test StorySpec model."""

    def test_create_minimal_spec(self):
        """Test creating spec with minimal required fields."""
        spec = StorySpec(
            meta={"story_id": "test_001", "seed": 137},
            content={
                "setting": {"place": "Test City", "time": "Now", "weather_budget": []},
                "characters": [],
            },
        )
        assert spec.schema_version == "StorySpec@2"
        assert spec.meta.story_id == "test_001"

    def test_spec_defaults(self):
        """Test default values are applied."""
        spec = StorySpec(
            meta={"story_id": "test_001", "seed": 137},
            content={
                "setting": {"place": "Test", "time": "Now", "weather_budget": []},
                "characters": [],
            },
        )
        assert spec.voice.person == "first"
        assert spec.form.dialogue_ratio == 0.25


class TestGenerationConfig:
    """Test GenerationConfig model."""

    def test_create_default_config(self):
        """Test creating config with defaults."""
        config = GenerationConfig()
        assert config.schema_version == "GenerationConfig@2"
        assert config.seed == 137
        assert config.num_candidates == 8

    def test_config_optimizer_settings(self):
        """Test optimizer settings."""
        config = GenerationConfig()
        assert config.optimizer.mode == "adamish"
        assert config.optimizer.max_iters == 10


class TestEvalReport:
    """Test EvalReport model."""

    def test_create_minimal_report(self):
        """Test creating report with minimal fields."""
        report = EvalReport(
            run_id="run_001",
            candidate_id="cand_001",
            config_hash="abc123",
        )
        assert report.schema_version == "EvalReport@2"
        assert report.run_id == "run_001"

    def test_report_scores(self):
        """Test score fields."""
        report = EvalReport(
            run_id="run_001",
            candidate_id="cand_001",
            config_hash="abc123",
        )
        assert report.scores.overall == 0.0
        assert report.pass_fail is False


class TestAuthorProfile:
    """Test AuthorProfile model."""

    def test_create_default_profile(self):
        """Test creating profile with defaults."""
        profile = AuthorProfile()
        assert profile.schema_version == "AuthorProfile@1"
        assert profile.syntax.avg_sentence_len == 14
        assert profile.profanity.allowed is False

    def test_profile_validation(self):
        """Test profile validation."""
        profile = AuthorProfile(
            lexicon={"prefer": ["test"], "avoid": ["bad"]},
            syntax={"avg_sentence_len": 20, "variance": 0.6, "em_dash": "frequent"},
        )
        assert profile.syntax.avg_sentence_len == 20
