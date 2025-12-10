"""Model registry - centralized model configuration."""

from dataclasses import dataclass
from typing import List, Optional

# Known Ollama model prefixes (for auto-detection)
OLLAMA_PREFIXES = [
    "llama",
    "mistral",
    "gemma",
    "codellama",
    "deepseek",
    "qwen",
    "phi",
    "vicuna",
    "orca",
    "neural-chat",
    "starling",
    "dolphin",
]

# Known Anthropic model prefixes (for auto-detection)
ANTHROPIC_PREFIXES = [
    "claude",
]


@dataclass
class ModelInfo:
    """Information about a model."""
    name: str
    provider: str  # "openai", "anthropic", "ollama"
    description: str = ""


# Known models for autocomplete
KNOWN_MODELS: List[ModelInfo] = [
    # OpenAI
    ModelInfo("gpt-4o-mini", "openai", "Fast, cheap, good quality"),
    ModelInfo("gpt-4o", "openai", "More capable"),
    ModelInfo("gpt-4-turbo", "openai", "GPT-4 Turbo"),
    ModelInfo("gpt-4.1-mini", "openai", "GPT-4.1 mini"),
    ModelInfo("gpt-4.1-nano", "openai", "GPT-4.1 nano"),
    ModelInfo("o1-mini", "openai", "O1 mini"),
    ModelInfo("o3-mini", "openai", "O3 mini"),
    # Anthropic - Claude 4.5 (latest)
    ModelInfo("claude-sonnet-4-5", "anthropic", "Smart, complex agents/coding"),
    ModelInfo("claude-3-7-sonnet-20250219", "anthropic", "Claude 3.7 Sonnet"),
    ModelInfo("claude-haiku-4-5", "anthropic", "Fastest, near-frontier"),
    ModelInfo("claude-opus-4-5", "anthropic", "Max intelligence"),
    ModelInfo("claude-opus-4-5-20251101", "anthropic", "Claude Opus 4.5"),
    ModelInfo("claude-haiku-4-5-20251001", "anthropic", "Claude Haiku 4.5"),
    ModelInfo("claude-sonnet-4-5-20250929", "anthropic", "Claude Sonnet 4.5"),
    ModelInfo("claude-opus-4-1-20250805", "anthropic", "Claude Opus 4.1"),
    ModelInfo("claude-opus-4-20250514", "anthropic", "Claude Opus 4"),
    ModelInfo("claude-sonnet-4-20250514", "anthropic", "Claude Sonnet 4"),
    ModelInfo("claude-3-5-haiku-20241022", "anthropic", "Claude 3.5 Haiku"),
    ModelInfo("claude-3-haiku-20240307", "anthropic", "Claude 3 Haiku"),
    # Ollama - Local models (free)
    ModelInfo("llama3.2:latest", "ollama", "Good general purpose"),
    ModelInfo("mistral:7b-instruct", "ollama", "Fast and capable"),
    ModelInfo("codellama:latest", "ollama", "Code-focused"),
    ModelInfo("deepseek-coder:latest", "ollama", "Code-focused"),
]


def get_model_names() -> List[str]:
    """Return list of known model names for autocomplete."""
    return [m.name for m in KNOWN_MODELS]


def is_ollama_model(model: str) -> bool:
    """Check if a model should use Ollama adapter."""
    model_lower = model.lower()
    return any(model_lower.startswith(prefix) for prefix in OLLAMA_PREFIXES)


def is_anthropic_model(model: str) -> bool:
    """Check if a model should use Anthropic adapter."""
    model_lower = model.lower()
    return any(model_lower.startswith(prefix) for prefix in ANTHROPIC_PREFIXES)


def get_provider(model: str) -> str:
    """Determine the provider for a model."""
    if is_ollama_model(model):
        return "ollama"
    elif is_anthropic_model(model):
        return "anthropic"
    else:
        return "openai"
