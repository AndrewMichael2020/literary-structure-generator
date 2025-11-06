# Motif Labeling Prompt Template

**Version:** v1  
**Component:** motif_labeler  
**Purpose:** Label extracted motif anchors with concise thematic tags

---

## Task

You are given a list of motif anchor phrases extracted from a literary text. Your task is to generate concise, evocative thematic labels (1-3 words each) that capture the essence of each motif.

## Guidelines

- Each label should be 1-3 words
- Use lowercase unless proper nouns
- Focus on themes, emotions, or symbolic meanings
- Avoid generic labels like "thing" or "event"
- Labels should be literary/thematic, not literal descriptions

## Input Format

The input will be a list of anchor phrases, one per line.

## Output Format

Return one label per line, in the same order as the input anchors.

## Example

**Input:**
```
blood on the gauze
night sky overhead
trembling hands
```

**Output:**
```
mortality_visceral
cosmic_indifference
anxiety_manifestation
```

---

## Your Task

Label the following motif anchors:

{anchors}
