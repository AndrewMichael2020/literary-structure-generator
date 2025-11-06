"""
LLM adapters for component-specific tasks.

Provides high-level functions for each LLM-using component:
- label_motifs: Label motif anchors with thematic tags
- name_imagery: Name imagery palette categories
- paraphrase_beats: Generate beat summaries
- stylefit_score: Score text against style spec
- repair_pass: Fix constraint violations

Each adapter:
1. Loads the appropriate prompt template
2. Gets the configured client via router
3. Optionally checks cache
4. Calls the LLM
5. Logs the call with version/params/checksums
6. Returns processed output
"""

import hashlib
import json
from pathlib import Path

from literary_structure_generator.llm.cache import LLMCache
from literary_structure_generator.llm.router import get_client, get_params
from literary_structure_generator.utils.decision_logger import log_decision
from literary_structure_generator.utils.profanity import structural_bleep

# Global cache instance
_cache: LLMCache | None = None


def _get_cache() -> LLMCache:
    """Get or create global cache instance."""
    global _cache  # noqa: PLW0603
    if _cache is None:
        _cache = LLMCache()
    return _cache


def _load_prompt_template(template_name: str) -> tuple[str, str]:
    """
    Load prompt template from prompts/ directory.

    Args:
        template_name: Template filename (e.g., 'motif_labeling.v1.md')

    Returns:
        Tuple of (template_content, version)
    """
    # Find prompts directory
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    if not prompts_dir.exists():
        prompts_dir = Path.cwd() / "prompts"

    template_path = prompts_dir / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")

    # Extract version from template (look for "Version: vX")
    version = "v1"  # Default
    for line in content.split("\n"):
        if "**Version:**" in line:
            version = line.split("**Version:**")[1].strip()
            break

    return content, version


def _compute_semantic_checksum(items: list[str]) -> str:
    """
    Compute checksum over normalized list output.

    Args:
        items: List of strings

    Returns:
        SHA256 hash (first 16 chars)
    """
    # Normalize: strip, lowercase, sort
    normalized = sorted([item.strip().lower() for item in items if item.strip()])
    combined = "\n".join(normalized)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _log_llm_call(
    component: str,
    model: str,
    template_version: str,
    params: dict,
    input_hash: str,
    output_checksum: str | None = None,
    run_id: str = "run_001",
    iteration: int = 0,
):
    """
    Log LLM call with drift control metadata.

    Args:
        component: Component name
        model: Model identifier
        template_version: Prompt template version
        params: LLM parameters
        input_hash: Hash of input
        output_checksum: Optional checksum of output
        run_id: Run identifier
        iteration: Iteration number
    """
    # Compute params hash
    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]

    metadata = {
        "component": component,
        "model": model,
        "template_version": template_version,
        "params_hash": params_hash,
        "input_hash": input_hash,
    }

    if output_checksum:
        metadata["llm_checksum"] = output_checksum

    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="LLM",
        decision=f"{component} call with {model}",
        reasoning=f"LLM call for {component} using prompt {template_version}",
        parameters={
            "temperature": params.get("temperature"),
            "max_tokens": params.get("max_tokens"),
        },
        metadata=metadata,
    )


def label_motifs(
    anchors: list[str],
    run_id: str = "run_001",
    iteration: int = 0,
    use_cache: bool = True,
) -> list[str]:
    """
    Label motif anchors with thematic tags.

    Args:
        anchors: List of motif anchor phrases
        run_id: Run identifier for logging
        iteration: Iteration number
        use_cache: Whether to use cache

    Returns:
        List of thematic labels (same length as anchors)
    """
    component = "motif_labeler"

    # Load template
    template, version = _load_prompt_template("motif_labeling.v1.md")

    # Format prompt
    anchors_str = "\n".join(anchors)
    prompt = template.replace("{anchors}", anchors_str)

    # Get client and params
    client = get_client(component)
    params = get_params(component)

    # Check cache
    input_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    cached = None
    if use_cache:
        cache = _get_cache()
        cached = cache.get(component, params["model"], version, params, prompt)

    if cached:
        labels = [line.strip() for line in cached.split("\n") if line.strip()]
    else:
        # Call LLM
        response = client.complete(prompt)

        # Parse response
        labels = [line.strip() for line in response.split("\n") if line.strip()]

        # Store in cache
        if use_cache:
            cache.put(component, params["model"], version, params, prompt, response)

    # Apply grit filter to all labels
    labels = [structural_bleep(label) for label in labels]

    # Compute checksum
    checksum = _compute_semantic_checksum(labels)

    # Log call
    _log_llm_call(
        component, params["model"], version, params, input_hash, checksum, run_id, iteration
    )

    return labels


def name_imagery(
    phrases: list[str],
    run_id: str = "run_001",
    iteration: int = 0,
    use_cache: bool = True,
) -> list[str]:
    """
    Name imagery palette categories.

    Args:
        phrases: List of imagery phrases
        run_id: Run identifier
        iteration: Iteration number
        use_cache: Whether to use cache

    Returns:
        List of category names (same length as phrases)
    """
    component = "imagery_namer"

    # Load template
    template, version = _load_prompt_template("imagery_naming.v1.md")

    # Format prompt
    phrases_str = "\n".join(phrases)
    prompt = template.replace("{phrases}", phrases_str)

    # Get client and params
    client = get_client(component)
    params = get_params(component)

    # Check cache
    input_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    cached = None
    if use_cache:
        cache = _get_cache()
        cached = cache.get(component, params["model"], version, params, prompt)

    if cached:
        names = [line.strip() for line in cached.split("\n") if line.strip()]
    else:
        # Call LLM
        response = client.complete(prompt)

        # Parse response
        names = [line.strip() for line in response.split("\n") if line.strip()]

        # Store in cache
        if use_cache:
            cache.put(component, params["model"], version, params, prompt, response)

    # Apply grit filter to all names
    names = [structural_bleep(name) for name in names]

    # Compute checksum
    checksum = _compute_semantic_checksum(names)

    # Log call
    _log_llm_call(
        component, params["model"], version, params, input_hash, checksum, run_id, iteration
    )

    return names


def paraphrase_beats(
    functions: list[str],
    register_hint: str = "neutral",
    run_id: str = "run_001",
    iteration: int = 0,
    use_cache: bool = True,
) -> list[str]:
    """
    Paraphrase beat functions into summaries.

    Args:
        functions: List of beat function descriptions
        register_hint: Register style (clinical, lyrical, terse, neutral)
        run_id: Run identifier
        iteration: Iteration number
        use_cache: Whether to use cache

    Returns:
        List of beat summaries (same length as functions)
    """
    component = "beat_paraphraser"

    # Load template
    template, version = _load_prompt_template("beat_paraphrase.v1.md")

    # Format prompt
    functions_str = "\n".join(functions)
    prompt = template.replace("{functions}", functions_str)
    prompt = prompt.replace("{register_hint}", register_hint)

    # Get client and params
    client = get_client(component)
    params = get_params(component)

    # Check cache
    input_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    cached = None
    if use_cache:
        cache = _get_cache()
        cached = cache.get(component, params["model"], version, params, prompt)

    if cached:
        summaries = [line.strip() for line in cached.split("\n") if line.strip()]
    else:
        # Call LLM
        response = client.complete(prompt)

        # Parse response
        summaries = [line.strip() for line in response.split("\n") if line.strip()]

        # Store in cache
        if use_cache:
            cache.put(component, params["model"], version, params, prompt, response)

    # Apply grit filter to all summaries
    summaries = [structural_bleep(summary) for summary in summaries]

    # Compute checksum
    checksum = _compute_semantic_checksum(summaries)

    # Log call
    _log_llm_call(
        component, params["model"], version, params, input_hash, checksum, run_id, iteration
    )

    return summaries


def stylefit_score(
    text: str,
    spec_summary: str,
    run_id: str = "run_001",
    iteration: int = 0,
    use_cache: bool = True,
) -> float:
    """
    Score how well text matches style specification.

    Args:
        text: Generated text to score
        spec_summary: Style specification summary
        run_id: Run identifier
        iteration: Iteration number
        use_cache: Whether to use cache

    Returns:
        Score between 0.0 and 1.0
    """
    component = "stylefit"

    # Load template
    template, version = _load_prompt_template("stylefit.v1.md")

    # Format prompt
    prompt = template.replace("{text}", text)
    prompt = prompt.replace("{spec_summary}", spec_summary)

    # Get client and params
    client = get_client(component)
    params = get_params(component)

    # Check cache
    input_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    cached = None
    if use_cache:
        cache = _get_cache()
        cached = cache.get(component, params["model"], version, params, prompt)

    if cached:
        response = cached
    else:
        # Call LLM
        response = client.complete(prompt)

        # Store in cache
        if use_cache:
            cache.put(component, params["model"], version, params, prompt, response)

    # Parse score
    try:
        score = float(response.strip())
        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
    except ValueError:
        score = 0.5  # Default if parsing fails

    # Log call (no checksum for single float)
    _log_llm_call(component, params["model"], version, params, input_hash, None, run_id, iteration)

    return score


def repair_pass(
    text: str,
    constraints: dict,
    run_id: str = "run_001",
    iteration: int = 0,
    use_cache: bool = True,
) -> str:
    """
    Repair text to fix constraint violations.

    Args:
        text: Text to repair
        constraints: Dictionary of constraints and issues
        run_id: Run identifier
        iteration: Iteration number
        use_cache: Whether to use cache

    Returns:
        Repaired text
    """
    component = "repair_pass"

    # Load template
    template, version = _load_prompt_template("repair_pass.v1.md")

    # Format constraints
    constraints_str = "\n".join([f"- {k}: {v}" for k, v in constraints.items()])

    # Format prompt
    prompt = template.replace("{text}", text)
    prompt = prompt.replace("{constraints}", constraints_str)

    # Get client and params
    client = get_client(component)
    params = get_params(component)

    # Check cache
    input_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    cached = None
    if use_cache:
        cache = _get_cache()
        cached = cache.get(component, params["model"], version, params, prompt)

    if cached:
        repaired = cached
    else:
        # Call LLM
        repaired = client.complete(prompt)

        # Store in cache
        if use_cache:
            cache.put(component, params["model"], version, params, prompt, repaired)

    # Apply grit filter to repaired text
    repaired = structural_bleep(repaired.strip())

    # Log call (no checksum for single text)
    _log_llm_call(component, params["model"], version, params, input_hash, None, run_id, iteration)

    return repaired
