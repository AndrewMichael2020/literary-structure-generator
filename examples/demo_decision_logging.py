#!/usr/bin/env python
"""
Demonstration of decision logging across workflow runs.

This script shows how each agent can log decisions during a workflow run.
"""

from literary_structure_generator.utils.decision_logger import log_decision, load_decision_logs


def demonstrate_decision_logging():
    """Demonstrate decision logging for all agents."""
    run_id = "demo_run_001"
    iteration = 0

    print("=" * 80)
    print("Decision Logging Demonstration")
    print("=" * 80)
    print()

    # Digest agent logs decision
    print("[Digest Agent] Logging decision about LLM model selection...")
    digest_log = log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Digest",
        decision="Use GPT-4 for LLM-assisted analysis",
        reasoning="GPT-4 provides superior beat labeling, motif extraction, and voice analysis compared to GPT-3.5",
        parameters={
            "model": "gpt-4",
            "filepath": "Emergency.txt",
            "exemplar_length": 2500,
        },
        metadata={"stage": "initialization"},
    )
    print(f"  ✓ Logged to: runs/{run_id}/iter_{iteration}/reason_logs/")
    print()

    # SpecSynth agent logs decision
    print("[SpecSynth Agent] Logging decision about voice parameters...")
    spec_log = log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="SpecSynth",
        decision="Set voice.person to 'first' based on exemplar digest",
        reasoning="Exemplar digest shows 95% first-person pronouns with intimate narrative distance",
        parameters={
            "first_person_ratio": 0.95,
            "distance": "intimate",
            "alpha_exemplar": 0.7,
        },
        outcome="voice.person='first', voice.distance='intimate'",
    )
    print(f"  ✓ Outcome: {spec_log.outcome}")
    print()

    # Generator agent logs decisions
    print("[Generator Agent] Logging ensemble generation decisions...")
    for candidate_id in range(3):
        gen_log = log_decision(
            run_id=run_id,
            iteration=iteration,
            agent="Generator",
            decision=f"Generate candidate {candidate_id}",
            reasoning=f"Using temperature sweep [{0.7 + candidate_id * 0.1:.1f}] for diversity",
            parameters={
                "candidate_id": candidate_id,
                "seed": 137 + candidate_id,
                "temperature": 0.7 + candidate_id * 0.1,
            },
        )
        print(f"  ✓ Candidate {candidate_id} logged")
    print()

    # Evaluator agent logs decision
    print("[Evaluator Agent] Logging evaluation suite decision...")
    eval_log = log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Evaluator",
        decision="Run full evaluation suite on 3 candidates",
        reasoning="Using 7 metrics: stylefit, formfit, coherence, freshness, overlap_guard, valence_arc_fit, cadence",
        parameters={
            "num_candidates": 3,
            "evaluator_suite": ["stylefit", "formfit", "coherence", "freshness", "overlap_guard", "valence_arc_fit", "cadence"],
            "objective_weights": {
                "stylefit": 0.3,
                "formfit": 0.3,
                "coherence": 0.25,
                "freshness": 0.1,
                "cadence": 0.05,
            },
        },
    )
    print("  ✓ Evaluation suite logged")
    print()

    # Optimizer agent logs decision
    print("[Optimizer Agent] Logging optimization decision...")
    opt_log = log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Optimizer",
        decision="Select candidate 2 and update config with Adam-ish optimizer",
        reasoning="Candidate 2 achieved highest overall score (0.847). Applying gradients to improve next iteration.",
        parameters={
            "best_candidate_id": 2,
            "best_score": 0.847,
            "step_size": 0.1,
            "beta1": 0.8,
            "beta2": 0.95,
        },
        outcome="Updated GenerationConfig with gradient-based parameter adjustments",
    )
    print(f"  ✓ Outcome: {opt_log.outcome}")
    print()

    # Load and display all logs
    print("=" * 80)
    print("Loading Decision Logs")
    print("=" * 80)
    print()

    all_logs = load_decision_logs(run_id)
    print(f"Total logs for {run_id}: {len(all_logs)}")
    print()

    # Display summary by agent
    agents = ["Digest", "SpecSynth", "Generator", "Evaluator", "Optimizer"]
    for agent in agents:
        agent_logs = load_decision_logs(run_id, agent=agent)
        print(f"  {agent:12} : {len(agent_logs):2} log(s)")
    print()

    # Show detailed log for SpecSynth
    print("=" * 80)
    print("Sample Decision Log (SpecSynth)")
    print("=" * 80)
    spec_logs = load_decision_logs(run_id, agent="SpecSynth")
    if spec_logs:
        log = spec_logs[0]
        print(f"Schema:     {log.schema_version}")
        print(f"Timestamp:  {log.timestamp}")
        print(f"Run ID:     {log.run_id}")
        print(f"Iteration:  {log.iteration}")
        print(f"Agent:      {log.agent}")
        print(f"Decision:   {log.decision}")
        print(f"Reasoning:  {log.reasoning}")
        print(f"Parameters: {log.parameters}")
        print(f"Outcome:    {log.outcome}")
    print()

    print("=" * 80)
    print("Demonstration Complete!")
    print("=" * 80)
    print()
    print(f"Decision logs saved to: runs/{run_id}/iter_{iteration}/reason_logs/")
    print("Each agent's decisions are logged as JSON files for reproducibility.")


if __name__ == "__main__":
    demonstrate_decision_logging()
