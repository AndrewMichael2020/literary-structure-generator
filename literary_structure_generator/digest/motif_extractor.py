"""
Motif Extractor module

Heuristic-based extraction of recurring motifs, themes, and imagery.

Extracts:
    - Recurring motifs and themes using TF-IDF and PMI
    - Imagery palettes (concrete nouns and adjective-noun pairs)
    - Lexical domains
"""

import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from literary_structure_generator.models.exemplar_digest import Motif
from literary_structure_generator.utils.decision_logger import log_decision


# Content words: exclude common stop words
STOP_WORDS = {
    "the", "and", "but", "or", "as", "if", "when", "where", "while",
    "a", "an", "of", "in", "on", "at", "to", "for", "with", "from",
    "by", "about", "through", "over", "under", "into", "onto",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "is", "was", "are", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "can", "must", "shall", "this", "that", "these", "those", "which", "who",
    "what", "said", "like", "just", "now", "so", "then", "there", "their",
}

# Concrete nouns - common imagery categories
CONCRETE_CATEGORIES = {
    "medical": ["blood", "gauze", "wound", "bandage", "cut", "hospital", "doctor", "nurse", "medicine"],
    "light": ["light", "lights", "fluorescent", "glow", "shine", "bright", "dark", "shadow"],
    "road": ["road", "street", "highway", "pavement", "asphalt", "car", "vehicle"],
    "weather": ["rain", "snow", "wind", "cloud", "sun", "storm", "fog"],
    "nature": ["tree", "leaf", "grass", "flower", "sky", "water", "river", "ocean"],
}


def _tokenize_words(text: str) -> List[str]:
    """Tokenize text into words."""
    return re.findall(r"\b[\w']+\b", text.lower())


def _tokenize_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r"[.!?]+(?:\s+|$)", text)
    return [s.strip() for s in sentences if s.strip()]


def _extract_ngrams(words: List[str], n: int) -> List[str]:
    """Extract n-grams from words."""
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def _compute_tf_idf(
    ngrams: List[str],
    sentences: List[List[str]],
) -> Dict[str, float]:
    """
    Compute TF-IDF scores for n-grams.
    
    Args:
        ngrams: List of n-grams to score
        sentences: List of tokenized sentences
        
    Returns:
        Dictionary mapping n-grams to TF-IDF scores
    """
    # Count total occurrences (TF)
    ngram_counts = Counter(ngrams)
    total_ngrams = len(ngrams)
    
    # Count document frequency (DF)
    doc_freq = defaultdict(int)
    for sent_words in sentences:
        # Extract n-grams from this sentence
        sent_ngrams = set()
        for n in range(1, 5):  # 1-4 grams
            sent_ngrams.update(_extract_ngrams(sent_words, n))
        
        for ng in sent_ngrams:
            if ng in ngram_counts:
                doc_freq[ng] += 1
    
    # Compute TF-IDF
    num_docs = len(sentences)
    tf_idf = {}
    for ng, count in ngram_counts.items():
        tf = count / total_ngrams
        idf = math.log(num_docs / (1 + doc_freq[ng]))
        tf_idf[ng] = tf * idf
    
    return tf_idf


def _compute_pmi(
    ngrams: List[str],
    word_counts: Counter,
    total_words: int,
) -> Dict[str, float]:
    """
    Compute Pointwise Mutual Information for multi-word n-grams.
    
    Args:
        ngrams: List of n-grams
        word_counts: Counter of individual word frequencies
        total_words: Total word count
        
    Returns:
        Dictionary mapping n-grams to PMI scores
    """
    ngram_counts = Counter(ngrams)
    pmi_scores = {}
    
    for ng, count in ngram_counts.items():
        words = ng.split()
        if len(words) < 2:
            # PMI only meaningful for multi-word phrases
            pmi_scores[ng] = 0.0
            continue
        
        # P(w1, w2, ..., wn)
        p_ngram = count / total_words
        
        # P(w1) * P(w2) * ... * P(wn)
        p_independent = 1.0
        for word in words:
            p_word = word_counts[word] / total_words
            p_independent *= p_word
        
        # PMI = log(P(w1, w2, ...) / (P(w1) * P(w2) * ...))
        if p_independent > 0:
            pmi = math.log(p_ngram / p_independent)
        else:
            pmi = 0.0
        
        pmi_scores[ng] = pmi
    
    return pmi_scores


def _cluster_into_motifs(
    top_ngrams: List[Tuple[str, float]],
    max_motifs: int = 10,
) -> List[str]:
    """
    Cluster related n-grams into motifs.
    
    Simple heuristic: group n-grams that share words.
    
    Args:
        top_ngrams: List of (ngram, score) tuples
        max_motifs: Maximum number of motifs to return
        
    Returns:
        List of motif names (just the top ngram from each cluster)
    """
    # For now, just return the top n-grams as motif names
    # In a more sophisticated implementation, we'd cluster by semantic similarity
    motifs = []
    seen_words = set()
    
    for ngram, score in top_ngrams:
        words = set(ngram.split())
        
        # Check if this overlaps significantly with existing motifs
        if len(words & seen_words) < len(words) / 2:
            motifs.append(ngram)
            seen_words.update(words)
        
        if len(motifs) >= max_motifs:
            break
    
    return motifs


def extract_motifs(
    text: str,
    run_id: str = "run_001",
    iteration: int = 0,
    top_k: int = 20,
) -> List[Motif]:
    """
    Extract recurring motifs using TF-IDF and PMI.
    
    Args:
        text: Input text to analyze
        run_id: Run ID for logging
        iteration: Iteration number for logging
        top_k: Number of top motifs to extract
        
    Returns:
        List of Motif objects with motif names, anchors, and co-occurrences
    """
    # Tokenize
    words = _tokenize_words(text)
    sentences = [_tokenize_words(s) for s in _tokenize_sentences(text)]
    
    # Filter stop words for content analysis
    content_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    
    # Extract n-grams (1-4)
    all_ngrams = []
    for n in range(1, 5):
        all_ngrams.extend(_extract_ngrams(content_words, n))
    
    # Compute TF-IDF
    tf_idf_scores = _compute_tf_idf(all_ngrams, sentences)
    
    # Compute PMI for multi-word phrases
    word_counts = Counter(content_words)
    pmi_scores = _compute_pmi(all_ngrams, word_counts, len(content_words))
    
    # Combine scores (weighted average)
    combined_scores = {}
    for ng in all_ngrams:
        tf_idf = tf_idf_scores.get(ng, 0.0)
        pmi = pmi_scores.get(ng, 0.0)
        combined_scores[ng] = 0.7 * tf_idf + 0.3 * pmi
    
    # Get top scoring n-grams
    top_ngrams = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k * 2]
    
    # Filter to multi-word phrases and single important words
    filtered_ngrams = [
        (ng, score) for ng, score in top_ngrams
        if len(ng.split()) > 1 or word_counts[ng] >= 3
    ][:top_k]
    
    # Cluster into motifs
    motif_names = _cluster_into_motifs(filtered_ngrams, max_motifs=10)
    
    # Find anchors (positions) for each motif
    motif_objects = []
    token_offset = 0
    
    for motif_name in motif_names:
        anchors = []
        motif_words = motif_name.split()
        
        # Find positions where this motif appears
        for i in range(len(words) - len(motif_words) + 1):
            if words[i:i + len(motif_words)] == motif_words:
                anchors.append(i)
        
        motif_objects.append(
            Motif(
                motif=motif_name,
                anchors=anchors[:10],  # Limit to first 10 occurrences
                co_occurs_with=[],  # Could compute co-occurrence later
            )
        )
    
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Digest",
        decision=f"Extracted {len(motif_objects)} motifs: {[m.motif for m in motif_objects[:3]]}",
        reasoning="Used TF-IDF + PMI ranking, clustered by word overlap",
        parameters={"top_k": top_k, "num_motifs": len(motif_objects)},
        metadata={"stage": "motif_extraction"},
    )
    
    return motif_objects


def extract_imagery_palettes(
    text: str,
    run_id: str = "run_001",
    iteration: int = 0,
    top_k_per_category: int = 5,
) -> Dict[str, List[str]]:
    """
    Extract imagery palettes organized by category.
    
    Collects frequent concrete nouns and adjective-noun pairs.
    
    Args:
        text: Input text to analyze
        run_id: Run ID for logging
        iteration: Iteration number for logging
        top_k_per_category: Number of top images per category
        
    Returns:
        Dictionary mapping categories to imagery lists
    """
    # Tokenize into sentences
    sentences = _tokenize_sentences(text)
    
    # Extract adjective-noun pairs (simple heuristic: adj followed by noun)
    # Pattern: one or more adjectives followed by a noun
    adj_noun_pattern = r'\b([a-z]+(?:ly)?)\s+([a-z]+)\b'
    
    imagery_palettes = {}
    
    # Categorize concrete nouns
    for category, keywords in CONCRETE_CATEGORIES.items():
        category_imagery = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Find category keywords
            for keyword in keywords:
                if keyword in sentence_lower:
                    # Look for adjective-noun pairs with this keyword
                    adj_noun_matches = re.findall(
                        r'\b([a-z]+(?:ly)?)\s+' + re.escape(keyword) + r'\b',
                        sentence_lower
                    )
                    for adj in adj_noun_matches:
                        if adj not in STOP_WORDS:
                            category_imagery.append(f"{adj} {keyword}")
                    
                    # Also add the bare noun
                    category_imagery.append(keyword)
        
        # Count and get top K
        imagery_counts = Counter(category_imagery)
        top_imagery = [img for img, count in imagery_counts.most_common(top_k_per_category)]
        
        if top_imagery:
            imagery_palettes[category] = top_imagery
    
    # Also extract general adjective-noun pairs that are frequent
    all_adj_noun = []
    for sentence in sentences:
        matches = re.findall(adj_noun_pattern, sentence.lower())
        for adj, noun in matches:
            if adj not in STOP_WORDS and noun not in STOP_WORDS and len(noun) > 3:
                all_adj_noun.append(f"{adj} {noun}")
    
    top_general = [img for img, count in Counter(all_adj_noun).most_common(top_k_per_category * 2)]
    if top_general:
        imagery_palettes["general"] = top_general[:top_k_per_category]
    
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Digest",
        decision=f"Extracted imagery palettes: {list(imagery_palettes.keys())}",
        reasoning="Identified concrete nouns and adjective-noun pairs by category",
        parameters={"categories": len(imagery_palettes), "top_k_per_category": top_k_per_category},
        metadata={"stage": "imagery_extraction", "palettes": {k: v[:2] for k, v in imagery_palettes.items()}},
    )
    
    return imagery_palettes


def extract_lexical_domains(text: str) -> Dict[str, List[str]]:
    """
    Extract lexical domains (medical, working-class, etc.).
    
    Args:
        text: Input text to analyze
        
    Returns:
        Dictionary mapping domains to word lists
    """
    # Simple implementation: categorize based on keyword presence
    words = _tokenize_words(text)
    word_counts = Counter(words)
    
    domains = {}
    
    # Medical domain
    medical_keywords = ["blood", "hospital", "doctor", "nurse", "patient", "medicine", "treatment", "wound", "pain"]
    medical_words = [w for w in word_counts if w in medical_keywords]
    if medical_words:
        domains["medical"] = medical_words
    
    # Working-class domain
    working_class_keywords = ["work", "job", "shift", "factory", "wage", "labor", "tired", "boss"]
    working_class_words = [w for w in word_counts if w in working_class_keywords]
    if working_class_words:
        domains["working_class"] = working_class_words
    
    return domains
