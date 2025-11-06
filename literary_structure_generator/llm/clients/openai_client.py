"""
OpenAI LLM client implementation.

Connects to OpenAI API with retry logic and error handling.
"""

import os
import random
import time

from literary_structure_generator.llm.base import LLMClient


class OpenAIClient(LLMClient):
    """
    OpenAI API client with retry logic.

    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, **kwargs):
        """
        Initialize OpenAI client.

        Args:
            **kwargs: Parameters passed to base LLMClient

        Raises:
            ImportError: If openai package not installed
            ValueError: If OPENAI_API_KEY not set
        """
        super().__init__(**kwargs)

        try:
            import openai

            self.openai = openai
        except ImportError as e:
            raise ImportError(
                "openai package required for OpenAIClient. Install with: pip install openai"
            ) from e

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set to use OpenAIClient")

        self.client = openai.OpenAI(api_key=api_key, timeout=self.timeout_s)
        self._last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def complete(self, prompt: str, max_retries: int = 2, **kwargs) -> str:
        """
        Generate completion with retry logic.

        Args:
            prompt: Input prompt
            max_retries: Number of retries on failure
            **kwargs: Override parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text

        Raises:
            Exception: If all retries fail
        """
        # Merge kwargs with defaults
        params = {
            "model": kwargs.get("model", self.model),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        if self.seed is not None:
            params["seed"] = self.seed

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}], **params
                )

                # Extract usage statistics
                if hasattr(response, "usage") and response.usage:
                    self._last_usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }

                # Extract and return text
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content.strip()

                raise ValueError("Empty response from OpenAI API")

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    # Exponential backoff with jitter (0.0-1.0 seconds)
                    base_wait = 2**attempt
                    jitter = random.random()
                    wait_time = base_wait + jitter
                    time.sleep(wait_time)
                else:
                    raise last_error from e

        raise RuntimeError("Unexpected retry loop exit")

    def get_usage(self) -> dict:
        """Get token usage from last API call."""
        return self._last_usage
