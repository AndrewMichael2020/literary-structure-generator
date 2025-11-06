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

## Quick Start

### 1. Generate Exemplar Digest

```python
from literary_structure_generator.digest.assemble import assemble_digest

digest = assemble_digest(
    filepath="Emergency.txt",
    model="gpt-4",
    output_path="artifacts/exemplar_digest_emergency.json"
)
```

### 2. Synthesize StorySpec

```python
from literary_structure_generator.spec.synthesizer import synthesize_spec

spec = synthesize_spec(
    digest=digest,
    story_id="story_001",
    seed=137,
    output_path="artifacts/story_spec_001.json"
)
```

### 3. Generate Story Candidates

```python
from literary_structure_generator.generation.ensemble import generate_ensemble
from literary_structure_generator.models.generation_config import GenerationConfig

config = GenerationConfig(seed=137, num_candidates=8)
candidates = generate_ensemble(spec, config, run_id="run_001")
```

### 4. Evaluate Candidates

```python
from literary_structure_generator.evaluation.assemble import assemble_eval_report

for candidate in candidates:
    report = assemble_eval_report(
        text=candidate["text"],
        run_id="run_001",
        candidate_id=candidate["id"],
        spec=spec,
        digest=digest,
        exemplar_text=exemplar_text,
        config=config
    )
```

### 5. Run Full Pipeline (CLI)

```bash
python -m literary_structure_generator.orchestrators.full_pipeline \
  --exemplar Emergency.txt \
  --author-profile profiles/author_v1.json \
  --story-id story_001 \
  --seed 137 \
  --output-dir artifacts/run_001/ \
  --num-iterations 10 \
  --num-candidates 8
```

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
  - Profanity filtering (Clean Mode)
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
