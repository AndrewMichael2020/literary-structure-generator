# Literary Structure Generator

[![CI](https://github.com/AndrewMichael2020/literary-structure-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewMichael2020/literary-structure-generator/actions/workflows/ci.yml)
[![CodeQL](https://github.com/AndrewMichael2020/literary-structure-generator/actions/workflows/codeql.yml/badge.svg)](https://github.com/AndrewMichael2020/literary-structure-generator/actions/workflows/codeql.yml)
[![Coverage](https://codecov.io/gh/AndrewMichael2020/literary-structure-generator/branch/main/graph/badge.svg)](https://codecov.io/gh/AndrewMichael2020/literary-structure-generator)
![Lint: Ruff](https://img.shields.io/badge/lint-ruff-46a2f1)
![Style: Black](https://img.shields.io/badge/style-black-000000)
![Types: mypy](https://img.shields.io/badge/types-mypy-2A6DB2)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Issues](https://img.shields.io/github/issues/AndrewMichael2020/literary-structure-generator)
![Last commit](https://img.shields.io/github/last-commit/AndrewMichael2020/literary-structure-generator)

An agentic workflow for literary short-story generation that learns structural DNA from exemplar texts and generates new stories with similar form but original content.

---

**Project Status**  
Current Phase: 7 Complete — Full Pipeline Operational  
Coverage: ≥ 80% (target met)  
All core phases implemented: Digest → Spec → Generation → Evaluation → Optimization

---

## Overview

This system implements a reproducible, inspectable workflow that:
- **Learns a story's DNA** from exemplar texts (structure, voice, pacing, motifs, POV)
- **Maps that DNA into a portable "StorySpec"** with tunable parameters
- **Generates new stories** in new contexts using your voice preferences
- **Audits itself** with quantitative and qualitative metrics
- **Leaves an observable trace** of every step with JSON artifacts

## Key Features

### Separate Form from Content
- Extract reusable structure (beats, transitions, rhetoric) from exemplars
- Swap in new content (setting, characters, themes)
- Generate stories with learned form but original content

### Multi-Stage Workflow
```
Exemplar → Digest → StorySpec → Generate Candidates → Evaluate → Optimize → Final Story
```

### Anti-Plagiarism Guardrails
- Max shared n-gram ≤ 12 tokens
- Overall overlap ≤ 3% vs exemplar
- SimHash Hamming distance ≥ 18 for 256-bit chunks
- No verbatim text stored in artifacts

### Grit Handling
**Content Safety Policy**: Grit is replaced with `[bleep]` when required for narrative authenticity. This universal filtering system maintains tone and rhythm while ensuring appropriate content across all outputs.

### Reproducibility
- Same seed + config → same output
- All artifacts JSON-serializable
- Version tracking for schemas

## Architecture

For detailed architecture documentation including system diagrams, see [docs/architecture.md](docs/architecture.md).

### Core Data Artifacts (Pydantic Models)

1. **ExemplarDigest**: Extracted DNA from exemplar text
   - Stylometry (sentence patterns, POS, punctuation)
   - Discourse structure (beats, dialogue, focalization)
   - Pacing, motifs, imagery palettes

2. **StorySpec**: Portable specification for generation
   - Voice (POV, tense, register, syntax, diction)
   - Form (structure, beat map, scene/summary ratios)
   - Content (setting, characters, motifs)
   - Constraints (anti-plagiarism, length, safety)

3. **GenerationConfig**: Orchestrator control parameters
   - LLM parameters (temperature, top_p, seeds)
   - Diversity controls, constraint enforcement
   - Optimizer settings (Adam-ish schedule)

4. **EvalReport**: Multi-metric assessment
   - Scores (stylefit, formfit, coherence, freshness)
   - Per-beat analysis, drift detection
   - Tuning suggestions for next iteration

5. **AuthorProfile**: User voice preferences
   - Lexicon, syntax, register sliders
   - Grit policy, content safety

### Main Modules

- **digest/**: Exemplar analysis and DNA extraction
- **spec/**: StorySpec synthesis from digest
- **generation/**: Beat-by-beat draft generation with LLMs
- **evaluation/**: Multi-metric scoring and quality assessment
- **optimization/**: Iterative refinement loop
- **profiles/**: AuthorProfile management and learning
- **orchestrators/**: End-to-end workflow automation
- **utils/**: Shared utilities (text processing, similarity, I/O)
- **llm/**: LLM integration with routing, caching, and drift controls

## Installation

```bash
# Clone the repository
git clone https://github.com/AndrewMichael2020/literary-structure-generator.git
cd literary-structure-generator

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

## LLM Configuration

The system uses LLM adapters for motif labeling, imagery naming, and beat summarization. By default, it uses a **mock client** for offline/deterministic testing.

### Using OpenAI API (Optional)

To use OpenAI models instead of the mock client:

1. Set your API key:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

2. Update `literary_structure_generator/llm/config/llm_routing.json`:
   ```json
   {
     "global": {
       "provider": "openai",
       "temperature": 0.2,
       "max_tokens": 512
     }
   }
   ```

### LLM Routing Configuration

Configure per-component model selection in `llm/config/llm_routing.json`:

```json
{
  "global": {
    "provider": "mock",
    "temperature": 0.2,
    "top_p": 0.9,
    "max_tokens": 512,
    "seed": 137
  },
  "components": {
    "motif_labeler": { "model": "gpt-4o-mini" },
    "imagery_namer": { "model": "gpt-4o-mini" },
    "beat_paraphraser": { "model": "gpt-4o", "max_tokens": 256 }
  }
}
```

### Drift Controls

The LLM integration includes drift control mechanisms:
- **Prompt versioning**: Templates in `prompts/` with version headers
- **Sampling caps**: Default temperature ≤ 0.3 for stability
- **Semantic checksums**: SHA256 over normalized outputs
- **Caching**: SQLite-based cache in `runs/llm_cache.db`
- **Logging**: All LLM calls tracked with params_hash and input_hash

## Quick Start (LLM-Only Flow)

The implemented end-to-end flow uses these concrete entry points:

1. `analyze_text()` in `ingest/digest_exemplar.py` to create an `ExemplarDigest`
2. `synthesize_spec()` in `spec/synthesizer.py` to produce a `StorySpec`
3. `generate_candidates()` in `pipeline/generate_candidates.py` to create and evaluate multiple drafts (beats → stitch → repair → evaluate). It persists artifacts automatically under `runs/<run_id>/`.

There is currently no `full_pipeline` module and the earlier placeholder `assemble_digest()` in `digest/assemble.py` is not implemented. The examples and scripts below reflect the real, working API surface.

### 0. Environment Setup

```bash
git clone https://github.com/AndrewMichael2020/literary-structure-generator.git
cd literary-structure-generator
pip install -r requirements.txt
python -m spacy download en_core_web_sm
export OPENAI_API_KEY="your-key"   # if using OpenAI components
```

Optional: Adjust `literary_structure_generator/llm/config/llm_routing.json` for per-component providers.

### 1. Generate ExemplarDigest from an exemplar text

```python
from literary_structure_generator.ingest.digest_exemplar import analyze_text

digest = analyze_text(
    path="data/Emergency.txt",  # path to your exemplar
    run_id="emergency_digest_001",
    iteration=0,
    output_dir="runs"
)
```

Artifacts saved to `runs/emergency_digest_001/ExemplarDigest_Emergency.json`.

### 2. Synthesize a StorySpec

```python
from literary_structure_generator.spec.synthesizer import synthesize_spec

spec = synthesize_spec(
    digest=digest,
    story_id="emergency_story_001",
    seed=137,
    alpha_exemplar=0.7,
    output_path="runs/spec_demo/StorySpec_emergency_story_001.json",
    run_id="spec_demo",
    iteration=0,
)
```

### 3. Multi-Candidate Generation + Evaluation (beats → stitch → repair → evaluate)

```python
from literary_structure_generator.pipeline.generate_candidates import generate_candidates

with open("data/Emergency.txt", encoding="utf-8") as f:
    exemplar_text = f.read()

result = generate_candidates(
    spec=spec,
    digest=digest,
    exemplar_text=exemplar_text,
    n_candidates=3,
    run_id="emergency_run_001",
)

print("Best candidate:", result["best_id"])
```

Artifacts created under `runs/emergency_run_001/`:
```
summary.json
run_metadata.json
cand_001/ (repaired.txt, stitched.txt, eval_report.json, beat_results.json, metadata.json)
cand_002/ ...
cand_003/ ...
```

### 4. Inspect Evaluation Metrics

Each `cand_XXX/eval_report.json` contains `scores` (overall, stylefit, formfit, coherence, freshness, cadence, dialogue_balance) and per-beat notes. Use these for manual tuning.

### 5. Optimization Loop (Optional)

An iterative optimizer exists under `optimization/` (e.g. `examples/demo_optimization.py`). Run the demo:

```bash
python examples/demo_optimization.py
```

This will produce an optimization run with evolving specs and a `best_draft.txt` artifact.

### LLM-Only Routing Configuration

To run fully with live LLMs (no mock components), edit `literary_structure_generator/llm/config/llm_routing.json`:

```jsonc
{
  "global": {
    "provider": "openai",
    "temperature": 0.25,
    "top_p": 0.9,
    "max_tokens": 512,
    "timeout_s": 30
  },
  "components": {
    "beat_generator": { "model": "gpt-4o", "max_tokens": 800, "temperature": 0.6 },
    "beat_paraphraser": { "provider": "openai", "model": "gpt-4o-mini", "max_tokens": 256, "temperature": 0.4 },
    "repair_pass": { "provider": "openai", "model": "gpt-4o-mini", "max_tokens": 320, "temperature": 0.25 },
    "motif_labeler": { "provider": "openai", "model": "gpt-4o-mini", "temperature": 0.2 },
    "imagery_namer": { "provider": "openai", "model": "gpt-4o-mini", "max_tokens": 64, "temperature": 0.2 },
    "stylefit": { "provider": "openai", "model": "gpt-4o", "temperature": 0.2 }
  }
}
```

If you need a hybrid mode (e.g., limit token usage), set `global.provider` to `mock` and override only heavy quality-improvement steps:

```jsonc
{
  "global": { "provider": "mock", "temperature": 0.2, "max_tokens": 512, "seed": 137 },
  "components": {
    "repair_pass": { "provider": "openai", "model": "gpt-4o-mini", "max_tokens": 320, "temperature": 0.25 },
    "beat_paraphraser": { "provider": "openai", "model": "gpt-4o-mini", "max_tokens": 256 }
  }
}
```

Reloading: The router auto-loads the JSON on first access. To force a different file, set `LLM_ROUTING_CONFIG` to an absolute path.

### Common LLM-Only Pitfalls

- Ensure `OPENAI_API_KEY` is exported before importing generation modules.
- Quota errors (HTTP 429): Reduce `n_candidates`, lower `max_tokens`, or use hybrid routing.
- Temperature for `gpt-5*` models: The router strips unsupported params automatically.
- Consistency: For deterministic-ish runs, keep seed + low temperature and avoid paraphraser randomness.

### Minimal Single-Beat Generation Example

```python
from literary_structure_generator.generation.draft_generator import generate_beat_text
from literary_structure_generator.models.story_spec import StorySpec, BeatSpec, MetaInfo, Content, Setting

spec = StorySpec(
    meta=MetaInfo(story_id="quick_demo", seed=42),
    content=Content(setting=Setting(place="rural clinic", time="dusk")),
)
spec.form.beat_map = [BeatSpec(id="beat_1", function="opening", target_words=120, cadence="mixed", summary="Protagonist arrives as light fades")]

beat = generate_beat_text(beat_spec=spec.form.beat_map[0], story_spec=spec, exemplar=None)
print(beat["text"])
```

---
This revised Quick Start reflects the current implemented API. Remove or ignore earlier placeholder examples referencing unimplemented modules (`full_pipeline`, `assemble_digest`, `generation.ensemble`, `evaluation.assemble`).

## Project Status

**Current Phase**: Phase 7 Complete ✅ — Full Pipeline Operational

### Completed Phases:

- ✅ **Phase 1**: Foundation & Scaffolding
  - Project structure and configuration
  - Pydantic models for all data artifacts (ExemplarDigest, StorySpec, GenerationConfig, EvalReport, AuthorProfile)
  - Module stubs with docstrings
  - Roadmap and development plan

- ✅ **Phase 2**: ExemplarDigest Pipeline
  - Heuristic analyzers (stylometry, discourse, pacing, coherence)
  - Entity extraction and coherence graphs
  - Motif extraction and imagery palettes
  - Valence arc and lexical domain analysis
  - Full digest assembler with decision logging

- ✅ **Phase 3**: StorySpec Synthesis & LLM Integration
  - Voice parameter mapping from digest
  - Form parameter mapping (beat structure, dialogue ratio)
  - Content section initialization
  - Anti-plagiarism constraint setup
  - Full synthesis pipeline with decision logging
  - LLM adapters with routing and drift controls
  - Offline testing support with MockClient

- ✅ **Phase 4**: Beat-by-Beat Draft Generation
  - Per-beat text generation with LLM routing
  - Beat stitching into coherent narrative
  - Anti-plagiarism guards (n-gram overlap, SimHash)
  - Grit filtering (Clean Mode)
  - Repair passes for quality improvement
  - GPT-5 model compatibility

- ✅ **Phase 5**: Comprehensive Evaluation Suite
  - Heuristic evaluators (stylefit, formfit, coherence, motif coverage, cadence)
  - LLM-based style scoring
  - Anti-plagiarism validation
  - Per-beat analysis and drift detection
  - Red flags and tuning suggestions
  - Full EvalReport generation

- ✅ **Phase 6**: Multi-Candidate Generation Pipeline
  - Generate multiple story candidates
  - Evaluate all candidates
  - Select best candidate based on scores
  - Complete artifact persistence

- ✅ **Phase 7**: Iterative Optimization Loop
  - Deterministic optimizer with parameter adjustments
  - Early stopping logic
  - Multi-iteration refinement
  - Decision logging for all optimizations

### Available Tools & Demos:

- **Digest Pipeline**: `examples/demo_digest.py` - Generate ExemplarDigest from exemplar text
- **Spec Synthesis**: `examples/demo_spec_synthesis.py` - Synthesize StorySpec from digest
- **Draft Generation**: `examples/demo_draft_generation.py` - Generate story drafts beat-by-beat
- **Evaluation**: `examples/demo_evaluation.py` - Evaluate story quality with metrics
- **Multi-Candidate Pipeline**: `examples/demo_generate_candidates.py` - Generate and select best candidate
- **Optimization Loop**: `examples/demo_optimization.py` - Full iterative refinement workflow
- **Decision Logging**: `examples/demo_decision_logging.py` - Demonstrate agent decision tracking

### Test Coverage:

- **240+ tests** passing
- **81% overall coverage** (exceeds 80% target)
- All tests support offline operation with MockClient
- Comprehensive integration tests for full pipeline

### System Capabilities:

The system now provides a complete end-to-end workflow:
1. **Analyze** exemplar texts to extract structural DNA
2. **Synthesize** portable StorySpec with voice, form, and content parameters
3. **Generate** multiple story candidates with anti-plagiarism guards
4. **Evaluate** candidates across multiple quality dimensions
5. **Optimize** iteratively to improve quality
6. **Persist** complete artifact trails for reproducibility

All functionality is production-ready and fully tested.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=literary_structure_generator --cov-report=term-missing

# Run specific test file
pytest tests/test_models.py
```

### Code Style

```bash
# Format code
black literary_structure_generator/

# Lint code
ruff literary_structure_generator/

# Type checking
mypy literary_structure_generator/
```

## Documentation

- [Architecture](docs/architecture.md): System diagrams and component relationships
- [ROADMAP.md](ROADMAP.md): Detailed implementation roadmap
- [CONTRIBUTING.md](CONTRIBUTING.md): Development setup and contribution guidelines
- [SECURITY.md](SECURITY.md): Security policy and best practices
- [agentic_short_story_system_instruct_v_0.md](agentic_short_story_system_instruct_v_0.md): Original concept document
- [examples/](examples/): Example configurations and outputs

## License

MIT License - see [LICENSE](LICENSE) for details

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing guidelines, and PR process.

This project is in active development. Contributions welcome!

## Security

See [SECURITY.md](SECURITY.md) for security policy, responsible disclosure, and best practices.

## Citation

If you use this system in your research or creative work, please cite:

```
@software{literary_structure_generator,
  author = {Andrew Michael},
  title = {Literary Structure Generator},
  year = {2024},
  url = {https://github.com/AndrewMichael2020/literary-structure-generator}
}
```
