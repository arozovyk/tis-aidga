"""OpenAI model adapter."""

import re
from typing import Optional

from openai import OpenAI


# Models that don't support custom temperature (only default=1)
MODELS_NO_TEMPERATURE = [
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-5",
    "gpt-5.1",
    "o1",
    "o1-mini",
    "o1-pro",
    "o3",
    "o3-mini",
    "o3-pro",
    "o4-mini",
]


class OpenAIAdapter:
    """Adapter for OpenAI API."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.model = model
        self.temperature = temperature
        self.client = OpenAI(api_key=api_key)

    def _supports_temperature(self) -> bool:
        """Check if the model supports custom temperature."""
        for prefix in MODELS_NO_TEMPERATURE:
            if self.model.startswith(prefix):
                return False
        return True

    def invoke(self, prompt: str, system_prompt: str = None) -> str:
        """Send prompt to model and get response."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Build kwargs - some models don't support temperature
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        if self._supports_temperature():
            kwargs["temperature"] = self.temperature

        response = self.client.chat.completions.create(**kwargs)

        return response.choices[0].message.content

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
