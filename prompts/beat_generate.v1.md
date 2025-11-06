# Beat Generation Prompt Template

**Version:** v1  
**Component:** beat_generator  
**Purpose:** Generate prose for a single story beat

---

## Task

You are generating a specific beat (narrative unit) for a short story. Your task is to write compelling prose that fulfills the beat's function while adhering to the specified voice, style, and content parameters.

## Beat Specification

**Function:** {function}  
**Summary:** {summary}  
**Target words:** {target_words}  
**Cadence:** {cadence}

## Voice & Style Parameters

**Person:** {person}  
**Distance:** {distance}  
**Tense:** {tense}  

**Syntax:**
- Average sentence length: {avg_sentence_len} words (variance: {sentence_variance})
- Style: {parataxis_style}
- Fragments allowed: {fragments_ok}

**Register:**
{register_info}

**Dialogue ratio hint:** {dialogue_ratio} (approximate - use as a guide, not strict rule)

## Content Guidance

**Setting:** {setting_place}, {setting_time}

**Characters:**
{character_names}

**Motifs/themes to weave lightly (not literally):**
{motifs}

**Imagery palette (use sparingly):**
{imagery}

**Props:**
{props}

## Constraints

- Write exactly this beat, do not skip ahead to future beats
- Stay within {target_words} ± 20% word count
- Use character names only; do not copy exemplar phrasing
- Avoid clichés and unearned epiphanies
- Match the specified voice and syntax parameters
- Keep motifs subtle and organic to the narrative

## Output Format

Return only the prose text for this beat. No explanations, no metadata, no additional commentary.

---

**Generate the beat:**
