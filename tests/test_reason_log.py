"""
Tests for ReasonLog model and decision logger

Validates ReasonLog schema and decision logging functionality.
"""

import json
import pytest
from pathlib import Path
import tempfile
import shutil

from literary_structure_generator.models.reason_log import ReasonLog
from literary_structure_generator.utils.decision_logger import log_decision, load_decision_logs


class TestReasonLog:
    """Test ReasonLog model."""

    def test_create_minimal_reason_log(self):
        """Test creating ReasonLog with minimal required fields."""
        log = ReasonLog(
            run_id="run_001",
            iteration=0,
            agent="SpecSynth",
            decision="Test decision",
            reasoning="Test reasoning",
        )
        assert log.schema_version == "ReasonLog@1"
        assert log.run_id == "run_001"
        assert log.agent == "SpecSynth"

    def test_reason_log_with_all_fields(self):
        """Test creating ReasonLog with all fields."""
        log = ReasonLog(
            run_id="run_001",
            iteration=2,
            agent="Evaluator",
            decision="Select best candidate",
            reasoning="Candidate 3 has highest overall score",
            parameters={"best_score": 0.85, "candidate_id": "cand_003"},
            outcome="Selected candidate cand_003",
            metadata={"num_candidates": 8},
        )
        assert log.iteration == 2
        assert log.parameters["best_score"] == 0.85
        assert log.outcome == "Selected candidate cand_003"

    def test_reason_log_serialization(self):
        """Test JSON serialization/deserialization."""
        log = ReasonLog(
            run_id="run_001",
            iteration=0,
            agent="Digest",
            decision="Use GPT-4 for analysis",
            reasoning="GPT-4 provides best beat labeling",
        )
        json_data = log.model_dump_json()
        loaded = ReasonLog.model_validate_json(json_data)
        assert loaded.agent == "Digest"
        assert loaded.decision == "Use GPT-4 for analysis"

    def test_reason_log_timestamp(self):
        """Test that timestamp is auto-generated."""
        log = ReasonLog(
            run_id="run_001",
            iteration=0,
            agent="Generator",
            decision="Test decision",
            reasoning="Test reasoning",
        )
        assert log.timestamp is not None
        assert "T" in log.timestamp  # ISO 8601 format


class TestDecisionLogger:
    """Test decision logging utilities."""

    def setup_method(self):
        """Create temporary directory for test outputs."""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_log_decision_creates_file(self):
        """Test that log_decision creates a JSON file."""
        log = log_decision(
            run_id="test_run",
            iteration=0,
            agent="SpecSynth",
            decision="Test decision",
            reasoning="Test reasoning",
            output_dir=self.test_dir,
        )

        # Check that file was created
        log_dir = Path(self.test_dir) / "test_run" / "iter_0" / "reason_logs"
        assert log_dir.exists()
        log_files = list(log_dir.glob("SpecSynth_*.json"))
        assert len(log_files) == 1

    def test_log_decision_with_parameters(self):
        """Test logging with parameters and metadata."""
        log = log_decision(
            run_id="test_run",
            iteration=1,
            agent="Optimizer",
            decision="Update config",
            reasoning="Apply gradients",
            parameters={"step_size": 0.1, "beta1": 0.8},
            outcome="Config updated",
            metadata={"convergence": False},
            output_dir=self.test_dir,
        )

        # Load and verify content
        log_dir = Path(self.test_dir) / "test_run" / "iter_1" / "reason_logs"
        log_files = list(log_dir.glob("Optimizer_*.json"))
        assert len(log_files) == 1

        with open(log_files[0]) as f:
            data = json.load(f)
            assert data["agent"] == "Optimizer"
            assert data["parameters"]["step_size"] == 0.1
            assert data["outcome"] == "Config updated"

    def test_log_multiple_decisions(self):
        """Test logging multiple decisions."""
        for i in range(3):
            log_decision(
                run_id="test_run",
                iteration=0,
                agent="Generator",
                decision=f"Generate candidate {i}",
                reasoning=f"Creating candidate {i}",
                output_dir=self.test_dir,
            )

        # Check that all files were created
        log_dir = Path(self.test_dir) / "test_run" / "iter_0" / "reason_logs"
        log_files = list(log_dir.glob("Generator_*.json"))
        assert len(log_files) == 3

    def test_load_decision_logs_all(self):
        """Test loading all decision logs for a run."""
        # Create some logs
        log_decision(
            run_id="test_run",
            iteration=0,
            agent="Digest",
            decision="Decision 1",
            reasoning="Reason 1",
            output_dir=self.test_dir,
        )
        log_decision(
            run_id="test_run",
            iteration=0,
            agent="SpecSynth",
            decision="Decision 2",
            reasoning="Reason 2",
            output_dir=self.test_dir,
        )

        # Load all logs
        logs = load_decision_logs("test_run", output_dir=self.test_dir)
        assert len(logs) == 2
        assert logs[0].agent in ["Digest", "SpecSynth"]

    def test_load_decision_logs_by_iteration(self):
        """Test loading logs filtered by iteration."""
        # Create logs in different iterations
        log_decision(
            run_id="test_run",
            iteration=0,
            agent="Generator",
            decision="Iter 0 decision",
            reasoning="Reason",
            output_dir=self.test_dir,
        )
        log_decision(
            run_id="test_run",
            iteration=1,
            agent="Generator",
            decision="Iter 1 decision",
            reasoning="Reason",
            output_dir=self.test_dir,
        )

        # Load only iteration 0
        logs = load_decision_logs("test_run", iteration=0, output_dir=self.test_dir)
        assert len(logs) == 1
        assert logs[0].iteration == 0

    def test_load_decision_logs_by_agent(self):
        """Test loading logs filtered by agent."""
        # Create logs from different agents
        log_decision(
            run_id="test_run",
            iteration=0,
            agent="Evaluator",
            decision="Eval decision",
            reasoning="Reason",
            output_dir=self.test_dir,
        )
        log_decision(
            run_id="test_run",
            iteration=0,
            agent="Optimizer",
            decision="Opt decision",
            reasoning="Reason",
            output_dir=self.test_dir,
        )

        # Load only Evaluator logs
        logs = load_decision_logs("test_run", agent="Evaluator", output_dir=self.test_dir)
        assert len(logs) == 1
        assert logs[0].agent == "Evaluator"

    def test_load_decision_logs_empty_run(self):
        """Test loading logs from non-existent run."""
        logs = load_decision_logs("nonexistent_run", output_dir=self.test_dir)
        assert len(logs) == 0
