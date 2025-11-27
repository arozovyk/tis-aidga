"""Model adapters for TIS Driver Agent."""

from .openai_adapter import OpenAIAdapter
from .ollama_adapter import OllamaAdapter

__all__ = ["OpenAIAdapter", "OllamaAdapter"]
