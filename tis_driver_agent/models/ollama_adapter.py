"""Ollama model adapter for local LLM inference."""

import re
import requests
from typing import Optional


class OllamaAdapter:
    """Adapter for Ollama local LLM API."""

    def __init__(
        self,
        model: str = "llama3.2:latest",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature

    def invoke(self, prompt: str, system_prompt: str = None) -> str:
        """Send prompt to Ollama model and get response."""
        url = f"{self.base_url}/api/generate"

        # Build the full prompt with system prompt if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=None)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: `ollama serve`"
            )

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

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check if our model is in the list (handle tag variations)
                base_model = self.model.split(":")[0]
                return any(base_model in name for name in model_names)
            return False
        except:
            return False
