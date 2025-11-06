# Example Artifacts

This directory contains example configurations and outputs for the Literary Structure Generator.

## Files

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
