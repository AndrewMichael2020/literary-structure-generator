"""
Tests for profanity filtering functionality.

Validates structural [bleep] replacement, edge cases, and integration.
"""

import pytest

from literary_structure_generator.utils.profanity import (
    apply_profanity_filter,
    count_bleeps,
    structural_bleep,
)


class TestStructuralBleep:
    """Test core structural_bleep function."""

    def test_single_profanity(self):
        """Test single profanity replacement."""
        text = "This is fucking great!"
        result = structural_bleep(text)
        assert result == "This is [bleep] great!"
        assert "fuck" not in result.lower()

    def test_multiple_profanity(self):
        """Test multiple profanity replacements."""
        text = "What the hell is this shit?"
        result = structural_bleep(text)
        assert result == "What the [bleep] is this [bleep]?"
        assert "hell" not in result.lower()
        assert "shit" not in result.lower()

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        text = "FUCK this Damn thing"
        result = structural_bleep(text)
        assert result == "[bleep] this [bleep] thing"

    def test_custom_substitution(self):
        """Test custom substitution string."""
        text = "This is shit"
        result = structural_bleep(text, substitution="***")
        assert result == "This is ***"

    def test_word_boundaries(self):
        """Test that word boundaries are respected."""
        # "assessment" contains "ass" but should not be filtered
        text = "This assessment is class work"
        result = structural_bleep(text)
        assert result == "This assessment is class work"

    def test_empty_text(self):
        """Test empty text handling."""
        assert structural_bleep("") == ""
        assert structural_bleep(None) == None

    def test_no_profanity(self):
        """Test text without profanity."""
        text = "This is a perfectly clean sentence."
        result = structural_bleep(text)
        assert result == text

    def test_profanity_variants(self):
        """Test different variants of profanity."""
        text = "He was fucking around and got fucked up by that fucker"
        result = structural_bleep(text)
        assert "fuck" not in result.lower()
        assert result.count("[bleep]") == 3

    def test_preserves_whitespace(self):
        """Test that whitespace is preserved."""
        text = "What  the   hell\nis\tthis?"
        result = structural_bleep(text)
        assert "  the   [bleep]\nis\tthis" in result

    def test_preserves_punctuation(self):
        """Test that punctuation is preserved."""
        text = "What the hell?! This is shit."
        result = structural_bleep(text)
        assert result == "What the [bleep]?! This is [bleep]."


class TestCountBleeps:
    """Test profanity counting function."""

    def test_count_single(self):
        """Test counting single profanity."""
        text = "This is shit"
        assert count_bleeps(text) == 1

    def test_count_multiple(self):
        """Test counting multiple profanities."""
        text = "What the fuck is this shit?"
        assert count_bleeps(text) == 2

    def test_count_zero(self):
        """Test counting when no profanity present."""
        text = "This is a clean sentence"
        assert count_bleeps(text) == 0

    def test_count_case_insensitive(self):
        """Test counting is case-insensitive."""
        text = "FUCK this Shit"
        assert count_bleeps(text) == 2

    def test_count_empty(self):
        """Test counting on empty text."""
        assert count_bleeps("") == 0
        assert count_bleeps(None) == 0


class TestApplyProfanityFilter:
    """Test high-level profanity filter application."""

    def test_filter_enabled(self):
        """Test filter when enabled."""
        text = "This is fucking great shit"
        result, count = apply_profanity_filter(text, enabled=True, log_replacements=True)
        assert "fuck" not in result.lower()
        assert "shit" not in result.lower()
        assert count == 2

    def test_filter_disabled(self):
        """Test filter when disabled."""
        text = "This is fucking great shit"
        result, count = apply_profanity_filter(text, enabled=False)
        assert result == text
        assert count is None

    def test_without_logging(self):
        """Test filter without replacement logging."""
        text = "This is shit"
        result, count = apply_profanity_filter(text, enabled=True, log_replacements=False)
        assert "shit" not in result.lower()
        assert count is None

    def test_custom_substitution_in_apply(self):
        """Test custom substitution in apply_profanity_filter."""
        text = "This is damn good"
        result, _ = apply_profanity_filter(text, enabled=True, substitution="[REDACTED]")
        assert result == "This is [REDACTED] good"


class TestNarrativeContext:
    """Test profanity filter in realistic narrative contexts."""

    def test_dialogue_preservation(self):
        """Test that dialogue structure is preserved."""
        text = '"What the hell are you doing?" she asked.\n"None of your damn business," he replied.'
        result = structural_bleep(text)
        assert '"What the [bleep] are you doing?" she asked.' in result
        assert '"None of your [bleep] business," he replied.' in result

    def test_narrative_rhythm(self):
        """Test that narrative rhythm is maintained."""
        text = "The day was going to hell. Everything was shit. He knew it was fucked."
        result = structural_bleep(text)
        # Check structure is preserved
        assert result.count(".") == 3
        assert "The day was going to [bleep]." in result

    def test_mixed_clean_and_profane(self):
        """Test mixed content."""
        text = """He walked down the street, contemplating his choices.
"This is complete shit," he muttered.
The sun was setting beautifully over the horizon."""
        result = structural_bleep(text)
        # Clean parts unchanged
        assert "He walked down the street, contemplating his choices." in result
        assert "The sun was setting beautifully over the horizon." in result
        # Profanity replaced
        assert "[bleep]" in result
        assert "shit" not in result.lower()

    def test_intensity_preservation(self):
        """Test that multiple profanities in sequence maintain intensity."""
        text = "This is fucking bullshit"  # "bullshit" not in list but "shit" is
        result = structural_bleep(text)
        # At least "fucking" should be replaced
        assert "[bleep]" in result
        assert "fuck" not in result.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_profanity_at_start(self):
        """Test profanity at start of text."""
        text = "Shit, I forgot"
        result = structural_bleep(text)
        assert result == "[bleep], I forgot"

    def test_profanity_at_end(self):
        """Test profanity at end of text."""
        text = "I forgot, shit"
        result = structural_bleep(text)
        assert result == "I forgot, [bleep]"

    def test_only_profanity(self):
        """Test text that is only profanity."""
        text = "fuck"
        result = structural_bleep(text)
        assert result == "[bleep]"

    def test_repeated_profanity(self):
        """Test repeated same profanity."""
        text = "fuck fuck fuck"
        result = structural_bleep(text)
        assert result == "[bleep] [bleep] [bleep]"

    def test_unicode_text(self):
        """Test with unicode characters."""
        text = "This is fucking café"
        result = structural_bleep(text)
        assert result == "This is [bleep] café"

    def test_newlines_and_tabs(self):
        """Test preservation of newlines and tabs."""
        text = "Line 1 with shit\nLine 2 with\tdamn"
        result = structural_bleep(text)
        assert result == "Line 1 with [bleep]\nLine 2 with\t[bleep]"


class TestIntegrationScenarios:
    """Test integration scenarios matching actual use cases."""

    def test_clean_mode_always_enabled(self):
        """Test that filter runs even when Clean Mode = false in config."""
        # This simulates the requirement that profanity filtering
        # should be universal, not dependent on a config flag
        text = "This fucking works"
        result = structural_bleep(text)
        assert "[bleep]" in result

    def test_post_llm_filtering(self):
        """Test filtering after LLM generation."""
        llm_output = "The character was pissed off and said 'What the hell?'"
        result = structural_bleep(llm_output)
        assert "[bleep]" in result

    def test_repair_pass_filtering(self):
        """Test filtering after repair pass."""
        repaired_text = "He fixed the damn problem but it was still shit"
        result = structural_bleep(repaired_text)
        assert result == "He fixed the [bleep] problem but it was still [bleep]"

    def test_maintains_tone_markers(self):
        """Test that tone and style markers are preserved."""
        text = "Well, hell, I suppose that's just how it is."
        result = structural_bleep(text)
        # Structure maintained
        assert "Well," in result
        assert "I suppose that's just how it is." in result
        # Profanity replaced
        assert "[bleep]" in result
