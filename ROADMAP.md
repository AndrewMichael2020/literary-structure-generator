# Literary Structure Generator — Implementation Roadmap

## System Summary

This project implements an agentic workflow for literary short-story generation that learns structural DNA from exemplar texts (starting with Denis Johnson's "Emergency") and generates new stories with similar form but original content.

### Core Architecture

**Key Principle**: Separate "Form" from "Content"
- Extract reusable structure (beats, transitions, voice) from exemplar
- Swap in new content (setting, characters, themes)
- Iterate through: **Spec → Draft → Critique → Revise**

**Main Workflow**: `Exemplar → Digest → StorySpec → Generate Candidates → Evaluate → Optimize → Final Story`

### Core Data Artifacts (JSON/Pydantic Models)

1. **ExemplarDigest**: Extracted DNA from exemplar text
   - Stylometry (sentence length, POS patterns, punctuation)
   - Discourse structure (beats, dialogue ratio, focalization)
   - Pacing curves, motif maps, imagery palettes
   - Coherence graphs, event scripts

2. **StorySpec**: Portable specification for story generation
   - Voice (POV, tense, distance, register, syntax, diction)
   - Form (structure, beat map, scene/summary ratios)
   - Content (setting, characters, motifs, imagery)
   - Constraints (anti-plagiarism, length, safety)

3. **GenerationConfig**: Orchestrator control parameters
   - LLM parameters (temperature, top_p, seeds)
   - Diversity controls, constraint enforcement
   - Evaluator suite configuration
   - Optimizer settings (Adam-ish schedule)

4. **EvalReport**: Multi-metric assessment per candidate
   - Scores (stylefit, formfit, coherence, freshness, overlap_guard)
   - Per-beat analysis, coherence graphs
   - Drift analysis, tuning suggestions
   - Guardrail pass/fail, reproducibility data

### Anti-Plagiarism Guardrails

- Max shared n-gram ≤ 12 tokens
- Overall overlap ≤ 3% vs exemplar
- SimHash Hamming distance ≥ 18 for 256-bit chunks
- No verbatim paragraphs stored in artifacts

---

## Phase 1: Foundation & Data Contracts (Week 1-2)

### 1.1 Project Setup
**Deliverable**: Basic Python project structure

**Tasks**:
- [x] Create folder structure:
  ```
  literary_structure_generator/
  ├── models/          # Pydantic schemas
  ├── digest/          # Exemplar analysis
  ├── spec/            # StorySpec synthesis
  ├── generation/      # Draft generation
  ├── evaluation/      # Scoring & metrics
  ├── optimization/    # Optimizer loop
  ├── profiles/        # AuthorProfile utilities
  ├── orchestrators/   # High-level workflows
  └── utils/           # Shared utilities
  ```
- [x] Add `pyproject.toml` with dependencies (pydantic, spacy, etc.)
- [x] Add `requirements.txt` for pip users
- [x] Create `__init__.py` in all modules

**Dependencies** (initial):
- `pydantic>=2.0` — Data validation
- `spacy>=3.0` — NLP analysis
- `numpy` — Numerical operations
- `simhash` — Similarity detection
- `openai` or `anthropic` — LLM integration (placeholder)

### 1.2 Core Data Models
**Deliverable**: Pydantic schemas for all 4 artifacts

**Tasks**:
- [x] `models/exemplar_digest.py` — ExemplarDigest@2 schema
- [x] `models/story_spec.py` — StorySpec@2 schema
- [x] `models/generation_config.py` — GenerationConfig@2 schema
- [x] `models/eval_report.py` — EvalReport@2 schema
- [x] `models/author_profile.py` — AuthorProfile@1 schema
- [x] Add version fields, validation rules
- [x] Create example JSON files in `examples/`

**Validation Rules**:
- Schema version tracking
- Seed reproducibility
- Range checks on sliders (0.0-1.0)
- Required field enforcement

---

## Phase 2: ExemplarDigest — Extract Story DNA (Week 3-4)

### 2.1 Heuristic Analyzers
**Deliverable**: Statistical extraction from Emergency.txt

**Modules**:
- [x] `digest/stylometry.py` — Sentence length histograms, type-token ratio, MTLD, POS n-grams, punctuation density
- [x] `digest/discourse.py` — Scene/summary detection, dialogue extraction, tense distribution
- [x] `digest/pacing.py` — Pacing curves, paragraph length distribution, whitespace analysis
- [x] `digest/coherence.py` — Entity tracking, pronoun chains, temporal markers

**Tests**:
- Load Emergency.txt
- Run heuristic pipeline
- Validate output matches expected distributions
- Check no verbatim text stored

### 2.2 LLM-Assisted Annotation
**Deliverable**: Beat labeling and motif extraction

**Modules**:
- [x] `digest/beat_labeler.py` — LLM prompts to identify structural beats (cold_open, inciting_turn, setpieces, coda)
- [x] `digest/motif_extractor.py` — Identify recurring themes, imagery palettes, event scripts
- [x] `digest/voice_analyzer.py` — POV distance, free indirect discourse markers

**Integration**:
- Combine heuristic + LLM outputs → `ExemplarDigest.json`
- Add versioning, metadata
- Export visualization plots (optional)

### 2.3 Digest Assembler
**Deliverable**: `digest/assemble.py` — orchestrate full digest pipeline

**Tasks**:
- [x] Load exemplar text
- [x] Run all analyzers in sequence
- [x] Merge results into ExemplarDigest model
- [x] Validate against schema
- [x] Save to `artifacts/exemplar_digest_emergency.json`

---

## Phase 3: StorySpec Synthesis (Week 5)

### 3.1 Spec Generator
**Deliverable**: `spec/synthesizer.py` — map Digest → initial StorySpec

**Logic**:
- Copy voice parameters from Digest (sentence length, register, syntax)
- Copy form structure (beat map, ratios)
- Initialize content section with placeholders
- Set constraints from anti-plagiarism policy

**Tunable Sliders**:
- Allow manual adjustments to register sliders
- Content swap (new setting, characters, motifs)
- Constraint relaxation (for testing)

### 3.2 AuthorProfile Integration
**Deliverable**: `profiles/author_profile.py` — blend exemplar + user voice

**Tasks**:
- [x] Define blending weights (`alpha_exemplar` vs `alpha_author`)
- [x] Support "Clean Mode" (no profanity) vs "Grit Mode" (future)
- [x] Create sample `AuthorProfile.json` templates

**Example Blending**:
- `avg_sentence_len = 0.7 * exemplar_len + 0.3 * author_len`
- Register sliders: weighted average

---

## Phase 4: Draft Generation (Week 6-7)

### 4.1 Beat-by-Beat Prompting
**Deliverable**: `generation/beat_drafter.py` — structured prompts per beat

**Prompt Template**:
```
You are the Drafter. Using StorySpec beat {id}, write ~{target_words} words
in {voice.person} POV with {voice.distance} distance.
Honor dialogue_ratio {ratio}. Keep syntax: avg_len={avg}, fragments_ok={frag}.
Avoid phrasing >12 tokens from exemplar.
Transition: {next_hint}.
```

**Features**:
- Temperature sweeps per beat
- Repetition penalty
- Stop sequences
- Length tolerance (±20%)

### 4.2 Candidate Ensemble
**Deliverable**: `generation/ensemble.py` — generate k candidates

**Strategy**:
- Generate 6-8 candidates per run
- Vary: temperature, seed, beat shuffle (±15%)
- Spec jitter: small random variations to sliders
- Parallel generation (async LLM calls)

### 4.3 Constraint Enforcement
**Deliverable**: `generation/constraints.py` — real-time guardrails

**Checks**:
- Max n-gram vs exemplar (reject if >12)
- Lexicon filters (taboo words)
- Length targets (min/max)
- POV consistency

---

## Phase 5: Evaluation Suite (Week 8-9)

### 5.1 Automated Metrics
**Deliverable**: `evaluation/metrics/` — objective scores

**Modules**:
- [x] `stylefit.py` — Cosine similarity to AuthorProfile + Digest (sentence length dist, POS, function words)
- [x] `formfit.py` — Beat coverage, scene/summary ratio, dialogue balance
- [x] `coherence.py` — Entity tracking, pronoun resolution, contradiction detection
- [x] `freshness.py` — SimHash distance, semantic novelty vs exemplar
- [x] `overlap_guard.py` — N-gram overlap, Levenshtein bursts

**Output**: Per-metric score 0.0-1.0, rationale text

### 5.2 Subjective Rubrics (LLM-Assisted)
**Deliverable**: `evaluation/subjective.py` — qualitative assessment

**Prompts**:
- Does the ending re-color earlier beats without preaching?
- Are "numinous" moments grounded in concrete detail?
- Prose texture: concreteness, sensory spread, verb energy

**Output**: Boolean + short justification

### 5.3 Report Assembler
**Deliverable**: `evaluation/assemble.py` — generate EvalReport

**Tasks**:
- [x] Run all metrics on candidate
- [x] Compute weighted overall score
- [x] Identify red flags (POV drift, mode collapse)
- [x] Generate tuning suggestions
- [x] Save to `artifacts/eval_report_{candidate_id}.json`

---

## Phase 6: Optimization Loop (Week 10-11)

### 6.1 Optimizer (Adam-ish)
**Deliverable**: `optimization/optimizer.py` — iterative refinement

**Algorithm**:
- Start: warmup iterations (2) with fixed config
- Iterate: adjust GenerationConfig + Spec sliders based on gradients
- Patience: stop if no improvement for 3 iterations
- Exploration: random jitter to escape local minima

**Parameters**:
- Step size, beta1, beta2 (Adam momentum)
- Exploration radius
- Population size for evolutionary sampling

### 6.2 Workflow Orchestration
**Deliverable**: `orchestrators/full_pipeline.py` — end-to-end automation

**Workflow**:
1. Load exemplar → Digest
2. Synthesize StorySpec (with AuthorProfile)
3. Generate k candidates
4. Evaluate all
5. Select best, update config
6. Iterate (up to max_iters)
7. Output final story + artifacts

**CLI**:
```bash
python -m literary_structure_generator.orchestrators.full_pipeline \
  --exemplar Emergency.txt \
  --author-profile profiles/author_v1.json \
  --output artifacts/run_001/
```

---

## Phase 7: Testing & Validation (Week 12)

### 7.1 Reconstruction Test
**Deliverable**: Validate Spec can reconstruct exemplar *form* (not text)

**Test**:
- Run full pipeline with Emergency.txt as exemplar
- Generate story targeting same beat structure
- Verify: no verbatim text, but beat functions match
- Metrics: formfit >0.7, overlap <3%, stylefit >0.65

### 7.2 Unit Tests
**Files**: `tests/test_*.py`

**Coverage**:
- [x] Pydantic model validation
- [x] Digest analyzers (stylometry, discourse)
- [x] Spec synthesis
- [x] Metrics (stylefit, formfit, overlap_guard)
- [x] Optimizer convergence

### 7.3 Integration Tests
**Test**: Full pipeline with small exemplar

**Assertions**:
- All artifacts created
- Schemas valid
- Guardrails enforced
- Reproducibility (same seed → same output)

---

## Phase 8: First Original Story (Week 13)

### 8.1 Content Swap
**Tasks**:
- Edit StorySpec.content: new setting, characters, motifs
- Keep voice + form from Emergency digest
- Run generation pipeline

**Example**:
- Original: ER room, drug-fueled accidents
- New: Late-night diner, philosophical conversations, small-town ennui

### 8.2 Iteration & Refinement
**Process**:
- Generate candidates
- Review EvalReports
- Adjust sliders (lyric ↑, dialogue_ratio ↓)
- Re-run optimizer
- Human review final draft

---

## Phase 9: Multi-Exemplar Generalization (Future)

### 9.1 Exemplar Library
**Goal**: Extract digests from multiple authors/stories

**Tasks**:
- [ ] Add 5-10 more exemplars (Carver, Munro, Saunders)
- [ ] Generate Digests for each
- [ ] Cluster analysis: identify reusable "forms"

### 9.2 Form Templates
**Deliverable**: Pre-built StorySpec templates

**Examples**:
- "Carver-style minimalism" (low register, short sentences, high dialogue)
- "Saunders satire" (high irony, anachronism, absurdist beats)
- "Munro time-weave" (complex analepsis, distant narrator)

---

## Phase 10: Advanced Features (Future Backlog)

### 10.1 Vision Grounding
**Integration**: `utils/vision_analyzer.py`

**Flow**:
- User uploads photos → Vision LLM extracts objects, mood, lighting
- Inject into imagery_palette and sensory_quotas
- Anchor beats to visual anchors

### 10.2 Profanity/Grit Mode
**Toggle**: `profanity.allowed = true` in AuthorProfile

**Safety**:
- Use permissive content-policy models
- Set frequency caps (e.g., max 2 instances)
- Keep n-gram/SimHash guardrails

### 10.3 Interactive Tuning UI
**Deliverable**: Web interface for spec editing

**Features**:
- Slider controls for voice/form parameters
- Real-time preview of generated beats
- Diff view vs exemplar digest
- One-click re-generation

---

## File/Folder Structure (Python Project)

```
literary-structure-generator/
│
├── literary_structure_generator/       # Main package
│   ├── __init__.py
│   │
│   ├── models/                         # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── exemplar_digest.py
│   │   ├── story_spec.py
│   │   ├── generation_config.py
│   │   ├── eval_report.py
│   │   └── author_profile.py
│   │
│   ├── digest/                         # Exemplar analysis
│   │   ├── __init__.py
│   │   ├── stylometry.py
│   │   ├── discourse.py
│   │   ├── pacing.py
│   │   ├── coherence.py
│   │   ├── beat_labeler.py
│   │   ├── motif_extractor.py
│   │   ├── voice_analyzer.py
│   │   └── assemble.py
│   │
│   ├── spec/                           # StorySpec synthesis
│   │   ├── __init__.py
│   │   └── synthesizer.py
│   │
│   ├── generation/                     # Draft generation
│   │   ├── __init__.py
│   │   ├── beat_drafter.py
│   │   ├── ensemble.py
│   │   └── constraints.py
│   │
│   ├── evaluation/                     # Scoring & metrics
│   │   ├── __init__.py
│   │   ├── metrics/
│   │   │   ├── __init__.py
│   │   │   ├── stylefit.py
│   │   │   ├── formfit.py
│   │   │   ├── coherence.py
│   │   │   ├── freshness.py
│   │   │   └── overlap_guard.py
│   │   ├── subjective.py
│   │   └── assemble.py
│   │
│   ├── optimization/                   # Optimizer loop
│   │   ├── __init__.py
│   │   └── optimizer.py
│   │
│   ├── profiles/                       # AuthorProfile utilities
│   │   ├── __init__.py
│   │   ├── author_profile.py
│   │   └── learn_author_profile.py
│   │
│   ├── orchestrators/                  # High-level workflows
│   │   ├── __init__.py
│   │   └── full_pipeline.py
│   │
│   └── utils/                          # Shared utilities
│       ├── __init__.py
│       ├── text_utils.py               # Tokenization, n-gram extraction
│       ├── similarity.py               # SimHash, Levenshtein
│       └── io_utils.py                 # JSON serialization
│
├── tests/                              # Test suite
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_digest.py
│   ├── test_spec.py
│   ├── test_generation.py
│   ├── test_evaluation.py
│   └── test_optimization.py
│
├── examples/                           # Example artifacts
│   ├── author_profile_v1.json
│   ├── story_spec_emergency.json
│   ├── generation_config_default.json
│   └── README.md
│
├── artifacts/                          # Runtime outputs (gitignored)
│   └── .gitkeep
│
├── pyproject.toml                      # Poetry/pip config
├── requirements.txt                    # Pip dependencies
├── README.md                           # Project overview
├── ROADMAP.md                          # This file
├── agentic_short_story_system_instruct_v_0.md  # Concept doc
└── Emergency.txt                       # Exemplar text

```

---

## Next Steps (Immediate Actions)

1. **Set up project structure** (Phase 1.1)
   - Create all folders and `__init__.py` files
   - Add `pyproject.toml` and `requirements.txt`

2. **Define Pydantic models** (Phase 1.2)
   - Implement all 5 schemas with validation
   - Create example JSON files

3. **Start digest pipeline** (Phase 2.1)
   - Implement stylometry.py with spaCy
   - Test on Emergency.txt

4. **Iterate incrementally**
   - Each module gets its own Issue/PR
   - Write tests alongside implementation
   - Review artifacts at each stage

---

## Success Metrics

- **Reconstruction Test**: Generate story with Emergency form, <3% overlap
- **Original Story**: New content + learned form scores >0.7 overall
- **Reproducibility**: Same seed → identical output
- **Observability**: All artifacts JSON-serializable, diffable, auditable
- **Modularity**: Each phase independently testable

---

## Notes on Incremental Development

- **Start simple**: Heuristics before LLMs; hard-coded beats before learned ones
- **Fail fast**: Add guardrails early (overlap checks, length limits)
- **Trace everything**: Every decision writes to JSON
- **Human-in-loop optional**: Core loop converges autonomously; manual tuning optional
- **Avoid premature optimization**: Get one full pass working before refining algorithms

---

**Status**: Roadmap complete. Ready for Phase 1 scaffolding.
