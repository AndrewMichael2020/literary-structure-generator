# Repair Pass Prompt Template

**Version:** v1  
**Component:** repair_pass  
**Purpose:** Fix constraint violations and improve quality of generated text

---

## Task

You are given a piece of generated text and a list of constraints/issues to fix. Your task is to repair the text while maintaining its narrative intent and style.

## Repair Guidelines

- Fix constraint violations (e.g., length, forbidden words)
- Improve clarity without changing the core narrative
- Maintain the original voice and style
- Preserve character consistency
- Ensure smooth transitions
- Do not add new plot elements

## Common Constraint Types

- **Length**: Adjust to target word count
- **Overlap**: Remove phrases that overlap with exemplar
- **Grit**: Replace with clean alternatives
- **Coherence**: Fix logical inconsistencies
- **Style**: Adjust to match voice specification

## Output Format

Return only the repaired text, without explanations or metadata.

## Example

**Original Text:**
```
The doctor was very, very, very worried about the patient.
```

**Constraints:**
```
- Reduce repetition
- More clinical tone
```

**Repaired Text:**
```
The doctor showed concern for the patient's condition.
```

---

## Your Task

**Original Text:**
```
{text}
```

**Constraints:**
{constraints}

**Repaired Text:**
