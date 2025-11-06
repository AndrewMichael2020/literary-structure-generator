"""
Coherence Graph Fit Evaluator

Evaluates entity continuity in generated text:
- Builds light entity map from draft
- Penalizes abrupt aliasing/unseen name spikes
- Tracks entity mention consistency

Returns score 0..1
"""

import re
from collections import defaultdict


def extract_entities(text: str) -> list[tuple[str, str]]:
    """
    Extract named entities from text using simple heuristics.

    Args:
        text: Text to analyze

    Returns:
        List of (entity, type) tuples
    """
    entities = []

    # Pattern for capitalized words (simple NER proxy)
    # Exclude common sentence starters
    sentences = re.split(r"[.!?]+", text)

    for sentence in sentences:
        words = sentence.split()
        for i, word in enumerate(words):
            # Skip first word of sentence (often capitalized anyway)
            if i == 0:
                continue

            # Check if word is capitalized and not a common word
            if word and word[0].isupper() and len(word) > 1:
                # Clean punctuation
                clean_word = re.sub(r"[^\w\s-]", "", word)
                if clean_word and clean_word not in ["I", "The", "A", "An"]:
                    # Simple type inference
                    if clean_word.lower() in ["hospital", "clinic", "office", "building", "house"]:
                        entity_type = "PLACE"
                    elif clean_word.endswith("s") or clean_word.lower() in [
                        "company",
                        "department",
                    ]:
                        entity_type = "ORG"
                    else:
                        entity_type = "PERSON"  # Default assumption

                    entities.append((clean_word, entity_type))

    return entities


def build_entity_map(entities: list[tuple[str, str]]) -> dict[str, dict]:
    """
    Build entity map with mention counts and positions.

    Args:
        entities: List of (entity, type) tuples

    Returns:
        Dictionary mapping entity names to metadata
    """
    entity_map = defaultdict(lambda: {"type": "", "mentions": 0, "positions": [], "aliases": set()})

    for i, (entity, entity_type) in enumerate(entities):
        entity_map[entity]["type"] = entity_type
        entity_map[entity]["mentions"] += 1
        entity_map[entity]["positions"].append(i)

        # Track potential aliases (entities with same first word)
        first_word = entity.split()[0] if " " in entity else entity
        entity_map[entity]["aliases"].add(first_word)

    return dict(entity_map)


def detect_aliasing_issues(entity_map: dict[str, dict]) -> tuple[float, list[str]]:
    """
    Detect abrupt aliasing (same entity with different names without introduction).

    Args:
        entity_map: Entity map from build_entity_map

    Returns:
        Tuple of (penalty score 0..1, list of issues)
    """
    issues = []
    penalty = 0.0

    # Group entities by potential aliases
    alias_groups = defaultdict(list)
    for entity, metadata in entity_map.items():
        for alias in metadata["aliases"]:
            alias_groups[alias].append(entity)

    # Check for suspicious alias groups (multiple full names with same first name)
    for alias, full_names in alias_groups.items():
        if len(full_names) > 1:
            # Check if these are truly different entities or just aliasing
            # If mentioned close together without clarification, it's confusing
            positions = []
            for name in full_names:
                positions.extend(entity_map[name]["positions"])

            if len(positions) > 1:
                positions.sort()
                # Check for close mentions without clarification
                for i in range(len(positions) - 1):
                    if positions[i + 1] - positions[i] < 5:  # Within 5 mentions
                        issues.append(f"Potential aliasing confusion: {full_names}")
                        penalty += 0.1

    # Cap penalty
    penalty = min(1.0, penalty)

    return penalty, issues


def detect_name_spikes(entity_map: dict[str, dict], threshold: int = 10) -> tuple[float, list[str]]:
    """
    Detect unseen name spikes (entities appearing suddenly many times).

    Args:
        entity_map: Entity map from build_entity_map
        threshold: Mention count threshold for spike detection

    Returns:
        Tuple of (penalty score 0..1, list of issues)
    """
    issues = []
    penalty = 0.0

    for entity, metadata in entity_map.items():
        mentions = metadata["mentions"]

        # Check if entity appears many times
        if mentions >= threshold:
            # Check if concentrated in one region (spike)
            positions = metadata["positions"]
            if len(positions) > 1:
                position_range = max(positions) - min(positions)
                # If all mentions within small range, it's a spike
                if position_range < len(positions) * 2:
                    issues.append(
                        f"Name spike: {entity} appears {mentions} times in concentrated region"
                    )
                    penalty += 0.15

    # Cap penalty
    penalty = min(1.0, penalty)

    return penalty, issues


def check_entity_introduction(text: str, entity_map: dict[str, dict]) -> float:
    """
    Check if major entities are properly introduced.

    Args:
        text: Full text
        entity_map: Entity map

    Returns:
        Score 0..1 (higher is better)
    """
    # Heuristic: Major entities (high mention count) should appear in first third
    total_entities = len(entity_map)
    if total_entities == 0:
        return 1.0  # No entities, no problem

    # Find major entities (top 50% by mentions)
    sorted_entities = sorted(entity_map.items(), key=lambda x: x[1]["mentions"], reverse=True)

    major_entities = sorted_entities[: max(1, total_entities // 2)]

    # Check if they appear early
    early_count = 0
    for _entity, metadata in major_entities:
        if metadata["positions"]:
            first_pos = min(metadata["positions"])
            # Early means in first third of entity mentions
            if first_pos < total_entities // 3:
                early_count += 1

    return early_count / len(major_entities) if major_entities else 1.0


def evaluate_coherence_graph_fit(text: str) -> dict[str, any]:
    """
    Evaluate entity continuity and coherence.

    Args:
        text: Generated text to evaluate

    Returns:
        Dictionary with overall score and component details
    """
    # Extract entities
    entities = extract_entities(text)

    # Build entity map
    entity_map = build_entity_map(entities)

    # Detect aliasing issues
    aliasing_penalty, aliasing_issues = detect_aliasing_issues(entity_map)

    # Detect name spikes
    spike_penalty, spike_issues = detect_name_spikes(entity_map)

    # Check entity introduction
    introduction_score = check_entity_introduction(text, entity_map)

    # Calculate overall score
    # Start with 1.0 and apply penalties
    overall = 1.0 - aliasing_penalty - spike_penalty
    overall = overall * introduction_score
    overall = max(0.0, min(1.0, overall))

    return {
        "overall": overall,
        "entity_count": len(entity_map),
        "aliasing_penalty": aliasing_penalty,
        "spike_penalty": spike_penalty,
        "introduction_score": introduction_score,
        "issues": aliasing_issues + spike_issues,
        "entities": {
            name: {"type": meta["type"], "mentions": meta["mentions"]}
            for name, meta in entity_map.items()
        },
    }
