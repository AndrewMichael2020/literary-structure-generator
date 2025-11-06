"""
LLM router for per-component model selection.

Loads llm_routing.json and provides get_client() and get_params()
that merge global defaults with component-specific overrides.
"""

import json
import os
from pathlib import Path
from typing import Optional

from literary_structure_generator.llm.base import LLMClient
from literary_structure_generator.llm.clients.mock_client import MockClient

# Cache for routing config
_routing_config: Optional[dict] = None


def load_routing_config() -> dict:
    """
    Load LLM routing configuration.

    Returns:
        Routing configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    global _routing_config

    if _routing_config is not None:
        return _routing_config

    # Look for config in multiple locations
    config_paths = [
        Path(__file__).parent / "config" / "llm_routing.json",
        Path.cwd() / "llm_routing.json",
        Path.cwd() / "config" / "llm_routing.json",
    ]

    # Allow override via environment variable
    env_config = os.getenv("LLM_ROUTING_CONFIG")
    if env_config:
        config_paths.insert(0, Path(env_config))

    for path in config_paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _routing_config = json.load(f)
                return _routing_config

    # Fallback to default if no config found
    _routing_config = {
        "global": {
            "provider": "mock",
            "timeout_s": 20,
            "seed": 137,
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 512,
        },
        "components": {},
    }
    return _routing_config


def get_params(component: str) -> dict:
    """
    Get merged parameters for a component.

    Merges global defaults with component-specific overrides.

    Args:
        component: Component name (e.g., 'motif_labeler', 'imagery_namer')

    Returns:
        Dictionary of LLM parameters
    """
    config = load_routing_config()

    # Start with global defaults
    params = config.get("global", {}).copy()

    # Merge component-specific overrides
    component_params = config.get("components", {}).get(component, {})
    params.update(component_params)

    return params


def get_client(component: str) -> LLMClient:
    """
    Get LLM client for a specific component.

    Args:
        component: Component name (e.g., 'motif_labeler')

    Returns:
        Configured LLMClient instance

    Raises:
        ValueError: If provider is unsupported
    """
    params = get_params(component)
    provider = params.get("provider", "mock")

    # Extract client parameters
    client_params = {
        "model": params.get("model", "gpt-4o-mini"),
        "temperature": params.get("temperature", 0.2),
        "top_p": params.get("top_p", 0.9),
        "max_tokens": params.get("max_tokens", 512),
        "seed": params.get("seed"),
        "timeout_s": params.get("timeout_s", 20),
    }

    # Instantiate appropriate client
    if provider == "mock":
        return MockClient(**client_params)
    if provider == "openai":
        from literary_structure_generator.llm.clients.openai_client import OpenAIClient

        return OpenAIClient(**client_params)
    if provider == "anthropic":
        # Placeholder for future Anthropic support
        raise ValueError(f"Provider '{provider}' not yet implemented. Use 'mock' or 'openai'.")
    raise ValueError(f"Unknown provider: {provider}. Supported: 'mock', 'openai', 'anthropic'")
