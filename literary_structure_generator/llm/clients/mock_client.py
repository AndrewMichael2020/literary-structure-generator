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
        prompt_tokens = len(prompt.split())
        prompt_lower = prompt.lower()

        if self._is_beat_generation_prompt(prompt_lower):
            response = self._mock_beat_generation(prompt)
        elif self._is_repair_prompt(prompt_lower):
            response = self._mock_repair(prompt)
        elif self._is_motif_prompt(prompt_lower):
            response = self._mock_motif_labels(prompt)
        elif self._is_imagery_prompt(prompt_lower):
            response = self._mock_imagery_names(prompt)
        elif self._is_beat_paraphrase_prompt(prompt_lower):
            response = self._mock_beat_paraphrase(prompt)
        elif self._is_stylefit_prompt(prompt_lower):
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

    def _is_beat_generation_prompt(self, prompt_lower: str) -> bool:
        """Detect beat-generation prompts."""
        return (
            "component:** beat_generator" in prompt_lower
            or "component: beat_generator" in prompt_lower
            or "beat generation prompt template" in prompt_lower
            or "beat specification" in prompt_lower
            or "generate the beat" in prompt_lower
            or "generate prose for this beat" in prompt_lower
        )

    def _is_repair_prompt(self, prompt_lower: str) -> bool:
        """Detect repair prompts."""
        return (
            "component:** repair_pass" in prompt_lower
            or "component: repair_pass" in prompt_lower
            or "repair pass prompt template" in prompt_lower
            or ("repair" in prompt_lower and "original text" in prompt_lower)
        )

    def _is_motif_prompt(self, prompt_lower: str) -> bool:
        """Detect motif-labeling prompts."""
        return "motif" in prompt_lower and (
            "label" in prompt_lower or "anchors" in prompt_lower or "theme" in prompt_lower
        )

    def _is_imagery_prompt(self, prompt_lower: str) -> bool:
        """Detect imagery-naming prompts."""
        return "imagery" in prompt_lower and (
            "name" in prompt_lower or "phrases" in prompt_lower or "palette" in prompt_lower
        )

    def _is_beat_paraphrase_prompt(self, prompt_lower: str) -> bool:
        """Detect beat-paraphrase prompts."""
        return "beat" in prompt_lower and (
            "paraphrase" in prompt_lower or "summaries" in prompt_lower or "summary" in prompt_lower
        )

    def _is_stylefit_prompt(self, prompt_lower: str) -> bool:
        """Detect stylefit prompts."""
        return "stylefit" in prompt_lower or "score (0.0-1.0)" in prompt_lower

    def _mock_motif_labels(self, prompt: str) -> str:
        """Generate mock motif labels."""
        lines = [
            line.strip("- ").strip()
            for line in prompt.split("\n")
            if line.strip() and not line.lstrip().startswith("#")
        ]
        content_lines = [
            line
            for line in lines
            if "version:" not in line.lower()
            and "component:" not in line.lower()
            and "purpose:" not in line.lower()
        ]

        if content_lines:
            return "\n".join([f"theme_{i + 1}" for i in range(min(len(content_lines), 5))])
        return "healing\ncrisis\ntransformation"

    def _mock_imagery_names(self, prompt: str) -> str:
        """Generate mock imagery names."""
        lines = [
            line.strip("- ").strip()
            for line in prompt.split("\n")
            if line.strip() and not line.lstrip().startswith("#")
        ]
        content_lines = [
            line
            for line in lines
            if "version:" not in line.lower()
            and "component:" not in line.lower()
            and "purpose:" not in line.lower()
        ]

        if content_lines:
            return "\n".join([f"imagery_{i + 1}" for i in range(min(len(content_lines), 5))])
        return "medical_setting\nnight_atmosphere\nurgency"

    def _mock_beat_paraphrase(self, prompt: str) -> str:
        """Generate mock beat paraphrases."""
        candidate_lines = []
        for line in prompt.split("\n"):
            stripped = line.strip("- ").strip()
            if not stripped or stripped.startswith("#"):
                continue
            lowered = stripped.lower()
            if any(
                marker in lowered
                for marker in [
                    "version:",
                    "component:",
                    "purpose:",
                    "task",
                    "output",
                    "register",
                ]
            ):
                continue
            if len(stripped.split()) <= 20:
                candidate_lines.append(stripped)

        if candidate_lines:
            return "\n".join(
                [f"summary_{i + 1}: {line}" for i, line in enumerate(candidate_lines[:5])]
            )
        return "opening scene\ndevelopment\nresolution"

    def _mock_repair(self, prompt: str) -> str:
        """Generate mock repair output."""
        match = re.search(
            r"\*\*original text:\*\*\s*```\s*(.+?)\s*```\s*\*\*constraints",
            prompt,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            original_text = match.group(1).strip()
            if "doctor was very" not in original_text.lower():
                return original_text

        fenced_blocks = re.findall(r"```\s*(.+?)\s*```", prompt, flags=re.DOTALL)
        for block in fenced_blocks:
            clean_block = block.strip()
            if clean_block and "doctor was very" not in clean_block.lower():
                return clean_block

        return "[mock repaired text - repair pass would improve this]"

    def _mock_beat_generation(self, prompt: str) -> str:
        """Generate mock beat prose."""
        target_words = 200
        target_patterns = [
            r"\*\*target words:\*\*\s*(\d+)",
            r"target words:\s*(\d+)",
            r"target_words[^\d]*(\d+)",
        ]
        for pattern in target_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                target_words = int(match.group(1))
                break

        function = "scene"
        function_patterns = [
            r"\*\*function:\*\*\s*(.+?)(?:\n|\r|$)",
            r"function:\s*(.+?)(?:\n|\r|$)",
        ]
        for pattern in function_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                function = match.group(1).strip()
                break

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

        if "opening" in function.lower() or "establish" in function.lower():
            sentences[0] = "The day began quietly, as most days did."
        elif "develop" in function.lower() or "conflict" in function.lower():
            sentences[0] = "The tension in the room was palpable."
        elif "resolution" in function.lower() or "conclud" in function.lower():
            sentences[0] = "In the end, nothing was quite as she'd expected."

        words_per_sentence = sum(len(sentence.split()) for sentence in sentences) / len(sentences)
        num_sentences = max(5, int(target_words / words_per_sentence))

        result_sentences = []
        for i in range(num_sentences):
            result_sentences.append(sentences[i % len(sentences)])

        return " ".join(result_sentences)
