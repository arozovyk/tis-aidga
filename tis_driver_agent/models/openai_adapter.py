"""OpenAI model adapter."""

import re
from typing import Optional

from openai import OpenAI


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

    def invoke(self, prompt: str, system_prompt: str = None) -> str:
        """Send prompt to model and get response."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=self.temperature
        )

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
