# Beat Paraphrase Prompt Template

**Version:** v1  
**Component:** beat_paraphraser  
**Purpose:** Generate concise beat summaries from functional descriptions

---

## Task

You are given a list of beat function descriptions from a story structure. Your task is to paraphrase each function into a concise, evocative summary (5-15 words) suitable for a beat map.

## Guidelines

- Each summary should be 5-15 words
- Use active, vivid language
- Capture the narrative function and emotional tone
- Match the register hint if provided (e.g., "clinical", "lyrical", "terse")
- Summaries should be self-contained and clear

## Register Hints

- **clinical**: objective, detached, precise
- **lyrical**: poetic, flowing, metaphorical
- **terse**: brief, punchy, direct
- **neutral**: balanced, clear, accessible

## Input Format

The input will be a list of beat functions, one per line, optionally with a register hint.

## Output Format

Return one summary per line, in the same order as the input functions.

## Example

**Input (register: terse):**
```
establish setting and tone
develop conflict and action
resolution and denouement
```

**Output:**
```
Set scene, establish stakes
Conflict escalates, choices narrow
Aftermath, consequences settle
```

---

## Your Task

Register hint: {register_hint}

Paraphrase the following beat functions:

{functions}
