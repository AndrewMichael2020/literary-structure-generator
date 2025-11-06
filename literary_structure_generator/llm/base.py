"""
Base LLM client interface.

Defines the common interface for all LLM clients (OpenAI, Anthropic, Mock).
Handles seed management and sampling defaults.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMClient(ABC):
    """Base class for LLM clients."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: int = 512,
        seed: Optional[int] = None,
        timeout_s: int = 20,
    ):
        """
        Initialize LLM client.

        Args:
            model: Model identifier
            temperature: Sampling temperature (0.0-2.0), default 0.2 for stability
            top_p: Nucleus sampling parameter (0.0-1.0)
            max_tokens: Maximum tokens to generate
            seed: Random seed for reproducibility
            timeout_s: Timeout in seconds
        """
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.seed = seed
        self.timeout_s = timeout_s

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """
        Generate completion for the given prompt.

        Args:
            prompt: Input prompt text
            **kwargs: Additional parameters to override defaults

        Returns:
            Generated text completion

        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    def get_usage(self) -> dict:
        """
        Get token usage statistics for the last call.

        Returns:
            Dictionary with 'prompt_tokens', 'completion_tokens', 'total_tokens'
        """
        pass
