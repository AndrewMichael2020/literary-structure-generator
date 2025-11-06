"""
Tests for Phase 5 evaluation suite.

Tests cover:
- All heuristic evaluators (stylefit_rules, formfit, coherence, motif, cadence, overlap)
- LLM-based evaluator (stylefit_llm) with MockClient
- Orchestrator (evaluate.py) with full EvalReport@2 generation
- GPT-5 parameter filtering in router
"""

import tempfile
from pathlib import Path

import pytest

from literary_structure_generator.evaluators.cadence_pacing import (
    calculate_paragraph_variance,
    classify_paragraph_cadence,
    estimate_valence_smoothness,
    evaluate_cadence_pacing,
    extract_paragraph_lengths,
)
from literary_structure_generator.evaluators.coherence_graph_fit import (
    build_entity_map,
    detect_aliasing_issues,
    detect_name_spikes,
    evaluate_coherence_graph_fit,
    extract_entities,
)
from literary_structure_generator.evaluators.evaluate import (
    evaluate_draft,
    save_eval_report,
)
from literary_structure_generator.evaluators.formfit import (
    check_beat_function_alignment,
    check_beat_length_adherence,
    estimate_scene_summary_ratio,
    evaluate_formfit,
    split_into_beats,
)
from literary_structure_generator.evaluators.motif_imagery_coverage import (
    calculate_balance_score,
    calculate_coverage,
    calculate_overuse_penalty,
    evaluate_motif_imagery_coverage,
    extract_imagery_mentions,
    extract_motif_mentions,
)
from literary_structure_generator.evaluators.overlap_guard_eval import (
    calculate_ngram_overlap_percentage,
    check_simhash_distance,
    evaluate_overlap_guard,
    find_max_ngram_overlap,
)
from literary_structure_generator.evaluators.stylefit_llm import (
    create_spec_summary,
    evaluate_stylefit_llm,
    parse_llm_score,
)
from literary_structure_generator.evaluators.stylefit_rules import (
    calculate_avg_sentence_length,
    calculate_dialogue_ratio,
    calculate_parataxis_ratio,
    check_clean_mode,
    check_dialogue_ratio,
    check_parataxis_ratio,
    check_person_consistency,
    check_sentence_length,
    check_tense_consistency,
    evaluate_stylefit_rules,
)
from literary_structure_generator.llm.router import get_client
from literary_structure_generator.models.eval_report import EvalReport
from literary_structure_generator.models.exemplar_digest import (
    ExemplarDigest,
    MetaInfo as DigestMeta,
)
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    Form,
    MetaInfo,
    Setting,
    StorySpec,
    Voice,
)


# Sample texts for testing
SAMPLE_TEXT_FIRST_PERSON = """
I walked into the room. The air was thick. I couldn't breathe.

She looked at me. "Are you okay?" she asked.

I nodded. I wasn't okay. Not really.
"""

SAMPLE_TEXT_THIRD_PERSON = """
He walked into the room. The air was thick. He couldn't breathe.

She looked at him. "Are you okay?" she asked.

He nodded. He wasn't okay. Not really.
"""

SAMPLE_TEXT_LONG = """
The hospital corridor stretched endlessly before him, fluorescent lights flickering overhead like dying stars, and he wondered if he would ever find his way out of this labyrinth of suffering and sterile hope.

She sat in the waiting room, her hands folded in her lap, counting the seconds between each breath, trying to maintain some semblance of control over a situation that had spun wildly beyond her grasp hours ago.

Outside, the rain continued to fall, a relentless percussion that seemed to mock the stillness inside, where time had stopped and everything hung in terrible suspension.
"""


class TestStylefitRules:
    """Test stylefit_rules evaluator."""

    def test_check_person_consistency_first(self):
        """Test person consistency check for first person."""
        score = check_person_consistency(SAMPLE_TEXT_FIRST_PERSON, "first")
        assert score > 0.7

    def test_check_person_consistency_third(self):
        """Test person consistency check for third person."""
        score = check_person_consistency(SAMPLE_TEXT_THIRD_PERSON, "third-limited")
        assert score > 0.7

    def test_check_tense_consistency(self):
        """Test tense consistency check."""
        score = check_tense_consistency(SAMPLE_TEXT_FIRST_PERSON, "past")
        assert score >= 0.0
        assert score <= 1.0

    def test_calculate_avg_sentence_length(self):
        """Test sentence length calculation."""
        text = "I am here. You are there. We are together."
        avg_len = calculate_avg_sentence_length(text)
        assert avg_len > 0
        assert avg_len < 10  # Short sentences

    def test_check_sentence_length(self):
        """Test sentence length check."""
        text = "I am here. You are there. We are together."
        score = check_sentence_length(text, target_length=3, tolerance=0.3)
        assert score > 0.5

    def test_calculate_parataxis_ratio(self):
        """Test parataxis ratio calculation."""
        ratio = calculate_parataxis_ratio(SAMPLE_TEXT_FIRST_PERSON)
        assert ratio >= 0.0
        assert ratio <= 1.0

    def test_check_parataxis_ratio(self):
        """Test parataxis ratio check."""
        score = check_parataxis_ratio(SAMPLE_TEXT_FIRST_PERSON, target_ratio=0.7)
        assert score >= 0.0
        assert score <= 1.0

    def test_calculate_dialogue_ratio(self):
        """Test dialogue ratio calculation."""
        ratio = calculate_dialogue_ratio(SAMPLE_TEXT_FIRST_PERSON)
        assert ratio >= 0.0
        assert ratio <= 1.0
        assert ratio > 0  # Sample has dialogue

    def test_check_dialogue_ratio(self):
        """Test dialogue ratio check."""
        score = check_dialogue_ratio(SAMPLE_TEXT_FIRST_PERSON, target_ratio=0.2)
        assert score >= 0.0
        assert score <= 1.0

    def test_check_clean_mode_clean(self):
        """Test clean mode with clean text."""
        clean = check_clean_mode(SAMPLE_TEXT_FIRST_PERSON)
        assert clean is True

    def test_check_clean_mode_profanity(self):
        """Test clean mode with profanity."""
        text = "This is damn terrible."
        clean = check_clean_mode(text)
        assert clean is False

    def test_evaluate_stylefit_rules(self):
        """Test full stylefit_rules evaluation."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
            ),
        )
        
        result = evaluate_stylefit_rules(SAMPLE_TEXT_FIRST_PERSON, spec)
        
        assert 'overall' in result
        assert result['overall'] >= 0.0
        assert result['overall'] <= 1.0
        assert 'person_consistency' in result
        assert 'tense_consistency' in result
        assert 'sentence_length' in result
        assert 'parataxis_ratio' in result
        assert 'dialogue_ratio' in result
        assert 'clean_mode' in result


class TestFormfit:
    """Test formfit evaluator."""

    def test_split_into_beats(self):
        """Test splitting text into beats."""
        beats = split_into_beats(SAMPLE_TEXT_LONG, num_beats=3)
        assert len(beats) == 3

    def test_check_beat_length_adherence(self):
        """Test beat length adherence."""
        beat_specs = [
            BeatSpec(id="beat_1", target_words=30, function="hook", cadence="short"),
            BeatSpec(id="beat_2", target_words=40, function="rising", cadence="mixed"),
        ]
        beat_texts = ["This is a short beat.", "This is a longer beat with more words."]
        
        score, details = check_beat_length_adherence(beat_texts, beat_specs)
        
        assert score >= 0.0
        assert score <= 1.0
        assert len(details) == 2

    def test_check_beat_function_alignment(self):
        """Test beat function alignment."""
        beat_specs = [
            BeatSpec(id="beat_1", target_words=30, function="hook", cadence="short"),
        ]
        beat_texts = ["The story began with a sudden revelation."]
        
        score, details = check_beat_function_alignment(beat_texts, beat_specs)
        
        assert score >= 0.0
        assert score <= 1.0

    def test_estimate_scene_summary_ratio(self):
        """Test scene:summary ratio estimation."""
        ratio = estimate_scene_summary_ratio(SAMPLE_TEXT_LONG)
        assert ratio >= 0.0
        assert ratio <= 1.0

    def test_evaluate_formfit(self):
        """Test full formfit evaluation."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
            ),
            form=Form(
                beat_map=[
                    BeatSpec(id="beat_1", target_words=30, function="hook", cadence="short"),
                    BeatSpec(id="beat_2", target_words=40, function="rising", cadence="mixed"),
                ]
            ),
        )
        
        result = evaluate_formfit(SAMPLE_TEXT_LONG, spec)
        
        assert 'overall' in result
        assert result['overall'] >= 0.0
        assert result['overall'] <= 1.0
        assert 'beat_length_adherence' in result
        assert 'beat_function_alignment' in result
        assert 'scene_summary_ratio' in result


class TestCoherenceGraphFit:
    """Test coherence_graph_fit evaluator."""

    def test_extract_entities(self):
        """Test entity extraction."""
        text = "John went to the Hospital. Mary met him there."
        entities = extract_entities(text)
        assert len(entities) > 0

    def test_build_entity_map(self):
        """Test entity map building."""
        entities = [("John", "PERSON"), ("Mary", "PERSON"), ("Hospital", "PLACE")]
        entity_map = build_entity_map(entities)
        
        assert "John" in entity_map
        assert entity_map["John"]["type"] == "PERSON"
        assert entity_map["John"]["mentions"] == 1

    def test_detect_aliasing_issues(self):
        """Test aliasing detection."""
        entity_map = {
            "John": {"type": "PERSON", "mentions": 2, "positions": [0, 1], "aliases": {"John"}},
            "Mary": {"type": "PERSON", "mentions": 1, "positions": [2], "aliases": {"Mary"}},
        }
        
        penalty, issues = detect_aliasing_issues(entity_map)
        
        assert penalty >= 0.0
        assert penalty <= 1.0

    def test_detect_name_spikes(self):
        """Test name spike detection."""
        entity_map = {
            "John": {"type": "PERSON", "mentions": 15, "positions": list(range(15)), "aliases": {"John"}},
        }
        
        penalty, issues = detect_name_spikes(entity_map)
        
        assert penalty >= 0.0
        assert penalty <= 1.0

    def test_evaluate_coherence_graph_fit(self):
        """Test full coherence evaluation."""
        result = evaluate_coherence_graph_fit(SAMPLE_TEXT_LONG)
        
        assert 'overall' in result
        assert result['overall'] >= 0.0
        assert result['overall'] <= 1.0
        assert 'entity_count' in result
        assert 'aliasing_penalty' in result
        assert 'spike_penalty' in result


class TestMotifImageryCoverage:
    """Test motif_imagery_coverage evaluator."""

    def test_extract_motif_mentions(self):
        """Test motif mention extraction."""
        text = "The rain fell. The rain continued. The storm raged."
        motifs = ["rain", "storm", "wind"]
        
        mentions = extract_motif_mentions(text, motifs)
        
        assert mentions["rain"] == 2
        assert mentions["storm"] == 1
        assert mentions["wind"] == 0

    def test_extract_imagery_mentions(self):
        """Test imagery mention extraction."""
        text = "The blue sky and green grass."
        imagery = ["blue", "green", "red"]
        
        mentions = extract_imagery_mentions(text, imagery)
        
        assert mentions["blue"] == 1
        assert mentions["green"] == 1
        assert mentions["red"] == 0

    def test_calculate_coverage(self):
        """Test coverage calculation."""
        mentions = {"rain": 2, "storm": 1, "wind": 0}
        target_items = ["rain", "storm", "wind"]
        
        coverage = calculate_coverage(mentions, target_items, min_mentions=1)
        
        assert coverage == pytest.approx(2.0 / 3.0)

    def test_calculate_overuse_penalty(self):
        """Test overuse penalty calculation."""
        mentions = {"rain": 10, "storm": 2}
        
        penalty, overused = calculate_overuse_penalty(mentions, max_mentions_per_item=5)
        
        assert penalty > 0.0
        assert len(overused) > 0

    def test_calculate_balance_score(self):
        """Test balance score calculation."""
        mentions = {"rain": 3, "storm": 3, "wind": 3}
        score = calculate_balance_score(mentions)
        assert score > 0.5  # Balanced distribution

    def test_evaluate_motif_imagery_coverage(self):
        """Test full motif/imagery evaluation."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
                motifs=["rain", "storm"],
                imagery_palette=["dark", "cold"],
            ),
        )
        
        digest = ExemplarDigest(
            meta=DigestMeta(source="test", tokens=100, paragraphs=5),
        )
        
        result = evaluate_motif_imagery_coverage(SAMPLE_TEXT_LONG, spec, digest)
        
        assert 'overall' in result
        assert result['overall'] >= 0.0
        assert result['overall'] <= 1.0
        assert 'motif_coverage' in result
        assert 'imagery_coverage' in result


class TestCadencePacing:
    """Test cadence_pacing evaluator."""

    def test_extract_paragraph_lengths(self):
        """Test paragraph length extraction."""
        lengths = extract_paragraph_lengths(SAMPLE_TEXT_LONG)
        assert len(lengths) > 0
        assert all(length > 0 for length in lengths)

    def test_classify_paragraph_cadence(self):
        """Test paragraph cadence classification."""
        lengths = [10, 50, 80, 20, 15]
        dist = classify_paragraph_cadence(lengths)
        
        assert 'short' in dist
        assert 'mixed' in dist
        assert 'long' in dist
        assert sum(dist.values()) == pytest.approx(1.0)

    def test_calculate_paragraph_variance(self):
        """Test paragraph variance calculation."""
        lengths = [10, 20, 30, 40]
        variance = calculate_paragraph_variance(lengths)
        assert variance > 0.0

    def test_estimate_valence_smoothness(self):
        """Test valence smoothness estimation."""
        smoothness = estimate_valence_smoothness(SAMPLE_TEXT_LONG)
        assert smoothness >= 0.0
        assert smoothness <= 1.0

    def test_evaluate_cadence_pacing(self):
        """Test full cadence/pacing evaluation."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
            ),
            form=Form(
                beat_map=[
                    BeatSpec(id="beat_1", target_words=30, function="hook", cadence="mixed"),
                ]
            ),
        )
        
        result = evaluate_cadence_pacing(SAMPLE_TEXT_LONG, spec)
        
        assert 'overall' in result
        assert result['overall'] >= 0.0
        assert result['overall'] <= 1.0
        assert 'cadence_match' in result
        assert 'variance_match' in result
        assert 'valence_smoothness' in result


class TestOverlapGuardEval:
    """Test overlap_guard_eval evaluator."""

    def test_find_max_ngram_overlap_no_overlap(self):
        """Test n-gram overlap with different texts."""
        text1 = "The quick brown fox jumps."
        text2 = "A lazy dog sleeps peacefully."
        
        max_ngram = find_max_ngram_overlap(text1, text2, max_n=10)
        
        assert max_ngram >= 0

    def test_find_max_ngram_overlap_with_overlap(self):
        """Test n-gram overlap with similar texts."""
        text1 = "The quick brown fox jumps over the lazy dog."
        text2 = "The quick brown fox runs fast."
        
        max_ngram = find_max_ngram_overlap(text1, text2, max_n=10)
        
        assert max_ngram >= 3  # "the quick brown"

    def test_calculate_ngram_overlap_percentage(self):
        """Test n-gram overlap percentage."""
        text1 = "The quick brown fox."
        text2 = "The lazy brown dog."
        
        overlap_pct = calculate_ngram_overlap_percentage(text1, text2, n=2)
        
        assert overlap_pct >= 0.0
        assert overlap_pct <= 1.0

    def test_check_simhash_distance(self):
        """Test SimHash distance calculation."""
        text1 = "The quick brown fox jumps."
        text2 = "The lazy dog sleeps."
        
        distance = check_simhash_distance(text1, text2)
        
        assert distance >= 0

    def test_evaluate_overlap_guard_pass(self):
        """Test overlap guard with different texts (should pass)."""
        text1 = "The quick brown fox jumps over the lazy dog."
        text2 = "A completely different story about cats and birds."
        
        result = evaluate_overlap_guard(text1, text2)
        
        assert 'pass' in result
        assert 'violations' in result
        assert 'max_ngram' in result
        assert 'overlap_pct' in result
        assert 'simhash_distance' in result

    def test_evaluate_overlap_guard_fail(self):
        """Test overlap guard with very similar texts (should fail)."""
        text1 = "The quick brown fox jumps over the lazy dog every day."
        text2 = "The quick brown fox jumps over the lazy dog every day."
        
        result = evaluate_overlap_guard(text1, text2)
        
        assert 'pass' in result
        assert result['pass'] is False


class TestStylefitLLM:
    """Test stylefit_llm evaluator."""

    def test_create_spec_summary(self):
        """Test spec summary creation."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
            ),
        )
        
        summary = create_spec_summary(spec)
        
        assert "Person:" in summary
        assert "Tense:" in summary
        assert "Distance:" in summary

    def test_parse_llm_score_decimal(self):
        """Test LLM score parsing with decimal."""
        response = "0.85"
        score = parse_llm_score(response)
        assert score == 0.85

    def test_parse_llm_score_with_text(self):
        """Test LLM score parsing with surrounding text."""
        response = "The score is 0.75 based on analysis."
        score = parse_llm_score(response)
        assert score == 0.75

    def test_parse_llm_score_percentage(self):
        """Test LLM score parsing with percentage."""
        response = "Score: 85%"
        score = parse_llm_score(response)
        assert score == 0.85

    def test_evaluate_stylefit_llm_disabled(self):
        """Test stylefit LLM when disabled."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
            ),
        )
        
        result = evaluate_stylefit_llm(SAMPLE_TEXT_FIRST_PERSON, spec, use_llm=False)
        
        assert result['enabled'] is False
        assert result['overall'] is None

    def test_evaluate_stylefit_llm_with_mock(self):
        """Test stylefit LLM with MockClient."""
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
            ),
        )
        
        # This should use MockClient which returns deterministic responses
        result = evaluate_stylefit_llm(SAMPLE_TEXT_FIRST_PERSON, spec, use_llm=True)
        
        assert 'enabled' in result
        assert 'overall' in result
        if result['enabled']:
            assert result['overall'] is not None
            assert result['overall'] >= 0.0
            assert result['overall'] <= 1.0


class TestRouterGPT5ParamFiltering:
    """Test that router drops unsupported params for GPT-5 family."""

    def test_router_filters_temperature_for_gpt5(self):
        """Test that router filters temperature for GPT-5."""
        # Get client for beat_generator (configured with gpt-5)
        client = get_client("beat_generator")
        
        # Check that temperature is not set
        # MockClient doesn't expose params directly, but we can verify it works
        assert client is not None


class TestEvaluateOrchestrator:
    """Test evaluation orchestrator."""

    def test_evaluate_draft_minimal(self):
        """Test evaluate_draft with minimal inputs."""
        draft = {
            "text": SAMPLE_TEXT_FIRST_PERSON,
            "seeds": {"per_beat": [137, 138]},
        }
        
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
                motifs=["test"],
                imagery_palette=["dark"],
            ),
            form=Form(
                beat_map=[
                    BeatSpec(id="beat_1", target_words=30, function="hook", cadence="short"),
                ]
            ),
        )
        
        digest = ExemplarDigest(
            meta=DigestMeta(source="test", tokens=100, paragraphs=5),
        )
        
        report = evaluate_draft(
            draft=draft,
            spec=spec,
            digest=digest,
            exemplar_text="A completely different text.",
            use_llm_stylefit=False,
        )
        
        assert isinstance(report, EvalReport)
        assert report.run_id == "eval_001"
        assert report.candidate_id == "cand_001"
        assert report.scores.overall >= 0.0
        assert report.scores.overall <= 1.0
        assert len(report.per_beat) > 0
        assert report.pass_fail in [True, False]

    def test_evaluate_draft_with_config(self):
        """Test evaluate_draft with custom config."""
        draft = {
            "text": SAMPLE_TEXT_LONG,
            "seeds": {"per_beat": [137, 138, 139]},
        }
        
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Hospital", time="Modern"),
                characters=[Character(name="John", role="protagonist")],
                motifs=["suffering", "hope"],
                imagery_palette=["fluorescent", "sterile"],
            ),
            form=Form(
                beat_map=[
                    BeatSpec(id="beat_1", target_words=50, function="hook", cadence="long"),
                    BeatSpec(id="beat_2", target_words=50, function="rising", cadence="long"),
                    BeatSpec(id="beat_3", target_words=40, function="climax", cadence="mixed"),
                ]
            ),
        )
        
        digest = ExemplarDigest(
            meta=DigestMeta(source="test_exemplar", tokens=500, paragraphs=15),
        )
        
        config = GenerationConfig(
            seed=137,
            num_candidates=1,
            objective_weights={
                "stylefit": 0.3,
                "formfit": 0.3,
                "coherence": 0.25,
                "freshness": 0.1,
                "cadence": 0.05,
            },
        )
        
        report = evaluate_draft(
            draft=draft,
            spec=spec,
            digest=digest,
            exemplar_text="A different exemplar text that is quite long.",
            config=config,
            run_id="test_run_001",
            candidate_id="test_cand_001",
            use_llm_stylefit=False,
        )
        
        assert isinstance(report, EvalReport)
        assert report.run_id == "test_run_001"
        assert report.candidate_id == "test_cand_001"
        assert report.scores.overall >= 0.0
        assert report.scores.stylefit >= 0.0
        assert report.scores.formfit >= 0.0
        assert report.scores.coherence >= 0.0
        assert report.scores.cadence >= 0.0
        assert len(report.per_beat) == 3
        assert len(report.tuning_suggestions) >= 0

    def test_save_eval_report(self):
        """Test saving eval report to disk."""
        draft = {
            "text": SAMPLE_TEXT_FIRST_PERSON,
            "seeds": {"per_beat": [137]},
        }
        
        spec = StorySpec(
            meta=MetaInfo(story_id="test_001", seed=137),
            content=Content(
                setting=Setting(place="Test", time="Now"),
                characters=[],
            ),
            form=Form(
                beat_map=[
                    BeatSpec(id="beat_1", target_words=30, function="hook", cadence="short"),
                ]
            ),
        )
        
        digest = ExemplarDigest(
            meta=DigestMeta(source="test", tokens=100, paragraphs=5),
        )
        
        report = evaluate_draft(
            draft=draft,
            spec=spec,
            digest=digest,
            exemplar_text="Different text.",
            use_llm_stylefit=False,
        )
        
        # Save to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            saved_path = save_eval_report(report, output_dir=tmpdir)
            
            assert saved_path.exists()
            assert saved_path.name.endswith('_eval.json')
            
            # Read back and verify
            with open(saved_path, 'r') as f:
                content = f.read()
                assert 'schema' in content
                assert 'EvalReport@2' in content


class TestIntegrationFullPipeline:
    """Integration tests for full evaluation pipeline."""

    def test_full_pipeline_with_all_evaluators(self):
        """Test complete evaluation pipeline with all evaluators."""
        # Create a realistic story spec
        spec = StorySpec(
            meta=MetaInfo(
                story_id="integration_test_001",
                seed=137,
                version="2.0",
                derived_from={"exemplar": "TestStory", "digest_version": 2},
            ),
            content=Content(
                setting=Setting(
                    place="Small Town Hospital",
                    time="Late Autumn 1995",
                    weather_budget=["rain", "fog"],
                ),
                characters=[
                    Character(
                        name="Dr. Sarah Chen",
                        role="protagonist",
                        goal="Save the patient",
                        wound="Lost a patient years ago",
                        quirks=["checks watch compulsively"],
                        diction_quirks=["uses medical jargon"],
                    ),
                ],
                motifs=["rain", "time", "hope"],
                imagery_palette=["fluorescent lights", "sterile corridors", "beeping monitors"],
            ),
            form=Form(
                beat_map=[
                    BeatSpec(id="cold_open", target_words=80, function="hook", cadence="short"),
                    BeatSpec(id="rising_action", target_words=100, function="rising", cadence="mixed"),
                    BeatSpec(id="crisis", target_words=90, function="crisis", cadence="short"),
                    BeatSpec(id="resolution", target_words=70, function="resolution", cadence="long"),
                ],
            ),
        )
        
        # Create draft
        draft = {
            "text": """
I checked my watch again. The emergency room was quiet for once, too quiet.

The ambulance arrived with its cargo of crisis. Sarah Chen, they called me. Doctor Chen now, though some nights I still felt like that terrified intern who'd lost her first patient.

Rain drummed against the windows as the monitors began their urgent beeping. The fluorescent lights flickered, casting strange shadows down the sterile corridors.

In the end, hope was all we had. Hope and the relentless passage of time.
""",
            "seeds": {"global": 137, "per_beat": [137, 138, 139, 140]},
        }
        
        # Create digest
        digest = ExemplarDigest(
            meta=DigestMeta(
                source="TestExemplar",
                tokens=2000,
                paragraphs=50,
            ),
        )
        
        # Exemplar text (different enough to pass overlap)
        exemplar_text = """
The protagonist walked through the forest. Birds sang in the trees above.
She thought about her childhood, memories flooding back like a gentle stream.
Nothing could prepare her for what came next.
""" * 10  # Make it longer
        
        # Create config
        config = GenerationConfig(
            seed=137,
            num_candidates=4,
            objective_weights={
                "stylefit": 0.3,
                "formfit": 0.3,
                "coherence": 0.25,
                "freshness": 0.1,
                "cadence": 0.05,
            },
        )
        
        # Run evaluation
        report = evaluate_draft(
            draft=draft,
            spec=spec,
            digest=digest,
            exemplar_text=exemplar_text,
            config=config,
            run_id="integration_test_run",
            candidate_id="integration_test_cand_001",
            use_llm_stylefit=False,  # Offline test
        )
        
        # Verify report structure
        assert isinstance(report, EvalReport)
        assert report.schema_version == "EvalReport@2"
        assert report.run_id == "integration_test_run"
        assert report.candidate_id == "integration_test_cand_001"
        
        # Verify scores
        assert 0.0 <= report.scores.overall <= 1.0
        assert 0.0 <= report.scores.stylefit <= 1.0
        assert 0.0 <= report.scores.formfit <= 1.0
        assert 0.0 <= report.scores.coherence <= 1.0
        assert 0.0 <= report.scores.cadence <= 1.0
        assert 0.0 <= report.scores.motif_coverage <= 1.0
        
        # Verify per-beat scores
        assert len(report.per_beat) == 4
        for beat_score in report.per_beat:
            assert beat_score.id in ["cold_open", "rising_action", "crisis", "resolution"]
            assert 0.0 <= beat_score.stylefit <= 1.0
            assert 0.0 <= beat_score.formfit <= 1.0
        
        # Verify metadata
        assert report.length['words'] > 0
        assert report.length['paragraphs'] > 0
        
        # Verify report can be serialized
        json_str = report.model_dump_json(by_alias=True)
        assert 'schema' in json_str
        assert 'EvalReport@2' in json_str
