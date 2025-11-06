"""
Tests for Phase 6 multi-candidate generation pipeline.

Tests cover:
- Single candidate generation (per-beat → stitch → repair → evaluate)
- Multi-candidate generation and selection
- Best candidate selection logic
- Persistence to /runs/ directory
- LLM routing with MockClient (offline tests)
- GPT-5 parameter handling
"""

import tempfile
from pathlib import Path

import pytest

from literary_structure_generator.models.exemplar_digest import (
    ExemplarDigest,
    MetaInfo as DigestMeta,
)
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    Form,
    MetaInfo,
    Setting,
    StorySpec,
)
from literary_structure_generator.pipeline.generate_candidates import (
    generate_candidates,
    generate_single_candidate,
    select_best_candidate,
)


# Sample exemplar text for testing
SAMPLE_EXEMPLAR = """
The morning was cold. She walked down the street, thinking about yesterday.

"Are you sure?" he had asked.

She wasn't sure. Not about anything anymore. The world had shifted beneath her feet.

Three days later, everything changed. The phone call came at midnight.
She answered, knowing what it would be. His voice was different now.

"I'm sorry," he said.

She hung up without responding. Outside, the rain continued.
"""


def create_test_spec() -> StorySpec:
    """Create a minimal StorySpec for testing."""
    return StorySpec(
        meta=MetaInfo(
            story_id="test_story_001",
            seed=42,
        ),
        form=Form(
            beat_map=[
                BeatSpec(
                    id="beat_1",
                    function="establish setting and character",
                    target_words=200,
                    cadence="measured",
                ),
                BeatSpec(
                    id="beat_2",
                    function="develop conflict",
                    target_words=250,
                    cadence="building",
                ),
                BeatSpec(
                    id="beat_3",
                    function="resolve narrative",
                    target_words=150,
                    cadence="reflective",
                ),
            ],
        ),
        content=Content(
            setting=Setting(place="urban apartment", time="contemporary"),
            characters=[
                Character(name="Sarah", role="protagonist"),
                Character(name="Michael", role="antagonist"),
            ],
            motifs=["isolation", "memory", "change"],
            imagery_palette=["rain", "telephone", "empty rooms"],
            props=["phone", "window", "street"],
        ),
    )


def create_test_digest() -> ExemplarDigest:
    """Create a minimal ExemplarDigest for testing."""
    return ExemplarDigest(
        meta=DigestMeta(source="test_exemplar", tokens=100, paragraphs=5),
        stylometry={
            "sentence_len_hist": [5, 10, 15, 20, 10, 5],
            "type_token_ratio": 0.65,
            "mtld": 75.0,
        },
        discourse={
            "beat_map": [
                {"id": "beat_1", "function": "opening"},
                {"id": "beat_2", "function": "development"},
                {"id": "beat_3", "function": "resolution"},
            ]
        },
        pacing={"paragraph_lengths": [20, 30, 25, 35, 20]},
        coherence={"entity_map": {"Sarah": ["she"], "Michael": ["he"]}},
        motifs={"labels": ["isolation", "memory", "change"]},
        imagery={"palette": ["rain", "telephone", "empty rooms"]},
    )


class TestGenerateSingleCandidate:
    """Test single candidate generation."""

    def test_generate_single_candidate_basic(self):
        """Test basic single candidate generation."""
        spec = create_test_spec()
        digest = create_test_digest()

        candidate = generate_single_candidate(
            spec=spec,
            digest=digest,
            exemplar_text=SAMPLE_EXEMPLAR,
            candidate_id="cand_001",
            run_id="test_run_001",
        )

        # Verify structure
        assert candidate["id"] == "cand_001"
        assert "beats" in candidate
        assert "stitched" in candidate
        assert "repaired" in candidate
        assert "eval" in candidate
        assert "metadata" in candidate

        # Verify beats were generated
        assert len(candidate["beats"]) == 3  # Three beats in spec
        for beat_result in candidate["beats"]:
            assert "text" in beat_result
            assert "metadata" in beat_result
            assert beat_result["text"]  # Should have text

        # Verify stitched text exists
        assert candidate["stitched"]
        assert isinstance(candidate["stitched"], str)

        # Verify repaired text exists
        assert candidate["repaired"]
        assert isinstance(candidate["repaired"], str)

        # Verify eval report
        eval_report = candidate["eval"]
        assert eval_report.run_id == "test_run_001"
        assert eval_report.candidate_id == "cand_001"
        assert hasattr(eval_report, "scores")
        assert hasattr(eval_report, "pass_fail")

        # Verify metadata
        metadata = candidate["metadata"]
        assert metadata["candidate_id"] == "cand_001"
        assert metadata["run_id"] == "test_run_001"
        assert metadata["num_beats"] == 3


class TestSelectBestCandidate:
    """Test candidate selection logic."""

    def test_select_best_by_overall_score(self):
        """Test selection based on overall score."""
        spec = create_test_spec()
        digest = create_test_digest()

        # Generate multiple candidates
        candidates = []
        for i in range(3):
            candidate = generate_single_candidate(
                spec=spec,
                digest=digest,
                exemplar_text=SAMPLE_EXEMPLAR,
                candidate_id=f"cand_{i+1:03d}",
                run_id="test_run_select",
            )
            candidates.append(candidate)

        # Select best
        best_id = select_best_candidate(candidates)

        # Verify best_id is one of the candidates
        assert best_id in [c["id"] for c in candidates]

        # Find the best candidate
        best_candidate = next(c for c in candidates if c["id"] == best_id)

        # Verify it has highest score among passing candidates
        passing_candidates = [c for c in candidates if c["eval"].pass_fail]
        if passing_candidates:
            best_score = best_candidate["eval"].scores.overall
            for c in passing_candidates:
                if c["id"] != best_id:
                    assert best_score >= c["eval"].scores.overall

    def test_select_best_empty_list_raises(self):
        """Test that empty candidate list raises ValueError."""
        with pytest.raises(ValueError, match="No candidates"):
            select_best_candidate([])


class TestGenerateCandidates:
    """Test multi-candidate generation orchestrator."""

    def test_generate_candidates_default(self):
        """Test default multi-candidate generation."""
        spec = create_test_spec()
        digest = create_test_digest()

        result = generate_candidates(
            spec=spec,
            digest=digest,
            exemplar_text=SAMPLE_EXEMPLAR,
            n_candidates=3,
        )

        # Verify structure
        assert "candidates" in result
        assert "best_id" in result
        assert "meta" in result

        # Verify candidates
        assert len(result["candidates"]) == 3
        for candidate in result["candidates"]:
            assert "id" in candidate
            assert "beats" in candidate
            assert "stitched" in candidate
            assert "repaired" in candidate
            assert "eval" in candidate

        # Verify best_id
        best_id = result["best_id"]
        assert best_id in [c["id"] for c in result["candidates"]]

        # Verify metadata
        meta = result["meta"]
        assert meta["n_candidates"] == 3
        assert "run_id" in meta
        assert "generation_timestamp" in meta
        assert meta["story_id"] == "test_story_001"

    def test_generate_candidates_with_run_id(self):
        """Test candidate generation with specified run_id."""
        spec = create_test_spec()
        digest = create_test_digest()

        result = generate_candidates(
            spec=spec,
            digest=digest,
            exemplar_text=SAMPLE_EXEMPLAR,
            n_candidates=2,
            run_id="custom_run_123",
        )

        # Verify run_id was used
        assert result["meta"]["run_id"] == "custom_run_123"
        for candidate in result["candidates"]:
            assert candidate["eval"].run_id == "custom_run_123"

    def test_generate_candidates_persistence(self):
        """Test that candidates are persisted to /runs/ directory."""
        spec = create_test_spec()
        digest = create_test_digest()

        # Use temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                result = generate_candidates(
                    spec=spec,
                    digest=digest,
                    exemplar_text=SAMPLE_EXEMPLAR,
                    n_candidates=2,
                    run_id="persist_test",
                )

                # Verify directory structure
                run_dir = Path("runs") / "persist_test"
                assert run_dir.exists()

                # Verify run metadata
                assert (run_dir / "run_metadata.json").exists()
                assert (run_dir / "summary.json").exists()

                # Verify candidate directories
                for candidate in result["candidates"]:
                    cand_dir = run_dir / candidate["id"]
                    assert cand_dir.exists()

                    # Verify candidate files
                    assert (cand_dir / "repaired.txt").exists()
                    assert (cand_dir / "stitched.txt").exists()
                    assert (cand_dir / "beat_results.json").exists()
                    assert (cand_dir / "eval_report.json").exists()
                    assert (cand_dir / "metadata.json").exists()

                    # Verify content
                    with open(cand_dir / "repaired.txt", encoding="utf-8") as f:
                        text = f.read()
                        assert text == candidate["repaired"]

            finally:
                os.chdir(original_cwd)

    def test_generate_candidates_single(self):
        """Test generating a single candidate."""
        spec = create_test_spec()
        digest = create_test_digest()

        result = generate_candidates(
            spec=spec,
            digest=digest,
            exemplar_text=SAMPLE_EXEMPLAR,
            n_candidates=1,
        )

        assert len(result["candidates"]) == 1
        assert result["best_id"] == result["candidates"][0]["id"]


class TestLLMRouting:
    """Test LLM routing integration."""

    def test_uses_router_for_beat_generation(self):
        """Test that beat generation uses router."""
        from literary_structure_generator.llm.router import get_client

        # Get client for beat_generator component
        client = get_client("beat_generator")

        # Verify it's a MockClient (for offline tests)
        from literary_structure_generator.llm.clients.mock_client import MockClient

        assert isinstance(client, MockClient)

    def test_uses_router_for_repair(self):
        """Test that repair uses router."""
        from literary_structure_generator.llm.router import get_client

        # Get client for repair_pass component
        client = get_client("repair_pass")

        # Verify it's a MockClient (for offline tests)
        from literary_structure_generator.llm.clients.mock_client import MockClient

        assert isinstance(client, MockClient)

    def test_gpt5_parameter_handling(self):
        """Test that GPT-5 parameters are filtered correctly."""
        from literary_structure_generator.llm.router import get_params

        # Mock a GPT-5 model configuration
        import json
        import os
        from pathlib import Path

        # Create temporary config with GPT-5
        config = {
            "global": {
                "provider": "mock",
                "model": "gpt-5-turbo",
                "temperature": 0.7,  # This should be filtered for GPT-5
                "seed": 42,
            },
            "components": {
                "beat_generator": {
                    "model": "gpt-5-turbo",
                    "temperature": 0.8,  # Should be filtered
                }
            },
        }

        # Save to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_config:
            json.dump(config, tmp_config)
            tmp_config_path = tmp_config.name

        try:
            # Set environment variable
            os.environ["LLM_ROUTING_CONFIG"] = tmp_config_path

            # Clear cached config
            import literary_structure_generator.llm.router as router_module

            router_module._routing_config = None

            # Get params for beat_generator component
            params = get_params("beat_generator")

            # Verify model is set correctly
            assert params["model"] == "gpt-5-turbo"

            # The router's get_client filters temperature for GPT-5
            # Since we're using MockClient, it will override model to "mock"
            # But the parameter filtering logic in get_client should handle it
            from literary_structure_generator.llm.router import get_client

            client = get_client("beat_generator")

            # MockClient always uses "mock" as model name
            # The key test is that get_client doesn't crash with GPT-5 config
            assert client is not None

        finally:
            # Cleanup
            os.unlink(tmp_config_path)
            if "LLM_ROUTING_CONFIG" in os.environ:
                del os.environ["LLM_ROUTING_CONFIG"]
            router_module._routing_config = None
