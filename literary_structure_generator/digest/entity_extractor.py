"""
Entity Extractor module

Heuristic-based entity extraction for the coherence graph.
Extracts entities (PERSON, PLACE, ORG, OBJECT, ANIMAL, VEHICLE) and relationships.

Follows the spec from instructions_on_graph_entities.md
"""

import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from literary_structure_generator.models.exemplar_digest import Beat, Edge, Entity
from literary_structure_generator.utils.decision_logger import log_decision


# Blacklist of common sentence starters, weekdays, months
ENTITY_BLACKLIST = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "the", "a", "an", "and", "but", "or", "so", "yet",
}

# Place suffixes that indicate a PLACE entity
PLACE_SUFFIXES = [
    "street", "st.", "st", "ave", "avenue", "road", "rd", "county", "hospital",
    "park", "building", "center", "centre", "square", "plaza", "lane",
]

# Nickname map for alias resolution
NICKNAME_MAP = {
    "jim": "james",
    "jimmy": "james",
    "bob": "robert",
    "bobby": "robert",
    "dick": "richard",
    "rick": "richard",
    "bill": "william",
    "will": "william",
    "mike": "michael",
    "dan": "daniel",
    "dave": "david",
    "chris": "christopher",
    "tony": "anthony",
    "joe": "joseph",
    "ben": "benjamin",
    "matt": "matthew",
}


def _tokenize_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r"[.!?]+(?:\s+|$)", text)
    return [s.strip() for s in sentences if s.strip()]


def _split_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _detect_capitalized_spans(sentence: str, is_sentence_start: bool = False) -> List[str]:
    """
    Detect capitalized multi-token spans that could be entities.
    
    Args:
        sentence: Input sentence
        is_sentence_start: Whether this is the first sentence in a context
        
    Returns:
        List of capitalized spans
    """
    # Find capitalized words, allowing for multi-word names
    # Pattern: Capital letter + lowercase letters, optionally repeated
    pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
    matches = re.findall(pattern, sentence)
    
    candidates = []
    for match in matches:
        # Skip if on blacklist
        if match.lower() in ENTITY_BLACKLIST:
            continue
        # Skip single-letter words unless they're "I"
        if len(match) < 2 and match != "I":
            continue
        candidates.append(match)
    
    return candidates


def _classify_entity_type(text: str, context: str = "") -> str:
    """
    Classify entity type based on heuristics.
    
    Args:
        text: Entity text
        context: Surrounding context
        
    Returns:
        Entity type: PERSON, PLACE, ORG, OBJECT, ANIMAL, VEHICLE
    """
    text_lower = text.lower()
    context_lower = context.lower()
    
    # Check for place suffixes
    for suffix in PLACE_SUFFIXES:
        if text_lower.endswith(suffix):
            return "PLACE"
    
    # Check for place prepositions in context
    place_patterns = [
        r"\bin\s+" + re.escape(text),
        r"\bat\s+" + re.escape(text),
        r"\bto\s+" + re.escape(text),
    ]
    for pattern in place_patterns:
        if re.search(pattern, context, re.IGNORECASE):
            return "PLACE"
    
    # Check for organization indicators
    org_suffixes = ["inc", "corp", "company", "ltd", "llc", "department"]
    for suffix in org_suffixes:
        if text_lower.endswith(suffix):
            return "ORG"
    
    # Default to PERSON for capitalized names
    return "PERSON"


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def _resolve_aliases(
    candidates: List[Tuple[str, str, str]]
) -> Dict[str, Dict]:
    """
    Resolve entity aliases and merge duplicates.
    
    Args:
        candidates: List of (entity_text, entity_type, context) tuples
        
    Returns:
        Dictionary mapping canonical name to entity info
    """
    entities = {}
    entity_id_counter = 1
    
    for entity_text, entity_type, context in candidates:
        entity_lower = entity_text.lower()
        
        # Check if this matches an existing entity
        matched = False
        for canonical, info in entities.items():
            canonical_lower = canonical.lower()
            
            # Exact match (case-insensitive)
            if entity_lower == canonical_lower:
                info["surface_forms"].add(entity_text)
                info["mentions"] += 1
                matched = True
                break
            
            # Nickname match
            if entity_lower in NICKNAME_MAP:
                if NICKNAME_MAP[entity_lower] == canonical_lower:
                    info["surface_forms"].add(entity_text)
                    info["aliases"].add(entity_text)
                    info["mentions"] += 1
                    matched = True
                    break
            
            if canonical_lower in NICKNAME_MAP:
                if NICKNAME_MAP[canonical_lower] == entity_lower:
                    # Update canonical to the longer form
                    if len(entity_text) > len(canonical):
                        entities[entity_text] = info
                        del entities[canonical]
                    info["surface_forms"].add(entity_text)
                    info["aliases"].add(entity_text)
                    info["mentions"] += 1
                    matched = True
                    break
            
            # Levenshtein distance for short names (typos, variations)
            if len(entity_text) <= 6 and entity_type == "PERSON":
                if _levenshtein_distance(entity_lower, canonical_lower) <= 1:
                    info["surface_forms"].add(entity_text)
                    info["mentions"] += 1
                    matched = True
                    break
            
            # Last name matching (for "John Smith" vs "Smith")
            words_entity = entity_text.split()
            words_canonical = canonical.split()
            if len(words_entity) > 1 and len(words_canonical) > 1:
                if words_entity[-1].lower() == words_canonical[-1].lower():
                    # Prefer the longer form
                    if len(entity_text) > len(canonical):
                        entities[entity_text] = info
                        del entities[canonical]
                    info["surface_forms"].add(entity_text)
                    info["mentions"] += 1
                    matched = True
                    break
        
        if not matched:
            # Create new entity
            entity_id = f"E{entity_id_counter}"
            entity_id_counter += 1
            entities[entity_text] = {
                "id": entity_id,
                "type": entity_type,
                "surface_forms": {entity_text},
                "aliases": set(),
                "mentions": 1,
            }
    
    return entities


def _extract_speaker_attribution(sentence: str, entities: Dict[str, Dict]) -> List[Tuple[str, str]]:
    """
    Extract speaker attribution from dialogue.
    
    Args:
        sentence: Sentence containing dialogue
        entities: Known entities
        
    Returns:
        List of (speaker, target) tuples
    """
    attributions = []
    
    # Patterns for speaker attribution
    # "...", said X
    # "...", X said
    # "...", X said to Y
    patterns = [
        r'"[^"]*",\s+(\w+)\s+said\s+to\s+(\w+)',
        r'"[^"]*",\s+said\s+(\w+)\s+to\s+(\w+)',
        r'"[^"]*",\s+(\w+)\s+said',
        r'"[^"]*",\s+said\s+(\w+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, sentence, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                if len(match) == 2:
                    speaker, target = match
                    attributions.append((speaker, target))
                else:
                    speaker = match
                    attributions.append((speaker, None))
            else:
                attributions.append((match, None))
    
    return attributions


def extract_entities(
    text: str,
    beats: List[Beat],
    min_mentions: int = 2,
    min_edge_weight: int = 2,
    run_id: str = "run_001",
    iteration: int = 0,
) -> Tuple[List[Entity], List[Edge], Dict[str, int | float]]:
    """
    Extract entities and relationships from text.
    
    Args:
        text: Input text
        beats: List of beat segments
        min_mentions: Minimum mentions to keep an entity
        min_edge_weight: Minimum edge weight to keep
        run_id: Run ID for logging
        iteration: Iteration number for logging
        
    Returns:
        Tuple of (entities, edges, stats)
    """
    # Preprocess: split into paragraphs and sentences
    paragraphs = _split_paragraphs(text)
    all_sentences = []
    sentence_to_para = {}
    sentence_to_beat = {}
    
    # Map sentences to paragraphs and beats
    token_offset = 0
    for para_idx, para in enumerate(paragraphs):
        sentences = _tokenize_sentences(para)
        for sent in sentences:
            all_sentences.append(sent)
            sentence_to_para[len(all_sentences) - 1] = para_idx
            
            # Determine beat for this sentence (simple heuristic based on position)
            # For now, just use token count as proxy
            words = sent.split()
            sent_end = token_offset + len(words)
            
            # Find which beat this sentence belongs to
            beat_id = "unknown"
            for beat in beats:
                if beat.span[0] <= token_offset < beat.span[1]:
                    beat_id = beat.id
                    break
            
            sentence_to_beat[len(all_sentences) - 1] = beat_id
            token_offset += len(words)
    
    # Step 1: Extract candidate entities
    candidates = []
    for sent_idx, sentence in enumerate(all_sentences):
        spans = _detect_capitalized_spans(sentence, is_sentence_start=(sent_idx == 0))
        for span in spans:
            entity_type = _classify_entity_type(span, sentence)
            candidates.append((span, entity_type, sentence))
    
    # Step 2: Resolve aliases
    entities_dict = _resolve_aliases(candidates)
    
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Digest",
        decision=f"Extracted {len(entities_dict)} candidate entities before filtering",
        reasoning="Used capitalized span detection and alias resolution",
        parameters={"candidates": len(candidates), "unique_entities": len(entities_dict)},
        metadata={"stage": "entity_extraction"},
    )
    
    # Step 3: Build entity lookup by surface forms
    surface_to_canonical = {}
    for canonical, info in entities_dict.items():
        for surface in info["surface_forms"]:
            surface_to_canonical[surface.lower()] = canonical
    
    # Step 4: Extract co-occurrence edges
    edge_dict = defaultdict(lambda: {
        "weight_sent": 0,
        "weight_para": 0,
        "beats": set(),
    })
    
    for sent_idx, sentence in enumerate(all_sentences):
        # Find entities in this sentence
        entities_in_sent = []
        for surface, canonical in surface_to_canonical.items():
            if surface in sentence.lower():
                entities_in_sent.append(canonical)
        
        # Remove duplicates
        entities_in_sent = list(set(entities_in_sent))
        
        # Create co-occurrence edges
        for i, e1 in enumerate(entities_in_sent):
            for e2 in entities_in_sent[i + 1:]:
                # Ensure consistent ordering (alphabetical)
                source, target = sorted([e1, e2])
                edge_key = (source, target, "co_occurs")
                edge_dict[edge_key]["weight_sent"] += 1
                edge_dict[edge_key]["beats"].add(sentence_to_beat[sent_idx])
    
    # Add paragraph-level co-occurrence
    for para_idx in range(len(paragraphs)):
        # Find all sentences in this paragraph
        sent_indices = [i for i, p in sentence_to_para.items() if p == para_idx]
        
        # Find all entities in these sentences
        entities_in_para = set()
        for sent_idx in sent_indices:
            sentence = all_sentences[sent_idx]
            for surface, canonical in surface_to_canonical.items():
                if surface in sentence.lower():
                    entities_in_para.add(canonical)
        
        # Add paragraph weight to edges
        entities_in_para = list(entities_in_para)
        for i, e1 in enumerate(entities_in_para):
            for e2 in entities_in_para[i + 1:]:
                source, target = sorted([e1, e2])
                edge_key = (source, target, "co_occurs")
                if edge_key in edge_dict:
                    edge_dict[edge_key]["weight_para"] += 1
    
    # Step 5: Extract speaker attribution edges (optional)
    for sent_idx, sentence in enumerate(all_sentences):
        attributions = _extract_speaker_attribution(sentence, entities_dict)
        for speaker, target in attributions:
            # Find canonical forms
            speaker_canonical = surface_to_canonical.get(speaker.lower())
            target_canonical = surface_to_canonical.get(target.lower()) if target else None
            
            if speaker_canonical and target_canonical:
                edge_key = (speaker_canonical, target_canonical, "speaks_to")
                edge_dict[edge_key]["weight_sent"] += 1
                edge_dict[edge_key]["beats"].add(sentence_to_beat[sent_idx])
    
    # Step 6: Filter by min_mentions and min_edge_weight
    filtered_entities = {
        canonical: info
        for canonical, info in entities_dict.items()
        if info["mentions"] >= min_mentions
    }
    
    filtered_edges = {
        edge_key: info
        for edge_key, info in edge_dict.items()
        if info["weight_sent"] >= min_edge_weight or edge_key[2] == "speaks_to"
    }
    
    # Step 7: Build Entity and Edge objects
    entities_list = [
        Entity(
            id=info["id"],
            canonical=canonical,
            type=info["type"],
            surface_forms=list(info["surface_forms"]),
            aliases=list(info["aliases"]),
            mentions=info["mentions"],
        )
        for canonical, info in filtered_entities.items()
    ]
    
    edges_list = [
        Edge(
            source=entities_dict[edge_key[0]]["id"],
            target=entities_dict[edge_key[1]]["id"],
            relation=edge_key[2],
            weight_sent=info["weight_sent"],
            weight_para=info["weight_para"],
            beats=list(info["beats"]),
        )
        for edge_key, info in filtered_edges.items()
        if edge_key[0] in filtered_entities and edge_key[1] in filtered_entities
    ]
    
    # Step 8: Compute stats
    num_entities = len(entities_list)
    num_edges = len(edges_list)
    
    # Calculate average degree
    if num_entities > 0:
        degree_sum = sum(
            sum(1 for e in edges_list if e.source == entity.id or e.target == entity.id)
            for entity in entities_list
        )
        avg_degree = degree_sum / num_entities
    else:
        avg_degree = 0.0
    
    # Calculate largest component (simplified: just count reachable from first entity)
    largest_component = num_entities  # Simplified for now
    
    stats = {
        "num_entities": num_entities,
        "num_edges": num_edges,
        "avg_degree": avg_degree,
        "largest_component": largest_component,
    }
    
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Digest",
        decision=f"entities={num_entities}, edges={num_edges}, avg_degree={avg_degree:.2f}",
        reasoning=f"Filtered to entities with ≥{min_mentions} mentions, edges with ≥{min_edge_weight} weight",
        parameters=stats,
        metadata={"stage": "entity_graph"},
    )
    
    return entities_list, edges_list, stats
