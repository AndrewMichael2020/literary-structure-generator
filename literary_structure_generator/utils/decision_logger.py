"""
Decision Logger

Utility for logging agent decisions across workflow runs.
Provides a simple log_decision() function that can be called from any agent
without circular imports.

Each decision is saved as a ReasonLog JSON file in the /runs/{run_id}/iter_{iteration}/ directory.
"""

import json
from pathlib import Path
from typing import Any, Optional

from literary_structure_generator.models.reason_log import ReasonLog


def log_decision(
    run_id: str,
    iteration: int,
    agent: str,
    decision: str,
    reasoning: str,
    parameters: Optional[dict[str, Any]] = None,
    outcome: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    output_dir: str = "runs",
) -> ReasonLog:
    """
    Log an agent decision to a ReasonLog JSON file.

    Creates a timestamped decision log entry and saves it to:
    {output_dir}/{run_id}/iter_{iteration}/reason_logs/{agent}_{timestamp}.json

    Args:
        run_id: Unique run identifier
        iteration: Iteration number (0-indexed)
        agent: Agent name (Digest, SpecSynth, Generator, Evaluator, Optimizer)
        decision: Brief description of the decision made
        reasoning: Explanation of why this decision was made
        parameters: Optional dict of parameters that influenced the decision
        outcome: Optional outcome or result of the decision
        metadata: Optional additional context or metadata
        output_dir: Base output directory for runs (default: "runs")

    Returns:
        ReasonLog object that was created and saved

    Example:
        >>> log_decision(
        ...     run_id="run_001",
        ...     iteration=0,
        ...     agent="SpecSynth",
        ...     decision="Set voice.person to 'first'",
        ...     reasoning="Exemplar shows 95% first-person pronouns",
        ...     parameters={"first_person_ratio": 0.95},
        ...     outcome="voice.person='first'"
        ... )
    """
    # Create ReasonLog object
    reason_log = ReasonLog(
        run_id=run_id,
        iteration=iteration,
        agent=agent,
        decision=decision,
        reasoning=reasoning,
        parameters=parameters or {},
        outcome=outcome,
        metadata=metadata or {},
    )

    # Create output directory structure
    log_dir = Path(output_dir) / run_id / f"iter_{iteration}" / "reason_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = reason_log.timestamp.replace(":", "-").replace(".", "-")
    filename = f"{agent}_{timestamp}.json"
    filepath = log_dir / filename

    # Save to JSON file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(reason_log.model_dump(by_alias=True), f, indent=2)

    return reason_log


def load_decision_logs(
    run_id: str,
    iteration: Optional[int] = None,
    agent: Optional[str] = None,
    output_dir: str = "runs",
) -> list[ReasonLog]:
    """
    Load decision logs for a run, optionally filtered by iteration and/or agent.

    Args:
        run_id: Unique run identifier
        iteration: Optional iteration number to filter by
        agent: Optional agent name to filter by
        output_dir: Base output directory for runs (default: "runs")

    Returns:
        List of ReasonLog objects matching the filters

    Example:
        >>> logs = load_decision_logs("run_001", iteration=0)
        >>> logs = load_decision_logs("run_001", agent="Evaluator")
    """
    logs = []
    run_dir = Path(output_dir) / run_id

    if not run_dir.exists():
        return logs

    # Determine which iteration directories to search
    if iteration is not None:
        iter_dirs = [run_dir / f"iter_{iteration}"]
    else:
        iter_dirs = sorted(run_dir.glob("iter_*"))

    # Load logs from each iteration directory
    for iter_dir in iter_dirs:
        log_dir = iter_dir / "reason_logs"
        if not log_dir.exists():
            continue

        # Find matching log files
        if agent is not None:
            log_files = sorted(log_dir.glob(f"{agent}_*.json"))
        else:
            log_files = sorted(log_dir.glob("*.json"))

        # Load each log file
        for log_file in log_files:
            with open(log_file, encoding="utf-8") as f:
                data = json.load(f)
                logs.append(ReasonLog(**data))

    return logs
