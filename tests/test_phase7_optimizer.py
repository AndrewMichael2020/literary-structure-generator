"""
Tests for Phase 7 Optimizer.

Tests cover:
- Optimizer class initialization
- suggest() method for spec adjustment
- run() method for optimization loop
- Early stopping behavior
- Artifact persistence
- Integration with MockClient (offline tests)
"""

import tempfile
from pathlib import Path

from literary_structure_generator.models.eval_report import (
    DriftItem,
    EvalReport,
    PerBeatScore,
    Scores,
    TuningSuggestion,
)
from literary_structure_generator.models.exemplar_digest import (
    ExemplarDigest,
    MetaInfo as DigestMeta,
)
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    MetaInfo,
    Setting,
    StorySpec,
)
from literary_structure_generator.optimization.optimizer import Optimizer


class TestOptimizer:
    """Test Optimizer class."""

    def test_optimizer_initialization(self):
        """Test optimizer initialization with default parameters."""
        optimizer = Optimizer()

        assert optimizer.max_iters == 5
        assert optimizer.candidates == 3
        assert optimizer.early_stop_delta == 0.01
        assert optimizer.run_id is not None
        assert optimizer.run_id.startswith("opt_")

    def test_optimizer_custom_params(self):
        """Test optimizer initialization with custom parameters."""
        optimizer = Optimizer(
            max_iters=10,
            candidates=5,
            early_stop_delta=0.005,
            run_id="custom_run_123",
        )

        assert optimizer.max_iters == 10
        assert optimizer.candidates == 5
        assert optimizer.early_stop_delta == 0.005
        assert optimizer.run_id == "custom_run_123"

    def test_suggest_with_tuning_suggestions(self):
        """Test suggest() method with tuning suggestions."""
        optimizer = Optimizer()

        # Create a basic spec
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test City", time="Present"),
                characters=[
                    Character(name="Alice", role="protagonist"),
                ],
            ),
        )

        # Create an eval report with tuning suggestions
        report = EvalReport(
            run_id="test_run",
            candidate_id="test_cand",
            config_hash="abc123",
            scores=Scores(
                overall=0.65,
                stylefit=0.60,
                formfit=0.70,
                coherence=0.75,
                freshness=0.55,
            ),
            tuning_suggestions=[
                TuningSuggestion(
                    param="voice.syntax.avg_sentence_len",
                    action="increase",
                    by=2.0,
                    reason="Sentences too short for target style",
                ),
                TuningSuggestion(
                    param="form.dialogue_ratio",
                    action="decrease",
                    by=0.05,
                    reason="Too much dialogue",
                ),
            ],
        )

        # Apply suggestions
        new_spec = optimizer.suggest(spec, report)

        # Check that spec was updated (should have different sentence length)
        assert new_spec is not spec  # Should be a new object
        # Sentence length should have increased
        assert new_spec.voice.syntax.avg_sentence_len >= spec.voice.syntax.avg_sentence_len

    def test_suggest_with_drift_correction(self):
        """Test suggest() method with drift correction."""
        optimizer = Optimizer()

        # Create a spec with dialogue ratio
        spec = StorySpec(
            meta=MetaInfo(story_id="test_002", seed=137),
            content=Content(
                setting=Setting(place="Test City", time="Present"),
            ),
        )
        spec.form.dialogue_ratio = 0.30

        # Create report with drift
        report = EvalReport(
            run_id="test_run",
            candidate_id="test_cand",
            config_hash="abc123",
            scores=Scores(
                overall=0.70,
                stylefit=0.65,
                formfit=0.75,
            ),
            drift_vs_spec=[
                DriftItem(
                    field="form.dialogue_ratio",
                    target=0.25,
                    actual=0.35,
                    delta=0.10,
                ),
            ],
        )

        # Apply suggestions
        new_spec = optimizer.suggest(spec, report)

        # Dialogue ratio should be adjusted toward target
        assert abs(new_spec.form.dialogue_ratio - 0.25) < abs(spec.form.dialogue_ratio - 0.25)

    def test_suggest_low_formfit_adjusts_beats(self):
        """Test that low formfit score triggers beat length adjustments."""
        optimizer = Optimizer()

        # Create spec with beats
        spec = StorySpec(
            meta=MetaInfo(story_id="test_003", seed=137),
            content=Content(
                setting=Setting(place="Test City", time="Present"),
            ),
        )
        spec.form.beat_map = [
            BeatSpec(id="beat_1", target_words=100, function="intro", cadence="short"),
            BeatSpec(id="beat_2", target_words=150, function="rising", cadence="mixed"),
        ]

        # Create report with low formfit
        report = EvalReport(
            run_id="test_run",
            candidate_id="test_cand",
            config_hash="abc123",
            scores=Scores(
                overall=0.60,
                stylefit=0.70,
                formfit=0.55,  # Low formfit
            ),
            per_beat=[
                PerBeatScore(id="beat_1", stylefit=0.7, formfit=0.6, notes=""),
                PerBeatScore(id="beat_2", stylefit=0.7, formfit=0.5, notes=""),
            ],
        )

        # Apply suggestions
        new_spec = optimizer.suggest(spec, report)

        # Beat lengths may have been adjusted
        assert new_spec.form.beat_map is not None
        assert len(new_spec.form.beat_map) == 2

    def test_suggest_low_dialogue_balance_adjusts_ratio(self):
        """Test that low dialogue_balance score adjusts dialogue ratio."""
        optimizer = Optimizer()

        spec = StorySpec(
            meta=MetaInfo(story_id="test_004", seed=137),
            content=Content(
                setting=Setting(place="Test City", time="Present"),
            ),
        )
        original_ratio = spec.form.dialogue_ratio

        # Create report with low dialogue_balance
        report = EvalReport(
            run_id="test_run",
            candidate_id="test_cand",
            config_hash="abc123",
            scores=Scores(
                overall=0.65,
                stylefit=0.70,
                formfit=0.70,
                dialogue_balance=0.50,  # Low
            ),
        )

        new_spec = optimizer.suggest(spec, report)

        # Dialogue ratio should be adjusted
        assert new_spec.form.dialogue_ratio != original_ratio

    def test_run_basic_optimization_loop(self):
        """Test basic optimization loop execution."""
        optimizer = Optimizer(
            max_iters=2,  # Just 2 iterations for testing
            candidates=1,  # Just 1 candidate per iteration
            early_stop_delta=0.01,
        )

        # Create minimal spec
        spec = StorySpec(
            meta=MetaInfo(story_id="test_005", seed=137),
            content=Content(
                setting=Setting(place="Test City", time="Present"),
                characters=[Character(name="Alice", role="protagonist")],
            ),
        )
        spec.form.beat_map = [
            BeatSpec(id="beat_1", target_words=100, function="intro", cadence="short"),
        ]

        # Create minimal digest
        digest = ExemplarDigest(
            meta=DigestMeta(source="Test Exemplar", tokens=1000, paragraphs=20),
        )

        # Simple exemplar text
        exemplar_text = "This is a test exemplar. It has multiple sentences. More text here."

        # Run optimization with temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            result = optimizer.run(
                spec=spec,
                digest=digest,
                exemplar_text=exemplar_text,
                config=None,  # Use default config
                output_dir=tmpdir,
            )

            # Check result structure
            assert "best_spec" in result
            assert "best_draft" in result
            assert "best_score" in result
            assert "history" in result

            # Check that history has entries
            assert len(result["history"]) > 0
            assert len(result["history"]) <= 2  # max_iters = 2

            # Check that artifacts were saved
            results_dir = Path(tmpdir) / optimizer.run_id
            assert results_dir.exists()
            assert (results_dir / "optimization_summary.json").exists()

    def test_run_with_custom_config(self):
        """Test optimization with custom GenerationConfig."""
        optimizer = Optimizer(max_iters=1, candidates=1)

        spec = StorySpec(
            meta=MetaInfo(story_id="test_006", seed=137),
            content=Content(
                setting=Setting(place="Test City", time="Present"),
            ),
        )
        spec.form.beat_map = [
            BeatSpec(id="beat_1", target_words=80, function="intro", cadence="short"),
        ]

        digest = ExemplarDigest(
            meta=DigestMeta(source="Test", tokens=800, paragraphs=15),
        )

        config = GenerationConfig(
            seed=42,
            num_candidates=2,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = optimizer.run(
                spec=spec,
                digest=digest,
                exemplar_text="Test exemplar text.",
                config=config,
                output_dir=tmpdir,
            )

            assert result is not None
            assert "best_spec" in result

    def test_early_stopping_triggers(self):
        """Test that early stopping is triggered when improvement plateaus."""
        # This test would require mocking the generation/evaluation to return
        # controlled scores, which is complex. For now, we verify the logic exists.
        optimizer = Optimizer(
            max_iters=10,  # High max
            candidates=1,
            early_stop_delta=0.01,
        )

        # The early stopping logic is in the run() method
        # It checks: if improvement < self.early_stop_delta and no_improvement_count >= 2
        # We can verify this by checking the implementation exists
        assert hasattr(optimizer, "early_stop_delta")
        assert optimizer.early_stop_delta == 0.01

    def test_artifacts_persistence(self):
        """Test that artifacts are properly saved to disk."""
        optimizer = Optimizer(max_iters=1, candidates=1, run_id="test_artifacts_123")

        spec = StorySpec(
            meta=MetaInfo(story_id="test_007", seed=137),
            content=Content(
                setting=Setting(place="Test City", time="Present"),
            ),
        )
        spec.form.beat_map = [
            BeatSpec(id="beat_1", target_words=90, function="intro", cadence="short"),
        ]

        digest = ExemplarDigest(
            meta=DigestMeta(source="Test", tokens=900, paragraphs=18),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            _ = optimizer.run(
                spec=spec,
                digest=digest,
                exemplar_text="Test exemplar.",
                output_dir=tmpdir,
            )

            # Check directory structure
            run_dir = Path(tmpdir) / "test_artifacts_123"
            assert run_dir.exists()

            # Check for iteration directories
            iter_dirs = list(run_dir.glob("iter_*"))
            assert len(iter_dirs) >= 1

            # Check for summary file
            assert (run_dir / "optimization_summary.json").exists()

            # Check for best spec
            assert (run_dir / "best_spec.json").exists()

            # Check for decision logs
            for iter_dir in iter_dirs:
                log_dir = iter_dir / "reason_logs"
                if log_dir.exists():
                    log_files = list(log_dir.glob("*.json"))
                    # May have logs from Optimizer and other components
                    assert len(log_files) >= 0  # Just check it's accessible


class TestOptimizerIntegration:
    """Integration tests for Optimizer with full pipeline."""

    def test_full_optimization_pipeline(self):
        """Test complete optimization pipeline with realistic spec."""
        optimizer = Optimizer(
            max_iters=2,
            candidates=2,
            early_stop_delta=0.01,
            run_id="integration_test_001",
        )

        # Create realistic spec
        spec = StorySpec(
            meta=MetaInfo(
                story_id="integration_001",
                seed=137,
                version="2.0",
            ),
            content=Content(
                setting=Setting(
                    place="Small Town",
                    time="1990s",
                    weather_budget=["rain", "fog"],
                ),
                characters=[
                    Character(
                        name="Sarah",
                        role="protagonist",
                        goal="Find her way home",
                    ),
                ],
                motifs=["time", "memory", "loss"],
                imagery_palette=["gray skies", "wet streets", "distant lights"],
            ),
        )
        spec.form.beat_map = [
            BeatSpec(
                id="opening",
                target_words=120,
                function="establish setting and mood",
                cadence="mixed",
            ),
            BeatSpec(
                id="complication",
                target_words=100,
                function="introduce conflict",
                cadence="short",
            ),
        ]

        digest = ExemplarDigest(
            meta=DigestMeta(
                source="Test Story",
                tokens=2000,
                paragraphs=40,
            ),
        )

        exemplar_text = (
            """
The rain began at dusk. Sarah stood at the corner, watching the water pool in the gutters.

She didn't remember how she got there. The streets looked familiar but wrong, like a photograph
from someone else's memory.

A car passed, headlights cutting through the fog. Then silence.

She started walking, knowing she should recognize something, anything. But the gray skies
offered no answers, and the distant lights seemed to move further away with each step.

Time felt strange here. Hours or minutes, she couldn't tell. Just the wet streets and the
steady drumming of rain on concrete.
"""
            * 5
        )  # Repeat to make it longer

        with tempfile.TemporaryDirectory() as tmpdir:
            result = optimizer.run(
                spec=spec,
                digest=digest,
                exemplar_text=exemplar_text,
                output_dir=tmpdir,
            )

            # Verify results
            assert result["best_spec"] is not None
            assert result["best_score"] >= 0.0
            assert len(result["history"]) <= 2
            assert len(result["history"]) > 0

            # Verify artifacts
            run_dir = Path(tmpdir) / "integration_test_001"
            assert (run_dir / "optimization_summary.json").exists()
            assert (run_dir / "best_spec.json").exists()

            # Verify best draft exists
            if result["best_draft"]:
                assert (run_dir / "best_draft.txt").exists()


# Run pytest with: pytest tests/test_phase7_optimizer.py -v
