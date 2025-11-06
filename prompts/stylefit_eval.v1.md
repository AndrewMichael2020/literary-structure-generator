# Stylefit Scoring Prompt Template

**Version:** v1  
**Component:** stylefit  
**Purpose:** Score how well generated text matches a style specification

---

## Task

You are given a piece of generated text and a style specification summary. Your task is to score (0.0-1.0) how well the text matches the specified style.

## Scoring Criteria

Evaluate the text on:
- **Sentence structure**: Does it match the target sentence length and complexity?
- **Voice/POV**: Does it maintain consistent person and distance?
- **Diction**: Does the word choice match the register?
- **Rhythm**: Does the pacing and cadence feel right?
- **Dialogue style**: If present, does it match conventions?

## Scoring Scale

- **0.9-1.0**: Excellent match, natural and consistent
- **0.7-0.89**: Good match, minor deviations
- **0.5-0.69**: Moderate match, noticeable deviations
- **0.3-0.49**: Poor match, significant deviations
- **0.0-0.29**: Very poor match, style mismatch

## Output Format

Return only a single floating-point number between 0.0 and 1.0.

## Example

**Style Spec:**
```
Person: first, Distance: intimate, Avg sentence: 12 words, Register: conversational
```

**Text:**
```
I remember the night it happened. The air was thick. We didn't speak.
```

**Output:**
```
0.85
```

---

## Your Task

**Style Spec:**
{spec_summary}

**Text:**
{text}

**Score (0.0-1.0):**
