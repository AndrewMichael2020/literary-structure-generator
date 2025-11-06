"""
StyleFit LLM Evaluator

LLM-based style scoring using routed client:
- Uses "stylefit" component from router
- Loads prompt template from prompts/stylefit_eval.v1.md
- Router must drop unsupported params for GPT-5 family

Returns score 0..1
"""

import re
from pathlib import Path
from typing import Dict

from literary_structure_generator.llm.router import get_client
from literary_structure_generator.models.story_spec import StorySpec


def load_prompt_template(template_name: str = "stylefit_eval.v1.md") -> str:
    """
    Load prompt template from prompts directory.
    
    Args:
        template_name: Template file name
        
    Returns:
        Template content as string
    """
    # Look for template in multiple locations
    possible_paths = [
        Path(__file__).parent.parent.parent / "prompts" / template_name,
        Path.cwd() / "prompts" / template_name,
    ]
    
    for path in possible_paths:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    
    # Fallback to embedded template
    return """# Stylefit Scoring Prompt Template

**Version:** v1  
**Component:** stylefit  
**Purpose:** Score how well generated text matches a style specification

---

## Task

You are given a piece of generated text and a style specification summary. Your task is to score (0.0-1.0) how well the text matches the specified style.

## Scoring Criteria

Evaluate the text on:
- **Sentence structure**: Does it match the target sentence length and complexity?
- **Voice/POV**: Does it maintain consistent person and distance?
- **Diction**: Does the word choice match the register?
- **Rhythm**: Does the pacing and cadence feel right?
- **Dialogue style**: If present, does it match conventions?

## Scoring Scale

- **0.9-1.0**: Excellent match, natural and consistent
- **0.7-0.89**: Good match, minor deviations
- **0.5-0.69**: Moderate match, noticeable deviations
- **0.3-0.49**: Poor match, significant deviations
- **0.0-0.29**: Very poor match, style mismatch

## Output Format

Return only a single floating-point number between 0.0 and 1.0.

---

## Your Task

**Style Spec:**
{spec_summary}

**Text:**
{text}

**Score (0.0-1.0):**
"""


def create_spec_summary(spec: StorySpec) -> str:
    """
    Create concise style spec summary for prompt.
    
    Args:
        spec: StorySpec object
        
    Returns:
        Summary string
    """
    summary_parts = [
        f"Person: {spec.voice.person}",
        f"Tense: {spec.voice.tense_strategy.primary}",
        f"Distance: {spec.voice.distance}",
        f"Avg sentence length: {spec.voice.syntax.avg_sentence_len} words",
        f"Parataxis ratio: {spec.voice.syntax.parataxis_vs_hypotaxis:.2f}",
        f"Dialogue ratio: {spec.form.dialogue_ratio:.2f}",
    ]
    
    # Add register sliders
    register = spec.voice.register_sliders
    if register:
        register_str = ", ".join(f"{k}: {v:.2f}" for k, v in register.items())
        summary_parts.append(f"Register: {register_str}")
    
    return "\n".join(summary_parts)


def parse_llm_score(response: str) -> float:
    """
    Parse LLM response to extract score.
    
    Args:
        response: LLM response text
        
    Returns:
        Extracted score 0..1
    """
    # Try to find a number in the response
    # Look for patterns like "0.85" or "Score: 0.85"
    patterns = [
        r'(\d+\.\d+)',  # Decimal number
        r'(\d+)',       # Integer
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            try:
                score = float(match.group(1))
                # Ensure in valid range
                if score > 1.0:
                    score = score / 100.0  # Convert percentage to ratio
                score = max(0.0, min(1.0, score))
                return score
            except ValueError:
                continue
    
    # Default to 0.5 if can't parse
    return 0.5


def evaluate_stylefit_llm(
    text: str,
    spec: StorySpec,
    use_llm: bool = True
) -> Dict[str, any]:
    """
    Evaluate style using LLM via router.
    
    Args:
        text: Generated text to evaluate
        spec: StorySpec with style targets
        use_llm: Whether to use LLM (if False, returns None)
        
    Returns:
        Dictionary with score and metadata
    """
    if not use_llm:
        return {
            "overall": None,
            "enabled": False,
            "note": "LLM stylefit disabled"
        }
    
    # Get routed client for "stylefit" component
    client = get_client("stylefit")
    
    # Load prompt template
    template = load_prompt_template()
    
    # Create spec summary
    spec_summary = create_spec_summary(spec)
    
    # Truncate text if too long (to fit in context)
    max_text_length = 2000  # characters
    if len(text) > max_text_length:
        text_sample = text[:max_text_length] + "..."
    else:
        text_sample = text
    
    # Fill template
    prompt = template.format(spec_summary=spec_summary, text=text_sample)
    
    # Call LLM
    try:
        response = client.complete(prompt)
        
        # Parse score
        score = parse_llm_score(response)
        
        return {
            "overall": score,
            "enabled": True,
            "model": client.model,
            "raw_response": response,
        }
    
    except Exception as e:
        # If LLM call fails, return error
        return {
            "overall": None,
            "enabled": False,
            "error": str(e),
            "note": "LLM stylefit failed"
        }
