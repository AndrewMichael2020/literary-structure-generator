"""
Integration test demonstrating decision logging across agents

This test simulates the workflow with multiple agents logging decisions.
"""

import tempfile
import shutil
from pathlib import Path

from literary_structure_generator.utils.decision_logger import log_decision, load_decision_logs


def test_workflow_decision_logging():
    """Test full workflow with all agents logging decisions."""
    test_dir = tempfile.mkdtemp()

    try:
        run_id = "test_workflow"
        iteration = 0

        # Digest agent decision
        log_decision(
            run_id=run_id,
            iteration=iteration,
            agent="Digest",
            decision="Use GPT-4 for LLM analysis",
            reasoning="GPT-4 provides best beat labeling and motif extraction",
            parameters={"model": "gpt-4", "filepath": "Emergency.txt"},
            output_dir=test_dir,
        )

        # SpecSynth agent decision
        log_decision(
            run_id=run_id,
            iteration=iteration,
            agent="SpecSynth",
            decision="Set voice.person to 'first'",
            reasoning="Exemplar shows 95% first-person pronouns",
            parameters={"first_person_ratio": 0.95, "alpha_exemplar": 0.7},
            outcome="voice.person='first'",
            output_dir=test_dir,
        )

        # Generator agent decisions
        for cand_id in range(3):
            log_decision(
                run_id=run_id,
                iteration=iteration,
                agent="Generator",
                decision=f"Generate candidate {cand_id}",
                reasoning=f"Using temperature sweep for candidate {cand_id}",
                parameters={"candidate_id": cand_id, "seed": 137 + cand_id},
                output_dir=test_dir,
            )

        # Evaluator agent decision
        log_decision(
            run_id=run_id,
            iteration=iteration,
            agent="Evaluator",
            decision="Run full evaluation suite",
            reasoning="Evaluating all candidates with 7 metrics",
            parameters={"num_candidates": 3, "evaluator_suite": ["stylefit", "formfit"]},
            output_dir=test_dir,
        )

        # Optimizer agent decision
        log_decision(
            run_id=run_id,
            iteration=iteration,
            agent="Optimizer",
            decision="Select best candidate and update config",
            reasoning="Candidate 2 has highest overall score (0.85)",
            parameters={"best_candidate_id": 2, "best_score": 0.85},
            outcome="Updated config with gradients",
            output_dir=test_dir,
        )

        # Load and verify all logs
        all_logs = load_decision_logs(run_id, output_dir=test_dir)
        assert (
            len(all_logs) == 7
        )  # 1 Digest + 1 SpecSynth + 3 Generator + 1 Evaluator + 1 Optimizer

        # Verify each agent has logs
        digest_logs = load_decision_logs(run_id, agent="Digest", output_dir=test_dir)
        assert len(digest_logs) == 1
        assert digest_logs[0].agent == "Digest"

        spec_logs = load_decision_logs(run_id, agent="SpecSynth", output_dir=test_dir)
        assert len(spec_logs) == 1
        assert spec_logs[0].outcome == "voice.person='first'"

        gen_logs = load_decision_logs(run_id, agent="Generator", output_dir=test_dir)
        assert len(gen_logs) == 3

        eval_logs = load_decision_logs(run_id, agent="Evaluator", output_dir=test_dir)
        assert len(eval_logs) == 1

        opt_logs = load_decision_logs(run_id, agent="Optimizer", output_dir=test_dir)
        assert len(opt_logs) == 1

        # Verify directory structure
        iter_dir = Path(test_dir) / run_id / f"iter_{iteration}"
        assert iter_dir.exists()

        reason_logs_dir = iter_dir / "reason_logs"
        assert reason_logs_dir.exists()

        # Verify JSON files exist
        log_files = list(reason_logs_dir.glob("*.json"))
        assert len(log_files) == 7

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_multi_iteration_logging():
    """Test logging across multiple iterations."""
    test_dir = tempfile.mkdtemp()

    try:
        run_id = "test_multi_iter"

        # Log decisions across 3 iterations
        for iteration in range(3):
            log_decision(
                run_id=run_id,
                iteration=iteration,
                agent="Optimizer",
                decision=f"Iteration {iteration} update",
                reasoning=f"Updating config based on iteration {iteration} results",
                parameters={"iteration": iteration, "score": 0.7 + iteration * 0.05},
                output_dir=test_dir,
            )

        # Load all logs
        all_logs = load_decision_logs(run_id, output_dir=test_dir)
        assert len(all_logs) == 3

        # Load logs for specific iteration
        iter_1_logs = load_decision_logs(run_id, iteration=1, output_dir=test_dir)
        assert len(iter_1_logs) == 1
        assert iter_1_logs[0].iteration == 1
        assert iter_1_logs[0].parameters["score"] == 0.75

        # Verify directory structure
        run_dir = Path(test_dir) / run_id
        iter_dirs = list(run_dir.glob("iter_*"))
        assert len(iter_dirs) == 3

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
