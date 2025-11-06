# Entity Graph Instructions (docs/entities.md)

## Purpose
Extract a lightweight, deterministic **entity graph** from a literary short story for use in `ExemplarDigest@2` and later evaluation. Avoid heavy NLP dependencies; prefer regex + small lexicons. Keep functions small and deterministic.

## Outputs
Populate these fields in `ExemplarDigest@2`:

```json
"coherence_graph": {
  "entities": [
    {
      "id": "E1",
      "canonical": "Georgie",
      "type": "PERSON",
      "surface_forms": ["Georgie"],
      "aliases": [],
      "mentions": 23
    }
  ],
  "edges": [
    {
      "source": "E1",
      "target": "E2",
      "relation": "co_occurs",
      "weight_sent": 14,
      "weight_para": 6,
      "beats": ["setpiece_1","setpiece_2"]
    }
  ],
  "stats": {
    "num_entities": 0,
    "num_edges": 0,
    "avg_degree": 0.0,
    "largest_component": 0
  }
}
```

### Entity types
`PERSON | PLACE | ORG | OBJECT | ANIMAL | VEHICLE`

### Edge relations
- `co_occurs` – entities appear in the same sentence
- `speaks_to` – speaker attribution link (optional if detected)
- `located_in` – basic place containment if obvious (optional)

---

## Pipeline

### 0) Preprocess
- Split into paragraphs and sentences. Keep indices.
- Detect dialogue spans: regex for quoted text `"..."`.
- Keep a `beat_index` from `digest.discourse.beats` to map each sentence to a beat id.

### 1) Candidate entity detection (heuristics)
- **Capitalized multi-token spans** not at start of sentence, unless in a whitelist.
- **Person-name regex:** `([A-Z][a-z]+)(\s[A-Z][a-z]+)*` with stoplist: weekdays, months, common sentence starters.
- **Place cues:** capitalized tokens followed by words like *Street*, *Ave*, *Hospital*, *County*, or preceded by “in/at”.
- **From imagery/motifs:** concrete nouns in `imagery_palettes` and `motif_map` may seed `OBJECT` candidates.
- Drop anything shorter than 2 chars, or on a configurable blacklist.

### 2) Alias resolution
Deterministic merges in this order:
1. **Exact lowercase match**
2. **Initial + last name** → same last name within a small window
3. **Nickname map** (small static dict, e.g., Jim↔James)
4. **Levenshtein distance ≤ 1** for short names

Prefer the longest surface form as `canonical`. Keep `surface_forms` set. Count mentions.

### 3) Speaker attribution (optional, recommended)
Patterns:
- `"...", said X` or `"...", X said`
- `"...", X said to Y` → set `speaks_to` edge X→Y if Y is a known PERSON
- If no explicit target, link speaker to nearest mentioned PERSON in same paragraph
- If none, target `"Narrator"` virtual node (not included in entities list; used only for edge bookkeeping)

### 4) Co-occurrence edges
For each sentence:
- Add `co_occurs` edges for each unordered pair of detected entities in that sentence
- Increment `weight_sent` by 1 per sentence
- Increment `weight_para` once per paragraph if both appear anywhere in that paragraph
- Append the sentence’s beat id to the edge’s `beats` set

### 5) Beat mapping
Using `digest.discourse.beats` spans (char index or sentence ranges), assign each sentence a `beat_id`. If not present, tag as `"unknown"`.

### 6) Prune and normalize
- Remove entities with `mentions < min_mentions` (default 2)
- Remove edges with `weight_sent < 2` unless `speaks_to`
- Compute stats: `num_entities`, `num_edges`, `avg_degree`, `largest_component`

### 7) Logging
Use `log_decision()`:
```
[Digest] entities=7, edges=12, largest_component=5
[Digest] speakers: {Georgie: 6 quotes, Narrator: 3 quotes}
```

---

## Pydantic snippets

```python
from typing import List, Dict, Union, Literal
from pydantic import BaseModel

class Entity(BaseModel):
    id: str
    canonical: str
    type: Literal["PERSON","PLACE","ORG","OBJECT","ANIMAL","VEHICLE"]
    surface_forms: List[str] = []
    aliases: List[str] = []
    mentions: int

class Edge(BaseModel):
    source: str
    target: str
    relation: Literal["co_occurs","speaks_to","located_in"]
    weight_sent: int = 0
    weight_para: int = 0
    beats: List[str] = []

class CoherenceGraph(BaseModel):
    entities: List[Entity] = []
    edges: List[Edge] = []
    stats: Dict[str, Union[int, float]]
```

---

## Config knobs (`storylab/config/entity_extraction.json`)

```json
{
  "min_mentions": 2,
  "min_edge_weight_sent": 2,
  "merge_levenshtein_max": 1,
  "nickname_map": {"jim":"james","bob":"robert"},
  "place_suffixes": ["Street","St.","Ave","Road","County","Hospital"],
  "blacklist": ["Monday","Tuesday","January","February"]
}
```

---

## Tests

**File:** `tests/test_entities_basic.py`

- Synthetic text with two named people, one place, one object, and quotes.
- Assert:
  - merged aliases work (James + Jim → one node)
  - co_occurs edge weights increment correctly
  - `speaks_to` edges created where patterns match
  - stats computed and plausible
- Keep tests deterministic. No network calls.

Example synthetic text:

```text
James met Jim on Willow Street. "I saw the red car," James said to Jim.
Later, James and Robert walked to County Hospital. "It was loud," said Robert.
```

Expected:
- Entities: James/Jim merged; Robert; Willow Street (PLACE); County Hospital (PLACE); red car (OBJECT)
- Edges: co_occurs pairs; speaks_to from speakers to targets when detected.

---

## Complexity
- Linear in tokens with small constants. Graph size bounded by pruning thresholds.
