"""Mock LLM client for deterministic testing."""

import re

from literary_structure_generator.llm.base import LLMClient


class MockClient(LLMClient):
    """
    Deterministic mock client for offline testing.

    Returns predictable outputs based on prompt patterns without API calls.
    Useful for CI/CD pipelines and reproducible tests.
    """

    def __init__(self, **kwargs):
        """Initialize mock client."""
        # Remove 'model' from kwargs if present since we override it
        kwargs.pop("model", None)
        super().__init__(model="mock", **kwargs)
        self._last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def complete(self, prompt: str, **_kwargs) -> str:
        """
        Generate mock completion based on prompt patterns.

        Args:
            prompt: Input prompt
            **kwargs: Ignored for mock

        Returns:
            Deterministic mock response
        """
        # Estimate token counts
        prompt_tokens = len(prompt.split())

        # Pattern matching for different adapter types (order matters - most specific first)
        if "generate the beat" in prompt.lower() or "beat specification" in prompt.lower():
            response = self._mock_beat_generation(prompt)
        elif "repair" in prompt.lower() and "original text" in prompt.lower():
            response = self._mock_repair(prompt)
        elif "label" in prompt.lower() and "motif" in prompt.lower():
            response = self._mock_motif_labels(prompt)
        elif "name" in prompt.lower() and "imagery phrases" in prompt.lower():
            response = self._mock_imagery_names(prompt)
        elif "paraphrase" in prompt.lower() or (
            "beat" in prompt.lower()
            and "function" in prompt.lower()
            and "paraphrase" in prompt.lower()
        ):
            response = self._mock_beat_paraphrase(prompt)
        elif "stylefit" in prompt.lower() or "score" in prompt.lower():
            response = "0.75"
        else:
            response = "[mock response]"

        completion_tokens = len(response.split())
        self._last_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

        return response

    def get_usage(self) -> dict:
        """Get mock usage statistics."""
        return self._last_usage

    def _mock_motif_labels(self, prompt: str) -> str:
        """Generate mock motif labels."""
        # Extract anchors from prompt if present
        lines = prompt.split("\n")
        anchors = [line.strip() for line in lines if line.strip() and not line.startswith("#")]

        if len(anchors) > 2:
            # Return mock labels based on anchor count
            return "\n".join([f"theme_{i+1}" for i in range(min(len(anchors), 5))])
        return "healing\ncrisis\ntransformation"

    def _mock_imagery_names(self, prompt: str) -> str:
        """Generate mock imagery names."""
        lines = prompt.split("\n")
        phrases = [line.strip() for line in lines if line.strip() and not line.startswith("#")]

        if len(phrases) > 2:
            return "\n".join([f"imagery_{i+1}" for i in range(min(len(phrases), 5))])
        return "medical_setting\nnight_atmosphere\nurgency"

    def _mock_beat_paraphrase(self, prompt: str) -> str:
        """Generate mock beat paraphrases."""
        # Extract functions from prompt
        lines = prompt.split("\n")
        functions = [line.strip() for line in lines if line.strip() and not line.startswith("#")]

        if len(functions) > 2:
            return "\n".join([f"summary_{i+1}" for i in range(min(len(functions), 5))])
        return "opening scene\ndevelopment\nresolution"

    def _mock_repair(self, prompt: str) -> str:
        """Generate mock repair output."""
        # Extract original text between **Original Text:** and **Constraints:**
        if "**original text:**" in prompt.lower():
            # Try to find text between markers
            match = re.search(
                r"\*\*original text:\*\*\s*```\s*(.+?)\s*```\s*\*\*constraints",
                prompt,
                re.DOTALL | re.IGNORECASE,
            )
            if match:
                original_text = match.group(1).strip()
                # Skip if it's the example from the template
                if "doctor was very" not in original_text.lower():
                    return original_text

        # Fallback: return placeholder that won't corrupt output
        return "[mock repaired text - repair pass would improve this]"

    def _mock_beat_generation(self, prompt: str) -> str:
        """Generate mock beat prose."""
        # Extract target words if present
        target_words = 200
        if "target words:" in prompt.lower():
            match = re.search(r"target words:\*\*\s*(\d+)", prompt, re.IGNORECASE)
            if match:
                target_words = int(match.group(1))

        # Generate mock prose based on function if available
        function = "scene"
        if "function:**" in prompt:
            match = re.search(r"function:\*\*\s*(.+?)[\n*]", prompt, re.IGNORECASE)
            if match:
                function = match.group(1).strip()

        # Generate contextual prose
        sentences = [
            "The morning air carried the scent of rain.",
            "She stood at the window, watching the street below.",
            "Her thoughts drifted to the conversation from last night.",
            "It wasn't supposed to happen this way.",
            "But here she was, facing the consequences.",
            "The phone rang, breaking the silence.",
            "She let it ring three times before answering.",
            "His voice was different, uncertain.",
            "They spoke in careful sentences, measuring each word.",
            "When she hung up, everything had changed.",
            "Outside, the leaves were turning.",
            "The season was shifting, relentless.",
            "She watched a bird land on the windowsill.",
            "For a moment, nothing else mattered.",
            "Then the moment passed.",
        ]

        # Vary based on function
        if "opening" in function.lower() or "establish" in function.lower():
            sentences[0] = "The day began quietly, as most days did."
        elif "develop" in function.lower() or "conflict" in function.lower():
            sentences[0] = "The tension in the room was palpable."
        elif "resolution" in function.lower() or "conclud" in function.lower():
            sentences[0] = "In the end, nothing was quite as she'd expected."

        # Calculate how many sentences needed
        words_per_sentence = sum(len(s.split()) for s in sentences) / len(sentences)
        num_sentences = max(5, int(target_words / words_per_sentence))

        result_sentences = []
        for i in range(num_sentences):
            result_sentences.append(sentences[i % len(sentences)])

        return " ".join(result_sentences)
