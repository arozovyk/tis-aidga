"""Anthropic model adapter."""

import re
from typing import Optional

from anthropic import Anthropic


class AnthropicAdapter:
    """Adapter for Anthropic API (Claude models)."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.model = model
        self.temperature = temperature
        self.client = Anthropic(api_key=api_key)

    def invoke(self, prompt: str, system_prompt: str = None) -> str:
        """Send prompt to model and get response."""
        kwargs = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)

        return response.content[0].text

    def extract_code(self, response: str) -> str:
        """Extract C code from markdown response."""
        # Look for ```c ... ``` blocks
        pattern = r"```c\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Fallback: try to find any code block
        pattern = r"```\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Last resort: return as-is (might be raw code)
        return response.strip()
