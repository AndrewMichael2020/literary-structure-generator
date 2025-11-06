# Phase 4: Draft Generation Guide

This guide explains how to use the Phase 4 per-beat draft generation pipeline.

## Overview

Phase 4 implements a complete draft generation system that:
1. Generates prose for individual story beats using LLM
2. Stitches beats into a coherent narrative
3. Enforces anti-plagiarism constraints
4. Applies Clean Mode filtering
5. Runs quality improvement repairs
6. Saves all artifacts for review

## Quick Start

```python
from literary_structure_generator.generation.draft_generator import run_draft_generation
from literary_structure_generator.models.story_spec import (
    BeatSpec, Character, Content, MetaInfo, Setting, StorySpec
)

# Create a story specification
spec = StorySpec(
    meta=MetaInfo(story_id="my_story", seed=137),
    content=Content(
        setting=Setting(place="Hospital", time="1973"),
        characters=[
            Character(name="Dr. Smith", role="protagonist")
        ],
    ),
)

# Define beats
spec.form.beat_map = [
    BeatSpec(
        id="beat_1",
        target_words=200,
        function="establish setting",
        cadence="mixed",
    ),
    BeatSpec(
        id="beat_2",
        target_words=250,
        function="develop conflict",
        cadence="long",
    ),
]

# Generate draft
result = run_draft_generation(spec, output_dir="runs/my_story")

# Access results
print(f"Stitched text: {result['stitched']}")
print(f"Final text: {result['final']}")
print(f"Metadata: {result['metadata']}")
```

## Components

### 1. Draft Generator (`draft_generator.py`)

Main orchestration module for the generation pipeline.

**Key Functions:**

- `generate_beat_text()` - Generate text for a single beat
  - Uses `beat_generator` LLM component
  - Enforces overlap guards
  - Applies Clean Mode filtering
  - Retries up to 2 times on guard failure

- `stitch_beats()` - Combine beat texts into story
  - Simple paragraph-break stitching
  - Future: more sophisticated transitions

- `run_draft_generation()` - Complete pipeline
  - Generate all beats
  - Stitch together
  - Run repair pass
  - Re-check guards
  - Save artifacts

### 2. Overlap Guards (`guards.py`)

Anti-plagiarism and content filtering.

**Functions:**

- `max_ngram_overlap()` - N-gram overlap detection
  - Checks n-grams from size 3 to 12
  - Returns maximum overlap percentage
  - Threshold: ≤3% overlap allowed

- `simhash_distance()` - SimHash Hamming distance
  - Uses 256-bit fingerprints
  - Returns Hamming distance (0-256)
  - Threshold: ≥18 bits different

- `clean_mode()` - Grit filtering
  - Replaces grit with neutral alternatives
  - Maintains readability
  - Configurable per StorySpec

- `check_overlap_guard()` - Combined guard check
  - Runs all overlap checks
  - Returns pass/fail with violations

### 3. Repair Pass (`repair.py`)

LLM-based quality improvement.

**Functions:**

- `repair_text()` - Apply LLM repair pass
  - Uses `repair_pass` LLM component
  - Fixes POV leaks
  - Balances paragraph rhythm
  - Avoids unearned epiphanies
  - Re-enforces guards after repair

- `calculate_paragraph_variance()` - Cadence check
  - Computes paragraph length variance
  - Triggers rebalancing if variance > 100

### 4. LLM Router Updates

Enhanced router to support GPT-5 family models.

**New Features:**

- Automatic parameter filtering for GPT-5
  - Detects `gpt-5*` model names
  - Omits `temperature` parameter (unsupported)
  - Maintains compatibility with other models

**Configuration:**

```json
{
  "components": {
    "beat_generator": {
      "model": "gpt-5",
      "max_tokens": 800
    },
    "repair_pass": {
      "model": "opus-4.1",
      "temperature": 0.3,
      "max_tokens": 800
    }
  }
}
```

## Prompts

### Beat Generation Prompt (`beat_generate.v1.md`)

Structured prompt for beat-level generation with:
- Beat function and summary
- Voice parameters (person, distance, tense)
- Syntax constraints (sentence length, parataxis)
- Register sliders (lyric, deadpan, etc.)
- Dialogue ratio hint
- Content guidance (motifs, imagery, props)

### Repair Prompt (`repair_pass.v1.md`)

Already exists - used for post-generation repair.

## Artifact Persistence

All generation artifacts saved to `/runs/{story_id}/`:

- `story_spec.json` - Input specification
- `beat_results.json` - Per-beat generation metadata
- `stitched.txt` - Stitched beats (before repair)
- `repaired.txt` - After repair pass
- `final.txt` - Final output (after Clean Mode)
- `metadata.json` - Generation metadata

## Testing

Phase 4 includes comprehensive offline tests using MockClient:

```bash
# Run Phase 4 tests
pytest tests/test_phase4_generation.py -v

# Run all tests with coverage
pytest tests/ --cov=literary_structure_generator
```

**Test Coverage:**
- Total: 77% (1929 statements)
- draft_generator.py: 93%
- guards.py: 98%
- repair.py: 80%
- similarity.py: 90%

## Demo

Run the included demo:

```bash
python examples/demo_draft_generation.py
```

This demonstrates:
- Creating a StorySpec
- Defining beats
- Running generation pipeline
- Saving artifacts
- Viewing results

## Advanced Usage

### Custom Exemplar Checking

```python
result = run_draft_generation(
    spec,
    exemplar=original_text,  # Check against exemplar
    output_dir="runs/my_story"
)

# Check guard results
if result['metadata']['final_guard']['passed']:
    print("✓ Passed all anti-plagiarism checks")
else:
    print("✗ Guard violations:", result['metadata']['final_guard']['violations'])
```

### Routing Overrides

```python
result = run_draft_generation(
    spec,
    routing_overrides={
        "beat_generator": {"model": "gpt-4o", "temperature": 0.7}
    }
)
```

### Manual Beat Generation

```python
from literary_structure_generator.generation.draft_generator import generate_beat_text

beat = BeatSpec(id="b1", target_words=200, function="opening", cadence="mixed")
result = generate_beat_text(beat, spec, exemplar=exemplar)

print(f"Text: {result['text']}")
print(f"Guard passed: {result['guard_passed']}")
print(f"Metadata: {result['metadata']}")
```

## API Reference

See module docstrings for detailed API documentation:
- `literary_structure_generator.generation.draft_generator`
- `literary_structure_generator.generation.guards`
- `literary_structure_generator.generation.repair`

## Next Steps

Future enhancements:
- More sophisticated beat stitching with transitions
- Adaptive repair based on specific violation types
- Multi-pass refinement
- Style consistency checking across beats
- Dialogue formatting enforcement
