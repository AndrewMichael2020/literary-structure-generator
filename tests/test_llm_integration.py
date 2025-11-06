"""
Tests for LLM integration components.

Tests cover:
- Mock client behavior
- Router configuration
- Cache mechanism
- Adapter functions
- Drift controls and checksums
"""

import tempfile
from pathlib import Path

from literary_structure_generator.llm.adapters import (
    label_motifs,
    name_imagery,
    paraphrase_beats,
    repair_pass,
    stylefit_score,
)
from literary_structure_generator.llm.base import LLMClient
from literary_structure_generator.llm.cache import LLMCache
from literary_structure_generator.llm.clients.mock_client import MockClient
from literary_structure_generator.llm.router import get_client, get_params, load_routing_config


class TestMockClient:
    """Test mock client for deterministic testing."""

    def test_mock_client_initialization(self):
        """Test mock client can be initialized."""
        client = MockClient(temperature=0.5, max_tokens=100)
        assert client.model == "mock"
        assert client.temperature == 0.5
        assert client.max_tokens == 100

    def test_mock_client_completion(self):
        """Test mock client returns predictable output."""
        client = MockClient()
        response = client.complete("This is a test prompt")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_mock_client_motif_pattern(self):
        """Test mock client recognizes motif labeling pattern."""
        client = MockClient()
        prompt = "Label the following motif anchors:\nblood\nshadow\nlight"
        response = client.complete(prompt)
        assert "theme" in response or "healing" in response

    def test_mock_client_imagery_pattern(self):
        """Test mock client recognizes imagery naming pattern."""
        client = MockClient()
        prompt = "Name the following imagery phrases:\nwhite walls\ncopper taste"
        response = client.complete(prompt)
        assert "imagery" in response or "medical" in response

    def test_mock_client_usage_tracking(self):
        """Test mock client tracks token usage."""
        client = MockClient()
        client.complete("Short prompt")
        usage = client.get_usage()
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage
        assert usage["total_tokens"] > 0


class TestRouter:
    """Test LLM router configuration."""

    def test_load_routing_config(self):
        """Test routing config can be loaded."""
        config = load_routing_config()
        assert "global" in config
        assert "components" in config

    def test_get_params_global(self):
        """Test get_params returns global defaults."""
        params = get_params("unknown_component")
        assert "provider" in params
        assert "temperature" in params
        assert "max_tokens" in params

    def test_get_params_component_override(self):
        """Test component-specific params override globals."""
        params = get_params("motif_labeler")
        assert "model" in params
        # Should have either global or component-specific model
        assert params["model"] in ["mock", "gpt-4o-mini", "gpt-4o"]

    def test_get_client_mock(self):
        """Test get_client returns mock client by default."""
        client = get_client("test_component")
        assert isinstance(client, LLMClient)
        assert isinstance(client, MockClient)

    def test_get_client_component_specific(self):
        """Test get_client can get component-specific client."""
        client = get_client("motif_labeler")
        assert isinstance(client, LLMClient)


class TestCache:
    """Test LLM response caching."""

    def test_cache_initialization(self):
        """Test cache can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_path=str(Path(tmpdir) / "test.db"))
            assert Path(cache.db_path).exists()

    def test_cache_put_get(self):
        """Test storing and retrieving cached responses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_path=str(Path(tmpdir) / "test.db"))

            component = "test_component"
            model = "test_model"
            template_version = "v1"
            params = {"temperature": 0.2}
            input_text = "test input"
            response = "test response"

            cache.put(component, model, template_version, params, input_text, response)
            retrieved = cache.get(component, model, template_version, params, input_text)

            assert retrieved == response

    def test_cache_miss(self):
        """Test cache returns None for cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_path=str(Path(tmpdir) / "test.db"))

            retrieved = cache.get("component", "model", "v1", {}, "input")
            assert retrieved is None

    def test_cache_clear(self):
        """Test cache can be cleared."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_path=str(Path(tmpdir) / "test.db"))

            cache.put("comp1", "model", "v1", {}, "input1", "response1")
            cache.put("comp2", "model", "v1", {}, "input2", "response2")

            stats_before = cache.stats()
            assert stats_before["total_entries"] == 2

            cache.clear()

            stats_after = cache.stats()
            assert stats_after["total_entries"] == 0

    def test_cache_clear_component(self):
        """Test cache can be cleared for specific component."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_path=str(Path(tmpdir) / "test.db"))

            cache.put("comp1", "model", "v1", {}, "input1", "response1")
            cache.put("comp2", "model", "v1", {}, "input2", "response2")

            cache.clear(component="comp1")

            assert cache.get("comp1", "model", "v1", {}, "input1") is None
            assert cache.get("comp2", "model", "v1", {}, "input2") == "response2"

    def test_cache_stats(self):
        """Test cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_path=str(Path(tmpdir) / "test.db"))

            cache.put("comp1", "model", "v1", {}, "input1", "response1")
            cache.put("comp1", "model", "v1", {}, "input2", "response2")
            cache.put("comp2", "model", "v1", {}, "input3", "response3")

            stats = cache.stats()
            assert stats["total_entries"] == 3
            assert "by_component" in stats
            assert stats["by_component"]["comp1"] == 2
            assert stats["by_component"]["comp2"] == 1


class TestAdapters:
    """Test LLM adapter functions."""

    def test_label_motifs(self):
        """Test motif labeling adapter."""
        anchors = ["blood on gauze", "night sky", "trembling hands"]
        labels = label_motifs(anchors, run_id="test_run", iteration=0)

        assert isinstance(labels, list)
        # Should return at least one label
        assert len(labels) >= 1
        # Labels should be strings
        assert all(isinstance(label, str) for label in labels)

    def test_label_motifs_empty(self):
        """Test motif labeling with empty input."""
        labels = label_motifs([], run_id="test_run", iteration=0)
        assert isinstance(labels, list)

    def test_name_imagery(self):
        """Test imagery naming adapter."""
        phrases = ["white hospital walls", "copper taste", "sterile instruments"]
        names = name_imagery(phrases, run_id="test_run", iteration=0)

        assert isinstance(names, list)
        assert len(names) >= 1
        assert all(isinstance(name, str) for name in names)

    def test_name_imagery_empty(self):
        """Test imagery naming with empty input."""
        names = name_imagery([], run_id="test_run", iteration=0)
        assert isinstance(names, list)

    def test_paraphrase_beats(self):
        """Test beat paraphrasing adapter."""
        functions = [
            "establish setting and tone",
            "develop conflict and action",
            "resolution and denouement",
        ]
        summaries = paraphrase_beats(
            functions, register_hint="neutral", run_id="test_run", iteration=0
        )

        assert isinstance(summaries, list)
        assert len(summaries) >= 1
        assert all(isinstance(summary, str) for summary in summaries)

    def test_paraphrase_beats_different_registers(self):
        """Test beat paraphrasing with different registers."""
        functions = ["introduce characters"]

        for register in ["clinical", "lyrical", "terse", "neutral"]:
            summaries = paraphrase_beats(
                functions, register_hint=register, run_id="test_run", iteration=0
            )
            assert isinstance(summaries, list)
            assert len(summaries) >= 1

    def test_stylefit_score(self):
        """Test stylefit scoring adapter."""
        text = "I remember the night it happened. The air was thick. We didn't speak."
        spec_summary = "Person: first, Distance: intimate, Avg sentence: 12 words"

        score = stylefit_score(text, spec_summary, run_id="test_run", iteration=0)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_stylefit_score_empty(self):
        """Test stylefit scoring with empty text."""
        score = stylefit_score("", "spec", run_id="test_run", iteration=0)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_repair_pass(self):
        """Test repair pass adapter."""
        text = "The doctor was very, very, very worried about the patient."
        constraints = {"repetition": "reduce", "tone": "more clinical"}

        repaired = repair_pass(text, constraints, run_id="test_run", iteration=0)

        assert isinstance(repaired, str)
        assert len(repaired) > 0

    def test_repair_pass_empty_constraints(self):
        """Test repair pass with empty constraints."""
        text = "Some text to repair."
        repaired = repair_pass(text, {}, run_id="test_run", iteration=0)
        assert isinstance(repaired, str)

    def test_adapter_caching(self):
        """Test that adapters use caching."""
        anchors = ["test motif"]

        # First call - should hit LLM
        labels1 = label_motifs(anchors, run_id="test_cache", iteration=0, use_cache=True)

        # Second call - should hit cache
        labels2 = label_motifs(anchors, run_id="test_cache", iteration=0, use_cache=True)

        # Results should be identical (deterministic from cache)
        assert labels1 == labels2

    def test_adapter_no_cache(self):
        """Test adapters can bypass cache."""
        anchors = ["test motif"]

        # Call without cache
        labels = label_motifs(anchors, run_id="test_nocache", iteration=0, use_cache=False)
        assert isinstance(labels, list)


class TestDriftControls:
    """Test drift control mechanisms."""

    def test_semantic_checksum_consistency(self):
        """Test that semantic checksums are consistent for normalized outputs."""
        from literary_structure_generator.llm.adapters import _compute_semantic_checksum

        items1 = ["healing", "crisis", "transformation"]
        items2 = ["  Healing  ", "CRISIS", "Transformation"]

        # Should produce same checksum after normalization
        checksum1 = _compute_semantic_checksum(items1)
        checksum2 = _compute_semantic_checksum(items2)

        assert checksum1 == checksum2

    def test_semantic_checksum_different(self):
        """Test that different outputs produce different checksums."""
        from literary_structure_generator.llm.adapters import _compute_semantic_checksum

        items1 = ["healing", "crisis"]
        items2 = ["transformation", "conflict"]

        checksum1 = _compute_semantic_checksum(items1)
        checksum2 = _compute_semantic_checksum(items2)

        assert checksum1 != checksum2

    def test_llm_call_logging(self):
        """Test that LLM calls are logged with metadata."""
        from literary_structure_generator.utils.decision_logger import load_decision_logs

        run_id = "test_drift_logging"

        # Make an LLM call
        label_motifs(["test"], run_id=run_id, iteration=0)

        # Check that it was logged
        logs = load_decision_logs(run_id)

        # Should have at least one LLM-related log entry
        llm_logs = [log for log in logs if log.agent == "LLM"]
        assert len(llm_logs) > 0

        # Check metadata includes drift control fields
        metadata = llm_logs[0].metadata
        assert "component" in metadata
        assert "model" in metadata
        assert "template_version" in metadata
        assert "params_hash" in metadata

    def test_temperature_caps(self):
        """Test that default temperature is capped for stability."""
        params = get_params("motif_labeler")

        # Default temperature should be ≤ 0.3 for stability
        assert params.get("temperature", 1.0) <= 0.3


class TestIntegration:
    """Integration tests for LLM components."""

    def test_full_motif_pipeline(self):
        """Test complete motif labeling pipeline."""
        anchors = [
            "blood on gauze",
            "night sky overhead",
            "trembling hands",
            "white hospital walls",
        ]

        labels = label_motifs(anchors, run_id="integration_test", iteration=0)

        assert len(labels) >= 1
        assert all(isinstance(label, str) for label in labels)

    def test_full_imagery_pipeline(self):
        """Test complete imagery naming pipeline."""
        phrases = [
            "white hospital walls",
            "copper taste of blood",
            "sterile instrument tray",
        ]

        names = name_imagery(phrases, run_id="integration_test", iteration=0)

        assert len(names) >= 1
        assert all(isinstance(name, str) for name in names)

    def test_full_beat_pipeline(self):
        """Test complete beat paraphrasing pipeline."""
        functions = [
            "establish setting and tone",
            "develop conflict and action",
            "resolution and denouement",
        ]

        summaries = paraphrase_beats(
            functions, register_hint="terse", run_id="integration_test", iteration=0
        )

        assert len(summaries) >= 1
        assert all(isinstance(summary, str) for summary in summaries)
