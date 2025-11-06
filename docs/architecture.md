# Architecture Documentation

This document provides detailed architecture diagrams for the Literary Structure Generator system. Each diagram is followed by a brief explanation of the components and their relationships.

---

## 1. High-Level Pipeline

The complete end-to-end pipeline from exemplar to optimized story:

```mermaid
flowchart LR
    A[Exemplar Text] --> B[Digest Pipeline]
    B --> C[ExemplarDigest]
    C --> D[Spec Synthesizer]
    D --> E[StorySpec]
    E --> F[Generate Candidates]
    F --> G[Candidate Drafts]
    G --> H[Evaluate]
    H --> I[EvalReports]
    I --> J[Optimize]
    J --> K{Converged?}
    K -->|No| E
    K -->|Yes| L[Final Story]
    
    style A fill:#e1f5ff
    style L fill:#d4edda
    style C fill:#fff3cd
    style E fill:#fff3cd
    style I fill:#fff3cd
```

**Explanation:**
The pipeline begins with an exemplar text that is analyzed by the digest pipeline to extract its structural DNA (stylometry, discourse patterns, pacing, motifs). This produces an `ExemplarDigest`. The spec synthesizer then creates a portable `StorySpec` that maps voice, form, and content parameters. Multiple candidate drafts are generated from the spec, evaluated using a comprehensive suite of metrics, and iteratively optimized until convergence. The system supports reproducibility through seeded randomness and JSON-serializable artifacts at each stage.

---

## 2. LLM Routing, Caching & Prompt Flow

How LLM calls are routed, cached, and executed with drift control:

```mermaid
flowchart TB
    A[Component Request] --> B[Router]
    B --> C{Check Config}
    C -->|Component Override| D[Get Component Config]
    C -->|Default| E[Get Global Config]
    D --> F[Load Prompt Template]
    E --> F
    F --> G{Check Cache?}
    G -->|Yes| H[LLMCache SQLite]
    H -->|Hit| I[Return Cached]
    H -->|Miss| J{Provider?}
    G -->|No| J
    J -->|mock| K[MockClient]
    J -->|openai| L[OpenAIClient]
    J -->|anthropic| M[AnthropicClient]
    K --> N[LLM Response]
    L --> N
    M --> N
    N --> O[Apply Grit Filter]
    O --> P[Compute Checksum]
    P --> Q[Log Decision]
    Q --> R[Cache Result]
    R --> S[Return to Component]
    
    style H fill:#fff3cd
    style O fill:#f8d7da
    style Q fill:#d1ecf1
```

**Explanation:**
The LLM router centralizes all LLM interactions. When a component (e.g., `motif_labeler`, `beat_paraphraser`) requests LLM completion, the router checks for component-specific or global configuration. It loads the versioned prompt template from the `prompts/` directory, optionally checks the SQLite cache (keyed by prompt + params), and dispatches to the appropriate client (Mock, OpenAI, or Anthropic). Responses pass through the universal grit filter, are checksummed for drift detection, logged for reproducibility, cached for efficiency, and returned to the caller.

---

## 3. Per-Beat Generation Sequence

Detailed sequence of generating a single beat with memory and validation:

```mermaid
sequenceDiagram
    participant DG as DraftGenerator
    participant BG as BeatGenerator
    participant Router as LLMRouter
    participant LLM as LLM Client
    participant Guards as Guards
    participant Filter as GritFilter
    
    DG->>BG: generate_beat_text(beat_spec, memory)
    BG->>BG: Build context from memory
    BG->>Router: Request LLM completion
    Router->>LLM: complete(prompt)
    LLM-->>Router: raw_text
    Router->>Filter: structural_bleep(raw_text)
    Filter-->>Router: filtered_text
    Router-->>BG: filtered_text
    BG->>Guards: Check constraints
    Guards->>Guards: Length validation
    Guards->>Guards: Grit check
    Guards-->>BG: validation_result
    alt Validation Pass
        BG->>BG: Update memory
        BG-->>DG: beat_result
    else Validation Fail
        BG->>BG: Retry with adjusted params
        BG->>Router: Request retry
    end
    DG->>DG: Append to beat_texts[]
```

**Explanation:**
Beat generation is context-aware and iterative. The `DraftGenerator` orchestrates per-beat generation, passing accumulated memory (previous beats' text and functions) to the `BeatGenerator`. The generator constructs a prompt enriched with context, requests completion via the router, and receives grit-filtered text. Guards validate length and content constraints. If validation fails, the generator retries with adjusted parameters (e.g., reduced temperature, stricter length hints). Successfully validated beats update the memory context for subsequent beats.

---

## 4. Evaluation Suite Composition

How multiple evaluators contribute to a comprehensive `EvalReport`:

```mermaid
flowchart TB
    A[Generated Text] --> B[Evaluation Orchestrator]
    B --> C[StyleFit Rules]
    B --> D[StyleFit LLM]
    B --> E[FormFit]
    B --> F[CoherenceGraphFit]
    B --> G[MotifImageryCoverage]
    B --> H[OverlapGuard]
    B --> I[CadencePacing]
    B --> J[ValenceArcFit]
    
    C --> K[Component Scores]
    D --> K
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K
    
    K --> L[Weighted Aggregation]
    L --> M[Overall Score]
    
    K --> N[Drift Detection]
    N --> O[Identify Deviations]
    
    K --> P[Red Flag Detection]
    P --> Q[Constraint Violations]
    
    M --> R[EvalReport@2]
    O --> R
    Q --> R
    R --> S[Tuning Suggestions]
    
    style R fill:#d4edda
    style S fill:#fff3cd
```

**Explanation:**
The evaluation orchestrator runs a comprehensive suite of 8+ evaluators in parallel. **StyleFit** evaluators check voice conformance (POV, tense, syntax patterns) using both heuristic rules and optional LLM scoring. **FormFit** validates structural adherence (beat lengths, dialogue ratio, scene/summary balance). **CoherenceGraphFit** ensures entity consistency and narrative coherence. **MotifImageryCoverage** verifies thematic alignment. **OverlapGuard** enforces anti-plagiarism constraints (n-gram overlap, SimHash distance). **CadencePacing** checks rhythm and paragraph variance. **ValenceArcFit** validates emotional trajectory. Component scores are aggregated with configurable weights to produce an overall score. The report also includes drift items (deviations from spec), red flags (hard constraint violations), and tuning suggestions for the optimizer.

---

## 5. Runs & Artifacts Layout

File system organization of runs, iterations, and artifacts:

```mermaid
flowchart LR
    A[runs/] --> B[llm_cache.db]
    A --> C[run_001/]
    C --> D[iter_0/]
    C --> E[iter_1/]
    C --> F[iter_N/]
    
    D --> G[candidates/]
    D --> H[eval_reports/]
    D --> I[spec.json]
    D --> J[config.json]
    D --> K[decisions.jsonl]
    
    G --> L[candidate_0.txt]
    G --> M[candidate_1.txt]
    G --> N[candidate_N.txt]
    
    H --> O[eval_0.json]
    H --> P[eval_1.json]
    H --> Q[eval_N.json]
    
    style A fill:#e1f5ff
    style B fill:#fff3cd
    style I fill:#fff3cd
    style J fill:#fff3cd
    style K fill:#d1ecf1
```

**Explanation:**
The `runs/` directory contains all execution artifacts. `llm_cache.db` is a shared SQLite cache for LLM responses, keyed by (component, model, prompt_version, params, prompt_text). Each run gets a timestamped directory (e.g., `run_001/`), which contains subdirectories for each optimization iteration. Within each iteration: `candidates/` stores generated draft texts, `eval_reports/` stores JSON evaluation results, `spec.json` captures the current `StorySpec`, `config.json` stores the `GenerationConfig`, and `decisions.jsonl` logs every decision made by agents (LLM calls, optimizer adjustments, etc.) in append-only JSONL format for full reproducibility and auditing.

---

## 6. Data Model Relationships

Core Pydantic models and their relationships:

```mermaid
classDiagram
    class ExemplarDigest {
        +schema_version: str
        +stylometry: Stylometry
        +discourse: Discourse
        +pacing: Pacing
        +coherence: Coherence
        +motifs: list[MotifPattern]
        +imagery_palette: list[ImageryCategory]
        +valence_arc: ValenceArc
    }
    
    class StorySpec {
        +schema_version: str
        +story_id: str
        +voice: Voice
        +form: Form
        +content: Content
        +constraints: Constraints
    }
    
    class GenerationConfig {
        +schema_version: str
        +seed: int
        +num_candidates: int
        +per_beat_generation: PerBeatGeneration
        +diversity: Diversity
        +constraint_enforcement: ConstraintEnforcement
        +repair_steps: RepairSteps
        +grit: Grit
        +optimizer: Optimizer
    }
    
    class EvalReport {
        +schema_version: str
        +run_id: str
        +candidate_id: str
        +scores: Scores
        +per_beat: list[PerBeatScore]
        +drift: list[DriftItem]
        +red_flags: list[str]
        +tuning_suggestions: list[TuningSuggestion]
    }
    
    class AuthorProfile {
        +schema_version: str
        +profile_id: str
        +voice_prefs: VoicePrefs
        +lexicon: Lexicon
        +grit: GritPolicy
        +content_safety: ContentSafety
    }
    
    ExemplarDigest --> StorySpec : synthesizes
    StorySpec --> GenerationConfig : configures
    StorySpec --> EvalReport : evaluates against
    AuthorProfile --> StorySpec : influences
    GenerationConfig --> EvalReport : parameterizes
```

**Explanation:**
The system uses five core Pydantic models as JSON-serializable data artifacts:

1. **ExemplarDigest** captures the structural DNA extracted from an exemplar text (voice patterns, discourse structure, pacing rhythms, coherence graphs, motifs, imagery, emotional arc).

2. **StorySpec** is synthesized from the digest and represents a portable specification for generation. It defines voice parameters (POV, tense, syntax), form (beat structure, dialogue ratio), content (setting, characters, themes), and anti-plagiarism constraints.

3. **GenerationConfig** controls the orchestrator's behavior: LLM sampling parameters, diversity controls, constraint enforcement, repair settings, grit filtering, evaluator suite composition, and optimizer hyperparameters.

4. **EvalReport** contains comprehensive evaluation results: component scores, per-beat analysis, drift detection (deviations from spec), red flags (constraint violations), and tuning suggestions for iterative improvement.

5. **AuthorProfile** captures user voice preferences and can be learned from a corpus or manually configured. It influences spec synthesis by blending with exemplar patterns.

All models are versioned (e.g., `@2`) for schema evolution and use Pydantic for validation, type safety, and JSON serialization.

---

## Key Design Principles

1. **Reproducibility**: Seeded randomness, versioned prompts, decision logging, and JSON artifacts enable exact reproduction of any run.

2. **Modularity**: Each component (digest, spec, generation, evaluation, optimization) is independently testable and swappable.

3. **Transparency**: All LLM calls, decisions, and intermediate artifacts are logged and inspectable.

4. **Anti-Plagiarism**: Multi-layered guards (n-gram overlap, SimHash distance, entity blocking) prevent verbatim copying.

5. **Drift Control**: Prompt versioning, semantic checksums, and low-temperature sampling prevent model drift.

6. **Grit Handling**: Universal `[bleep]` filtering maintains narrative authenticity while ensuring content safety.

7. **Iterative Refinement**: Evaluation-driven optimization loop continuously improves quality through targeted adjustments.
