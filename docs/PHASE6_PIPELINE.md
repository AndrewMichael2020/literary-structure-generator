# Phase 6: Multi-Candidate Generation Pipeline

## Overview

The Phase 6 pipeline orchestrates the generation of multiple candidate story drafts, evaluates each one using the Phase 5 evaluation suite, and selects the best candidate based on quality metrics.

## Architecture

Each candidate goes through a complete generation and evaluation pipeline:

```
1. Per-beat Generation
   ↓ (using LLM router: beat_generator)
2. Stitch Beats
   ↓
3. Guards (overlap %, SimHash, grit)
   ↓
4. Repair Pass
   ↓ (using LLM router: repair_pass)
5. Evaluate (Phase 5 orchestrator)
   ↓
6. Select Best Candidate
```

## Usage

### Offline Testing (MockClient)

```python
from literary_structure_generator.pipeline.generate_candidates import generate_candidates
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.models.exemplar_digest import ExemplarDigest

# Create your spec and digest
spec = StorySpec(...)
digest = ExemplarDigest(...)
exemplar_text = "..."

# Generate 3 candidates (uses MockClient by default)
result = generate_candidates(
    spec=spec,
    digest=digest,
    exemplar_text=exemplar_text,
    n_candidates=3,
)

# Access results
best_candidate_id = result['best_id']
candidates = result['candidates']
for candidate in candidates:
    print(f"{candidate['id']}: {candidate['eval'].scores.overall:.3f}")
```

### Live API Calls

1. Set your API key: `export OPENAI_API_KEY=sk-...`
2. Configure `llm_routing.json` with `provider: "openai"`
3. Run the demo script:

```bash
python examples/demo_generate_candidates.py
```

## LLM Routing

All LLM calls go through the router (`literary_structure_generator.llm.router`):
- `beat_generator` component for per-beat generation
- `repair_pass` component for repair passes

The router handles:
- Model selection based on configuration
- Parameter merging (global + component-specific)
- GPT-5 parameter filtering (removes `temperature` for GPT-5 models)

## Selection Logic

The best candidate is selected based on:
1. **Pass/Fail Status**: Candidates that pass guards and quality thresholds are preferred
2. **Overall Score**: Higher overall evaluation score wins
3. **Freshness Score**: Used as a tie-breaker

## Output Structure

Results are persisted to `/runs/{run_id}/`:

```
runs/
└── {run_id}/
    ├── run_metadata.json       # Run metadata
    ├── summary.json            # Candidate scores summary
    ├── cand_001/
    │   ├── repaired.txt        # Final repaired text
    │   ├── stitched.txt        # Stitched beats (before repair)
    │   ├── beat_results.json   # Per-beat generation results
    │   ├── eval_report.json    # Phase 5 evaluation report
    │   └── metadata.json       # Generation metadata
    ├── cand_002/
    │   └── ...
    └── cand_003/
        └── ...
```

## Tests

All tests use `MockClient` for offline, deterministic testing:

```bash
pytest tests/test_phase6_pipeline.py -v
```

Tests cover:
- Single candidate generation
- Multi-candidate generation
- Best candidate selection
- Persistence to disk
- LLM routing integration
- GPT-5 parameter handling

## API Reference

### `generate_candidates()`

```python
def generate_candidates(
    spec: StorySpec,
    digest: ExemplarDigest,
    exemplar_text: str,
    n_candidates: int = 3,
    routing_overrides: Optional[dict] = None,
    run_id: Optional[str] = None,
) -> dict:
    """
    Generate N candidate drafts, evaluate them, and select the best.

    Args:
        spec: StorySpec with voice, form, and content parameters
        digest: ExemplarDigest for comparison
        exemplar_text: Original exemplar text (for overlap checking)
        n_candidates: Number of candidates to generate (default: 3)
        routing_overrides: Optional routing configuration overrides
        run_id: Optional run identifier (auto-generated if not provided)

    Returns:
        Dictionary with:
            - candidates: List of candidate dicts
            - best_id: ID of the best candidate
            - meta: Metadata about the run
    """
```

### `generate_single_candidate()`

```python
def generate_single_candidate(
    spec: StorySpec,
    digest: ExemplarDigest,
    exemplar_text: str,
    candidate_id: str,
    run_id: str,
    config: Optional[GenerationConfig] = None,
) -> dict:
    """
    Generate a single candidate draft.

    Returns:
        Dictionary with:
            - id: candidate_id
            - beats: List of beat generation results
            - stitched: Stitched text
            - repaired: Repaired text
            - eval: EvalReport object
            - metadata: Generation metadata
    """
```

### `select_best_candidate()`

```python
def select_best_candidate(candidates: list[dict]) -> str:
    """
    Select the best candidate based on evaluation scores.

    Returns:
        ID of the best candidate
    """
```

## Integration with Existing Phases

- **Phase 4**: Uses `generate_beat_text()`, `stitch_beats()`, `repair_text()`
- **Phase 5**: Uses `evaluate_draft()` for comprehensive evaluation
- **Router**: All LLM calls route through `get_client()` and `get_params()`

## Future Enhancements

Potential improvements:
- Parallel candidate generation for faster processing
- Custom selection criteria (e.g., prefer higher formfit vs stylefit)
- Incremental saving (save each candidate as it completes)
- Support for different diversity strategies between candidates
