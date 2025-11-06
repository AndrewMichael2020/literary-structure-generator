# Literary Structure Generator

An agentic workflow for literary short-story generation that learns structural DNA from exemplar texts and generates new stories with similar form but original content.

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

### Reproducibility
- Same seed + config → same output
- All artifacts JSON-serializable
- Version tracking for schemas

## Architecture

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
   - Profanity policy, content safety

### Main Modules

- **digest/**: Exemplar analysis and DNA extraction
- **spec/**: StorySpec synthesis from digest
- **generation/**: Beat-by-beat draft generation with LLMs
- **evaluation/**: Multi-metric scoring and quality assessment
- **optimization/**: Iterative refinement loop
- **profiles/**: AuthorProfile management and learning
- **orchestrators/**: End-to-end workflow automation
- **utils/**: Shared utilities (text processing, similarity, I/O)

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

**Current Phase**: Foundation & Scaffolding ✅

This is the initial scaffolding with:
- ✅ Project structure and configuration
- ✅ Pydantic models for all data artifacts
- ✅ Module stubs with docstrings
- ✅ Roadmap and development plan

**Next Steps** (see [ROADMAP.md](ROADMAP.md)):
- Phase 2: Implement ExemplarDigest pipeline
- Phase 3: Implement StorySpec synthesis
- Phase 4: Implement draft generation
- Phase 5: Implement evaluation suite
- Phase 6: Implement optimization loop

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

- [ROADMAP.md](ROADMAP.md): Detailed implementation roadmap
- [agentic_short_story_system_instruct_v_0.md](agentic_short_story_system_instruct_v_0.md): Original concept document
- [examples/](examples/): Example configurations and outputs

## License

MIT License - see [LICENSE](LICENSE) for details

## Contributing

This project is in early development. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

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
