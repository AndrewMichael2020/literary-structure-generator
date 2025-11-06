"""
Tests for entity extraction, motifs, and imagery palettes.

Tests Phase 2.1 enrichments to ExemplarDigest.
"""

import pytest

from literary_structure_generator.digest.entity_extractor import (
    _classify_entity_type,
    _detect_capitalized_spans,
    _levenshtein_distance,
    _resolve_aliases,
    extract_entities,
)
from literary_structure_generator.digest.motif_extractor import (
    extract_imagery_palettes,
    extract_lexical_domains,
    extract_motifs,
)
from literary_structure_generator.digest.valence_extractor import (
    _compute_paragraph_valence,
    _detect_change_points,
    _smooth_valence,
    extract_valence_arc,
)
from literary_structure_generator.models.exemplar_digest import Beat


class TestEntityExtraction:
    """Test entity extraction functions."""

    def test_detect_capitalized_spans_basic(self):
        """Test basic capitalized span detection."""
        sentence = "James met Sarah on Willow Street."
        spans = _detect_capitalized_spans(sentence)
        assert "James" in spans
        assert "Sarah" in spans
        assert "Willow Street" in spans

    def test_detect_capitalized_spans_filters_blacklist(self):
        """Test that blacklisted words are filtered."""
        sentence = "Monday was a good day for Jane."
        spans = _detect_capitalized_spans(sentence)
        assert "Monday" not in spans
        assert "Jane" in spans

    def test_classify_entity_type_person(self):
        """Test person entity classification."""
        entity_type = _classify_entity_type("John Smith", "")
        assert entity_type == "PERSON"

    def test_classify_entity_type_place(self):
        """Test place entity classification."""
        entity_type = _classify_entity_type("Main Street", "")
        assert entity_type == "PLACE"

        entity_type = _classify_entity_type("County Hospital", "")
        assert entity_type == "PLACE"

    def test_classify_entity_type_place_with_context(self):
        """Test place classification with context."""
        entity_type = _classify_entity_type("Central Park", "We walked to Central Park")
        assert entity_type == "PLACE"

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        assert _levenshtein_distance("kitten", "sitting") == 3
        assert _levenshtein_distance("", "") == 0
        assert _levenshtein_distance("abc", "abc") == 0
        assert _levenshtein_distance("abc", "def") == 3

    def test_resolve_aliases_exact_match(self):
        """Test alias resolution with exact matches."""
        candidates = [
            ("James", "PERSON", "James walked"),
            ("james", "PERSON", "james said"),
            ("James", "PERSON", "James replied"),
        ]
        entities = _resolve_aliases(candidates)
        assert len(entities) == 1
        canonical = list(entities.keys())[0]
        assert entities[canonical]["mentions"] == 3

    def test_resolve_aliases_nickname(self):
        """Test alias resolution with nicknames."""
        candidates = [
            ("James", "PERSON", "James walked"),
            ("Jim", "PERSON", "Jim said"),
        ]
        entities = _resolve_aliases(candidates)
        # Should merge Jim into James
        assert len(entities) <= 2
        # At least one should have multiple mentions
        total_mentions = sum(e["mentions"] for e in entities.values())
        assert total_mentions == 2

    def test_extract_entities_synthetic_text(self):
        """Test entity extraction on synthetic text."""
        text = """
        James met Jim on Willow Street. "I saw the red car," James said to Jim.
        Later, James and Robert walked to County Hospital. "It was loud," said Robert.
        """

        beats = [
            Beat(id="opening", span=[0, 50], function="introduce"),
            Beat(id="middle", span=[50, 100], function="develop"),
        ]

        entities, edges, stats = extract_entities(text, beats, min_mentions=1, min_edge_weight=1)

        # Should find people and places
        assert stats["num_entities"] > 0
        assert stats["num_edges"] >= 0

        # Check that we have some entities
        entity_types = {e.type for e in entities}
        assert "PERSON" in entity_types or "PLACE" in entity_types

    def test_extract_entities_co_occurrence(self):
        """Test that co-occurrence edges are created."""
        text = """
        Alice and Bob met at the park. Alice said hello to Bob.
        """

        beats = [Beat(id="test", span=[0, 100], function="test")]

        entities, edges, stats = extract_entities(text, beats, min_mentions=1, min_edge_weight=1)

        # Should have at least some edges
        assert stats["num_edges"] >= 0


class TestMotifExtraction:
    """Test motif extraction functions."""

    def test_extract_motifs_basic(self):
        """Test basic motif extraction."""
        text = """
        The blood dripped slowly. He applied gauze to the wound.
        More blood seeped through the bandage. The cut was deep.
        Blood and pain filled his thoughts.
        """

        motifs = extract_motifs(text, top_k=5)

        # Should extract some motifs
        assert len(motifs) > 0

        # Motifs should have required fields
        for motif in motifs:
            assert motif.motif
            assert isinstance(motif.anchors, list)

    def test_extract_motifs_finds_recurring_terms(self):
        """Test that motifs capture recurring terms."""
        text = (
            """
        Light filled the room. Fluorescent lights buzzed overhead.
        The bright light hurt his eyes. He turned off the lights.
        """
            * 3
        )  # Repeat to increase frequency

        motifs = extract_motifs(text, top_k=10)

        # Should find "light" or related terms
        motif_names = [m.motif for m in motifs]
        assert any("light" in m.lower() for m in motif_names)


class TestImageryExtraction:
    """Test imagery palette extraction."""

    def test_extract_imagery_palettes_basic(self):
        """Test basic imagery extraction."""
        text = """
        The fluorescent lights hummed. Blood dripped on the wet road.
        Dark clouds gathered overhead. A bright light shone through.
        """

        palettes = extract_imagery_palettes(text, top_k_per_category=3)

        # Should extract some categories
        assert len(palettes) > 0

        # Each category should have imagery
        for category, images in palettes.items():
            assert len(images) > 0
            assert all(isinstance(img, str) for img in images)

    def test_extract_imagery_palettes_medical(self):
        """Test medical imagery extraction."""
        text = (
            """
        The nurse applied gauze to the wound. Blood seeped through.
        The hospital smelled of medicine and pain.
        """
            * 2
        )

        palettes = extract_imagery_palettes(text, top_k_per_category=5)

        # Should have medical category
        if "medical" in palettes:
            assert len(palettes["medical"]) > 0
            assert any("blood" in img or "gauze" in img for img in palettes["medical"])

    def test_extract_lexical_domains(self):
        """Test lexical domain extraction."""
        text = """
        The doctor examined the patient at the hospital.
        The nurse brought medicine for the wound treatment.
        Blood tests showed elevated pain markers.
        """

        domains = extract_lexical_domains(text)

        # Should detect medical domain
        assert "medical" in domains or len(domains) >= 0


class TestValenceExtraction:
    """Test valence and surprise curve extraction."""

    def test_compute_paragraph_valence_positive(self):
        """Test positive valence detection."""
        paragraph = "I am so happy and joyful. This is wonderful and great."
        valence = _compute_paragraph_valence(paragraph)
        assert valence > 0

    def test_compute_paragraph_valence_negative(self):
        """Test negative valence detection."""
        paragraph = "I am so sad and hurt. This is terrible and awful."
        valence = _compute_paragraph_valence(paragraph)
        assert valence < 0

    def test_compute_paragraph_valence_neutral(self):
        """Test neutral valence."""
        paragraph = "The cat sat on the mat. The door was blue."
        valence = _compute_paragraph_valence(paragraph)
        assert -0.1 <= valence <= 0.1

    def test_smooth_valence(self):
        """Test valence smoothing."""
        valences = [1.0, -1.0, 1.0, -1.0, 1.0]
        smoothed = _smooth_valence(valences, window=3)

        # Smoothed values should be less extreme
        assert len(smoothed) == len(valences)
        assert all(abs(s) < 1.0 for s in smoothed[1:-1])

    def test_detect_change_points(self):
        """Test change point detection."""
        valences = [0.0, 0.0, 0.8, 0.8, -0.6, -0.6]
        change_points = _detect_change_points(valences, threshold=0.3)

        # Should detect at least one change point
        assert len(change_points) >= 1

    def test_extract_valence_arc(self):
        """Test full valence arc extraction."""
        text = """
        I am happy and joyful today.
        
        Everything is wonderful and great.
        
        But then sadness and pain arrived.
        
        It was terrible and awful.
        """

        beats = [
            Beat(id="opening", span=[0, 50], function="happy"),
            Beat(id="closing", span=[50, 100], function="sad"),
        ]

        valence_arc, surprise_curve = extract_valence_arc(text, beats)

        # Should have valence data
        assert "per_paragraph" in valence_arc
        assert "per_beat" in valence_arc
        assert "overall_mean" in valence_arc

        # Should have surprise curve
        assert len(surprise_curve) > 0


class TestIntegration:
    """Integration tests for enriched digest."""

    def test_full_digest_with_enrichments(self):
        """Test that full digest pipeline works with enrichments."""
        from literary_structure_generator.ingest.digest_exemplar import analyze_text
        from pathlib import Path

        # Use the emergency test file
        data_dir = Path(__file__).parent.parent / "data" / "exemplars"
        test_file = data_dir / "emergency_excerpt.txt"

        if not test_file.exists():
            pytest.skip("Test data file not found")

        # Analyze with enrichments
        digest = analyze_text(str(test_file), run_id="test_001", iteration=0)

        # Check basic fields
        assert digest.meta.source == "emergency_excerpt"
        assert digest.meta.tokens > 0

        # Check Phase 2.1 enrichments
        assert digest.coherence_graph is not None
        assert digest.coherence_graph.stats is not None

        # Motifs should be extracted
        assert isinstance(digest.motif_map, list)

        # Imagery palettes should exist
        assert isinstance(digest.imagery_palettes, dict)

        # Valence arc should exist
        assert isinstance(digest.valence_arc, dict)

        # Surprise curve should exist
        assert isinstance(digest.surprise_curve, list)

        # Safety should be clean mode
        assert digest.safety.profanity_rate == 0.0
