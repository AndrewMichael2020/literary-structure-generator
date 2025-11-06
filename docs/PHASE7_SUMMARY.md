# Phase 7: Optimization Loop - Implementation Summary

## Overview

Phase 7 implements an iterative optimization engine that uses evaluation feedback to refine the StorySpec and GenerationConfig over multiple rounds. The optimizer applies deterministic heuristics to adjust parameters based on EvalReport scores and suggestions.

## Core Components

### 1. Optimizer Class (`literary_structure_generator/optimization/optimizer.py`)

The main `Optimizer` class provides:

- **Constructor parameters:**
  - `max_iters`: Maximum optimization iterations (default: 5)
  - `candidates`: Number of candidates per iteration (default: 3)
  - `early_stop_delta`: Minimum improvement threshold (default: 0.01)
  - `run_id`: Unique run identifier (auto-generated if not provided)

- **Key methods:**
  - `suggest(spec, report)`: Returns updated StorySpec with directed adjustments
  - `run(spec, digest, exemplar_text, config, output_dir)`: Executes multi-iteration optimization loop

### 2. Adjustable Parameters

The optimizer makes small, incremental adjustments to:

| Parameter | Adjustment Range | Trigger Condition |
|-----------|------------------|-------------------|
| `form.beat_map[*].target_words` | ±5-15% | Low formfit score |
| `voice.syntax.avg_sentence_len` | ±1-2 tokens | Low stylefit score |
| `form.dialogue_ratio` | ±0.03 | Low dialogue_balance score |
| `generation.temperature` | ±0.05 | Low/high freshness score |
| `objective_weights` | Rebalanced | Low-scoring metrics |

Additionally, the optimizer applies tuning suggestions from evaluators and corrects drift from target specifications.

### 3. Optimization Loop

Each iteration follows this workflow:

```
1. Generate N candidates with current spec/config
2. Evaluate each candidate using full evaluation suite
3. Select best candidate based on overall score
4. Adjust spec/config based on evaluation feedback
5. Check for early stopping condition
6. Repeat or terminate
```

### 4. Early Stopping

Optimization terminates when:
- Maximum iterations reached, OR
- Improvement < `early_stop_delta` for 2 consecutive iterations

### 5. Artifact Persistence

All artifacts are saved to `/runs/{run_id}/`:

```
runs/
└── {run_id}/
    ├── best_spec.json              # Best StorySpec found
    ├── best_draft.txt              # Best draft text
    ├── optimization_summary.json   # Summary statistics
    ├── iter_0/
    │   ├── draft_0.txt
    │   ├── draft_1.txt
    │   └── reason_logs/
    │       └── Optimizer_*.json
    ├── iter_1/
    │   └── ...
    └── ...
```

## Testing

### Test Coverage

- **11 comprehensive tests** in `tests/test_phase7_optimizer.py`
- **95% code coverage** for `optimizer.py`
- All tests use MockClient for offline operation
- Tests cover:
  - Initialization and configuration
  - `suggest()` method with various feedback scenarios
  - `run()` method with different configurations
  - Early stopping behavior
  - Artifact persistence
  - Full integration scenarios

### Running Tests

```bash
# Run all Phase 7 tests
python -m pytest tests/test_phase7_optimizer.py -v

# Run specific test class
python -m pytest tests/test_phase7_optimizer.py::TestOptimizer -v

# Run with coverage
python -m pytest tests/test_phase7_optimizer.py --cov=literary_structure_generator/optimization
```

## Demo Script

### Usage

```bash
# Offline mode (default, uses MockClient)
python examples/demo_optimization.py

# Live mode with real LLM (requires OPENAI_API_KEY)
OPENAI_API_KEY=xxx python examples/demo_optimization.py --live
```

### Demo Output

The demo script provides:
- Configuration summary
- Real-time progress updates
- Score progression across iterations
- Best candidate metrics
- Artifact locations
- Excerpt from best draft
- Optimization summary

## Design Decisions

### 1. Deterministic Heuristics

The optimizer uses deterministic heuristics rather than ML-based optimization for:
- **Predictability**: Results are reproducible given the same inputs
- **Debuggability**: Easy to understand why adjustments were made
- **Reliability**: No dependency on external models or training data

### 2. Incremental Adjustments

Small, incremental changes (±5-15% for lengths, ±1-2 for discrete values) to:
- Avoid large spec changes that could destabilize generation
- Allow gradual convergence toward better configurations
- Maintain spec coherence across iterations

### 3. Decision Logging

All optimizer decisions are logged using the `log_decision()` utility:
- Full transparency of optimization process
- Reproducibility and debugging support
- Audit trail for understanding results

### 4. Router Integration

All LLM calls route through the existing router:
- Automatically filters unsupported parameters for GPT-5 models
- Consistent with rest of codebase
- Supports both mock and real LLM clients

## Integration with Existing Pipeline

The optimizer integrates seamlessly with existing components:

- **Generation**: Uses `run_draft_generation()` from `draft_generator.py`
- **Evaluation**: Uses `evaluate_draft()` from `evaluators/evaluate.py`
- **Models**: Works with existing `StorySpec`, `GenerationConfig`, and `EvalReport` models
- **Logging**: Uses existing `log_decision()` utility
- **LLM**: Routes through existing router with GPT-5 support

## Performance Characteristics

### Typical Runtime

With MockClient (offline mode):
- Single iteration: ~0.5-1 seconds
- 3 iterations with 2 candidates each: ~3-6 seconds
- 5 iterations with 3 candidates each: ~7-15 seconds

With real LLM (live mode):
- Depends on LLM latency and rate limits
- Each generation can take 5-30 seconds
- Total time scales linearly with (iterations × candidates)

### Memory Usage

- Modest memory footprint
- Stores best spec/draft in memory
- Writes artifacts to disk incrementally

## Future Enhancements

Potential improvements for future phases:

1. **Adaptive step sizes**: Adjust parameter change magnitude based on score trends
2. **Multi-objective optimization**: Pareto frontier for conflicting objectives
3. **Population-based search**: Maintain multiple spec candidates in parallel
4. **Bayesian optimization**: Learn parameter response surfaces
5. **Spec constraints**: Enforce bounds and constraints on adjustments
6. **Caching**: Cache generation results for identical specs
7. **Parallel evaluation**: Evaluate candidates concurrently

## Conclusion

Phase 7 delivers a robust, deterministic optimization engine that:
- ✅ Implements all specified adjustable parameters
- ✅ Includes early stopping logic
- ✅ Persists comprehensive artifacts
- ✅ Routes all LLM calls through router
- ✅ Handles GPT-5 model compatibility
- ✅ Provides offline testing with MockClient
- ✅ Includes demo script for live use
- ✅ Maintains 95% code coverage
- ✅ Passes all 229 existing tests + 11 new tests

The implementation is production-ready and ready for integration into the full literary generation pipeline.
