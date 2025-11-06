"""Mock LLM client for deterministic testing."""

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
        kwargs.pop('model', None)
        super().__init__(model="mock", **kwargs)
        self._last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def complete(self, prompt: str, **kwargs) -> str:
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
        
        # Pattern matching for different adapter types
        if "label" in prompt.lower() and "motif" in prompt.lower():
            response = self._mock_motif_labels(prompt)
        elif "name" in prompt.lower() and "imagery" in prompt.lower():
            response = self._mock_imagery_names(prompt)
        elif "paraphrase" in prompt.lower() or "beat" in prompt.lower():
            response = self._mock_beat_paraphrase(prompt)
        elif "stylefit" in prompt.lower() or "score" in prompt.lower():
            response = "0.75"
        elif "repair" in prompt.lower():
            response = self._mock_repair(prompt)
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
        # Extract text snippet if present
        if "```" in prompt:
            parts = prompt.split("```")
            if len(parts) >= 2:
                return parts[1].strip()
        return "[repaired text]"
