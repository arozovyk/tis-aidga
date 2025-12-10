"""Model factory - creates appropriate model adapters."""

import os
import sys

from .registry import is_ollama_model, is_anthropic_model
from .openai_adapter import OpenAIAdapter
from .ollama_adapter import OllamaAdapter
from .anthropic_adapter import AnthropicAdapter


def create_model_adapter(
    model: str,
    api_key: str = None,
    temperature: float = 0.7,
    ollama_url: str = None,
):
    """
    Create the appropriate model adapter based on model name.

    Args:
        model: Model name (e.g., "gpt-4o-mini", "claude-sonnet-4-5", "llama3.2:latest")
        api_key: API key (used for OpenAI models)
        temperature: Sampling temperature
        ollama_url: Ollama server URL (default: http://localhost:11434)

    Returns:
        Model adapter instance (OpenAIAdapter, AnthropicAdapter, or OllamaAdapter)
    """
    if is_ollama_model(model):
        adapter = OllamaAdapter(
            model=model,
            base_url=ollama_url or "http://localhost:11434",
            temperature=temperature,
        )
        # Verify Ollama is available
        if not adapter.is_available():
            print(f"Warning: Ollama model '{model}' may not be available.")
            print("Make sure Ollama is running: `ollama serve`")
            print(f"And the model is pulled: `ollama pull {model}`")
        return adapter
    elif is_anthropic_model(model):
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            print("Error: ANTHROPIC_API_KEY not found.")
            print("Set it via: export ANTHROPIC_API_KEY='your-key'")
            print("Or add to .env file in current directory")
            sys.exit(1)
        return AnthropicAdapter(
            model=model,
            api_key=anthropic_key,
            temperature=temperature,
        )
    else:
        return OpenAIAdapter(
            model=model,
            api_key=api_key,
            temperature=temperature,
        )
