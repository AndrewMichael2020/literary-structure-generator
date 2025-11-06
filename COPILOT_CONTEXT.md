# Literary Structure Generator - Copilot Context

## Overview

The Literary Structure Generator is an agentic workflow system for literary short-story generation that learns structural DNA from exemplar texts and generates new stories with similar form but original content.

**Key Principle**: Separate "Form" from "Content"
- Extract reusable structure (beats, transitions, voice) from exemplar
- Swap in new content (setting, characters, themes)
- Generate stories with learned form but original content

## Current Status

**Phase 7 Complete** ✅ — Full pipeline operational from exemplar analysis through iterative optimization.

### Completed Implementation

All core phases (1-7) are now implemented and tested:
- ✅ Phase 1: Foundation & scaffolding
- ✅ Phase 2: ExemplarDigest pipeline with heuristic and LLM-enhanced analysis
- ✅ Phase 3: StorySpec synthesis with LLM adapters, routing, and drift controls
- ✅ Phase 4: Beat-by-beat draft generation with guards and repair passes
- ✅ Phase 5: Comprehensive evaluation suite (heuristic + LLM metrics)
- ✅ Phase 6: Multi-candidate generation pipeline
- ✅ Phase 7: Iterative optimization loop with early stopping

**Test Coverage**: 81% (240+ tests, all passing)
**Reproducibility**: Full decision logging and artifact persistence

## Architecture

### Core Pipeline

```
Exemplar → Digest → StorySpec → Generate → Evaluate → Optimize → Final Story
```

### Core Data Artifacts (Pydantic Models)

1. **ExemplarDigest** (`models/exemplar_digest.py`)
   - Extracted DNA from exemplar text
   - Stylometry (sentence patterns, punctuation, function words)
   - Discourse structure (beats, dialogue, focalization)
   - Pacing, motifs, imagery palettes
   - Coherence graphs, valence arcs

2. **StorySpec** (`models/story_spec.py`)
   - Portable specification for generation
   - Voice (POV, tense, distance, syntax)
   - Form (structure, beat map, dialogue ratio)
   - Content (setting, characters, motifs)
   - Constraints (anti-plagiarism, length, safety)

3. **GenerationConfig** (`models/generation_config.py`)
   - Orchestrator control parameters
   - LLM parameters (temperature, top_p, seeds)
   - Diversity controls, constraint enforcement
   - Optimizer settings

4. **EvalReport** (`models/eval_report.py`)
   - Multi-metric assessment
   - Scores (stylefit, formfit, coherence, freshness)
   - Per-beat analysis, drift detection

5. **AuthorProfile** (`models/author_profile.py`)
   - User voice preferences
   - Lexicon, syntax, register sliders
   - Profanity policy, content safety

### Module Structure

- **digest/**: Exemplar analysis and DNA extraction
  - `digest_exemplar.py`: Main digest pipeline
  - `motif_extractor.py`: TF-IDF + PMI motif extraction
  - `entity_extractor.py`: Heuristic NER + co-occurrence
  - `valence_extractor.py`: Lexicon-based sentiment analysis
  - Other analyzers: stylometry, discourse, pacing, coherence

- **spec/**: StorySpec synthesis from digest
  - `synthesizer.py`: Maps digest to spec with voice/form/content

- **ingest/**: Entry points for digest pipeline
  - `digest_exemplar.py`: Main analyze_text() function

- **llm/**: LLM integration (Phase 3.2) ⭐
  - `router.py`: Per-component model routing
  - `cache.py`: SQLite-based response caching
  - `adapters.py`: High-level component functions
  - `base.py`: LLMClient interface
  - `clients/mock_client.py`: Deterministic offline mock
  - `clients/openai_client.py`: OpenAI API client
  - `config/llm_routing.json`: Routing configuration

- **generation/**: Beat-by-beat draft generation (planned)
- **evaluation/**: Multi-metric scoring (planned)
- **optimization/**: Iterative refinement (planned)
- **utils/**: Shared utilities
  - `decision_logger.py`: Decision tracking for reproducibility
  - `text_utils.py`, `similarity.py`, `io_utils.py`

## LLM Integration (Phase 3.2)

### Architecture

The LLM system is **first-class** and **mandatory** for agentic operations, with **offline-safe defaults** for CI/CD.

#### Component Routing

Each component can use a different model, configured via `llm/config/llm_routing.json`:

```json
{
  "global": {
    "provider": "mock",          // Default: mock for offline testing
    "temperature": 0.2,           // Low temp for stability
    "max_tokens": 512,
    "seed": 137
  },
  "components": {
    "motif_labeler": { "model": "gpt-4o-mini", "temperature": 0.2 },
    "imagery_namer": { "model": "gpt-4o-mini" },
    "beat_paraphraser": { "model": "gpt-4o", "max_tokens": 256 },
    "stylefit": { "model": "gpt-4o" },
    "repair_pass": { "model": "claude-opus-4", "temperature": 0.3 }
  }
}
```

#### Adapters

High-level functions in `llm/adapters.py`:

- **`label_motifs(anchors)`**: Label motif anchors with thematic tags
- **`name_imagery(phrases)`**: Generate evocative imagery category names
- **`paraphrase_beats(functions, register_hint)`**: Summarize beat functions
- **`stylefit_score(text, spec_summary)`**: Score text against style spec (0.0-1.0)
- **`repair_pass(text, constraints)`**: Fix constraint violations

Each adapter:
1. Loads versioned prompt template from `prompts/`
2. Gets configured client via router
3. Checks cache (SQLite in `runs/llm_cache.db`)
4. Calls LLM if cache miss
5. Logs call with version/params/checksums
6. Returns processed output

#### Drift Controls

To ensure reproducibility and stability:

1. **Prompt Versioning**: Templates in `prompts/*.v1.md` with version headers
2. **Sampling Caps**: Default temperature ≤ 0.3 for stability
3. **Semantic Checksums**: SHA256 over normalized list outputs
4. **Caching**: SQLite cache keyed by {component, model, template_version, params_hash, input_hash}
5. **Logging**: All calls logged with metadata to decision logs
6. **Seed Control**: Configurable seed for deterministic sampling

#### Testing Strategy

- **CI/CD**: Uses `MockClient` by default (no API key required)
- **Development**: Can use `openai` provider with `OPENAI_API_KEY`
- **Coverage**: 75%+ with extensive LLM integration tests

### Using LLM Adapters

#### In Digest Pipeline

`ingest/digest_exemplar.py` calls adapters after motif/imagery extraction:

```python
# Extract motifs heuristically
motif_map = extract_motifs(text, ...)

# LLM enhancement: label motifs
from literary_structure_generator.llm.adapters import label_motifs
motif_anchors = [m.motif for m in motif_map[:10]]
labels = label_motifs(motif_anchors, run_id=run_id, iteration=iteration)
```

#### In Spec Synthesis

`spec/synthesizer.py` calls adapters during beat mapping:

```python
# Extract beat functions
beat_functions = [beat.function for beat in digest.discourse.beats]

# LLM enhancement: paraphrase beats
from literary_structure_generator.llm.adapters import paraphrase_beats
summaries = paraphrase_beats(beat_functions, register_hint="neutral", ...)
```

#### Offline Testing

No API key needed - mock client returns deterministic outputs:

```python
# Default routing uses mock provider
client = get_client("motif_labeler")  # Returns MockClient
labels = label_motifs(["blood", "shadow"])  # Returns mock labels
```

#### Production Use

Set `OPENAI_API_KEY` and update routing config:

```json
{
  "global": {
    "provider": "openai",
    ...
  }
}
```

## Anti-Plagiarism Guardrails

- Max shared n-gram ≤ 12 tokens
- Overall overlap ≤ 3% vs exemplar
- SimHash Hamming distance ≥ 18 for 256-bit chunks
- No verbatim text stored in artifacts
- Profanity filter on all outputs (Clean Mode)

## Reproducibility

- Same seed + config → same output
- All artifacts JSON-serializable
- Version tracking for schemas
- Decision logging for all choices
- LLM calls cached and logged with checksums

## Development Workflow

### Running Tests

```bash
# All tests (uses mock client, no API key needed)
pytest

# With coverage
pytest --cov=literary_structure_generator --cov-report=term-missing

# Specific test file
pytest tests/test_llm_integration.py
```

### Code Style

```bash
# Format
black literary_structure_generator/

# Lint
ruff literary_structure_generator/

# Type check
mypy literary_structure_generator/
```

### Decision Logging

All components log decisions via `utils/decision_logger.py`:

```python
from literary_structure_generator.utils.decision_logger import log_decision

log_decision(
    run_id="run_001",
    iteration=0,
    agent="Digest",
    decision="Extracted 10 motifs",
    reasoning="Used TF-IDF + PMI ranking",
    parameters={"top_k": 10},
    metadata={"stage": "motif_extraction"}
)
```

Logs stored in `runs/{run_id}/reason_log_{iteration}.json`.

## Project Status

**Phase 7 Complete** ✅ — Full Pipeline Operational

### Completed Phases
- ✅ Phase 1: Foundation & scaffolding
- ✅ Phase 2: ExemplarDigest pipeline
- ✅ Phase 3: StorySpec synthesis
- ✅ Phase 3.2: LLM adapters with routing and drift controls
- ✅ Phase 4: Beat-by-beat draft generation
- ✅ Phase 5: Comprehensive evaluation suite
- ✅ Phase 6: Multi-candidate generation pipeline
- ✅ Phase 7: Iterative optimization loop

### Production-Ready Features
- Complete digest-to-story pipeline
- Multi-candidate generation with selection
- Iterative quality optimization
- Full decision logging and reproducibility
- Offline testing with MockClient
- 81% test coverage (240+ tests)

## Decision Logging Implementation

### Overview
The system includes structured decision logging for complete reproducibility and traceability of agent decisions across workflow runs and iterations.

### Core Implementation

**ReasonLog Model** (`models/reason_log.py`)
- Pydantic ReasonLog@1 schema
- Captures: timestamp, run_id, iteration, agent, decision, reasoning, parameters, outcome, metadata
- Full JSON serialization with timezone-aware timestamps

**Decision Logger** (`utils/decision_logger.py`)
- `log_decision()`: Creates and saves decision logs
- `load_decision_logs()`: Loads and filters logs
- No circular imports - imports only models

### Directory Structure

Decision logs are organized as follows:
```
runs/
└── {run_id}/
    ├── iter_0/
    │   └── reason_logs/
    │       ├── Digest_{timestamp}.json
    │       ├── SpecSynth_{timestamp}.json
    │       ├── Generator_{timestamp}.json
    │       ├── Evaluator_{timestamp}.json
    │       └── Optimizer_{timestamp}.json
    ├── iter_1/
    │   └── reason_logs/
    └── ...
```

### Agent Integration

All agents log decisions via `utils/decision_logger.py`:

```python
from literary_structure_generator.utils.decision_logger import log_decision

log_decision(
    run_id="run_001",
    iteration=0,
    agent="Digest",
    decision="Extracted 10 motifs",
    reasoning="Used TF-IDF + PMI ranking",
    parameters={"top_k": 10},
    metadata={"stage": "motif_extraction"}
)
```

Logs stored in `runs/{run_id}/iter_{iteration}/reason_logs/`.

**Integrated Agents:**
- `digest/assemble.py` - Digest pipeline decisions
- `spec/synthesizer.py` - Spec synthesis decisions
- `generation/ensemble.py` - Generation decisions
- `evaluation/assemble.py` - Evaluation decisions
- `optimization/optimizer.py` - Optimization decisions

### Usage Examples

```python
from literary_structure_generator.utils.decision_logger import load_decision_logs

# Load all logs for a run
all_logs = load_decision_logs("run_001")

# Filter by agent
spec_logs = load_decision_logs("run_001", agent="SpecSynth")

# Filter by iteration
iter_0_logs = load_decision_logs("run_001", iteration=0)
```

## Phase-Specific Implementation Details

### Phase 4: Draft Generation (Complete)

**Core Modules:**
- `generation/draft_generator.py` - Beat-by-beat LLM generation with retry logic
- `generation/guards.py` - Anti-plagiarism guards (n-gram overlap, SimHash)
- `generation/repair.py` - LLM-based quality improvement
- `utils/similarity.py` - SimHash fingerprint generation

**Key Features:**
- Per-beat structured prompting with StorySpec constraints
- Anti-plagiarism guards: max n-gram ≤12, overlap ≤3%, SimHash distance ≥18
- Profanity filtering with `[bleep]` replacement
- Automatic retry up to 2 times on guard failure
- GPT-5 model compatibility (auto-filters temperature param)
- Complete artifact management in `/runs/{story_id}/`

**Test Coverage:** 93-98% for generation modules (43 new tests)

### Phase 5: Evaluation Suite (Complete)

**Evaluator Modules:**
- `evaluators/stylefit_rules.py` - Heuristic style checks (POV, tense, syntax)
- `evaluators/formfit.py` - Structural adherence (beat lengths, dialogue ratio)
- `evaluators/coherence_graph_fit.py` - Entity continuity tracking
- `evaluators/motif_imagery_coverage.py` - Thematic coverage analysis
- `evaluators/cadence_pacing.py` - Rhythm and pacing checks
- `evaluators/overlap_guard_eval.py` - Anti-plagiarism validation
- `evaluators/stylefit_llm.py` - LLM-based style scoring (optional)
- `evaluators/evaluate.py` - Main orchestrator

**Multi-Metric Scoring:**
- Stylefit (30%): Voice, tense, syntax, dialogue
- Formfit (30%): Beat structure, length, function
- Coherence (25%): Entity continuity
- Freshness (10%): Overlap guard pass/fail
- Cadence (5%): Rhythm and pacing
- Optional: Motif coverage, LLM stylefit

**Key Features:**
- Deterministic heuristics for reproducibility
- Per-beat scoring and analysis
- Red flags for quality issues
- Actionable tuning suggestions
- EvalReport@2 schema compliance
- Persistence to `/runs/{run_id}/{candidate_id}_eval.json`

**Test Coverage:** 81% overall (50 new Phase 5 tests)

### Phase 6: Multi-Candidate Pipeline (Complete)

**Core Module:**
- `pipeline/generate_candidates.py` - Multi-candidate orchestration

**Pipeline Steps:**
1. Generate N candidates (default: 3)
2. Per-candidate: beat generation → stitch → guards → repair → evaluate
3. Select best candidate based on overall score and freshness
4. Persist all artifacts

**Key Features:**
- Parallel-ready candidate generation
- Complete evaluation for each candidate
- Best candidate selection logic
- Full artifact persistence to `/runs/{run_id}/`
- LLM routing integration
- GPT-5 parameter filtering

**Test Coverage:** 97% for generate_candidates.py (10 comprehensive tests)

### Phase 7: Optimization Loop (Complete)

**Core Module:**
- `optimization/optimizer.py` - Iterative refinement engine

**Optimizer Class:**
- `suggest(spec, report)`: Returns updated StorySpec with directed adjustments
- `run(spec, digest, exemplar_text, config, output_dir)`: Multi-iteration optimization loop

**Adjustable Parameters:**
- Beat target words (±5-15%)
- Average sentence length (±1-2 tokens)
- Dialogue ratio (±0.03)
- Generation temperature (±0.05)
- Objective weights (rebalanced)

**Key Features:**
- Deterministic heuristics for predictability
- Small incremental adjustments for stability
- Early stopping (improvement < threshold for 2 iterations)
- Decision logging for all adjustments
- Complete artifact persistence

**Test Coverage:** 95% for optimizer.py (11 comprehensive tests)

## Key Files

### Entry Points
- `ingest/digest_exemplar.py::analyze_text()` - Main digest function
- `spec/synthesizer.py::synthesize_spec()` - Main spec synthesis
- `generation/draft_generator.py::run_draft_generation()` - Draft generation
- `evaluators/evaluate.py::evaluate_draft()` - Evaluation orchestrator
- `pipeline/generate_candidates.py::generate_candidates()` - Multi-candidate pipeline
- `optimization/optimizer.py::Optimizer.run()` - Optimization loop

### Configuration
- `llm/config/llm_routing.json` - LLM routing config
- `prompts/*.v1.md` - Prompt templates

### Core Models
- `models/exemplar_digest.py` - ExemplarDigest@2
- `models/story_spec.py` - StorySpec@2
- `models/generation_config.py` - GenerationConfig@2
- `models/eval_report.py` - EvalReport@2
- `models/author_profile.py` - AuthorProfile@1
- `models/reason_log.py` - ReasonLog@1

### Tests
- `tests/test_digest_exemplar.py` - Digest pipeline tests
- `tests/test_spec_synthesis.py` - Spec synthesis tests
- `tests/test_llm_integration.py` - LLM integration tests
- `tests/test_enrichments.py` - Motif/imagery/valence tests
- `tests/test_phase4_generation.py` - Draft generation tests
- `tests/test_phase5_evaluation.py` - Evaluation suite tests
- `tests/test_phase6_pipeline.py` - Multi-candidate pipeline tests
- `tests/test_phase7_optimizer.py` - Optimization loop tests
- `tests/test_reason_log.py` - Decision logging tests
- `tests/test_workflow_logging.py` - Integration logging tests

### Documentation
- `README.md` - User guide and quick start
- `ROADMAP.md` - Implementation plan and roadmap
- `docs/architecture.md` - System architecture diagrams
- `docs/PHASE4_GUIDE.md` - Phase 4 usage guide
- `docs/PHASE6_PIPELINE.md` - Phase 6 pipeline documentation
- `COPILOT_CONTEXT.md` - This file (complete context for GitHub Copilot)

## Common Patterns

### Creating a New Adapter

1. Add prompt template to `prompts/component_name.v1.md`
2. Add component config to `llm/config/llm_routing.json`
3. Implement function in `llm/adapters.py`:
   ```python
   def my_adapter(input_data, run_id="run_001", iteration=0, use_cache=True):
       component = "my_component"
       template, version = _load_prompt_template("my_template.v1.md")
       prompt = template.replace("{input}", input_data)
       client = get_client(component)
       params = get_params(component)
       # ... cache check, LLM call, logging
       return result
   ```
4. Add tests in `tests/test_llm_integration.py`

### Adding a New Digest Feature

1. Implement extractor in `digest/my_feature.py`
2. Add to `ExemplarDigest` model in `models/exemplar_digest.py`
3. Call from `ingest/digest_exemplar.py::analyze_text()`
4. Optionally enhance with LLM adapter
5. Add tests in `tests/test_enrichments.py`

### Working with Decision Logs

```python
from literary_structure_generator.utils.decision_logger import load_decision_logs

# Load all logs for a run
logs = load_decision_logs("run_001")

# Filter by agent
digest_logs = [log for log in logs if log.agent == "Digest"]

# Filter by iteration
iter_0_logs = [log for log in logs if log.iteration == 0]
```

## Tips for Copilot

- **LLM calls are cheap in tests** - MockClient is fast and deterministic
- **Always use decision logging** - Helps with debugging and reproducibility
- **Respect anti-plagiarism** - Never copy exemplar text verbatim
- **Maintain coverage** - Keep test coverage ≥ 75%
- **Use type hints** - All functions should have type annotations
- **Document decisions** - Why a particular approach was chosen

## Security

- No secrets in code or artifacts
- API keys via environment variables only
- Profanity filtering on all LLM outputs
- No exemplar text stored verbatim
- Cache keys use hashes, not raw prompts
