# LLM Routing Configuration Guide

This document describes the LLM routing configuration system and the rationale behind model selection for different components.

## Configuration File Location

The active LLM routing configuration is located at:
```
literary_structure_generator/llm/config/llm_routing.json
```

This is the canonical source for all LLM routing decisions in the system.

## Configuration Structure

The routing configuration has two main sections:

### Global Defaults

```json
{
  "global": {
    "provider": "mock",
    "timeout_s": 20,
    "seed": 137,
    "temperature": 0.2,
    "top_p": 0.9,
    "max_tokens": 512
  }
}
```

These values apply to all components unless overridden.

### Component-Specific Overrides

Each component can override global settings:

```json
{
  "components": {
    "motif_labeler": {
      "model": "gpt-4o-mini",
      "temperature": 0.2
    },
    "beat_paraphraser": {
      "model": "gpt-5-mini",
      "max_tokens": 256,
      "temperature": 0.25
    }
  }
}
```

## Model Selection Rationale

The system uses a tiered approach to optimize costs while maintaining quality:

### Tier 1: High-Throughput Components (gpt-4o-mini, gpt-5-mini)

**Components:** `motif_labeler`, `imagery_namer`, `beat_paraphraser`, `stylefit`

**Models:** `gpt-4o-mini` or `gpt-5-mini`

**Rationale:**
- These components process many requests per run
- Cost savings of 60-90% vs premium models
- Sufficient quality for labeling, paraphrasing, and evaluation tasks
- `gpt-5-mini` provides strong performance at a fraction of gpt-4o's cost

**Cost Impact:** Expected 30%+ reduction in per-run costs

### Tier 2: Creative Generation (gpt-5)

**Components:** `beat_generator`

**Model:** `gpt-5`

**Rationale:**
- Requires strong creative writing capabilities
- Higher temperature (0.8) for diverse outputs
- Critical for story quality
- Worth the premium for this step

### Tier 3: Literary Polish - Finalists Only (opus-4.1)

**Components:** `repair_pass`

**Model:** `opus-4.1`

**Special Configuration:**
```json
{
  "repair_pass": {
    "model": "opus-4.1",
    "temperature": 0.3,
    "max_tokens": 800,
    "finalists_only": 3
  }
}
```

**Rationale:**
- Excellent for literary polish and constraint fixing
- Most expensive model in the system
- `finalists_only: 3` gates Opus to only the top 3 candidates after initial evaluation
- Reduces Opus invocations by 67%+ (from N candidates to top-K only)
- Best value when applied to finalists that have already been validated

## Advanced Features

### Finalists-Only Mode

When `finalists_only` is set on a component (currently `repair_pass`), the system:

1. Generates all N candidates without applying that component
2. Evaluates all candidates using cheaper components
3. Ranks candidates by evaluation score
4. Applies the expensive component only to top-K finalists
5. Re-evaluates finalists with the enhanced version

This dramatically reduces costs for expensive operations while maintaining quality where it matters most.

### Tie-Break Model Support

For evaluation components like `stylefit`, you can specify a tie-break model:

```json
{
  "stylefit": {
    "model": "gpt-5-mini",
    "temperature": 0.2,
    "tie_break_model": "gpt-5"
  }
}
```

**Future Enhancement:** The system can optionally re-score only the top-K candidates with the premium model as a final tie-breaker.

## GPT-5 Family Support

The router automatically handles GPT-5 family models:
- Removes `temperature` parameter (not supported by GPT-5)
- Maintains other parameters like `max_tokens`, `top_p`, etc.

## Environment Override

You can override the config file location using an environment variable:

```bash
export LLM_ROUTING_CONFIG=/path/to/custom/llm_routing.json
```

The system searches for config in this order:
1. `$LLM_ROUTING_CONFIG` (if set)
2. `literary_structure_generator/llm/config/llm_routing.json` (default)
3. `./llm_routing.json` (current directory)
4. `./config/llm_routing.json`

## Monitoring and Auditing

All LLM calls are logged with:
- Component name
- Model used
- Prompt template version
- Parameter hash
- Input/output checksums

This enables:
- Cost attribution per component
- Detection of model drift
- Reproducibility across runs

## Cost Analysis

Based on typical workloads:

| Component | Model | Relative Cost | Invocations/Run | Impact |
|-----------|-------|---------------|-----------------|--------|
| motif_labeler | gpt-4o-mini | 1x | ~10 | Low |
| imagery_namer | gpt-4o-mini | 1x | ~10 | Low |
| beat_paraphraser | gpt-5-mini | 0.5x | ~50 | **High** |
| stylefit | gpt-5-mini | 0.5x | ~100 | **High** |
| beat_generator | gpt-5 | 10x | ~10 | Medium |
| repair_pass | opus-4.1 | 20x | 3 (finalists) | **High** |

**Key Savings:**
- Paraphrase/eval dominates token volume → switching to gpt-5-mini saves 30%+
- Gating Opus to 3 finalists instead of N candidates saves 67%+ on repair costs

## Best Practices

1. **Use cheaper models for high-throughput tasks** - paraphrasing, labeling, evaluation
2. **Reserve premium models for creative work** - story generation, literary polish
3. **Gate expensive operations to finalists** - use `finalists_only` parameter
4. **Monitor costs per component** - check decision logs for attribution
5. **Test config changes** - validate quality on small corpus before production use
6. **Version control** - treat routing config as critical infrastructure code

## See Also

- [Phase 6 Pipeline Documentation](PHASE6_PIPELINE.md)
- [Architecture Overview](architecture.md)
- [Decision Logging](../README.md#decision-logging)
