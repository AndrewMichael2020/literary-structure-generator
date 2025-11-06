# Imagery Naming Prompt Template

**Version:** v1  
**Component:** imagery_namer  
**Purpose:** Generate evocative names for imagery palette categories

---

## Task

You are given a list of imagery phrases (concrete nouns and adjective-noun pairs) extracted from a literary text. Your task is to generate evocative category names that capture the sensory/symbolic essence of each phrase.

## Guidelines

- Each name should be 1-3 words
- Use lowercase with underscores (e.g., "winter_silence")
- Focus on sensory qualities, atmosphere, or symbolic meaning
- Capture both literal and metaphorical dimensions
- Avoid generic categories

## Input Format

The input will be a list of imagery phrases, one per line.

## Output Format

Return one category name per line, in the same order as the input phrases.

## Example

**Input:**
```
white hospital walls
copper taste of blood
sterile instrument tray
```

**Output:**
```
clinical_emptiness
metallic_mortality
surgical_precision
```

---

## Your Task

Name the following imagery phrases:

{phrases}
