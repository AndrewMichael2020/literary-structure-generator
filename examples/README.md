# Example Artifacts

This directory contains example configurations, scripts, and outputs for the Literary Structure Generator.

## Example Scripts

### Decision Logging Demo

**File:** `demo_decision_logging.py`

Demonstrates the ReasonLog schema and agent decision logging across a workflow run.

#### Running the Demo

```bash
python examples/demo_decision_logging.py
```

#### What it demonstrates

1. **All Five Agents** logging decisions:
   - **Digest**: LLM model selection
   - **SpecSynth**: Voice parameter synthesis
   - **Generator**: Candidate generation with diversity
   - **Evaluator**: Evaluation suite execution
   - **Optimizer**: Best candidate selection and config updates

2. **Structured Logging**: Each decision includes:
   - Agent name and timestamp
   - Decision description and reasoning
   - Parameters that influenced the decision
   - Outcome (when applicable)
   - Metadata for additional context

3. **Output Directory Structure**:
   ```
   runs/
   └── {run_id}/
       └── iter_{iteration}/
           └── reason_logs/
               ├── Digest_{timestamp}.json
               ├── SpecSynth_{timestamp}.json
               ├── Generator_{timestamp}.json
               ├── Evaluator_{timestamp}.json
               └── Optimizer_{timestamp}.json
   ```

4. **Loading and Filtering Logs**:
   - Load all logs for a run
   - Filter by specific agent
   - Filter by iteration
   - Query decision history

#### Example Output

```json
{
  "schema": "ReasonLog@1",
  "timestamp": "2024-01-15T10:30:00.000000+00:00",
  "run_id": "demo_run_001",
  "iteration": 0,
  "agent": "SpecSynth",
  "decision": "Set voice.person to 'first' based on exemplar digest",
  "reasoning": "Exemplar digest shows 95% first-person pronouns",
  "parameters": {
    "first_person_ratio": 0.95,
    "distance": "intimate",
    "alpha_exemplar": 0.7
  },
  "outcome": "voice.person='first', voice.distance='intimate'",
  "metadata": {}
}
```

## Configuration Examples

### AuthorProfile Examples

- `author_profile_v1.json`: Basic author profile with conservative settings (Clean Mode)
- `author_profile_minimal.json`: Minimal profile for testing

### StorySpec Examples

- `story_spec_emergency.json`: Full spec derived from "Emergency" exemplar

### GenerationConfig Examples

- `generation_config_default.json`: Default generation configuration
- `generation_config_fast.json`: Fast iteration config (fewer candidates, iterations)

## Usage

Load example configurations:

```python
from literary_structure_generator.models import AuthorProfile
from literary_structure_generator.utils.io_utils import load_json

profile = load_json("examples/author_profile_v1.json", AuthorProfile)
```

Use as templates for your own configurations.
