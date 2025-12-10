"""Model adapters for TIS Driver Agent."""

from .openai_adapter import OpenAIAdapter
from .ollama_adapter import OllamaAdapter
from .anthropic_adapter import AnthropicAdapter
from .factory import create_model_adapter
from .registry import (
    OLLAMA_PREFIXES,
    ANTHROPIC_PREFIXES,
    KNOWN_MODELS,
    ModelInfo,
    get_model_names,
    is_ollama_model,
    is_anthropic_model,
    get_provider,
)

__all__ = [
    "OpenAIAdapter",
    "OllamaAdapter",
    "AnthropicAdapter",
    "create_model_adapter",
    "OLLAMA_PREFIXES",
    "ANTHROPIC_PREFIXES",
    "KNOWN_MODELS",
    "ModelInfo",
    "get_model_names",
    "is_ollama_model",
    "is_anthropic_model",
    "get_provider",
]
