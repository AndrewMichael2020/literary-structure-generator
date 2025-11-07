"""
Tests for LLM routing configuration features.

Tests cover:
- Finalists-only repair pass gating
- Tie-break model support
- Configuration parameter handling
"""

import json
import tempfile
from pathlib import Path

import pytest

from literary_structure_generator.llm.router import get_params, load_routing_config
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.pipeline.generate_candidates import (
    generate_candidates,
    generate_single_candidate,
)


class TestFinalistsOnlyGating:
    """Test finalists-only repair pass gating."""

    def test_finalists_only_config_loaded(self):
        """Test that finalists_only parameter is loaded from config."""
        params = get_params("repair_pass")
        assert "finalists_only" in params
        assert params["finalists_only"] == 3

    def test_other_components_no_finalists_only(self):
        """Test that other components don't have finalists_only."""
        params = get_params("beat_paraphraser")
        assert "finalists_only" not in params or params["finalists_only"] is None

    def test_generate_single_candidate_skip_repair(self, basic_spec, basic_digest):
        """Test that generate_single_candidate can skip repair."""
        # Create minimal test data
        exemplar_text = "This is a short exemplar story. It has multiple sentences."
        
        candidate = generate_single_candidate(
            spec=basic_spec,
            digest=basic_digest,
            exemplar_text=exemplar_text,
            candidate_id="test_001",
            run_id="test_run",
            skip_repair=True,
        )
        
        # When skip_repair=True, stitched and repaired should be the same
        assert candidate["stitched"] == candidate["repaired"]
        assert "is_finalist" not in candidate["metadata"]

    def test_generate_single_candidate_with_repair(self, basic_spec, basic_digest):
        """Test that generate_single_candidate applies repair by default."""
        exemplar_text = "This is a short exemplar story. It has multiple sentences."
        
        candidate = generate_single_candidate(
            spec=basic_spec,
            digest=basic_digest,
            exemplar_text=exemplar_text,
            candidate_id="test_001",
            run_id="test_run",
            skip_repair=False,
        )
        
        # Repair may or may not change text, but should be applied
        assert "repaired" in candidate
        assert "final_guard" in candidate["metadata"]


class TestTieBreakModel:
    """Test tie-break model configuration."""

    def test_stylefit_has_tie_break_model(self):
        """Test that stylefit component has tie_break_model configured."""
        params = get_params("stylefit")
        assert "tie_break_model" in params
        assert params["tie_break_model"] == "gpt-5"

    def test_tie_break_model_not_in_other_components(self):
        """Test that other components don't have tie_break_model."""
        params = get_params("beat_paraphraser")
        assert "tie_break_model" not in params or params["tie_break_model"] is None


class TestConfigurationChanges:
    """Test that configuration changes are applied correctly."""

    def test_beat_paraphraser_uses_gpt5_mini(self):
        """Test that beat_paraphraser is configured with gpt-5-mini."""
        params = get_params("beat_paraphraser")
        assert params["model"] == "gpt-5-mini"

    def test_stylefit_uses_gpt5_mini(self):
        """Test that stylefit is configured with gpt-5-mini."""
        params = get_params("stylefit")
        assert params["model"] == "gpt-5-mini"

    def test_repair_pass_uses_opus(self):
        """Test that repair_pass is configured with opus-4.1."""
        params = get_params("repair_pass")
        assert params["model"] == "opus-4.1"

    def test_config_has_all_components(self):
        """Test that config file has all expected components."""
        config = load_routing_config()
        components = config.get("components", {})
        
        expected_components = [
            "motif_labeler",
            "imagery_namer", 
            "beat_paraphraser",
            "stylefit",
            "beat_generator",
            "repair_pass",
        ]
        
        for component in expected_components:
            assert component in components, f"Missing component: {component}"


class TestFinalistsMetadata:
    """Test that finalists mode adds proper metadata."""

    def test_finalists_mode_metadata_present(self, basic_spec, basic_digest):
        """Test that finalists mode adds metadata to result."""
        exemplar_text = "This is a short exemplar story. It has multiple sentences."
        
        # Generate with finalists mode enabled
        result = generate_candidates(
            spec=basic_spec,
            digest=basic_digest,
            exemplar_text=exemplar_text,
            n_candidates=3,
            run_id="test_finalists_run",
        )
        
        # Check metadata
        assert "finalists_only_mode" in result["meta"]
        assert result["meta"]["finalists_only_mode"] is True
        assert "num_finalists" in result["meta"]
        assert result["meta"]["num_finalists"] == 3

    def test_candidates_have_finalist_flag(self, basic_spec, basic_digest):
        """Test that candidates have is_finalist flag when finalists mode is used."""
        exemplar_text = "This is a short exemplar story. It has multiple sentences."
        
        result = generate_candidates(
            spec=basic_spec,
            digest=basic_digest,
            exemplar_text=exemplar_text,
            n_candidates=5,
            run_id="test_finalists_flags",
        )
        
        # Count finalists
        finalists = [c for c in result["candidates"] if c["metadata"].get("is_finalist", False)]
        non_finalists = [c for c in result["candidates"] if not c["metadata"].get("is_finalist", False)]
        
        # Should have 3 finalists and 2 non-finalists
        assert len(finalists) == 3
        assert len(non_finalists) == 2


# Fixtures

@pytest.fixture
def basic_spec():
    """Create a basic StorySpec for testing."""
    from literary_structure_generator.models.story_spec import (
        BeatSpec,
        Form,
        MetaInfo,
        Content,
        Setting,
        Character,
    )
    
    # Create minimal beat map
    beats = [
        BeatSpec(
            id="beat_001",
            function="Opening scene",
            target_words=50,
            cadence="measured",
        ),
        BeatSpec(
            id="beat_002", 
            function="Development",
            target_words=50,
            cadence="building",
        ),
    ]
    
    return StorySpec(
        meta=MetaInfo(
            story_id="test_story",
            seed=42,
        ),
        form=Form(
            beat_map=beats,
        ),
        content=Content(
            setting=Setting(place="test location", time="present"),
            characters=[Character(name="Test", role="protagonist")],
            motifs=["test"],
            imagery_palette=["light"],
            props=["desk"],
        ),
    )


@pytest.fixture
def basic_digest():
    """Create a basic ExemplarDigest for testing."""
    from literary_structure_generator.models.exemplar_digest import (
        MetaInfo as DigestMeta,
    )
    
    return ExemplarDigest(
        meta=DigestMeta(
            source="test_exemplar",
            tokens=100,
            paragraphs=3,
        ),
        stylometry={
            "sentence_len_hist": [5, 10, 15],
            "type_token_ratio": 0.6,
            "mtld": 70.0,
        },
        discourse={
            "beat_map": [
                {"id": "beat_001", "function": "opening"},
                {"id": "beat_002", "function": "development"},
            ]
        },
        pacing={"paragraph_lengths": [20, 30]},
        coherence={"entity_map": {"Test": ["they"]}},
        motifs={"labels": ["test"]},
        imagery={"palette": ["light"]},
    )
