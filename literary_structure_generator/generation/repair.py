"""
Repair pass module

LLM-based repair for generated text:
    - Fix minor POV leaks
    - Balance paragraph rhythm
    - Avoid unearned epiphanies
    - Cadence checking
    - Profanity filtering with [bleep] replacement
"""

from literary_structure_generator.llm.router import get_client
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.utils.profanity import structural_bleep


def calculate_paragraph_variance(text: str) -> float:
    """
    Calculate variance in paragraph lengths.

    Args:
        text: Input text

    Returns:
        Variance in paragraph token counts
    """
    if not text:
        return 0.0

    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if len(paragraphs) < 2:
        return 0.0

    # Calculate lengths
    lengths = [len(p.split()) for p in paragraphs]

    # Calculate variance
    mean = sum(lengths) / len(lengths)
    return sum((x - mean) ** 2 for x in lengths) / len(lengths)


def build_repair_notes(text: str, spec: StorySpec, issues: list[str]) -> dict:
    """
    Build repair notes for LLM prompt.

    Args:
        text: Text to repair
        spec: Story specification
        issues: List of specific issues to address

    Returns:
        Dictionary of repair notes
    """
    notes = {
        "issues": issues,
        "voice_person": spec.voice.person,
        "voice_distance": spec.voice.distance,
        "target_words": spec.constraints.length_words.target,
    }

    # Check paragraph variance
    variance = calculate_paragraph_variance(text)
    if variance > 100:  # Threshold for high variance
        notes["issues"].append(
            "High paragraph length variance - consider rebalancing for better rhythm"
        )

    return notes


def repair_text(
    stitched: str,
    spec: StorySpec,
    notes: dict | None = None,
) -> str:
    """
    Apply LLM repair pass to stitched text.

    Fixes minor issues while preserving narrative intent:
        - POV leaks
        - Paragraph rhythm
        - Unearned epiphanies
        - Style consistency

    Args:
        stitched: Stitched beat text to repair
        spec: Story specification
        notes: Optional repair notes/issues

    Returns:
        Repaired text
    """
    if notes is None:
        notes = {"issues": []}

    # Build full notes
    repair_notes = build_repair_notes(stitched, spec, notes.get("issues", []))

    # Format constraints for prompt
    constraints_text = "\n".join(f"- {issue}" for issue in repair_notes["issues"])

    if not constraints_text:
        # No issues to fix, return as-is
        return stitched

    # Load repair prompt template
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "repair_pass.v1.md"

    if prompt_path.exists():
        with open(prompt_path, encoding="utf-8") as f:
            template = f.read()
    else:
        # Fallback template
        template = """# Repair Pass

**Original Text:**
```
{text}
```

**Constraints:**
{constraints}

**Repaired Text:**"""

    # Format prompt
    prompt = template.replace("{text}", stitched).replace("{constraints}", constraints_text)

    # Get LLM client for repair_pass component
    client = get_client("repair_pass")

    # Generate repaired text
    repaired = client.complete(prompt)

    # Clean up code block markers if present
    if "```" in repaired:
        parts = repaired.split("```")
        if len(parts) >= 2:
            # Extract content between code blocks
            repaired = parts[1].strip()
            # Remove language identifier if present
            if "\n" in repaired:
                lines = repaired.split("\n", 1)
                if lines[0].strip() in ["", "text", "markdown"]:
                    repaired = lines[1] if len(lines) > 1 else repaired

    # Apply profanity filter to repaired text and return
    return structural_bleep(repaired.strip())
