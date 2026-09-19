"""
LLM Provider Abstraction Layer
"""
import os
from typing import Optional
from configs.settings import settings


class LLMClient:
    """
    Client wrapper for interacting with the configured LLM provider.
    Supports Groq (via OpenAI-compatible API), OpenAI, Gemini, and Anthropic.
    """
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or settings.llm_provider).lower()
        self.model = model or settings.llm_model

    def generate_reply(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        """
        Generates text using the configured provider.
        """
        if self.provider == "groq":
            api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
            if not api_key or "your_" in api_key:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
            
            from openai import OpenAI
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key,
            )
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        elif self.provider == "openai":
            api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key or "your_" in api_key:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        elif self.provider == "anthropic":
            api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key or "your_" in api_key:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            kwargs = {
                "model": self.model,
                "max_tokens": 1024,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            response = client.messages.create(**kwargs)
            return response.content[0].text if response.content else ""

        elif self.provider == "gemini":
            api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not api_key or "your_" in api_key:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text or ""

        else:
            return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
